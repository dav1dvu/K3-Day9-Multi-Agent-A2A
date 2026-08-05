# Kế Hoạch Triển Khai Dự Án Multi-Agent E-commerce Dispute Resolution (Nhóm 5 Thành Viên)

Dự án yêu cầu xây dựng hệ thống **Multi-Agent** điều tra 50 yêu cầu hỗ trợ của khách hàng trên dữ liệu Olist (`data/`), áp dụng quy tắc nghiệp vụ `EC_POLICY_V1`, xuất file kết quả JSON đạt chuẩn schema, tạo trace log và báo cáo cá nhân.

---

## 1. Phân Công Vai Trò Cho 5 Thành Viên (Roles & Responsibilities)

| Thành viên | Vai trò | Nhiệm vụ chính phụ trách | Deliverables / Files phụ trách |
| :--- | :--- | :--- | :--- |
| **Thành viên 1** | **Team Leader & Architect** | - Thiết kế kiến trúc tổng thể Multi-Agent.<br>- Xây dựng **Coordinator Agent** (điều phối luồng handoff, tổng hợp kết quả).<br>- Quản lý `trace.jsonl` và `metadata.json` (model <= 10B). | - `architecture.md`<br>- `metadata.json`<br>- `coordinator_agent.py` / orchestrator<br>- `trace.jsonl` |
| **Thành viên 2** | **Order & Seller Agent Lead** | - Xây dựng **Order & Seller Agent**.<br>- Xử lý truy vấn orders, items, sellers.<br>- Xác định tình trạng hủy đơn (`canceled`), hết hàng (`unavailable`) và mốc bàn giao hàng (`order_delivered_carrier_date` vs `shipping_limit_date`). | - `order_seller_agent.py`<br>- logic đối soát Order & Seller<br>- báo cáo cá nhân `individual_*.md` |
| **Thành viên 3** | **Payment & Finance Agent Lead** | - Xây dựng **Payment Agent**.<br>- Bảng tính toán tài chính: `item_total_brl`, `freight_total_brl`, `payment_total_brl`.<br>- Kiểm tra split payment (sai số 0.10 BRL), đề xuất số tiền refund (`recommended_refund_brl`). | - `payment_agent.py`<br>- logic tính tiền & refund<br>- báo cáo cá nhân `individual_*.md` |
| **Thành viên 4** | **Logistics & Delivery Agent Lead** | - Xây dựng **Delivery Agent**.<br>- So sánh `order_delivered_customer_date` vs `order_estimated_delivery_date`.<br>- Phân định nguyên nhân chậm trễ (`SELLER_HANDOFF_AFTER_LIMIT` vs `CARRIER_DELIVERED_AFTER_ESTIMATE`). | - `delivery_agent.py`<br>- logic kiểm tra vận chuyển<br>- báo cáo cá nhân `individual_*.md` |
| **Thành viên 5** | **Policy & Verifier Agent (QA Lead)** | - Xây dựng **Policy Agent** & **Verifier Agent**.<br>- Kiểm tra Evidence IDs đúng chuẩn (`order:`, `item:`, `payment:`, `seller:`, `policy:`).<br>- Validate output schema, giới hạn mảng (max 5 entities, 10 evidence, 3 causes, 3 parties, 5 actions), đóng gói ZIP. | - `policy_verifier_agent.py`<br>- script validate schema & ZIP<br>- báo cáo cá nhân `individual_*.md` |

---

## 2. Kế Hoạch Thực Hiện Chi Tiết Theo Phân Đoạn (Phase-by-Phase Timeline)

### Phase 1: Phân Tích Yêu Cầu, Chuẩn Bị Dữ Liệu & Thiết Kế Kiến Trúc (09:30 - 10:00)

- **Mục tiêu**: Thống nhất quy ước dữ liệu, cấu trúc thư mục, schema hợp lệ và luồng giao tiếp handoff giữa 5 Agent.
- **Nhiệm vụ từng thành viên**:
  - **Thành viên 1**: Viết phác thảo `architecture.md` mô tả 5 Sub-Agents và Coordinator Agent. Khai báo model (<= 10B parameters, ví dụ: Qwen2.5-7B/Llama-3.1-8B local hoặc API) vào `metadata.json`.
  - **Thành viên 2**: Khảo sát 9 file CSV trong `data/` (`orders.csv`, `order_items.csv`, `sellers.csv`). Định nghĩa hàm helper load & query order/seller nhanh theo `claimed_order_id`.
  - **Thành viên 3**: Khảo sát `order_payments.csv`. Viết helper tính tổng tiền thanh toán (`payment_value`), số lượng dòng payment, và công thức kiểm tra sai số 0.10 BRL.
  - **Thành viên 4**: Khảo sát các mốc thời gian (`shipping_limit_date`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`).
  - **Thành viên 5**: Tổng hợp bảng ma trận quy tắc nghiệp vụ `EC_POLICY_V1` (6 primary issues) và dựng hàm kiểm tra định dạng chuẩn của Evidence ID.

---

### Phase 2: Phát Triển Chi Tiết Các Sub-Agent & Module Phụ Trách (10:00 - 11:00)

- **Mục tiêu**: Hoàn thiện các agent đơn lẻ có khả năng phân tích chính xác từng khía cạnh dữ liệu.
- **Nhiệm vụ từng thành viên**:
  - **Thành viên 1**: Xây dựng khung `CoordinatorAgent` nhận JSON input (`EC_xxx.json`), phân phối công việc tới các Sub-Agent, ghi log trace vào `trace.jsonl`.
  - **Thành viên 2**: Phát triển `OrderSellerAgent` để kiểm tra:
    - Nếu `order_status` là `canceled` hoặc `unavailable` -> gắn tag tương ứng.
    - So sánh `order_delivered_carrier_date` với `shipping_limit_date` của từng item.
  - **Thành viên 3**: Phát triển `PaymentAgent` để kiểm tra:
    - Tổng `payment_value` vs `(item_total + freight_total)`.
    - Phân tích `valid_split_payment` (khi có >= 2 payment row và tổng khớp trong sai số 0.10 BRL).
  - **Thành viên 4**: Phát triển `DeliveryAgent` để kiểm tra:
    - Đơn có bị giao muộn không (`order_delivered_customer_date > order_estimated_delivery_date`).
    - Nếu muộn: carrier nhận trễ -> trách nhiệm `seller`; carrier nhận đúng hạn nhưng giao trễ -> trách nhiệm `logistics_provider`.
  - **Thành viên 5**: Phát triển `PolicyVerifierAgent`:
    - Áp dụng ma trận ưu tiên (Hủy đơn/Thiếu hàng > Giao trễ do Seller > Giao trễ do Carrier > Split payment hợp lệ > Không hỗ trợ giao trễ).
    - Tạo danh sách Evidence IDs hợp lệ (Ví dụ: `item:abc123:1`, `policy:SELLER_HANDOFF_AFTER_LIMIT`).

---

### Phase 3: Tích Hợp Multi-Agent Pipeline & Chạy 50 Cases (11:00 - 11:45)

- **Mục tiêu**: Chạy thử nghiệm end-to-end trên toàn bộ 50 case (`EC_001.json` - `EC_050.json`), xuất kết quả ra thư mục `output/`.
- **Nhiệm vụ từng thành viên**:
  - **Thành viên 1**: Cho chạy pipeline chính xử lý 50 case, theo dõi tiến trình và ghi nhận file `trace.jsonl`.
  - **Thành viên 2 & 3**: Phối hợp kiểm tra các trường hợp đơn bị thiếu item (`item_ids` và `seller_ids` rỗng, tiền item/freight = `0.0`).
  - **Thành viên 4**: Kiểm tra tính chính xác của các case giao đúng hạn (`unsupported_late_claim` -> `case_status: no_action`).
  - **Thành viên 5**: Viết script tự động kiểm tra (validator) trên 50 file output trong `output/`:
    - Kiểm tra schema JSON đầy đủ các trường.
    - Kiểm tra số lượng phần tử không vượt quá giới hạn (max 5 entity IDs, 10 evidence IDs, 3 root causes, 3 responsible parties, 5 actions).
    - Kiểm tra `confidence` nằm trong khoảng `[0, 1]`.

---

### Phase 4: Đánh Giá Hard Gates, Tối Ưu Điểm Số & Khắc Phục Lỗi (11:45 - 12:15)

- **Mục tiêu**: Rà soát kỹ 6 thành phần tính điểm để đạt điểm tối đa (Primary issue 20%, Affected entities 20%, Root cause 15%, Evidence 15%, Financial 20%, Actions 10%).
- **Nhiệm vụ từng thành viên**:
  - **Thành viên 1**: Rà soát `architecture.md` (đã vẽ đúng sơ đồ agent, vai trò, quyền truy cập dữ liệu và luồng handoff chưa).
  - **Thành viên 2**: Kiểm tra xem evidence `seller:<seller_id>` và `item:<order_id>:<item_seq>` có khớp 100% dữ liệu gốc Olist không.
  - **Thành viên 3**: Rà soát các phép làm tròn tài chính (làm tròn đúng 2 chữ số thập phân, tiền hoàn `recommended_refund_brl` chính xác theo loại lỗi).
  - **Thành viên 4**: Rà soát lại việc chọn `party_type` (`seller`, `logistics_provider`, `platform`) và `party_id` (`seller_id`, `LOGISTICS_PROVIDER`, `OLIST_PLATFORM`).
  - **Thành viên 5**: Đảm bảo không file nào bị lỗi Hard gate (nhận 0 điểm).

---

### Phase 5: Đóng Gói Artifacts & Hoàn Thiện Nộp Bài (12:15 - 12:30)

- **Mục tiêu**: Hoàn tất nộp bài đúng quy định trước Checkpoint 3 (12:30 - 13:00).
- **Nhiệm vụ từng thành viên**:
  - **Cả 5 thành viên**: Mỗi người tự điền hoàn thiện báo cáo cá nhân của mình dựa trên template `individual_5SoCuoiMHV_HoVaTen.md` (đổi tên file thành `individual_<5SoCuoiMHV>_<HoVaTen>.md`).
  - **Thành viên 5**: Đóng gói folder `output/` thành file ZIP chứa duy nhất 50 file JSON (`EC_001.json` - `EC_050.json`), không chứa file lạ hay thư mục con.
  - **Thành viên 1**: Kiểm tra repo nhóm đã có đủ các file bắt buộc:
    1. `architecture.md`
    2. `metadata.json`
    3. `trace.jsonl`
    4. 5 file báo cáo cá nhân `individual_*.md`
    5. Source code (không có `.env`, không có API key cứng).
  - **Thành viên 1**: Thực hiện `git commit` và `git push` toàn bộ codebase lên repository nhóm, sau đó gửi file zip `output.zip` nộp bài.

---

## 3. Kế Hoạch Xác Minh & Kiểm Thử (Verification Plan)

### Kiểm Tra Tự Động (Automated Checks)
1. **Validator Script (`validate_output.py`)**:
   - Kiểm tra tồn tại đủ 50 file JSON trong `output/`.
   - Validate JSON Schema đối với từng file.
   - Kiểm tra định dạng Regex cho Evidence IDs (`order:.*`, `item:.*:.*`, `payment:.*:.*`, `seller:.*`, `policy:.*`).
2. **Audit Trace Log**:
   - Kiểm tra `trace.jsonl` đảm bảo ghi nhận thực sự luồng handoff và trao đổi giữa các Agent trong 50 case.

### Kiểm Tra Thủ Công (Manual Checks)
1. Rà soát ngẫu nhiên 5 case (ví dụ `EC_001`, `EC_010`, `EC_025`, `EC_040`, `EC_050`) xem kết quả primary issue và tài chính có hợp lý với mô tả và dữ liệu CSV không.
2. Kiểm tra các file báo cáo cá nhân không bị trùng lặp nguyên văn và điền đúng thông tin cá nhân.
