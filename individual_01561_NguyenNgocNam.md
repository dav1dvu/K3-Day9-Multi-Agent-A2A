# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Ngọc Nam |
| MSSV | 01561 |
| Khóa/Lớp | K3 |
| Vai trò chính | Payment & Finance Agent Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `src/payment_agent.py` | `order_id`, `item_total_brl`, `freight_total_brl` từ Coordinator | `PaymentFindings` đã đối soát | Hoàn thành |
| Kiểm thử Payment Phase 2 | `src/test_payment_agent.py` | Dữ liệu Olist và các trường hợp biên | Kết quả kiểm thử single/split/missing/tolerance | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đồng bộ contract handoff | Coordinator và Policy Agent | Policy sử dụng trực tiếp cờ `valid_split_payment` do Payment Agent cung cấp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Lập chỉ mục payment theo `order_id` | `src/payment_agent.py:PaymentQuery` | Truy xuất các dòng payment đã sắp xếp theo `payment_sequential` | `python src/verify_phase1.py` |
| Đối soát tài chính | `src/payment_agent.py:PaymentAgent.analyze` | Tổng payment, số dòng, độ lệch và trạng thái khớp | `python -m unittest src.test_payment_agent -v` |
| Phát hiện split payment hợp lệ | `src/payment_agent.py:PaymentAgent.analyze` | `valid_split_payment = is_split_payment and payment_matches_order` | `python -m unittest src.test_payment_agent -v` |
| Xử lý ca không có payment | `src/payment_agent.py:PaymentAgent.analyze` | Không nhận nhầm trường hợp `0 = 0` là payment hợp lệ | `test_missing_payment_is_not_a_false_match` |

Kết quả kiểm tra trên 50 case chính thức: 50 case có payment, 42 case đối soát khớp, 9 case là split payment và cả 9 case đều là split payment hợp lệ.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Payment Agent phải cộng toàn bộ `payment_value` của một đơn, kể cả khi khách thanh toán bằng nhiều dòng hoặc nhiều phương thức. Tổng này được so sánh với `item_total_brl + freight_total_brl`; độ lệch tối đa được chấp nhận là `0.10 BRL`.

### Cách triển khai

- Đọc `olist_order_payments_dataset.csv` một lần bằng pandas và nhóm theo `order_id`.
- Chuyển tiền sang `decimal.Decimal` từ chuỗi và làm tròn thương mại bằng `ROUND_HALF_UP` đến `0.01 BRL`.
- Tính `payment_total_brl` từ các dòng payment đã sắp xếp.
- Gán `has_payment` khi có ít nhất một dòng payment.
- Gán `payment_matches_order` khi có payment và độ lệch không vượt quá `0.10 BRL`.
- Gán `valid_split_payment` khi có từ hai dòng payment và tổng payment khớp tổng đơn.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `order_id: str`, `item_total_brl`, `freight_total_brl` |
| Output | `payment_rows`, `payment_total_brl`, `payment_count`, `has_payment`, `is_split_payment`, `payment_matches_order`, `valid_split_payment`, `tolerance_diff_brl` |
| Module phụ thuộc | `data/olist_order_payments_dataset.csv` |
| Module sử dụng output | `CoordinatorAgent`, `PolicyAgent`, `VerifierAgent` |
| Điều kiện lỗi cần xử lý | Thiếu file/cột dữ liệu, `order_id` rỗng, giá trị tiền không hợp lệ, đơn không có payment |

### Cách xác minh

```bash
python -m unittest src.test_payment_agent -v
python src/verify_phase1.py
```

- Kết quả mong đợi: single payment khớp nhưng không phải split; split payment khớp được gắn hợp lệ; độ lệch `0.10` được nhận và `0.11` bị từ chối; thiếu payment không được coi là khớp.
- Kết quả thực tế: 4/4 kiểm thử Payment Agent đạt và kiểm thử hồi quy Phase 1 đạt.
- Artifact/log: `src/test_payment_agent.py` và `logging/trace.jsonl`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Phép cộng `float` có thể sinh sai số nhị phân, không phù hợp để quyết định ngưỡng tiền `0.10 BRL`.
- **Các phương án đã cân nhắc:** dùng `round(float, 2)` hoặc dùng `decimal.Decimal` với quy tắc làm tròn rõ ràng.
- **Phương án đã chọn:** `Decimal` kết hợp `ROUND_HALF_UP`.
- **Lý do:** kết quả tiền có thể tái lập, xử lý chính xác giá trị biên và không phụ thuộc biểu diễn nhị phân của `float`.
- **Bằng chứng:** kiểm thử xác nhận độ lệch `0.10` trả về `True`, còn `0.11` trả về `False`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** đơn không có payment và tổng item/freight bằng `0.0` có thể bị nhận nhầm là đã đối soát thành công vì `0.0 == 0.0`.
- **Nguyên nhân gốc:** điều kiện cũ chỉ kiểm tra độ lệch mà không kiểm tra sự tồn tại của payment.
- **Cách xử lý:** bổ sung `has_payment`; `payment_matches_order` chỉ đúng khi `has_payment` đúng và độ lệch không quá `0.10`.
- **Cách xác minh:** `test_missing_payment_is_not_a_false_match` kiểm tra payment rỗng trả về `payment_matches_order = False` và `valid_split_payment = False`.
- **Điều học được:** cần phân biệt giá trị tổng bằng không với việc thực sự có bản ghi giao dịch.

## 7. Hiểu biết về luồng end-to-end

1. Coordinator đọc input, xác thực schema và lấy `claimed_order_id`.
2. Order & Seller Agent truy xuất đơn, item, seller, đồng thời tính tổng giá sản phẩm và phí vận chuyển.
3. Payment Agent nhận các tổng này để đối soát với dữ liệu thanh toán; Delivery Agent phân tích các mốc vận chuyển.
4. Policy Agent kết hợp findings theo thứ tự ưu tiên `EC_POLICY_V1`, xác định vấn đề, trách nhiệm, tiền hoàn và hành động.
5. Verifier Agent kiểm tra schema, entity, evidence và giới hạn trước khi ghi JSON vào `output/`.
6. Trace ghi lại các lần gọi agent và handoff để kiểm toán luồng multi-agent.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Nguyễn Ngọc Nam
**Ngày xác nhận:** 2026-08-05
