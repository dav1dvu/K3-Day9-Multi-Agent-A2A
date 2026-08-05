"""Order & Seller Agent.

Loads orders/order_items/sellers from `data/`, resolves a claimed_order_id and
returns an OrderSellerFindings dict (see architecture.md section 7.1). Pure
pandas lookups — no LLM involved.
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from common import clean, money, parse_ts


class OrderSellerQuery:
    """Fast in-memory lookup index over orders, order_items and sellers."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.orders = self._load_orders()
        self.order_items = self._load_order_items()
        self.sellers = self._load_sellers()

        self._order_index = self.orders.set_index("order_id")
        self._order_items_by_order = self.order_items.groupby("order_id")
        self._seller_index = self.sellers.set_index("seller_id")

    def _load_orders(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "olist_orders_dataset.csv", dtype=str)

    def _load_order_items(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "olist_order_items_dataset.csv", dtype=str)
        df["order_item_id"] = df["order_item_id"].astype(int)
        df["price"] = df["price"].astype(float)
        df["freight_value"] = df["freight_value"].astype(float)
        return df

    def _load_sellers(self) -> pd.DataFrame:
        return pd.read_csv(self.data_dir / "olist_sellers_dataset.csv", dtype=str)

    @staticmethod
    def normalize_claimed_order_id(claimed_order_id: str) -> str:
        return claimed_order_id.strip()

    def get_order(self, claimed_order_id: str) -> Optional[pd.Series]:
        claimed_order_id = self.normalize_claimed_order_id(claimed_order_id)
        try:
            return self._order_index.loc[claimed_order_id]
        except KeyError:
            return None

    def get_order_items(self, claimed_order_id: str) -> pd.DataFrame:
        claimed_order_id = self.normalize_claimed_order_id(claimed_order_id)
        try:
            return self._order_items_by_order.get_group(claimed_order_id).sort_values("order_item_id").copy()
        except KeyError:
            return pd.DataFrame(columns=self.order_items.columns)

    def seller_exists(self, seller_id: str) -> bool:
        return seller_id in self._seller_index.index


def load_order_seller_query(data_dir: str = "data") -> OrderSellerQuery:
    """Load order and seller CSVs and return a reusable query helper."""
    return OrderSellerQuery(data_dir=data_dir)


class OrderSellerAgent:
    """Resolves a claimed_order_id into order status, items, sellers and totals."""

    def __init__(self, query: Optional[OrderSellerQuery] = None, data_dir: str = "data"):
        self.query = query or load_order_seller_query(data_dir)

    def analyze(self, claimed_order_id: str) -> Dict:
        order = self.query.get_order(claimed_order_id)
        order_id = self.query.normalize_claimed_order_id(claimed_order_id)
        found = order is not None

        items_df = self.query.get_order_items(claimed_order_id) if found else pd.DataFrame()
        order_status = clean(order["order_status"]) if found else None
        carrier_date = clean(order["order_delivered_carrier_date"]) if found else None
        carrier_ts = parse_ts(carrier_date)

        items: List[Dict] = []
        for _, row in items_df.iterrows():
            shipping_limit_date = clean(row["shipping_limit_date"])
            limit_ts = parse_ts(shipping_limit_date)
            carrier_after_limit = bool(carrier_ts and limit_ts and carrier_ts > limit_ts)
            items.append(
                {
                    "order_item_id": int(row["order_item_id"]),
                    "product_id": clean(row["product_id"]),
                    "seller_id": clean(row["seller_id"]),
                    "shipping_limit_date": shipping_limit_date,
                    "price": money(row["price"]),
                    "freight_value": money(row["freight_value"]),
                    "carrier_after_limit": carrier_after_limit,
                }
            )

        item_total = money(sum(i["price"] for i in items))
        freight_total = money(sum(i["freight_value"] for i in items))
        seller_ids = sorted({i["seller_id"] for i in items if i["seller_id"]})

        is_canceled = order_status == "canceled"
        is_unavailable = order_status == "unavailable"
        status_tags: List[str] = []
        if is_canceled:
            status_tags.append("canceled")
        if is_unavailable:
            status_tags.append("unavailable")
        any_carrier_after_limit = any(i["carrier_after_limit"] for i in items)

        return {
            "order_id": order_id,
            "order_found": found,
            "order_status": order_status,
            "order_purchase_timestamp": clean(order["order_purchase_timestamp"]) if found else None,
            "order_approved_at": clean(order["order_approved_at"]) if found else None,
            "order_delivered_carrier_date": carrier_date,
            "order_delivered_customer_date": clean(order["order_delivered_customer_date"]) if found else None,
            "order_estimated_delivery_date": clean(order["order_estimated_delivery_date"]) if found else None,
            "customer_id": clean(order["customer_id"]) if found else None,
            "items": items,
            "item_total_brl": item_total,
            "freight_total_brl": freight_total,
            "seller_ids": seller_ids,
            "is_canceled": is_canceled,
            "is_unavailable": is_unavailable,
            "status_tags": status_tags,
            "any_carrier_after_limit": any_carrier_after_limit,
        }


if __name__ == "__main__":
    agent = OrderSellerAgent()
    # Test with a known order ID if run directly
    try:
        res = agent.analyze("e2a03ccf5ea816036608b2d8c3ab8e60")
        print("Test analysis successful. Keys returned:")
        print(list(res.keys()))
    except Exception as e:
        print(f"Direct test failed: {e}")
