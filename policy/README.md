# adsense-policy-automation

정책/보조금 롱테일 SEO 사이트를 자동 생성하는 파이프라인입니다.

## Stack

- Static serving: Cloudflare Pages
- Automation: GitHub Actions
- Data store: JSON snapshots in Git
- Runtime: Python 3.11+

## Directory

- `apps/site`: generated static site output (`dist`)
- `data/sources`: source connector configs (`*.yaml`, JSON-subset YAML)
- `data/raw/YYYY-MM-DD`: raw snapshots by source
- `data/canonical`: normalized datasets (`latest`, `previous`)
- `artifacts/runs/{run_id}`: run artifacts (reports, manifests)
- `agents/*`: team role definitions and skills
- `.github/workflows`: CI/CD pipelines

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_pipeline.py --run-id local-001 --mode bootstrap --site-base-url https://pol.cbbxs.com
```

Generated site is written to `apps/site/dist`.

## Required Secrets (GitHub)

- `DATA_GO_KR_API_KEY` (data.go.kr `Decoding` key 권장, 기본)
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `PAGES_PROJECT_NAME`
- `ADSENSE_CLIENT_ID` (optional)
- `GA_MEASUREMENT_ID` (optional, example: `G-XXXXXXXXXX`)

## Optional Secrets (future source expansion)

- `KSTARTUP_API_KEY`

## Pipeline Commands

```bash
.venv/bin/python scripts/preflight_check.py --profile refresh --allow-missing-adsense
.venv/bin/python scripts/run_pipeline.py --run-id daily-20260217 --mode daily --site-base-url https://pol.cbbxs.com
.venv/bin/python scripts/quality_gate.py --canonical data/canonical/latest/policies.json --site-dir apps/site/dist
.venv/bin/python scripts/verify_public_urls.py --base-url https://pol.cbbxs.com
```

## Notes

- Source config files are `.yaml` but parsed as JSON-subset YAML for minimal dependencies.
- If all primary sources fail, pipeline marks `hard_fail` and blocks deploy.
- All Python scripts enforce `.venv` execution.
- Runtime policy log: `docs/decision-log.md`
- Go-live checklist: `docs/cbbxs-go-live.md`
