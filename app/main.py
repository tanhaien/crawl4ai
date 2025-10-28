import os
import time
import tempfile
from typing import Optional, List

import streamlit as st
import validators

from app.crawler import BFSCrawler, make_zip, ALLOWED_DOC_EXT, IMAGE_EXT
from app.types import CrawlItem


st.set_page_config(page_title="Depth-3 File Crawler", layout="wide")

st.title("Depth-3 File Crawler")

with st.sidebar:
    st.markdown("### Cấu hình")
    default_url = "https://www.siemens.com/global/en/products/automation/systems/industrial/plc/s7-1200.html"
    url = st.text_input("Nhập URL gốc", value=default_url)
    depth = st.number_input("Độ sâu liên kết (0-3)", min_value=0, max_value=3, value=3, step=1)
    include_images = st.checkbox("Bao gồm ảnh (png/jpg/webp)", value=False)
    max_pages = st.number_input("Giới hạn số trang tối đa", min_value=1, max_value=2000, value=200, step=10)
    max_size_mb = st.number_input("Giới hạn kích thước mỗi tệp (MB, 0 = bỏ qua)", min_value=0, max_value=2048, value=0, step=10)
    max_workers = st.number_input("Số luồng tải song song", min_value=1, max_value=32, value=6, step=1)

    start = st.button("Quét & Tải tệp")

if start:
    if not validators.url(url):
        st.error("URL không hợp lệ.")
        st.stop()

    temp_dir = os.path.join(tempfile.gettempdir(), "streamlit-crawl", str(int(time.time())))
    os.makedirs(temp_dir, exist_ok=True)

    st.info("Đang quét trang...")
    crawler = BFSCrawler(root_url=url, max_depth=int(depth), include_images=bool(include_images), max_pages=int(max_pages))
    pages, file_urls = crawler.crawl()

    st.write(f"Số trang duyệt được: {len(pages)}")
    st.write(f"Số URL tệp phát hiện: {len(file_urls)}")

    if not file_urls:
        st.warning("Không tìm thấy tệp phù hợp.")
        st.stop()

    st.info("Đang tải tệp...")
    items: List[CrawlItem] = crawler.download_all(dest_dir=temp_dir, max_size_mb=(None if max_size_mb == 0 else int(max_size_mb)), max_workers=int(max_workers))

    # Hiển thị bảng kết quả
    import pandas as pd
    df = pd.DataFrame([
        {
            "file": it.filename,
            "status": it.status,
            "size(bytes)": it.size_bytes,
            "mime": it.mime_type,
            "url": it.file_url,
            "local": it.local_path,
            "error": it.error,
        }
        for it in items
    ])

    st.dataframe(df, use_container_width=True)

    # ZIP download
    success_items = [it for it in items if it.status == "success"]
    if success_items:
        zip_bytes, count = make_zip(success_items, zip_name="files.zip")
        st.download_button(
            label=f"Tải ZIP ({count} tệp)",
            data=zip_bytes,
            file_name="crawl_files.zip",
            mime="application/zip",
        )

    st.success("Hoàn tất.")
else:
    st.caption("Nhập URL và bấm 'Quét & Tải tệp' để bắt đầu.")
