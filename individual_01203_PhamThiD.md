# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Phạm Thị D |
| MSSV            | 202601203 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Policy Agent & Verifier QA Lead |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Policy & Verifier Agents | `src/policy_verifier_agent.py`, `src/agents/verifier.py`, `src/validate_output.py` | Tất cả findings từ sub-agents | Verified output JSON files & Validation report | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Đánh giá Policy & Verification Schema | `src/agents/verifier.py`, `src/validate_output.py` | 50/50 file JSON pass 100% kiểm thử | `python src/validate_output.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Áp dụng ma trận ưu tiên `EC_POLICY_V1` để ra quyết định xử lý (Hủy đơn/Thiếu hàng > Giao trễ do Seller > Giao trễ do Carrier > Split payment hợp lệ > Không hỗ trợ giao trễ).
2. Thẩm định output JSON: kiểm tra giới hạn mảng (max 5 entities, 10 evidence, 3 causes, 3 parties, 5 actions), định dạng Evidence ID chuẩn (`order:`, `item:`, `payment:`, `seller:`, `policy:`).

### Cách triển khai
- Thẩm định bằng Regex `EVIDENCE_PATTERNS` để check định dạng của từng loại Evidence ID.
- `VerifierAgent` đóng vai trò **Single Writer** duy nhất để lắp ráp dữ liệu từ `CaseContext` và ghi file ra thư mục `output/EC_XXX.json`.
- Viết script độc lập `src/validate_output.py` để kiểm tra chéo bằng chứng xuất hiện trong CSV Olist gốc và đối chiếu recommended refund.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | Full Case Context từ Coordinator |
| Output | File JSON đạt chuẩn schema trong `output/` |
| Module phụ thuộc | Tất cả Sub-Agents |
| Module sử dụng output | Giám khảo chấm điểm bài lab |

### Cách xác minh

```bash
python src/validate_output.py
```

- **Kết quả mong đợi:** 50/50 cases output hợp lệ, in ra: `VALIDATION PASSED — 50/50 cases OK.`
- **Kết quả thực tế:** Cả 50/50 files đều PASS kiểm thử chéo và schema validation.
- **Artifact/log:** `src/validate_output.py`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Giới hạn mảng Evidence IDs (tối đa 10 phần tử).
- **Các phương án đã cân nhắc:**
  1. Giữ nguyên tất cả Evidence IDs do các agent tạo ra mà không có bộ lọc.
  2. Gom nhóm, loại bỏ trùng lặp và cắt danh sách tối đa 10 phần tử theo ngân sách tối đa (`budget`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Tránh việc số lượng bằng chứng vượt quá giới hạn và vi phạm quy định schema (Hard gate rule nhận 0 điểm). Việc phân bổ budget bảo đảm giữ lại bằng chứng quan trọng nhất (như policy rule và order ID) và chỉ làm giàu thêm bằng các item/payment IDs tương ứng trong giới hạn cho phép.
- **Bằng chứng quyết định phù hợp:** 50/50 output cases đều đạt điểm tuyệt đối về evidence IDs trên hệ thống validator độc lập.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Thừa evidence ID sản phẩm hoặc người bán khi đơn hàng không có dòng sản phẩm (item_ids và seller_ids rỗng, ví dụ như ở case `unavailable`).
- **Cách xử lý:** Kiểm tra sự tồn tại của item và seller trước khi sinh bằng chứng `item:` và `seller:` trong logic xây dựng evidence của Policy Agent.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử chéo, các đơn hàng không có item row trả về `item_ids` và `seller_ids` rỗng đúng quy định mà không bị sinh dư bằng chứng.

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

**Họ và tên:** Phạm Thị D
**Ngày xác nhận:** 2026-08-05
