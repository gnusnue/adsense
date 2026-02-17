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

    for source_id, rows in source_rows.items():
        src = source_map[source_id]
        mapping = src.get("mapping", {})
        for row in rows:
            policy_id = str(row.get(mapping.get("id_field", "id"), "")).strip()
            title = str(row.get(mapping.get("title_field", "title"), "")).strip()
            if not policy_id:
                seed = f"{source_id}:{title}:{row.get(mapping.get('region_field', ''), '')}"
                policy_id = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
            if not title:
                continue
            canonical.append(
                {
                    "policy_id": policy_id,
                    "title": title,
                    "region": str(row.get(mapping.get("region_field", "region"), "전국")).strip() or "전국",
                    "target_group": str(
                        row.get(mapping.get("target_field", "target_group"), "일반")
                    ).strip()
                    or "일반",
                    "category": str(row.get(mapping.get("category_field", "category"), "기타")).strip()
                    or "기타",
                    "eligibility_text": str(
                        row.get(mapping.get("eligibility_field", "eligibility_text"), "공고문 참고")
                    ).strip()
                    or "공고문 참고",
                    "benefit_text": str(
                        row.get(mapping.get("benefit_field", "benefit_text"), "공고문 참고")
                    ).strip()
                    or "공고문 참고",
                    "application_period_text": str(
                        row.get(
                            mapping.get("application_period_field", "application_period_text"),
                            "공고문 참고",
                        )
                    ).strip()
                    or "공고문 참고",
                    "official_url": str(
                        row.get(mapping.get("official_url_field", "official_url"), "")
                    ).strip(),
                    "source_org": str(row.get("source_org", source_id)).strip() or source_id,
                    "source_api": source_id,
                    "source_updated_at": str(
                        row.get(mapping.get("updated_field", "source_updated_at"), "")
                    ).strip()
                    or now,
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
            "ads-slot",
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
        ad_slots = text.count("ads-slot")
        if ad_slots > 3:
            hard.append(f"ad slot over limit in {page}")
        if "공식기관이 아니며" not in text:
            hard.append(f"disclaimer missing in {page}")
        for phrase in banned_phrases:
            if phrase in text:
                hard.append(f"banned phrase found in {page}: {phrase}")
    if detail_pages and all("ads-slot" not in p.read_text(encoding="utf-8") for p in detail_pages):
        soft.append("no ads slot found in detail pages")

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


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def render_layout(title: str, description: str, canonical_url: str, body: str, adsense_client_id: str = "") -> str:
    adsense = ""
    if adsense_client_id:
        adsense = (
            f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={html_escape(adsense_client_id)}" '
            'crossorigin="anonymous"></script>'
        )
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
  {adsense}
</head>
<body>
  <header class="site-header"><a href="/">혜택정리</a></header>
  <main class="container">
  {body}
  </main>
  <footer class="site-footer">데이터 출처: 각 정책의 공식 공고 페이지</footer>
</body>
</html>
"""


def generate_site(
    canonical: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    site_dir: Path,
    site_base_url: str,
    adsense_client_id: str = "",
) -> dict[str, Any]:
    if site_dir.exists():
        shutil.rmtree(site_dir)
    ensure_dir(site_dir)

    styles = """
:root {
  --bg: #f7f8f5;
  --surface: #ffffff;
  --text: #1f2937;
  --muted: #64748b;
  --primary: #0f766e;
  --border: #d6d3d1;
}
body { margin: 0; font-family: 'Noto Sans KR', sans-serif; background: linear-gradient(180deg, #f7f8f5, #eef2ff); color: var(--text); }
.site-header { padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--surface); position: sticky; top: 0; }
.site-header a { text-decoration: none; color: var(--primary); font-weight: 700; }
.container { max-width: 820px; margin: 24px auto; padding: 0 16px 48px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 16px; }
.muted { color: var(--muted); font-size: 14px; }
.ads-slot { border: 1px dashed #f59e0b; padding: 10px; margin: 14px 0; background: #fffbeb; font-size: 13px; color: #92400e; }
ul { padding-left: 18px; }
a { color: var(--primary); }
"""
    write_text(site_dir / "styles.css", styles.strip() + "\n")

    active = [r for r in canonical if r.get("status") == "active"]
    generated_pages = 0
    excluded_pages = 0
    sitemap_urls: list[str] = []

    listing_items = []
    for rec in active:
        slug = slugify(rec["policy_id"])
        page_path = site_dir / "grants" / slug / "index.html"
        canonical_url = f"{site_base_url.rstrip('/')}/grants/{slug}/"
        description = f"{rec['target_group']} 대상 {rec['category']} 정책. 신청기간, 조건, 방법, 서류를 한 번에 확인."
        body = f"""
<article class="card">
  <h1>{html_escape(rec['title'])}</h1>
  <p class="muted">{html_escape(rec['region'])} · {html_escape(rec['target_group'])} · {html_escape(rec['category'])}</p>
  <section><h2>요약</h2><p>{html_escape(rec['benefit_text'])}</p></section>
  <div class="ads-slot">광고 슬롯: top_banner</div>
  <section><h2>지원 대상</h2><p>{html_escape(rec['eligibility_text'])}</p></section>
  <section><h2>지원 내용</h2><p>{html_escape(rec['benefit_text'])}</p></section>
  <section><h2>신청 기간</h2><p>{html_escape(rec['application_period_text'])}</p></section>
  <section><h2>신청 방법</h2><p>자세한 신청 방법은 공식 출처에서 확인하세요.</p></section>
  <div class="ads-slot">광고 슬롯: in_content</div>
  <section><h2>제출 서류</h2><p>공고문 기준으로 준비하세요.</p></section>
  <section><h2>공식 출처</h2><p><a href="{html_escape(rec['official_url'])}" rel="noopener noreferrer" target="_blank">{html_escape(rec['official_url'])}</a></p></section>
  <section><h2>최종 확인 시각</h2><p>{html_escape(rec['last_checked_at'])}</p></section>
  <section><h2>안내</h2><p>본 사이트는 공식기관이 아니며, 최종 신청 및 자격 판단은 반드시 원문 공고를 확인하세요.</p></section>
  <div class="ads-slot">광고 슬롯: bottom</div>
</article>
"""
        html = render_layout(rec["title"], description, canonical_url, body, adsense_client_id)
        write_text(page_path, html)
        generated_pages += 1
        sitemap_urls.append(canonical_url)
        listing_items.append(f'<li><a href="/grants/{slug}/">{html_escape(rec["title"])}</a></li>')

    # Hubs
    for key, route in [("region", "region"), ("target_group", "target"), ("category", "category")]:
        grouped = group_by(active, key)
        for group_value, rows in grouped.items():
            slug = slugify(group_value)
            page_path = site_dir / "grants" / route / slug / "index.html"
            canonical_url = f"{site_base_url.rstrip('/')}/grants/{route}/{slug}/"
            items = "\n".join(
                f'<li><a href="/grants/{slugify(r["policy_id"])}/">{html_escape(r["title"])}</a></li>' for r in rows
            )
            body = f"""
<article class="card">
  <h1>{html_escape(group_value)} {html_escape(route)} 정책</h1>
  <ul>{items}</ul>
</article>
"""
            html = render_layout(f"{group_value} 정책 모음", "정책 모음 페이지", canonical_url, body, adsense_client_id)
            write_text(page_path, html)
            generated_pages += 1
            sitemap_urls.append(canonical_url)

    # Updates page
    update_items = "\n".join(
        f"<li>{html_escape(c['title'])}: {html_escape(c['change_type'])}</li>" for c in changes[:100]
    )
    updates_body = f"""
<article class="card">
  <h1>최근 변경사항</h1>
  <ul>{update_items}</ul>
</article>
"""
    updates_url = f"{site_base_url.rstrip('/')}/updates/"
    write_text(site_dir / "updates" / "index.html", render_layout("최근 변경사항", "정책 변경 내역", updates_url, updates_body, adsense_client_id))
    generated_pages += 1
    sitemap_urls.append(updates_url)

    # Home
    home_body = f"""
<article class="card">
  <h1>정책/보조금 찾기</h1>
  <p>정책 정보를 매일 갱신합니다.</p>
  <ul>{''.join(listing_items[:50])}</ul>
  <p><a href="/updates/">최근 변경사항 보기</a></p>
</article>
"""
    home_url = f"{site_base_url.rstrip('/')}/"
    write_text(site_dir / "index.html", render_layout("혜택정리", "정책/보조금 정보를 매일 갱신", home_url, home_body, adsense_client_id))
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
