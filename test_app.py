#!/usr/bin/env python3
"""
Test script cho Smart URL Scanner
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from url_analyzer import URLAnalyzer
from file_downloader import FileDownloader

def test_url_analyzer():
    """Test URL Analyzer"""
    print("🔍 Testing URL Analyzer...")
    
    analyzer = URLAnalyzer()
    
    # Test với một URL đơn giản
    test_url = "https://httpbin.org/html"
    
    try:
        result = analyzer.scan_url(test_url, max_depth=1)
        
        if result['status'] == 'success':
            print(f"✅ Scan thành công!")
            print(f"   - Files tìm thấy: {len(result['files'])}")
            print(f"   - Links tìm thấy: {result['links']['total_count']}")
            print(f"   - Title: {result['metadata']['title']}")
            return True
        else:
            print(f"❌ Scan thất bại: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi test URL Analyzer: {str(e)}")
        return False

def test_file_downloader():
    """Test File Downloader"""
    print("\n📥 Testing File Downloader...")
    
    downloader = FileDownloader()
    
    # Test với một file nhỏ
    test_url = "https://httpbin.org/robots.txt"
    
    try:
        result = downloader.download_file(test_url, "test_robots.txt")
        
        if result['success']:
            print(f"✅ Download thành công!")
            print(f"   - Filename: {result['filename']}")
            print(f"   - Size: {result['size']} bytes")
            print(f"   - MIME type: {result['mime_type']}")
            return True
        else:
            print(f"❌ Download thất bại: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi test File Downloader: {str(e)}")
        return False

def test_file_info():
    """Test file info detection"""
    print("\n📋 Testing File Info Detection...")
    
    downloader = FileDownloader()
    
    # Test với các URLs khác nhau
    test_urls = [
        "https://httpbin.org/robots.txt",
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    ]
    
    success_count = 0
    
    for url in test_urls:
        try:
            info = downloader.get_file_info(url)
            if info['accessible']:
                print(f"✅ {info['filename']} - {info['size']} - {info['file_category']}")
                success_count += 1
            else:
                print(f"❌ {url} - {info.get('error', 'Not accessible')}")
        except Exception as e:
            print(f"❌ Lỗi với {url}: {str(e)}")
    
    return success_count > 0

def main():
    """Main test function"""
    print("🚀 Bắt đầu test Smart URL Scanner...")
    
    tests = [
        ("URL Analyzer", test_url_analyzer),
        ("File Downloader", test_file_downloader),
        ("File Info Detection", test_file_info)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Testing {test_name}")
        print('='*50)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print(f"\n{'='*50}")
    print(f"KẾT QUẢ TEST: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 Tất cả tests đều PASSED! App sẵn sàng để deploy.")
        return True
    else:
        print("⚠️ Một số tests FAILED. Cần kiểm tra lại.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
