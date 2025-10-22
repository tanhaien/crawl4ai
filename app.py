import streamlit as st
import asyncio
import json
import io
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

# Use LXML strategy for better compatibility with Streamlit Cloud
# Playwright requires system dependencies that aren't available on Streamlit Cloud

# Cấu hình trang
st.set_page_config(
    page_title="Crawl4AI Web App",
    page_icon="🕷️",
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
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🕷️ Crawl4AI Web App</h1>', unsafe_allow_html=True)
st.markdown("### Crawl và extract dữ liệu từ bất kỳ website nào")

# Info about LXML strategy
st.info("ℹ️ **Lưu ý**: App sử dụng LXML strategy để tương thích tốt với Streamlit Cloud. Một số website phức tạp có thể cần JavaScript rendering.")

# Sidebar cho cấu hình
with st.sidebar:
    st.header("⚙️ Cấu hình Crawl")
    
    # Chế độ crawl
    crawl_mode = st.selectbox(
        "Chế độ crawl:",
        ["Simple (1 trang)", "Deep Crawl (nhiều trang)"],
        help="Simple: chỉ crawl URL được nhập. Deep: crawl sâu với nhiều trang liên kết."
    )
    
    # Các tùy chọn cho deep crawl
    if crawl_mode == "Deep Crawl (nhiều trang)":
        max_depth = st.slider("Độ sâu tối đa:", 1, 5, 2)
        max_pages = st.slider("Số trang tối đa:", 1, 50, 10)
        include_external = st.checkbox("Bao gồm link ngoài", value=False)
        
        # Domain filter
        domain_filter = st.text_input(
            "Giới hạn domain (tùy chọn):",
            placeholder="example.com",
            help="Để trống để crawl tất cả domain"
        )
    else:
        max_depth = 1
        max_pages = 1
        include_external = False
        domain_filter = ""

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📝 Nhập URL")
    url_input = st.text_input(
        "URL cần crawl:",
        placeholder="https://example.com",
        help="Nhập URL đầy đủ bao gồm http:// hoặc https://"
    )

with col2:
    st.header("📊 Thống kê")
    if 'crawl_results' in st.session_state:
        st.metric("Số trang đã crawl", len(st.session_state.crawl_results))
        if st.session_state.crawl_results:
            total_chars = sum(len(result['markdown'] or "") for result in st.session_state.crawl_results)
            st.metric("Tổng ký tự", f"{total_chars:,}")

# Button crawl
if st.button("🚀 Bắt đầu Crawl", type="primary", use_container_width=True):
    if not url_input:
        st.error("Vui lòng nhập URL!")
    elif not url_input.startswith(('http://', 'https://')):
        st.error("URL phải bắt đầu bằng http:// hoặc https://")
    else:
        with st.spinner("Đang crawl dữ liệu..."):
            try:
                # Tạo progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Không cần cấu hình Crawl4AI nữa - sử dụng requests trực tiếp
                
                # Thực hiện crawl với requests và BeautifulSoup (không cần Playwright)
                def crawl_website():
                    try:
                        # Headers để tránh bị block
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept-Encoding': 'gzip, deflate',
                            'Connection': 'keep-alive',
                        }
                        
                        results = []
                        
                        if crawl_mode == "Simple (1 trang)":
                            # Simple crawl - chỉ 1 trang
                            result = crawl_single_page(url_input, headers)
                            if result:
                                results.append(result)
                        else:
                            # Deep crawl - nhiều trang
                            results = crawl_multiple_pages(
                                url_input, headers, max_depth, max_pages, 
                                include_external, domain_filter
                            )
                        
                        return results
                        
                    except Exception as e:
                        st.error(f"❌ Crawl error: {str(e)}")
                        return []
                
                def crawl_single_page(url, headers):
                    """Crawl một trang đơn lẻ"""
                    try:
                        response = requests.get(url, headers=headers, timeout=30)
                        response.raise_for_status()
                        
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extract metadata
                        title = soup.find('title')
                        title_text = title.get_text().strip() if title else ""
                        
                        description = soup.find('meta', attrs={'name': 'description'})
                        description_text = description.get('content', '') if description else ""
                        
                        keywords = soup.find('meta', attrs={'name': 'keywords'})
                        keywords_text = keywords.get('content', '') if keywords else ""
                        
                        author = soup.find('meta', attrs={'name': 'author'})
                        author_text = author.get('content', '') if author else ""
                        
                        # Convert to markdown-like format
                        markdown_content = convert_to_markdown(soup)
                        
                        return {
                            'url': url,
                            'title': title_text,
                            'description': description_text,
                            'keywords': keywords_text,
                            'author': author_text,
                            'markdown': markdown_content,
                            'html': str(soup),
                            'metadata': {
                                'title': title_text,
                                'description': description_text,
                                'keywords': keywords_text,
                                'author': author_text,
                                'depth': 0
                            }
                        }
                    except Exception as e:
                        st.error(f"❌ Error crawling {url}: {str(e)}")
                        return None
                
                def crawl_multiple_pages(start_url, headers, max_depth, max_pages, include_external, domain_filter):
                    """Crawl nhiều trang"""
                    results = []
                    visited = set()
                    to_visit = [(start_url, 0)]  # (url, depth)
                    
                    while to_visit and len(results) < max_pages:
                        current_url, depth = to_visit.pop(0)
                        
                        if current_url in visited or depth > max_depth:
                            continue
                            
                        visited.add(current_url)
                        
                        # Check domain filter
                        if domain_filter:
                            parsed_url = urlparse(current_url)
                            if domain_filter not in parsed_url.netloc:
                                continue
                        
                        result = crawl_single_page(current_url, headers)
                        if result:
                            results.append(result)
                            
                            # Find new links if not at max depth
                            if depth < max_depth:
                                try:
                                    response = requests.get(current_url, headers=headers, timeout=30)
                                    soup = BeautifulSoup(response.content, 'html.parser')
                                    
                                    for link in soup.find_all('a', href=True):
                                        href = link['href']
                                        full_url = urljoin(current_url, href)
                                        
                                        # Check if external links are allowed
                                        if not include_external:
                                            if urlparse(full_url).netloc != urlparse(start_url).netloc:
                                                continue
                                        
                                        if full_url not in visited and len(results) < max_pages:
                                            to_visit.append((full_url, depth + 1))
                                            
                                except Exception as e:
                                    st.warning(f"⚠️ Could not extract links from {current_url}: {str(e)}")
                    
                    return results
                
                def convert_to_markdown(soup):
                    """Convert HTML to markdown-like format"""
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Get text content
                    text = soup.get_text()
                    
                    # Clean up whitespace
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    return text
                
                # Chạy crawl function
                results = crawl_website()
                
                # Lưu kết quả vào session state
                st.session_state.crawl_results = results
                st.session_state.crawl_url = url_input
                st.session_state.crawl_time = datetime.now()
                
                progress_bar.progress(100)
                status_text.text("Hoàn thành!")
                
                st.success(f"✅ Crawl thành công! Đã crawl {len(results)} trang.")
                
            except Exception as e:
                st.error(f"❌ Lỗi khi crawl: {str(e)}")
                st.session_state.crawl_results = None

# Hiển thị kết quả
if 'crawl_results' in st.session_state and st.session_state.crawl_results:
    st.header("📋 Kết quả Crawl")
    
    # Tabs cho các định dạng khác nhau
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Preview", "📝 Markdown", "🔗 JSON", "🌐 HTML"])
    
    with tab1:
        st.subheader("Xem trước nội dung")
        for i, result in enumerate(st.session_state.crawl_results[:3]):  # Chỉ hiển thị 3 trang đầu
            with st.expander(f"Trang {i+1}: {result['url']}"):
                if result['markdown']:
                    st.markdown(result['markdown'][:1000] + "..." if len(result['markdown']) > 1000 else result['markdown'])
                else:
                    st.text("Không có nội dung markdown")
    
    with tab2:
        st.subheader("Nội dung Markdown")
        markdown_content = ""
        for result in st.session_state.crawl_results:
            markdown_content += f"# {result['url']}\n\n"
            markdown_content += result['markdown'] or "Không có nội dung"
            markdown_content += "\n\n---\n\n"
        
        st.text_area("Markdown Content", markdown_content, height=400)
        
        # Download button cho Markdown
        st.download_button(
            label="📥 Download Markdown",
            data=markdown_content,
            file_name=f"crawl_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    with tab3:
        st.subheader("Dữ liệu JSON")
        json_data = []
        for result in st.session_state.crawl_results:
            json_data.append({
                "url": result['url'],
                "title": result.get('title', ''),
                "description": result.get('description', ''),
                "keywords": result.get('keywords', ''),
                "author": result.get('author', ''),
                "markdown": result['markdown'],
                "html": result['html'],
                "metadata": result['metadata']
            })
        
        json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        st.json(json_data)
        
        # Download button cho JSON
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"crawl_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with tab4:
        st.subheader("Nội dung HTML")
        html_content = ""
        for result in st.session_state.crawl_results:
            html_content += f"<!-- {result['url']} -->\n"
            html_content += result['html'] or "Không có nội dung HTML"
            html_content += "\n\n"
        
        st.text_area("HTML Content", html_content, height=400)
        
        # Download button cho HTML
        st.download_button(
            label="📥 Download HTML",
            data=html_content,
            file_name=f"crawl_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html"
        )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🕷️ Powered by <a href='https://github.com/unclecode/crawl4ai' target='_blank'>Crawl4AI</a> | 
        Made with ❤️ using Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True
)
