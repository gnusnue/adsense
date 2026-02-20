# GitHub Setup Guide

## 1. Branch and Protection

1. Default branch: `main`
2. Branch protection for `main`:
   - Require a pull request before merging
   - Require status checks to pass: `policy-quality-gate / quality`
   - Restrict direct pushes (allow admin bypass only if needed)

## 2. Repository Secrets

Required:

- `DATA_GO_KR_API_KEY` (data.go.kr `Decoding` key 사용, `Encoding` key 비권장)
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `POLICY_PAGES_PROJECT_NAME` (없으면 `PAGES_PROJECT_NAME` fallback)

Optional:

- `ADSENSE_CLIENT_ID`
- `GA_MEASUREMENT_ID` (예: `G-XXXXXXXXXX`)
- `KSTARTUP_API_KEY` (source enabled 시)

## 3. Repository Variables

- `POLICY_SITE_BASE_URL=https://pol.cbbxs.com`

## 4. Workflows

- `policy-refresh.yml`
  - Schedule: daily at `06:13 KST`
  - Runs data fetch/normalize/site generation
  - Commits JSON snapshots and generated static files
- `policy-quality-gate.yml`
  - Runs on PR
  - Blocks merge on hard quality failures
- `policy-deploy.yml`
  - Runs on successful `policy-refresh`
  - Deploys `policy/apps/site/dist` to Cloudflare Pages

All workflows create and use `.venv`:

- install: `.venv/bin/pip install -r requirements.txt`
- run: `.venv/bin/python ...`

## 5. First Bring-up Checklist

1. Add all secrets/variables
2. Set `POLICY_SITE_BASE_URL=https://pol.cbbxs.com`
3. Run `policy-refresh` manually once
4. Verify `data/canonical/latest/policies.json` updated
5. Verify `policy-deploy` completed
6. Open `https://pol.cbbxs.com/sitemap.xml` and `https://pol.cbbxs.com/updates/`

## 6. Domain / DNS

For this project, DNS authority is expected on Cloudflare for apex domain routing:

1. Add `cbbxs.com` zone to Cloudflare
2. Copy all existing DNS records from registrar DNS to Cloudflare DNS
3. Update domain nameservers at registrar to Cloudflare NS
4. Add custom domain `pol.cbbxs.com` in Cloudflare Pages
5. Verify SSL status is `Active`
