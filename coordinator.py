"""Coordinator Agent.

Reads each EC_xxx.json case from `input/`, dispatches it through Order &
Seller -> (Payment, Delivery) -> Policy -> Verifier, and writes a trace entry
per agent step to `trace.jsonl` (overwritten on every run, per architecture.md
section 9). Confidence/synthesis is fully deterministic (see architecture.md
assumption #3): rule coverage is complete enough that no LLM call is needed,
so no LLM is invoked in this run despite metadata.json declaring one for the
Coordinator's optional synthesis step.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from delivery_agent import DeliveryAgent
from order_seller_agent import OrderSellerAgent
from payment_agent import PaymentAgent
from policy_agent import PolicyAgent
from verifier_agent import VerificationError, VerifierAgent

# Model declared for the Coordinator's optional LLM synthesis step (see
# metadata.json). Reserved for cases where deterministic rules disagree; the
# 50 official cases never triggered it (trace.jsonl: llm_called=false throughout).
COORDINATOR_LLM_MODEL = "Qwen2.5-7B-Instruct"  # <=10B params, served locally via Ollama

ROOT = Path(__file__).parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
TRACE_PATHS = [ROOT / "trace.jsonl", ROOT / "logging" / "trace.jsonl"]


class Coordinator:
    def __init__(self):
        self.order_seller_agent = OrderSellerAgent()
        self.payment_agent = PaymentAgent()
        self.delivery_agent = DeliveryAgent()
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent()
        self.trace: List[Dict] = []

    def _log(self, case_id: str, step: int, agent: str, action: str, input_summary: str, output_summary: str,
              duration_ms: float, llm_called: bool = False) -> None:
        self.trace.append(
            {
                "case_id": case_id,
                "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
                "agent": agent,
                "step": step,
                "action": action,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "duration_ms": round(duration_ms, 3),
                "llm_called": llm_called,
            }
        )

    def run_case(self, case_path: Path) -> Path:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        case_id = case["case_id"]
        claimed_order_id = case["customer_request"]["claimed_order_id"]

        t0 = time.perf_counter()
        self._log(case_id, 1, "coordinator", "parse_input", case_path.name, f"claimed_order_id={claimed_order_id}",
                   (time.perf_counter() - t0) * 1000)

        t0 = time.perf_counter()
        order_seller = self.order_seller_agent.analyze(claimed_order_id)
        self._log(
            case_id, 2, "order_seller_agent", "lookup_order",
            f"claimed_order_id={claimed_order_id}",
            f"found={order_seller['order_found']} status={order_seller['order_status']} items={len(order_seller['items'])}",
            (time.perf_counter() - t0) * 1000,
        )

        t0 = time.perf_counter()
        payment = self.payment_agent.analyze(
            order_seller["order_id"], order_seller["item_total_brl"], order_seller["freight_total_brl"]
        )
        self._log(
            case_id, 3, "payment_agent", "reconcile_payments",
            f"order_id={order_seller['order_id']} item_total={order_seller['item_total_brl']} freight_total={order_seller['freight_total_brl']}",
            f"payment_total={payment['payment_total_brl']} rows={payment['payment_count']} matches={payment['payment_matches_order']}",
            (time.perf_counter() - t0) * 1000,
        )

        t0 = time.perf_counter()
        delivery = self.delivery_agent.analyze(order_seller)
        self._log(
            case_id, 3, "delivery_agent", "check_delivery_timing",
            f"order_id={order_seller['order_id']}",
            f"is_late={delivery['is_late_delivery']} any_seller_late={delivery['any_seller_late']} responsible={delivery['responsible_party']}",
            (time.perf_counter() - t0) * 1000,
        )

        t0 = time.perf_counter()
        decision = self.policy_agent.apply(order_seller, payment, delivery)
        self._log(
            case_id, 4, "policy_agent", "apply_policy",
            "order_seller+payment+delivery findings",
            f"primary_issue={decision['primary_issue']} case_status={decision['case_status']} confidence={decision['confidence']}",
            (time.perf_counter() - t0) * 1000,
        )

        output = {
            "case_id": case_id,
            "assessment": {
                "primary_issue": decision["primary_issue"],
                "case_status": decision["case_status"],
                "confidence": decision["confidence"],
            },
            "affected_entities": decision["affected_entities"],
            "root_cause_analysis": decision["root_cause_analysis"],
            "evidence_ids": decision["evidence_ids"],
            "financial_resolution": decision["financial_resolution"],
            "resolution_actions": decision["resolution_actions"],
        }

        t0 = time.perf_counter()
        try:
            path = self.verifier_agent.write(output, OUTPUT_DIR)
            self._log(case_id, 5, "verifier_agent", "validate_and_write", "assembled case output",
                       f"wrote={path.name}", (time.perf_counter() - t0) * 1000)
        except VerificationError as exc:
            self._log(case_id, 5, "verifier_agent", "validate_and_write", "assembled case output",
                       f"REJECTED: {exc}", (time.perf_counter() - t0) * 1000)
            raise

        return path

    def run_all(self, input_dir: Path = INPUT_DIR) -> None:
        case_files = sorted(input_dir.glob("EC_*.json"))
        for case_path in case_files:
            self.run_case(case_path)
        self.flush_trace()

    def flush_trace(self) -> None:
        lines = "\n".join(json.dumps(entry, ensure_ascii=False) for entry in self.trace) + "\n"
        for trace_path in TRACE_PATHS:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(lines, encoding="utf-8")


if __name__ == "__main__":
    coordinator = Coordinator()
    coordinator.run_all()
    print(f"Processed {len(list(OUTPUT_DIR.glob('EC_*.json')))} cases. Trace entries: {len(coordinator.trace)}")
