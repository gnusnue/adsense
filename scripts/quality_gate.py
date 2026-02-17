#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from runtime_guard import enforce_venv
from pipeline_lib import ROOT, compute_quality_metrics, evaluate_quality, read_json, validate_schema


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run quality gate checks")
    parser.add_argument("--canonical", required=True, help="Path to canonical policies.json")
    parser.add_argument("--site-dir", required=True, help="Path to generated static site directory")
    parser.add_argument("--previous", default="", help="Optional previous canonical policies.json")
    return parser.parse_args()


def main() -> int:
    enforce_venv()
    args = parse_args()
    canonical_path = Path(args.canonical)
    site_dir = Path(args.site_dir)
    previous_path = Path(args.previous) if args.previous else None

    if not canonical_path.exists():
        print(f"[ERROR] canonical file not found: {canonical_path}")
        return 1
    if not site_dir.exists():
        print(f"[ERROR] site dir not found: {site_dir}")
        return 1

    canonical = read_json(canonical_path)
    if not isinstance(canonical, list):
        print("[ERROR] canonical must be list")
        return 1

    previous_count = 0
    if previous_path and previous_path.exists():
        prev = read_json(previous_path)
        if isinstance(prev, list):
            previous_count = len(prev)

    metrics = compute_quality_metrics(canonical, site_dir=site_dir)
    official_url_missing = sum(1 for r in canonical if not str(r.get("official_url", "")).strip())
    report = evaluate_quality(metrics, previous_count, len(canonical), official_url_missing)

    schema_errors = validate_schema(report, ROOT / "schemas" / "quality.v1.schema.json")
    if schema_errors:
        print("[ERROR] quality schema invalid")
        for err in schema_errors[:5]:
            print(f"- {err}")
        return 1

    print(f"quality decision: {report['decision']}")
    print(f"metrics: {report['metrics']}")
    if report["hard_fail"]:
        print("hard_fail:")
        for item in report["hard_fail"]:
            print(f"- {item}")
        return 2
    if report["soft_fail"]:
        print("soft_fail:")
        for item in report["soft_fail"]:
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
