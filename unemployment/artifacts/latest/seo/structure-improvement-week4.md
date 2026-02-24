## uem.cbbxs.com 4주차 실행 결과 (검증 체계 고도화)

기준일: 2026-02-24
목표: 배포 전 실패를 더 빨리 잡기 위해 구조화데이터/정적자산 검증을 CI 레벨에서 강화

### 실행 항목
1. 구조화데이터 검증 확대
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 추가 검증:
  - 홈(`/`)에 `WebSite`, `Organization`, `BreadcrumbList` 존재
  - 상세 5페이지(`/apply/`, `/eligibility/`, `/recognition/`, `/income-report/`, `/faq/`)에 `Article`, `BreadcrumbList` 존재
  - `Article.mainEntityOfPage.@id`가 canonical URL과 일치
  - `Article.headline/datePublished/dateModified` 존재
  - `BreadcrumbList` 길이 및 마지막 항목 URL 일치

2. 정적 자산 참조 무결성 검사
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 추가 검증:
  - HTML 내 `/assets/...` 참조 파일이 dist에 실제 존재하는지 검사
  - 깨진 정적 링크가 있으면 CI 실패

3. 기존 검증 유지
- FAQ 문항 수(JSON-LD vs UI) 일치
- canonical/self-reference
- 404 noindex/nofollow
- 레거시 301 리다이렉트 규칙
- favicon/preconnect/home 외부 JS 로드 검증

### 변경 파일
- `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/structure-fix-checklist.md`
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/structure-improvement-week4.md`

### 검증 결과
- `npm run build:css` 성공
- `python3 scripts/build_site.py --site-base-url "https://uem.cbbxs.com"` 성공
- `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url "https://uem.cbbxs.com"` 성공

### 잔여 과제 (다음 라운드)
1. robots 운영 주체 단일화(Cloudflare managed와 build 생성 정책 중 1개 기준 확정)
2. JSON-LD 필드 값과 페이지 본문 텍스트 동기화 검사(semantic diff) 추가
3. 주요 페이지 Lighthouse CI(모바일) 자동 측정 도입
