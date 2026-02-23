#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path

CORE_ROUTES = ("/", "/apply/", "/eligibility/", "/recognition/", "/income-report/", "/faq/")
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated unemployment site")
    parser.add_argument("--dist-root", default="apps/site/dist")
    parser.add_argument("--site-base-url", default="https://uem.cbbxs.com")
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


def main() -> int:
    args = parse_args()
    dist_root = Path(args.dist_root).resolve()
    failures: list[str] = []

    validate_core_pages(dist_root, args.site_base_url, failures)
    validate_not_found(dist_root, failures)
    validate_redirects(dist_root, failures)
    validate_faq_jsonld(dist_root, failures)
    validate_og_image(dist_root, failures)
    validate_material_nosnippet(dist_root, failures)

    if failures:
        print("[FAIL] quality checks failed:")
        for item in failures:
            print(f" - {item}")
        return 1

    print("[OK] quality checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
