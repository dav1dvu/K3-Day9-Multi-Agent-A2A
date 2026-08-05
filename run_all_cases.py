from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List


def main() -> int:
    root = Path.cwd()
    sys.path.insert(0, str(root))

    from src.agents.coordinator import CoordinatorAgent, TRACE_FILE

    parser = argparse.ArgumentParser(
        description="Run the Coordinator pipeline for all EC_*.json cases under input/."
    )
    parser.add_argument(
        "--input-dir",
        default="input",
        help="Path to the directory containing EC_*.json inputs (default: input)",
    )
    parser.add_argument(
        "--pattern",
        default="EC_*.json",
        help="Filename glob pattern to select case files (default: EC_*.json)",
    )
    parser.add_argument(
        "--keep-trace",
        action="store_true",
        help="Do not remove existing logging/trace.jsonl before running.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop execution immediately when a case fails.",
    )
    args = parser.parse_args()

    input_dir = root / args.input_dir
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        return 1

    case_files: List[Path] = sorted(input_dir.glob(args.pattern))
    if not case_files:
        print(f"ERROR: No files matched {args.pattern} under {input_dir}")
        return 1

    trace_file = TRACE_FILE
    if trace_file.exists() and not args.keep_trace:
        trace_file.unlink()

    agent = CoordinatorAgent()
    print(f"Running {len(case_files)} cases through CoordinatorAgent...")

    failures: List[str] = []
    for case_file in case_files:
        print(f"Processing {case_file.name}...")
        try:
            agent.run_case(str(case_file))
        except Exception as exc:
            failures.append(f"{case_file.name}: {exc}")
            print(f"  FAILED: {exc}")
            if args.stop_on_error:
                break

    print("\n=== Summary ===")
    print(f"Cases processed: {len(case_files)}")
    if failures:
        print(f"Success: {len(case_files) - len(failures)}")
        print(f"Failures: {len(failures)}")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Success: all cases processed.")
    print(f"Output directory: {root / 'output'}")
    print(f"Trace file: {trace_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
