#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from runtime_guard import enforce_venv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify public URLs after deployment")
    parser.add_argument("--base-url", default="https://cbbxs.com")
    return parser.parse_args()


def fetch_status(url: str) -> tuple[int, str]:
    req = Request(url, method="GET")
    with urlopen(req, timeout=20) as resp:  # noqa: S310
        body = resp.read().decode("utf-8", errors="ignore")
        return resp.status, body


def main() -> int:
    enforce_venv()
    args = parse_args()
    base = args.base_url.rstrip("/") + "/"
    checks = ["/", "/updates/", "/sitemap.xml"]
    failures: list[str] = []

    for path in checks:
        url = urljoin(base, path.lstrip("/"))
        try:
            status, body = fetch_status(url)
            if status >= 400:
                failures.append(f"{url} returned {status}")
            if path == "/" and "혜택정리" not in body:
                failures.append(f"{url} missing expected marker")
            if path == "/sitemap.xml" and "<urlset" not in body:
                failures.append(f"{url} missing urlset tag")
            print(f"[OK] {url} => {status}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{url} => {exc}")

    if failures:
        print("\n[ERROR] public verification failed:")
        for f in failures:
            print(f"- {f}")
        return 1

    print("\npublic verification passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
