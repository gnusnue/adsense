#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ALLOWED_ROUTES = {"/", "/apply/", "/eligibility/", "/recognition/", "/income-report/", "/faq/"}
ALLOWED_SOURCES = {"top", "rising"}
ALLOWED_STATUS = {"idea", "live", "drop"}
MIN_RISING_COUNT = 6
FINAL_PICK_COUNT = 10
OFFICIAL_SOURCE_DOMAINS = ("work24.go.kr", "edrm.ei.go.kr", "moel.go.kr")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate weekly longtail artifacts")
    parser.add_argument(
        "--weekly-file",
        required=True,
        help="Path to weekly-YYYY-MM-DD.md",
    )
    parser.add_argument(
        "--backlog-file",
        default="unemployment/artifacts/latest/seo/longtail/keyword-backlog.csv",
        help="Path to keyword backlog csv",
    )
    parser.add_argument(
        "--impact-file",
        default="unemployment/artifacts/latest/seo/longtail/impact-log.csv",
        help="Path to impact log csv",
    )
    return parser.parse_args()


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def clean_route(value: str) -> str:
    return value.strip().strip("`").strip()


def is_checked_checkbox(md_text: str, label: str) -> bool:
    pattern = re.compile(rf"^\s*-\s*\[[xX]\]\s*{re.escape(label)}\s*$", flags=re.MULTILINE)
    return bool(pattern.search(md_text))


def is_todo_keyword(keyword: str) -> bool:
    value = keyword.strip().lower()
    return value.startswith("todo")


def parse_markdown_table(md_text: str, section_title: str) -> list[list[str]]:
    section = re.search(
        rf"^##\s+.*{re.escape(section_title)}.*$([\s\S]*?)(?=^##\s+|\Z)",
        md_text,
        flags=re.MULTILINE,
    )
    if not section:
        return []
    rows: list[list[str]] = []
    for line in section.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    if len(rows) < 2:
        return []
    # drop header and separator rows
    data_rows = []
    for cells in rows[2:]:
        if all(re.fullmatch(r"-*:?-+", c.replace(" ", "")) for c in cells):
            continue
        data_rows.append(cells)
    return data_rows


def validate_weekly_markdown(path: Path, failures: list[str]) -> list[dict[str, str]]:
    require(path.exists(), f"weekly file not found: {path}", failures)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    required_views = (
        "지난 12개월 / 대한민국 / 웹 검색",
        "지난 30일 / 대한민국 / 웹 검색",
        "지난 5년 / 대한민국 / 웹 검색",
    )
    for view in required_views:
        require(view in text, f"missing trends view checklist item: {view}", failures)
        require(is_checked_checkbox(text, view), f"trends checklist must be checked: {view}", failures)

    rows = parse_markdown_table(text, "최종 채택 10개")
    require(bool(rows), "failed to parse table in section '최종 채택 10개'", failures)
    require(len(rows) == FINAL_PICK_COUNT, f"final picks must be {FINAL_PICK_COUNT}, got {len(rows)}", failures)
    picks: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        require(len(row) >= 6, f"row {idx} in final picks must have at least 6 columns", failures)
        if len(row) < 6:
            continue
        keyword, route, score_text, source, status, reason = row[:6]
        record = {
            "keyword": keyword.strip(),
            "route": clean_route(route),
            "score": score_text.strip(),
            "source": source.strip().lower(),
            "status": status.strip().lower(),
            "reason": reason.strip(),
        }
        picks.append(record)

    seen_keywords: set[str] = set()
    rising_count = 0
    for pick in picks:
        keyword = pick["keyword"]
        route = pick["route"]
        source = pick["source"]
        status = pick["status"]
        score_text = pick["score"]

        require(keyword != "", "empty keyword found in final picks", failures)
        require(not is_todo_keyword(keyword), f"placeholder keyword is not allowed in final picks: {keyword}", failures)
        require(keyword not in seen_keywords, f"duplicate keyword in final picks: {keyword}", failures)
        seen_keywords.add(keyword)
        require(route in ALLOWED_ROUTES, f"invalid route in final picks: {route}", failures)
        require(source in ALLOWED_SOURCES, f"invalid source in final picks: {source}", failures)
        require(status in ALLOWED_STATUS, f"invalid status in final picks: {status}", failures)
        try:
            score = float(score_text)
        except ValueError:
            failures.append(f"invalid score in final picks: {score_text}")
            score = -1.0
        require(0.0 <= score <= 10.0, f"score out of range (0~10): {score_text}", failures)
        if source == "rising":
            rising_count += 1
    require(rising_count >= MIN_RISING_COUNT, f"rising keywords must be at least {MIN_RISING_COUNT}, got {rising_count}", failures)

    link_section = re.search(r"^##\s+6\)\s+공식 출처 링크\s*$([\s\S]*?)(?=^##\s+|\Z)", text, flags=re.MULTILINE)
    require(link_section is not None, "missing section '6) 공식 출처 링크'", failures)
    if link_section:
        urls = re.findall(r"https?://[^\s)]+", link_section.group(1))
        require(len(urls) >= 2, "official source links must include at least 2 URLs", failures)
        domain_hit = any(any(domain in url for domain in OFFICIAL_SOURCE_DOMAINS) for url in urls)
        require(domain_hit, "official source links must include at least one trusted domain", failures)

    return picks


def validate_csv_schema(path: Path, required_columns: list[str], failures: list[str]) -> list[dict[str, str]]:
    require(path.exists(), f"csv file not found: {path}", failures)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            failures.append(f"csv missing header: {path}")
            return []
        for col in required_columns:
            require(col in reader.fieldnames, f"csv missing required column '{col}': {path}", failures)
        return list(reader)


def validate_backlog(path: Path, picks: list[dict[str, str]], failures: list[str]) -> None:
    rows = validate_csv_schema(path, ["keyword", "route", "score", "source", "status"], failures)
    keyword_index: dict[str, dict[str, str]] = {}
    for row in rows:
        keyword = (row.get("keyword") or "").strip()
        route = clean_route((row.get("route") or ""))
        score_text = (row.get("score") or "").strip()
        source = (row.get("source") or "").strip().lower()
        status = (row.get("status") or "").strip().lower()
        if keyword:
            keyword_index[keyword] = row
        require(route in ALLOWED_ROUTES, f"invalid route in backlog row: {route}", failures)
        require(source in ALLOWED_SOURCES, f"invalid source in backlog row: {source}", failures)
        require(status in ALLOWED_STATUS, f"invalid status in backlog row: {status}", failures)
        try:
            score = float(score_text)
        except ValueError:
            failures.append(f"invalid score in backlog row: {score_text}")
            score = -1.0
        require(0.0 <= score <= 10.0, f"backlog score out of range (0~10): {score_text}", failures)

    for pick in picks:
        require(
            pick["keyword"] in keyword_index,
            f"selected keyword missing in backlog csv: {pick['keyword']}",
            failures,
        )


def validate_impact_log(path: Path, failures: list[str]) -> None:
    rows = validate_csv_schema(
        path,
        ["week", "keyword", "page", "impressions", "clicks", "ctr", "position", "decision"],
        failures,
    )
    for row in rows:
        page = (row.get("page") or "").strip()
        page = clean_route(page)
        if page:
            require(page in ALLOWED_ROUTES, f"invalid page(route) in impact log row: {page}", failures)


def main() -> int:
    args = parse_args()
    failures: list[str] = []

    weekly_file = Path(args.weekly_file).resolve()
    backlog_file = Path(args.backlog_file).resolve()
    impact_file = Path(args.impact_file).resolve()

    picks = validate_weekly_markdown(weekly_file, failures)
    validate_backlog(backlog_file, picks, failures)
    validate_impact_log(impact_file, failures)

    if failures:
        print("[FAIL] longtail quality checks failed:")
        for issue in failures:
            print(f" - {issue}")
        return 1

    print("[OK] longtail quality checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
