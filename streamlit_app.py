import streamlit as st
import asyncio
from pathlib import Path
from datetime import datetime
import zipfile
import json
import shutil
from pdf_crawler import PDFCrawler, CONFIG

st.set_page_config(
    page_title="PDF Crawler",
    page_icon="📄",
    layout="wide"
)

def zip_directory(source_dir: Path, output_path: Path):
    """Zip a directory and return the zip file path"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in source_dir.rglob('*'):
            if file.is_file():
                zipf.write(file, file.relative_to(source_dir))
    return output_path

def main():
    st.title("📄 PDF Crawler")
    st.markdown("**Nhập URL và crawl tất cả file PDF từ website**")
    
    # URL input
    st.subheader("Nhập URLs")
    urls_input = st.text_area(
        "Nhập một hoặc nhiều URL (mỗi dòng một URL)",
        height=150,
        placeholder="https://example.com/documents\nhttps://another-site.com/papers"
    )
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    with col1:
        max_pages = st.number_input(
            "Số trang tối đa mỗi site",
            min_value=1,
            max_value=200,
            value=50,
            help="Giới hạn số trang web sẽ crawl từ mỗi site"
        )
    
    with col2:
        max_concurrent = st.number_input(
            "Số download đồng thời",
            min_value=1,
            max_value=20,
            value=5,
            help="Số file PDF có thể download cùng lúc"
        )
    
    with col3:
        timeout = st.number_input(
            "Timeout (giây)",
            min_value=10,
            max_value=180,
            value=60,
            help="Thời gian chờ tối đa cho mỗi request"
        )
    
    # Start button
    if st.button("🚀 Bắt đầu Crawl", type="primary", use_container_width=True):
        # Parse URLs
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        
        if not urls:
            st.warning("⚠️ Vui lòng nhập ít nhất một URL")
            return
        
        # Update config
        CONFIG["max_pages_per_site"] = max_pages
        CONFIG["max_concurrent_downloads"] = max_concurrent
        CONFIG["timeout"] = timeout
        
        # Create unique output directory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = Path(f"runs/run_{timestamp}")
        output_dir = run_dir / "downloaded_pdfs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update CONFIG paths
        CONFIG["output_dir"] = str(output_dir)
        CONFIG["log_file"] = str(run_dir / "pdf_crawler.log")
        CONFIG["metadata_file"] = str(run_dir / "pdf_downloads_metadata.json")
        CONFIG["progress_file"] = str(run_dir / "pdf_crawler_progress.json")
        
        # Progress indicators
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔄 Đang khởi tạo crawler...")
            crawler = PDFCrawler()
            
            status_text.text(f"🔍 Đang crawl {len(urls)} site(s)...")
            
            # Run the crawler
            async def run_crawler():
                await crawler.run(urls)
            
            asyncio.run(run_crawler())
            
            progress_bar.progress(100)
            status_text.text("✅ Hoàn thành!")
            
            # Display results
            st.success("🎉 Crawl hoàn tất!")
            
            # Summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Sites đã xử lý", crawler.metadata['sites_processed'])
            with col2:
                st.metric("PDFs tìm thấy", crawler.metadata['pdfs_found'])
            with col3:
                st.metric("PDFs tải về", crawler.metadata['pdfs_downloaded'])
            with col4:
                st.metric("Tổng dung lượng", f"{crawler.metadata['total_size_mb']:.2f} MB")
            
            # Failed downloads
            if crawler.failed_downloads:
                with st.expander(f"⚠️ {len(crawler.failed_downloads)} download thất bại"):
                    for fail in crawler.failed_downloads[:10]:  # Show first 10
                        st.text(f"• {fail['url']}\n  Lỗi: {fail['error']}")
            
            # Metadata display
            with st.expander("📊 Xem metadata chi tiết"):
                metadata_file = Path(CONFIG["metadata_file"])
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    st.json(metadata)
            
            # Download section
            if crawler.metadata['pdfs_downloaded'] > 0:
                st.subheader("📥 Tải xuống kết quả")
                
                # Create zip file
                zip_path = run_dir / "pdfs.zip"
                status_text.text("📦 Đang đóng gói files...")
                zip_directory(output_dir, zip_path)
                
                # Download button for zip
                with open(zip_path, 'rb') as f:
                    st.download_button(
                        label=f"⬇️ Tải tất cả ({crawler.metadata['pdfs_downloaded']} PDFs)",
                        data=f,
                        file_name=f"pdfs_{timestamp}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                
                # Show list of downloaded files
                with st.expander("📑 Danh sách file đã tải"):
                    pdf_files = list(output_dir.rglob("*.pdf"))
                    for i, pdf_file in enumerate(pdf_files[:50], 1):  # Show first 50
                        st.text(f"{i}. {pdf_file.relative_to(output_dir)}")
                    if len(pdf_files) > 50:
                        st.text(f"... và {len(pdf_files) - 50} file khác")
            else:
                st.warning("⚠️ Không tìm thấy PDF nào để tải xuống")
            
            # Log viewer
            with st.expander("📝 Xem log"):
                log_file = Path(CONFIG["log_file"])
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                    st.text_area("Log output", log_content, height=300)
                    
        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ Lỗi: {str(e)}")
            
            # Show log on error
            log_file = Path(CONFIG["log_file"])
            if log_file.exists():
                with st.expander("📝 Chi tiết lỗi (log)"):
                    with open(log_file, 'r') as f:
                        st.text(f.read())
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Lưu ý:**
    - Crawler sẽ tìm và tải tất cả file PDF từ các URL được cung cấp
    - Kết quả lưu tạm thời trên Streamlit Cloud, vui lòng tải về ngay sau khi crawl xong
    - Thời gian crawl phụ thuộc vào số lượng trang và PDF trên website
    """)

if __name__ == "__main__":
    main()
