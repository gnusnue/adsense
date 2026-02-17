# Session Notes

## 2026-02-17

### Mandatory Python Runtime

- This repository must run Python tasks inside `.venv`.
- Do not run project scripts with system `python3`.
- `DATA_GO_KR_API_KEY`는 data.go.kr `Decoding` key를 기본으로 사용한다.

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
- API 가용성 점검 기록: `docs/api-availability-2026-02-17.md`

### Real Data Load (2025 H2+)

- Script: `scripts/load_kstartup_historical.py`
- Source endpoint: `https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01`
- Command:
  - `.venv/bin/python scripts/load_kstartup_historical.py --cutoff-date 20250701 --per-page 100 --max-pages 400`
- Output:
  - `data/raw/2026-02-17/kr_policy_kstartup_announcement_all.json` (full raw)
  - `data/raw/2026-02-17/kr_policy_kstartup_announcement_from_20250701.json` (filtered canonical-like)
  - `data/canonical/latest/policies.json` (2063 rows, min_date=`20250701`)
