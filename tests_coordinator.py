import json
import os
from pathlib import Path

import pytest

from src.agents.coordinator import CoordinatorAgent, CoordinatorError, TRACE_FILE


VALID_INPUT = {
    "case_id": "EC_TEST",
    "opened_at": "2026-08-05T00:00:00-03:00",
    "customer_request": {
        "language": "vi",
        "message": "Kiểm tra đơn hàng.",
        "claimed_order_id": "e2a03ccf5ea816036608b2d8c3ab8e60",
    },
    "policy_version": "EC_POLICY_V1",
}


def cleanup_trace():
    if TRACE_FILE.exists():
        TRACE_FILE.unlink()


def test_valid_input_runs_and_writes_trace(tmp_path, monkeypatch):
    cleanup_trace()
    agent = CoordinatorAgent()
    input_path = tmp_path / "EC_TEST.json"
    input_path.write_text(json.dumps(VALID_INPUT, ensure_ascii=False), encoding="utf-8")

    state = agent.run_case(str(input_path))

    assert state.case_id == "EC_TEST"
    assert state.order_seller_findings is not None
    assert state.payment_findings is not None
    assert state.delivery_findings is not None
    assert state.policy_decision is not None
    assert state.final_context["case_id"] == "EC_TEST"
    assert TRACE_FILE.exists()

    lines = TRACE_FILE.read_text().strip().splitlines()
    events = [json.loads(line)["event"] for line in lines]
    assert events[0] == "case_started"
    assert events[-1] == "case_completed"
    assert events.count("agent_started") == 5
    assert events.count("agent_completed") == 5
    assert events.count("handoff") == 4
    assert events.count("case_failed") == 0


def test_missing_required_case_field_raises():
    agent = CoordinatorAgent()
    payload = dict(VALID_INPUT)
    del payload["case_id"]
    with pytest.raises(ValueError, match="Missing required case fields"):
        agent._validate_input(payload)


def test_missing_customer_request_field_raises():
    agent = CoordinatorAgent()
    payload = dict(VALID_INPUT)
    payload["customer_request"] = {"language": "vi", "message": "Hi"}
    with pytest.raises(ValueError, match="Missing required customer_request fields"):
        agent._validate_input(payload)


def test_agent_failure_creates_structured_error(tmp_path, monkeypatch):
    cleanup_trace()
    agent = CoordinatorAgent()
    input_path = tmp_path / "EC_TEST.json"
    input_path.write_text(json.dumps(VALID_INPUT, ensure_ascii=False), encoding="utf-8")

    def fail_analyze(*args, **kwargs):
        raise RuntimeError("Sub-agent failed")

    monkeypatch.setattr(agent.payment, "analyze", fail_analyze)

    with pytest.raises(CoordinatorError) as exc_info:
        agent.run_case(str(input_path))

    err = exc_info.value
    assert err.case_id == "EC_TEST"
    assert err.agent_name == "PaymentAgent"
    assert "Sub-agent failed" in err.message
    assert TRACE_FILE.exists()
    trace = [json.loads(line) for line in TRACE_FILE.read_text().strip().splitlines()]
    assert trace[-1]["event"] == "case_failed"
    assert trace[-1]["agent"] == "PaymentAgent"
    assert trace[-1]["status"] == "failed"


if __name__ == "__main__":
    pytest.main([__file__])
