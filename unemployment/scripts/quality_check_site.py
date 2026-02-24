#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path

CORE_ROUTES = ("/", "/apply/", "/eligibility/", "/recognition/", "/income-report/", "/faq/")
ARTICLE_ROUTES = ("/apply/", "/eligibility/", "/recognition/", "/income-report/", "/faq/")
LEGACY_REDIRECTS = (
    ("/calculator", "/"),
    ("/calculator/", "/"),
    ("/about", "/"),
    ("/about/", "/"),
    ("/updates", "/"),
    ("/updates/", "/"),
    ("/fraud-risk", "/"),
    ("/fraud-risk/", "/"),
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ROBOTS_MODE_CLOUDFLARE = "cloudflare-managed"
ROBOTS_MODE_BUILD = "build-managed"
ROBOTS_MODES = (ROBOTS_MODE_CLOUDFLARE, ROBOTS_MODE_BUILD)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated unemployment site")
    parser.add_argument("--dist-root", default="apps/site/dist")
    parser.add_argument("--site-base-url", default="https://uem.cbbxs.com")
    parser.add_argument("--robots-mode", default=ROBOTS_MODE_CLOUDFLARE)
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_meta_content(html: str, name: str) -> str | None:
    pattern = re.compile(
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        flags=re.IGNORECASE,
    )
    match = pattern.search(html)
    return match.group(1).strip() if match else None


def find_canonical(html: str) -> str | None:
    pattern = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', flags=re.IGNORECASE)
    match = pattern.search(html)
    return match.group(1).strip() if match else None


def parse_jsonld_blocks(html: str) -> list[dict]:
    blocks: list[dict] = []
    for raw in re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        text = raw.strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            blocks.append(parsed)
    return blocks


def flatten_jsonld_types(blocks: list[dict]) -> set[str]:
    types: set[str] = set()
    for block in blocks:
        block_type = block.get("@type")
        if isinstance(block_type, str):
            types.add(block_type)
        graph = block.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict) and isinstance(item.get("@type"), str):
                    types.add(item["@type"])
    return types


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        raise ValueError(f"invalid PNG file: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def dist_path_for_route(dist_root: Path, route: str) -> Path:
    if route == "/":
        return dist_root / "index.html"
    return dist_root / route.strip("/") / "index.html"


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_core_pages(dist_root: Path, base_url: str, failures: list[str]) -> None:
    base = base_url.rstrip("/")
    for route in CORE_ROUTES:
        path = dist_path_for_route(dist_root, route)
        require(path.exists(), f"missing core page: {path}", failures)
        if not path.exists():
            continue
        html = read_text(path)
        require(bool(re.search(r"<title>[^<]+</title>", html, flags=re.IGNORECASE)), f"missing title: {path}", failures)
        description = find_meta_content(html, "description")
        require(bool(description), f"missing meta description: {path}", failures)
        canonical = find_canonical(html)
        expected_canonical = f"{base}{route}"
        require(canonical == expected_canonical, f"canonical mismatch: {path} expected {expected_canonical}, got {canonical}", failures)


def validate_not_found(dist_root: Path, failures: list[str]) -> None:
    path = dist_root / "404.html"
    require(path.exists(), "missing 404.html in dist", failures)
    if not path.exists():
        return
    html = read_text(path)
    robots = (find_meta_content(html, "robots") or "").replace(" ", "").lower()
    require("noindex" in robots and "nofollow" in robots, "404 robots meta must include noindex,nofollow", failures)


def validate_redirects(dist_root: Path, failures: list[str]) -> None:
    redirects = dist_root / "_redirects"
    require(redirects.exists(), "missing _redirects in dist", failures)
    if not redirects.exists():
        return
    content = read_text(redirects)
    for src, dst in LEGACY_REDIRECTS:
        line = f"{src} {dst} 301"
        require(line in content, f"missing redirect rule: {line}", failures)


def validate_faq_jsonld(dist_root: Path, failures: list[str]) -> None:
    faq_path = dist_root / "faq" / "index.html"
    require(faq_path.exists(), "missing /faq/index.html in dist", failures)
    if not faq_path.exists():
        return
    html = read_text(faq_path)
    ui_questions = len(re.findall(r"<details\b", html, flags=re.IGNORECASE))
    blocks = parse_jsonld_blocks(html)
    faq_block = next((block for block in blocks if block.get("@type") == "FAQPage"), None)
    require(faq_block is not None, "missing FAQPage JSON-LD block in /faq/", failures)
    if faq_block is None:
        return
    main_entity = faq_block.get("mainEntity", [])
    jsonld_questions = sum(1 for entry in main_entity if isinstance(entry, dict) and entry.get("@type") == "Question")
    require(
        jsonld_questions == ui_questions,
        f"FAQ question count mismatch: JSON-LD={jsonld_questions}, UI={ui_questions}",
        failures,
    )


def validate_structured_data(dist_root: Path, base_url: str, failures: list[str]) -> None:
    base = base_url.rstrip("/")
    home = dist_root / "index.html"
    require(home.exists(), "missing home page for structured data checks", failures)
    if not home.exists():
        return

    home_blocks = parse_jsonld_blocks(read_text(home))
    home_types = flatten_jsonld_types(home_blocks)
    require("WebSite" in home_types, "home must include WebSite JSON-LD", failures)
    require("Organization" in home_types, "home must include Organization JSON-LD", failures)
    require("BreadcrumbList" in home_types, "home must include BreadcrumbList JSON-LD", failures)

    for route in ARTICLE_ROUTES:
        path = dist_path_for_route(dist_root, route)
        require(path.exists(), f"missing page for structured data checks: {path}", failures)
        if not path.exists():
            continue
        html = read_text(path)
        blocks = parse_jsonld_blocks(html)
        types = flatten_jsonld_types(blocks)
        require("Article" in types, f"{path} must include Article JSON-LD", failures)
        require("BreadcrumbList" in types, f"{path} must include BreadcrumbList JSON-LD", failures)

        article = next((block for block in blocks if block.get("@type") == "Article"), None)
        require(article is not None, f"missing Article block in {path}", failures)
        if isinstance(article, dict):
            headline = article.get("headline")
            require(isinstance(headline, str) and headline.strip(), f"Article headline missing in {path}", failures)
            modified = article.get("dateModified")
            published = article.get("datePublished")
            require(isinstance(modified, str) and bool(modified.strip()), f"Article dateModified missing in {path}", failures)
            require(
                isinstance(published, str) and bool(published.strip()),
                f"Article datePublished missing in {path}",
                failures,
            )
            main_entity = article.get("mainEntityOfPage")
            expected = f"{base}{route}"
            actual = main_entity.get("@id") if isinstance(main_entity, dict) else None
            require(actual == expected, f"Article mainEntityOfPage mismatch in {path}: expected {expected}, got {actual}", failures)

        breadcrumb = next((block for block in blocks if block.get("@type") == "BreadcrumbList"), None)
        require(breadcrumb is not None, f"missing BreadcrumbList block in {path}", failures)
        if isinstance(breadcrumb, dict):
            elements = breadcrumb.get("itemListElement")
            require(isinstance(elements, list) and len(elements) >= 2, f"BreadcrumbList too short in {path}", failures)
            if isinstance(elements, list) and elements:
                last = elements[-1]
                if isinstance(last, dict):
                    expected = f"{base}{route}"
                    actual = last.get("item")
                    require(actual == expected, f"Breadcrumb terminal item mismatch in {path}: expected {expected}, got {actual}", failures)


def validate_og_image(dist_root: Path, failures: list[str]) -> None:
    image = dist_root / "og-image.png"
    require(image.exists(), "missing og-image.png", failures)
    if not image.exists():
        return
    try:
        width, height = read_png_size(image)
    except Exception as exc:
        failures.append(str(exc))
        return
    require((width, height) == (1200, 630), f"og-image.png must be 1200x630, got {width}x{height}", failures)


def validate_material_nosnippet(dist_root: Path, failures: list[str]) -> None:
    for html_file in sorted(dist_root.rglob("*.html")):
        html = read_text(html_file)
        tags = re.findall(
            r'<span\b[^>]*class=["\'][^"\']*material-symbols-outlined[^"\']*["\'][^>]*>',
            html,
            flags=re.IGNORECASE,
        )
        for tag in tags:
            if re.search(r"\bdata-nosnippet\b", tag, flags=re.IGNORECASE):
                continue
            failures.append(f"missing data-nosnippet on material icon tag in {html_file}: {tag}")


def validate_css_pipeline(dist_root: Path, base_url: str, failures: list[str]) -> None:
    base = base_url.rstrip("/")
    stylesheet = f'{base}/assets/site.css'
    expected_routes = CORE_ROUTES + ("/404/",)

    for route in expected_routes:
        html_path = dist_path_for_route(dist_root, route) if route != "/404/" else dist_root / "404.html"
        require(html_path.exists(), f"missing page for css check: {html_path}", failures)
        if not html_path.exists():
            continue
        html = read_text(html_path)
        require("cdn.tailwindcss.com" not in html, f"tailwind CDN script must be removed: {html_path}", failures)
        require(stylesheet in html, f"missing static site.css link: {html_path}", failures)

    css_path = dist_root / "assets" / "site.css"
    require(css_path.exists(), "missing generated stylesheet: dist/assets/site.css", failures)


def validate_no_partial_tokens(dist_root: Path, failures: list[str]) -> None:
    for html_file in sorted(dist_root.rglob("*.html")):
        html = read_text(html_file)
        require("{{PARTIAL:" not in html, f"unresolved partial token in dist HTML: {html_file}", failures)


def validate_brand_assets(dist_root: Path, base_url: str, failures: list[str]) -> None:
    base = base_url.rstrip("/")
    favicon = dist_root / "favicon.svg"
    require(favicon.exists(), "missing favicon.svg in dist", failures)

    expected_routes = CORE_ROUTES + ("/404/",)
    for route in expected_routes:
        html_path = dist_path_for_route(dist_root, route) if route != "/404/" else dist_root / "404.html"
        if not html_path.exists():
            continue
        html = read_text(html_path)
        require(
            f'{base}/favicon.svg' in html and 'rel="icon"' in html,
            f"missing favicon link in {html_path}",
            failures,
        )
        if "fonts.googleapis.com" in html:
            require(
                'rel="preconnect" href="https://fonts.googleapis.com"' in html,
                f"missing preconnect for fonts.googleapis.com in {html_path}",
                failures,
            )
            require(
                'rel="preconnect" href="https://fonts.gstatic.com" crossorigin' in html,
                f"missing preconnect for fonts.gstatic.com in {html_path}",
                failures,
            )


def validate_home_calculator_script(dist_root: Path, base_url: str, failures: list[str]) -> None:
    base = base_url.rstrip("/")
    home = dist_root / "index.html"
    script = dist_root / "assets" / "home-calculator.js"
    require(script.exists(), "missing home calculator script: dist/assets/home-calculator.js", failures)
    require(home.exists(), "missing home page for script validation", failures)
    if not home.exists():
        return
    html = read_text(home)
    require(
        f'<script defer src="{base}/assets/home-calculator.js"></script>' in html,
        "home page must load deferred external calculator script",
        failures,
    )
    require("function onlyDigits(" not in html, "home page still contains inline calculator logic", failures)


def validate_local_asset_references(dist_root: Path, failures: list[str]) -> None:
    for html_file in sorted(dist_root.rglob("*.html")):
        html = read_text(html_file)
        refs = re.findall(r'(?:src|href)=["\'](/assets/[^"\']+)["\']', html, flags=re.IGNORECASE)
        for ref in refs:
            rel = ref.lstrip("/")
            target = dist_root / rel
            require(target.exists(), f"missing referenced asset {ref} in {html_file}", failures)


def validate_robots_authority(dist_root: Path, base_url: str, robots_mode: str, failures: list[str]) -> None:
    robots = dist_root / "robots.txt"
    base = base_url.rstrip("/")
    if robots_mode == ROBOTS_MODE_CLOUDFLARE:
        require(not robots.exists(), "robots.txt must not be generated when robots mode is cloudflare-managed", failures)
        return
    require(robots.exists(), "missing robots.txt in build-managed mode", failures)
    if not robots.exists():
        return
    content = read_text(robots)
    require("User-agent: *" in content, "robots.txt missing User-agent directive", failures)
    require("Allow: /" in content, "robots.txt missing Allow directive", failures)
    require(f"Sitemap: {base}/sitemap.xml" in content, "robots.txt missing sitemap directive", failures)


def main() -> int:
    args = parse_args()
    dist_root = Path(args.dist_root).resolve()
    robots_mode = args.robots_mode.strip().lower()
    failures: list[str] = []
    if robots_mode not in ROBOTS_MODES:
        failures.append(f"invalid robots mode '{args.robots_mode}'. expected one of: {', '.join(ROBOTS_MODES)}")
        robots_mode = ROBOTS_MODE_CLOUDFLARE

    validate_core_pages(dist_root, args.site_base_url, failures)
    validate_not_found(dist_root, failures)
    validate_redirects(dist_root, failures)
    validate_structured_data(dist_root, args.site_base_url, failures)
    validate_faq_jsonld(dist_root, failures)
    validate_og_image(dist_root, failures)
    validate_material_nosnippet(dist_root, failures)
    validate_css_pipeline(dist_root, args.site_base_url, failures)
    validate_no_partial_tokens(dist_root, failures)
    validate_brand_assets(dist_root, args.site_base_url, failures)
    validate_home_calculator_script(dist_root, args.site_base_url, failures)
    validate_local_asset_references(dist_root, failures)
    validate_robots_authority(dist_root, args.site_base_url, robots_mode, failures)

    if failures:
        print("[FAIL] quality checks failed:")
        for item in failures:
            print(f" - {item}")
        return 1

    print("[OK] quality checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
