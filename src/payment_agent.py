"""Payment data helpers for the Phase 1 payment/finance workstream.

The module loads Olist payment rows once, indexes them by ``order_id`` and
reconciles their total against the item plus freight total produced by the
Order & Seller Agent.  All business decisions are deterministic; no LLM is
used for financial arithmetic.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd


MoneyLike = Union[str, int, float, Decimal]
TOLERANCE_BRL = Decimal("0.10")
CENT = Decimal("0.01")


def as_money(value: MoneyLike) -> Decimal:
    """Convert a numeric value to BRL cents using commercial rounding."""
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def within_tolerance(actual: MoneyLike, expected: MoneyLike) -> bool:
    """Return whether two BRL values differ by at most 0.10 BRL."""
    return abs(as_money(actual) - as_money(expected)) <= TOLERANCE_BRL


class PaymentQuery:
    """Reusable in-memory index over ``olist_order_payments_dataset.csv``."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.payments = self._load_payments()
        self._payments_by_order = self.payments.groupby("order_id", sort=False)

    def _load_payments(self) -> pd.DataFrame:
        path = self.data_dir / "olist_order_payments_dataset.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Payment dataset not found: {path}")

        df = pd.read_csv(path, dtype=str)
        required = {
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Payment dataset is missing columns: {sorted(missing)}")

        df["payment_sequential"] = pd.to_numeric(
            df["payment_sequential"], errors="raise"
        ).astype(int)
        df["payment_installments"] = pd.to_numeric(
            df["payment_installments"], errors="raise"
        ).astype(int)
        df["payment_value"] = pd.to_numeric(
            df["payment_value"], errors="raise"
        ).astype(float)
        return df

    @staticmethod
    def normalize_order_id(order_id: str) -> str:
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id must be a non-empty string")
        return order_id.strip()

    def get_payments(self, order_id: str) -> pd.DataFrame:
        order_id = self.normalize_order_id(order_id)
        try:
            rows = self._payments_by_order.get_group(order_id)
        except KeyError:
            return pd.DataFrame(columns=self.payments.columns)
        return rows.sort_values("payment_sequential").copy()


def load_payment_query(data_dir: str = "data") -> PaymentQuery:
    """Load and index the payment dataset for reuse across many cases."""
    return PaymentQuery(data_dir=data_dir)


class PaymentAgent:
    """Build the ``PaymentFindings`` contract described in architecture.md."""

    def __init__(
        self, query: Optional[PaymentQuery] = None, data_dir: str = "data"
    ):
        self.query = query or load_payment_query(data_dir)

    def analyze(
        self, order_id: str, item_total_brl: MoneyLike, freight_total_brl: MoneyLike
    ) -> Dict:
        order_id = self.query.normalize_order_id(order_id)
        rows_df = self.query.get_payments(order_id)

        rows: List[Dict] = []
        payment_total = Decimal("0.00")
        for _, row in rows_df.iterrows():
            payment_value = as_money(row["payment_value"])
            payment_total += payment_value
            rows.append(
                {
                    "payment_sequential": int(row["payment_sequential"]),
                    "payment_type": str(row["payment_type"]),
                    "payment_installments": int(row["payment_installments"]),
                    "payment_value": float(payment_value),
                }
            )

        payment_total = as_money(payment_total)
        expected_total = as_money(as_money(item_total_brl) + as_money(freight_total_brl))
        difference = as_money(abs(payment_total - expected_total))

        return {
            "order_id": order_id,
            "payment_rows": rows,
            "payment_total_brl": float(payment_total),
            "payment_count": len(rows),
            "is_split_payment": len(rows) >= 2,
            "payment_matches_order": difference <= TOLERANCE_BRL,
            "tolerance_diff_brl": float(difference),
        }


if __name__ == "__main__":
    # Small smoke test using a known split-payment order from the Olist data.
    agent = PaymentAgent()
    print(agent.analyze("0016dfedd97fc2950e388d2971d718c7", 59.99, 10.56))
