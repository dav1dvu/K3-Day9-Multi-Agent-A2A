from src.agents.verifier import EVIDENCE_PATTERNS, VerifierAgent
from src.policy_verifier_agent import PolicyAgent


def findings():
    return (
        {
            "order_id": "o1",
            "order_found": True,
            "order_status": "delivered",
            "items": [{"order_item_id": 1}],
            "item_total_brl": 100.0,
            "freight_total_brl": 15.0,
            "seller_ids": ["s1"],
            "order_delivered_customer_date": "2018-01-10 00:00:00",
            "order_estimated_delivery_date": "2018-01-11 00:00:00",
        },
        {
            "payment_total_brl": 115.0,
            "payment_count": 1,
            "payment_rows": [{"payment_sequential": 1}],
            "payment_matches_order": True,
            "valid_split_payment": False,
        },
        {
            "is_late_delivery": False,
            "any_seller_late": False,
            "seller_shipping_limits": [],
        },
    )


def test_policy_priority_and_all_rules():
    agent = PolicyAgent()
    order, payment, delivery = findings()
    assert agent.decide(order, payment, delivery)["primary_issue"] == "unsupported_late_claim"
    payment["payment_count"] = 2
    payment["valid_split_payment"] = True
    assert agent.decide(order, payment, delivery)["primary_issue"] == "valid_split_payment"
    delivery.update(
        is_late_delivery=True,
        any_seller_late=True,
        seller_shipping_limits=[{"seller_id": "s1", "seller_handoff_late": True}],
    )
    assert agent.decide(order, payment, delivery)["primary_issue"] == "late_delivery_seller"
    delivery["any_seller_late"] = False
    assert agent.decide(order, payment, delivery)["primary_issue"] == "late_delivery_logistics"
    order["order_status"] = "canceled"
    payment["payment_total_brl"] = 115.0
    assert agent.decide(order, payment, delivery)["primary_issue"] == "canceled_order_paid"


def test_evidence_and_verifier():
    assert EVIDENCE_PATTERNS["item"].fullmatch("item:o1:1")
    assert not EVIDENCE_PATTERNS["item"].fullmatch("item:o1")
    result = {
        "case_id": "EC_001",
        "assessment": {
            "primary_issue": "unsupported_late_claim",
            "case_status": "no_action",
            "confidence": 1.0,
        },
        "affected_entities": {
            "order_ids": ["o1"],
            "item_ids": [],
            "seller_ids": [],
            "payment_ids": [],
        },
        "root_cause_analysis": {
            "ranked_causes": [{"cause_code": "DELIVERY_WITHIN_ESTIMATE", "rank": 1}],
            "responsible_parties": [],
        },
        "evidence_ids": ["order:o1", "policy:DELIVERY_WITHIN_ESTIMATE"],
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": 0.0,
            "freight_total_brl": 0.0,
            "payment_total_brl": 0.0,
            "recommended_refund_brl": 0.0,
        },
        "resolution_actions": ["reject_late_refund"],
    }
    assert VerifierAgent().validate(result) == []
