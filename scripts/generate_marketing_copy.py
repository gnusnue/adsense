#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
from typing import Any

from runtime_guard import enforce_venv
from pipeline_lib import ROOT, now_iso, read_json, write_json


AMOUNT_PATTERNS = [
    re.compile(r"(연\s*\d[\d,]*(?:\.\d+)?\s*(?:원|천원|만원|억 원|억원))"),
    re.compile(r"(\d[\d,]*(?:\.\d+)?\s*(?:원|천원|만원|억 원|억원))"),
    re.compile(r"(\d[\d,]*(?:\.\d+)?\s*%)"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate marketing copy from canonical policies")
    parser.add_argument("--input", default="data/canonical/latest/policies.json", help="Input canonical JSON path")
    parser.add_argument(
        "--output",
        default="artifacts/latest/content/marketing_copy.json",
        help="Output JSON path for generated copy",
    )
    parser.add_argument("--top-n", type=int, default=200, help="Number of records to generate copy for")
    parser.add_argument("--style", default="benefit-first", choices=["benefit-first"], help="Copy style preset")
    return parser.parse_args()


def clean_text(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_yyyymmdd(value: str) -> dt.date | None:
    digits = "".join(ch for ch in clean_text(value) if ch.isdigit())
    if len(digits) < 8:
        return None
    text = digits[:8]
    try:
        return dt.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def format_date_yyyy_mm_dd(value: str) -> str:
    parsed = parse_yyyymmdd(value)
    if parsed is None:
        return clean_text(value)
    return parsed.isoformat()


def parse_period(period_text: str) -> tuple[dt.date | None, dt.date | None]:
    tokens = re.findall(r"\d{8}", clean_text(period_text))
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return parse_yyyymmdd(tokens[0]), None
    return parse_yyyymmdd(tokens[0]), parse_yyyymmdd(tokens[1])


def format_period(period_text: str) -> str:
    start, end = parse_period(period_text)
    if start and end:
        return f"{start.isoformat()} ~ {end.isoformat()}"
    if start:
        return f"{start.isoformat()} ~ 공고문 참고"
    return clean_text(period_text) or "공고문 참고"


def first_sentence(text: str) -> str:
    if not text:
        return ""
    # Prefer first complete sentence; fallback to first 120 chars.
    parts = re.split(r"(?<=[.!?])\s+", text)
    picked = parts[0].strip() if parts else ""
    if not picked:
        return text[:120].strip()
    if len(picked) > 140:
        return picked[:140].rstrip() + "..."
    return picked


def compact_title(title: str) -> str:
    text = clean_text(title)
    text = re.sub(r"^\d{4}년\s*", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def shorten(text: str, limit: int) -> str:
    value = clean_text(text)
    if len(value) <= limit:
        return value
    return value[: max(limit - 1, 0)].rstrip() + "…"


def extract_amount_hook(*texts: str) -> str:
    for text in texts:
        candidate = clean_text(text)
        if not candidate:
            continue
        for pattern in AMOUNT_PATTERNS:
            match = pattern.search(candidate)
            if match:
                return clean_text(match.group(1))
    return ""


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def date_score(row: dict[str, Any]) -> int:
        digits = "".join(ch for ch in clean_text(row.get("source_updated_at", "")) if ch.isdigit())
        if len(digits) >= 8:
            return int(digits[:8])
        return 0

    def info_score(row: dict[str, Any]) -> int:
        return len(clean_text(row.get("benefit_text"))) + len(clean_text(row.get("eligibility_text")))

    return sorted(
        rows,
        key=lambda row: (
            clean_text(row.get("status")).lower() != "active",
            -date_score(row),
            -info_score(row),
        ),
    )


def primary_target(target_text: str) -> str:
    cleaned = clean_text(target_text)
    if not cleaned:
        return "신청자"
    for token in re.split(r"[,/·ㆍ|]", cleaned):
        part = token.strip()
        if part:
            return part
    return cleaned


def resolve_deadline_hook(period_text: str, status: str, today: dt.date) -> tuple[str, int | None]:
    _, end = parse_period(period_text)
    if status != "active":
        return "접수 마감", None
    if end is None:
        return "신청 일정 확인", None
    days_left = (end - today).days
    if days_left < 0:
        return "접수 마감", days_left
    if days_left <= 3:
        return f"마감 임박 D-{days_left}", days_left
    if days_left <= 7:
        return f"마감 D-{days_left}", days_left
    if days_left <= 14:
        return "2주 내 마감", days_left
    return f"{end.isoformat()}까지", days_left


def pick_template_index(policy_id: str, size: int) -> int:
    if size <= 0:
        return 0
    digits = "".join(ch for ch in policy_id if ch.isdigit())
    if digits:
        return int(digits) % size
    return len(policy_id) % size


def build_copy(row: dict[str, Any], style: str) -> dict[str, Any]:
    title = clean_text(row.get("title")) or "지원사업 공고"
    short_title = compact_title(title)
    benefit = clean_text(row.get("benefit_text")) or "지원 내용은 공고문 참고"
    target = clean_text(row.get("target_group")) or "공고문 참고"
    period_raw = clean_text(row.get("application_period_text")) or "공고문 참고"
    period = format_period(period_raw)
    status = clean_text(row.get("status")).lower()
    region = clean_text(row.get("region")) or "전국"
    policy_id = clean_text(row.get("policy_id"))
    target_one = primary_target(target)
    today = dt.date.today()

    amount_hook = extract_amount_hook(
        clean_text(row.get("benefit_text")),
        clean_text(row.get("eligibility_text")),
        title,
    )
    deadline_hook, days_left = resolve_deadline_hook(period_raw, status, today)

    templates = [
        f"[{deadline_hook}] {region} {target_one} 지원사업 | {short_title}",
        f"{amount_hook + ' 혜택' if amount_hook else deadline_hook}: {short_title}",
        f"{target_one} 필수 확인: {short_title} ({period})",
        f"{region} {short_title} | 지원대상·신청기간 한눈에",
    ]
    headline = shorten(templates[pick_template_index(policy_id or short_title, len(templates))], 68)
    if style == "benefit-first" and amount_hook:
        headline = shorten(f"[{deadline_hook}] {amount_hook} 혜택 가능? {short_title}", 68)

    summary = f"{first_sentence(benefit)} 대상: {target}. 신청 기간: {period}."
    if status == "closed":
        summary = f"접수 마감 공고입니다. {summary}"

    cta = "신청 전 지원 자격·제출서류·일정을 공식 공고에서 확인하세요."

    alternatives = [
        shorten(f"[{deadline_hook}] {target_one} 지원 대상·기간 정리", 62),
        shorten(f"{amount_hook + ' 혜택,' if amount_hook else ''} 놓치기 쉬운 신청 조건: {short_title}", 62),
        shorten(f"{region} {target_one} 신청 전 체크포인트 | {short_title}", 62),
    ]

    return {
        "policy_id": policy_id,
        "source_title": title,
        "headline": headline,
        "summary": summary,
        "cta": cta,
        "alternatives": alternatives,
        "application_period_text": period,
        "status": status,
        "official_url": clean_text(row.get("official_url")),
        "source_org": clean_text(row.get("source_org")),
        "meta": {
            "style": style,
            "used_amount_hook": bool(amount_hook),
            "amount_hook": amount_hook,
            "deadline_hook": deadline_hook,
            "days_left": days_left,
        },
    }


def main() -> int:
    enforce_venv()
    args = parse_args()
    input_path = ROOT / args.input
    output_path = ROOT / args.output

    rows = read_json(input_path)
    if not isinstance(rows, list):
        raise RuntimeError("input canonical must be a list")

    selected = sort_rows([row for row in rows if isinstance(row, dict)])[: max(args.top_n, 0)]
    copies = [build_copy(row, args.style) for row in selected]

    result = {
        "generated_at": now_iso(),
        "input": str(input_path),
        "output": str(output_path),
        "style": args.style,
        "total_input_rows": len(rows),
        "generated_rows": len(copies),
        "items": copies,
    }
    write_json(output_path, result)
    print(
        f"generated marketing copy: {len(copies)} items -> {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
