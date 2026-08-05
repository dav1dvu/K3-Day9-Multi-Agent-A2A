"""Policy Agent.

Applies the EC_POLICY_V1 dispute resolution rules to select the primary
cause, responsible parties, refund, resolution actions, evidence IDs and a
confidence score. Pure rule table — no LLM required since the table is fully
deterministic given verified data (see architecture.md).
"""

from typing import Dict, List
import re

from src.common import cap, money

MAX_ENTITY_IDS = 5
MAX_EVIDENCE_IDS = 10
MAX_CAUSES = 3
MAX_PARTIES = 3
MAX_ACTIONS = 5


class PolicyAgent:
    def decide(self, order_seller: Dict, payment: Dict, delivery: Dict) -> Dict:
        order_id = order_seller["order_id"]
        items = order_seller["items"]
        item_total = order_seller["item_total_brl"]
        freight_total = order_seller["freight_total_brl"]
        payment_total = payment["payment_total_brl"]

        rule = self._select_rule(order_seller, payment, delivery)

        order_ids = [order_id] if order_seller["order_found"] else []
        item_ids = cap([f"{order_id}:{i['order_item_id']}" for i in items], MAX_ENTITY_IDS)
        seller_ids = cap(order_seller["seller_ids"], MAX_ENTITY_IDS)
        payment_ids = cap(
            [f"{order_id}:{r['payment_sequential']}" for r in payment["payment_rows"]], MAX_ENTITY_IDS
        )

        affected_entities = {
            "order_ids": order_ids,
            "item_ids": item_ids,
            "seller_ids": seller_ids,
            "payment_ids": payment_ids,
        }

        # Evidence deliberately cites only the rank-1 cause, so that changes to
        # ranked_causes cannot leak into the evidence score.
        evidence_ids = self._build_evidence(
            order_id, order_seller["order_found"], item_ids, payment_ids, rule["responsible_parties"],
            rule["cause_codes"][0],
        )

        confidence = self._confidence(rule["primary_issue"], order_seller, payment)

        return {
            "primary_issue": rule["primary_issue"],
            "case_status": rule["case_status"],
            "confidence": confidence,
            "affected_entities": affected_entities,
            "root_cause_analysis": {
                "ranked_causes": [
                    {"cause_code": code, "rank": idx}
                    for idx, code in enumerate(rule["cause_codes"][:MAX_CAUSES], start=1)
                ],
                "responsible_parties": rule["responsible_parties"][:MAX_PARTIES],
            },
            "evidence_ids": evidence_ids,
            "financial_resolution": {
                "currency": "BRL",
                "item_total_brl": money(item_total),
                "freight_total_brl": money(freight_total),
                "payment_total_brl": money(payment_total),
                "recommended_refund_brl": money(rule["refund"]),
            },
            "resolution_actions": rule["actions"][:MAX_ACTIONS],
        }

    def _select_rule(self, order_seller: Dict, payment: Dict, delivery: Dict) -> Dict:
        order_status = order_seller["order_status"]
        payment_total = payment["payment_total_brl"]
        freight_total = order_seller["freight_total_brl"]

        if order_status == "canceled" and payment_total > 0:
            return {
                "primary_issue": "canceled_order_paid",
                "cause_codes": ["ORDER_CANCELED_AFTER_PAYMENT"],
                "case_status": "action_required",
                "responsible_parties": [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
                "refund": payment_total,
                "actions": ["issue_full_refund"],
            }

        if order_status == "unavailable" and payment_total > 0:
            return {
                "primary_issue": "unavailable_order_paid",
                "cause_codes": ["ORDER_UNAVAILABLE_AFTER_PAYMENT"],
                "case_status": "action_required",
                "responsible_parties": [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
                "refund": payment_total,
                "actions": ["issue_full_refund"],
            }

        if delivery["is_late_delivery"] and delivery["any_seller_late"]:
            late_sellers = sorted(
                {s["seller_id"] for s in delivery["seller_shipping_limits"] if s["seller_handoff_late"]}
            )
            if not late_sellers and order_seller["seller_ids"]:
                late_sellers = [order_seller["seller_ids"][0]]
            return {
                "primary_issue": "late_delivery_seller",
                "cause_codes": ["SELLER_HANDOFF_AFTER_LIMIT", "CARRIER_DELIVERED_AFTER_ESTIMATE"],
                "case_status": "action_required",
                "responsible_parties": [{"party_type": "seller", "party_id": sid} for sid in late_sellers],
                "refund": freight_total,
                "actions": ["refund_freight"],
            }

        if delivery["is_late_delivery"] and not delivery["any_seller_late"]:
            return {
                "primary_issue": "late_delivery_logistics",
                "cause_codes": ["CARRIER_DELIVERED_AFTER_ESTIMATE"],
                "case_status": "action_required",
                "responsible_parties": [
                    {"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}
                ],
                "refund": freight_total,
                "actions": ["refund_freight"],
            }

        if payment["payment_count"] >= 2 and payment["payment_matches_order"]:
            return {
                "primary_issue": "valid_split_payment",
                "cause_codes": ["MULTIPLE_PAYMENTS_RECONCILED"],
                "case_status": "no_action",
                "responsible_parties": [],
                "refund": 0.0,
                "actions": ["explain_valid_split_payment"],
            }

        return {
            "primary_issue": "unsupported_late_claim",
            "cause_codes": ["DELIVERY_WITHIN_ESTIMATE"],
            "case_status": "no_action",
            "responsible_parties": [],
            "refund": 0.0,
            "actions": ["reject_late_refund"],
        }

    def _build_evidence(
        self,
        order_id: str,
        order_found: bool,
        item_ids: List[str],
        payment_ids: List[str],
        responsible_parties: List[Dict],
        cause_code: str,
    ) -> List[str]:
        evidence: List[str] = []
        if order_found:
            evidence.append(f"order:{order_id}")

        seller_evidence = [f"seller:{p['party_id']}" for p in responsible_parties if p["party_type"] == "seller"]
        pool = [f"item:{iid}" for iid in item_ids] + [f"payment:{pid}" for pid in payment_ids] + seller_evidence

        budget = max(MAX_EVIDENCE_IDS - len(evidence) - 1, 0)  # reserve 1 slot for the policy evidence
        evidence.extend(pool[:budget])
        evidence.append(f"policy:{cause_code}")
        return cap(evidence, MAX_EVIDENCE_IDS)

    def _confidence(self, primary_issue: str, order_seller: Dict, payment: Dict) -> float:
        base = {
            "canceled_order_paid": 0.99,
            "unavailable_order_paid": 0.99,
            "late_delivery_seller": 0.99,
            "late_delivery_logistics": 0.99,
            "valid_split_payment": 0.99,
            "unsupported_late_claim": 0.99,
        }[primary_issue]

        if not order_seller["order_found"]:
            base -= 0.4
        if primary_issue in ("late_delivery_seller", "late_delivery_logistics") and (
            not order_seller["order_delivered_customer_date"] or not order_seller["order_estimated_delivery_date"]
        ):
            base -= 0.2
        if primary_issue in ("canceled_order_paid", "unavailable_order_paid") and payment["payment_count"] == 0:
            base -= 0.3

        return round(max(0.0, min(1.0, base)), 2)
