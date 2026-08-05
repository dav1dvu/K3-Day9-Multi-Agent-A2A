"""Verifier Agent stub for EC case output validation and file writing."""

import json
from pathlib import Path
from typing import Any, Dict


class VerifierAgent:
    def validate_and_write(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        case_id = case_context.get("case_id")
        if not case_id:
            raise ValueError("case_id missing from final case context")

        required_keys = {
            "case_id",
            "input",
            "order_seller_findings",
            "payment_findings",
            "delivery_findings",
            "policy_decision",
        }
        missing = required_keys - set(case_context.keys())
        if missing:
            raise ValueError(f"Final case context is missing keys: {sorted(missing)}")

        output_path = Path("output") / f"{case_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(case_context, handle, ensure_ascii=False, indent=2)
        return {"output_path": str(output_path), "case_id": case_id}
