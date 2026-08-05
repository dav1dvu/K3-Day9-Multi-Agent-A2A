"""Phase 2 verification for the Payment Agent.

Run from the repository root with::

    python -m unittest src.test_payment_agent -v
"""

import unittest

from src.order_seller_agent import OrderSellerAgent
from src.payment_agent import PaymentAgent, within_tolerance


SPLIT_ORDER_ID = "0016dfedd97fc2950e388d2971d718c7"
SINGLE_ORDER_ID = "53cdb2fc8bc7dce0b6741e2150273451"


class PaymentAgentPhase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.order_agent = OrderSellerAgent(data_dir="data")
        cls.payment_agent = PaymentAgent(data_dir="data")

    def analyze_real_order(self, order_id):
        order = self.order_agent.analyze(order_id)
        self.assertTrue(order["order_found"])
        return self.payment_agent.analyze(
            order_id,
            order["item_total_brl"],
            order["freight_total_brl"],
        )

    def test_valid_split_payment_from_real_data(self):
        findings = self.analyze_real_order(SPLIT_ORDER_ID)

        self.assertEqual(findings["payment_count"], 2)
        self.assertEqual(findings["payment_total_brl"], 70.55)
        self.assertTrue(findings["has_payment"])
        self.assertTrue(findings["is_split_payment"])
        self.assertTrue(findings["payment_matches_order"])
        self.assertTrue(findings["valid_split_payment"])
        self.assertEqual(findings["tolerance_diff_brl"], 0.0)
        self.assertEqual(
            [row["payment_sequential"] for row in findings["payment_rows"]],
            [1, 2],
        )

    def test_single_payment_is_reconciled_but_not_split(self):
        findings = self.analyze_real_order(SINGLE_ORDER_ID)

        self.assertEqual(findings["payment_count"], 1)
        self.assertEqual(findings["payment_total_brl"], 141.46)
        self.assertTrue(findings["payment_matches_order"])
        self.assertFalse(findings["is_split_payment"])
        self.assertFalse(findings["valid_split_payment"])

    def test_tolerance_boundary_is_inclusive(self):
        at_boundary = self.payment_agent.analyze(SPLIT_ORDER_ID, 60.09, 10.56)
        outside_boundary = self.payment_agent.analyze(SPLIT_ORDER_ID, 60.10, 10.56)

        self.assertEqual(at_boundary["tolerance_diff_brl"], 0.10)
        self.assertTrue(at_boundary["payment_matches_order"])
        self.assertTrue(at_boundary["valid_split_payment"])
        self.assertEqual(outside_boundary["tolerance_diff_brl"], 0.11)
        self.assertFalse(outside_boundary["payment_matches_order"])
        self.assertFalse(outside_boundary["valid_split_payment"])
        self.assertTrue(within_tolerance(100.10, 100.00))
        self.assertFalse(within_tolerance(100.11, 100.00))

    def test_missing_payment_is_not_a_false_match(self):
        findings = self.payment_agent.analyze("missing-order-id", 0.0, 0.0)

        self.assertEqual(findings["payment_rows"], [])
        self.assertEqual(findings["payment_count"], 0)
        self.assertEqual(findings["payment_total_brl"], 0.0)
        self.assertFalse(findings["has_payment"])
        self.assertFalse(findings["payment_matches_order"])
        self.assertFalse(findings["valid_split_payment"])


if __name__ == "__main__":
    unittest.main()
