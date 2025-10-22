import streamlit as st
import asyncio
import json
import io
import subprocess
import sys
from datetime import datetime
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    DomainFilter,
    URLPatternFilter,
    ContentTypeFilter
)

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
            total_chars = sum(len(result.markdown or "") for result in st.session_state.crawl_results)
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
                
                # Cấu hình crawler
                if crawl_mode == "Deep Crawl (nhiều trang)":
                    # Tạo filter chain cho deep crawl
                    filters = []
                    if domain_filter:
                        filters.append(DomainFilter(allowed_domains=[domain_filter]))
                    filters.extend([
                        URLPatternFilter(patterns=["*"]),
                        ContentTypeFilter(allowed_types=["text/html"])
                    ])
                    
                    config = CrawlerRunConfig(
                        deep_crawl_strategy=BFSDeepCrawlStrategy(
                            max_depth=max_depth,
                            include_external=include_external,
                            max_pages=max_pages,
                            filter_chain=FilterChain(filters) if filters else None
                        ),
                        scraping_strategy=LXMLWebScrapingStrategy(),
                        verbose=False
                    )
                else:
                    # Simple crawl
                    config = CrawlerRunConfig(
                        scraping_strategy=LXMLWebScrapingStrategy(),
                        verbose=False
                    )
                
                # Thực hiện crawl với error handling và LXML strategy
                async def crawl_website():
                    try:
                        # Force LXML strategy for Streamlit Cloud compatibility
                        lxml_config = CrawlerRunConfig(
                            scraping_strategy=LXMLWebScrapingStrategy(),
                            verbose=False
                        )
                        
                        # Add deep crawl strategy if needed
                        if crawl_mode == "Deep Crawl (nhiều trang)":
                            filters = []
                            if domain_filter:
                                filters.append(DomainFilter(allowed_domains=[domain_filter]))
                            filters.extend([
                                URLPatternFilter(patterns=["*"]),
                                ContentTypeFilter(allowed_types=["text/html"])
                            ])
                            
                            lxml_config = CrawlerRunConfig(
                                deep_crawl_strategy=BFSDeepCrawlStrategy(
                                    max_depth=max_depth,
                                    include_external=include_external,
                                    max_pages=max_pages,
                                    filter_chain=FilterChain(filters) if filters else None
                                ),
                                scraping_strategy=LXMLWebScrapingStrategy(),
                                verbose=False
                            )
                        
                        async with AsyncWebCrawler() as crawler:
                            results = await crawler.arun(url_input, config=lxml_config)
                            return results
                            
                    except Exception as e:
                        st.error(f"❌ Crawl error: {str(e)}")
                        # Try with even simpler config
                        st.info("🔄 Trying with basic LXML crawl...")
                        try:
                            basic_config = CrawlerRunConfig(
                                scraping_strategy=LXMLWebScrapingStrategy(),
                                verbose=False
                            )
                            async with AsyncWebCrawler() as crawler:
                                results = await crawler.arun(url_input, config=basic_config)
                                return results
                        except Exception as fallback_error:
                            st.error(f"❌ Fallback also failed: {str(fallback_error)}")
                            raise fallback_error
                
                # Chạy async function
                results = asyncio.run(crawl_website())
                
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
            with st.expander(f"Trang {i+1}: {result.url}"):
                if result.markdown:
                    st.markdown(result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown)
                else:
                    st.text("Không có nội dung markdown")
    
    with tab2:
        st.subheader("Nội dung Markdown")
        markdown_content = ""
        for result in st.session_state.crawl_results:
            markdown_content += f"# {result.url}\n\n"
            markdown_content += result.markdown or "Không có nội dung"
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
                "url": result.url,
                "title": result.metadata.get('title', ''),
                "description": result.metadata.get('description', ''),
                "keywords": result.metadata.get('keywords', ''),
                "author": result.metadata.get('author', ''),
                "markdown": result.markdown,
                "html": result.html,
                "metadata": result.metadata
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
            html_content += f"<!-- {result.url} -->\n"
            html_content += result.html or "Không có nội dung HTML"
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
