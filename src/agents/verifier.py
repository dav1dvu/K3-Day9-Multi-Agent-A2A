"""Verifier Agent for output validation and file writing."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

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
    def validate(self, output: Dict[str, Any]) -> List[str]:
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

    def validate_and_write(self, case_context: Dict[str, Any]) -> Dict[str, Any]:
        case_id = case_context.get("case_id")
        if not case_id:
            raise ValueError("case_id missing from final case context")

        decision = case_context.get("policy_decision", {})

        # Assemble the official output matching Section 6 schema of README.md
        output = {
            "case_id": case_id,
            "assessment": {
                "primary_issue": decision.get("primary_issue"),
                "case_status": decision.get("case_status"),
                "confidence": decision.get("confidence"),
            },
            "affected_entities": decision.get("affected_entities", {}),
            "root_cause_analysis": decision.get("root_cause_analysis", {}),
            "evidence_ids": decision.get("evidence_ids", []),
            "financial_resolution": decision.get("financial_resolution", {}),
            "resolution_actions": decision.get("resolution_actions", []),
        }

        # Validate
        errors = self.validate(output)
        if errors:
            raise VerificationError(f"{case_id}: " + "; ".join(errors))

        # Write output file
        output_path = Path("output") / f"{case_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(output, handle, ensure_ascii=False, indent=2)

        return {"output_path": str(output_path), "case_id": case_id}
