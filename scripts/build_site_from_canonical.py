#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from runtime_guard import enforce_venv
from pipeline_lib import ROOT, build_manifest, generate_site, read_json, validate_schema, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build static site from canonical dataset")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--canonical", default="data/canonical/latest/policies.json")
    parser.add_argument("--site-base-url", default=os.getenv("SITE_BASE_URL", "https://cbbxs.com"))
    return parser.parse_args()


def main() -> int:
    enforce_venv()
    args = parse_args()
    canonical_path = ROOT / args.canonical
    if not canonical_path.exists():
        print(f"[ERROR] canonical not found: {canonical_path}")
        return 1

    canonical = read_json(canonical_path)
    if not isinstance(canonical, list):
        print("[ERROR] canonical must be list")
        return 1

    site_dir = ROOT / "apps" / "site" / "dist"
    adsense_client_id = os.getenv("ADSENSE_CLIENT_ID", "")
    ga_measurement_id = os.getenv("GA_MEASUREMENT_ID", "")
    site_result = generate_site(canonical, [], site_dir, args.site_base_url, adsense_client_id, ga_measurement_id)

    manifest = build_manifest(
        run_id=args.run_id,
        generated_pages=site_result["generated_pages"],
        excluded_pages=site_result["excluded_pages"],
        sitemap_entries=site_result["sitemap_entries"],
    )
    manifest["generated_thumbnails"] = int(site_result.get("generated_thumbnails", 0))
    schema_errors = validate_schema(manifest, ROOT / "schemas" / "manifest.v1.schema.json")
    if schema_errors:
        print(f"[ERROR] manifest invalid: {schema_errors[:5]}")
        return 1

    write_json(ROOT / "artifacts" / "latest" / "pages" / "manifest.json", manifest)
    write_json(ROOT / "artifacts" / "latest" / "frontend" / "thumbnails.json", site_result.get("thumbnails", []))
    print("site build completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
