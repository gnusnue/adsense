# Decision Log

## 2026-02-17

### Python Runtime Policy

Decision:

- All project Python tasks must run in repository-local virtual environment `.venv`.

Scope:

1. Local commands
2. GitHub Actions workflows
3. Pipeline scripts (`scripts/*.py`)

Implementation:

1. Workflows use `.venv/bin/pip` and `.venv/bin/python`
2. Scripts enforce venv via `scripts/runtime_guard.py`
3. Documentation updated with `.venv` command examples

Verification commands:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_pipeline.py --run-id verify-venv --mode bootstrap --site-base-url https://cbbxs.com
.venv/bin/python scripts/quality_gate.py --canonical data/canonical/latest/policies.json --previous data/canonical/previous/policies.json --site-dir apps/site/dist
```

### cbbxs.com Deployment Baseline

Decision:

- Production base URL defaults to `https://cbbxs.com`.
- DNS authority for apex domain deployment is Cloudflare NS delegation.

Implementation:

1. Workflows fallback `SITE_BASE_URL` changed to `https://cbbxs.com`.
2. Added preflight secret checks in CI (`scripts/preflight_check.py`).
3. Added public endpoint verification script (`scripts/verify_public_urls.py`).
4. Added go-live runbook (`docs/cbbxs-go-live.md`).

Verification commands:

```bash
.venv/bin/python scripts/preflight_check.py --profile refresh --allow-missing-adsense
.venv/bin/python scripts/preflight_check.py --profile deploy --allow-missing-adsense
.venv/bin/python scripts/verify_public_urls.py --base-url https://cbbxs.com
```
