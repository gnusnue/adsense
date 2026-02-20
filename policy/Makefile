VENV_PY := .venv/bin/python
VENV_PIP := .venv/bin/pip
BASE_URL := https://pol.cbbxs.com

.PHONY: venv install preflight-refresh preflight-deploy run-bootstrap run-daily quality build weekly verify-prod

venv:
	python3 -m venv .venv

install: venv
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

preflight-refresh:
	$(VENV_PY) scripts/preflight_check.py --profile refresh --allow-missing-adsense

preflight-deploy:
	$(VENV_PY) scripts/preflight_check.py --profile deploy --allow-missing-adsense

run-bootstrap:
	$(VENV_PY) scripts/run_pipeline.py --run-id local-bootstrap --mode bootstrap --site-base-url $(BASE_URL)

run-daily:
	$(VENV_PY) scripts/run_pipeline.py --run-id local-daily --mode daily --site-base-url $(BASE_URL)

quality:
	$(VENV_PY) scripts/quality_gate.py --canonical data/canonical/latest/policies.json --previous data/canonical/previous/policies.json --site-dir apps/site/dist

build:
	$(VENV_PY) scripts/build_site_from_canonical.py --run-id local-build --site-base-url $(BASE_URL)

weekly:
	$(VENV_PY) scripts/weekly_report.py

verify-prod:
	$(VENV_PY) scripts/verify_public_urls.py --base-url $(BASE_URL)
