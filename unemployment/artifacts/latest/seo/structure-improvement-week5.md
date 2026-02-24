## uem.cbbxs.com 5주차 실행 결과 (robots 운영 주체 단일화)

기준일: 2026-02-24
목표: robots 제어권을 Cloudflare managed로 단일화하고, 빌드/검증/배포 경로 전부 동일 정책으로 고정

### 실행 항목
1. 빌드 스크립트 robots 모드 도입
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
- 추가 파라미터: `--robots-mode`
- 지원 모드:
  - `cloudflare-managed` (기본): `dist/robots.txt`를 생성하지 않음
  - `build-managed`: 기존 방식으로 `robots.txt` 생성
- 안전장치:
  - cloudflare-managed인데 `dist/robots.txt`가 존재하면 빌드 실패

2. 품질검사에 robots 권한 검증 추가
- 수정 파일: `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- 추가 파라미터: `--robots-mode`
- 검증 규칙:
  - `cloudflare-managed`: `dist/robots.txt`가 없어야 통과
  - `build-managed`: `robots.txt` 존재 + `User-agent/Allow/Sitemap` 문구 검증

3. CI/배포 워크플로 일관성 반영
- 수정 파일:
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-refresh.yml`
  - `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-deploy.yml`
- 변경 사항:
  - 환경변수 `ROBOTS_MODE` 추가
  - build/quality 실행 시 `--robots-mode "$ROBOTS_MODE"` 전달
  - 기본값은 `cloudflare-managed`

### 검증 결과
- `npm run build:css` 성공
- `python3 scripts/build_site.py --site-base-url "https://uem.cbbxs.com" --robots-mode cloudflare-managed` 성공
- `python3 scripts/quality_check_site.py --dist-root apps/site/dist --site-base-url "https://uem.cbbxs.com" --robots-mode cloudflare-managed` 성공
- 확인: `dist/robots.txt` 미생성(Cloudflare managed 단일 정책)

### 변경 파일
- `/Users/eunsung/Documents/adsense/unemployment/scripts/build_site.py`
- `/Users/eunsung/Documents/adsense/unemployment/scripts/quality_check_site.py`
- `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-quality-gate.yml`
- `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-refresh.yml`
- `/Users/eunsung/Documents/adsense/.github/workflows/unemployment-deploy.yml`
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/structure-fix-checklist.md`
- `/Users/eunsung/Documents/adsense/unemployment/artifacts/latest/seo/structure-improvement-week5.md`

### 다음 라운드 후보
1. JSON-LD와 본문 간 의미 일치(semantic consistency) 자동검증
2. Lighthouse CI 모바일 성능 측정 자동화
3. Search Console 성능 API 기반 주간 CTR 튜닝 자동 리포트
