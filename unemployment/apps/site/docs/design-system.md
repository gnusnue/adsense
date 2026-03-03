# UEM 디자인 시스템 (v1)

## 목적
- UEM 사이트 템플릿에서 반복되는 UI 영역을 표준화해, 페이지 추가/수정 시 일관성 유지와 작업 속도를 높인다.

## 공통 영역 분석
- 공통 레이아웃: 상단 헤더, 탭바, 본문 래퍼, 푸터
- 공통 섹션 블록: 흰색 배경 + 라운드 + 보더 카드형 섹션
- 공통 히어로 영역: 키커(배지), 제목, 요약, 3열 요약 카드, CTA
- 공통 관련가이드 영역: 섹션 헤더 + CTA + 3열 링크 카드
- 공통 메타 영역: 작성/검수 정보 + 공식 출처 + 캡션
- 공통 네비게이션 상태: 헤더 탭(active/inactive), 상단 탭바(active/inactive)

## 토큰
- 파일: `apps/site/styles/input.css` (`:root`)
- 색상
  - `--ds-color-primary: #1c74e9`
  - `--ds-color-surface: #ffffff`
  - `--ds-color-surface-soft: #f8fafc`
  - `--ds-color-border: #e2e8f0`
  - `--ds-color-text: #0f172a`
  - `--ds-color-text-subtle: #475569`
  - `--ds-color-text-muted: #64748b`
- 형태/효과
  - `--ds-radius-lg: 0.75rem`
  - `--ds-radius-xl: 1rem`
  - `--ds-shadow-soft: 0 1px 2px rgba(15, 23, 42, 0.06)`
  - `--ds-shadow-elevated: 0 6px 24px rgba(15, 23, 42, 0.08)`

## 컴포넌트 클래스
- 레이아웃
  - `ds-shell`: 기본 페이지 본문 래퍼
  - `ds-shell-compact`: 홈처럼 내부 간격 제어가 필요한 본문 래퍼
  - `ds-shell-narrow`: 404 등 협폭 본문 래퍼
- 섹션
  - `ds-section`: 표준 콘텐츠 섹션
  - `ds-section-body`: 본문 텍스트 톤
  - `ds-section-title`: 섹션 제목
- 히어로
  - `ds-kicker`
  - `ds-kicker-warning`
  - `ds-hero-title`
  - `ds-hero-description`
  - `ds-summary-grid`
  - `ds-summary-card`
  - `ds-summary-label`
  - `ds-cta-button`
- 본문 링크
  - `ds-body-link`
- 관련 가이드
  - `ds-related-head`
  - `ds-related-grid`
  - `ds-related-card`
- 메타/출처
  - `ds-meta-section`
  - `ds-meta-title`
  - `ds-meta-subtitle`
  - `ds-meta-caption`
  - `ds-source-link`
- 내비게이션 상태
  - `ds-nav-link`, `ds-nav-link-active`, `ds-nav-link-inactive`
  - `ds-tab-link`, `ds-tab-link-active`, `ds-tab-link-inactive`

## 동작 방식
- 내비게이션 active/inactive 클래스는 `scripts/build_site.py`에서 `active_tab` 기준으로 주입한다.
- Tailwind safelist는 동적 주입되는 `ds-nav-*`, `ds-tab-*`를 포함한다.

## 적용 규칙
- 신규 페이지는 다음 순서를 기본으로 사용:
  1. `<main class="ds-shell">`
  2. 상단 요약 섹션은 `ds-section` + `ds-kicker` + `ds-hero-title` + `ds-summary-*`
  3. 하단 관련가이드 섹션은 `ds-related-*`
  4. 작성/검수 영역은 `ds-meta-section`
- 상세가이드 하위 페이지도 동일 규칙을 사용하고, 본문 링크는 `ds-body-link`를 사용한다.
- 개별 페이지 특수 UI(계산기 폼, FAQ details 등)는 페이지 전용 클래스를 유지한다.
