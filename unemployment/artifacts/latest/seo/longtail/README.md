# uem.cbbxs.com Longtail 운영 가이드

## 목적
Google Trends(대한민국) + Search Console만 사용해 매주 롱테일 10개를 선별하고,
기존 6페이지(`/`, `/apply/`, `/eligibility/`, `/recognition/`, `/income-report/`, `/faq/`)에 반영한다.

## 고정 운영 규칙
- 지역: 대한민국
- 검색 유형: 웹 검색
- Trends 확인 뷰:
  - 지난 12개월 / 대한민국 / 웹 검색
  - 지난 30일 / 대한민국 / 웹 검색
  - 지난 5년 / 대한민국 / 웹 검색
- 수집 대상: 관련 검색어 `Top`, `Rising`
- 주간 채택량: 10개
- 신규 URL 생성: 금지

## 산출물
1. `weekly-YYYY-MM-DD.md`
2. `keyword-backlog.csv`
3. `impact-log.csv`

## 주간 작업 순서 (45분)
1. 20분: Trends 수집/후보 생성
2. 10분: 스코어링/최종 10개 확정
3. 10분: 2~3페이지 반영안 작성
4. 5분: 다음 주 실험군 정의

## 검증 명령
아래 명령으로 주간 파일과 백로그 형식을 점검한다.

```bash
python3 unemployment/scripts/longtail_quality_check.py \
  --weekly-file unemployment/artifacts/latest/seo/longtail/weekly-YYYY-MM-DD.md \
  --backlog-file unemployment/artifacts/latest/seo/longtail/keyword-backlog.csv
```

## 스코어링 기준 (10점)
- 의도 적합도: 0~4
- 상승 신호: 0~3
- 전환 기여도: 0~2
- 카니벌 위험: 0~-2

채택 규칙:
- 동일 키워드는 1개 페이지만 타깃
- 카니벌 위험 -2는 제외
- 최종 10개 중 Rising 출처 최소 6개
