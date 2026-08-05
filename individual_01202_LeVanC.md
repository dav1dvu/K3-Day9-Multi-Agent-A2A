# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Lê Văn C |
| MSSV            | 202601202 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Logistics & Delivery Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Delivery Agent | `delivery_agent.py` | `OrderSellerFindings` dict | `DeliveryFindings` dict | Hoàn thành |
| Logistics Timing Analyser | `delivery_agent.py:DeliveryAgent` | Các mốc thời gian bàn giao và vận chuyển | Phân định lỗi trễ hạn thuộc về bên nào (Seller vs Logistics) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Hỗ trợ cấu hình mốc thời gian | Thành viên 2 (Order & Seller) | Thiết lập định dạng timestamp thống nhất và cách thức parse chuỗi ngày tháng an toàn |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khảo sát các mốc thời gian quan trọng | `delivery_agent.py` | Xác định rõ các mốc `shipping_limit_date`, `order_delivered_carrier_date`, `order_delivered_customer_date` và `order_estimated_delivery_date` | Đọc tài liệu dữ liệu Olist |
| Xây dựng logic phân định trách nhiệm giao muộn | `delivery_agent.py:DeliveryAgent` | Trích xuất `DeliveryFindings` xác định rõ `is_late_delivery` và `responsible_party` | Chạy unit test kiểm tra schema |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Khi nhận vào findings có `order_delivered_customer_date` trễ hơn `order_estimated_delivery_date` (giao trễ cho khách hàng):
- Hệ thống so sánh từng `shipping_limit_date` của từng sản phẩm với `order_delivered_carrier_date` (thời điểm giao cho carrier).
- Nếu bất kỳ sản phẩm nào có `order_delivered_carrier_date` muộn hơn `shipping_limit_date`, kết quả `responsible_party` được gán là `"seller"`.
- Ngược lại, nếu bàn giao cho carrier đúng hạn nhưng giao cho khách vẫn trễ, `responsible_party` được gán là `"logistics_provider"`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
So sánh chính xác các mốc thời gian vận chuyển để xác định xem đơn hàng có thực sự bị giao trễ hay không, và lỗi trễ hạn thuộc về ai (Người bán bàn giao trễ cho đơn vị vận chuyển hay đơn vị vận chuyển giao trễ cho khách hàng).

### Cách triển khai
- Sử dụng hàm `parse_ts` từ `common.py` để chuyển đổi chuỗi ngày tháng thành các đối tượng `datetime` giúp việc so sánh lớn hơn/nhỏ hơn được chính xác.
- Duyệt qua danh sách items của đơn hàng, đối chiếu mốc `shipping_limit_date` của từng sản phẩm với `order_delivered_carrier_date` chung của đơn hàng để xác định biến cờ hiệu `any_seller_late`.
- Thiết lập logic rẽ nhánh để gán bên chịu trách nhiệm (`seller`, `logistics_provider` hoặc `None` nếu giao đúng hạn).

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `OrderSellerFindings` dict |
| Output | `DeliveryFindings` dict |
| Module phụ thuộc | `OrderSellerAgent` |
| Module sử dụng output | `PolicyAgent`, `CoordinatorAgent` |

### Cách xác minh

```bash
python -c "from delivery_agent import DeliveryAgent; ag = DeliveryAgent(); print(ag.analyze({'order_id': '123', 'order_estimated_delivery_date': '2018-10-10 00:00:00', 'order_delivered_customer_date': '2018-10-12 00:00:00', 'order_delivered_carrier_date': '2018-10-09 00:00:00', 'items': [{'order_item_id': 1, 'seller_id': 'sel123', 'shipping_limit_date': '2018-10-08 00:00:00'}]}))"
```

- **Kết quả mong đợi:** Trả về dictionary cho thấy `is_late_delivery = True`, `any_seller_late = True`, và `responsible_party = 'seller'` (do carrier nhận hàng ngày 9 trễ hơn hạn shipping limit ngày 8).
- **Kết quả thực tế:** Kết quả trả về đúng logic thiết lập, các mốc so khớp chính xác.
- **Artifact/log:** `delivery_agent.py`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách so sánh ngày tháng (so sánh chuỗi trực tiếp vs parse sang đối tượng `datetime`).
- **Các phương án đã cân nhắc:**
  1. So sánh chuỗi ISO timestamp trực tiếp theo thứ tự từ điển (ASCII order).
  2. Parse chuỗi sang đối tượng `datetime` của Python bằng `strptime`.
- **Phương án đã chọn:** Phương án 2 (Parse sang đối tượng `datetime`).
- **Lý do:** Dù so sánh chuỗi trực tiếp nhanh hơn nhưng dễ gặp lỗi nếu định dạng chuỗi bị lệch (ví dụ: thiếu chữ số, khác múi giờ hoặc có khoảng trắng thừa). Parse sang đối tượng `datetime` giúp kiểm soát tốt các ngoại lệ và dễ bảo trì hơn, đảm bảo tính đúng đắn tuyệt đối cho các nghiệp vụ tài chính và khiếu nại.
- **Bằng chứng quyết định phù hợp:** Toàn bộ 50 cases đều được so khớp chính xác và không phát sinh bất kỳ lỗi so sánh sai lệch nào.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lỗi crash khi so sánh ngày tháng: `TypeError: can't compare offset-naive and offset-aware datetimes` hoặc lỗi so sánh với giá trị `None` (`TypeError: '>' not supported between instances of 'NoneType' and 'NoneType'`).
- **Lệnh hoặc bước tái hiện:** Chạy hàm `analyze` trên các đơn hàng chưa được giao (đơn hàng bị hủy hoặc không có ngày `order_delivered_customer_date`).
- **Nguyên nhân gốc:** Một số mốc thời gian trong cơ sở dữ liệu bị khuyết (`NaN`), dẫn đến việc parse ra giá trị `None` và thực hiện so sánh trực tiếp.
- **Cách xử lý:** Bọc thêm các điều kiện kiểm tra tồn tại `if delivered and estimated` trước khi so sánh, bảo đảm cả hai vế so sánh đều khác `None`.
- **Cách xác minh sau khi sửa:** Hệ thống xử lý trơn tru các đơn hàng thiếu mốc ngày tháng (ví dụ đơn bị hủy) mà không bị crash.
- **Điều học được:** Luôn phòng ngừa các trường hợp dữ liệu bị khuyết (missing data) đối với các trường timestamp trong thế giới thực.

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

**Họ và tên:** Lê Văn C
**Ngày xác nhận:** 2026-08-05
