"""Policy/Verifier Agent - Phase 1."""

import re

ISSUES = {
    "canceled_order_paid",
    "unavailable_order_paid",
    "late_delivery_seller",
    "late_delivery_logistics",
    "valid_split_payment",
    "unsupported_late_claim",
}

CAUSES = {
    "SELLER_HANDOFF_AFTER_LIMIT",
    "CARRIER_DELIVERED_AFTER_ESTIMATE",
    "ORDER_CANCELED_AFTER_PAYMENT",
    "ORDER_UNAVAILABLE_AFTER_PAYMENT",
    "MULTIPLE_PAYMENTS_RECONCILED",
    "DELIVERY_WITHIN_ESTIMATE",
}

EVIDENCE_RE = re.compile(
    r"^(order:[^:]+|item:[^:]+:\d+|payment:[^:]+:\d+|seller:[^:]+|policy:[A-Z_]+)$"
)


class PolicyAgent:
    def decide(self, order, payment, delivery):
        status = order["order_status"]
        payment_total = round(payment["payment_total_brl"], 2)
        freight_total = round(order["freight_total_brl"], 2)

        if status == "canceled" and payment_total > 0:
            return self._decision(
                "canceled_order_paid",
                "ORDER_CANCELED_AFTER_PAYMENT",
                {"party_type": "platform", "party_id": "OLIST_PLATFORM"},
                payment_total,
                "issue_full_refund",
            )

        if status == "unavailable" and payment_total > 0:
            return self._decision(
                "unavailable_order_paid",
                "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                {"party_type": "platform", "party_id": "OLIST_PLATFORM"},
                payment_total,
                "issue_full_refund",
            )

        if delivery["is_late_delivery"] and delivery["any_seller_late"]:
            seller_id = delivery["late_seller_ids"][0]
            return self._decision(
                "late_delivery_seller",
                "SELLER_HANDOFF_AFTER_LIMIT",
                {"party_type": "seller", "party_id": seller_id},
                freight_total,
                "refund_freight",
            )

        if delivery["is_late_delivery"]:
            return self._decision(
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                {
                    "party_type": "logistics_provider",
                    "party_id": "LOGISTICS_PROVIDER",
                },
                freight_total,
                "refund_freight",
            )

        if payment["payment_count"] >= 2 and payment["payment_matches_order"]:
            return self._decision(
                "valid_split_payment",
                "MULTIPLE_PAYMENTS_RECONCILED",
                None,
                0.0,
                "explain_valid_split_payment",
            )

        if payment["payment_matches_order"]:
            return self._decision(
                "unsupported_late_claim",
                "DELIVERY_WITHIN_ESTIMATE",
                None,
                0.0,
                "reject_late_refund",
            )

        raise ValueError("Cannot classify this case")

    @staticmethod
    def _decision(issue, cause, party, refund, action):
        return {
            "primary_issue": issue,
            "case_status": "action_required" if refund > 0 else "no_action",
            "root_cause_codes": [{"cause_code": cause, "rank": 1}],
            "responsible_parties": [party] if party else [],
            "recommended_refund_brl": round(refund, 2),
            "resolution_actions": [action],
        }


def is_valid_evidence_id(evidence_id):
    return bool(EVIDENCE_RE.fullmatch(evidence_id))
class VerifierAgent:
    """Validate final output before Coordinator writes it."""

    TOP_LEVEL = {
        "case_id", "assessment", "affected_entities", "root_cause_analysis",
        "evidence_ids", "financial_resolution", "resolution_actions",
    }

    def validate(self, result: dict) -> None:
        missing = self.TOP_LEVEL - set(result)
        if missing:
            raise ValueError(f"missing top-level fields: {sorted(missing)}")

        assessment = result["assessment"]
        if assessment["primary_issue"] not in ISSUES:
            raise ValueError("invalid primary_issue")
        if assessment["case_status"] not in {"action_required", "no_action"}:
            raise ValueError("invalid case_status")
        confidence = assessment["confidence"]
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")

        entities = result["affected_entities"]
        for key in ("order_ids", "item_ids", "seller_ids", "payment_ids"):
            if key not in entities:
                raise ValueError(f"missing entity set: {key}")
            if len(entities[key]) > 5:
                raise ValueError(f"{key} exceeds maximum 5")

        evidence = result["evidence_ids"]
        if len(evidence) > 10 or any(not is_valid_evidence_id(x) for x in evidence):
            raise ValueError("invalid evidence_ids")

        analysis = result["root_cause_analysis"]
        causes = analysis["ranked_causes"]
        parties = analysis["responsible_parties"]
        if len(causes) > 3 or len(parties) > 3:
            raise ValueError("root cause/party limit exceeded")
        if any(x["cause_code"] not in CAUSES for x in causes):
            raise ValueError("invalid cause_code")
        if len(result["resolution_actions"]) > 5:
            raise ValueError("resolution_actions exceeds maximum 5")

        financial = result["financial_resolution"]
        if financial["currency"] != "BRL":
            raise ValueError("currency must be BRL")
        refund = round(float(financial["recommended_refund_brl"]), 2)
        if refund < 0:
            raise ValueError("refund cannot be negative")
        if assessment["case_status"] == "no_action" and refund != 0:
            raise ValueError("no_action requires zero refund")

        return None
