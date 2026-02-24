## uem.cbbxs.com 3주차 실행 결과 (성능/운영 안정화)

기준일: 2026-02-24
목표: 2주차 기반 위에서 유지보수성/초기 로딩/브랜드 신호를 저위험으로 보강

### 실행 항목
1. 홈 계산기 스크립트 외부 분리
- 기존: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/home/index.html` 인라인 대형 스크립트
- 변경: `/Users/eunsung/Documents/adsense/unemployment/apps/site/static/assets/home-calculator.js` 로 분리
- 반영: 홈에서 `defer` 외부 스크립트 로드

2. favicon 추가
- 신규 파일: `/Users/eunsung/Documents/adsense/unemployment/apps/site/static/favicon.svg`
- 반영: 빌드 시 모든 페이지 head에 favicon 링크 자동 주입

3. 폰트 로딩 최적화(저위험)
- 반영: Google Fonts 사용 페이지에 `preconnect` 자동 주입
  - `https://fonts.googleapis.com`
  - `https://fonts.gstatic.com`
- 적용 위치: 빌드 단계 주입 (`build_site.py`)

4. 품질 게이트 확장
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 추가 검증:
  - `favicon.svg` 파일 존재
  - 핵심 페이지 favicon 링크 존재
  - 폰트 preconnect 존재
  - 홈 계산기 외부 스크립트 로드 여부
  - 홈 인라인 계산 로직 잔존 여부

### 변경 파일
- `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/home/index.html`
- `/Users/eunsung/Documents/adsense/unemployment/apps/site/static/assets/home-calculator.js`
- `/Users/eunsung/Documents/adsense/unemployment/apps/site/static/favicon.svg`
- `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
- `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/structure-fix-checklist.md`

### 검증 결과
- `npm run build:css` 성공
- `python3 scripts/build_site.py --site-base-url "https://uem.cbbxs.com"` 성공
- `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url "https://uem.cbbxs.com"` 성공

### 잔여 과제 (다음 라운드)
1. 구조화데이터 CI 검증을 페이지별(Article/Breadcrumb)로 확장
2. robots 운영 주체 단일화(Cloudflare managed vs build 생성 정책)
3. 정적 리소스 누락/해시 전략 도입 검토
