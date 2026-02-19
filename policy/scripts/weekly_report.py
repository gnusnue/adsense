#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from runtime_guard import enforce_venv

ROOT = Path(__file__).resolve().parents[1]


def safe_read(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def main() -> int:
    enforce_venv()
    latest = ROOT / "artifacts" / "latest"
    quality = safe_read(latest / "quality" / "report.json")
    monetization = safe_read(latest / "monetization" / "report.json")
    publish = safe_read(latest / "publish" / "report.json")
    run_meta = safe_read(latest / "run_meta.json")

    print("# Weekly Ops Snapshot")
    print(f"- run_id: {run_meta.get('run_id', 'n/a')}")
    print(f"- status: {run_meta.get('status', 'n/a')}")
    print(f"- generated_pages: {publish.get('generated_pages', 'n/a')}")
    print(f"- quality_decision: {quality.get('decision', 'n/a')}")
    print(f"- monetization_decision: {monetization.get('decision', 'n/a')}")
    metrics = quality.get("metrics", {})
    if isinstance(metrics, dict):
        print(f"- null_ratio: {metrics.get('null_ratio', 'n/a')}")
        print(f"- duplicate_ratio: {metrics.get('duplicate_ratio', 'n/a')}")
        print(f"- broken_link_ratio: {metrics.get('broken_link_ratio', 'n/a')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
