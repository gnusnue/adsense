# uem.cbbxs.com Search Console 재크롤링 체크리스트

기준일: 2026-02-22

## 1) 속성/사이트맵
- [ ] Search Console 속성 선택: `https://uem.cbbxs.com/`
- [ ] `sitemap.xml` 재제출: `https://uem.cbbxs.com/sitemap.xml`
- [ ] 상태가 `성공`으로 반영되는지 확인

## 2) 우선 색인 요청 URL (핵심 6개)
- [ ] `https://uem.cbbxs.com/`
- [ ] `https://uem.cbbxs.com/apply/`
- [ ] `https://uem.cbbxs.com/eligibility/`
- [ ] `https://uem.cbbxs.com/recognition/`
- [ ] `https://uem.cbbxs.com/income-report/`
- [ ] `https://uem.cbbxs.com/faq/`

요청 방법: Search Console > URL 검사 > "실시간 테스트" > "색인 생성 요청"

## 3) 정리된 URL 확인 (중복/레거시)
- [ ] `https://uem.cbbxs.com/calculator/` 가 `301 -> /`인지 확인
- [ ] `https://uem.cbbxs.com/about/` 가 `301 -> /`인지 확인
- [ ] `https://uem.cbbxs.com/updates/` 가 `301 -> /`인지 확인
- [ ] `https://uem.cbbxs.com/fraud-risk/` 가 `301 -> /`인지 확인
- [ ] 임의 URL(예: `/random-not-exist-123/`)이 `404`인지 확인

## 4) 일주일 모니터링
- [ ] 색인 생성 > 페이지 탭에서 제외 사유 확인
- [ ] `중복, Google에서 다른 표준 페이지 선택함` 감소 여부 확인
- [ ] 실적 > 검색 결과에서 핵심 6개 URL 노출/클릭 증가 확인

## 5) 성공 기준
- [ ] 핵심 6개 URL 모두 `색인됨`
- [ ] 레거시 URL이 별도 색인되지 않음
- [ ] 404 URL이 `색인 안 됨`으로 유지됨
