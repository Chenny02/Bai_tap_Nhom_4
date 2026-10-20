# Chuyển PDF đề thi sang LaTeX, chạy cục bộ miễn phí

Python 3.11; Marker 1.10.1 nhận dạng chữ và công thức; Pandoc đóng gói LaTeX.
Không API key, không gọi dịch vụ OCR trả phí, không gửi PDF tới dịch vụ cloud.
Lần đầu cần Internet để tải thư viện và trọng số mô hình (có thể nhiều GB).
CPU chạy được nhưng chậm; GPU NVIDIA tương thích PyTorch sẽ nhanh hơn.
Marker phiên bản này miễn phí cho sử dụng cá nhân/nghiên cứu; xem giấy phép
trọng số nếu dùng kinh doanh: https://github.com/datalab-to/marker/tree/v1.10.1

## Cài đặt (PowerShell trong thư mục này)

```powershell
$env:PYTHONUTF8='1'
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe convert.py --doctor
```

Đã ghim phiên bản Marker để dùng mô hình PyTorch cục bộ, tránh thay đổi backend
của các bản mới. Không thêm `--use_llm`. Pandoc binary được cài kèm qua pip.
Chỉ cần MiKTeX/TeX Live khi dùng `--compile`; tệp `.tex` vẫn xuất được khi thiếu nó.

## Chạy một PDF trước

Toàn bộ logic xử lý nằm trong `convert.py`; vẫn cần cài thư viện từ
`requirements.txt` một lần. Đầu vào là đường dẫn PDF. Đầu ra mặc định luôn là
thư mục `output` cạnh `convert.py`, bất kể terminal đang đứng ở đâu:
`D:\KHMT 18-01\Trực quan và phân tích dữ liệu\Đề toán lớp 9\pdf_to_tex\output`.

```powershell
.\.venv\Scripts\python.exe convert.py "D:\KHMT 18-01\Trực quan và phân tích dữ liệu\Đề toán lớp 9\Đề\3\de-thi-2024.pdf"
```

Cũng có thể chạy `convert.py` không kèm đối số rồi nhập/dán đường dẫn khi được
hỏi. Ví dụ trên tạo `output\de-thi-2024\document.tex` cùng các tệp hỗ trợ.
Thêm `--compile` để tạo PDF. `--output` vẫn có thể dùng nếu muốn đổi thư mục.

## Chạy cả bộ

```powershell
.\.venv\Scripts\python.exe convert.py "..\Đề" --output "..\LaTeX_Python" --compile
```

Mặc định dùng CPU. GPU: thêm `--device cuda` sau khi cài PyTorch CUDA phù hợp.
`--limit 1` chỉ xử lý PDF đầu tiên. Công cụ không ghi đè thư mục kết quả đã có:
hãy dùng tên output mới nếu chạy lại.
Thêm `--plan` để liệt kê danh sách PDF/đầu ra trước khi tải mô hình hoặc OCR.

Mỗi PDF tạo một thư mục tương ứng, chứa:

- `document.tex`: tài liệu LaTeX độc lập, dùng XeLaTeX và Times New Roman.
- `raw.md`: nhận dạng thô để đối chiếu; `selected.md`: nội dung được xuất.
- `metadata.json`, `report.json`: nguồn SHA-256, cấu hình, cảnh báo và trạng thái.
- Ảnh trích từ PDF, nếu có. Giữ các ảnh cạnh `.tex` khi sao chép.
- `document.pdf`, log và `build-output.txt` nếu yêu cầu biên dịch thành công.

Toàn bộ kết quả OCR được gắn `content_verified: false`. Code không tự giải bài,
không sửa số liệu, không đổi số câu và không tuyên bố biên dịch được là đúng nội dung.
OCR vẫn có thể mất dấu căn/điều kiện. Hình vẽ được giữ dạng ảnh; không chuyển sang TikZ.
Pandoc có thể không giữ nguyên bố cục/nhận đủ bảng HTML; cần kiểm tra bản xuất.

## PDF gộp đề và đáp án; lọc phần đại số

Mặc định giữ toàn bộ PDF trong một `.tex`, kể cả hình học. Không tự đoán phần
đại số hay ranh giới đề/đáp án. Để tách, dùng manifest chỉ rõ trang hoặc chuỗi mốc
đã nhìn thấy trong `raw.md` sau lượt OCR đầu tiên:

```json
{
  "jobs": [
    {
      "pdf": "3/de-thi-2024.pdf",
      "output": "3/de-thi",
      "pages": "0",
      "exclude": [{"start": "Câu IV (3,0 điểm)", "end": "Câu V (0,5 điểm)"}]
    },
    {
      "pdf": "3/dap-an-2024.pdf",
      "output": "3/dap-an",
      "pages": "0-1"
    }
  ]
}
```

Ví dụ mốc trên chỉ minh họa: phải chép chính xác từ `raw.md`, kể cả Markdown.
Trang tính từ 0. `start`/`end` ở cấp job giới hạn nội dung (giữ start, bỏ end).
`exclude` xóa từ start tới trước end, không đổi số câu phía sau. Mốc không duy nhất
hoặc không tìm thấy sẽ báo lỗi, không âm thầm bỏ bài. Đáp án dạng bảng có thể cần
chọn trang hoặc rà thủ công vì câu hỏi có thể nằm trong ô bảng.

```powershell
.\.venv\Scripts\python.exe convert.py "..\Đề" --manifest jobs.json --output "..\LaTeX_Python_loc" --compile
```

Với nguồn gộp và lời giải xen kẽ từng câu, không thể tách chỉ theo trang: cần
cấu hình mốc theo kết quả OCR hoặc chỉnh `selected.md`. Không tự bịa hai bản riêng.

Xuất lại Markdown đã kiểm tra mà không chạy OCR:

```powershell
.\.venv\Scripts\python.exe convert.py --from-markdown "duong-dan\selected.md" --output "..\ban_xuat_lai" --compile
```

Nếu Markdown có ảnh, sao chép ảnh về đúng vị trí trong thư mục kết quả trước khi
biên dịch lại; chế độ này chủ yếu dành cho văn bản/công thức.

## Kiểm tra

```powershell
py -3.11 -m unittest discover -s . -p "test_*.py" -v
```

Các test kiểm tra giữ số câu, báo lỗi mốc mơ hồ và chuyển công thức bằng Pandoc;
không thay thế việc đối chiếu từng công thức OCR với PDF.
