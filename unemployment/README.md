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
