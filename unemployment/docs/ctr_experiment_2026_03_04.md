# CTR Experiment Plan (2026-03-04)

## Goal

- 노출은 있으나 클릭이 0%인 핵심 페이지의 CTR 개선.
- 1차 목표: 순위 6~12 구간 URL의 CTR을 14일 내 1% 이상으로 끌어올리기.

## Scope

- `/income-report/`
- `/recognition/`
- `/apply/`
- `/faq/`
- `/eligibility/`

## Baseline (Search Console Snapshot)

- 기준일: 2026-03-04
- `/income-report/`: 노출 100, 클릭 0, CTR 0%, 평균순위 7.2
- `/recognition/`: 노출 16, 클릭 0, CTR 0%, 평균순위 7.8
- `/apply/`: 노출 29, 클릭 0, CTR 0%, 평균순위 11.4
- `/faq/`: 노출 11, 클릭 0, CTR 0%, 평균순위 11.7
- `/eligibility/`: 노출 4, 클릭 0, CTR 0%, 평균순위 10.8

## Changes Applied on 2026-03-04

- 제목/메타설명 CTR 카피 업데이트 (핵심 쿼리 전면 배치).
- H1/첫 문단 쿼리 정합 튜닝.
- 상단 `한눈에 결론` 블록 추가 (요약형 스니펫 노출 대응).
- 상단 `최종 검수일/기준 출처` 노출 강화.
- 내부 링크 앵커를 쿼리형 문구로 정교화.
- 롱테일 신규 페이지 2건 발행.

## Measurement Window

- 1차 체크: 2026-03-11 (7일)
- 2차 체크: 2026-03-18 (14일)

## Evaluation Rule

- URL별 CTR 절대 상승폭이 +0.8%p 이상이면 유지.
- CTR 개선이 없고 노출이 30 이상인 URL은 제목 A/B 2차 카피 적용.
- 순위가 15 이상으로 하락하면 CTR 카피 재실험보다 본문 정합/내부링크를 우선 보강.

## Data Pull Template

- Search Console > 성과 > 검색 결과
- 필터: 기간(최근 28일), 국가(대한민국), 검색 유형(웹)
- 컬럼: query, page, clicks, impressions, ctr, position

