# Source Inventory (지원사업 수집)

기준일: 2026-02-17

## 목적

지원사업/정책 공고 수집에 사용하는 페이지, endpoint, 기대 응답 구조를 정리한다.

## Endpoint 정리

| 구분 | 페이지 URL | 호출 Endpoint | 기대 응답(Top-level) | 기대 데이터(`data[]` 핵심 필드) |
|---|---|---|---|---|
| 지원사업 공고(우선) | `https://nidview.k-startup.go.kr/view/public/kisedKstartupService/announcementInformation` | `https://nidview.k-startup.go.kr/view/public/call/kisedKstartupService/announcementInformation?page=1&perPage=...` | `currentCount, data, matchCount, page, perPage, totalCount` | `pbanc_sn, biz_pbanc_nm, pbanc_ctnt, supt_biz_clsfc, pbanc_rcpt_bgng_dt, pbanc_rcpt_end_dt, aply_trgt, supt_regin, detl_pg_url, biz_gdnc_url, sprv_inst` |
| 통합공고 사업정보(우선) | `https://nidview.k-startup.go.kr/view/public/kisedKstartupService/businessInformation` | `https://nidview.k-startup.go.kr/view/public/call/kisedKstartupService/businessInformation?page=1&perPage=...` | `currentCount, data, matchCount, page, perPage, totalCount` | `biz_category_cd, supt_biz_titl_nm, biz_supt_trgt_info, biz_supt_bdgt_info, biz_supt_ctnt, supt_biz_chrct, biz_yr, detl_pg_url` |
| 정책/가이드 콘텐츠(보강) | `https://nidview.k-startup.go.kr/view/public/kisedKstartupService/contentInformation` | `https://nidview.k-startup.go.kr/view/public/call/kisedKstartupService/contentInformation?page=1&perPage=...` | `currentCount, data, matchCount, page, perPage, totalCount` | `clss_cd, titl_nm, fstm_reg_dt, view_cnt, detl_pg_url, file_nm` |
| 통계/리포트(보강) | `https://nidview.k-startup.go.kr/view/public/kisedKstartupService/statisticalInformation` | `https://nidview.k-startup.go.kr/view/public/call/kisedKstartupService/statisticalInformation?page=1&perPage=...` | `currentCount, data, matchCount, page, perPage, totalCount` | `titl_nm, ctnt, fstm_reg_dt, last_mdfcn_dt, detl_pg_url, file_nm` |

## v1 운영 권장

1. Primary A: `announcementInformation`
2. Primary B: `businessInformation`
3. Secondary: `contentInformation`, `statisticalInformation`

## 참고

- 위 endpoint는 NIDView 공개 샘플 호출 경로 기준이다.
- 배포 전, 실제 운영 API key 정책과 호출 허용 범위를 재확인한다.
