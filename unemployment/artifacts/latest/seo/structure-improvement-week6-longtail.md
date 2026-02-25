## uem.cbbxs.com 롱테일 운영체계 구축 (Google Trends, 주간 수동)

기준일: 2026-02-25  
목표: 검색순위 개선을 위해 롱테일 키워드 발굴/선별/반영 루틴을 파일+검증 스크립트로 표준화

### 구현 항목
1. 롱테일 운영 디렉토리 신설
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/longtail`

2. 주간 문서 템플릿/초기 파일 생성
- `weekly-template.md`
- `weekly-2026-02-25.md`

3. 운영 로그 CSV 추가
- `keyword-backlog.csv` (`keyword,route,score,source,status`)
- `impact-log.csv` (`week,keyword,page,impressions,clicks,ctr,position,decision`)

4. 운영 가이드 문서화
- `README.md`에 고정 규칙(대한민국/웹검색/3뷰/주간 10개)과 45분 루틴 명시

5. 롱테일 품질 검증 스크립트 추가
- `/Users/eunsung/Documents/adsense/unemployment/scripts/longtail_quality_check.py`
- 검증 항목:
  - 최종 채택 키워드 10개 여부
  - 중복 키워드/허용 route/source/status 검증
  - Rising 최소 6개 검증
  - 공식 출처 링크 섹션/도메인 검증
  - backlog/impact CSV 스키마 검증

### 검증 결과
- `python3 unemployment/scripts/longtail_quality_check.py --weekly-file unemployment/artifacts/latest/seo/longtail/weekly-2026-02-25.md --backlog-file unemployment/artifacts/latest/seo/longtail/keyword-backlog.csv --impact-file unemployment/artifacts/latest/seo/longtail/impact-log.csv` 통과
- 기존 사이트 빌드/품질검사(`build_site.py`, `quality_check_site.py`) 영향 없음 확인

### 다음 실행 포인트
1. Google Trends 수집 후 `weekly-2026-02-25.md`의 TODO 키워드를 실제 후보로 교체
2. 채택 10개를 `keyword-backlog.csv`에 status=`live`로 반영
3. 2주/4주 지표를 `impact-log.csv`에 누적 기록
