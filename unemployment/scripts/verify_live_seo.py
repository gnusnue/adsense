#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CORE_ROUTES = ("/", "/apply/", "/eligibility/", "/recognition/", "/income-report/", "/faq/")
ROBOTS_MODE_CLOUDFLARE = "cloudflare-managed"
ROBOTS_MODE_BUILD = "build-managed"
ROBOTS_MODES = (ROBOTS_MODE_CLOUDFLARE, ROBOTS_MODE_BUILD)


@dataclass
class HttpResult:
    status: int
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify live SEO smoke checks for unemployment site")
    parser.add_argument("--base-url", default="https://uem.cbbxs.com")
    parser.add_argument("--robots-mode", default=ROBOTS_MODE_CLOUDFLARE)
    parser.add_argument("--allow-robots-head-mismatch", action="store_true")
    return parser.parse_args()


def request(url: str, method: str = "GET") -> HttpResult:
    req = Request(url, method=method, headers={"User-Agent": "SEO-Smoke-Check/1.0"})
    try:
        with urlopen(req, timeout=20) as res:
            body = res.read().decode("utf-8", errors="replace")
            return HttpResult(status=res.getcode(), body=body)
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return HttpResult(status=exc.code, body=body)
    except URLError as exc:
        raise RuntimeError(f"network error for {url}: {exc}") from exc


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")
    robots_mode = args.robots_mode.strip().lower()
    failures: list[str] = []

    if robots_mode not in ROBOTS_MODES:
        failures.append(f"invalid robots mode '{args.robots_mode}'. expected one of: {', '.join(ROBOTS_MODES)}")
        robots_mode = ROBOTS_MODE_CLOUDFLARE

    robots_get = request(f"{base}/robots.txt", method="GET")
    require(robots_get.status == 200, f"robots GET must be 200, got {robots_get.status}", failures)
    if robots_mode == ROBOTS_MODE_BUILD:
        require("Sitemap:" in robots_get.body, "robots must include Sitemap directive in build-managed mode", failures)
        robots_head = request(f"{base}/robots.txt", method="HEAD")
        if not args.allow_robots_head_mismatch:
            require(robots_head.status == 200, f"robots HEAD must be 200, got {robots_head.status}", failures)

    sitemap = request(f"{base}/sitemap.xml", method="GET")
    require(sitemap.status == 200, f"sitemap GET must be 200, got {sitemap.status}", failures)
    require("<urlset" in sitemap.body, "sitemap body must include <urlset>", failures)

    for route in CORE_ROUTES:
        res = request(f"{base}{route}", method="GET")
        require(res.status == 200, f"{route} must return 200, got {res.status}", failures)

    if failures:
        print("[FAIL] live seo checks failed:")
        for issue in failures:
            print(f" - {issue}")
        return 1

    print("[OK] live seo checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
