"""Verification script for Phase 1.

Instantiates OrderSellerAgent and DeliveryAgent, tests them with sample orders
representing different statuses (delivered, canceled, unavailable), and checks if the
outputs match the required data contracts in architecture.md.
"""

import sys
import pandas as pd
from order_seller_agent import OrderSellerAgent
from delivery_agent import DeliveryAgent

# Ensure UTF-8 printing on Windows
if sys.platform.startswith("win"):
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    print("=== STARTING PHASE 1 VERIFICATION ===")
    
    # 1. Initialize Agents
    print("\n[Step 1] Initializing agents...")
    try:
        order_seller = OrderSellerAgent(data_dir="data")
        delivery = DeliveryAgent()
        print("Success: Agents initialized successfully.")
    except Exception as e:
        print(f"Error initializing agents: {e}")
        sys.exit(1)
        
    # 2. Pick sample orders from datasets
    print("\n[Step 2] Selecting sample orders for testing...")
    orders_df = pd.read_csv("data/olist_orders_dataset.csv", nrows=100)
    
    # Let's find one delivered order, one canceled, and one unavailable
    delivered_orders = orders_df[orders_df["order_status"] == "delivered"]
    canceled_orders = orders_df[orders_df["order_status"] == "canceled"]
    unavailable_orders = orders_df[orders_df["order_status"] == "unavailable"]
    
    test_cases = []
    if not delivered_orders.empty:
        test_cases.append(("delivered", delivered_orders.iloc[0]["order_id"]))
    if not canceled_orders.empty:
        test_cases.append(("canceled", canceled_orders.iloc[0]["order_id"]))
    if not unavailable_orders.empty:
        test_cases.append(("unavailable", unavailable_orders.iloc[0]["order_id"]))
        
    # If any is empty, let's fallback to some default rows
    while len(test_cases) < 3 and len(orders_df) > len(test_cases):
        oid = orders_df.iloc[len(test_cases)]["order_id"]
        status = orders_df.iloc[len(test_cases)]["order_status"]
        if (status, oid) not in test_cases:
            test_cases.append((status, oid))
            
    print(f"Selected {len(test_cases)} test cases:")
    for status, oid in test_cases:
        print(f" - Order ID: {oid} (Status: {status})")
        
    # 3. Execute analysis
    print("\n[Step 3] Running analyses and validating data contracts...")
    
    # Required keys according to architecture.md
    expected_order_keys = {
        "order_id", "order_status", "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date", "items", "item_total_brl", "freight_total_brl",
        "seller_ids", "customer_id"
    }
    
    expected_delivery_keys = {
        "order_id", "order_estimated_delivery_date", "order_delivered_customer_date",
        "order_delivered_carrier_date", "is_late_delivery", "seller_shipping_limits",
        "any_seller_late", "responsible_party"
    }
    
    for status, oid in test_cases:
        print(f"\n--- Testing Order: {oid} ({status}) ---")
        
        # Run Order & Seller Agent
        print("Running OrderSellerAgent...")
        findings = order_seller.analyze(oid)
        
        # Check keys
        missing_order_keys = expected_order_keys - set(findings.keys())
        if missing_order_keys:
            print(f"WARNING: Missing keys in OrderSellerAgent findings: {missing_order_keys}")
        else:
            print("OrderSellerAgent findings contain all required keys.")
            
        print(f"  Order Status: {findings['order_status']}")
        print(f"  Items Count: {len(findings['items'])}")
        print(f"  Item Total: {findings['item_total_brl']} BRL")
        print(f"  Freight Total: {findings['freight_total_brl']} BRL")
        print(f"  Seller IDs: {findings['seller_ids']}")
        
        # Run Delivery Agent
        print("Running DeliveryAgent...")
        deliv_findings = delivery.analyze(findings)
        
        # Check keys
        missing_deliv_keys = expected_delivery_keys - set(deliv_findings.keys())
        if missing_deliv_keys:
            print(f"WARNING: Missing keys in DeliveryFindings: {missing_deliv_keys}")
        else:
            print("DeliveryAgent findings contain all required keys.")
            
        print(f"  Is Late Delivery: {deliv_findings['is_late_delivery']}")
        print(f"  Any Seller Late: {deliv_findings['any_seller_late']}")
        print(f"  Responsible Party: {deliv_findings['responsible_party']}")
        
    print("\n=== PHASE 1 VERIFICATION COMPLETED ===")

if __name__ == "__main__":
    main()
