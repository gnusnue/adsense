# System Architecture (v1)

## Pipeline

1. `content_marketer`: create content plan
2. `data_engineer`: fetch API + normalize to canonical
3. `backend_engineer`: generate static pages and manifest
4. `frontend_engineer`: apply SEO/meta/ad slots
5. `qa_engineer`: quality gate checks
6. `monetization_adops`: ad policy gate checks
7. `backend_engineer`: deploy-ready output
8. `pm_orchestrator`: run summary

## Runtime Artifacts

- `artifacts/runs/{run_id}/run_meta.json`
- `artifacts/runs/{run_id}/content/plan.json`
- `artifacts/runs/{run_id}/raw/{source}.json`
- `artifacts/runs/{run_id}/canonical/policies.json`
- `artifacts/runs/{run_id}/quality/report.json`
- `artifacts/runs/{run_id}/frontend/report.json`
- `artifacts/runs/{run_id}/monetization/report.json`
- `artifacts/runs/{run_id}/pages/manifest.json`
- `artifacts/runs/{run_id}/publish/report.json`

## Gates

Hard fail blocks deploy:

- Missing `official_url` exists
- Required field null ratio > 5%
- Duplicate ratio > 3%
- Broken link ratio > 1%
- Missing required frontend sections
- Ad policy violations
