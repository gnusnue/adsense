## uem.cbbxs.com SEO 개선 실행 계획

기준일: 2026-02-26  
목표: 기술 SEO/콘텐츠 운영/신뢰 신호를 동시에 보강해 색인 안정성과 CTR, 장기 순위 방어력을 높인다.

### 범위
- 워크스페이스: `/Users/eunsung/Documents/adsense/unemployment`
- 대상: 핵심 6개 URL (`/`, `/apply/`, `/eligibility/`, `/recognition/`, `/income-report/`, `/faq/`)
- 운영 환경: Cloudflare Pages + Cloudflare Managed robots

### 우선순위 로드맵
1. `P0 (이번 주)`: 색인/크롤링 실패 가능성과 운영 공백 제거
2. `P1 (다음 주)`: 구조화데이터/신뢰신호/내부링크 강화
3. `P2 (2~4주)`: 성능·운영 자동화 고도화

---

### P0: 즉시 처리
1. robots 일관성 복구 (`HEAD/GET 모두 200`)
- 문제: `HEAD /robots.txt` 404, `GET /robots.txt` 200
- 작업:
  - Cloudflare Managed robots 설정 점검/재배포
  - `Sitemap: https://uem.cbbxs.com/sitemap.xml` 라인 추가
- 완료 기준:
  - `HEAD`/`GET` 모두 200
  - robots 본문에 sitemap 지시어 존재
- 검증:
  - `curl -I https://uem.cbbxs.com/robots.txt`
  - `curl https://uem.cbbxs.com/robots.txt`

2. 롱테일 운영 데이터 공백 해소 + CI 연결
- 문제: 주간 파일 `TODO` 상태, backlog 비어 있음, CI 미연결
- 작업 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/longtail/weekly-2026-02-25.md`
  - `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/longtail/keyword-backlog.csv`
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
- 완료 기준:
  - 최종 채택 10개 실데이터 입력
  - backlog에 채택 키워드 반영
  - PR 품질게이트에서 `longtail_quality_check.py` 실행

3. FAQ를 글로벌 네비게이션에 포함
- 문제: `faq` 페이지가 상단/탭 공통 네비에 없어 내부 링크 신호 약함
- 작업 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/header.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/partials/tabbar.html`
  - `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py` (탭 클래스 렌더링 범위)
- 완료 기준:
  - 데스크톱/모바일 공통 네비에 FAQ 노출
  - `active_tab=faq`일 때 활성 스타일 정상 적용

4. `page-meta.json`을 단일 메타 소스로 강제
- 문제: `title/description` 필드는 정의돼 있으나 빌드 치환에 미사용
- 작업 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
  - `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 완료 기준:
  - page-meta의 title/description과 HTML 메타 불일치 시 빌드 실패 또는 품질게이트 실패

5. `updated_at` 실수정일 반영 체계 정립
- 문제: 모든 페이지가 동일 날짜로 고정
- 작업:
  - 페이지별 수정일 갱신 정책 문서화
  - 변경된 페이지만 `updated_at` 업데이트
- 작업 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/page-meta.json`
  - `/Users/eunsung/Documents/adsense/unemployment/README.md`
- 완료 기준:
  - 페이지별 `lastmod`가 실제 수정 이력을 반영

---

### P1: 다음 스프린트
1. 구조화데이터 보강
- 작업:
  - Article에 `image` 추가
  - Organization/Publisher에 `logo`, `sameAs` 추가
  - WebSite에 `SearchAction` 추가
- 작업 파일:
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/home/index.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/apply/index.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/eligibility/index.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/recognition/index.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/income-report/index.html`
  - `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/faq/index.html`

2. 메타 확장(소셜/국제화)
- 작업:
  - `og:site_name`, `og:locale`, `twitter:url` 추가
  - 연도 표기 룰 통일(핵심 페이지 타이틀)
- 완료 기준:
  - 핵심 6개 페이지 메타 스키마 동일 포맷 유지

3. E-E-A-T 신뢰 페이지 분리
- 작업:
  - `/about/` 또는 `/editorial-policy/`를 실제 콘텐츠 페이지로 제공
  - 현재 `/about -> /` 리다이렉트 전략 재검토
- 완료 기준:
  - 책임주체/검수정책/문의경로를 URL 단위로 명시

4. 라이브 SEO 스모크 테스트 추가
- 작업:
  - 배포 후 라이브 URL 점검 스크립트 추가 (`robots/sitemap/canonical/status`)
  - CI 또는 배포 워크플로 후행 단계 연결
- 완료 기준:
  - 배포 직후 핵심 SEO 오류 조기 탐지 가능

---

### P2: 2~4주
1. CWV/성능 최적화
- 작업:
  - 폰트 self-host 또는 폰트 로딩 축소
  - HTML 캐시 정책(Edge 캐싱) 검토
- 완료 기준:
  - 모바일 LCP/INP 안정화 추세 확인

2. 롱테일 운영 자동화
- 작업:
  - Search Console 지표 기반 주간 리포트 자동 생성
  - 주간 키워드 후보/성과 로그 자동 채움
- 완료 기준:
  - 수동 TODO 입력 없는 주간 운영 루틴 정착

3. 운영 문서 동기화
- 작업:
  - 체크리스트/개선 문서의 완료 상태를 실제 배포 상태와 동기화
- 완료 기준:
  - 문서와 운영 현황 간 불일치 제거

---

### 실행 순서 (권장)
1. `P0-1` robots 일관성 복구
2. `P0-2` 롱테일 실데이터 입력 + CI 연결
3. `P0-3` FAQ 네비 편입
4. `P0-4` page-meta 단일 소스 강제
5. `P0-5` updated_at 운영 규칙 반영
6. 이후 `P1` 구조화데이터/신뢰신호 확장

### 체크포인트
- 모든 변경은 `scripts/quality_check_site.py` 통과
- 라이브 확인:
  - `https://uem.cbbxs.com/robots.txt`
  - `https://uem.cbbxs.com/sitemap.xml`
  - 핵심 6개 URL HTTP 200/정규 URL 308 여부
- Search Console:
  - Sitemap `성공`
  - 핵심 6개 URL `색인됨`
