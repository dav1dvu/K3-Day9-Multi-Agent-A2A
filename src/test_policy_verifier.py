from src.policy_verifier_agent import PolicyAgent, VerifierAgent, is_valid_evidence_id


def findings():
    return (
        {"order_id": "o1", "order_status": "delivered", "freight_total_brl": 15.0},
        {"payment_total_brl": 115.0, "payment_count": 1, "payment_matches_order": True},
        {"is_late_delivery": False, "any_seller_late": False, "late_seller_ids": []},
    )


def test_policy_priority_and_all_rules():
    agent = PolicyAgent()
    order, payment, delivery = findings()
    assert agent.decide(order, payment, delivery)["primary_issue"] == "unsupported_late_claim"
    payment["payment_count"] = 2
    assert agent.decide(order, payment, delivery)["primary_issue"] == "valid_split_payment"
    delivery.update(is_late_delivery=True, any_seller_late=True, late_seller_ids=["s1"])
    assert agent.decide(order, payment, delivery)["primary_issue"] == "late_delivery_seller"
    delivery["any_seller_late"] = False
    assert agent.decide(order, payment, delivery)["primary_issue"] == "late_delivery_logistics"
    order["order_status"] = "canceled"
    payment["payment_total_brl"] = 115.0
    assert agent.decide(order, payment, delivery)["primary_issue"] == "canceled_order_paid"


def test_evidence_and_verifier():
    assert is_valid_evidence_id("item:o1:1")
    assert not is_valid_evidence_id("item:o1")
    result = {
        "case_id": "EC_001",
        "assessment": {"primary_issue": "unsupported_late_claim", "case_status": "no_action", "confidence": 1.0},
        "affected_entities": {"order_ids": ["o1"], "item_ids": [], "seller_ids": [], "payment_ids": []},
        "root_cause_analysis": {"ranked_causes": [{"cause_code": "DELIVERY_WITHIN_ESTIMATE", "rank": 1}], "responsible_parties": []},
        "evidence_ids": ["order:o1", "policy:DELIVERY_WITHIN_ESTIMATE"],
        "financial_resolution": {"currency": "BRL", "recommended_refund_brl": 0.0},
        "resolution_actions": ["reject_late_refund"],
    }
    VerifierAgent().validate(result)
