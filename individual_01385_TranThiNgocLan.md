# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Trần Thị Ngọc Lan |
| MSSV            | 2A202601385 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Order & Seller Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Order & Seller Agent | `src/order_seller_agent.py` | `claimed_order_id` từ Coordinator | Dữ liệu chi tiết về đơn hàng, danh sách sản phẩm, người bán và tổng chi phí | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khảo sát cấu trúc tệp dữ liệu Olist | [src/order_seller_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/order_seller_agent.py) | Module truy vấn nhanh bằng pandas, tối ưu hóa bộ nhớ | Chạy `python src/verify_phase1.py` |
| Xử lý trạng thái và mốc bàn giao người bán | [src/order_seller_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/order_seller_agent.py) | Trích xuất trạng thái hủy (`canceled`), hết hàng (`unavailable`), gắn nhãn cờ trễ hạn | Chạy `python src/verify_phase1.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Đơn hàng khách hàng khai báo (`claimed_order_id`) có thể ở dạng hash 32 ký tự viết hoa hoặc viết thường, cần được chuẩn hóa.
2. Trích xuất đầy đủ và chính xác danh sách các sản phẩm (`items`) thuộc đơn hàng đó kèm theo thông tin của từng người bán (`seller_id`) và hạn bàn giao hàng (`shipping_limit_date`).
3. Xác định xem người bán có bàn giao trễ cho bên vận chuyển không (so sánh `order_delivered_carrier_date` với `shipping_limit_date` của từng sản phẩm).

### Cách triển khai
- Sử dụng pandas để đọc dữ liệu từ thư mục `data/` một lần duy nhất (`load_order_seller_query`), xây dựng cấu trúc truy vấn nhanh theo nhóm bằng cách gom nhóm dữ liệu theo `order_id` để tăng tốc độ xử lý hàng trăm lần so với duyệt tuần tự.
- Thực hiện chuẩn hóa `claimed_order_id.strip().lower()` để so khớp.
- Gắn nhãn cờ `carrier_after_limit` cho từng item và cờ `any_carrier_after_limit` ở mức tổng thể đơn hàng.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `claimed_order_id` (string) |
| Output | Từ điển dữ liệu chứa: `order_id`, `order_status`, `items` (sắp xếp tăng dần theo `order_item_id`), `item_total_brl`, `freight_total_brl`, `seller_ids` (sắp xếp chữ cái), `is_canceled`, `is_unavailable`, `status_tags`, `any_carrier_after_limit` |

### Cách xác minh
```bash
python src/verify_phase1.py
```
- **Kết quả mong đợi:** Script xác minh in ra kết quả phân tích Order & Seller Agent chính xác cho tất cả test cases, không gặp lỗi định dạng dữ liệu hay thiếu trường.
- **Kết quả thực tế:** Tất cả 3 case mẫu kiểm tra đều đạt và hiển thị đầy đủ thông tin.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Các mốc thời gian trong cơ sở dữ liệu Olist được lưu trữ dưới dạng chuỗi (string) thô. Việc so sánh chuỗi thô trực tiếp dễ gặp lỗi khi có sự sai lệch định dạng hoặc múi giờ.
- **Các phương án đã cân nhắc:**
  1. So sánh chuỗi thô bằng toán tử so sánh chuỗi thông thường (nhanh nhưng không an toàn).
  2. Chuyển đổi toàn bộ chuỗi thời gian thành đối tượng `datetime` có nhận thức múi giờ (timezone-aware datetime) bằng hàm `pandas.to_datetime` hoặc helper `parse_ts`.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo độ chính xác tuyệt đối trong việc so sánh thời gian, không bị ảnh hưởng bởi định dạng khác nhau của giây hoặc múi giờ lệch.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi gặp đơn hàng không tồn tại trong hệ thống hoặc đơn hàng bị hủy ở trạng thái sớm (chưa có thông tin vận chuyển `order_delivered_carrier_date` là `NaN`), việc gọi phương thức xử lý chuỗi thời gian trực tiếp bị lỗi `AttributeError` hoặc `TypeError` do giá trị `NaN` trong pandas.
- **Cách xử lý:** Bổ sung hàm helper `clean` để lọc sạch các giá trị `NaN`/`None` thành `None` trước khi xử lý, và gán giá trị mặc định trống cho các trường tính toán khi đơn hàng không tồn tại.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra với các đơn hàng bị hủy hoặc không tồn tại, hệ thống trả về kết quả an toàn với `order_found = False` và không bị sập chương trình.

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

**Họ và tên:** Trần Thị Ngọc Lan
**Ngày xác nhận:** 2026-08-05
