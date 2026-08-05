# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Vũ Nguyễn Quốc Đạt |
| MSSV            | 00004 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Logistics & Delivery Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Delivery Agent | `src/delivery_agent.py` | `order_seller_findings` từ Coordinator | Thông tin phân tích thời gian giao hàng và phân định trách nhiệm chậm trễ | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Phân tích thời hạn giao nhận | [src/delivery_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/delivery_agent.py) | Module tính toán trễ hạn giao khách và bàn giao cho bên vận chuyển | Chạy `python src/verify_phase1.py` |
| Phân định trách nhiệm chậm trễ | [src/delivery_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/delivery_agent.py) | Logic gán lỗi chính xác cho Seller hoặc Logistics Provider | Chạy `python src/verify_phase1.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Xác định xem đơn hàng có bị giao muộn cho khách hàng hay không (`order_delivered_customer_date` > `order_estimated_delivery_date`).
2. Nếu đơn hàng bị giao muộn, cần phân định trách nhiệm lỗi thuộc về ai:
   - Nếu bên người bán bàn giao hàng cho đơn vị vận chuyển trễ so với thời hạn cho phép (`order_delivered_carrier_date` > `shipping_limit_date` của bất kỳ sản phẩm nào trong đơn hàng) $\rightarrow$ lỗi thuộc về người bán (`seller`).
   - Nếu người bán bàn giao hàng đúng hạn nhưng khách hàng nhận trễ $\rightarrow$ lỗi thuộc về đơn vị vận chuyển (`logistics_provider`).
3. Trích xuất danh sách các người bán bàn giao trễ hàng (`late_seller_ids`).

### Cách triển khai
- Sử dụng helper `parse_ts` để chuyển đổi các chuỗi thời gian của đơn hàng và sản phẩm thành đối tượng datetime.
- Duyệt qua danh sách `items` của đơn hàng để so sánh từng mốc hạn giao của seller.
- Gán giá trị cờ `is_late_delivery` và tính toán `responsible_party` tương ứng.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `order_seller_findings` (dict) |
| Output | Từ điển gồm: `is_late_delivery`, `seller_shipping_limits`, `late_seller_ids`, `any_seller_late`, `responsible_party` |

### Cách xác minh
```bash
python src/verify_phase1.py
```
- **Kết quả mong đợi:** Đối với đơn giao trễ có seller bàn giao trễ hàng, lỗi gán cho `"seller"`. Đối với đơn giao trễ nhưng seller giao đúng hạn, lỗi gán cho `"logistics_provider"`.
- **Kết quả thực tế:** Hệ thống phân loại chính xác các trường hợp giao trễ mẫu và gán trách nhiệm đúng theo ma trận nghiệp vụ.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Một đơn hàng có thể có nhiều sản phẩm và các sản phẩm đó có thể thuộc về các người bán (sellers) khác nhau với các mốc hạn giao hàng (`shipping_limit_date`) khác nhau.
- **Các phương án đã cân nhắc:**
  1. Chỉ so sánh mốc hạn giao hàng của sản phẩm đầu tiên trong đơn hàng (nhanh nhưng sai lệch nếu đơn hàng có nhiều sản phẩm).
  2. Duyệt qua tất cả sản phẩm của đơn hàng, so sánh từng `shipping_limit_date` riêng biệt và lưu cờ trễ cho từng mặt hàng.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo tính đúng đắn khi đơn hàng chứa sản phẩm của nhiều người bán. Chỉ cần một người bán bàn giao trễ hàng gây ảnh hưởng đến tiến độ, cờ `any_seller_late` sẽ được bật để quy trách nhiệm chính xác.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Với các đơn hàng không được giao thành công hoặc bị hủy, ngày giao hàng cho khách `order_delivered_customer_date` là trống (`NaN`/`None`). Phép so sánh datetime trực tiếp sẽ bị crash do kiểu dữ liệu `NoneType`.
- **Cách xử lý:** Bổ sung điều kiện kiểm tra tồn tại của các mốc thời gian: `bool(delivered and estimated and delivered > estimated)`. Nếu thiếu thông tin, mặc định coi như không trễ giao hàng (`is_late_delivery = False`).
- **Cách xác minh sau khi sửa:** Chạy kiểm tra với các đơn hàng đặc biệt ở Phase 3, hệ thống hoạt động ổn định và không phát sinh lỗi ngoại lệ.

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

**Họ và tên:** Vũ Nguyễn Quốc Đạt
**Ngày xác nhận:** 2026-08-05
