## uem.cbbxs.com 구조 개선 상세 설계 (저위험 점진개선, 2주)

### 요약
- 목표: 현재 정적 구조를 유지하면서 SEO/CWV/운영 안정성을 높인다.
- 기간: 2주.
- 범위: P0 중심(날짜 신뢰성, Tailwind CDN 제거, 공통 레이아웃 중복 축소, 품질 게이트 강화).
- 제약: URL/라우팅/리다이렉트 정책은 유지한다.

### 구현 범위
1. `UPDATED_AT` 신뢰성 개선.
2. Tailwind CDN 제거 후 정적 CSS 빌드 전환(Node 기반 Tailwind CLI).
3. 공통 레이아웃(헤더/탭/푸터) 중복 축소를 위한 빌드 파셜 도입.
4. CI 품질 게이트 확장(메타/스키마/리다이렉트/404/noindex/정적 자산 검사).

### 상세 설계

#### 1) 날짜/페이지 메타 소스 분리
- 신규 파일: `/Users/eunsung/Documents/adsense/unemployment/apps/site/page-meta.json`
- 스키마:
  - `route`: `/`, `/apply/` 등
  - `updated_at`: `YYYY-MM-DD`
  - `title`, `description` (검증용)
  - `active_tab`
- 빌드 규칙:
  - `{{UPDATED_AT}}`는 전역 오늘 날짜가 아니라 `route` 기준 `updated_at`로 치환.
  - `sitemap.xml <lastmod>`도 route별 값 사용.
  - `route` 누락 시 빌드 실패.
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`

#### 2) Tailwind CDN 제거 및 정적 CSS 파이프라인
- 신규 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/package.json`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/tailwind.config.js`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/styles/input.css`
- 빌드 산출물:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/static/assets/site.css`
- HTML 변경:
  - 6페이지 + 404에서 `cdn.tailwindcss.com` 제거.
  - `<link rel="stylesheet" href="{{BASE_URL}}/assets/site.css">` 추가.
- CI 변경:
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
  - Node setup + `npm ci` + `npm run build:css` 추가.
- 배포 워크플로도 동일 단계 추가:
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-refresh.yml`
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-deploy.yml`

#### 3) 공통 레이아웃 파셜 도입 (저위험)
- 신규 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/header.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/tabbar.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/footer.html`
- 페이지 규칙:
  - 기존 페이지는 구조 유지, 공통 블록만 토큰으로 치환.
  - 토큰 예:
    - `{{PARTIAL:HEADER}}`
    - `{{PARTIAL:TABBAR}}`
    - `{{PARTIAL:FOOTER}}`
- 빌드 처리:
  - `build_site.py`에 파셜 로더 추가.
  - `active_tab`은 `page-meta.json` 값으로 클래스 주입.
- 기대효과:
  - 탭/로고/헤더 높이/간격 회귀를 단일 소스로 차단.

#### 4) 품질 게이트 확장
- 신규 검증 스크립트:
  - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 체크 항목:
  - 핵심 6 URL의 `title/description/canonical` 존재.
  - canonical 자기참조 확인.
  - `/404.html`의 `noindex,nofollow` 확인.
  - `_redirects`에 레거시 301 규칙 존재 확인.
  - FAQ 페이지 JSON-LD `Question` 개수 == 화면 FAQ 개수.
  - `og-image.png` 존재 및 1200x630 확인.
  - `material-symbols-outlined` 중 `data-nosnippet` 누락 탐지.
- CI에서 빌드 후 검증 스크립트 실행, 실패 시 머지 차단.

### 공개 API/인터페이스 변경
1. URL/라우팅/리다이렉트 변경 없음.
2. 빌드 인터페이스 변경:
- 기존 `scripts/build_site.py` + CSS 빌드 선행 필요.
3. 운영 파일 추가:
- `page-meta.json`, `partials/*`, `quality_check_site.py`, Tailwind 설정 파일.
4. 검색 인터페이스는 유지하되 `sitemap lastmod`가 route별 실제 수정일 기반으로 정확화.

### 테스트 시나리오
1. 빌드 테스트:
- `python3 scripts/build_site.py --site-base-url "https://uem.cbbxs.com"` 성공.
- `npm run build:css` 성공.
2. 정적 산출물 테스트:
- `dist/index.html` 등 핵심 6페이지 메타 존재.
- `dist/og-image.png` 존재, 1200x630.
- `dist/404.html`의 `noindex,nofollow`.
3. 구조화데이터 테스트:
- FAQ JSON-LD 문항 수와 화면 문항 수 일치.
- Article/Breadcrumb JSON-LD 파싱 오류 없음.
4. 회귀 테스트:
- 모바일 375/412에서 탭 한 줄 스크롤 유지.
- 로고/헤더/탭 높이 홈 vs 세부탭 일치.
5. 배포 후 확인:
- `https://uem.cbbxs.com/og-image.png` 200.
- 핵심 6페이지 `canonical`이 `https://uem.cbbxs.com/...` 자기참조.

### 일정 (2주)
1. 1주차:
- [x] `page-meta.json` 도입.
- [x] `build_site.py` route별 날짜 치환/사이트맵 lastmod 반영.
- [x] 품질 체크 스크립트 초안 + CI 연결.
2. 2주차:
- [x] Tailwind CLI 정적 CSS 전환.
- [x] 파셜 도입(헤더/탭/푸터).
- [x] CI/배포 워크플로 최종 반영 및 회귀 검증.

### 가정 및 기본값
1. Cloudflare managed robots는 유지.
2. 신규 페이지 생성은 이번 라운드 제외.
3. 디자인 언어는 현재 Stitch 기반 스타일을 보존.
4. CSS 빌드는 Node 기반 Tailwind CLI를 표준으로 사용.
5. 성공 기준:
- 기술 검증 실패 0.
- 모바일 네비/레이아웃 회귀 0.
- Search Console 기준 핵심 6페이지 색인 안정 상태 유지.
