import streamlit as st
import asyncio
import json
import io
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from url_analyzer import URLAnalyzer
from file_downloader import FileDownloader

# Cấu hình trang
st.set_page_config(
    page_title="Smart URL Scanner & Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .scan-result-card {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .file-item {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        border-bottom: 1px solid #eee;
    }
    .file-item:hover {
        background-color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🔍 Smart URL Scanner & Analyzer</h1>', unsafe_allow_html=True)
st.markdown("### Scan URL, phân tích resources và download files một cách thông minh")

# Initialize session state
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []
if 'download_results' not in st.session_state:
    st.session_state.download_results = None

# Sidebar cho cấu hình
with st.sidebar:
    st.header("⚙️ Cấu hình Scan")
    
    # Scan depth
    max_depth = st.slider("Độ sâu scan:", 1, 3, 2, help="Số cấp độ links để scan")
    
    # File type filters
    st.subheader("🔍 Lọc File Types")
    file_types = st.multiselect(
        "Chọn loại file muốn hiển thị:",
        ["pdf", "docx", "xlsx", "pptx", "images", "videos", "audio", "archives", "code", "data", "other"],
        default=["pdf", "docx", "xlsx", "pptx", "images", "videos", "audio", "archives"]
    )
    
    # Size filter
    st.subheader("📏 Lọc theo kích thước")
    min_size = st.number_input("Kích thước tối thiểu (KB):", min_value=0, value=0)
    max_size = st.number_input("Kích thước tối đa (KB):", min_value=0, value=10000)

# Main content - Step 1: URL Input & Scan
st.header("📝 Bước 1: Nhập URL và Scan")

col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input(
        "URL cần scan:",
        placeholder="https://example.com",
        help="Nhập URL đầy đủ bao gồm http:// hoặc https://",
        key="url_input"
    )

with col2:
    st.write("")  # Spacing
    st.write("")  # Spacing
    scan_button = st.button("🔍 Scan URL", type="primary", use_container_width=True)

# Scan URL
if scan_button:
    if not url_input:
        st.error("Vui lòng nhập URL!")
    elif not url_input.startswith(('http://', 'https://')):
        st.error("URL phải bắt đầu bằng http:// hoặc https://")
    else:
        with st.spinner("Đang scan URL..."):
            try:
                analyzer = URLAnalyzer()
                scan_results = analyzer.scan_url(url_input, max_depth)
                
                if scan_results['status'] == 'success':
                    st.session_state.scan_results = scan_results
                    st.session_state.selected_files = []  # Reset selection
                    st.success(f"✅ Scan thành công! Tìm thấy {len(scan_results['files'])} files và {scan_results['links']['total_count']} links.")
                else:
                    st.error(f"❌ Lỗi khi scan: {scan_results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Lỗi khi scan: {str(e)}")

# Step 2: Display Scan Results
if st.session_state.scan_results:
    st.header("📊 Bước 2: Kết quả Scan")
    
    scan_data = st.session_state.scan_results
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Files tìm thấy", len(scan_data['files']))
    with col2:
        st.metric("🔗 Links tìm thấy", scan_data['links']['total_count'])
    with col3:
        st.metric("🏠 Internal links", len(scan_data['links']['internal']))
    with col4:
        st.metric("🌐 External links", len(scan_data['links']['external']))
    
    # Metadata
    if scan_data['metadata']['title']:
        st.subheader("📋 Thông tin trang")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Tiêu đề:** {scan_data['metadata']['title']}")
            st.write(f"**Mô tả:** {scan_data['metadata']['description'][:200]}..." if scan_data['metadata']['description'] else "Không có mô tả")
        with col2:
            st.write(f"**Domain:** {scan_data['domain']}")
            st.write(f"**Tác giả:** {scan_data['metadata']['author']}" if scan_data['metadata']['author'] else "Không có thông tin tác giả")
    
    # Files section
    st.subheader("📁 Files được tìm thấy")
    
    # Filter files by type and size
    filtered_files = []
    for file_info in scan_data['files']:
        # Filter by file type
        if file_info['file_category'] not in file_types:
            continue
        
        # Filter by size (convert to KB for comparison)
        file_size_str = file_info.get('size', 'unknown')
        if file_size_str != 'unknown':
            try:
                # Parse size string (e.g., "1.5 MB" -> 1500 KB)
                size_value = float(file_size_str.split()[0])
                size_unit = file_size_str.split()[1] if len(file_size_str.split()) > 1 else 'KB'
                
                if size_unit == 'MB':
                    size_kb = size_value * 1024
                elif size_unit == 'GB':
                    size_kb = size_value * 1024 * 1024
                elif size_unit == 'B':
                    size_kb = size_value / 1024
                else:  # KB
                    size_kb = size_value
                
                if size_kb < min_size or size_kb > max_size:
                    continue
            except:
                pass  # Skip size filtering if can't parse
        
        filtered_files.append(file_info)
    
    if not filtered_files:
        st.warning("Không có files nào phù hợp với bộ lọc hiện tại.")
    else:
        st.write(f"Hiển thị {len(filtered_files)} files (tổng {len(scan_data['files'])} files)")
        
        # File selection
        st.subheader("✅ Chọn files để download")
        
        # Select all/none buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("Chọn tất cả"):
                st.session_state.selected_files = [f['url'] for f in filtered_files]
                st.rerun()
        with col2:
            if st.button("Bỏ chọn tất cả"):
                st.session_state.selected_files = []
                st.rerun()
        
        # File list with checkboxes
        for i, file_info in enumerate(filtered_files):
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            
            with col1:
                is_selected = file_info['url'] in st.session_state.selected_files
                if st.checkbox("", value=is_selected, key=f"file_{i}"):
                    if file_info['url'] not in st.session_state.selected_files:
                        st.session_state.selected_files.append(file_info['url'])
                else:
                    if file_info['url'] in st.session_state.selected_files:
                        st.session_state.selected_files.remove(file_info['url'])
            
            with col2:
                st.write(f"{file_info.get('icon', '📁')} **{file_info['filename']}**")
                st.write(f"🔗 {file_info['url'][:50]}...")
            
            with col3:
                st.write(f"📏 {file_info.get('size', 'unknown')}")
                st.write(f"🏷️ {file_info['file_category']}")
            
            with col4:
                st.write(f"📝 {file_info.get('mime_type', 'unknown')}")
                if file_info.get('element_text'):
                    st.write(f"💬 {file_info['element_text'][:30]}...")

# Step 3: Download Selected Files
if st.session_state.selected_files and st.session_state.scan_results:
    st.header("📥 Bước 3: Download Files")
    
    st.write(f"Đã chọn {len(st.session_state.selected_files)} files để download")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        download_button = st.button("📥 Download Selected Files", type="primary", use_container_width=True)
    
    with col2:
        download_zip_button = st.button("📦 Download as ZIP", use_container_width=True)
    
    if download_button or download_zip_button:
        with st.spinner("Đang download files..."):
            try:
                downloader = FileDownloader()
                
                # Prepare file list for download
                file_list = []
                for url in st.session_state.selected_files:
                    # Find file info from scan results
                    file_info = None
                    for f in st.session_state.scan_results['files']:
                        if f['url'] == url:
                            file_info = f
                            break
                    
                    if file_info:
                        file_list.append({
                            'url': url,
                            'filename': file_info['filename'],
                            'file_category': file_info['file_category']
                        })
                
                # Download files
                def progress_callback(progress, message):
                    st.write(f"Progress: {progress:.1%} - {message}")
                
                download_results = downloader.download_multiple_files(file_list, progress_callback)
                st.session_state.download_results = download_results
                
                # Show results
                successful_downloads = [r for r in download_results if r['success']]
                failed_downloads = [r for r in download_results if not r['success']]
                
                st.success(f"✅ Download hoàn thành! {len(successful_downloads)} files thành công, {len(failed_downloads)} files thất bại.")
                
                # Show failed downloads
                if failed_downloads:
                    st.error("❌ Files download thất bại:")
                    for failed in failed_downloads:
                        st.write(f"- {failed['filename']}: {failed['error']}")
                
                # Individual download buttons
                if successful_downloads:
                    st.subheader("📥 Download từng file")
                    for result in successful_downloads:
                        st.download_button(
                            label=f"📥 {result['filename']}",
                            data=result['content'],
                            file_name=result['filename'],
                            mime=result['mime_type']
                        )
                
                # ZIP download
                if download_zip_button and successful_downloads:
                    zip_data = downloader.create_zip_archive(successful_downloads)
                    st.download_button(
                        label="📦 Download All as ZIP",
                        data=zip_data,
                        file_name=f"downloaded_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                
            except Exception as e:
                st.error(f"❌ Lỗi khi download: {str(e)}")

# Additional tabs for detailed analysis
if st.session_state.scan_results:
    st.header("🔍 Phân tích chi tiết")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Thống kê", "🔗 Links", "📄 Content Analysis", "📋 Raw Data"])
    
    with tab1:
        st.subheader("📊 Thống kê tổng quan")
        
        # Content statistics
        content_stats = st.session_state.scan_results['content_analysis']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Cấu trúc nội dung:**")
            st.write(f"- Tiêu đề H1: {content_stats['headings']['h1']}")
            st.write(f"- Tiêu đề H2: {content_stats['headings']['h2']}")
            st.write(f"- Tiêu đề H3: {content_stats['headings']['h3']}")
            st.write(f"- Đoạn văn: {content_stats['paragraphs']}")
            st.write(f"- Hình ảnh: {content_stats['images']}")
        
        with col2:
            st.write("**Các elements khác:**")
            st.write(f"- Bảng: {content_stats['tables']}")
            st.write(f"- Danh sách: {content_stats['lists']}")
            st.write(f"- Form: {content_stats['forms']}")
            st.write(f"- Navigation: {content_stats['navigation_elements']}")
            st.write(f"- Main content: {content_stats['main_content_areas']}")
        
        st.write(f"**Tổng độ dài text:** {content_stats['text_length']:,} ký tự")
    
    with tab2:
        st.subheader("🔗 Phân tích Links")
        
        links_data = st.session_state.scan_results['links']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Internal Links:**")
            for link in links_data['internal'][:10]:  # Show first 10
                st.write(f"- {link['text']} → {link['url']}")
            
            if len(links_data['internal']) > 10:
                st.write(f"... và {len(links_data['internal']) - 10} links khác")
        
        with col2:
            st.write("**External Links:**")
            for link in links_data['external'][:10]:  # Show first 10
                st.write(f"- {link['text']} → {link['url']}")
            
            if len(links_data['external']) > 10:
                st.write(f"... và {len(links_data['external']) - 10} links khác")
    
    with tab3:
        st.subheader("📄 Phân tích nội dung")
        
        # Show content structure
        content_stats = st.session_state.scan_results['content_analysis']
        
        # Create a simple visualization
        import pandas as pd
        
        headings_data = []
        for level, count in content_stats['headings'].items():
            if count > 0:
                headings_data.append({
                    'Level': level.upper(),
                    'Count': count
                })
        
        if headings_data:
            df_headings = pd.DataFrame(headings_data)
            st.bar_chart(df_headings.set_index('Level'))
        
        # Other elements
        other_elements = {
            'Paragraphs': content_stats['paragraphs'],
            'Images': content_stats['images'],
            'Tables': content_stats['tables'],
            'Lists': content_stats['lists'],
            'Forms': content_stats['forms']
        }
        
        df_other = pd.DataFrame(list(other_elements.items()), columns=['Element', 'Count'])
        st.bar_chart(df_other.set_index('Element'))
    
    with tab4:
        st.subheader("📋 Dữ liệu thô")
        st.json(st.session_state.scan_results)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🔍 Smart URL Scanner & Analyzer | 
        Made with ❤️ using Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)