#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from runtime_guard import enforce_venv
from pipeline_lib import ROOT, now_iso, write_json


ANNOUNCEMENT_ENDPOINT = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load K-Startup announcement data into raw/canonical")
    parser.add_argument("--cutoff-date", default="20250701", help="Include rows where start_date >= cutoff (YYYYMMDD)")
    parser.add_argument("--per-page", type=int, default=200, help="Page size for source API")
    parser.add_argument("--max-pages", type=int, default=300, help="Max pages to fetch")
    parser.add_argument("--site-base-url", default="https://cbbxs.com", help="Canonical base URL for generated records")
    return parser.parse_args()


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key and key not in os.environ:
            os.environ[key] = value


def safe_date(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) >= 8:
        return digits[:8]
    return ""


def parse_col_item(item: ET.Element) -> dict[str, str]:
    row: dict[str, str] = {}
    for col in item.findall("col"):
        key = (col.attrib.get("name") or "").strip()
        if not key:
            continue
        row[key] = (col.text or "").strip()
    return row


def fetch_page(service_key: str, page: int, per_page: int) -> list[dict[str, str]]:
    params = {
        "serviceKey": service_key,
        "page": page,
        "perPage": per_page,
    }
    url = ANNOUNCEMENT_ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    root = ET.fromstring(body)
    items = root.findall("./data/item")
    return [parse_col_item(item) for item in items]


def fetch_all(service_key: str, per_page: int, max_pages: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page in range(1, max_pages + 1):
        page_rows: list[dict[str, str]] = []
        last_error: Exception | None = None
        for _ in range(3):
            try:
                page_rows = fetch_page(service_key, page, per_page)
                last_error = None
                break
            except (HTTPError, URLError, ET.ParseError) as exc:
                last_error = exc
                time.sleep(0.4)
        if last_error is not None:
            if page == 1:
                raise last_error
            # Some public APIs return 5xx after the last available page.
            break
        if not page_rows:
            break
        rows.extend(page_rows)
        if len(page_rows) < per_page:
            break
    return rows


def normalize_official_url(row: dict[str, str]) -> str:
    for key in ("detl_pg_url", "biz_aply_url", "biz_gdnc_url"):
        value = (row.get(key) or "").strip()
        if not value:
            continue
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return "https://" + value.lstrip("/")
    return "https://www.k-startup.go.kr"


def build_period_text(row: dict[str, str]) -> str:
    start = safe_date(row.get("pbanc_rcpt_bgng_dt", ""))
    end = safe_date(row.get("pbanc_rcpt_end_dt", ""))
    if start and end:
        return f"{start} ~ {end}"
    if start:
        return f"{start} ~ 공고문 참고"
    return "공고문 참고"


def to_canonical(rows: list[dict[str, str]], cutoff_date: str) -> list[dict[str, Any]]:
    now = now_iso()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        start = safe_date(row.get("pbanc_rcpt_bgng_dt", ""))
        if not start or start < cutoff_date:
            continue
        policy_id = (row.get("pbanc_sn") or row.get("id") or "").strip()
        title = (row.get("biz_pbanc_nm") or "").strip()
        if not policy_id or not title:
            continue
        if policy_id in seen:
            continue
        seen.add(policy_id)
        status = "active" if (row.get("rcrt_prgs_yn") or "").strip().upper() == "Y" else "closed"
        out.append(
            {
                "policy_id": policy_id,
                "title": title,
                "region": (row.get("supt_regin") or "전국").strip() or "전국",
                "target_group": (row.get("aply_trgt") or "일반").strip() or "일반",
                "category": (row.get("supt_biz_clsfc") or "창업").strip() or "창업",
                "eligibility_text": (row.get("aply_trgt_ctnt") or "공고문 참고").strip() or "공고문 참고",
                "benefit_text": (row.get("pbanc_ctnt") or "공고문 참고").strip() or "공고문 참고",
                "application_period_text": build_period_text(row),
                "official_url": normalize_official_url(row),
                "source_org": (row.get("sprv_inst") or row.get("pbanc_ntrp_nm") or "kstartup").strip() or "kstartup",
                "source_updated_at": start or now,
                "last_checked_at": now,
                "status": status,
                "source_api": "kr_policy_kstartup_announcement",
            }
        )
    return out


def rotate_and_write_canonical(canonical_rows: list[dict[str, Any]]) -> None:
    latest_path = ROOT / "data" / "canonical" / "latest" / "policies.json"
    previous_path = ROOT / "data" / "canonical" / "previous" / "policies.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    previous_path.parent.mkdir(parents=True, exist_ok=True)
    if latest_path.exists():
        shutil.copy2(latest_path, previous_path)
    write_json(latest_path, canonical_rows)


def main() -> int:
    enforce_venv()
    args = parse_args()
    load_env(ROOT / ".env.local")

    service_key = (os.getenv("DATA_GO_KR_API_KEY") or "").strip()
    if not service_key:
        raise RuntimeError("DATA_GO_KR_API_KEY is required")

    all_rows = fetch_all(service_key, args.per_page, args.max_pages)
    canonical_rows = to_canonical(all_rows, args.cutoff_date)

    today = dt.date.today().isoformat()
    raw_dir = ROOT / "data" / "raw" / today
    raw_dir.mkdir(parents=True, exist_ok=True)
    write_json(raw_dir / "kr_policy_kstartup_announcement_all.json", all_rows)
    write_json(raw_dir / f"kr_policy_kstartup_announcement_from_{args.cutoff_date}.json", canonical_rows)

    rotate_and_write_canonical(canonical_rows)

    summary = {
        "cutoff_date": args.cutoff_date,
        "fetched_rows": len(all_rows),
        "canonical_rows": len(canonical_rows),
        "saved_raw_dir": str(raw_dir),
        "canonical_latest": str(ROOT / "data" / "canonical" / "latest" / "policies.json"),
        "source_endpoint": ANNOUNCEMENT_ENDPOINT,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
