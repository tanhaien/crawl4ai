import os
import re
import io
import zipfile
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Iterable, List, Optional, Set, Tuple, Dict

import requests
from bs4 import BeautifulSoup
from slugify import slugify
from urllib.parse import urljoin, urlparse, urldefrag

from app.types import CrawlItem


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

ALLOWED_DOC_EXT = {"pdf","doc","docx","xls","xlsx","ppt","pptx","csv","txt","zip","rar","7z"}
IMAGE_EXT = {"png","jpg","jpeg","webp"}


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\s]+", " ", name).strip()
    name = slugify(name, separator="-")
    if not name:
        name = "file"
    return name


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def normalize_url(base_url: str, href: str) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if href.startswith("mailto:") or href.startswith("javascript:"):
        return None
    try:
        abs_url = urljoin(base_url, href)
        abs_url, _ = urldefrag(abs_url)
        return abs_url
    except Exception:
        return None


def same_site(base: str, target: str) -> bool:
    try:
        b = urlparse(base)
        t = urlparse(target)
        return (b.scheme, b.netloc) == (t.scheme, t.netloc)
    except Exception:
        return False


def get_extension_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if "." in path:
        return path.rsplit(".", 1)[-1]
    return ""


def is_file_candidate(url: str, include_images: bool) -> bool:
    ext = get_extension_from_url(url)
    if ext in ALLOWED_DOC_EXT:
        return True
    if include_images and ext in IMAGE_EXT:
        return True
    return False


def request_html(url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "").lower()
        if resp.status_code == 200 and "text/html" in ct:
            return resp.text
    except Exception:
        return None
    return None


def extract_links(html: str, base_url: str) -> Tuple[Set[str], Set[str]]:
    page_links: Set[str] = set()
    file_links: Set[str] = set()
    soup = BeautifulSoup(html, "lxml")

    # anchors
    for a in soup.find_all("a", href=True):
        url = normalize_url(base_url, a.get("href"))
        if not url:
            continue
        if is_file_candidate(url, include_images=True):
            file_links.add(url)
        else:
            page_links.add(url)

    # area maps
    for a in soup.find_all("area", href=True):
        url = normalize_url(base_url, a.get("href"))
        if not url:
            continue
        if is_file_candidate(url, include_images=True):
            file_links.add(url)
        else:
            page_links.add(url)

    # link tags (some direct assets)
    for l in soup.find_all("link", href=True):
        url = normalize_url(base_url, l.get("href"))
        if not url:
            continue
        if is_file_candidate(url, include_images=True):
            file_links.add(url)

    # source tags
    for s in soup.find_all(["source"], src=True):
        url = normalize_url(base_url, s.get("src"))
        if not url:
            continue
        if is_file_candidate(url, include_images=True):
            file_links.add(url)

    return page_links, file_links


def filename_from_headers(url: str, resp: requests.Response) -> str:
    cd = resp.headers.get("Content-Disposition")
    if cd:
        m = re.search(r'filename\*=UTF-8''([^;]+)', cd)
        if m:
            return sanitize_filename(m.group(1))
        m = re.search(r'filename="?([^";]+)"?', cd)
        if m:
            return sanitize_filename(m.group(1))
    # fallback from url path
    path = urlparse(url).path
    base = os.path.basename(path) or "file"
    return sanitize_filename(base)


def download_one(url: str, dest_dir: str, max_size_mb: Optional[int], session: Optional[requests.Session] = None) -> CrawlItem:
    sess = session or requests.Session()
    try:
        with sess.get(url, headers=DEFAULT_HEADERS, stream=True, timeout=25, allow_redirects=True) as resp:
            status = resp.status_code
            if status != 200:
                return CrawlItem(source_page_url="", file_url=url, local_path=None, filename=None, mime_type=resp.headers.get("Content-Type"), size_bytes=None, status="failed", error=f"HTTP {status}")

            content_length = resp.headers.get("Content-Length")
            if content_length is not None and max_size_mb is not None:
                try:
                    size_bytes = int(content_length)
                    if size_bytes > max_size_mb * 1024 * 1024:
                        return CrawlItem(source_page_url="", file_url=url, local_path=None, filename=None, mime_type=resp.headers.get("Content-Type"), size_bytes=size_bytes, status="skipped", error="exceeds limit")
                except ValueError:
                    pass

            filename = filename_from_headers(url, resp)
            name, ext = os.path.splitext(filename)
            if not ext:
                ext_guess = get_extension_from_url(url)
                if ext_guess:
                    filename = f"{filename}.{ext_guess}"
            safe_name = sanitize_filename(filename)
            ensure_dir(dest_dir)
            final_path = os.path.join(dest_dir, safe_name)

            # dedup
            counter = 1
            while os.path.exists(final_path):
                final_path = os.path.join(dest_dir, f"{name}-{counter}{ext}")
                counter += 1

            size_accum = 0
            with open(final_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    size_accum += len(chunk)
                    if max_size_mb is not None and size_accum > max_size_mb * 1024 * 1024:
                        # stop write and mark skipped
                        f.close()
                        try:
                            os.remove(final_path)
                        except Exception:
                            pass
                        return CrawlItem(source_page_url="", file_url=url, local_path=None, filename=None, mime_type=resp.headers.get("Content-Type"), size_bytes=size_accum, status="skipped", error="exceeds limit")
                    f.write(chunk)

            return CrawlItem(source_page_url="", file_url=url, local_path=final_path, filename=os.path.basename(final_path), mime_type=resp.headers.get("Content-Type"), size_bytes=size_accum, status="success", error=None)
    except Exception as e:
        return CrawlItem(source_page_url="", file_url=url, local_path=None, filename=None, mime_type=None, size_bytes=None, status="failed", error=str(e))


class BFSCrawler:
    def __init__(self, root_url: str, max_depth: int = 3, include_images: bool = False, max_pages: int = 200):
        self.root_url = root_url
        self.max_depth = max_depth
        self.include_images = include_images
        self.max_pages = max_pages
        self.visited_pages: Set[str] = set()
        self.file_urls: Set[str] = set()
        self.session = requests.Session()
        self.root_site = urlparse(root_url).netloc
        self.root_scheme = urlparse(root_url).scheme

    def crawl(self) -> Tuple[List[str], Set[str]]:
        from collections import deque
        q = deque([(self.root_url, 0)])
        collected_pages: List[str] = []

        while q and len(collected_pages) < self.max_pages:
            url, depth = q.popleft()
            if url in self.visited_pages:
                continue
            self.visited_pages.add(url)

            html = request_html(url)
            if not html:
                continue

            collected_pages.append(url)
            page_links, file_links = extract_links(html, url)

            # keep only same-site links
            for p in page_links:
                if same_site(self.root_url, p):
                    if depth + 1 <= self.max_depth:
                        q.append((p, depth + 1))

            # files: same site or any? Keep any (some CDNs)
            for f in file_links:
                # only add if matches filter
                if is_file_candidate(f, include_images=self.include_images):
                    self.file_urls.add(f)

        return collected_pages, self.file_urls

    def download_all(self, dest_dir: str, max_size_mb: Optional[int] = None, max_workers: int = 6) -> List[CrawlItem]:
        ensure_dir(dest_dir)
        items: List[CrawlItem] = []
        futures = []
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            for url in sorted(self.file_urls):
                futures.append(ex.submit(download_one, url, dest_dir, max_size_mb, self.session))
            for fut in as_completed(futures):
                item = fut.result()
                items.append(item)
        return items


def make_zip(items: List[CrawlItem], zip_name: str) -> Tuple[bytes, int]:
    mem = io.BytesIO()
    count = 0
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for it in items:
            if it.status == "success" and it.local_path and os.path.exists(it.local_path):
                arcname = it.filename or os.path.basename(it.local_path)
                zf.write(it.local_path, arcname=arcname)
                count += 1
    mem.seek(0)
    return mem.read(), count
