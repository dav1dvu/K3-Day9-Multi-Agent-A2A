# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Ngọc Nam |
| MSSV            | 00003 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Payment & Finance Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Payment Agent | `src/payment_agent.py` | `order_id`, `item_total`, `freight_total` từ Coordinator | Dữ liệu đối soát tài chính và so khớp thanh toán | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khảo sát tệp dữ liệu thanh toán Olist | [src/payment_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/payment_agent.py) | Module load nhanh dữ liệu thanh toán bằng pandas | Chạy `python src/verify_phase1.py` |
| Tính toán so khớp tài chính & trích xuất split payment | [src/payment_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/payment_agent.py) | Bảng tính tiền chính xác, cờ hiệu so khớp với sai số tối đa 0.10 BRL | Chạy `python src/verify_phase1.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Đối khớp tổng số tiền khách hàng đã thanh toán thực tế (tổng hợp từ nhiều dòng thanh toán trong `olist_order_payments_dataset.csv`) với số tiền đơn hàng trên hệ thống (tổng giá trị hàng hóa `item_total` + tiền cước vận chuyển `freight_total`).
2. Phát hiện và xử lý trường hợp thanh toán nhiều lần/nhiều phương thức (Split Payment).
3. Đảm bảo tính toán chính xác tuyệt đối, tránh sai số do số thực dấu phẩy động (floating-point precision) gây ra khi tính tổng nhiều giao dịch.

### Cách triển khai
- Đọc tệp dữ liệu thanh toán Olist, nhóm theo `order_id` và lưu trữ dưới dạng index truy vấn nhanh.
- Trích xuất danh sách các dòng thanh toán `payment_rows` (sắp xếp tăng dần theo `payment_sequential`).
- Áp dụng kiểm tra độ lệch tuyệt đối: `abs(payment_total - order_total) <= 0.10 BRL` để gán cờ `payment_matches_order`.
- Làm tròn mọi giá trị tài chính về đúng 2 chữ số thập phân sử dụng helper `money`.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `order_id` (string), `item_total_brl` (float), `freight_total_brl` (float) |
| Output | Từ từ điển chứa: `payment_total_brl`, `payment_count`, `payment_rows`, `is_split_payment` (số lần thanh toán >= 2), `payment_matches_order`, `absolute_difference` |

### Cách xác minh
```bash
python src/verify_phase1.py
```
- **Kết quả mong đợi:** So khớp thành công tổng tiền cho các đơn hàng mẫu và phát hiện đúng các đơn hàng split payment, cờ so khớp trả về `True` nếu sai số nằm trong khoảng `[0.0, 0.10]` BRL.
- **Kết quả thực tế:** Vượt qua toàn bộ các bước kiểm tra logic của script xác minh.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thực hiện phép so sánh trực tiếp tổng thanh toán với tổng đơn hàng, sai số dấu phẩy động của ngôn ngữ lập trình Python (ví dụ: `29.99 + 8.72 = 38.71000000000001` BRL) có thể khiến phép so sánh `==` trả về `False` dù về mặt toán học hai tổng bằng nhau.
- **Các phương án đã cân nhắc:**
  1. Sử dụng thư viện `decimal.Decimal` để tính toán tài chính (chính xác nhưng làm chậm tốc độ truy vấn pandas).
  2. Sử dụng phép làm tròn `round(value, 2)` sau mỗi phép tính và so sánh bằng sai số sai lệch tối đa `0.10` BRL.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo hiệu năng cao khi làm việc với lượng lớn dữ liệu bằng pandas, đồng thời đáp ứng hoàn hảo yêu cầu nghiệp vụ về khoảng sai số chấp nhận được (tolerance threshold) của đề bài.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Trong một số đơn hàng bị hủy hoặc không có dòng thanh toán nào trong CSV, hàm tính tổng tiền trả về giá trị `NaN` hoặc lỗi `Empty Dataframe` khi tính toán tổng thanh toán.
- **Cách xử lý:** Bổ sung kiểm tra sự tồn tại của dữ liệu trước khi tính toán. Nếu không tìm thấy thông tin thanh toán, trả về mặc định `payment_total_brl = 0.0` và `payment_count = 0` một cách an toàn.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử chéo và xác nhận hệ thống không bị lỗi khi đối mặt với đơn hàng bị hủy mà chưa thanh toán.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu thô từ Crossref API được tải về dưới dạng JSON, tiến hành làm sạch metadata, trích xuất nội dung văn bản. Văn bản được chia thành các đoạn nhỏ (chunking), sau đó đi qua mô hình nhúng (Embedding Model) để chuyển đổi thành vector đại diện và được lưu trữ vào cơ sở dữ liệu vector (Vector Database index) kèm metadata.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Tập evaluation set chứa các câu hỏi kiểm thử. Ground-truth document IDs là danh sách các tài liệu thực sự chứa câu trả lời chuẩn xác. Chất lượng retrieval được đo bằng việc so khớp các tài liệu được retrieve với ground-truth (qua Recall@K, Precision@K, MAP). Chất lượng câu trả lời (answer quality) được đánh giá bằng độ trùng khớp thông tin hoặc dùng LLM-as-a-judge để chấm điểm.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks kiểm tra tính đúng đắn, toàn vẹn và sạch sẽ của dữ liệu (schema, định dạng, logic nghiệp vụ). Freshness monitoring kiểm tra mức độ cập nhật của dữ liệu, tần suất cập nhật dữ liệu mới từ nguồn vào hệ thống index.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính nhất quán và tính khoa học của thực nghiệm (A/B testing). Khi giữ nguyên tập test set, mọi sự thay đổi của metric đo lường chất lượng hoàn toàn là do thay đổi cấu hình hệ thống (corrupted hoặc repaired) chứ không bị ảnh hưởng bởi sự khác biệt của câu hỏi đầu vào.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Repair thành công khi các metric đánh giá chất lượng (Recall, Accuracy, F1) phục hồi về mức tương đương hoặc vượt trội so với baseline, đồng thời các file output/artifact sinh ra đạt chuẩn schema cấu trúc và không còn chứa dữ liệu lỗi logic.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Ngọc Nam
**Ngày xác nhận:** 2026-08-05
