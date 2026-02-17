#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import traceback
from pathlib import Path

from runtime_guard import enforce_venv
from pipeline_lib import (
    ROOT,
    build_manifest,
    compute_quality_metrics,
    ensure_dir,
    evaluate_monetization,
    evaluate_quality,
    fetch_source,
    load_previous_latest,
    normalize_records,
    now_iso,
    read_json,
    read_json_subset_yaml,
    run_http_health_checks,
    save_canonical_with_rotation,
    validate_schema,
    write_json,
    write_run_meta,
    generate_site,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full daily policy pipeline")
    parser.add_argument("--run-id", required=True, help="Unique run id")
    parser.add_argument(
        "--mode",
        default="daily",
        choices=["daily", "bootstrap"],
        help="bootstrap allows fixture-only run",
    )
    parser.add_argument(
        "--site-base-url",
        default=os.getenv("SITE_BASE_URL", "https://cbbxs.com"),
        help="Public base URL used for canonical and sitemap",
    )
    return parser.parse_args()


def copy_run_artifacts(
    run_dir: Path,
    canonical: list[dict],
    manifest: dict,
    quality: dict,
    frontend: dict,
    monetization: dict,
    changes: list[dict],
    fetch_report: list[dict],
    thumbnails: list[dict],
) -> None:
    write_json(run_dir / "canonical" / "policies.json", canonical)
    write_json(run_dir / "pages" / "manifest.json", manifest)
    write_json(run_dir / "quality" / "report.json", quality)
    write_json(run_dir / "frontend" / "report.json", frontend)
    write_json(run_dir / "frontend" / "thumbnails.json", thumbnails)
    write_json(run_dir / "monetization" / "report.json", monetization)
    write_json(run_dir / "changes" / "changes.json", changes)
    write_json(run_dir / "fetch" / "report.json", fetch_report)


def sync_latest_run(run_dir: Path) -> None:
    latest = ROOT / "artifacts" / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(run_dir, latest)


def main() -> int:
    enforce_venv()
    args = parse_args()
    run_id: str = args.run_id
    mode: str = args.mode
    today = dt.date.today().isoformat()

    run_dir = ROOT / "artifacts" / "runs" / run_id
    ensure_dir(run_dir)
    run_meta_path = run_dir / "run_meta.json"
    write_run_meta(run_meta_path, run_id, "running", "start", {"mode": mode, "started_at": now_iso()})

    try:
        source_config_path = ROOT / "data" / "sources" / "policy_sources.yaml"
        source_config = read_json_subset_yaml(source_config_path)
        source_schema_errors = validate_schema(source_config, ROOT / "schemas" / "source_connector.v1.schema.json")
        if source_schema_errors:
            raise RuntimeError(f"source schema invalid: {source_schema_errors}")

        content_plan = read_json(ROOT / "data" / "content" / "cluster_defaults.json")
        write_json(run_dir / "content" / "plan.json", content_plan)

        source_rows: dict[str, list[dict]] = {}
        fetch_report: list[dict] = []
        primary_total = 0
        primary_success = 0

        for src in source_config.get("sources", []):
            if not src.get("enabled", False):
                continue
            rows, report = fetch_source(src)
            source_rows[src["source_id"]] = rows
            fetch_report.append(report)
            if src.get("primary", False):
                primary_total += 1
                if report.get("ok"):
                    primary_success += 1

            # raw snapshot by date
            raw_path = ROOT / "data" / "raw" / today / f"{src['source_id']}.json"
            write_json(raw_path, rows)
            write_json(run_dir / "raw" / f"{src['source_id']}.json", rows)

        if primary_total > 0 and primary_success == 0 and mode != "bootstrap":
            raise RuntimeError("all primary sources failed (hard fail)")

        previous = load_previous_latest()
        canonical, changes = normalize_records(source_rows, source_config.get("sources", []), previous)
        if not canonical:
            raise RuntimeError("canonical dataset is empty")

        policy_schema_errors = validate_schema(canonical, ROOT / "schemas" / "policy.v1.schema.json")
        if policy_schema_errors:
            raise RuntimeError(f"policy schema invalid: {policy_schema_errors[:5]}")

        save_canonical_with_rotation(canonical)

        adsense_client_id = os.getenv("ADSENSE_CLIENT_ID", "")
        ga_measurement_id = os.getenv("GA_MEASUREMENT_ID", "")
        site_dir = ROOT / "apps" / "site" / "dist"
        site_result = generate_site(
            canonical,
            changes,
            site_dir,
            args.site_base_url,
            adsense_client_id,
            ga_measurement_id,
        )
        thumbnail_errors = site_result.get("thumbnail_errors", [])
        frontend_soft_fail: list[str] = []
        if thumbnail_errors:
            frontend_soft_fail.append("thumbnail generation partial failure")

        frontend_metrics = compute_quality_metrics(canonical, site_dir=site_dir)
        frontend_hard_fail = [] if frontend_metrics.get("missing_sections_count", 0) == 0 else ["required frontend sections missing"]
        frontend_decision = "pass"
        if frontend_hard_fail:
            frontend_decision = "hard_fail"
        elif frontend_soft_fail:
            frontend_decision = "soft_fail"
        frontend_report = {
            "decision": frontend_decision,
            "hard_fail": frontend_hard_fail,
            "soft_fail": frontend_soft_fail,
            "metrics": frontend_metrics,
            "generated_thumbnails": int(site_result.get("generated_thumbnails", 0)),
            "thumbnail_errors": thumbnail_errors,
        }

        official_url_missing = sum(1 for r in canonical if not str(r.get("official_url", "")).strip())
        quality_report = evaluate_quality(
            metrics=frontend_metrics,
            previous_count=len(previous),
            current_count=len(canonical),
            official_url_missing=official_url_missing,
        )
        quality_schema_errors = validate_schema(quality_report, ROOT / "schemas" / "quality.v1.schema.json")
        if quality_schema_errors:
            raise RuntimeError(f"quality schema invalid: {quality_schema_errors[:5]}")

        monetization_report = evaluate_monetization(site_dir)

        manifest = build_manifest(
            run_id=run_id,
            generated_pages=site_result["generated_pages"],
            excluded_pages=site_result["excluded_pages"],
            sitemap_entries=site_result["sitemap_entries"],
        )
        manifest["generated_thumbnails"] = int(site_result.get("generated_thumbnails", 0))
        manifest_schema_errors = validate_schema(manifest, ROOT / "schemas" / "manifest.v1.schema.json")
        if manifest_schema_errors:
            raise RuntimeError(f"manifest schema invalid: {manifest_schema_errors[:5]}")

        publish_report = {
            "run_id": run_id,
            "deploy_ready": quality_report["decision"] != "hard_fail" and monetization_report["decision"] != "hard_fail",
            "quality_decision": quality_report["decision"],
            "monetization_decision": monetization_report["decision"],
            "generated_pages": site_result["generated_pages"],
            "generated_thumbnails": int(site_result.get("generated_thumbnails", 0)),
            "timestamp": now_iso(),
            "site_base_url": args.site_base_url,
            "health_check_errors": run_http_health_checks(args.site_base_url, ["/", "/updates/", "/sitemap.xml"])
            if args.site_base_url.startswith("http")
            else [],
        }
        write_json(run_dir / "publish" / "report.json", publish_report)
        copy_run_artifacts(
            run_dir,
            canonical,
            manifest,
            quality_report,
            frontend_report,
            monetization_report,
            changes,
            fetch_report,
            site_result.get("thumbnails", []),
        )

        if quality_report["decision"] == "hard_fail" or monetization_report["decision"] == "hard_fail":
            write_run_meta(
                run_meta_path,
                run_id,
                "failed",
                "gates",
                {
                    "quality": quality_report["decision"],
                    "monetization": monetization_report["decision"],
                    "generated_pages": site_result["generated_pages"],
                },
            )
            sync_latest_run(run_dir)
            print("pipeline finished with hard_fail gate")
            return 2

        write_run_meta(
            run_meta_path,
            run_id,
            "success",
            "completed",
            {
                "quality": quality_report["decision"],
                "monetization": monetization_report["decision"],
                "generated_pages": site_result["generated_pages"],
            },
        )
        sync_latest_run(run_dir)
        print("pipeline completed successfully")
        return 0
    except Exception as exc:  # noqa: BLE001
        write_run_meta(
            run_meta_path,
            run_id,
            "failed",
            "exception",
            {"error": str(exc), "traceback": traceback.format_exc()},
        )
        sync_latest_run(run_dir)
        print(f"[ERROR] pipeline failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
