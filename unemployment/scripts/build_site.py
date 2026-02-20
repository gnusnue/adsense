#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unemployment static site")
    parser.add_argument("--site-base-url", default="https://uem.cbbxs.com")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = ROOT / "apps" / "site" / "pages" / "unemployment-calculator" / "index.html"
    if not source.exists():
        print(f"[ERROR] source page not found: {source}")
        return 1

    dist = ROOT / "apps" / "site" / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True, exist_ok=True)

    html = source.read_text(encoding="utf-8")
    write_text(dist / "index.html", html)
    write_text(dist / "calculator" / "index.html", html)

    base = args.site_base_url.rstrip("/")
    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            f"  <url><loc>{base}/</loc></url>",
            f"  <url><loc>{base}/calculator/</loc></url>",
            "</urlset>",
            "",
        ]
    )
    write_text(dist / "sitemap.xml", sitemap)
    write_text(dist / "robots.txt", "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

    print("unemployment site build completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
