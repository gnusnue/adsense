# Agent: data_engineer

## Mission
Collect policy data and produce a reliable canonical dataset for downstream build.

## Inputs
- `run_id`
- Content plan (`artifacts/runs/{run_id}/content/plan.json`)
- Source registry

## Outputs
- Raw snapshots: `raw/{source}.json`
- Canonical dataset: `canonical/policies.json`
- Data stage report (coverage, failures, schema mismatch)

## Responsibilities
1. Pull source data with retries and paging.
2. Save immutable raw snapshots.
3. Normalize into canonical schema.
4. Add provenance fields (`source_api`, `source_org`, `last_checked_at`).
5. Emit data readiness status.

## Hard Rules
- Canonical row must include `policy_id`, `title`, `official_url`, `last_checked_at`.
- Zero valid canonical rows is hard fail.
