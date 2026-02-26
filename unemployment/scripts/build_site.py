#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
from html import escape as html_escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME_PAGE_DIR = "home"
NOT_FOUND_PAGE_DIR = "404"
PAGE_META_PATH = ROOT / "apps" / "site" / "page-meta.json"
PARTIALS_DIR = ROOT / "apps" / "site" / "partials"

NAV_TABS: tuple[str, ...] = ("calculator", "apply", "eligibility", "recognition", "income-report", "faq")
HEADER_ACTIVE_CLASS = "px-3 py-1.5 rounded-full bg-primary/10 text-primary font-semibold"
HEADER_INACTIVE_CLASS = "px-3 py-1.5 rounded-full hover:bg-slate-100 transition-colors"
TAB_ACTIVE_CLASS = "px-3 sm:px-4 py-2 rounded-xl bg-primary text-white text-[13px] sm:text-sm font-semibold whitespace-nowrap"
TAB_INACTIVE_CLASS = (
    "px-3 sm:px-4 py-2 rounded-xl text-[13px] sm:text-sm font-semibold "
    "whitespace-nowrap hover:bg-slate-100 transition-colors"
)

LEGACY_REDIRECTS: tuple[tuple[str, str], ...] = (
    ("/calculator", "/"),
    ("/calculator/", "/"),
    ("/about", "/"),
    ("/about/", "/"),
    ("/updates", "/"),
    ("/updates/", "/"),
    ("/fraud-risk", "/"),
    ("/fraud-risk/", "/"),
    ("/favicon.ico", "/favicon.svg"),
)
ROBOTS_MODE_CLOUDFLARE = "cloudflare-managed"
ROBOTS_MODE_BUILD = "build-managed"
ROBOTS_MODES: tuple[str, ...] = (ROBOTS_MODE_CLOUDFLARE, ROBOTS_MODE_BUILD)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_page_meta() -> dict[str, dict[str, str]]:
    if not PAGE_META_PATH.exists():
        raise FileNotFoundError(f"missing page meta file: {PAGE_META_PATH}")
    payload = json.loads(PAGE_META_PATH.read_text(encoding="utf-8"))
    pages = payload.get("pages")
    if not isinstance(pages, list):
        raise ValueError("page-meta.json must include a 'pages' array")

    by_route: dict[str, dict[str, str]] = {}
    required_keys = ("route", "updated_at", "title", "description", "active_tab")
    for item in pages:
        if not isinstance(item, dict):
            raise ValueError("each item in 'pages' must be an object")
        missing = [key for key in required_keys if key not in item]
        if missing:
            raise ValueError(f"page-meta entry missing keys {missing}: {item}")
        route = str(item["route"])
        if route in by_route:
            raise ValueError(f"duplicate route in page-meta.json: {route}")
        dt.date.fromisoformat(str(item["updated_at"]))
        active_tab = str(item["active_tab"])
        allowed_tabs = set(NAV_TABS) | {"none"}
        if active_tab not in allowed_tabs:
            raise ValueError(f"invalid active_tab '{active_tab}' for route '{route}'")
        by_route[route] = {key: str(item[key]) for key in required_keys}
    return by_route


def load_partials() -> dict[str, str]:
    names = ("header", "tabbar", "footer")
    partials: dict[str, str] = {}
    for name in names:
        path = PARTIALS_DIR / f"{name}.html"
        if not path.exists():
            raise FileNotFoundError(f"missing partial template: {path}")
        partials[name] = path.read_text(encoding="utf-8")
    return partials


def render_nav_classes(template: str, active_tab: str) -> str:
    rendered = template
    for tab in NAV_TABS:
        header_class = HEADER_ACTIVE_CLASS if tab == active_tab else HEADER_INACTIVE_CLASS
        tab_class = TAB_ACTIVE_CLASS if tab == active_tab else TAB_INACTIVE_CLASS
        rendered = rendered.replace(f"{{{{HEADER_CLASS:{tab}}}}}", header_class)
        rendered = rendered.replace(f"{{{{TAB_CLASS:{tab}}}}}", tab_class)
    return rendered


def render_partials(html: str, partials: dict[str, str], active_tab: str) -> str:
    rendered = html
    for name, template in partials.items():
        token = f"{{{{PARTIAL:{name.upper()}}}}}"
        rendered = rendered.replace(token, render_nav_classes(template, active_tab))
    return rendered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unemployment static site")
    parser.add_argument("--site-base-url", default="https://uem.cbbxs.com")
    parser.add_argument("--ga-measurement-id", default=os.getenv("GA_MEASUREMENT_ID", ""))
    parser.add_argument("--robots-mode", default=os.getenv("UNEMPLOYMENT_ROBOTS_MODE", ROBOTS_MODE_CLOUDFLARE))
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


def inject_head_defaults(html: str, base_url: str) -> str:
    snippets: list[str] = []
    if 'rel="icon"' not in html and "rel='icon'" not in html:
        snippets.append(f'  <link rel="icon" type="image/svg+xml" href="{base_url}/favicon.svg" />')

    if "fonts.googleapis.com" in html:
        if "rel=\"preconnect\" href=\"https://fonts.googleapis.com\"" not in html:
            snippets.append('  <link rel="preconnect" href="https://fonts.googleapis.com" />')
        if "rel=\"preconnect\" href=\"https://fonts.gstatic.com\"" not in html:
            snippets.append('  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />')

    if not snippets:
        return html

    head_close = re.search(r"</head>", html, flags=re.IGNORECASE)
    if not head_close:
        return f"{html}\n" + "\n".join(snippets) + "\n"
    return f"{html[:head_close.start()]}\n" + "\n".join(snippets) + f"\n{html[head_close.start():]}"


def update_title(html: str, title: str) -> str:
    pattern = re.compile(r"<title>.*?</title>", flags=re.IGNORECASE | re.DOTALL)
    replacement = f"<title>{html_escape(title)}</title>"
    if not pattern.search(html):
        raise ValueError("missing <title> tag")
    return pattern.sub(replacement, html, count=1)


def update_meta_content(html: str, key: str, value: str, *, attr: str = "name") -> str:
    escaped_key = re.escape(key)
    pattern = re.compile(
        rf'(<meta[^>]+{attr}=["\']{escaped_key}["\'][^>]*content=["\'])([^"\']*)(["\'][^>]*>)',
        flags=re.IGNORECASE,
    )
    if not pattern.search(html):
        raise ValueError(f'missing meta tag: {attr}="{key}"')
    return pattern.sub(rf"\1{html_escape(value)}\3", html, count=1)


def sync_page_metadata(html: str, page_info: dict[str, str]) -> str:
    title = page_info["title"]
    description = page_info["description"]
    rendered = html
    rendered = update_title(rendered, title)
    rendered = update_meta_content(rendered, "description", description, attr="name")
    rendered = update_meta_content(rendered, "og:title", title, attr="property")
    rendered = update_meta_content(rendered, "og:description", description, attr="property")
    rendered = update_meta_content(rendered, "twitter:title", title, attr="name")
    rendered = update_meta_content(rendered, "twitter:description", description, attr="name")
    return rendered


def main() -> int:
    args = parse_args()
    robots_mode = args.robots_mode.strip().lower()
    if robots_mode not in ROBOTS_MODES:
        print(f"[ERROR] invalid robots mode '{args.robots_mode}'. expected one of: {', '.join(ROBOTS_MODES)}")
        return 1

    dist = ROOT / "apps" / "site" / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)
    static_root = ROOT / "apps" / "site" / "static"
    if static_root.exists():
        shutil.copytree(static_root, dist, dirs_exist_ok=True)

    base = args.site_base_url.rstrip("/")
    page_meta = load_page_meta()
    partials = load_partials()
    ga_snippet = render_ga_snippet(args.ga_measurement_id)

    pages_root = ROOT / "apps" / "site" / "pages"
    page_files = sorted(pages_root.rglob("index.html"))
    if not page_files:
        print(f"[ERROR] no pages found under: {pages_root}")
        return 1

    sitemap_by_url: dict[str, str] = {}
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
        page_info = page_meta.get(route)
        if not page_info:
            print(f"[ERROR] missing route in page-meta.json: {route}")
            return 1

        html = page.read_text(encoding="utf-8")
        html = render_partials(html, partials, page_info["active_tab"])
        html = html.replace("{{BASE_URL}}", base).replace("{{UPDATED_AT}}", page_info["updated_at"])
        try:
            html = sync_page_metadata(html, page_info)
        except ValueError as exc:
            print(f"[ERROR] route {route}: {exc}")
            return 1
        html = inject_head_defaults(html, base)
        if "{{PARTIAL:" in html:
            print(f"[ERROR] unresolved partial token in {page}")
            return 1
        if "{{BASE_URL}}" in html or "{{UPDATED_AT}}" in html:
            print(f"[ERROR] unresolved value token in {page}")
            return 1
        html = inject_in_head(html, ga_snippet)
        write_text(out_path, html)
        if include_in_sitemap:
            url = f"{base}{route}"
            lastmod = page_info["updated_at"]
            existing = sitemap_by_url.get(url)
            if existing and existing != lastmod:
                print(f"[ERROR] conflicting lastmod for {url}: {existing} vs {lastmod}")
                return 1
            sitemap_by_url[url] = lastmod

    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[f"  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod></url>" for url, lastmod in sorted(sitemap_by_url.items())],
            "</urlset>",
            "",
        ]
    )
    write_text(dist / "sitemap.xml", sitemap)

    if robots_mode == ROBOTS_MODE_BUILD:
        write_text(dist / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    else:
        robots_path = dist / "robots.txt"
        if robots_path.exists():
            print("[ERROR] robots.txt exists in dist while robots mode is cloudflare-managed")
            return 1

    redirects = "\n".join([f"{src} {dst} 301" for src, dst in LEGACY_REDIRECTS]) + "\n"
    write_text(dist / "_redirects", redirects)

    print("unemployment site build completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
