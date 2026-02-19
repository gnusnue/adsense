#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_POLICY_FIELDS = [
    "policy_id",
    "title",
    "region",
    "target_group",
    "category",
    "eligibility_text",
    "benefit_text",
    "application_period_text",
    "official_url",
    "source_org",
    "source_updated_at",
    "last_checked_at",
    "status",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json_subset_yaml(path: Path) -> dict[str, Any]:
    # YAML superset: config file is written in JSON-compatible YAML.
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text)


def validate_schema(instance: Any, schema_path: Path) -> list[str]:
    if jsonschema is None:
        return []
    schema = read_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    out: list[str] = []
    for err in errors:
        out.append(f"{list(err.absolute_path)}: {err.message}")
    return out


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "unknown"


def read_items_path(payload: Any, items_path: str) -> list[dict[str, Any]]:
    if items_path == "":
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        return []
    cur = payload
    for token in items_path.split("."):
        if isinstance(cur, dict) and token in cur:
            cur = cur[token]
        else:
            return []
    if isinstance(cur, list):
        return [x for x in cur if isinstance(x, dict)]
    return []


def apply_auth(url: str, auth: dict[str, Any]) -> str:
    auth_type = (auth or {}).get("type", "none")
    if auth_type == "none":
        return url
    if auth_type == "query_key":
        env_key = auth.get("env_key")
        param_name = auth.get("param_name", "serviceKey")
        value = os.getenv(env_key or "")
        if not value:
            raise RuntimeError(f"missing secret env: {env_key}")
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        query[param_name] = [value]
        new_query = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )
    raise RuntimeError(f"unsupported auth type: {auth_type}")


def build_url(base: str, params: dict[str, Any]) -> str:
    if not params:
        return base
    parsed = urllib.parse.urlparse(base)
    query = urllib.parse.parse_qs(parsed.query)
    for k, v in params.items():
        query[k] = [str(v)]
    new_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )


def fetch_source(source: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_id = source["source_id"]
    kind = source.get("kind")
    mapping = source.get("mapping", {})
    items_path = mapping.get("items_path", "")
    pagination = source.get("pagination", {"mode": "none"})
    report = {"source_id": source_id, "ok": False, "rows": 0, "error": None}

    try:
        if kind == "file_json":
            payload = read_json(ROOT / source["endpoint"])
            items = read_items_path(payload, items_path) if items_path else payload
            if isinstance(items, list):
                rows = [x for x in items if isinstance(x, dict)]
            else:
                rows = []
            report["ok"] = True
            report["rows"] = len(rows)
            return rows, report

        if kind == "http_json":
            rows: list[dict[str, Any]] = []
            mode = pagination.get("mode", "none")
            if mode == "none":
                url = build_url(source["endpoint"], source.get("params", {}))
                url = apply_auth(url, source.get("auth", {}))
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                rows = read_items_path(payload, items_path)
            elif mode == "page":
                page_param = pagination.get("page_param", "page")
                size_param = pagination.get("size_param", "perPage")
                start_page = int(pagination.get("start_page", 1))
                max_pages = int(pagination.get("max_pages", 3))
                page_size = int(source.get("params", {}).get(size_param, 100))
                for page in range(start_page, start_page + max_pages):
                    params = dict(source.get("params", {}))
                    params[page_param] = page
                    params[size_param] = page_size
                    url = build_url(source["endpoint"], params)
                    url = apply_auth(url, source.get("auth", {}))
                    req = urllib.request.Request(url, method="GET")
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        payload = json.loads(resp.read().decode("utf-8"))
                    part = read_items_path(payload, items_path)
                    rows.extend(part)
                    if len(part) < page_size:
                        break
            else:
                raise RuntimeError(f"unsupported pagination mode: {mode}")

            report["ok"] = True
            report["rows"] = len(rows)
            return rows, report
        raise RuntimeError(f"unsupported source kind: {kind}")
    except Exception as exc:  # noqa: BLE001
        report["error"] = str(exc)
        return [], report


def normalize_records(
    source_rows: dict[str, list[dict[str, Any]]],
    source_defs: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_map = {s["source_id"]: s for s in source_defs}
    now = now_iso()
    canonical: list[dict[str, Any]] = []

    def pick_row_value(
        row: dict[str, Any],
        mapped_key: Any,
        default_key: str,
        fallback: str = "",
    ) -> str:
        keys: list[str] = []
        if isinstance(mapped_key, list):
            keys = [str(k).strip() for k in mapped_key if str(k).strip()]
        elif isinstance(mapped_key, str) and mapped_key.strip():
            keys = [mapped_key.strip()]
        else:
            keys = [default_key]

        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return fallback

    for source_id, rows in source_rows.items():
        src = source_map[source_id]
        mapping = src.get("mapping", {})
        fallback_official_url = str(src.get("fallback_official_url", "")).strip()
        for row in rows:
            policy_id = pick_row_value(row, mapping.get("id_field", "id"), "id")
            title = pick_row_value(row, mapping.get("title_field", "title"), "title")
            if not policy_id:
                seed_region = pick_row_value(row, mapping.get("region_field", "region"), "region")
                seed = f"{source_id}:{title}:{seed_region}"
                policy_id = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
            if not title:
                continue
            canonical.append(
                {
                    "policy_id": policy_id,
                    "title": title,
                    "region": pick_row_value(
                        row, mapping.get("region_field", "region"), "region", fallback="전국"
                    ),
                    "target_group": pick_row_value(
                        row, mapping.get("target_field", "target_group"), "target_group", fallback="일반"
                    ),
                    "category": pick_row_value(
                        row, mapping.get("category_field", "category"), "category", fallback="기타"
                    ),
                    "eligibility_text": pick_row_value(
                        row,
                        mapping.get("eligibility_field", "eligibility_text"),
                        "eligibility_text",
                        fallback="공고문 참고",
                    ),
                    "benefit_text": pick_row_value(
                        row,
                        mapping.get("benefit_field", "benefit_text"),
                        "benefit_text",
                        fallback="공고문 참고",
                    ),
                    "application_period_text": pick_row_value(
                        row,
                        mapping.get("application_period_field", "application_period_text"),
                        "application_period_text",
                        fallback="공고문 참고",
                    ),
                    "official_url": pick_row_value(
                        row,
                        mapping.get("official_url_field", "official_url"),
                        "official_url",
                        fallback=fallback_official_url,
                    ),
                    "source_org": pick_row_value(
                        row, mapping.get("source_org_field", "source_org"), "source_org", fallback=source_id
                    ),
                    "source_api": source_id,
                    "source_updated_at": pick_row_value(
                        row,
                        mapping.get("updated_field", "source_updated_at"),
                        "source_updated_at",
                        fallback=now,
                    ),
                    "last_checked_at": now,
                    "status": "active",
                }
            )

    deduped: dict[str, dict[str, Any]] = {}
    for rec in canonical:
        deduped[rec["policy_id"]] = rec
    canonical = list(deduped.values())

    previous_by_id = {p.get("policy_id"): p for p in previous_records if p.get("policy_id")}
    current_by_id = {c["policy_id"]: c for c in canonical}
    changes: list[dict[str, Any]] = []

    for pid, rec in current_by_id.items():
        old = previous_by_id.get(pid)
        if old is None:
            rec["change_type"] = "created"
            rec["change_summary"] = "신규 등록"
        else:
            fingerprint_keys = [
                "title",
                "region",
                "target_group",
                "category",
                "eligibility_text",
                "benefit_text",
                "application_period_text",
                "official_url",
            ]
            before = "|".join(str(old.get(k, "")) for k in fingerprint_keys)
            after = "|".join(str(rec.get(k, "")) for k in fingerprint_keys)
            if before == after:
                rec["change_type"] = "unchanged"
                rec["change_summary"] = "변경 없음"
            else:
                rec["change_type"] = "updated"
                rec["change_summary"] = "핵심 정보 변경"
        changes.append({"policy_id": pid, "change_type": rec["change_type"], "title": rec["title"]})

    for pid, old in previous_by_id.items():
        if pid not in current_by_id:
            closed = dict(old)
            closed["status"] = "closed"
            closed["last_checked_at"] = now
            closed["change_type"] = "closed"
            closed["change_summary"] = "현재 수집 기준 미노출"
            canonical.append(closed)
            changes.append({"policy_id": pid, "change_type": "closed", "title": closed.get("title", pid)})

    return canonical, changes


def compute_quality_metrics(canonical: list[dict[str, Any]], site_dir: Path | None = None) -> dict[str, Any]:
    total = len(canonical) if canonical else 1
    null_count = 0
    for rec in canonical:
        for field in REQUIRED_POLICY_FIELDS:
            value = rec.get(field)
            if value is None or str(value).strip() == "":
                null_count += 1
    null_ratio = null_count / (total * len(REQUIRED_POLICY_FIELDS))

    ids = [str(r.get("policy_id", "")).strip() for r in canonical if r.get("policy_id")]
    duplicate_ratio = 0.0
    if ids:
        duplicate_ratio = (len(ids) - len(set(ids))) / len(ids)

    bad_links = 0
    links = 0
    for rec in canonical:
        url = str(rec.get("official_url", ""))
        if url:
            links += 1
            if not (url.startswith("http://") or url.startswith("https://")):
                bad_links += 1
    broken_link_ratio = bad_links / (links or 1)

    missing_sections = 0
    if site_dir and site_dir.exists():
        required_fragments = [
            "공식 출처",
            "최종 확인 시각",
            "공식기관이 아니며",
            "rel=\"canonical\"",
        ]
        for html_path in site_dir.rglob("index.html"):
            rel_parts = html_path.relative_to(site_dir).parts
            # detail page only: grants/{slug}/index.html
            if len(rel_parts) != 3 or rel_parts[0] != "grants" or rel_parts[2] != "index.html":
                continue
            text = html_path.read_text(encoding="utf-8")
            for frag in required_fragments:
                if frag not in text:
                    missing_sections += 1
                    break

    return {
        "null_ratio": round(null_ratio, 6),
        "duplicate_ratio": round(duplicate_ratio, 6),
        "broken_link_ratio": round(broken_link_ratio, 6),
        "missing_sections_count": missing_sections,
        "total_policies": len(canonical),
    }


def evaluate_quality(
    metrics: dict[str, Any],
    previous_count: int,
    current_count: int,
    official_url_missing: int,
) -> dict[str, Any]:
    hard: list[str] = []
    soft: list[str] = []

    if official_url_missing > 0:
        hard.append("official_url missing exists")
    if metrics["null_ratio"] > 0.05:
        hard.append("required field null ratio > 5%")
    if metrics["duplicate_ratio"] > 0.03:
        hard.append("duplicate ratio > 3%")
    if metrics["broken_link_ratio"] > 0.01:
        hard.append("broken link ratio > 1%")
    if metrics["missing_sections_count"] > 0:
        hard.append("required frontend sections missing")

    if previous_count > 0:
        drop_ratio = max(previous_count - current_count, 0) / previous_count
        if drop_ratio > 0.2:
            soft.append("record volume drop > 20%")

    decision = "pass"
    if hard:
        decision = "hard_fail"
    elif soft:
        decision = "soft_fail"

    return {"decision": decision, "hard_fail": hard, "soft_fail": soft, "metrics": metrics}


def evaluate_monetization(site_dir: Path) -> dict[str, Any]:
    hard: list[str] = []
    soft: list[str] = []
    banned_phrases = ["광고를 클릭", "지금 클릭해서 지원받기"]
    detail_pages = list(site_dir.glob("grants/*/index.html"))

    if not detail_pages:
        hard.append("no policy detail pages generated")
    for page in detail_pages:
        text = page.read_text(encoding="utf-8")
        if "공식기관이 아니며" not in text:
            hard.append(f"disclaimer missing in {page}")
        for phrase in banned_phrases:
            if phrase in text:
                hard.append(f"banned phrase found in {page}: {phrase}")

    decision = "pass"
    if hard:
        decision = "hard_fail"
    elif soft:
        decision = "soft_fail"

    return {"decision": decision, "hard_fail": hard, "soft_fail": soft}


def group_by(records: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        value = str(rec.get(key, "기타")).strip() or "기타"
        grouped.setdefault(value, []).append(rec)
    return grouped


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def to_multiline_html(value: str, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    escaped = html_escape(text).replace("\r\n", "\n").replace("\r", "\n")
    return "<br />".join(escaped.split("\n"))


def extract_first_sentence(value: str, fallback: str = "공고문 참고") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    first_line = normalized.split("\n")[0].strip()
    if not first_line:
        first_line = normalized.strip()
    match = re.search(r"(.+?[.!?])(?:\s|$)", first_line)
    if match:
        sentence = match.group(1).strip()
    else:
        sentence = first_line
    if len(sentence) > 120:
        return sentence[:120].rstrip() + "..."
    return sentence


def format_benefit_detail_html(value: str, fallback: str = "공고문 참고") -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    if len(lines) <= 1:
        return f'<p class="preline benefit-body">{to_multiline_html(text, fallback=fallback)}</p>'

    cleaned_lines: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[\-\*\u2022\u25CB\u25CF\s]+", "", line).strip()
        cleaned = re.sub(r"^[0-9]+\)", "", cleaned).strip()
        cleaned = re.sub(r"^[①-⑳]", "", cleaned).strip()
        cleaned_lines.append(cleaned or line)
    items = "".join(f"<li>{html_escape(item)}</li>" for item in cleaned_lines)
    return f'<ul class="benefit-list">{items}</ul>'


def format_yyyymmdd(text: str) -> str:
    digits = "".join(ch for ch in str(text or "") if ch.isdigit())
    if len(digits) != 8:
        return str(text or "")
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def format_period_text(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "공고문 참고"

    pattern = re.compile(r"(?<!\d)(\d{8})(?!\d)")

    def repl(match: re.Match[str]) -> str:
        return format_yyyymmdd(match.group(1))

    converted = pattern.sub(repl, raw)
    return converted


def format_target_group_html(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return '<div class="target-pill-group"><span class="target-pill">일반</span></div>'
    normalized = (
        raw.replace("，", ",")
        .replace("ㆍ", ",")
        .replace("·", ",")
        .replace("/", ",")
        .replace("|", ",")
    )
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if not parts:
        return html_escape(raw)
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        deduped.append(part)
    if not deduped:
        deduped = ["일반"]
    chips = "".join(f'<span class="target-pill">{html_escape(part)}</span>' for part in deduped)
    return f'<div class="target-pill-group">{chips}</div>'


def format_target_group_compact(value: str, max_items: int = 3) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "일반"
    normalized = (
        raw.replace("，", ",")
        .replace("ㆍ", ",")
        .replace("·", ",")
        .replace("/", ",")
        .replace("|", ",")
    )
    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if not parts:
        return raw
    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        deduped.append(part)
    if len(deduped) <= max_items:
        label = ", ".join(deduped)
    else:
        label = ", ".join(deduped[:max_items]) + f" 외 {len(deduped) - max_items}"
    return label


def format_checked_at(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "확인 시각 정보 없음"
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(normalized)
        return parsed.strftime("%Y년 %m월 %d일 %H시")
    except ValueError:
        return html_escape(raw)


def parse_iso_datetime(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None


def extract_period_end_date(value: str) -> dt.date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if "상시" in raw:
        return None

    converted = format_period_text(raw)
    matches = re.findall(r"(\d{4})[-./](\d{2})[-./](\d{2})", converted)
    if matches:
        y, m, d = matches[-1]
        try:
            return dt.date(int(y), int(m), int(d))
        except ValueError:
            return None

    compact_matches = re.findall(r"(?<!\d)(\d{8})(?!\d)", raw)
    if not compact_matches:
        return None
    digits = compact_matches[-1]
    try:
        return dt.date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def render_layout(
    title: str,
    description: str,
    canonical_url: str,
    body: str,
    adsense_client_id: str = "",
    ga_measurement_id: str = "",
    social_image_url: str = "",
) -> str:
    adsense = ""
    if adsense_client_id:
        adsense = (
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={html_escape(adsense_client_id)}" '
            'crossorigin="anonymous"></script>'
        )
    analytics = ""
    if ga_measurement_id:
        escaped_measurement_id = html_escape(ga_measurement_id.strip())
        analytics = f"""
  <script async src="https://www.googletagmanager.com/gtag/js?id={escaped_measurement_id}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag() {{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{escaped_measurement_id}');
  </script>"""
    social_meta = ""
    if social_image_url:
        social_meta = f"""
  <meta property="og:image" content="{html_escape(social_image_url)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:image" content="{html_escape(social_image_url)}" />"""
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_escape(title)}</title>
  <meta name="description" content="{html_escape(description)}" />
  <link rel="canonical" href="{html_escape(canonical_url)}" />
  <link rel="stylesheet" href="/styles.css" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html_escape(title)}" />
  <meta property="og:description" content="{html_escape(description)}" />
  {social_meta}
  {analytics}
  {adsense}
</head>
<body>
  <header class="site-header">
    <div class="site-header-inner">
      <a class="brand" href="/"><span class="brand-dot"></span><span>지원알람</span></a>
      <nav class="site-nav">
        <a class="nav-link" href="/updates/">변경사항</a>
        <a class="nav-cta" href="/">정책 찾기</a>
      </nav>
    </div>
    <div class="reading-track"><div class="reading-bar"></div></div>
  </header>
  <main class="container">
  {body}
  </main>
  <footer class="site-footer" role="contentinfo">
    <nav class="footer-nav" aria-label="푸터 링크">
      <a href="/about/">소개</a>
      <a href="/privacy/">개인정보처리방침</a>
      <a href="/terms/">이용약관</a>
      <a href="/disclaimer/">면책문구</a>
      <a href="/sitemap.xml">사이트맵</a>
    </nav>
    <p class="footer-source">데이터 출처: 각 정책의 공식 공고 페이지</p>
    <p class="footer-copy">© 지원알람. All rights reserved.</p>
  </footer>
</body>
</html>
"""


def generate_site(
    canonical: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    site_dir: Path,
    site_base_url: str,
    adsense_client_id: str = "",
    ga_measurement_id: str = "",
) -> dict[str, Any]:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    ensure_dir(site_dir)

    styles = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&family=Noto+Sans+KR:wght@400;500;700&display=swap');

:root {
  --bg: #f2f5f9;
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #111827;
  --text-soft: #4b5563;
  --muted: #6b7280;
  --line: #dbe2ea;
  --primary: #2b8cee;
  --primary-deep: #1565c0;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
  background: #f8fafc;
  color: var(--text);
  line-height: 1.72;
}

a {
  color: var(--primary-deep);
  text-decoration: none;
}

a:hover { text-decoration: underline; }

.site-header {
  position: sticky;
  top: 0;
  z-index: 40;
  backdrop-filter: blur(12px);
  background: rgba(248, 250, 253, 0.86);
  border-bottom: 1px solid var(--line);
}

.site-header-inner {
  max-width: 1080px;
  margin: 0 auto;
  min-height: 68px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 1.08rem;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--primary-deep);
}

.brand-dot {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--primary);
}

.site-nav {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.nav-link,
.nav-cta {
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 0.84rem;
  font-weight: 700;
}

.nav-link {
  color: var(--text-soft);
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.8);
}

.nav-cta {
  color: #fff;
  background: var(--primary);
}

.reading-track {
  width: 100%;
  height: 3px;
  background: rgba(148, 163, 184, 0.25);
}

.reading-bar {
  width: 42%;
  height: 100%;
  background: var(--primary);
}

.container {
  max-width: 780px;
  margin: 0 auto;
  padding: 38px 18px 72px;
}

.policy-post {
  position: relative;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 28px;
  padding: 40px 36px;
}

.post-header {
  margin-bottom: 30px;
  text-align: left;
}

.kicker {
  margin: 0;
  color: var(--primary-deep);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.policy-title {
  margin: 12px 0 14px;
  color: var(--text);
  font-size: clamp(1.7rem, 4.2vw, 2.5rem);
  line-height: 1.22;
  letter-spacing: -0.02em;
}

.meta-line {
  margin: 0;
  color: var(--muted);
  font-size: 0.95rem;
  font-weight: 600;
}

.hero-block {
  margin: 0 0 26px;
}

.thumb-slot {
  border-radius: 20px;
  aspect-ratio: 16 / 9;
  min-height: 220px;
  display: flex;
  align-items: stretch;
  background: #eef4ff;
  border: 1px solid #c8def8;
  padding: 16px;
}

.thumb-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: 20px;
  border: 1px solid #c8def8;
  background: #eef4ff;
}

.thumb-guide {
  width: 100%;
  border-radius: 14px;
  border: 1px dashed #93c5fd;
  background: #ffffff;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 8px;
}

.thumb-label {
  align-self: flex-start;
  margin: 0;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.thumb-title {
  margin: 0;
  color: #0f172a;
  font-size: clamp(1rem, 2.2vw, 1.3rem);
  line-height: 1.35;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.thumb-meta {
  margin: 0;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
}

.thumb-caption {
  margin: 10px 2px 0;
  color: var(--muted);
  font-size: 0.82rem;
}

.policy-summary {
  margin: 0 0 20px;
  padding: 18px 20px;
  border-radius: 16px;
  border: 1px solid #c8def8;
  background: #f4f9ff;
}

.policy-summary h2 {
  margin: 0 0 8px;
  font-size: 1.02rem;
  line-height: 1.4;
}

.policy-summary p {
  margin: 0;
  color: var(--text-soft);
}

.toc-nav {
  margin: 0 0 10px;
}

.toc-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.toc-list a {
  display: block;
  padding: 8px 0;
  color: var(--text-soft);
  font-size: 0.88rem;
  font-weight: 600;
  border-bottom: 1px solid var(--line);
}

.article-section {
  margin: 0;
  padding: 20px 0;
  border-top: 1px solid var(--line);
}

.article-section h2 {
  margin: 0 0 10px;
  color: var(--text);
  font-size: 1.15rem;
  line-height: 1.35;
}

.article-section p {
  margin: 0;
  color: var(--text-soft);
}

.eligibility-focus {
  margin-top: 8px;
  padding: 20px 18px;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
  background: linear-gradient(180deg, #f0f7ff 0%, #f8fbff 100%);
}

.target-lead {
  margin: 0 0 12px !important;
  color: #1d4ed8 !important;
  font-weight: 700;
}

.target-pill-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.target-pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #93c5fd;
  background: #ffffff;
  color: #1e3a8a;
  font-size: 0.86rem;
  font-weight: 700;
  line-height: 1.25;
}

.eligibility-detail {
  margin-top: 14px !important;
  padding: 12px 14px;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  background: #ffffff;
}

.benefit-focus {
  margin-top: 12px;
  padding: 20px 18px;
  border: 1px solid #c7d2fe;
  border-radius: 16px;
  background: linear-gradient(180deg, #f4f5ff 0%, #fafbff 100%);
}

.benefit-lead {
  margin: 0 0 8px !important;
  color: #3730a3 !important;
  font-weight: 700;
}

.benefit-keyline {
  margin: 0 !important;
  color: #111827 !important;
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.6;
}

.benefit-detail {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid #e0e7ff;
  border-radius: 12px;
  background: #ffffff;
}

.benefit-body {
  margin: 0;
  color: var(--text-soft);
}

.benefit-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-soft);
}

.benefit-list li + li {
  margin-top: 8px;
}

.preline {
  white-space: normal;
  line-height: 1.78;
}

.spacer-sm {
  margin-top: 10px !important;
}

.notice-section {
  margin-top: 8px;
  padding: 16px 18px;
  border: 1px solid #fed7aa;
  border-radius: 14px;
  background: #fff7ed;
}

.notice-section h2 {
  font-size: 1rem;
}

.recommend-section {
  margin-top: 22px;
}

.recommend-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.recommend-card {
  display: block;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 13px 14px;
  background: var(--surface-muted);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.recommend-card:hover {
  text-decoration: none;
  border-color: #bfdbfe;
  background: #f8fbff;
}

.recommend-card span {
  display: block;
  margin-bottom: 4px;
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.recommend-card strong {
  color: var(--text);
  font-size: 0.93rem;
}

.home-hero {
  margin: 0 0 14px;
  padding: 24px 26px;
  border-radius: 20px;
  border: 1px solid rgba(43, 140, 238, 0.24);
  background: #f4f9ff;
}

.home-hero h1 {
  margin: 10px 0 10px;
  font-size: clamp(1.45rem, 3.5vw, 2.1rem);
  line-height: 1.28;
  letter-spacing: -0.02em;
}

.home-hero p {
  margin: 0;
  color: var(--text-soft);
}

.home-chip-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 0 0 14px;
}

.home-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  border: 1px solid #c8def8;
  background: #eef6ff;
  color: var(--text-soft);
  font-size: 0.85rem;
  font-weight: 700;
  padding: 7px 12px;
}

.home-chip:hover {
  text-decoration: none;
  border-color: #93c5fd;
  color: var(--primary-deep);
}

.home-section {
  margin: 0 0 14px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 8px;
}

.section-head h2 {
  margin: 0;
  font-size: 1.02rem;
}

.section-head a {
  color: var(--text-soft);
  font-size: 0.86rem;
  font-weight: 600;
}

.home-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.policy-card-item {
  min-width: 0;
}

.policy-card {
  position: relative;
  display: block;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 14px 13px;
  background: #fff;
  min-height: 156px;
  overflow: hidden;
}

.policy-card:hover {
  text-decoration: none;
  border-color: #bfdbfe;
  background: #f8fbff;
}

.policy-card-kicker {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 0.79rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.policy-card h3 {
  margin: 0 0 8px;
  font-size: 1rem;
  line-height: 1.45;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.policy-card-target {
  margin: 0 0 7px;
  color: var(--text-soft);
  font-size: 0.88rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.policy-card-period {
  margin: 0;
  color: var(--muted);
  font-size: 0.8rem;
  overflow-wrap: anywhere;
}

.policy-card-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 0.74rem;
  font-weight: 700;
  color: #9a3412;
  background: #ffedd5;
  border: 1px solid #fdba74;
}

.link-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.link-item a {
  display: block;
  border-bottom: 1px solid var(--line);
  color: var(--text);
  padding: 13px 2px;
  font-weight: 600;
}

.link-item a:hover {
  color: var(--primary-deep);
}

.inline-actions {
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.inline-actions a {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 9px 14px;
  border: 1px solid var(--line);
  font-weight: 700;
  color: var(--text-soft);
  background: #fff;
}

.inline-actions a.primary {
  color: #fff;
  border-color: transparent;
  background: var(--primary);
}

.empty-state {
  margin: 0;
  color: var(--muted);
}

.site-footer {
  margin-top: 28px;
  padding: 24px 18px 44px;
  border-top: 1px solid var(--line);
  text-align: center;
  background: #f8fafc;
}

.footer-nav {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px 14px;
  margin-bottom: 10px;
}

.footer-nav a {
  color: var(--text-soft);
  font-size: 0.84rem;
  text-decoration: none;
}

.footer-nav a:hover {
  color: var(--primary-deep);
  text-decoration: underline;
}

.footer-source,
.footer-copy {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}

@media (max-width: 780px) {
  .site-header-inner { min-height: 62px; }
  .site-nav { gap: 6px; }
  .nav-link, .nav-cta { padding: 8px 12px; }
  .container { padding-top: 26px; }
  .policy-post { border-radius: 20px; padding: 24px 18px; }
  .home-hero { padding: 18px; }
  .home-chip-row { margin-bottom: 12px; }
  .home-grid { grid-template-columns: 1fr; gap: 9px; }
  .policy-card { min-height: 0; }
  .section-head { align-items: center; }
  .toc-list { grid-template-columns: 1fr; }
  .recommend-grid { grid-template-columns: 1fr; }
  .footer-nav { gap: 8px 12px; }
}
"""
    write_text(site_dir / "styles.css", styles.strip() + "\n")

    active = [r for r in canonical if r.get("status") == "active"]
    generated_pages = 0
    excluded_pages = 0
    sitemap_urls: list[str] = []
    generated_thumbnails = 0
    thumbnail_errors: list[dict[str, str]] = []

    from generate_thumbnails import generate_thumbnails_for_policies

    thumbnail_base_image = Path(os.getenv("THUMBNAIL_BASE_IMAGE", "apps/site/assets/thumbnail/base.png"))
    if not thumbnail_base_image.is_absolute():
        thumbnail_base_image = ROOT / thumbnail_base_image

    thumbnail_output_dir = site_dir / "assets" / "thumbnails"
    thumbnail_result = generate_thumbnails_for_policies(
        policies=active,
        base_image_path=thumbnail_base_image,
        output_dir=thumbnail_output_dir,
        site_base_url=site_base_url,
        font_paths=[
            ROOT / "apps" / "site" / "assets" / "fonts" / "NotoSansCJKkr-Bold.otf",
            ROOT / "apps" / "site" / "assets" / "fonts" / "NotoSansCJKkr-Regular.otf",
            ROOT / "apps" / "site" / "assets" / "fonts" / "NotoSansKR-Bold.ttf",
            ROOT / "apps" / "site" / "assets" / "fonts" / "NotoSansKR-Regular.ttf",
        ],
    )
    thumbnail_items = thumbnail_result["items"]
    generated_thumbnails = int(thumbnail_result["generated"])
    thumbnail_errors = thumbnail_result["errors"]
    thumbnail_map = {str(item.get("slug", "")): item for item in thumbnail_items}

    home_cards: list[dict[str, Any]] = []
    for rec in active:
        slug = slugify(rec["policy_id"])
        page_path = site_dir / "grants" / slug / "index.html"
        canonical_url = f"{site_base_url.rstrip('/')}/grants/{slug}/"
        description = f"{rec['target_group']} 대상 {rec['category']} 정책. 신청기간, 조건, 방법, 서류를 한 번에 확인."
        thumbnail = thumbnail_map.get(slug)
        social_image_url = str(thumbnail.get("public_url", "")) if thumbnail else ""
        thumbnail_link = str(rec.get("official_url", "")).strip() or "#official"
        thumbnail_figure = f"""
  <figure class="hero-block" aria-label="정책 썸네일">
    <a href="{html_escape(thumbnail_link)}" target="_blank" rel="noopener noreferrer">
      <img class="thumb-image" src="{html_escape(str(thumbnail['relative_path']))}" alt="{html_escape(rec['title'])} 정책 썸네일" loading="lazy" />
    </a>
  </figure>
"""
        if thumbnail is None:
            thumbnail_figure = f"""
  <figure class="hero-block" aria-label="정책 썸네일 형태">
    <a href="{html_escape(thumbnail_link)}" target="_blank" rel="noopener noreferrer">
      <div class="thumb-slot" role="img" aria-label="정책 썸네일 미리보기">
        <div class="thumb-guide">
          <p class="thumb-label">대표 썸네일</p>
          <p class="thumb-title">{html_escape(rec['title'])}</p>
          <p class="thumb-meta">{html_escape(rec['region'])} · {html_escape(rec['target_group'])} · {html_escape(rec['category'])}</p>
        </div>
      </div>
    </a>
  </figure>
"""
        body = f"""
<article class="policy-post">
  <header class="post-header">
    <p class="kicker">{html_escape(rec['category'])}</p>
    <h1 class="policy-title">{html_escape(rec['title'])}</h1>
    <p class="meta-line">{html_escape(rec['region'])} · {html_escape(rec['target_group'])}</p>
  </header>
  {thumbnail_figure}
  <section class="policy-summary"><h2>핵심 요약</h2><p class="preline">{to_multiline_html(rec['benefit_text'], fallback='공고문 참고')}</p></section>
  <nav class="toc-nav" aria-label="정책 정보 목차">
    <ul class="toc-list">
      <li><a href="#eligibility">지원 대상</a></li>
      <li><a href="#benefit">지원 내용</a></li>
      <li><a href="#period">신청 기간</a></li>
      <li><a href="#method">신청 방법</a></li>
      <li><a href="#docs">제출 서류</a></li>
      <li><a href="#official">공식 출처</a></li>
    </ul>
  </nav>
  <section id="eligibility" class="article-section eligibility-focus">
    <h2>지원 대상</h2>
    <p class="target-lead">해당되는 대상 유형을 먼저 확인하세요.</p>
    {format_target_group_html(rec.get('target_group', '일반'))}
    <p class="preline eligibility-detail">{to_multiline_html(rec['eligibility_text'], fallback='공고문 참고')}</p>
  </section>
  <section id="benefit" class="article-section benefit-focus">
    <h2>지원 내용</h2>
    <p class="benefit-lead">이 사업에서 제공하는 핵심 지원입니다.</p>
    <p class="benefit-keyline">{html_escape(extract_first_sentence(rec['benefit_text'], fallback='공고문 참고'))}</p>
    <div class="benefit-detail">{format_benefit_detail_html(rec['benefit_text'], fallback='공고문 참고')}</div>
  </section>
  <section id="period" class="article-section"><h2>신청 기간</h2><p>{html_escape(format_period_text(rec['application_period_text']))}</p></section>
  <section id="method" class="article-section"><h2>신청 방법</h2><p>자세한 신청 방법은 공식 출처에서 확인하세요.</p></section>
  <section id="docs" class="article-section"><h2>제출 서류</h2><p>공고문 기준으로 준비하세요.</p></section>
  <section id="official" class="article-section"><h2>공식 출처</h2><p><a href="{html_escape(rec['official_url'])}" rel="noopener noreferrer" target="_blank">{html_escape(rec['official_url'])}</a></p></section>
  <section class="article-section"><h2>최종 확인 시각</h2><p>{format_checked_at(rec['last_checked_at'])}</p></section>
  <section class="notice-section"><h2>안내</h2><p>본 사이트는 공식기관이 아니며, 최종 신청 및 자격 판단은 반드시 원문 공고를 확인하세요.</p></section>
  <section class="recommend-section">
    <h2>함께 보면 좋은 페이지</h2>
    <div class="recommend-grid">
      <a class="recommend-card" href="/updates/"><span>Updates</span><strong>최근 변경사항 보기</strong></a>
      <a class="recommend-card" href="/"><span>Home</span><strong>다른 정책 더 보기</strong></a>
    </div>
  </section>
</article>
"""
        html = render_layout(
            rec["title"],
            description,
            canonical_url,
            body,
            adsense_client_id,
            ga_measurement_id,
            social_image_url=social_image_url,
        )
        write_text(page_path, html)
        generated_pages += 1
        sitemap_urls.append(canonical_url)
        home_cards.append(
            {
                "slug": slug,
                "title": str(rec.get("title", "")),
                "region": str(rec.get("region", "전국")),
                "target_group": str(rec.get("target_group", "일반")),
                "category": str(rec.get("category", "기타")),
                "period_text": format_period_text(str(rec.get("application_period_text", ""))),
                "checked_at": parse_iso_datetime(str(rec.get("last_checked_at", ""))),
                "period_end_date": extract_period_end_date(str(rec.get("application_period_text", ""))),
            }
        )

    # Hubs
    route_label_map = {"region": "지역", "target": "대상", "category": "분야"}
    for key, route in [("region", "region"), ("target_group", "target"), ("category", "category")]:
        grouped = group_by(active, key)
        for group_value, rows in grouped.items():
            slug = slugify(group_value)
            page_path = site_dir / "grants" / route / slug / "index.html"
            canonical_url = f"{site_base_url.rstrip('/')}/grants/{route}/{slug}/"
            items = "\n".join(
                f'<li class="link-item"><a href="/grants/{slugify(r["policy_id"])}/">{html_escape(r["title"])}</a></li>'
                for r in rows
            )
            body = f"""
<section class="home-hero">
  <p class="kicker">{html_escape(route_label_map.get(route, route))}</p>
  <h1>{html_escape(group_value)} 정책 모음</h1>
  <p>아래 목록에서 관심 정책을 선택해 상세 내용을 확인하세요.</p>
</section>
<article class="policy-post">
  <ul class="link-list">{items}</ul>
</article>
"""
            html = render_layout(
                f"{group_value} 정책 모음",
                "정책 모음 페이지",
                canonical_url,
                body,
                adsense_client_id,
                ga_measurement_id,
            )
            write_text(page_path, html)
            generated_pages += 1
            sitemap_urls.append(canonical_url)

    # Updates page
    update_items = "\n".join(
        f'<li class="link-item"><a href="/grants/{slugify(str(c.get("policy_id", "")) or "unknown")}/">{html_escape(c["title"])} · {html_escape(c["change_type"])}</a></li>'
        for c in changes[:100]
    )
    update_content = '<p class="empty-state">표시할 변경사항이 아직 없습니다.</p>'
    if update_items:
        update_content = f'<ul class="link-list">{update_items}</ul>'
    updates_body = f"""
<section class="home-hero">
  <p class="kicker">Updates</p>
  <h1>최근 변경사항</h1>
  <p>수집 파이프라인에서 감지한 최신 상태 변경 내역입니다.</p>
</section>
<article class="policy-post">
  {update_content}
</article>
"""
    updates_url = f"{site_base_url.rstrip('/')}/updates/"
    write_text(
        site_dir / "updates" / "index.html",
        render_layout("최근 변경사항", "정책 변경 내역", updates_url, updates_body, adsense_client_id, ga_measurement_id),
    )
    generated_pages += 1
    sitemap_urls.append(updates_url)

    # Policy pages
    policy_pages = [
        {
            "route": "about",
            "title": "소개",
            "description": "지원알람 사이트 소개",
            "body": """
<section class="home-hero">
  <p class="kicker">About</p>
  <h1>지원알람 소개</h1>
  <p>지원알람은 정책/보조금 정보를 빠르게 탐색할 수 있도록 정리하는 정보형 서비스입니다.</p>
</section>
<article class="policy-post">
  <section class="article-section"><h2>서비스 목적</h2><p>사용자가 정책 공고의 핵심을 빠르게 파악하고, 공식 출처로 안전하게 이동하도록 돕습니다.</p></section>
  <section class="article-section"><h2>데이터 원칙</h2><p>모든 정보는 공식 공고 페이지를 기준으로 확인되며, 최종 판단은 반드시 원문 공고를 확인해야 합니다.</p></section>
  <section class="notice-section"><h2>안내</h2><p>본 사이트는 공식기관이 아니며 정보 제공을 목적으로 운영됩니다.</p></section>
</article>
""",
        },
        {
            "route": "privacy",
            "title": "개인정보처리방침",
            "description": "지원알람 개인정보처리방침",
            "body": """
<section class="home-hero">
  <p class="kicker">Privacy</p>
  <h1>개인정보처리방침</h1>
  <p>서비스 운영 과정에서 수집되는 정보와 처리 목적을 안내합니다.</p>
</section>
<article class="policy-post">
  <section class="article-section"><h2>수집 정보</h2><p>서비스 안정성 점검을 위한 최소한의 접속 로그가 수집될 수 있습니다.</p></section>
  <section class="article-section"><h2>쿠키 및 분석</h2><p>서비스 개선을 위해 쿠키 또는 방문 통계 도구가 사용될 수 있습니다.</p></section>
  <section class="article-section"><h2>광고 관련 안내</h2><p>광고 기능이 활성화되는 경우 관련 쿠키 정책이 적용될 수 있으며, 세부 사항은 해당 광고 서비스 정책을 따릅니다.</p></section>
</article>
""",
        },
        {
            "route": "terms",
            "title": "이용약관",
            "description": "지원알람 이용약관",
            "body": """
<section class="home-hero">
  <p class="kicker">Terms</p>
  <h1>이용약관</h1>
  <p>서비스 이용 조건과 책임 범위를 안내합니다.</p>
</section>
<article class="policy-post">
  <section class="article-section"><h2>정보 제공 범위</h2><p>본 서비스는 정책 정보를 요약해 제공하며, 법률/행정적 확정 효력을 갖지 않습니다.</p></section>
  <section class="article-section"><h2>이용자 책임</h2><p>신청 자격, 일정, 제출 서류는 반드시 공식 출처에서 직접 확인해야 합니다.</p></section>
  <section class="article-section"><h2>책임 제한</h2><p>외부 사이트 정보 변경, 공고 수정 또는 지연으로 인한 손해에 대해 운영자는 책임을 지지 않습니다.</p></section>
</article>
""",
        },
        {
            "route": "disclaimer",
            "title": "면책문구",
            "description": "지원알람 면책문구",
            "body": """
<section class="home-hero">
  <p class="kicker">Disclaimer</p>
  <h1>면책문구</h1>
  <p>서비스 성격과 한계를 안내합니다.</p>
</section>
<article class="policy-post">
  <section class="notice-section"><h2>중요 안내</h2><p>본 사이트는 공식기관이 아니며, 최종 판단은 반드시 원문 공고를 확인하세요.</p></section>
  <section class="article-section"><h2>정보 정확성</h2><p>운영자는 최신 정보를 반영하기 위해 노력하지만, 일부 정보는 실제 공고와 시차가 있을 수 있습니다.</p></section>
  <section class="article-section"><h2>외부 링크</h2><p>공식 출처로 연결되는 외부 링크의 내용과 변경에 대해서는 운영자가 직접 통제하지 않습니다.</p></section>
</article>
""",
        },
    ]
    for page in policy_pages:
        route = page["route"]
        page_url = f"{site_base_url.rstrip('/')}/{route}/"
        write_text(
            site_dir / route / "index.html",
            render_layout(
                str(page["title"]),
                str(page["description"]),
                page_url,
                str(page["body"]),
                adsense_client_id,
                ga_measurement_id,
            ),
        )
        generated_pages += 1
        sitemap_urls.append(page_url)

    # Home
    today = dt.date.today()

    def checked_rank(card: dict[str, Any]) -> float:
        parsed = card.get("checked_at")
        if isinstance(parsed, dt.datetime):
            try:
                return parsed.timestamp()
            except OSError:
                return 0.0
        return 0.0

    recent_cards = sorted(home_cards, key=checked_rank, reverse=True)
    deadline_cards = [
        card
        for card in home_cards
        if isinstance(card.get("period_end_date"), dt.date)
        and 0 <= (card["period_end_date"] - today).days <= 14
    ]
    deadline_cards.sort(key=lambda card: (card["period_end_date"], -checked_rank(card)))
    deadline_slugs = {str(card.get("slug", "")) for card in deadline_cards}
    fresh_cards = [card for card in recent_cards if str(card.get("slug", "")) not in deadline_slugs]

    def render_home_card_list(rows: list[dict[str, Any]], empty_text: str) -> str:
        if not rows:
            return f'<p class="empty-state">{html_escape(empty_text)}</p>'
        chunks: list[str] = []
        for card in rows:
            slug = str(card.get("slug", "")).strip()
            title = str(card.get("title", "")).strip()
            region = str(card.get("region", "전국")).strip() or "전국"
            category = str(card.get("category", "기타")).strip() or "기타"
            target_group = format_target_group_compact(str(card.get("target_group", "일반")))
            period_text = str(card.get("period_text", "공고문 참고")).strip() or "공고문 참고"
            badge = ""
            end_date = card.get("period_end_date")
            if isinstance(end_date, dt.date):
                remaining = (end_date - today).days
                if remaining == 0:
                    badge = '<span class="policy-card-badge">오늘 마감</span>'
                elif remaining == 1:
                    badge = '<span class="policy-card-badge">내일 마감</span>'
                elif remaining > 1:
                    badge = f'<span class="policy-card-badge">{remaining}일 남음</span>'
            chunks.append(
                f"""<li class="policy-card-item">
  <a class="policy-card" href="/grants/{html_escape(slug)}/">
    <p class="policy-card-kicker">{html_escape(region)} · {html_escape(category)}</p>
    <h3>{html_escape(title)}</h3>
    <p class="policy-card-target">{html_escape(target_group)}</p>
    <p class="policy-card-period">신청기간: {html_escape(period_text)}</p>
    {badge}
  </a>
</li>"""
            )
        return f'<ul class="home-grid">{"".join(chunks)}</ul>'

    deadline_content = render_home_card_list(deadline_cards[:12], "마감 임박 정책이 아직 없습니다.")
    fresh_content = render_home_card_list(fresh_cards[:12], "최근 업데이트된 정책이 아직 없습니다.")
    all_content = render_home_card_list(recent_cards[:36], "표시할 정책이 아직 없습니다.")

    home_body = f"""
<section class="home-hero">
  <p class="kicker">Policy Feed</p>
  <h1>정책/보조금 찾기</h1>
  <p>매일 갱신되는 정책 정보를 한 화면에서 빠르게 확인할 수 있습니다.</p>
  <div class="inline-actions">
    <a class="primary" href="/updates/">최근 변경사항 보기</a>
  </div>
</section>
<nav class="home-chip-row" aria-label="홈 섹션 바로가기">
  <a class="home-chip" href="#home-deadline">마감 임박</a>
  <a class="home-chip" href="#home-fresh">최근 업데이트</a>
  <a class="home-chip" href="#home-all">전체 정책</a>
</nav>
<article id="home-deadline" class="policy-post home-section">
  <div class="section-head">
    <h2>마감 임박</h2>
    <a href="/updates/">변경사항 보기</a>
  </div>
  {deadline_content}
</article>
<article id="home-fresh" class="policy-post home-section">
  <div class="section-head">
    <h2>최근 업데이트</h2>
    <a href="/updates/">전체 업데이트</a>
  </div>
  {fresh_content}
</article>
<article id="home-all" class="policy-post home-section">
  <div class="section-head">
    <h2>전체 정책</h2>
    <a href="/updates/">최신 순 정렬</a>
  </div>
  {all_content}
</article>
<article class="policy-post">
  <p class="empty-state">정책 상세에서 신청 조건과 공식 출처를 확인하세요.</p>
</article>
"""
    home_url = f"{site_base_url.rstrip('/')}/"
    write_text(
        site_dir / "index.html",
        render_layout("지원알람", "정책/보조금 정보를 매일 갱신", home_url, home_body, adsense_client_id, ga_measurement_id),
    )
    generated_pages += 1
    sitemap_urls.append(home_url)

    # robots + sitemap
    robots = "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n"
    write_text(site_dir / "robots.txt", robots)
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in sorted(set(sitemap_urls)):
        sitemap_lines.append(f"  <url><loc>{html_escape(u)}</loc><lastmod>{now_iso()}</lastmod></url>")
    sitemap_lines.append("</urlset>")
    write_text(site_dir / "sitemap.xml", "\n".join(sitemap_lines) + "\n")

    return {
        "generated_pages": generated_pages,
        "excluded_pages": excluded_pages,
        "sitemap_entries": len(set(sitemap_urls)),
        "sitemap_urls": sorted(set(sitemap_urls)),
        "generated_thumbnails": generated_thumbnails,
        "thumbnail_errors": thumbnail_errors,
        "thumbnails": thumbnail_items,
    }


def run_http_health_checks(site_base_url: str, top_urls: list[str]) -> list[str]:
    errors: list[str] = []
    for rel in top_urls:
        url = f"{site_base_url.rstrip('/')}{rel}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status >= 400:
                    errors.append(f"{url} => {resp.status}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url} => {exc}")
    return errors


def load_previous_latest() -> list[dict[str, Any]]:
    latest_path = ROOT / "data" / "canonical" / "latest" / "policies.json"
    if not latest_path.exists():
        return []
    data = read_json(latest_path)
    return data if isinstance(data, list) else []


def save_canonical_with_rotation(canonical: list[dict[str, Any]]) -> None:
    latest_dir = ROOT / "data" / "canonical" / "latest"
    prev_dir = ROOT / "data" / "canonical" / "previous"
    latest_path = latest_dir / "policies.json"
    prev_path = prev_dir / "policies.json"
    ensure_dir(latest_dir)
    ensure_dir(prev_dir)
    if latest_path.exists():
        shutil.copy2(latest_path, prev_path)
    write_json(latest_path, canonical)


def write_run_meta(path: Path, run_id: str, status: str, stage: str, details: dict[str, Any]) -> None:
    payload = {
        "run_id": run_id,
        "status": status,
        "stage": stage,
        "updated_at": now_iso(),
        "details": details,
    }
    write_json(path, payload)


def build_manifest(run_id: str, generated_pages: int, excluded_pages: int, sitemap_entries: int) -> dict[str, Any]:
    build_sha = os.getenv("GITHUB_SHA", "local")
    return {
        "run_id": run_id,
        "generated_pages": generated_pages,
        "excluded_pages": excluded_pages,
        "sitemap_entries": sitemap_entries,
        "build_sha": build_sha,
        "generated_at": now_iso(),
    }


def fail(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise RuntimeError(msg)
