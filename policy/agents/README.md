# Policy Service Team Agents (v2)

This directory defines a role-first cross-functional team model.

## Team Roles (1 agent per role)

1. `pm_orchestrator` (PM)
2. `content_marketer` (SEO Content)
3. `data_engineer` (DE)
4. `backend_engineer` (BE)
5. `frontend_engineer` (FE)
6. `qa_engineer` (QA)
7. `monetization_adops` (AdOps)

## Directory Layout

1. `agents/pm/pm_orchestrator.md`
2. `agents/content/content_marketer.md`
3. `agents/data/data_engineer.md`
4. `agents/backend/backend_engineer.md`
5. `agents/frontend/frontend_engineer.md`
6. `agents/qa/qa_engineer.md`
7. `agents/adops/monetization_adops.md`
8. Each folder includes `skills.md` for role-specific capability definitions.

## Execution Flow

1. PM opens run and priority.
2. Content marketer defines long-tail plan.
3. DE collects and normalizes policy data.
4. BE generates pages/build artifacts.
5. FE applies UI/SEO/ad-slot rules.
6. QA runs hard/soft gates.
7. AdOps runs monetization policy checks.
8. BE deploys release if gates pass.
9. PM closes run and writes summary.

## Contracts

- All roles use the same `run_id`.
- Handoffs are artifact-based and reproducible.
- QA or AdOps hard-fail blocks deploy.
