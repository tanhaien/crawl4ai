"""
File Downloader Module - Xử lý download nhiều file types
"""

import requests
import os
import zipfile
import io
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import mimetypes
from datetime import datetime


class FileDownloader:
    """Class để download và quản lý files"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # File type icons mapping
        self.file_icons = {
            'pdf': '📄',
            'docx': '📝',
            'xlsx': '📊',
            'pptx': '📈',
            'images': '🖼️',
            'videos': '🎥',
            'audio': '🎵',
            'archives': '📦',
            'code': '💻',
            'data': '📋',
            'other': '📁'
        }
    
    def download_file(self, url: str, filename: Optional[str] = None) -> Dict:
        """
        Download một file từ URL
        
        Args:
            url: URL của file
            filename: Tên file tùy chỉnh (optional)
            
        Returns:
            Dict chứa kết quả download
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Lấy filename nếu không được cung cấp
            if not filename:
                filename = self._get_filename_from_url(url, response)
            
            # Lấy content
            content = response.content
            
            return {
                'success': True,
                'url': url,
                'filename': filename,
                'content': content,
                'size': len(content),
                'mime_type': response.headers.get('content-type', 'unknown'),
                'status_code': response.status_code
            }
            
        except Exception as e:
            return {
                'success': False,
                'url': url,
                'filename': filename or 'unknown',
                'error': str(e),
                'size': 0
            }
    
    def download_multiple_files(self, file_list: List[Dict], progress_callback=None) -> List[Dict]:
        """
        Download nhiều files
        
        Args:
            file_list: List các file info dicts
            progress_callback: Callback function để update progress
            
        Returns:
            List các kết quả download
        """
        results = []
        total_files = len(file_list)
        
        for i, file_info in enumerate(file_list):
            url = file_info['url']
            filename = file_info.get('filename', '')
            
            # Download file
            result = self.download_file(url, filename)
            results.append(result)
            
            # Update progress
            if progress_callback:
                progress = (i + 1) / total_files
                progress_callback(progress, f"Downloading {filename}")
        
        return results
    
    def create_zip_archive(self, downloaded_files: List[Dict], zip_filename: str = None) -> bytes:
        """
        Tạo ZIP archive từ các files đã download
        
        Args:
            downloaded_files: List các file đã download thành công
            zip_filename: Tên file ZIP
            
        Returns:
            Bytes của ZIP file
        """
        if not zip_filename:
            zip_filename = f"downloaded_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in downloaded_files:
                if file_info['success']:
                    # Tạo folder structure dựa trên file category
                    category = file_info.get('category', 'other')
                    filename = file_info['filename']
                    
                    # Tạo path trong ZIP
                    zip_path = f"{category}/{filename}"
                    
                    # Add file vào ZIP
                    zip_file.writestr(zip_path, file_info['content'])
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def organize_files_by_category(self, files: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Tổ chức files theo category
        
        Args:
            files: List các file info
            
        Returns:
            Dict với key là category và value là list files
        """
        organized = {}
        
        for file_info in files:
            category = file_info.get('file_category', 'other')
            if category not in organized:
                organized[category] = []
            organized[category].append(file_info)
        
        return organized
    
    def get_file_info(self, url: str) -> Dict:
        """
        Lấy thông tin file từ URL (không download)
        
        Args:
            url: URL của file
            
        Returns:
            Dict chứa thông tin file
        """
        try:
            # HEAD request để lấy metadata
            response = requests.head(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse URL
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1] or 'unknown'
            
            # Lấy file size
            content_length = response.headers.get('content-length')
            size = self._format_size(int(content_length)) if content_length else 'unknown'
            
            # Lấy MIME type
            mime_type = response.headers.get('content-type', 'unknown')
            
            # Determine file category
            category = self._get_file_category(filename, mime_type)
            
            return {
                'url': url,
                'filename': filename,
                'size': size,
                'mime_type': mime_type,
                'file_category': category,
                'icon': self.file_icons.get(category, '📁'),
                'last_modified': response.headers.get('last-modified', 'unknown'),
                'accessible': True
            }
            
        except Exception as e:
            return {
                'url': url,
                'filename': 'unknown',
                'size': 'unknown',
                'mime_type': 'unknown',
                'file_category': 'other',
                'icon': '❌',
                'last_modified': 'unknown',
                'accessible': False,
                'error': str(e)
            }
    
    def _get_filename_from_url(self, url: str, response: requests.Response) -> str:
        """Lấy filename từ URL hoặc response headers"""
        # Try từ Content-Disposition header
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
            return filename
        
        # Try từ URL
        parsed_url = urlparse(url)
        filename = parsed_url.path.split('/')[-1]
        
        if filename and '.' in filename:
            return filename
        
        # Fallback
        return f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _get_file_category(self, filename: str, mime_type: str) -> str:
        """Xác định file category từ filename và MIME type"""
        filename_lower = filename.lower()
        
        # Check by extension
        if any(filename_lower.endswith(ext) for ext in ['.pdf']):
            return 'pdf'
        elif any(filename_lower.endswith(ext) for ext in ['.docx', '.doc']):
            return 'docx'
        elif any(filename_lower.endswith(ext) for ext in ['.xlsx', '.xls']):
            return 'xlsx'
        elif any(filename_lower.endswith(ext) for ext in ['.pptx', '.ppt']):
            return 'pptx'
        elif any(filename_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']):
            return 'images'
        elif any(filename_lower.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']):
            return 'videos'
        elif any(filename_lower.endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']):
            return 'audio'
        elif any(filename_lower.endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz']):
            return 'archives'
        elif any(filename_lower.endswith(ext) for ext in ['.js', '.css', '.html', '.htm', '.php', '.py']):
            return 'code'
        elif any(filename_lower.endswith(ext) for ext in ['.json', '.xml', '.csv', '.txt', '.rtf']):
            return 'data'
        
        # Check by MIME type
        if mime_type.startswith('image/'):
            return 'images'
        elif mime_type.startswith('video/'):
            return 'videos'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type == 'application/pdf':
            return 'pdf'
        elif 'word' in mime_type:
            return 'docx'
        elif 'excel' in mime_type or 'spreadsheet' in mime_type:
            return 'xlsx'
        elif 'powerpoint' in mime_type or 'presentation' in mime_type:
            return 'pptx'
        elif 'zip' in mime_type or 'rar' in mime_type:
            return 'archives'
        
        return 'other'
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size thành readable string"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def get_download_statistics(self, files: List[Dict]) -> Dict:
        """
        Tính toán thống kê download
        
        Args:
            files: List các file info
            
        Returns:
            Dict chứa thống kê
        """
        stats = {
            'total_files': len(files),
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_size': 0,
            'by_category': {},
            'largest_file': None,
            'smallest_file': None
        }
        
        successful_files = []
        
        for file_info in files:
            if file_info.get('success', False):
                stats['successful_downloads'] += 1
                size = file_info.get('size', 0)
                stats['total_size'] += size
                successful_files.append(file_info)
                
                # Category stats
                category = file_info.get('file_category', 'other')
                if category not in stats['by_category']:
                    stats['by_category'][category] = {'count': 0, 'size': 0}
                stats['by_category'][category]['count'] += 1
                stats['by_category'][category]['size'] += size
                
                # Largest/smallest file
                if not stats['largest_file'] or size > stats['largest_file']['size']:
                    stats['largest_file'] = file_info
                if not stats['smallest_file'] or size < stats['smallest_file']['size']:
                    stats['smallest_file'] = file_info
            else:
                stats['failed_downloads'] += 1
        
        # Format total size
        stats['total_size_formatted'] = self._format_size(stats['total_size'])
        
        return stats


def download_files(file_list: List[Dict], progress_callback=None) -> List[Dict]:
    """
    Convenience function để download files
    
    Args:
        file_list: List các file info
        progress_callback: Progress callback function
        
    Returns:
        List các kết quả download
    """
    downloader = FileDownloader()
    return downloader.download_multiple_files(file_list, progress_callback)


if __name__ == "__main__":
    # Test function
    test_files = [
        {'url': 'https://example.com/file1.pdf', 'filename': 'test1.pdf'},
        {'url': 'https://example.com/file2.docx', 'filename': 'test2.docx'}
    ]
    
    def progress_callback(progress, message):
        print(f"Progress: {progress:.1%} - {message}")
    
    results = download_files(test_files, progress_callback)
    print(f"Downloaded {len(results)} files")
