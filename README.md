# adsense monorepo

This repository is split into two independent workspaces:

- `policy/`: government support policy ingestion, static generation, and deployment
- `unemployment/`: unemployment-benefit site and assets

## Workflows

- `policy-refresh` -> `policy-deploy`
- `unemployment-refresh` -> `unemployment-deploy`
- `policy-quality-gate` (PR validation for `policy/`)

## Local build

Policy:

```bash
cd policy
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_site_from_canonical.py --run-id local --site-base-url https://cbbxs.com
```

Unemployment:

```bash
cd unemployment
python -m venv .venv
.venv/bin/python scripts/build_site.py --site-base-url https://unemployment.cbbxs.com
```
