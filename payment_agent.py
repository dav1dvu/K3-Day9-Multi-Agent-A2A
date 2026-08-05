"""Payment Agent.

Reconciles order_payments against item_total + freight_total, flags split
payments and checks the 0.10 BRL tolerance. Pure pandas/arithmetic — no LLM.
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from common import money

TOLERANCE_BRL = 0.10


class PaymentQuery:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.payments = self._load_payments()
        self._payments_by_order = self.payments.groupby("order_id")

    def _load_payments(self) -> pd.DataFrame:
        df = pd.read_csv(self.data_dir / "olist_order_payments_dataset.csv", dtype=str)
        df["payment_sequential"] = df["payment_sequential"].astype(int)
        df["payment_installments"] = df["payment_installments"].astype(int)
        df["payment_value"] = df["payment_value"].astype(float)
        return df

    def get_payments(self, order_id: str) -> pd.DataFrame:
        try:
            return self._payments_by_order.get_group(order_id).sort_values("payment_sequential").copy()
        except KeyError:
            return pd.DataFrame(columns=self.payments.columns)


def load_payment_query(data_dir: str = "data") -> PaymentQuery:
    return PaymentQuery(data_dir=data_dir)


class PaymentAgent:
    def __init__(self, query: Optional[PaymentQuery] = None, data_dir: str = "data"):
        self.query = query or load_payment_query(data_dir)

    def analyze(self, order_id: str, item_total_brl: float, freight_total_brl: float) -> Dict:
        rows_df = self.query.get_payments(order_id)
        rows: List[Dict] = [
            {
                "payment_sequential": int(row["payment_sequential"]),
                "payment_type": row["payment_type"],
                "payment_installments": int(row["payment_installments"]),
                "payment_value": money(row["payment_value"]),
            }
            for _, row in rows_df.iterrows()
        ]

        payment_total = money(sum(r["payment_value"] for r in rows))
        expected_total = money(item_total_brl + freight_total_brl)
        tolerance_diff = money(abs(payment_total - expected_total))

        return {
            "order_id": order_id,
            "payment_rows": rows,
            "payment_total_brl": payment_total,
            "payment_count": len(rows),
            "is_split_payment": len(rows) >= 2,
            "payment_matches_order": tolerance_diff <= TOLERANCE_BRL,
            "tolerance_diff_brl": tolerance_diff,
        }


if __name__ == "__main__":
    agent = PaymentAgent()
    print(agent.analyze("e2a03ccf5ea816036608b2d8c3ab8e60", 100.0, 15.0))
