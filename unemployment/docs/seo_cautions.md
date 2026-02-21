# Google Search Indexing & Ranking Rules (Unemployment Project)

목표: 신규 사이트가 Google Search에서 **색인(Index) 가능 상태**를 유지하고, **사람-우선(people-first)** 콘텐츠 + **기술/신뢰 신호**로 상위 노출 가능성을 극대화한다.

## 0) 용어

- **크롤링(Crawling)**: Googlebot이 URL을 방문해 콘텐츠를 가져오는 것
- **색인(Indexing)**: 가져온 콘텐츠를 Google 검색 DB에 등록하는 것
- **캐노니컬(Canonical)**: 중복/유사 URL 중 “대표 URL” 힌트
- **E-E-A-T**: Experience/Expertise/Authoritativeness/Trust (경험/전문성/권위/신뢰)

## 1) MUST: 색인/크롤링 기본 규칙 (이거 틀리면 검색에 안 뜸)

### 1.1 robots / noindex

- MUST: 중요한 페이지는 `robots.txt`로 막지 않는다.
- MUST: 검색 노출을 막고 싶다면 `noindex`를 사용한다. (robots만으로 “검색 제외”가 보장되지 않음)
- MUST: 배포 전/후에 **URL Inspection**으로 `Indexing allowed?` 확인.

### 1.2 Search Console + Sitemap

- MUST: Google Search Console에 사이트 등록 및 소유권 인증.
- MUST: `sitemap.xml` 생성 후 Search Console에 제출.
- SHOULD: robots.txt에 `Sitemap: https://example.com/sitemap.xml` 라인 추가.

### 1.3 URL 정규화(중복 방지)

- MUST: URL 규칙을 1개로 통일 (https, www/non-www, trailing slash, 대소문자).
- MUST: 중복/파라미터 페이지는 canonical/리다이렉트/내부링크로 신호를 일관되게 만든다.

## 2) MUST: 콘텐츠 규칙 (상위 노출의 핵심)

### 2.1 사람-우선 콘텐츠

- MUST: “검색엔진용”이 아니라 **사용자 문제 해결**이 1순위.
- MUST: 페이지마다 **검색 의도 1개**만 만족 (정의/비교/방법/가격/템플릿/리뷰 등 혼합 금지).
- MUST: 첫 화면(상단 5~10줄)에 **결론/요약/표/체크리스트**로 즉시 답 제공.

### 2.2 얇은/복붙/대량 생성 금지

- MUST NOT: 유사 문서 대량 생산(문장만 살짝 바꾸기), 자동 생성으로 페이지 수만 늘리기.
- MUST: “복제 불가” 요소 포함
  - 직접 해본 절차/실패/비용/스크린샷
  - 자체 데이터/계산 예시/다운로드 템플릿
  - 최신 기준(버전/날짜) 명시 + 변경 로그

### 2.3 업데이트 운영

- SHOULD: 핵심 글은 주기적으로 업데이트하고 `updated_at`(수정일) 및 변경사항을 기록.
- MUST: 오래된 정보(가격/법/정책/스펙)는 방치하지 않는다.

## 3) MUST: 신뢰(E-E-A-T) 규칙 (특히 돈/건강/법률 등 YMYL이면 필수)

- MUST: **작성자/운영자 정보**를 노출한다 (About, 프로필, 연락처, 책임 주체).
- MUST: 사실/통계/정책은 **1차 출처 링크**와 근거를 명시한다.
- MUST NOT: 과장/확정 표현 남발 (예: “무조건 1위”, “100%”, “확정 수익”).
- SHOULD: 리뷰/추천/비교 글은 선정 기준과 한계를 명시한다.

## 4) SHOULD: 사이트 구조/내부링크 규칙 (주제 권위 만들기)

- SHOULD: **허브-클러스터 구조** 운영
  - 허브(주제 대표 페이지) 1개
  - 클러스터(하위 글) 8~20개
- MUST: 내부링크 설계
  - 클러스터 → 허브 링크 필수
  - 관련 글끼리 2~3개 상호 연결
- MUST NOT: 빈 카테고리/태그 페이지 남발 (얇은 페이지 증가)

## 5) SHOULD: 성능/UX 규칙 (감점 방지)

- MUST: 모바일 기준으로 콘텐츠가 읽기 쉬워야 한다.
- SHOULD: Core Web Vitals를 “Good”에 가깝게 유지 (LCP/INP/CLS)
- SHOULD: 이미지 최적화(용량/포맷/lazy-load), 불필요한 JS 최소화, 폰트 최적화
- MUST NOT: 본문 가리는 과도한 팝업/광고/인터스티셜

## 6) SHOULD: 구조화 데이터(스키마) 규칙 (CTR/리치결과 도움)

- SHOULD: 해당되는 페이지에만 JSON-LD 구조화 데이터 적용 (Article/FAQ/HowTo/Product 등)
- MUST: 구조화 데이터 내용은 **페이지에 실제로 보이는 내용과 일치**해야 함
- MUST: 가이드 위반/스팸성 마크업 금지
- SHOULD: Rich Results Test + Search Console 리치결과 보고서로 검증

## 7) MUST NOT: 스팸/정책 위반 패턴 (회복이 어려움)

- MUST NOT: 만료 도메인/리다이렉트/대량 콘텐츠로 랭킹 조작(Expired domain abuse)
- MUST NOT: 대규모 저품질/비독창 콘텐츠 생산(Scaled content abuse)
- MUST NOT: 다른 사이트 권위에 기대는 기생 형태(Site reputation abuse)
- MUST NOT: 키워드 도배, 숨김 텍스트/링크, 링크 구매/교환 남발

## 8) 운영 체크리스트 (배포/운영 시 자동 점검 항목)

### 배포 직후 (D0)

- [ ] Search Console 등록/인증
- [ ] sitemap.xml 제출
- [ ] robots.txt에서 차단 규칙 점검
- [ ] 핵심 URL 5개 URL Inspection로 색인 가능 여부 확인
- [ ] https / www / slash 통일 + 리다이렉트 확인

### 콘텐츠 발행 (매 글마다)

- [ ] 검색 의도 1개로 고정
- [ ] 상단 요약/표/체크리스트 포함
- [ ] “경험/근거/데이터/템플릿” 최소 1개 포함
- [ ] 내부링크 3개 이상(허브/관련글/다음 행동)
- [ ] 제목(H1)과 메타 설명이 실제 내용과 일치

### 주간/월간

- [ ] Search Console: 노출↑인데 CTR↓ 페이지 → 제목/요약 개선
- [ ] Search Console: 순위 8~15위 페이지 → 내용 보강/내부링크 강화
- [ ] 중복/캐노니컬 이슈(“Google chose different canonical”) 점검
- [ ] CWV/성능 리그레션 점검

## 9) Done(완료) 정의 = 최소 합격 기준

- 색인: 핵심 페이지가 Search Console에서 “Indexed” 상태
- 정책: 스팸 정책 위반 패턴이 없음
- 콘텐츠: 상위 목표 키워드 클러스터(≥10개) 구축 + 허브 연결 완료
- 구조: 내부링크로 허브 권위가 누적되는 구조
- UX: 모바일에서 읽기/탐색 문제 없음, 과도한 팝업 없음

