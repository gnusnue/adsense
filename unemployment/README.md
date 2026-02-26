# unemployment

Standalone unemployment-benefit site workspace.

## SEO Notes

See `docs/seo_cautions.md`.

## Build

```bash
cd apps/site
npm ci
npm run build:css
cd ../..
python scripts/build_site.py --site-base-url https://uem.cbbxs.com
```

Optional GA4 tracking:

```bash
cd apps/site
npm ci
npm run build:css
cd ../..
GA_MEASUREMENT_ID=G-XXXXXXXXXX python scripts/build_site.py --site-base-url https://uem.cbbxs.com
```

Output directory: `apps/site/dist`

## `updated_at` Policy

- Source of truth: `apps/site/page-meta.json`
- Rule:
  - Update only routes whose visible content changed.
  - If a shared partial/build rule changes multiple pages, update all impacted routes.
- Publish check:

```bash
python scripts/build_site.py --site-base-url https://uem.cbbxs.com
python scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url https://uem.cbbxs.com --robots-mode cloudflare-managed
```

## Floating Tabbar Policy

- Source of truth: `apps/site/partials/tabbar.html`
- Rule: floating tabbar is fixed to 5 tabs.
- Fixed tabs (order): `calculator`, `apply`, `eligibility`, `recognition`, `income-report`
- Enforcement: `python scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url https://uem.cbbxs.com --robots-mode cloudflare-managed`

Quick lookup:

```bash
rg -n '\{\{TAB_CLASS:' apps/site/partials/tabbar.html
rg -o '\{\{TAB_CLASS:[^}]+' apps/site/partials/tabbar.html | wc -l
```

## Longtail Weekly Policy

- Weekly file naming: `artifacts/latest/seo/longtail/weekly-YYYY-MM-DD.md`
- Validator behavior: if `--weekly-file` is omitted, latest dated weekly file is auto-selected.

```bash
python scripts/longtail_quality_check.py \
  --longtail-dir artifacts/latest/seo/longtail \
  --backlog-file artifacts/latest/seo/longtail/keyword-backlog.csv \
  --impact-file artifacts/latest/seo/longtail/impact-log.csv
```

## Live SEO Smoke Check

- Command:

```bash
python scripts/verify_live_seo.py --base-url https://uem.cbbxs.com --robots-mode cloudflare-managed
```

- `robots-mode`:
  - `cloudflare-managed`: verifies robots accessibility and core route/sitemap availability
  - `build-managed`: additionally enforces `Sitemap:` in robots and `HEAD /robots.txt = 200`
