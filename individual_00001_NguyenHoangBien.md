# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Hoàng Biên |
| MSSV            | 00001 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Team Leader & Architect |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Coordinator Agent & Pipeline Orchestration | `src/agents/coordinator.py`, `src/run_pipeline.py`, `architecture.md`, `metadata.json` | Dữ liệu đầu vào case `EC_XXX.json` | Luồng chạy tuần tự qua các Sub-Agents, ghi trace logs | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Thiết kế kiến trúc Multi-Agent | [architecture.md](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/architecture.md) | Sơ đồ luồng, phân rã domain sub-agents sạch sẽ | Đánh giá chéo từ đội ngũ phát triển |
| Triển khai Coordinator Agent | [src/agents/coordinator.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/agents/coordinator.py) | Điều phối state handoffs qua 5 agents, tự động gọi LLM | Chạy unit tests `pytest src/tests_coordinator.py` |
| Triển khai Pipeline Runner | [src/run_pipeline.py](file:///c:/CODE/AITHUCCHIEN/LABS/DAY09_2A202601199_VuNguyenQuocDat/src/run_pipeline.py) | Chạy tự động và ghi nhận trace logs cho 50 cases | `python src/run_pipeline.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Thiết kế luồng luân chuyển dữ liệu (state handoff) giữa các Agent độc lập để tránh truy cập chéo dữ liệu thô (đảm bảo tính bảo mật và phân rã chức năng).
2. Tích hợp gọi mô hình ngôn ngữ lớn (LLM) để xác định tính nhất quán và tính điểm tin cậy (`confidence`) dựa trên kết quả trung gian, sử dụng kỹ thuật xoay tua (rotate) giữa 2 model đám mây: `gemma-4-31b-it` và `gemma-4-26b-a4b-it` bằng API Key.
3. Đồng bộ hóa trace log chuẩn xác định dạng JSONL tại cả `trace.jsonl` và `logging/trace.jsonl`.

### Cách triển khai
- Trực tiếp lập trình `CoordinatorAgent` để quản lý `CaseState`.
- Lập trình hàm `_evaluate_with_llm` sử dụng thư viện `requests` thực hiện POST API trực tiếp đến Google AI Studio, xoay tua model qua phép chia dư của số thứ tự đơn hàng (đơn lẻ gọi `gemma-4-31b-it`, đơn chẵn gọi `gemma-4-26b-a4b-it`).
- Thiết lập cơ chế ghi dấu vết qua `_write_trace`.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | JSON case gốc từ thư mục `input/` |
| Output | `CaseState` chứa thông tin từ sub-agents, trace log tại `trace.jsonl` |

### Cách xác minh
```bash
pytest src/tests_coordinator.py
python src/run_pipeline.py
```
- **Kết quả mong đợi:** Toàn bộ 4 test cases unit test đạt màu xanh, chạy pipeline thành công 50/50 cases mà không bị lỗi mạng hoặc lỗi mô hình.
- **Kết quả thực tế:** Test suite đạt 100% PASS, 50 case output được tạo và trace ghi nhận chi tiết mô hình xoay tua.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tích hợp gọi mô hình ngôn ngữ lớn ngoài local nhưng môi trường cài đặt thiếu thư viện `google-generativeai`.
- **Các phương án đã cân nhắc:**
  1. Cố gắng cài thêm package `google-generativeai` thông qua pip (nguy cơ lỗi môi trường, tốn thời gian cài đặt).
  2. Sử dụng thư viện `requests` có sẵn để tạo các POST request HTTP trực tiếp đến API endpoint của Google AI Studio (`generativelanguage.googleapis.com`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đây là giải pháp cực kỳ gọn nhẹ, độc lập, không phụ thuộc thư viện ngoài, hoạt động trơn tru trên mọi nền tảng Python cài sẵn `requests`, đảm bảo tốc độ phản hồi nhanh và khả năng tùy chỉnh body payload chi tiết (chứa prompt và parse thoughts).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy kiểm thử pytest song song với pipeline nền, kết quả kiểm thử unit test bị lỗi đếm số lượng bản ghi `agent_started` tăng vọt do hai tiến trình cùng ghi đè/nối thêm vào chung file `logging/trace.jsonl`.
- **Cách xử lý:** Tách biệt rõ sự kiện ghi vết của LLM thành `llm_started` và `llm_completed` thay vì dùng chung sự kiện `agent_started` của Sub-Agent, đồng thời cấu hình cơ chế xóa file vết cũ trước khi chạy pipeline.
- **Cách xác minh sau khi sửa:** Chạy pytest độc lập và song song đều pass 100% không bị xung đột bản ghi vết.

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

**Họ và tên:** Nguyễn Hoàng Biên
**Ngày xác nhận:** 2026-08-05
