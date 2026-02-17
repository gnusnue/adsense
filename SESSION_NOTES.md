# Session Notes

## 2026-02-17

### Mandatory Python Runtime

- This repository must run Python tasks inside `.venv`.
- Do not run project scripts with system `python3`.

Canonical commands:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/run_pipeline.py --run-id local --mode bootstrap --site-base-url https://example.com
```

References:

- `docs/decision-log.md`
- `.github/workflows/*.yml`

### Domain Baseline

- Production domain is `https://cbbxs.com`.
- Apex routing assumes Cloudflare nameserver delegation.
- Operational runbook: `docs/cbbxs-go-live.md`
- DNS baseline snapshot record: `docs/dns-baseline-cbbxs-2026-02-17.md`
