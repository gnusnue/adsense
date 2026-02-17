#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

from runtime_guard import enforce_venv


PROFILES = {
    "refresh": ["DATA_GO_KR_API_KEY"],
    "deploy": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID", "PAGES_PROJECT_NAME"],
    "all": [
        "DATA_GO_KR_API_KEY",
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "PAGES_PROJECT_NAME",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight check for required env vars")
    parser.add_argument("--profile", choices=sorted(PROFILES.keys()), default="all")
    parser.add_argument("--allow-missing-adsense", action="store_true", help="ADSENSE_CLIENT_ID is optional")
    return parser.parse_args()


def main() -> int:
    enforce_venv()
    args = parse_args()

    required = list(PROFILES[args.profile])
    missing = [name for name in required if not os.getenv(name)]

    # Optional warning
    adsense = os.getenv("ADSENSE_CLIENT_ID")
    if not adsense and not args.allow_missing_adsense:
        print("[WARN] ADSENSE_CLIENT_ID is not set (optional)")

    if missing:
        print("[ERROR] Missing required environment variables:")
        for name in missing:
            print(f"- {name}")
        return 1

    print(f"preflight ok (profile={args.profile})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
