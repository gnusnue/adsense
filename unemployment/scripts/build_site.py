#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import datetime as dt
import os
import re
from html import escape as html_escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_PAGE_DIR = "home"
NOT_FOUND_PAGE_DIR = "404"

LEGACY_REDIRECTS: tuple[tuple[str, str], ...] = (
    ("/calculator", "/"),
    ("/calculator/", "/"),
    ("/about", "/"),
    ("/about/", "/"),
    ("/updates", "/"),
    ("/updates/", "/"),
    ("/fraud-risk", "/"),
    ("/fraud-risk/", "/"),
)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unemployment static site")
    parser.add_argument("--site-base-url", default="https://uem.cbbxs.com")
    parser.add_argument("--ga-measurement-id", default=os.getenv("GA_MEASUREMENT_ID", ""))
    return parser.parse_args()


def render_ga_snippet(measurement_id: str) -> str:
    measurement_id = measurement_id.strip()
    if not measurement_id:
        return ""
    escaped_id = html_escape(measurement_id)
    return f"""
  <script async src="https://www.googletagmanager.com/gtag/js?id={escaped_id}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag() {{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{escaped_id}');
  </script>""".rstrip()


def inject_in_head(html: str, snippet: str) -> str:
    if not snippet:
        return html
    if "googletagmanager.com/gtag/js?id=" in html:
        return html
    head_close = re.search(r"</head>", html, flags=re.IGNORECASE)
    if not head_close:
        return f"{html}\n{snippet}\n"
    return f"{html[:head_close.start()]}\n{snippet}\n{html[head_close.start():]}"


def main() -> int:
    args = parse_args()

    dist = ROOT / "apps" / "site" / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)

    base = args.site_base_url.rstrip("/")
    updated_at = dt.date.today().isoformat()
    ga_snippet = render_ga_snippet(args.ga_measurement_id)

    pages_root = ROOT / "apps" / "site" / "pages"
    page_files = sorted(pages_root.rglob("index.html"))
    if not page_files:
        print(f"[ERROR] no pages found under: {pages_root}")
        return 1

    sitemap_urls: list[str] = []
    for page in page_files:
        rel = page.relative_to(pages_root)
        parts = list(rel.parts[:-1])  # drop index.html
        include_in_sitemap = True
        if parts == [HOME_PAGE_DIR]:
            route = "/"
            out_path = dist / "index.html"
        elif parts == [NOT_FOUND_PAGE_DIR]:
            route = "/404/"
            out_path = dist / "404.html"
            include_in_sitemap = False
        else:
            route = "/" + "/".join(parts) + "/"
            out_path = dist.joinpath(*parts, "index.html")

        html = page.read_text(encoding="utf-8")
        html = html.replace("{{BASE_URL}}", base).replace("{{UPDATED_AT}}", updated_at)
        html = inject_in_head(html, ga_snippet)
        write_text(out_path, html)
        if include_in_sitemap:
            sitemap_urls.append(f"{base}{route}")

    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[f"  <url><loc>{url}</loc><lastmod>{updated_at}</lastmod></url>" for url in sorted(set(sitemap_urls))],
            "</urlset>",
            "",
        ]
    )
    write_text(dist / "sitemap.xml", sitemap)
    write_text(dist / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write_text(
        dist / "_headers",
        "/404.html\n  X-Robots-Tag: noindex,nofollow\n/*\n  X-Robots-Tag: index,follow\n",
    )
    redirects = "\n".join([f"{src} {dst} 301" for src, dst in LEGACY_REDIRECTS]) + "\n"
    write_text(dist / "_redirects", redirects)

    print("unemployment site build completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
