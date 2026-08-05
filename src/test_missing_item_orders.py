"""Phase 3 coordination check for Members 2 & 3: orders with no order_items rows.

README.md section 4 requires: if an order has no item row, item_ids/seller_ids
must be empty and item_total_brl/freight_total_brl must be 0.0. This exercises
OrderSellerAgent and PaymentAgent against every real order in the Olist dataset
that has zero order_items rows, confirming the contract holds and that
PaymentAgent never reports a false match against a zeroed order/freight total.

Run from the repository root with::

    python -m unittest src.test_missing_item_orders -v
"""

import unittest

import pandas as pd

from src.order_seller_agent import OrderSellerAgent
from src.payment_agent import PaymentAgent


class MissingItemOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.order_agent = OrderSellerAgent(data_dir="data")
        cls.payment_agent = PaymentAgent(data_dir="data")

        orders = pd.read_csv("data/olist_orders_dataset.csv", dtype=str)
        items = pd.read_csv("data/olist_order_items_dataset.csv", dtype=str)
        cls.missing_item_order_ids = sorted(set(orders["order_id"]) - set(items["order_id"]))
        cls.status_by_order_id = orders.set_index("order_id")["order_status"]

    def test_dataset_actually_contains_missing_item_orders(self):
        # Sanity check: the edge case this suite verifies must be real, not hypothetical.
        self.assertGreater(len(self.missing_item_order_ids), 0)

    def test_order_seller_agent_zeroes_totals_for_every_missing_item_order(self):
        for order_id in self.missing_item_order_ids:
            findings = self.order_agent.analyze(order_id)
            self.assertTrue(findings["order_found"], order_id)
            self.assertEqual(findings["items"], [], order_id)
            self.assertEqual(findings["seller_ids"], [], order_id)
            self.assertEqual(findings["item_total_brl"], 0.0, order_id)
            self.assertEqual(findings["freight_total_brl"], 0.0, order_id)
            self.assertFalse(findings["any_carrier_after_limit"], order_id)

    def test_payment_agent_never_false_matches_a_zeroed_order(self):
        for order_id in self.missing_item_order_ids:
            findings = self.order_agent.analyze(order_id)
            payment = self.payment_agent.analyze(
                order_id, findings["item_total_brl"], findings["freight_total_brl"]
            )
            if payment["payment_total_brl"] > 0.10:
                self.assertFalse(
                    payment["payment_matches_order"],
                    f"{order_id}: paid {payment['payment_total_brl']} BRL against an "
                    "order with no items but was reported as a matching payment",
                )

    def test_canceled_and_unavailable_missing_item_orders_carry_correct_tags(self):
        canceled_or_unavailable = [
            oid
            for oid in self.missing_item_order_ids
            if self.status_by_order_id.get(oid) in {"canceled", "unavailable"}
        ]
        self.assertGreater(len(canceled_or_unavailable), 0)
        for order_id in canceled_or_unavailable:
            status = self.status_by_order_id[order_id]
            findings = self.order_agent.analyze(order_id)
            self.assertEqual(findings["status_tags"], [status], order_id)
            self.assertEqual(findings["is_canceled"], status == "canceled", order_id)
            self.assertEqual(findings["is_unavailable"], status == "unavailable", order_id)


if __name__ == "__main__":
    unittest.main()
