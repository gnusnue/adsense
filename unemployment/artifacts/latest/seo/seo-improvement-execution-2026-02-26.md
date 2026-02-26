## uem.cbbxs.com SEO 개선 실행 체크기록

기준일: 2026-02-26  
기준 계획서: `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/seo-improvement-plan-2026-02-26.md`

### P0 실행 상태

- [ ] `P0-1` robots 일관성 복구 (`HEAD/GET 모두 200`)
  - 상태: `BLOCKED (외부 설정 필요)`
  - 근거:
    - `python3 scripts/verify_live_seo.py --base-url https://uem.cbbxs.com` 실행 결과
    - 실패 항목:
      - `robots must include Sitemap directive`
      - `robots HEAD must be 200, got 404`
  - 저장소 내 조치:
    - 배포 워크플로에 라이브 SEO 스모크 체크 단계 추가
    - 파일: `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-deploy.yml`
    - 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/verify_live_seo.py`
  - 외부 후속 조치(Cloudflare 대시보드):
    - Managed robots에 `Sitemap: https://uem.cbbxs.com/sitemap.xml` 반영
    - `HEAD /robots.txt`가 200으로 응답하도록 설정/동작 확인

- [x] `P0-2` 롱테일 운영 데이터 공백 해소 + CI 연결
  - 반영 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/longtail/weekly-2026-02-25.md`
    - `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/longtail/keyword-backlog.csv`
    - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
  - 검증:
    - `[OK] longtail quality checks passed`

- [x] `P0-3` FAQ 글로벌 네비게이션 편입
  - 반영 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/header.html`
    - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/tabbar.html`
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py` (`NAV_TABS`에 `faq` 포함)
  - 결과:
    - FAQ 탭 노출 및 `active_tab=faq` 활성 스타일 동작

- [x] `P0-4` page-meta 단일 메타 소스 강제
  - 반영 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
    - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
    - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/404/index.html` (메타 태그 보강)
  - 결과:
    - 빌드 시 `title/description` + `og/twitter` 메타를 `page-meta.json` 값으로 동기화
    - 품질게이트에서 산출물 메타와 `page-meta.json` 일치 검증

- [x] `P0-5` `updated_at` 운영 규칙 반영
  - 반영 파일:
    - `/Users/eunsung/Documents/adsense/unemployment/apps/site/page-meta.json`
    - `/Users/eunsung/Documents/adsense/unemployment/README.md`
  - 결과:
    - 이번 공통 변경 영향 페이지 `updated_at`를 `2026-02-26`으로 갱신
    - README에 `updated_at` 갱신 규칙 추가

### 실행 검증 로그

1. `npm ci && npm run build:css`  
   - 결과: 성공

2. `python3 scripts/build_site.py --site-base-url https://uem.cbbxs.com`  
   - 결과: `unemployment site build completed`

3. `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url https://uem.cbbxs.com --robots-mode cloudflare-managed`  
   - 결과: `[OK] quality checks passed`

4. `python3 scripts/longtail_quality_check.py --weekly-file artifacts/latest/seo/longtail/weekly-2026-02-25.md --backlog-file artifacts/latest/seo/longtail/keyword-backlog.csv --impact-file artifacts/latest/seo/longtail/impact-log.csv`  
   - 결과: `[OK] longtail quality checks passed`

5. `python3 scripts/verify_live_seo.py --base-url https://uem.cbbxs.com`  
   - 결과: 실패 (`robots sitemap/head 이슈`)
