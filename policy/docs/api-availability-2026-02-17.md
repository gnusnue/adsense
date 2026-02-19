# API Availability Check (2026-02-17)

기준 키: `DATA_GO_KR_API_KEY` (Decoding key)

## 되는 것 (호출 성공)

- `https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01` (`200`)
- `https://apis.data.go.kr/B552735/kisedKstartupService01/getBusinessInformation01` (`200`)
- `https://apis.data.go.kr/B552735/kisedKstartupService01/getContentInformation01` (`200`)
- `https://apis.data.go.kr/B552735/kisedKstartupService01/getStatisticalInformation01` (`200`)
- `https://apis.data.go.kr/1721000/msitannouncementinfo/businessAnnouncMentList` (`200`, `resultCode=00`)
- `https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist` (`200`, `resultCode=0`)
- `https://apis.data.go.kr/1741000/Subsidy24/getSubsidy24` (`200`, `resultCode=INFO-0`)
- `https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade` (`200`, 이전 동일 세션 확인)

## 조건부 (접근 가능, 파라미터 보강 필요)

- `https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001` (`200`, `resultCode=10`)
- `https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfaredetailed` (`200`, `resultCode=10`)
- `https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfaredetailedV001` (`200`, `resultCode=40`)

## 안 되는 것 (403)

- `https://apis.data.go.kr/B552735/kisedCertService/getProductInformation` (`403`)
- `https://apis.data.go.kr/B552735/kisedCertService/getCorporateInformation` (`403`)
- `https://apis.data.go.kr/B552735/kisedSlpService/getCenterSpaceList` (`403`)
- `https://apis.data.go.kr/B552735/kisedSlpService/getCenterList` (`403`)
- `https://apis.data.go.kr/B552735/kisedEduService/getEducationInformation` (`403`)
- `https://apis.data.go.kr/B551014/SRVC_OD_API_SUPP_BUSI_INFO/todz_api_supp_busi_info_i` (`403`)

## 이번 점검에서 endpoint 미확정

- `https://www.data.go.kr/data/15134251/openapi.do` (페이지 정적 HTML에서 host/path 자동추출 불가)

## 운영 권장 (v1)

1. 우선 primary는 `kisedKstartupService01/getAnnouncementInformation01` + `.../getBusinessInformation01`로 구성
2. `403` 엔드포인트는 별도 승인/권한 확인 전까지 비활성 유지
3. 조건부 엔드포인트는 필수 파라미터 스펙 확정 후 재검증
