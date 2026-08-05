# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Vũ Tú Quỳnh |
| MSSV            | 01239 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Policy & Verifier Agent (QA Lead) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Policy & Verifier Agent / QA Validation | `src/policy_verifier_agent.py`, `src/agents/verifier.py`, `src/validate_output.py` | Kết quả phân tích từ các Sub-Agents | Quyết định xử lý và file JSON output đạt chuẩn schema | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Lập ma trận luật xử lý khiếu nại | [src/policy_verifier_agent.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/policy_verifier_agent.py) | Module gán nhãn vấn đề, xác định số tiền hoàn trả | Chạy `python src/run_pipeline.py` |
| Thẩm định dữ liệu đầu ra | [src/agents/verifier.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/agents/verifier.py) | Trình xác minh JSON schema và ghi file output | Chạy `python src/run_pipeline.py` |
| Xây dựng hệ thống kiểm thử QA độc lập | [src/validate_output.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/validate_output.py) | Script tự động đối soát chéo 50 file output với dữ liệu gốc Olist | `python src/validate_output.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Áp dụng chuẩn xác thứ tự ưu tiên của chính sách `EC_POLICY_V1` khi phân loại vấn đề (Canceled/Unavailable > Late Delivery Seller > Late Delivery Logistics > Valid Split Payment > Unsupported Late Claim).
2. Bảo đảm file đầu ra hoàn toàn không vi phạm các "Hard Gates" của cuộc thi (số lượng thực thể tối đa 5, số lượng bằng chứng tối đa 10, định dạng bằng chứng chuẩn, làm tròn đúng 2 chữ số thập phân).
3. Viết script kiểm thử độc lập đối soát toàn bộ 50 file kết quả đầu ra với dữ liệu thô CSV để phát hiện các bằng chứng "ma" (không tồn tại trong cơ sở dữ liệu gốc).

### Cách triển khai
- Viết logic `decide` của PolicyAgent dựa trên kết quả của các sub-agents.
- Viết `validate_and_write` lắp ráp thông tin vào schema yêu cầu và thực hiện kiểm tra regex, độ dài mảng dữ liệu.
- Phát triển độc lập `src/validate_output.py` sử dụng pandas để đối chiếu sự khớp dữ liệu trực tiếp từ CSV gốc.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | Dữ liệu `CaseContext` chứa thông tin từ các Sub-Agents |
| Output | File JSON lưu tại `output/EC_XXX.json` chuẩn hóa |

### Cách xác minh
```bash
python src/validate_output.py
```
- **Kết quả mong đợi:** 50/50 file JSON vượt qua tất cả các kiểm tra nghiêm ngặt của schema và được chứng thực trùng khớp 100% với dữ liệu thô Olist.
- **Kết quả thực tế:** Validator thông báo thành công: `VALIDATION PASSED — 50/50 cases OK.`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Hạn mức số lượng bằng chứng (Evidence IDs) tối đa được gửi lên hệ thống chỉ là 10. Khi đơn hàng có quá nhiều sản phẩm và giao dịch thanh toán, số lượng bằng chứng tích lũy từ các Sub-Agents có thể vượt quá 10, gây lỗi loại trực tiếp (nhận 0 điểm).
- **Các phương án đã cân nhắc:**
  1. Giữ nguyên toàn bộ bằng chứng (nguy cơ lỗi Hard Gate).
  2. Xây dựng cơ chế phân chia ngân sách (budget) bằng chứng: Ưu tiên bằng chứng quan trọng nhất (như order_id và policy_code), sau đó điền thêm các item và payment trong giới hạn còn lại.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo hệ thống luôn hoạt động an toàn dưới giới hạn 10 bản ghi bằng chứng của schema, đồng thời vẫn cung cấp đầy đủ thông tin thiết yếu nhất để xác minh lỗi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi gặp đơn hàng không tìm thấy thông tin sản phẩm (ví dụ trạng thái `unavailable` hoặc `canceled` sớm), hệ thống cố gắng tạo bằng chứng `item:` và `seller:` dẫn tới lỗi dữ liệu rỗng.
- **Cách xử lý:** Bổ sung điều kiện kiểm tra tính tồn tại của các trường thông tin trước khi xây dựng bằng chứng. Nếu không tìm thấy, bỏ qua việc sinh bằng chứng tương ứng để tránh rác dữ liệu.
- **Cách xác minh sau khi sửa:** Chạy lại validator độc lập, các đơn hàng đặc biệt đã pass và không còn sinh bằng chứng không hợp lệ.

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

**Họ và tên:** Vũ Tú Quỳnh
**Ngày xác nhận:** 2026-08-05
