import streamlit as st
import asyncio
from pathlib import Path
from datetime import datetime
import zipfile
import json
import shutil
from urllib.parse import urlparse
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
    
    # Initialize session state for crawl results
    if 'crawl_results' not in st.session_state:
        st.session_state.crawl_results = None
    if 'discovered_pdfs' not in st.session_state:
        st.session_state.discovered_pdfs = []
    if 'scan_complete' not in st.session_state:
        st.session_state.scan_complete = False
    if 'crawler_instance' not in st.session_state:
        st.session_state.crawler_instance = None
    
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
    
    # Phase 1: Discovery Button
    if not st.session_state.scan_complete:
        if st.button("🔍 Scan for PDFs (Discovery Phase)", type="primary", use_container_width=True):
            # Parse URLs
            urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
            
            if not urls:
                st.warning("⚠️ Vui lòng nhập ít nhất một URL")
                return
            
            # Validate URLs
            invalid_urls = []
            valid_urls = []
            for url in urls:
                try:
                    parsed = urlparse(url)
                    if parsed.scheme in ('http', 'https') and parsed.netloc:
                        valid_urls.append(url)
                    else:
                        invalid_urls.append(url)
                except Exception:
                    invalid_urls.append(url)
            
            if invalid_urls:
                st.error(f"❌ URL không hợp lệ: {', '.join(invalid_urls)}")
                st.info("ℹ️ URL phải bắt đầu bằng http:// hoặc https://")
                return
            
            urls = valid_urls
            
            # Update config
            CONFIG["max_pages_per_site"] = max_pages
            CONFIG["max_concurrent_downloads"] = max_concurrent
            CONFIG["timeout"] = timeout
            
            # Create unique output directory for this run in /tmp for Streamlit Cloud
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = Path(f"/tmp/runs/run_{timestamp}")
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
                
                status_text.text(f"🔍 Đang quét {len(urls)} site(s) để tìm PDF...")
                
                # Run the crawler in discover mode
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(crawler.run(urls, mode='discover'))
                
                progress_bar.progress(100)
                status_text.text("✅ Quét hoàn thành!")
                
                # Store discovered PDFs in session state
                st.session_state.discovered_pdfs = crawler.discovered_pdfs
                st.session_state.scan_complete = True
                st.session_state.crawler_instance = crawler
                st.session_state.run_dir = run_dir
                st.session_state.output_dir = output_dir
                st.session_state.timestamp = timestamp
                
                # Trigger display by rerunning
                st.rerun()
                        
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
    
    # Phase 2: Display discovered PDFs and Download Selected
    if st.session_state.scan_complete and st.session_state.discovered_pdfs:
        st.success(f"✅ Đã tìm thấy {len(st.session_state.discovered_pdfs)} file PDF!")
        
        st.markdown("---")
        st.subheader("📋 Chọn PDFs để tải xuống")
        
        # Display table header
        col1, col2, col3, col4 = st.columns([0.5, 3, 2, 2])
        with col1:
            st.markdown("**Chọn**")
        with col2:
            st.markdown("**Tên file**")
        with col3:
            st.markdown("**Domain**")
        with col4:
            st.markdown("**URL**")
        
        st.markdown("---")
        
        # Display PDFs with checkboxes
        selected_pdfs = []
        for idx, pdf in enumerate(st.session_state.discovered_pdfs):
            col1, col2, col3, col4 = st.columns([0.5, 3, 2, 2])
            with col1:
                selected = st.checkbox("", key=f"pdf_{idx}", label_visibility="hidden")
            with col2:
                st.write(pdf['filename'])
            with col3:
                st.write(pdf['domain'])
            with col4:
                url_display = pdf['url'][:40] + "..." if len(pdf['url']) > 40 else pdf['url']
                st.write(url_display)
            
            if selected:
                selected_pdfs.append(pdf)
        
        st.markdown("---")
        
        # Summary of selection
        if selected_pdfs:
            st.info(f"ℹ️ Đã chọn {len(selected_pdfs)} / {len(st.session_state.discovered_pdfs)} file PDF")
        else:
            st.warning("⚠️ Chưa chọn file nào")
        
        # Download selected PDFs button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Download Selected PDFs", type="primary", use_container_width=True, disabled=len(selected_pdfs)==0):
                # Progress indicators
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text(f"🔄 Đang tải {len(selected_pdfs)} file PDF...")
                    
                    crawler = st.session_state.crawler_instance
                    
                    # Run download for selected PDFs
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    result = loop.run_until_complete(crawler.download_selected_pdfs(selected_pdfs))
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Tải xuống hoàn thành!")
                    
                    # Load URL mapping from metadata
                    url_mapping = {}
                    metadata_file = Path(CONFIG["metadata_file"])
                    metadata = {}
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            url_mapping = metadata.get("downloaded_pdfs", {})
                    
                    # Save all results to session state
                    st.session_state.crawl_results = {
                        'metadata': crawler.metadata,
                        'failed_downloads': crawler.failed_downloads,
                        'run_dir': st.session_state.run_dir,
                        'output_dir': st.session_state.output_dir,
                        'timestamp': st.session_state.timestamp,
                        'url_mapping': url_mapping,
                        'metadata_file': CONFIG["metadata_file"],
                        'log_file': CONFIG["log_file"],
                        'full_metadata': metadata
                    }
                    
                    # Reset discovery state
                    st.session_state.scan_complete = False
                    st.session_state.discovered_pdfs = []
                    
                    # Trigger display by rerunning
                    st.rerun()
                            
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
        
        with col2:
            if st.button("🔄 Quét lại", use_container_width=True):
                st.session_state.scan_complete = False
                st.session_state.discovered_pdfs = []
                st.session_state.crawler_instance = None
                st.rerun()
    
    # Display results if crawl has been performed
    if st.session_state.crawl_results is not None:
        results = st.session_state.crawl_results
        
        # Display results
        st.success("🎉 Crawl hoàn tất!")
        
        # Summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sites đã xử lý", results['metadata']['sites_processed'])
        with col2:
            st.metric("PDFs tìm thấy", results['metadata']['pdfs_found'])
        with col3:
            st.metric("PDFs tải về", results['metadata']['pdfs_downloaded'])
        with col4:
            st.metric("Tổng dung lượng", f"{results['metadata']['total_size_mb']:.2f} MB")
        
        # Failed downloads
        if results['failed_downloads']:
            with st.expander(f"⚠️ {len(results['failed_downloads'])} download thất bại"):
                for fail in results['failed_downloads'][:10]:  # Show first 10
                    st.text(f"• {fail['url']}\n  Lỗi: {fail['error']}")
        
        # Metadata display
        with st.expander("📊 Xem metadata chi tiết"):
            st.json(results['full_metadata'])
        
        # Download section
        if results['metadata']['pdfs_downloaded'] > 0:
            st.subheader("📥 Tải xuống kết quả")

            # File search input
            search_terms = st.text_input(
                "🔍 Tìm kiếm file theo tên và URL (phân cách bằng dấu phẩy)",
                placeholder="Ví dụ: catalog, manual, guide...",
                help="Tìm kiếm trong cả tên file và URL gốc. Ví dụ: 'catalog' sẽ tìm cả file có tên catalog và file có URL chứa catalog"
            )

            # Get all PDF files
            pdf_files = list(results['output_dir'].rglob("*.pdf"))
            pdf_files.sort()

            # Parse search terms
            search_keywords = [term.strip().lower() for term in search_terms.split(',') if term.strip()] if search_terms else []

            # Separate priority files and other files
            priority_files = []
            other_files = []

            if search_keywords:
                for pdf_file in pdf_files:
                    file_name_lower = pdf_file.name.lower()

                    # Get original URL for this file
                    original_url = ""
                    for url, filepath in results['url_mapping'].items():
                        if Path(filepath).name == pdf_file.name:
                            original_url = url.lower()
                            break

                    # Search in both filename and original URL
                    name_match = any(keyword in file_name_lower for keyword in search_keywords)
                    url_match = any(keyword in original_url for keyword in search_keywords) if original_url else False

                    if name_match or url_match:
                        priority_files.append(pdf_file)
                    else:
                        other_files.append(pdf_file)
            else:
                other_files = pdf_files

            # Multi-select for PDF files
            st.subheader("📑 Chọn file PDF để tải xuống")

            selected_files = []

            # Priority files section
            if priority_files:
                st.markdown("### ⭐ File Ưu Tiên (khớp tìm kiếm)")
                for pdf_file in priority_files:
                    # Get original URL for this file
                    original_url = ""
                    for url, filepath in results['url_mapping'].items():
                        if Path(filepath).name == pdf_file.name:
                            original_url = url
                            break

                    col1, col2 = st.columns([0.05, 0.95])
                    with col1:
                        if st.checkbox("Select file", key=f"priority_{pdf_file}", label_visibility="hidden"):
                            selected_files.append(pdf_file)
                    with col2:
                        st.text(f"🎯 {pdf_file.relative_to(results['output_dir'])}")
                        if original_url:
                            st.caption(f"🔗 {original_url[:80]}{'...' if len(original_url) > 80 else ''}")

            # Other files section
            if other_files:
                if priority_files:
                    st.markdown("### 📁 Các File Khác")
                else:
                    st.markdown("### 📁 Tất Cả Các File")

                # Show files in batches to avoid UI issues
                batch_size = 20
                for i in range(0, len(other_files), batch_size):
                    batch = other_files[i:i+batch_size]
                    for pdf_file in batch:
                        # Get original URL for this file
                        original_url = ""
                        for url, filepath in results['url_mapping'].items():
                            if Path(filepath).name == pdf_file.name:
                                original_url = url
                                break

                        col1, col2 = st.columns([0.05, 0.95])
                        with col1:
                            if st.checkbox("Select file", key=f"other_{pdf_file}_{i}", label_visibility="hidden"):
                                selected_files.append(pdf_file)
                        with col2:
                            st.text(f"📄 {pdf_file.relative_to(results['output_dir'])}")
                            if original_url:
                                st.caption(f"🔗 {original_url[:80]}{'...' if len(original_url) > 80 else ''}")

            # Summary of selected files
            if selected_files:
                st.success(f"✅ Đã chọn {len(selected_files)} file")
            else:
                st.info("ℹ️ Chưa chọn file nào")

            # Initialize session state for download preparation
            if 'prepare_download' not in st.session_state:
                st.session_state.prepare_download = False

            # Button to prepare downloads
            st.markdown("---")
            if st.button("📥 Download các file đã chọn", type="primary", use_container_width=True, disabled=len(selected_files) == 0):
                st.session_state.prepare_download = True
                st.rerun()

            # Show download buttons only after user clicks "Prepare Download"
            if st.session_state.prepare_download:
                st.markdown("### 📦 Tải xuống")
                
                col1, col2 = st.columns(2)

                with col1:
                    if selected_files:
                        # Create zip for selected files
                        selected_zip_path = results['run_dir'] / "selected_pdfs.zip"

                        # Create temporary directory for selected files
                        temp_selected_dir = results['run_dir'] / "temp_selected"
                        temp_selected_dir.mkdir(exist_ok=True)

                        # Copy selected files to temp directory
                        for pdf_file in selected_files:
                            dest_path = temp_selected_dir / pdf_file.name
                            shutil.copy2(pdf_file, dest_path)

                        # Create zip
                        zip_directory(temp_selected_dir, selected_zip_path)

                        # Download button for selected files
                        with open(selected_zip_path, 'rb') as f:
                            st.download_button(
                                label=f"⬇️ Tải {len(selected_files)} file đã chọn",
                                data=f,
                                file_name=f"selected_pdfs_{results['timestamp']}.zip",
                                mime="application/zip",
                                use_container_width=True
                            )

                with col2:
                    # Download all files button
                    all_zip_path = results['run_dir'] / "all_pdfs.zip"
                    zip_directory(results['output_dir'], all_zip_path)

                    with open(all_zip_path, 'rb') as f:
                        st.download_button(
                            label=f"⬇️ Tải tất cả ({results['metadata']['pdfs_downloaded']} PDFs)",
                            data=f,
                            file_name=f"all_pdfs_{results['timestamp']}.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                
                # Reset button
                if st.button("🔄 Chọn lại file", use_container_width=True):
                    st.session_state.prepare_download = False
                    st.rerun()

            # File statistics
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tổng số file", len(pdf_files))
            with col2:
                if search_keywords:
                    st.metric("File Ưu tiên", len(priority_files))
                else:
                    st.metric("File Ưu tiên", "0")
            with col3:
                if search_keywords:
                    st.metric("File khác", len(other_files))
                else:
                    st.metric("File khác", len(pdf_files))
        else:
            st.warning("⚠️ Không tìm thấy PDF nào để tải xuống")
        
        # Log viewer
        with st.expander("📝 Xem log"):
            log_file = Path(results['log_file'])
            if log_file.exists():
                with open(log_file, 'r') as f:
                    log_content = f.read()
                st.text_area("Log output", log_content, height=300)
        
        # Clear results button
        st.markdown("---")
        if st.button("🔄 Crawl mới", key="clear_results", use_container_width=True):
            st.session_state.crawl_results = None
            st.rerun()
    
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
