import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Set, Dict, List
from urllib.parse import urljoin, urlparse
from datetime import datetime
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from tqdm import tqdm
import logging

CONFIG = {
    "input_file": "./crawl_data.txt",
    "output_dir": "downloaded_pdfs",
    "max_concurrent_downloads": 5,
    "max_pages_per_site": 50,  
    "timeout": 60,
    "user_agent": "Mozilla/5.0 (compatible; PDFCrawler/1.0)",
    "log_file": "pdf_crawler.log",
    "metadata_file": "pdf_downloads_metadata.json",
    "progress_file": "pdf_crawler_progress.json",
}

# Configure logging with duplicate prevention
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Only add handlers if they don't already exist
if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(CONFIG["log_file"])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


class PDFCrawler:
    def __init__(self):
        self.output_dir = Path(CONFIG["output_dir"])
        self.output_dir.mkdir(exist_ok=True)

        self.visited_urls: Set[str] = set()
        self.downloaded_pdfs: Dict[str, str] = {}
        self.discovered_pdfs: List[Dict] = []
        self.failed_downloads: List[Dict] = []
        self.metadata: Dict = {
            "sites_processed": 0,
            "pdfs_found": 0,
            "pdfs_downloaded": 0,
            "pdfs_failed": 0,
            "total_size_mb": 0.0
        }

        self.load_progress()

    def load_progress(self):
        progress_file = Path(CONFIG["progress_file"])
        if progress_file.exists():
            try:
                with open(progress_file, 'r') as f:
                    data = json.load(f)
                    self.downloaded_pdfs = data.get("downloaded_pdfs", {})
                    self.metadata = data.get("metadata", self.metadata)
                    logger.info(f"Resumed: {len(self.downloaded_pdfs)} PDFs already downloaded")
            except Exception as e:
                logger.error(f"Failed to load progress: {e}")

    def save_progress(self):
        try:
            with open(CONFIG["progress_file"], 'w') as f:
                json.dump({
                    "downloaded_pdfs": self.downloaded_pdfs,
                    "metadata": self.metadata
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=CONFIG["timeout"])) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '').lower()

                    if 'pdf' in content_type:
                        logger.debug(f"Direct PDF link detected: {url}")
                        return ""

                    try:
                        return await response.text(errors='ignore')
                    except UnicodeDecodeError:
                        logger.warning(f"Encoding error for {url}, skipping")
                        return ""
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return ""
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching {url}: {e}")
            return ""
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return ""

    async def download_pdf(self, session: aiohttp.ClientSession, pdf_url: str, source_site: str, semaphore: asyncio.Semaphore = None) -> bool:
        if pdf_url in self.downloaded_pdfs:
            logger.debug(f"Already downloaded: {pdf_url}")
            return True

        # Acquire semaphore to limit concurrent downloads
        if semaphore:
            async with semaphore:
                return await self._download_pdf_impl(session, pdf_url, source_site)
        else:
            return await self._download_pdf_impl(session, pdf_url, source_site)
    
    async def _download_pdf_impl(self, session: aiohttp.ClientSession, pdf_url: str, source_site: str) -> bool:
        try:
            site_domain = urlparse(source_site).netloc.replace('www.', '')
            site_dir = self.output_dir / site_domain
            site_dir.mkdir(exist_ok=True)

            pdf_filename = self.generate_filename(pdf_url)
            filepath = site_dir / pdf_filename

            async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')

                    if 'pdf' not in content_type.lower():
                        logger.warning(f"Not a PDF: {pdf_url} (Content-Type: {content_type})")
                        return False

                    content = await response.read()
                    file_size_mb = len(content) / (1024 * 1024)

                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(content)

                    self.downloaded_pdfs[pdf_url] = str(filepath)
                    self.metadata["pdfs_downloaded"] += 1
                    self.metadata["total_size_mb"] += file_size_mb

                    logger.info(f"Downloaded ({file_size_mb:.2f} MB): {pdf_filename}")
                    return True
                else:
                    logger.error(f"HTTP {response.status} for PDF: {pdf_url}")
                    self.failed_downloads.append({
                        "url": pdf_url,
                        "source_site": source_site,
                        "error": f"HTTP {response.status}"
                    })
                    return False

        except Exception as e:
            logger.error(f"Error downloading {pdf_url}: {e}")
            self.failed_downloads.append({
                "url": pdf_url,
                "source_site": source_site,
                "error": str(e)
            })
            self.metadata["pdfs_failed"] += 1
            return False

    def generate_filename(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        filename = path_parts[-1] if path_parts[-1] else 'document.pdf'

        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'

        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{url_hash}{ext}"

        return filename

    def find_pdf_links(self, html: str, base_url: str) -> Set[str]:
        pdf_links = set()

        try:
            soup = BeautifulSoup(html, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']

                full_url = urljoin(base_url, href)

                if self.is_pdf_link(full_url):
                    pdf_links.add(full_url)


            for tag in soup.find_all(['iframe', 'embed', 'object']):
                src = tag.get('src') or tag.get('data')
                if src:
                    full_url = urljoin(base_url, src)
                    if self.is_pdf_link(full_url):
                        pdf_links.add(full_url)

        except Exception as e:
            logger.error(f"Error parsing HTML for {base_url}: {e}")

        return pdf_links

    def is_pdf_link(self, url: str) -> bool:
        """Check if URL points to a PDF"""
        url_lower = url.lower()

        # Check file extension
        if url_lower.endswith('.pdf'):
            return True

        # Check query parameters
        if 'pdf' in url_lower and any(param in url_lower for param in ['download', 'file', 'doc']):
            return True

        return False

    def find_page_links(self, html: str, base_url: str) -> Set[str]:
        links = set()
        base_domain = urlparse(base_url).netloc

        try:
            soup = BeautifulSoup(html, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)

                if urlparse(full_url).netloc == base_domain:
                    full_url = full_url.split('#')[0]

                    if not any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.css', '.js', '.xml']):
                        links.add(full_url)

        except Exception as e:
            logger.error(f"Error finding page links: {e}")

        return links

    async def crawl_site(self, session: aiohttp.ClientSession, start_url: str, semaphore: asyncio.Semaphore, mode: str = 'discover'):
        logger.info(f"Crawling site: {start_url} (mode: {mode})")

        if self.is_pdf_link(start_url):
            logger.info(f"Direct PDF link provided: {start_url}")
            pdf_links = {start_url}
            pages_crawled = 0
        else:
            to_visit = {start_url}
            pdf_links = set()
            pages_crawled = 0

            while to_visit and pages_crawled < CONFIG["max_pages_per_site"]:
                url = to_visit.pop()

                if url in self.visited_urls:
                    continue

                self.visited_urls.add(url)
                pages_crawled += 1

                html = await self.fetch_page(session, url)
                if not html:
                    continue

                pdfs = self.find_pdf_links(html, url)
                pdf_links.update(pdfs)

                if pages_crawled < CONFIG["max_pages_per_site"]:
                    new_links = self.find_page_links(html, url)
                    to_visit.update(new_links - self.visited_urls)

                await asyncio.sleep(0.5)

        logger.info(f"Found {len(pdf_links)} PDFs on {start_url} (crawled {pages_crawled} pages)")
        self.metadata["pdfs_found"] += len(pdf_links)

        if mode == 'discover':
            # Discovery mode: collect metadata only, don't download
            site_domain = urlparse(start_url).netloc.replace('www.', '')
            for pdf_url in pdf_links:
                pdf_filename = self.generate_filename(pdf_url)
                self.discovered_pdfs.append({
                    'url': pdf_url,
                    'source_site': start_url,
                    'filename': pdf_filename,
                    'domain': site_domain,
                    'discovered_at': datetime.now().isoformat()
                })
            logger.info(f"Discovered {len(pdf_links)} PDFs in discovery mode")
        else:
            # Download mode: download PDFs as before
            download_tasks = [
                self.download_pdf(session, pdf_url, start_url, semaphore)
                for pdf_url in pdf_links
            ]

            if download_tasks:
                await asyncio.gather(*download_tasks)

        self.metadata["sites_processed"] += 1
        self.save_progress()

    async def run(self, urls: List[str], mode: str = 'discover') -> Dict:
        logger.info(f"Starting PDF crawler for {len(urls)} sites (mode: {mode})")

        semaphore = asyncio.Semaphore(CONFIG["max_concurrent_downloads"])

        connector = aiohttp.TCPConnector(limit=CONFIG["max_concurrent_downloads"])
        async with aiohttp.ClientSession(
            headers={"User-Agent": CONFIG["user_agent"]},
            connector=connector,
            max_line_size=16384,
            max_field_size=16384
        ) as session:
            tasks = []
            for url in urls:
                tasks.append(self.crawl_site(session, url, semaphore, mode))

            for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Crawling sites"):
                await task

        self.save_metadata()
        if mode == 'download':
            self.print_summary()
        
        return self.generate_summary()

    async def download_selected_pdfs(self, selected_urls: List[Dict]) -> Dict:
        """Download only user-selected PDFs from previously discovered list"""
        logger.info(f"Starting download of {len(selected_urls)} selected PDFs")
        
        semaphore = asyncio.Semaphore(CONFIG["max_concurrent_downloads"])
        connector = aiohttp.TCPConnector(limit=CONFIG["max_concurrent_downloads"])
        async with aiohttp.ClientSession(
            headers={"User-Agent": CONFIG["user_agent"]},
            connector=connector,
            max_line_size=16384,
            max_field_size=16384
        ) as session:
            download_tasks = []
            for pdf_info in selected_urls:
                url = pdf_info['url']
                source = pdf_info.get('source_site', url)
                download_tasks.append(
                    self.download_pdf(session, url, source, semaphore)
                )
            
            if download_tasks:
                await asyncio.gather(*download_tasks)
        
        return self.generate_summary()

    def generate_summary(self) -> Dict:
        """Generate summary of crawler results"""
        return {
            "metadata": self.metadata,
            "downloaded_pdfs": self.downloaded_pdfs,
            "discovered_pdfs": self.discovered_pdfs,
            "failed_downloads": self.failed_downloads
        }

    def save_metadata(self):
        metadata = {
            "metadata": self.metadata,
            "downloaded_pdfs": self.downloaded_pdfs,
            "discovered_pdfs": self.discovered_pdfs,
            "failed_downloads": self.failed_downloads
        }

        with open(CONFIG["metadata_file"], 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata saved to {CONFIG['metadata_file']}")

    def print_summary(self):
        print("\n" + "="*60)
        print("PDF CRAWLER SUMMARY")
        print("="*60)
        print(f"Sites processed: {self.metadata['sites_processed']}")
        print(f"PDFs found: {self.metadata['pdfs_found']}")
        print(f"PDFs downloaded: {self.metadata['pdfs_downloaded']}")
        print(f"PDFs failed: {self.metadata['pdfs_failed']}")
        print(f"Total size: {self.metadata['total_size_mb']:.2f} MB")
        print(f"Output directory: {self.output_dir}")
        print(f"Failed downloads: {len(self.failed_downloads)}")
        print("="*60 + "\n")


def load_urls_from_file(filepath: str) -> List[str]:
    urls = []

    with open(filepath, 'r') as f:
        content = f.read()

        lines = content.split('\n')
        current_url = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if '→' in line:
                line = line.split('→', 1)[1].strip()

            line = line.strip('"').strip()

            if line.startswith('http'):
                if current_url:
                    urls.append(current_url)
                current_url = line
            elif current_url:
                if line.startswith('http'):
                    urls.append(line)
                current_url = ""

        if current_url:
            urls.append(current_url)

    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


async def main():
    urls = load_urls_from_file(CONFIG["input_file"])
    logger.info(f"Loaded {len(urls)} URLs from {CONFIG['input_file']}")

    if not urls:
        logger.error("No URLs found in input file")
        return

    crawler = PDFCrawler()
    await crawler.run(urls)


if __name__ == "__main__":
    asyncio.run(main())
