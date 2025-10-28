# Depth-3 File Crawler (Streamlit)

## Chức năng
- Nhập 1 URL gốc, crawl liên kết nội bộ tối đa 3 mức (BFS).
- Phát hiện và tải các file tài liệu: pdf, docx, xlsx, pptx, csv, txt, zip, rar, 7z. Tuỳ chọn bao gồm ảnh png/jpg/webp.
- Tải song song, giới hạn kích thước mỗi file nếu cần, tạo ZIP tải về.

## Cài đặt cục bộ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy ứng dụng cục bộ
```bash
streamlit run app/main.py
```

## Deploy lên Streamlit Community Cloud
1. Push mã nguồn này lên một GitHub repo (ví dụ `username/depth3-crawler`).
2. Vào `https://share.streamlit.io` > New app.
3. Chọn repo/branch, đặt file chạy là `app/main.py`.
4. Thêm file `runtime.txt` (đã có) để chọn Python `python-3.10`.
5. Streamlit sẽ cài đặt từ `requirements.txt` tự động.
6. Sau deploy, mở app và nhập URL để chạy.

Lưu ý quyền truy cập outbound: một số domain có thể chặn; kiểm tra log trên trang Deploy nếu lỗi.

## Lưu ý
- Ứng dụng chỉ parse HTML tĩnh, không chạy JavaScript.
- Chỉ mở rộng trong cùng domain của URL gốc; link tệp có thể ở CDN ngoài domain vẫn được tải.
- Một số trang có thể chặn bot/UA; tuỳ chỉnh header/timeout nếu cần.
- Dữ liệu được lưu vào thư mục tạm (`/tmp/streamlit-crawl/<timestamp>`).

## Kiểm thử ví dụ
- URL: `https://www.siemens.com/global/en/products/automation/systems/industrial/plc/s7-1200.html`
- Kỳ vọng: phát hiện file PDF tài liệu nếu link xuất hiện trong HTML các trang nội bộ trong phạm vi 3 mức.
