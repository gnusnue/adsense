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
