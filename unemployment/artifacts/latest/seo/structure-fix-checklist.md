# uem.cbbxs.com 구조 개선 체크리스트

기준일: 2026-02-23
목표: 현재 구조에서 놓치기 쉬운 개선 항목을 우선순위로 관리

## P0 (우선 처리)

- [x] `UPDATED_AT` 치환 방식 개선
  - 현재 문제: 빌드 시 모든 페이지 날짜가 동일하게 오늘 날짜로 치환됨
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
  - 완료 기준: 실제 수정일 기반으로 날짜 표기(페이지별/콘텐츠별)

- [x] Tailwind CDN 의존 제거
  - 현재 문제: 런타임 CDN 로드로 성능/CWV 불리
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/home/index.html` 외 5개 페이지
  - 완료 기준: 정적 CSS 빌드 결과물 참조

- [x] 공통 레이아웃 템플릿화
  - 현재 문제: 헤더/탭/푸터가 6페이지에 중복
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/*.html`
  - 완료 기준: 공통 파셜/템플릿 한 곳 수정으로 전체 반영

## P1 (다음 스프린트)

- [x] 홈 계산기 JS 분리
  - 현재 문제: 대형 인라인 스크립트로 테스트/유지보수 어려움
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/home/index.html`
  - 완료 기준: 별도 JS 파일 분리 + 로딩

- [x] Quality Gate 강화
  - 현재 문제: CI가 빌드 성공만 확인
  - 수정 위치: `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
  - 완료 기준: 메타/스키마/리다이렉트/404 noindex 검사 추가

- [x] 폰트 로딩 최적화
  - 현재 문제: 외부 폰트 로딩 비용
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/*.html`
  - 완료 기준: preload/subset/self-host 검토 적용

## P2 (운영 안정화)

- [x] robots 운영 주체 단일화
  - 현재 문제: 빌드 생성 robots + Cloudflare managed 정책 병행
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
  - 완료 기준: 운영 정책/소스 오브 트루스 1개로 통일

- [x] favicon/앱아이콘 추가
  - 현재 문제: 브랜드 자산 부재
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/apps/site/pages/*.html`
  - 완료 기준: favicon 및 기본 meta 아이콘 반영

- [x] 구조화데이터 CI 검증
  - 현재 문제: 스키마 깨져도 배포됨
  - 수정 위치: `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
  - 완료 기준: FAQ/Article/Breadcrumb 정적 검증 추가

- [x] 정적 리소스 파이프라인 명시화
  - 현재 문제: static 리소스 규칙/검증 부족
  - 수정 위치: `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
  - 완료 기준: 정적 파일 누락/경로 오류 검증 추가

## 운영 메모

- 현재 핵심 페이지: `/`, `/apply/`, `/eligibility/`, `/recognition/`, `/income-report/`, `/faq/`
- 리다이렉트 유지: `/calculator`, `/about`, `/updates`, `/fraud-risk` -> `/`
- 404 정책 유지: `noindex,nofollow`
- 2026-02-24(3주차): 홈 계산기 JS 외부 분리, favicon 추가, 폰트 preconnect 주입, 품질게이트 보강 완료
- 2026-02-24(4주차): Article/Breadcrumb/WebSite/Organization JSON-LD 검증 추가, 정적 자산 참조 무결성 검사 추가
- 2026-02-24(5주차): robots 정책을 cloudflare-managed 단일 소스로 고정, build/quality/workflow에 robots-mode 일관 반영
