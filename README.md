# PDF Crawler (Streamlit)

Ứng dụng Streamlit để crawl và tải xuống tất cả file PDF từ danh sách URL.

## Tính năng
- Crawl nhiều website song song, giới hạn số trang mỗi site
- Tự động phát hiện link PDF (trực tiếp và nhúng iframe/object)
- Tải file PDF theo cấu trúc thư mục theo domain
- Theo dõi tiến trình, log, metadata
- Đóng gói kết quả thành file ZIP để tải về

## Chạy local
1) Yêu cầu Python 3.11
2) Cài đặt dependencies:
```
pip install -r requirements.txt
```
3) Chạy ứng dụng:
```
streamlit run streamlit_app.py
```

## Deploy lên Streamlit Community Cloud
1) Đẩy mã nguồn này lên GitHub (public hoặc private repo đều được)
2) Truy cập https://share.streamlit.io (hoặc https://streamlit.io/cloud) và đăng nhập
3) Chọn "New app" -> kết nối tới repo vừa đẩy
4) Chọn các thông tin:
   - Repository: <tên repo của bạn>
   - Branch: main (hoặc branch bạn dùng)
   - Main file path: `streamlit_app.py`
5) Nhấn "Deploy" để khởi chạy

Ghi chú:
- File `requirements.txt` đã khai báo toàn bộ dependencies cần thiết
- File `runtime.txt` đã khoá phiên bản Python 3.11 để deploy ổn định
- Hệ thống file trên Streamlit Cloud là tạm thời (ephemeral). Hãy tải file ZIP ngay sau khi crawl xong

## Cấu trúc chính
- `streamlit_app.py`: Giao diện và logic Streamlit
- `pdf_crawler.py`: Bộ máy crawl/parse/download PDF (asyncio + aiohttp)
- `requirements.txt`: Danh sách thư viện Python
- `runtime.txt`: Phiên bản Python cho Streamlit Cloud
- `runs/`: Thư mục chứa kết quả từng lần chạy (tạo động khi chạy)

## Mẹo sử dụng
- Nhập nhiều URL, mỗi dòng một URL
- Điều chỉnh số trang tối đa, số download đồng thời và timeout phù hợp
- Nếu website có nhiều PDF, thời gian xử lý sẽ lâu hơn
- Nếu có link lỗi, kiểm tra mục expander "📝 Xem log" để biết chi tiết

## License
MIT
