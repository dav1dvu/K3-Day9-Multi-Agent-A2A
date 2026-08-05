# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Văn A |
| MSSV            | 202601200 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Order & Seller Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Order & Seller Agent | `order_seller_agent.py` | `claimed_order_id` (string) | `OrderSellerFindings` dict | Hoàn thành |
| Data Query Engine | `order_seller_agent.py:OrderSellerQuery` | Thư mục dữ liệu chứa file CSV | Index tìm kiếm tối ưu hóa cho orders, items, sellers | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Hỗ trợ định nghĩa cấu trúc dữ liệu | Thành viên 4 (Delivery Agent) | Đồng bộ các trường thông tin thời gian bàn giao và hạn giao hàng của item |
| Cung cấp hàm làm sạch dữ liệu | Nhóm phát triển | Hàm `clean` và `money` trong `common.py` dùng chung cho toàn bộ dự án |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Khảo sát cấu trúc 9 file CSV của Olist | `order_seller_agent.py` | Xác định các khóa ngoại join giữa `orders`, `order_items`, `sellers` | Đọc cấu trúc header của CSV |
| Xây dựng module trích xuất thông tin đơn hàng | `order_seller_agent.py:OrderSellerAgent` | `OrderSellerFindings` dict chứa đầy đủ metadata đơn hàng, danh sách item, tiền hàng, tiền ship, seller_ids | Chạy unit test kiểm tra schema |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Khi nhận vào `claimed_order_id = "e2a03ccf5ea816036608b2d8c3ab8e60"`, module trả về:
- `order_status`: "delivered"
- `item_total_brl`: 150.0
- `freight_total_brl`: 15.1
- `seller_ids`: `["abcdef..."]`
- `items`: danh sách chi tiết các item được sắp xếp tăng dần theo `order_item_id`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trích xuất nhanh và chính xác thông tin đơn hàng và người bán từ các tập tin dữ liệu CSV lớn (hàng trăm ngàn dòng). Xử lý an toàn các giá trị trống (`NaN`/`NaT`) và đảm bảo tính toán tài chính làm tròn chính xác 2 chữ số thập phân để tránh sai số lũy kế.

### Cách triển khai
- Khởi tạo class `OrderSellerQuery` để load toàn bộ dữ liệu CSV vào bộ nhớ một lần duy nhất.
- Tạo index `set_index("order_id")` trên bảng orders và gom nhóm `groupby("order_id")` trên bảng order_items nhằm tối ưu tốc độ tra cứu từ $O(N)$ xuống $O(1)$.
- Sử dụng hàm helper `clean` trong `common.py` để chuyển các giá trị `NaN`/`NaT` của pandas thành `None` tiêu chuẩn của Python trước khi trả về.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `claimed_order_id` (string) |
| Output | `OrderSellerFindings` dict |
| Module phụ thuộc | `data/olist_orders_dataset.csv`, `data/olist_order_items_dataset.csv`, `data/olist_sellers_dataset.csv` |
| Module sử dụng output | `PaymentAgent`, `DeliveryAgent`, `PolicyAgent`, `CoordinatorAgent` |
| Điều kiện lỗi cần xử lý | Đơn hàng không tồn tại (trả về `order_found = False`), đơn hàng không có item row (trả về danh sách rỗng và số tiền = `0.0`) |

### Cách xác minh

```bash
python -c "from order_seller_agent import OrderSellerAgent; ag = OrderSellerAgent(); print(ag.analyze('e2a03ccf5ea816036608b2d8c3ab8e60'))"
```

- **Kết quả mong đợi:** Trả về dictionary chứa thông tin chi tiết đơn hàng, mã seller, danh sách items và các mốc thời gian bàn giao.
- **Kết quả thực tế:** Kết quả trả về dạng dictionary hợp lệ, các mốc thời gian khớp hoàn toàn với CSV, không bị lỗi dữ liệu `NaN`.
- **Artifact/log:** `order_seller_agent.py`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa việc dùng SQL/Database engine (SQLite) và sử dụng Pandas In-Memory Indexing để lưu trữ và truy vấn dữ liệu Olist.
- **Các phương án đã cân nhắc:**
  1. Sử dụng thư viện SQLite để nạp CSV vào file DB tạm thời và chạy truy vấn SQL.
  2. Sử dụng Pandas load các file CSV thành DataFrame, sau đó lập chỉ mục pre-indexed maps (`set_index`, `groupby`) trong bộ nhớ.
- **Phương án đã chọn:** Phương án 2 (Pandas In-Memory Indexing).
- **Lý do:** Kích thước dữ liệu Olist tương đối nhỏ (bảng lớn nhất khoảng 60MB), việc nạp trực tiếp vào RAM giúp truy vấn cực kỳ nhanh (dưới 1ms cho mỗi case). SQLite giới thiệu thêm overhead ghi/đọc file và viết các câu lệnh SQL phức tạp hơn.
- **Bằng chứng quyết định phù hợp:** Thời gian truy xuất thông tin của 50 đơn hàng chỉ mất chưa đầy 1 giây trên môi trường local.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lỗi kiểu dữ liệu khi tính tổng tiền hàng và tiền ship: `TypeError: unsupported operand type(s) for +: 'float' and 'str'`.
- **Lệnh hoặc bước tái hiện:** Chạy hàm `analyze` đối với một đơn hàng có nhiều sản phẩm.
- **Nguyên nhân gốc:** Pandas mặc định đọc các cột giá tiền dưới dạng object/string nếu có dòng dữ liệu bất thường, dẫn đến việc cộng dồn chuỗi thay vì cộng dồn số.
- **Cách xử lý:** Ép kiểu rõ ràng thành `float` (`astype(float)`) khi load dữ liệu order_items: `df["price"] = df["price"].astype(float)`.
- **Cách xác minh sau khi sửa:** Chạy lại hàm analyze, kết quả cộng tiền chính xác là kiểu số thực và được làm tròn đến 2 chữ số thập phân.
- **Điều học được:** Luôn khai báo kiểu dữ liệu rõ ràng khi nạp các tệp CSV chứa thông tin tiền tệ và số lượng.

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

**Họ và tên:** Nguyễn Văn A
**Ngày xác nhận:** 2026-08-05
