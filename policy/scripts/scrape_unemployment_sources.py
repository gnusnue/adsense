#!/usr/bin/env python3
"""Scrape official unemployment-benefit sources into raw files and Markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
from pathlib import Path

SOURCES: list[dict[str, str]] = [
    {
        "id": "ei_0201_overview",
        "name": "실업급여란",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0201Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_0202_eligibility",
        "name": "구직급여 지급대상",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0202Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_0203_amount",
        "name": "구직급여 지급액",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0203Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_0204_process",
        "name": "구직급여 지급절차",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0204Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_0213_online_qa",
        "name": "인터넷 실업인정 Q&A",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0213Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_0214_fraud",
        "name": "부정수급 안내",
        "url": "https://edrm.ei.go.kr/ei/eih/eg/pb/pbPersonBnef/retrievePb0214Info.do",
        "scope_start": "<!-- 콘텐츠 시작-->",
        "scope_end": "<!--콘텐츠 마침-->",
    },
    {
        "id": "ei_manual_mobile_pdf",
        "name": "실업인정 인터넷 신청 매뉴얼(모바일)",
        "url": "https://edrm.ei.go.kr/ei/common/dnfile/munual_mobile.pdf",
    },
    {
        "id": "eiac_calculator",
        "name": "실업급여 모의계산",
        "url": "https://eiac.ei.go.kr/ei/m/pf/MOW-PF-00-180-C.html",
    },
    {
        "id": "ei_stats",
        "name": "고용보험 통계",
        "url": "https://edrm.ei.go.kr/ei/eih/st/retrieveAdOfferList.do",
        "scope_start": "<div id=\"content\">",
        "scope_end": "<div id=\"footer\">",
    },
    {
        "id": "work24_main",
        "name": "고용24 메인",
        "url": "https://www.work24.go.kr/cm/main.do",
        "extract_text": "false",
    },
    {
        "id": "law_employment_insurance_act",
        "name": "고용보험법 조문",
        "url": "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0050&lsiSeq=276843&urlMode=lsScJoRltInfoR",
        "scope_start": "<!-- 본문 -->",
        "scope_end": "<!-- 본문 //-->",
    },
    {
        "id": "law_enforcement_decree",
        "name": "고용보험법 시행령 조문",
        "url": "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0074&lsiSeq=281219&urlMode=lsScJoRltInfoR",
        "scope_start": "<!-- 본문 -->",
        "scope_end": "<!-- 본문 //-->",
    },
    {
        "id": "law_enforcement_rule",
        "name": "고용보험법 시행규칙 조문",
        "url": "https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0089&lsiSeq=282391&urlMode=lsScJoRltInfoR",
        "scope_start": "<!-- 본문 -->",
        "scope_end": "<!-- 본문 //-->",
    },
]

NEWLINE_TAGS = [
    "br",
    "p",
    "div",
    "li",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "section",
    "article",
]


def extract_title(page_html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    title = html.unescape(match.group(1))
    return re.sub(r"\s+", " ", title).strip()


def clean_html_text(page_html: str) -> str:
    text = re.sub(r"<!--.*?-->", " ", page_html, flags=re.DOTALL)
    text = re.sub(
        r"<(script|style|noscript|svg|canvas|iframe)[^>]*>.*?</\1>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for tag in NEWLINE_TAGS:
        text = re.sub(rf"</?{tag}\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines: list[str] = []
    for line in text.split("\n"):
        compact = re.sub(r"[ \t]+", " ", line).strip()
        if compact:
            cleaned_lines.append(compact)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_md_text(text: str) -> str:
    safe = text.replace("```", "'''")
    return safe


def apply_scope(page_html: str, source: dict[str, str]) -> tuple[str, bool]:
    start = source.get("scope_start")
    end = source.get("scope_end")
    if not start or not end:
        return page_html, False

    start_idx = page_html.find(start)
    if start_idx < 0:
        return page_html, False
    start_idx += len(start)

    end_idx = page_html.find(end, start_idx)
    if end_idx < 0:
        return page_html[start_idx:], True
    return page_html[start_idx:end_idx], True


def read_html_file(raw_path: Path) -> str:
    payload = raw_path.read_bytes()
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_with_curl(url: str, raw_path: Path, header_path: Path) -> tuple[int, str]:
    cmd = [
        "curl",
        "-L",
        "-sS",
        "-D",
        str(header_path),
        "-o",
        str(raw_path),
        "-w",
        "%{http_code}|%{content_type}",
        url,
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "curl failed").strip()
        raise RuntimeError(message)

    status_code = 0
    content_type = ""
    status_and_type = (result.stdout or "").strip().split("|", maxsplit=1)
    if status_and_type and status_and_type[0].isdigit():
        status_code = int(status_and_type[0])
    if len(status_and_type) > 1:
        content_type = status_and_type[1].strip()

    header_text = header_path.read_text(encoding="utf-8", errors="replace")
    for line in header_text.splitlines():
        if line.lower().startswith("content-type:"):
            content_type = line.split(":", maxsplit=1)[1].strip()
    return status_code, content_type


def scrape(output_dir: Path, max_chars: int) -> tuple[list[dict[str, str]], list[str]]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, str]] = []
    md_sections: list[str] = []
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    for i, source in enumerate(SOURCES, start=1):
        record: dict[str, str] = {
            "id": source["id"],
            "name": source["name"],
            "url": source["url"],
            "fetched_at_utc": now_iso,
        }
        try:
            tmp_raw_path = raw_dir / f"{source['id']}.raw"
            header_path = raw_dir / f"{source['id']}.headers.txt"
            status_code, content_type = fetch_with_curl(source["url"], tmp_raw_path, header_path)

            record["status_code"] = str(status_code)
            record["content_type"] = content_type

            is_pdf = "pdf" in content_type.lower() or source["url"].lower().endswith(".pdf")
            extension = "pdf" if is_pdf else "html"
            raw_path = raw_dir / f"{source['id']}.{extension}"
            tmp_raw_path.replace(raw_path)
            if header_path.exists():
                header_path.unlink()

            record["raw_file"] = str(raw_path)
            record["raw_bytes"] = str(raw_path.stat().st_size)

            section_lines = [
                f"## {i}. {source['name']}",
                f"- URL: {source['url']}",
                f"- 수집시각(UTC): {now_iso}",
                f"- HTTP 상태: {status_code}",
                f"- Content-Type: {record['content_type'] or 'N/A'}",
                f"- 원본 파일: `{raw_path}`",
            ]

            if is_pdf:
                section_lines.append("- 추출 상태: PDF 원본만 저장 (텍스트 추출 미적용)")
            else:
                should_extract_text = source.get("extract_text", "true").lower() != "false"
                raw_html = read_html_file(raw_path)
                title = extract_title(raw_html)
                record["title"] = title

                if title:
                    section_lines.append(f"- 페이지 제목: {title}")

                if not should_extract_text:
                    section_lines.append("- 추출 상태: 텍스트 추출 생략(랜딩/포털 페이지)")
                else:
                    scoped_html, applied_scope = apply_scope(raw_html, source)
                    cleaned = clean_html_text(scoped_html)
                    record["text_chars"] = str(len(cleaned))
                    record["scope_applied"] = "true" if applied_scope else "false"

                    if applied_scope:
                        section_lines.append("- 본문 추출: 지정 마커 기준 본문 영역만 추출")
                    else:
                        section_lines.append("- 본문 추출: 전체 HTML에서 정제")

                    excerpt = cleaned[:max_chars]
                    if len(cleaned) > max_chars:
                        excerpt += "\n\n[...중략...]"
                    section_lines.extend(
                        [
                            "",
                            "### 추출 텍스트",
                            "",
                            normalize_md_text(excerpt) if excerpt else "(추출된 텍스트 없음)",
                        ]
                    )

            md_sections.append("\n".join(section_lines))
        except Exception as exc:  # noqa: BLE001
            record["error"] = str(exc)
            md_sections.append(
                "\n".join(
                    [
                        f"## {i}. {source['name']}",
                        f"- URL: {source['url']}",
                        f"- 수집시각(UTC): {now_iso}",
                        f"- 오류: {exc}",
                    ]
                )
            )

        records.append(record)

    return records, md_sections


def build_output_dir(user_output_dir: str | None) -> Path:
    if user_output_dir:
        return Path(user_output_dir)
    today = dt.date.today().isoformat()
    return Path("artifacts/latest/research") / f"unemployment-benefits-{today}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", help="Output directory for scraped files and markdown.")
    parser.add_argument(
        "--max-chars-per-page",
        type=int,
        default=8000,
        help="Maximum extracted characters per HTML page to include in markdown.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = build_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records, sections = scrape(output_dir=output_dir, max_chars=args.max_chars_per_page)

    md_path = output_dir / "sources.md"
    md_header = [
        "# 실업급여 관련 공식 자료 스크래핑",
        "",
        f"- 생성일시(UTC): {dt.datetime.now(dt.timezone.utc).isoformat()}",
        f"- 대상 URL 수: {len(SOURCES)}",
        "- 비고: 본 문서는 원문 텍스트 자동 추출본이며, 법적 판단 전 원문 확인 필요",
        "",
    ]
    md_path.write_text("\n\n".join(md_header + sections) + "\n", encoding="utf-8")

    index_path = output_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "output_dir": str(output_dir),
                "count": len(records),
                "sources": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Saved: {md_path}")
    print(f"Saved: {index_path}")
    print(f"Raw dir: {output_dir / 'raw'}")


if __name__ == "__main__":
    main()
