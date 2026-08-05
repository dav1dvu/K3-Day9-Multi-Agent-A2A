"""Delivery Agent.

Compares actual delivery/handoff timestamps against the estimated delivery
date and each item's shipping_limit_date, then attributes lateness to the
seller (late handoff to carrier) or the logistics provider (carrier picked up
on time but final delivery was still late). Pure timestamp comparison.
"""

from typing import Dict, List

from common import parse_ts


class DeliveryAgent:
    def analyze(self, order_seller_findings: Dict) -> Dict:
        f = order_seller_findings
        estimated = parse_ts(f["order_estimated_delivery_date"])
        delivered = parse_ts(f["order_delivered_customer_date"])
        carrier_pickup = parse_ts(f["order_delivered_carrier_date"])

        is_late_delivery = bool(delivered and estimated and delivered > estimated)

        seller_shipping_limits: List[Dict] = []
        any_seller_late = False
        for item in f["items"]:
            limit = parse_ts(item["shipping_limit_date"])
            handoff_late = bool(carrier_pickup and limit and carrier_pickup > limit)
            any_seller_late = any_seller_late or handoff_late
            seller_shipping_limits.append(
                {
                    "order_item_id": int(item["order_item_id"]),
                    "seller_id": item["seller_id"],
                    "shipping_limit_date": item["shipping_limit_date"],
                    "carrier_pickup_date": f["order_delivered_carrier_date"],
                    "seller_handoff_late": handoff_late,
                }
            )

        late_seller_ids: List[str] = [item["seller_id"] for item in seller_shipping_limits if item["seller_handoff_late"]]
        responsible_party = None
        if is_late_delivery:
            responsible_party = "seller" if any_seller_late else "logistics_provider"

        return {
            "order_id": f["order_id"],
            "order_estimated_delivery_date": f["order_estimated_delivery_date"],
            "order_delivered_customer_date": f["order_delivered_customer_date"],
            "order_delivered_carrier_date": f["order_delivered_carrier_date"],
            "is_late_delivery": is_late_delivery,
            "seller_shipping_limits": seller_shipping_limits,
            "late_seller_ids": late_seller_ids,
            "any_seller_late": any_seller_late,
            "responsible_party": responsible_party,
        }


if __name__ == "__main__":
    pass
