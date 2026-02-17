# cbbxs.com Go-Live Runbook

## Scope

Deploy `adsense-policy-automation` to `https://cbbxs.com` using Cloudflare Pages.

## A. Pre-migration backup (required)

1. Export or screenshot all current DNS records from registrar DNS:
   - `A`, `CNAME`, `MX`, `TXT`, `CAA`
2. Create explicit mail checklist:
   - MX
   - SPF (`TXT`)
   - DKIM (`TXT`/`CNAME`)
   - DMARC (`TXT`)

## B. Cloudflare setup

1. Add zone: `cbbxs.com`
2. Recreate all DNS records in Cloudflare DNS
3. Confirm no critical record is missing (mail first)

## C. GitHub setup

1. Repository secrets:
   - `DATA_GO_KR_API_KEY`
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `PAGES_PROJECT_NAME`
   - `ADSENSE_CLIENT_ID` (optional)
2. Repository variable:
   - `SITE_BASE_URL=https://cbbxs.com`

## D. Nameserver cutover

1. At registrar, change NS to the two Cloudflare nameservers.
2. Wait for propagation.
3. During propagation, avoid additional DNS edits on old provider.

## E. Pages domain binding

1. In Cloudflare Pages project, add custom domain `cbbxs.com`
2. Ensure certificate status is `Active`

## F. First production run

1. Run workflow `policy-refresh` manually.
2. Confirm workflow `deploy-pages` completed.
3. Verify public endpoints:
   - `https://cbbxs.com/`
   - `https://cbbxs.com/updates/`
   - `https://cbbxs.com/sitemap.xml`
4. Optional automated verification:

```bash
.venv/bin/python scripts/verify_public_urls.py --base-url https://cbbxs.com
```

## G. Rollback

1. DNS issue:
   - Restore missing records in Cloudflare DNS immediately
   - If critical outage persists, revert NS to previous provider as last resort
2. Deploy issue:
   - Inspect `artifacts/latest/run_meta.json` and workflow logs
   - Fix quality/deploy gate and redeploy

## H. Monitoring baseline

1. Daily check:
   - GitHub Actions `policy-refresh`, `deploy-pages`
2. Weekly check:
   - `scripts/weekly_report.py`
3. Critical signals:
   - hard fail in quality/monetization
   - missing sitemap or updates page
