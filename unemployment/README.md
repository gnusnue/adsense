# unemployment

Standalone unemployment-benefit site workspace.

## SEO Notes

See `docs/seo_cautions.md`.

## Build

```bash
python scripts/build_site.py --site-base-url https://uem.cbbxs.com
```

Optional GA4 tracking:

```bash
GA_MEASUREMENT_ID=G-XXXXXXXXXX python scripts/build_site.py --site-base-url https://uem.cbbxs.com
```

Output directory: `apps/site/dist`
