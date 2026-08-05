import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd


class OrderSellerQuery:
    """Helper for fast order and seller lookups by claimed_order_id.

    This class loads the 3 Olist CSVs from `data/` and builds in-memory
    lookup indexes for order records, order items, and seller details.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.orders = self._load_orders()
        self.order_items = self._load_order_items()
        self.sellers = self._load_sellers()

        self._order_index = self.orders.set_index("order_id")
        self._order_items_by_order = self.order_items.groupby("order_id")
        self._seller_index = self.sellers.set_index("seller_id")

    def _load_orders(self) -> pd.DataFrame:
        path = self.data_dir / "olist_orders_dataset.csv"
        return pd.read_csv(path, dtype=str)

    def _load_order_items(self) -> pd.DataFrame:
        path = self.data_dir / "olist_order_items_dataset.csv"
        return pd.read_csv(path, dtype=str)

    def _load_sellers(self) -> pd.DataFrame:
        path = self.data_dir / "olist_sellers_dataset.csv"
        return pd.read_csv(path, dtype=str)

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
            return self._order_items_by_order.get_group(claimed_order_id).copy()
        except KeyError:
            return pd.DataFrame(columns=self.order_items.columns)

    def get_sellers_for_order(self, claimed_order_id: str) -> pd.DataFrame:
        items = self.get_order_items(claimed_order_id)
        if items.empty:
            return pd.DataFrame(columns=self.sellers.columns)

        seller_ids = items["seller_id"].dropna().unique().tolist()
        if not seller_ids:
            return pd.DataFrame(columns=self.sellers.columns)

        return self.sellers[self.sellers["seller_id"].isin(seller_ids)].copy()

    def get_order_context(self, claimed_order_id: str) -> Dict[str, pd.DataFrame]:
        return {
            "order": self.get_order(claimed_order_id),
            "order_items": self.get_order_items(claimed_order_id),
            "sellers": self.get_sellers_for_order(claimed_order_id),
        }


def load_order_seller_query(data_dir: str = "data") -> OrderSellerQuery:
    """Load order and seller CSVs and return a reusable query helper."""
    return OrderSellerQuery(data_dir=data_dir)


if __name__ == "__main__":
    loader = load_order_seller_query("data")
    sample_id = "CLAIMED_ORDER_ID"
    order = loader.get_order(sample_id)
    print("Order record:\n", order)
    print("Order items:\n", loader.get_order_items(sample_id))
    print("Sellers for order:\n", loader.get_sellers_for_order(sample_id))
