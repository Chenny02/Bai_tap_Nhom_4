# Kiểm tra ngày 2026-10-20

- Python 3.11: kiểm tra cú pháp thành công.
- `test_convert.py`: 5/5 test đạt trong môi trường `.venv`.
- Chạy `--plan` trên thư mục Đề thật: tìm đủ 24 PDF trong 20 thư mục.
- Sinh `smoke_output/document.tex` bằng Pandoc thật: giữ tiếng Việt, Câu V,
  phân số và căn dưới dạng lệnh LaTeX, không dùng Verbatim hay chèn ảnh trang.
- Kiểm tra thiếu Marker/PyTorch: chương trình báo lỗi rõ và trả exit code 2;
  chưa tạo đầu ra giả khi không có mô hình.
- Chưa xác nhận biên dịch mẫu: trình biên dịch tích hợp bị chặn bởi môi trường
  sandbox; chạy XeLaTeX ngoài sandbox khởi động được nhưng MiKTeX phải tải nhiều
  gói bổ sung. Đã dừng lần kiểm tra trước khi có PDF hoàn chỉnh. Không tính đây
  là một lượt biên dịch thành công.

Chưa xác minh OCR end-to-end: đã dừng cài Marker/PyTorch để tránh tải bộ thư viện
và trọng số lớn khi ổ D còn khoảng 7 GB. Hiện `.venv` chỉ có Pandoc/pypandoc và
các công cụ Python cơ bản; phải cài đầy đủ requirements trước khi OCR PDF.
Không có kết quả chuyển PDF thật được tuyên bố đã đạt trong đợt kiểm tra này.

Mã gọi OCR theo API chính thức của Marker v1.10.1:
https://github.com/datalab-to/marker/blob/v1.10.1/README.md#use-from-python

Các tệp LaTeX cũ trong thư mục LaTeX không bị sửa bởi chương trình này.
