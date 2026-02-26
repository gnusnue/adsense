## SEO 랭크 개선 실행 체크기록

기준일: 2026-02-26

### 실행 체크리스트

- [x] 플로팅 탭바 5개 고정 정책 문서화 + 자동 검증 연결
  - 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/tabbar.html`
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
    - `/Users/eunsung/Documents/adsense/unemployment/README.md`

- [x] longtail 주간 파일 하드코딩 제거(최신 weekly 자동 선택)
  - 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/longtail_quality_check.py`
    - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`

- [x] refresh 워크플로에 품질게이트 삽입(품질 실패 시 자동 커밋 차단)
  - 파일:
    - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-refresh.yml`

- [x] deploy 라이브 SEO 스모크체크를 실패 게이트로 승격
  - 파일:
    - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-deploy.yml`
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/verify_live_seo.py`
  - 변경 내용:
    - `continue-on-error` 제거
    - `robots-mode` 기반 검증 분기(`cloudflare-managed` / `build-managed`)

- [x] page-meta 동기화 검증 범위 확장(og/twitter/Article JSON-LD)
  - 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`

- [x] 내부 링크 무결성 검증 추가 + `/favicon.ico` 404 완화
  - 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
  - 변경 내용:
    - 내부 `/path/` 링크가 실제 라우트로 존재하는지 검증
    - `_redirects`에 `/favicon.ico -> /favicon.svg 301` 추가

### 실행 검증 로그

1. `python3 scripts/build_site.py --site-base-url https://uem.cbbxs.com --robots-mode cloudflare-managed`
   - 결과: `unemployment site build completed`

2. `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url https://uem.cbbxs.com --robots-mode cloudflare-managed`
   - 결과: `[OK] quality checks passed`

3. `python3 scripts/longtail_quality_check.py --longtail-dir artifacts/latest/seo/longtail --backlog-file artifacts/latest/seo/longtail/keyword-backlog.csv --impact-file artifacts/latest/seo/longtail/impact-log.csv`
   - 결과: `[INFO] using latest weekly file: .../weekly-2026-02-25.md` + `[OK] longtail quality checks passed`

4. `python3 scripts/verify_live_seo.py --base-url https://uem.cbbxs.com --robots-mode cloudflare-managed`
   - 결과: `[OK] live seo checks passed`

5. `python3 scripts/build_site.py --site-base-url https://uem.cbbxs.com --robots-mode build-managed`
   - 결과: `unemployment site build completed`

6. `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url https://uem.cbbxs.com --robots-mode build-managed`
   - 결과: `[OK] quality checks passed`

7. `python3 -m py_compile scripts/build_site.py scripts/quality_check_site.py scripts/longtail_quality_check.py scripts/verify_live_seo.py`
   - 결과: 성공(출력 없음)
