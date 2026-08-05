# Multi-Agent Architecture — E-commerce Dispute Resolution

> Phiên bản: 1.0 · Ngày tạo: 2026-08-05 · Policy: `EC_POLICY_V1`

---

## 1. Tổng quan

Hệ thống gồm **1 Coordinator Agent** và **5 Sub-Agents** phối hợp xử lý 50 case khiếu nại
thương mại điện tử trên dữ liệu Olist. Mỗi agent phân tích một domain dữ liệu riêng biệt,
sau đó handoff bằng chứng cho Coordinator để tổng hợp kết luận cuối cùng.

### Nguyên tắc thiết kế

- **Separation of concerns**: mỗi agent chỉ truy cập dữ liệu thuộc domain của mình.
- **Evidence-based**: kết luận dựa trên dữ liệu có thể kiểm chứng từ CSV, không suy diễn.
- **Deterministic-first**: ưu tiên xử lý bằng Python xác định; LLM chỉ dùng khi cần
  suy luận ngôn ngữ tự nhiên hoặc tổng hợp phức tạp.
- **Single writer**: chỉ Verifier Agent được ghi file output cuối cùng.

---

## 2. Sơ đồ kiến trúc

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COORDINATOR AGENT                             │
│                  (Điều phối · Tổng hợp · Kết luận)                   │
│                                                                      │
│  Input: case JSON ──► Dispatch ──► Collect ──► Synthesize ──► Output │
└──────┬──────────┬──────────┬──────────┬──────────┬───────────────────┘
       │          │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼─────┐
  │ Order  │ │Payment │ │Delivery│ │ Policy │ │Verifier │
  │&Seller │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent   │
  │ Agent  │ │        │ │        │ │        │ │         │
  └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘
       │          │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼─────┐
  │orders  │ │payments│ │orders  │ │Business│ │All prev │
  │items   │ │items   │ │items   │ │ Rules  │ │ agent   │
  │sellers │ │        │ │        │ │        │ │ outputs │
  └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘
      CSV        CSV        CSV      Python     Validation
```

---

## 3. Danh sách Agent — Vai trò & I/O

### 3.1 Coordinator Agent

| Thuộc tính              | Mô tả                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| **Vai trò**             | Nhận case đầu vào, dispatch cho sub-agents theo thứ tự, thu thập kết quả, tổng hợp output |
| **Input**               | File JSON từ `input/` (case_id, customer_request, claimed_order_id)                        |
| **Output**              | `CaseContext` dict chứa toàn bộ findings → chuyển cho Verifier ghi file                   |
| **Quyền kết luận cuối** | ✅ **Có** — agent duy nhất đưa ra `primary_issue`, `case_status`, `confidence`              |
| **Quyền ghi output**    | ❌ Không — chuyển cho Verifier Agent ghi file                                               |
| **LLM / Python**        | **LLM**: tổng hợp findings thành kết luận khi có mâu thuẫn hoặc cần suy luận. **Python**: orchestration, dispatch, collect |

### 3.2 Order & Seller Agent

| Thuộc tính              | Mô tả                                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------ |
| **Vai trò**             | Truy vấn thông tin đơn hàng, items, seller; xác định trạng thái order và mốc bàn giao của seller      |
| **CSV truy cập**        | `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_sellers_dataset.csv`, `olist_products_dataset.csv` |
| **Input**               | `claimed_order_id` từ Coordinator                                                                      |
| **Output**              | `OrderSellerFindings` dict gồm: order_status, order_timestamps, item_list, seller_info, shipping_limit_dates, item_total, freight_total |
| **Quyền kết luận cuối** | ❌ Không                                                                                                |
| **Quyền ghi output**    | ❌ Không                                                                                                |
| **LLM / Python**        | **Python 100%** — truy vấn CSV bằng pandas, join bảng, trích xuất dữ liệu có cấu trúc                |

### 3.3 Payment Agent

| Thuộc tính              | Mô tả                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| **Vai trò**             | Đối soát payment: tính tổng payment, so khớp với item + freight, phát hiện split payment   |
| **CSV truy cập**        | `olist_order_payments_dataset.csv`                                                         |
| **Input**               | `order_id` + `item_total` + `freight_total` từ Order & Seller Agent (qua Coordinator)      |
| **Output**              | `PaymentFindings` dict gồm: payment_rows, payment_total, payment_count, payment_match (bool), tolerance_check |
| **Quyền kết luận cuối** | ❌ Không                                                                                    |
| **Quyền ghi output**    | ❌ Không                                                                                    |
| **LLM / Python**        | **Python 100%** — tính toán số học, so sánh với tolerance 0.10 BRL, logic xác định         |

### 3.4 Delivery Agent

| Thuộc tính              | Mô tả                                                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Vai trò**             | So sánh thời điểm giao thực tế với hạn giao ước tính; phân biệt trễ do seller hay do logistics                            |
| **CSV truy cập**        | `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`                                                                |
| **Input**               | `order_id` + `shipping_limit_dates` từ Order & Seller Agent (qua Coordinator)                                              |
| **Output**              | `DeliveryFindings` dict gồm: is_late (bool), delivered_date, estimated_date, carrier_date, seller_late (bool), responsible_party |
| **Quyền kết luận cuối** | ❌ Không                                                                                                                    |
| **Quyền ghi output**    | ❌ Không                                                                                                                    |
| **LLM / Python**        | **Python 100%** — so sánh timestamp, logic xác định seller vs logistics                                                    |

### 3.5 Policy Agent

| Thuộc tính              | Mô tả                                                                                                         |
| ----------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Vai trò**             | Áp dụng bảng quy tắc `EC_POLICY_V1` để xác định primary_issue, root_cause_code, responsible_party, refund và action |
| **Input**               | Toàn bộ findings từ Order & Seller, Payment, Delivery Agents (qua Coordinator)                                 |
| **Output**              | `PolicyDecision` dict gồm: primary_issue, root_cause_code, responsible_parties, recommended_refund_brl, resolution_actions, case_status |
| **Quyền kết luận cuối** | ❌ Không — đề xuất decision, Coordinator xác nhận                                                               |
| **Quyền ghi output**    | ❌ Không                                                                                                        |
| **LLM / Python**        | **Python 100%** — bảng điều kiện if/elif xác định, không cần suy luận ngôn ngữ                                 |

### 3.6 Verifier Agent

| Thuộc tính              | Mô tả                                                                                                                       |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Vai trò**             | Kiểm tra tính hợp lệ của output: schema validation, evidence ID format, số tiền consistency, giới hạn array; ghi file cuối |
| **Input**               | `CaseContext` hoàn chỉnh từ Coordinator (đã có PolicyDecision)                                                               |
| **Output**              | File JSON hợp lệ ghi vào `output/EC_XXX.json`                                                                               |
| **Quyền kết luận cuối** | ❌ Không — chỉ validate, không thay đổi kết luận                                                                             |
| **Quyền ghi output**    | ✅ **Có** — agent duy nhất được phép ghi file vào `output/`                                                                  |
| **LLM / Python**        | **Python 100%** — schema check, format check, range check, file I/O                                                         |

---

## 4. Luồng dữ liệu & Thứ tự Handoff

```
Step 1  ┌───────────────┐
        │  Coordinator  │  Đọc input/EC_XXX.json
        │  parse case   │  Trích claimed_order_id
        └──────┬────────┘
               │
Step 2  ┌──────▼────────┐
        │ Order & Seller│  Lookup order_id → orders, items, sellers
        │    Agent      │  Return: OrderSellerFindings
        └──────┬────────┘
               │
        ┌──────▼────────────────────────────────┐
        │          Coordinator (collect)         │
        │  Nhận OrderSellerFindings              │
        │  Dispatch song song 2 agent tiếp theo │
        └──────┬────────────┬───────────────────┘
               │            │
Step 3  ┌──────▼───┐  ┌────▼──────┐
        │ Payment  │  │ Delivery  │   ← Chạy song song (parallel)
        │  Agent   │  │  Agent    │
        └──────┬───┘  └────┬──────┘
               │            │
        ┌──────▼────────────▼───────────────────┐
        │          Coordinator (collect)         │
        │  Nhận PaymentFindings + DeliveryFndgs  │
        └──────────────┬────────────────────────┘
                       │
Step 4  ┌──────────────▼────────────────────────┐
        │          Policy Agent                  │
        │  Input: ALL findings                   │
        │  Output: PolicyDecision                │
        └──────────────┬────────────────────────┘
                       │
Step 5  ┌──────────────▼────────────────────────┐
        │          Coordinator (synthesize)      │
        │  Tổng hợp → CaseContext final          │
        │  Gán confidence, xác nhận kết luận     │
        │  [LLM nếu cần suy luận phức tạp]       │
        └──────────────┬────────────────────────┘
                       │
Step 6  ┌──────────────▼────────────────────────┐
        │          Verifier Agent                │
        │  Validate schema + evidence IDs        │
        │  Ghi output/EC_XXX.json                │
        └───────────────────────────────────────┘
```

### Giải thích thứ tự

| Step | Agent(s)              | Lý do thứ tự                                                       |
| ---- | --------------------- | ------------------------------------------------------------------- |
| 1    | Coordinator           | Parse input, khởi tạo context                                      |
| 2    | Order & Seller        | Phải chạy trước vì Payment và Delivery cần item_total, freight_total, shipping_limit_dates |
| 3    | Payment + Delivery    | Song song — độc lập nhau, cùng phụ thuộc output Step 2              |
| 4    | Policy                | Cần ALL findings để áp dụng bảng quy tắc                           |
| 5    | Coordinator           | Tổng hợp cuối, xác nhận hoặc override nếu mâu thuẫn                |
| 6    | Verifier              | Cuối cùng — validate và ghi file                                    |

---

## 5. Quyền hạn tóm tắt

| Agent            | Đọc CSV | Đưa kết luận cuối | Ghi output file | Dùng LLM |
| ---------------- | ------- | ------------------ | --------------- | -------- |
| Coordinator      | ❌       | ✅                  | ❌               | ✅ (khi cần) |
| Order & Seller   | ✅       | ❌                  | ❌               | ❌        |
| Payment          | ✅       | ❌                  | ❌               | ❌        |
| Delivery         | ✅       | ❌                  | ❌               | ❌        |
| Policy           | ❌       | ❌                  | ❌               | ❌        |
| Verifier         | ❌       | ❌                  | ✅               | ❌        |

---

## 6. Vị trí LLM vs Python xác định

### LLM tham gia (Qwen2.5-7B-Instruct)

| Vị trí                        | Mục đích                                                             | Khi nào kích hoạt                             |
| ----------------------------- | -------------------------------------------------------------------- | --------------------------------------------- |
| Coordinator — synthesize step | Tổng hợp findings từ nhiều agent, suy luận khi có mâu thuẫn dữ liệu | Khi logic xác định không đủ phân loại rõ ràng |
| Coordinator — confidence      | Đánh giá mức độ tin cậy của kết luận                                 | Mọi case (gán confidence score)               |

### Python xác định (không LLM)

| Module                   | Xử lý                                                                  |
| ------------------------ | ----------------------------------------------------------------------- |
| Order & Seller Agent     | Pandas query, join CSV, trích xuất timestamps, tính item/freight totals |
| Payment Agent            | Tổng payment, so sánh tolerance 0.10 BRL, đếm payment rows             |
| Delivery Agent           | So sánh timestamps, phân loại seller_late vs carrier_late               |
| Policy Agent             | Bảng if/elif rules theo EC_POLICY_V1                                    |
| Verifier Agent           | JSON schema validation, evidence ID regex, giới hạn array, ghi file    |
| Coordinator — parse/dispatch | Đọc JSON input, dispatch, collect findings                          |

---

## 7. Data Contracts giữa các Agent

### 7.1 OrderSellerFindings

```python
{
    "order_id": str,
    "order_status": str,                          # delivered, canceled, unavailable, ...
    "order_purchase_timestamp": str,
    "order_approved_at": str | None,
    "order_delivered_carrier_date": str | None,
    "order_delivered_customer_date": str | None,
    "order_estimated_delivery_date": str,
    "items": [
        {
            "order_item_id": int,
            "product_id": str,
            "seller_id": str,
            "shipping_limit_date": str,
            "price": float,
            "freight_value": float
        }
    ],
    "item_total_brl": float,                      # sum(price)
    "freight_total_brl": float,                   # sum(freight_value)
    "seller_ids": [str],
    "customer_id": str
}
```

### 7.2 PaymentFindings

```python
{
    "order_id": str,
    "payment_rows": [
        {
            "payment_sequential": int,
            "payment_type": str,
            "payment_installments": int,
            "payment_value": float
        }
    ],
    "payment_total_brl": float,                   # sum(payment_value)
    "payment_count": int,
    "is_split_payment": bool,                     # count >= 2
    "payment_matches_order": bool,                # |payment_total - (item_total + freight_total)| <= 0.10
    "tolerance_diff_brl": float
}
```

### 7.3 DeliveryFindings

```python
{
    "order_id": str,
    "order_estimated_delivery_date": str,
    "order_delivered_customer_date": str | None,
    "order_delivered_carrier_date": str | None,
    "is_late_delivery": bool,                     # delivered > estimated
    "seller_shipping_limits": [
        {
            "order_item_id": int,
            "seller_id": str,
            "shipping_limit_date": str,
            "carrier_pickup_date": str | None,
            "seller_handoff_late": bool           # carrier_date > shipping_limit_date
        }
    ],
    "any_seller_late": bool,
    "responsible_party": str | None               # "seller" | "logistics_provider" | None
}
```

### 7.4 PolicyDecision

```python
{
    "primary_issue": str,                         # e.g. "late_delivery_seller"
    "case_status": str,                           # "action_required" | "no_action"
    "root_cause_codes": [
        {"cause_code": str, "rank": int}
    ],
    "responsible_parties": [
        {"party_type": str, "party_id": str}
    ],
    "recommended_refund_brl": float,
    "resolution_actions": [str],
    "evidence_ids": [str]
}
```

---

## 8. Assumptions

> Các assumption dưới đây được ghi nhận vì chưa có source code thực tế tại thời điểm viết
> kiến trúc. Khi implement, cần xác minh và điều chỉnh nếu cần.

1. **Naming convention**: tên 5 sub-agents tuân theo gợi ý trong README section 7 —
   `Order & Seller Agent`, `Payment Agent`, `Delivery Agent`, `Policy Agent`, `Verifier Agent`.

2. **Song song Step 3**: Payment Agent và Delivery Agent có thể chạy song song vì output
   của chúng không phụ thuộc lẫn nhau. Implementation có thể dùng `asyncio` hoặc
   `concurrent.futures`.

3. **LLM usage tối thiểu**: do bài toán chủ yếu là logic xác định trên dữ liệu có cấu trúc,
   LLM chỉ được dùng ở Coordinator cho bước tổng hợp/confidence. Nếu pipeline xác định đủ
   tốt, LLM call có thể được bypass hoàn toàn cho performance.

4. **Model ≤ 10B**: sử dụng `Qwen2.5-7B-Instruct` (7.62B params) chạy local qua Ollama
   hoặc qua API tương đương. Không sử dụng model lớn hơn.

5. **Single-pass pipeline**: mỗi case chạy qua pipeline 1 lần, không có retry loop giữa
   các agent. Verifier chỉ validate, không gửi ngược lại Coordinator để sửa.

6. **metadata.json**: đặt tại `logging/metadata.json` theo cấu trúc repo hiện tại.
   Bản sao cũng đặt tại root `metadata.json` nếu cần.

---

## 9. Trace & Logging

Mỗi lần chạy pipeline ghi trace vào `logging/trace.jsonl` với format:

```json
{
  "case_id": "EC_001",
  "timestamp": "2026-08-05T09:30:00+07:00",
  "agent": "coordinator",
  "step": 1,
  "action": "parse_input",
  "input_summary": "...",
  "output_summary": "...",
  "duration_ms": 45,
  "llm_called": false
}
```

Mỗi agent step tạo một trace entry. Trace file chỉ giữ lượt chạy mới nhất (overwrite).
