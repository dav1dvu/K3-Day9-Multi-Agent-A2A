from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CaseState:
    case_id: str
    input_data: Dict[str, Any]
    order_seller_findings: Optional[Dict[str, Any]] = None
    payment_findings: Optional[Dict[str, Any]] = None
    delivery_findings: Optional[Dict[str, Any]] = None
    policy_decision: Optional[Dict[str, Any]] = None
    final_context: Optional[Dict[str, Any]] = None
    completed: bool = False
    failed: bool = False
    errors: List[Dict[str, Any]] = field(default_factory=list)
