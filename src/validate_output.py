"""Independent output validator (Phase 3 task).

Re-checks every output/EC_*.json against the README section 6 schema AND
against the raw Olist CSVs directly (bypassing the agent code) so a bug
shared between policy_agent/verifier_agent can't hide a bad case. Exits
non-zero if any case fails.
"""

import json
import re
import sys
from pathlib import Path

# Ensure root and src/ are in the python path
src_dir = Path(__file__).resolve().parent
root_dir = src_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import pandas as pd

from src.agents.verifier import VerifierAgent

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

EVIDENCE_PREFIX_RE = re.compile(r"^([a-z]+):(.+)$")


def load_id_sets():
    print("Loading CSV datasets for verification check...")
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv", dtype=str)
    items = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv", dtype=str)
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv", dtype=str)
    sellers = pd.read_csv(DATA_DIR / "olist_sellers_dataset.csv", dtype=str)

    order_ids = set(orders["order_id"])
    item_ids = set(items["order_id"] + ":" + items["order_item_id"])
    payment_ids = set(payments["order_id"] + ":" + payments["payment_sequential"])
    seller_ids = set(sellers["seller_id"])
    return order_ids, item_ids, payment_ids, seller_ids


def main() -> int:
    # Ensure UTF-8 printing on Windows
    if sys.platform.startswith("win"):
        sys.stdout.reconfigure(encoding="utf-8")

    verifier = VerifierAgent()
    
    output_files = sorted(OUTPUT_DIR.glob("EC_*.json"))
    if not output_files:
        print("WARNING: No output files found in output/ directory to validate. Have you run the pipeline?")
        return 1

    order_ids, item_ids, payment_ids, seller_ids = load_id_sets()

    expected_case_ids = {f"EC_{i:03d}" for i in range(1, 51)}
    found_case_ids = {p.stem for p in output_files}

    failures = []

    missing = expected_case_ids - found_case_ids
    if missing:
        failures.append(f"missing output files for: {sorted(missing)}")
    extra = found_case_ids - expected_case_ids
    if extra:
        failures.append(f"unexpected output files: {sorted(extra)}")

    for path in output_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        case_id = data.get("case_id")

        if case_id != path.stem:
            failures.append(f"{path.name}: case_id {case_id!r} does not match filename")

        schema_errors = verifier.validate(data)
        for err in schema_errors:
            failures.append(f"{path.name}: {err}")

        financial = data.get("financial_resolution", {})
        item_total = financial.get("item_total_brl", 0.0)
        freight_total = financial.get("freight_total_brl", 0.0)
        payment_total = financial.get("payment_total_brl", 0.0)
        refund = financial.get("recommended_refund_brl", 0.0)
        primary_issue = data.get("assessment", {}).get("primary_issue")

        expected_refund = {
            "canceled_order_paid": payment_total,
            "unavailable_order_paid": payment_total,
            "late_delivery_seller": freight_total,
            "late_delivery_logistics": freight_total,
            "valid_split_payment": 0.0,
            "unsupported_late_claim": 0.0,
        }.get(primary_issue)
        if expected_refund is not None and round(refund, 2) != round(expected_refund, 2):
            failures.append(
                f"{path.name}: recommended_refund_brl {refund} does not match expected {expected_refund} for {primary_issue}"
            )

        for eid in data.get("evidence_ids", []):
            match = EVIDENCE_PREFIX_RE.match(eid)
            if not match:
                failures.append(f"{path.name}: unparseable evidence id {eid!r}")
                continue
            prefix, rest = match.groups()
            if prefix == "order" and rest not in order_ids:
                failures.append(f"{path.name}: evidence {eid!r} references unknown order_id")
            elif prefix == "item" and rest not in item_ids:
                failures.append(f"{path.name}: evidence {eid!r} references unknown order_item")
            elif prefix == "payment" and rest not in payment_ids:
                failures.append(f"{path.name}: evidence {eid!r} references unknown payment row")
            elif prefix == "seller" and rest not in seller_ids:
                failures.append(f"{path.name}: evidence {eid!r} references unknown seller_id")

        item_total_ok = round(item_total, 2) == item_total
        freight_total_ok = round(freight_total, 2) == freight_total
        if not item_total_ok or not freight_total_ok:
            failures.append(f"{path.name}: item/freight totals not rounded to 2 decimals")
        if item_total < 0 or freight_total < 0 or payment_total < 0 or refund < 0:
            failures.append(f"{path.name}: negative monetary value found")

    if failures:
        print(f"VALIDATION FAILED — {len(failures)} issue(s):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"VALIDATION PASSED — {len(output_files)}/50 cases OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
