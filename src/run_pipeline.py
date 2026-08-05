"""Main execution runner to execute all 50 cases through the Multi-Agent pipeline."""

import os
import sys
import shutil
from pathlib import Path

# Ensure root and src are in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.coordinator import CoordinatorAgent, TRACE_FILE

def main():
    # Ensure UTF-8 printing on Windows
    if sys.platform.startswith("win"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("==================================================")
    print("Executing E-commerce Dispute Resolution Pipeline")
    print("==================================================")

    input_dir = ROOT / "input"
    output_dir = ROOT / "output"
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean up previous trace file if it exists to start fresh
    if TRACE_FILE.exists():
        print(f"Cleaning up previous trace file: {TRACE_FILE}")
        TRACE_FILE.unlink()

    case_files = sorted(list(input_dir.glob("EC_*.json")))
    if not case_files:
        print("ERROR: No test case files found in input/ directory.")
        sys.exit(1)

    print(f"Found {len(case_files)} cases to process.")
    
    coordinator = CoordinatorAgent()
    success_count = 0
    failure_count = 0

    for idx, case_path in enumerate(case_files, 1):
        case_id = case_path.stem
        print(f"[{idx:02d}/{len(case_files)}] Processing {case_id}...", end="", flush=True)
        try:
            state = coordinator.run_case(str(case_path))
            if state.completed:
                success_count += 1
                primary_issue = state.final_context["policy_decision"]["primary_issue"]
                print(f" SUCCESS (issue: {primary_issue})")
            else:
                failure_count += 1
                print(" FAILED (state not completed)")
        except Exception as e:
            failure_count += 1
            print(f" FAILED (Error: {e})")

    print("\n================== SUMMARY ==================")
    print(f"Total Cases:   {len(case_files)}")
    print(f"Success Count: {success_count}")
    print(f"Failure Count: {failure_count}")
    print("=============================================")

    # Copy logging/trace.jsonl to trace.jsonl (root)
    root_trace = ROOT / "trace.jsonl"
    if TRACE_FILE.exists():
        shutil.copy2(TRACE_FILE, root_trace)
        print(f"Trace log written to {TRACE_FILE} and {root_trace}")

    if failure_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
