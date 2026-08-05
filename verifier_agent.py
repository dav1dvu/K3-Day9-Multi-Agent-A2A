"""Verifier Agent.

Validates a fully-assembled case output against the README section 6 schema
(allowed enums, array limits, evidence ID format, confidence range) before it
is the only agent allowed to write to `output/`. Raises on any hard-gate
violation so a bad case fails loudly instead of being silently submitted.
"""

import json
import re
from pathlib import Path
from typing import Dict, List

PRIMARY_ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}
CASE_STATUSES = {"action_required", "no_action"}
PARTY_TYPES = {"seller", "logistics_provider", "platform"}

EVIDENCE_PATTERNS = {
    "order": re.compile(r"^order:[^:]+$"),
    "item": re.compile(r"^item:[^:]+:\d+$"),
    "payment": re.compile(r"^payment:[^:]+:\d+$"),
    "seller": re.compile(r"^seller:[^:]+$"),
    "policy": re.compile(r"^policy:[A-Z_]+$"),
}

MAX_ENTITY_IDS = 5
MAX_EVIDENCE_IDS = 10
MAX_CAUSES = 3
MAX_PARTIES = 3
MAX_ACTIONS = 5


class VerificationError(Exception):
    pass


class VerifierAgent:
    def validate(self, output: Dict) -> List[str]:
        errors: List[str] = []

        assessment = output.get("assessment", {})
        if assessment.get("primary_issue") not in PRIMARY_ISSUES:
            errors.append(f"invalid primary_issue: {assessment.get('primary_issue')!r}")
        if assessment.get("case_status") not in CASE_STATUSES:
            errors.append(f"invalid case_status: {assessment.get('case_status')!r}")
        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            errors.append(f"confidence out of range [0,1]: {confidence!r}")

        entities = output.get("affected_entities", {})
        for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
            values = entities.get(key, [])
            if len(values) > MAX_ENTITY_IDS:
                errors.append(f"{key} exceeds max {MAX_ENTITY_IDS}: {len(values)}")

        rca = output.get("root_cause_analysis", {})
        causes = rca.get("ranked_causes", [])
        parties = rca.get("responsible_parties", [])
        if len(causes) > MAX_CAUSES:
            errors.append(f"ranked_causes exceeds max {MAX_CAUSES}: {len(causes)}")
        if len(parties) > MAX_PARTIES:
            errors.append(f"responsible_parties exceeds max {MAX_PARTIES}: {len(parties)}")
        for party in parties:
            if party.get("party_type") not in PARTY_TYPES:
                errors.append(f"invalid party_type: {party.get('party_type')!r}")

        evidence_ids = output.get("evidence_ids", [])
        if len(evidence_ids) > MAX_EVIDENCE_IDS:
            errors.append(f"evidence_ids exceeds max {MAX_EVIDENCE_IDS}: {len(evidence_ids)}")
        for eid in evidence_ids:
            prefix = eid.split(":", 1)[0] if ":" in eid else ""
            pattern = EVIDENCE_PATTERNS.get(prefix)
            if pattern is None or not pattern.match(eid):
                errors.append(f"malformed evidence id: {eid!r}")

        actions = output.get("resolution_actions", [])
        if len(actions) > MAX_ACTIONS:
            errors.append(f"resolution_actions exceeds max {MAX_ACTIONS}: {len(actions)}")

        financial = output.get("financial_resolution", {})
        for key in ("item_total_brl", "freight_total_brl", "payment_total_brl", "recommended_refund_brl"):
            value = financial.get(key)
            if not isinstance(value, (int, float)):
                errors.append(f"financial_resolution.{key} is not numeric: {value!r}")
            elif round(value, 2) != value:
                errors.append(f"financial_resolution.{key} not rounded to 2 decimals: {value!r}")

        return errors

    def write(self, output: Dict, output_dir: Path) -> Path:
        errors = self.validate(output)
        if errors:
            raise VerificationError(f"{output.get('case_id')}: " + "; ".join(errors))

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{output['case_id']}.json"
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
