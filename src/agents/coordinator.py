"""Coordinator Agent for EC dispute cases.

This module orchestrates input parsing, sub-agent dispatch, state handoffs,
trace logging, and final case assembly. It does not implement sub-agent
business logic.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.order_seller_agent import OrderSellerAgent
from src.payment_agent import PaymentAgent
from src.delivery_agent import DeliveryAgent
from src.policy_verifier_agent import PolicyAgent
from src.agents.verifier import VerifierAgent
from src.models import CaseState

TRACE_FILE = Path("logging/trace.jsonl")
REQUIRED_CASE_FIELDS = {"case_id", "customer_request", "policy_version"}
REQUIRED_CUSTOMER_REQUEST_FIELDS = {"language", "message", "claimed_order_id"}


class CoordinatorError(Exception):
    def __init__(self, case_id: Optional[str], agent_name: str, message: str):
        self.case_id = case_id
        self.agent_name = agent_name
        self.message = message
        super().__init__(f"[{case_id or 'UNKNOWN'}][{agent_name}] {message}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_trace(event: str, case_id: Optional[str], agent_name: Optional[str], status: str, metadata: Dict[str, Any] = None) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "timestamp": _now_iso(),
        "event": event,
        "case_id": case_id,
        "agent": agent_name,
        "status": status,
        "metadata": metadata or {},
    }
    with TRACE_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class CoordinatorAgent:
    def __init__(self):
        self.order_seller = OrderSellerAgent()
        self.payment = PaymentAgent()
        self.delivery = DeliveryAgent()
        self.policy = PolicyAgent()
        self.verifier = VerifierAgent()

    @staticmethod
    def _validate_input(payload: Dict[str, Any]) -> None:
        missing = REQUIRED_CASE_FIELDS - set(payload.keys())
        if missing:
            raise ValueError(f"Missing required case fields: {sorted(missing)}")

        customer_request = payload.get("customer_request")
        if not isinstance(customer_request, dict):
            raise ValueError("customer_request must be an object")

        missing_cr = REQUIRED_CUSTOMER_REQUEST_FIELDS - set(customer_request.keys())
        if missing_cr:
            raise ValueError(f"Missing required customer_request fields: {sorted(missing_cr)}")

        claimed_order_id = customer_request.get("claimed_order_id")
        if not isinstance(claimed_order_id, str) or not claimed_order_id.strip():
            raise ValueError("claimed_order_id must be a non-empty string")

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Input JSON must be an object")
        return payload

    def _dispatch_agent(self, agent_name: str, fn, *args, **kwargs) -> Dict[str, Any]:
        _write_trace("agent_started", self.current_case_id, agent_name, "running", {"args": [], "kwargs": {}})
        try:
            result = fn(*args, **kwargs)
            if not isinstance(result, dict):
                raise TypeError(f"{agent_name} must return a dict")
            _write_trace("agent_completed", self.current_case_id, agent_name, "success", {"result_keys": sorted(result.keys())})
            return result
        except Exception as exc:
            _write_trace("agent_completed", self.current_case_id, agent_name, "failure", {"error": str(exc)})
            raise CoordinatorError(self.current_case_id, agent_name, str(exc)) from exc

    def _handoff(self, from_agent: str, to_agent: str, state_snapshot: Dict[str, Any]) -> None:
        _write_trace("handoff", self.current_case_id, None, "info", {"from": from_agent, "to": to_agent, "state_keys": sorted(state_snapshot.keys())})

    def run_case(self, input_path: str) -> CaseState:
        payload = self._load_json(Path(input_path))
        self._validate_input(payload)

        self.current_case_id = payload["case_id"]
        _write_trace("case_started", self.current_case_id, None, "started", {"input_path": str(input_path)})

        state = CaseState(case_id=self.current_case_id, input_data=payload)
        try:
            order_findings = self._dispatch_agent(
                "OrderSellerAgent", self.order_seller.analyze, payload["customer_request"]["claimed_order_id"]
            )
            state.order_seller_findings = order_findings

            self._handoff("OrderSellerAgent", "PaymentAgent", {"order_id": order_findings["order_id"], "item_total_brl": order_findings["item_total_brl"], "freight_total_brl": order_findings["freight_total_brl"]})
            payment_findings = self._dispatch_agent(
                "PaymentAgent",
                self.payment.analyze,
                order_findings["order_id"],
                order_findings["item_total_brl"],
                order_findings["freight_total_brl"],
            )
            state.payment_findings = payment_findings

            self._handoff("OrderSellerAgent", "DeliveryAgent", {"order_seller_findings": order_findings})
            delivery_findings = self._dispatch_agent(
                "DeliveryAgent", self.delivery.analyze, order_findings
            )
            state.delivery_findings = delivery_findings

            self._handoff("PaymentAgent+DeliveryAgent", "PolicyAgent", {
                "order_seller_findings": order_findings,
                "payment_findings": payment_findings,
                "delivery_findings": delivery_findings,
            })
            policy_decision = self._dispatch_agent(
                "PolicyAgent",
                self.policy.decide,
                order_findings,
                payment_findings,
                delivery_findings,
            )
            state.policy_decision = policy_decision

            self._handoff("PolicyAgent", "VerifierAgent", {"policy_decision": policy_decision})
            verifier_result = self._dispatch_agent(
                "VerifierAgent",
                self.verifier.validate_and_write,
                {
                    "case_id": state.case_id,
                    "input": payload,
                    "order_seller_findings": order_findings,
                    "payment_findings": payment_findings,
                    "delivery_findings": delivery_findings,
                    "policy_decision": policy_decision,
                },
            )

            final_context = {
                "case_id": state.case_id,
                "input": payload,
                "order_seller_findings": order_findings,
                "payment_findings": payment_findings,
                "delivery_findings": delivery_findings,
                "policy_decision": policy_decision,
                "verifier_result": verifier_result,
            }
            state.final_context = final_context
            state.completed = True
            _write_trace("case_completed", self.current_case_id, None, "success", {"final_keys": sorted(final_context.keys())})
            return state
        except CoordinatorError as err:
            state.failed = True
            state.errors.append({"agent": err.agent_name, "message": err.message})
            _write_trace("case_failed", self.current_case_id, err.agent_name, "failed", {"error": err.message})
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Coordinator Agent on a single case JSON input.")
    parser.add_argument("input_path", help="Path to EC_xxx.json")
    args = parser.parse_args()

    agent = CoordinatorAgent()
    state = agent.run_case(args.input_path)
    print(f"Completed case {state.case_id}, completed={state.completed}")
