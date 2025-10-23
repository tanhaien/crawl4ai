"""
URL Analyzer Module - Phân tích URL và phát hiện resources
"""

import requests
import mimetypes
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import List, Dict, Set, Optional, Tuple
import re
from datetime import datetime


class URLAnalyzer:
    """Class để phân tích URL và phát hiện các resources"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # File extensions để detect file types
        self.file_extensions = {
            'pdf': ['.pdf'],
            'docx': ['.docx', '.doc'],
            'xlsx': ['.xlsx', '.xls'],
            'pptx': ['.pptx', '.ppt'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
            'videos': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'code': ['.js', '.css', '.html', '.htm', '.php', '.py', '.java', '.cpp', '.c'],
            'data': ['.json', '.xml', '.csv', '.txt', '.rtf']
        }
    
    def scan_url(self, url: str, max_depth: int = 2) -> Dict:
        """
        Main scanning function - phân tích URL và tìm resources
        
        Args:
            url: URL cần scan
            max_depth: Độ sâu tối đa để crawl links
            
        Returns:
            Dict chứa kết quả scan
        """
        try:
            # Parse URL để lấy domain
            parsed_url = urlparse(url)
            base_domain = parsed_url.netloc
            
            # Fetch trang chính
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url)
            
            # Detect files
            files = self.detect_files(soup, url)
            
            # Extract links
            links = self.extract_links(soup, url, base_domain, max_depth)
            
            # Analyze content structure
            content_analysis = self.analyze_content(soup)
            
            return {
                'url': url,
                'domain': base_domain,
                'metadata': metadata,
                'files': files,
                'links': links,
                'content_analysis': content_analysis,
                'scan_time': datetime.now().isoformat(),
                'status': 'success'
            }
            
        except Exception as e:
            return {
                'url': url,
                'status': 'error',
                'error': str(e),
                'scan_time': datetime.now().isoformat()
            }
    
    def detect_files(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """
        Tìm tất cả file links trong trang
        
        Args:
            soup: BeautifulSoup object của trang
            base_url: URL gốc để resolve relative links
            
        Returns:
            List các file được tìm thấy
        """
        files = []
        file_links = set()  # Để tránh duplicate
        
        # Tìm tất cả links có thể là files
        for link in soup.find_all(['a', 'link'], href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip nếu đã xử lý URL này
            if full_url in file_links:
                continue
            file_links.add(full_url)
            
            # Detect file type
            file_info = self._analyze_file_url(full_url, link)
            if file_info:
                files.append(file_info)
        
        # Tìm trong img, video, audio tags
        for tag in soup.find_all(['img', 'video', 'audio', 'source']):
            src = tag.get('src') or tag.get('data-src')
            if src:
                full_url = urljoin(base_url, src)
                if full_url not in file_links:
                    file_links.add(full_url)
                    file_info = self._analyze_file_url(full_url, tag)
                    if file_info:
                        files.append(file_info)
        
        return files
    
    def extract_links(self, soup: BeautifulSoup, base_url: str, base_domain: str, max_depth: int) -> Dict:
        """
        Lấy all links với classification
        
        Args:
            soup: BeautifulSoup object
            base_url: URL gốc
            base_domain: Domain gốc
            max_depth: Độ sâu tối đa
            
        Returns:
            Dict chứa links được phân loại
        """
        links = {
            'internal': [],
            'external': [],
            'same_domain': [],
            'total_count': 0
        }
        
        link_set = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Skip nếu đã xử lý
            if full_url in link_set:
                continue
            link_set.add(full_url)
            
            parsed_url = urlparse(full_url)
            link_domain = parsed_url.netloc
            
            link_info = {
                'url': full_url,
                'text': link.get_text().strip() or href,
                'domain': link_domain,
                'depth': 0  # Sẽ được tính sau
            }
            
            # Phân loại links
            if link_domain == base_domain:
                links['same_domain'].append(link_info)
            elif link_domain:
                links['external'].append(link_info)
            else:
                links['internal'].append(link_info)
        
        links['total_count'] = len(link_set)
        return links
    
    def analyze_content(self, soup: BeautifulSoup) -> Dict:
        """
        Phân tích content structure
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dict chứa phân tích content
        """
        # Remove script và style
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Đếm các elements
        content_stats = {
            'headings': {
                'h1': len(soup.find_all('h1')),
                'h2': len(soup.find_all('h2')),
                'h3': len(soup.find_all('h3')),
                'h4': len(soup.find_all('h4')),
                'h5': len(soup.find_all('h5')),
                'h6': len(soup.find_all('h6'))
            },
            'paragraphs': len(soup.find_all('p')),
            'images': len(soup.find_all('img')),
            'links': len(soup.find_all('a')),
            'tables': len(soup.find_all('table')),
            'lists': len(soup.find_all(['ul', 'ol'])),
            'forms': len(soup.find_all('form')),
            'text_length': len(soup.get_text().strip())
        }
        
        # Detect navigation
        nav_elements = soup.find_all(['nav', 'menu', 'ul'], class_=re.compile(r'nav|menu', re.I))
        content_stats['navigation_elements'] = len(nav_elements)
        
        # Detect main content areas
        main_content = soup.find_all(['main', 'article', 'section'], class_=re.compile(r'content|main|article', re.I))
        content_stats['main_content_areas'] = len(main_content)
        
        return content_stats
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata từ trang"""
        metadata = {
            'title': '',
            'description': '',
            'keywords': '',
            'author': '',
            'language': '',
            'viewport': '',
            'robots': '',
            'canonical': '',
            'og_title': '',
            'og_description': '',
            'og_image': '',
            'twitter_card': ''
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            property_attr = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name == 'description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = content
            elif name == 'author':
                metadata['author'] = content
            elif name == 'language':
                metadata['language'] = content
            elif name == 'viewport':
                metadata['viewport'] = content
            elif name == 'robots':
                metadata['robots'] = content
            elif name == 'canonical':
                metadata['canonical'] = content
            elif property_attr == 'og:title':
                metadata['og_title'] = content
            elif property_attr == 'og:description':
                metadata['og_description'] = content
            elif property_attr == 'og:image':
                metadata['og_image'] = content
            elif name == 'twitter:card':
                metadata['twitter_card'] = content
        
        return metadata
    
    def _analyze_file_url(self, url: str, element) -> Optional[Dict]:
        """
        Phân tích một URL để xác định có phải file không
        
        Args:
            url: URL cần phân tích
            element: HTML element chứa URL
            
        Returns:
            Dict chứa thông tin file hoặc None nếu không phải file
        """
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Check file extension
        file_type = None
        file_category = None
        
        for category, extensions in self.file_extensions.items():
            for ext in extensions:
                if path.endswith(ext):
                    file_type = ext
                    file_category = category
                    break
            if file_type:
                break
        
        # Nếu không có extension, check MIME type từ URL
        if not file_type:
            mime_type, _ = mimetypes.guess_type(url)
            if mime_type:
                if mime_type.startswith('image/'):
                    file_category = 'images'
                elif mime_type.startswith('video/'):
                    file_category = 'videos'
                elif mime_type.startswith('audio/'):
                    file_category = 'audio'
                elif mime_type == 'application/pdf':
                    file_category = 'pdf'
                elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                    file_category = 'docx'
                elif mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
                    file_category = 'xlsx'
                elif mime_type in ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
                    file_category = 'pptx'
                elif mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
                    file_category = 'archives'
                else:
                    file_category = 'other'
        
        # Chỉ return nếu là file
        if file_category:
            return {
                'url': url,
                'filename': parsed_url.path.split('/')[-1] or 'unknown',
                'file_type': file_type or 'unknown',
                'file_category': file_category,
                'size': 'unknown',  # Sẽ được update sau
                'element_tag': element.name,
                'element_text': element.get_text().strip() if hasattr(element, 'get_text') else '',
                'mime_type': mimetypes.guess_type(url)[0] or 'unknown'
            }
        
        return None
    
    def get_file_size(self, url: str) -> str:
        """
        Lấy file size từ URL
        
        Args:
            url: URL của file
            
        Returns:
            String chứa size hoặc 'unknown'
        """
        try:
            response = requests.head(url, headers=self.headers, timeout=10)
            content_length = response.headers.get('content-length')
            
            if content_length:
                size_bytes = int(content_length)
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            else:
                return "unknown"
        except:
            return "unknown"


def scan_url(url: str, max_depth: int = 2) -> Dict:
    """
    Convenience function để scan URL
    
    Args:
        url: URL cần scan
        max_depth: Độ sâu tối đa
        
    Returns:
        Dict chứa kết quả scan
    """
    analyzer = URLAnalyzer()
    return analyzer.scan_url(url, max_depth)


if __name__ == "__main__":
    # Test function
    test_url = "https://example.com"
    result = scan_url(test_url)
    print(f"Scan result for {test_url}:")
    print(f"Files found: {len(result.get('files', []))}")
    print(f"Links found: {result.get('links', {}).get('total_count', 0)}")
