---
name: stock-report
description: 10년 장기투자 주간/수시 리포트 작성. "지금 조사해줘", "리포트 만들어줘", 주간 예약 실행 시 사용. 시장 온도계, 거시·환율, 메르 블로그 검토, 매도 검토, 3종목 추천을 작성해 main 브랜치에 누적한다.
---

# 장기투자 리포트 작성 절차

판단 기준은 저장소 루트의 `METHODOLOGY.md` 를 따른다. 먼저 읽는다.

## 0. 종류와 파일명 결정
- 일요일 정기 실행(예약 작업) → `reports/weekly/YYYY-MM-DD.md`
- 사용자가 수시로 요청 → `reports/adhoc/YYYY-MM-DD-HHMM.md` (한국시간)
- 날짜·시각은 `TZ=Asia/Seoul date` 로 구한다.

## 1. 이전 기록 읽기
- `README.md` 의 리포트 목록에서 **가장 최근 리포트**를 읽는다.
- `data/recommendations.csv`(추천 이력), `data/position_reviews.csv`(보유 판정), `data/blog_insights.csv`(블로그 주장) 를 읽는다.

## 2. 데이터 수집
1. 시장 지표 + 지난 추천 종목 + 이번 주 후보 종목:
   `python3 scripts/market_snapshot.py --save <지난 추천 티커들> <후보 티커들>`
   (국내 종목은 `005930.KS` 형식, 코스닥은 `.KQ`)
   - Yahoo의 비율(PER·PBR·PCR)은 며칠 전 가격 기준일 수 있다. 장중 급등락이 있으면 네이버 EPS·BPS(`https://m.stock.naver.com/api/stock/<코드>/integration`)로 현재가 기준으로 다시 계산한다.
   - 추천 이력의 `KRX-GOLD`(금현물)는 `GC=F × KRW=X ÷ 31.1035` 로 원/g 이론가를 계산해 추적한다.
2. 웹 검색(기본 standard 모드)으로 보강:
   - 코스피·코스닥 12개월 예상 PER/PBR, S&P500 예상 PER(FactSet Earnings Insight 최신호), CAPE(multpl), 버핏지수
   - IMF/OECD 성장률 전망과 조정, 미국·한국 기준금리 예상 경로, 환율 이슈, 지정학 이슈
   - 지난 추천 종목의 최근 실적·공시·뉴스(성장동력 점검용)
3. 블로그 새 글:
   `python3 scripts/blog_fetch.py <스크래치폴더>/blog --update-state`
   원문은 스크래치 폴더에만 둔다. 저장소에 복사하지 않는다.

## 3. 분석 순서
1. **매도 검토**: 지난 추천 전부를 METHODOLOGY 5장 기준으로 판정 → `data/position_reviews.csv` 에 행 추가
2. **시장 온도계**: METHODOLOGY 2장 표대로 시장별 점수 → 5단계 판정 + 매수 방식
3. **거시·환율이 단기적으로 가격에 반영된 정도**: 성장률 조정, 금리, 환율 → 한국/미국 주식과 금에 각각 무엇을 의미하는지
4. **블로그 검토**: 새 경제 글마다 반영/일부 반영/반론/참고 판정 → `data/blog_insights.csv` 에 행 추가. 과거 주장 중 결과가 확인된 것은 `outcome` 갱신
5. **업종 점수표**: METHODOLOGY 3장. 지난주 대비 점수 변화와 이유
6. **이번 주 3종목**: 서로 다른 업종. 시장이 고평가 이상이면 방어형 1개 포함. 재추천이면 표시
   → `data/recommendations.csv` 에 3행 추가

## 4. 리포트 양식 (`reports/TEMPLATE.md` 복사해서 채움)
섹션 순서: 요약 → 🚨 매도 검토 → 시장 온도계 → 거시·환율 → 블로그 검토 → 업종 점수표 → 이번 주 3종목 → 지난 추천 추적 → 출처 → 면책
- 모든 수치에 기준일, 주요 주장에 출처 링크
- 확인 못 한 수치는 "미확인"으로 적고 추정하지 않는다

## 5. 저장
1. `README.md` 의 「최신 리포트」 링크와 「리포트 목록」 표에 한 줄 추가
2. 커밋 후 **main 브랜치에 push**:
   ```bash
   git add -A && git commit -m "리포트: YYYY-MM-DD (weekly|adhoc)"
   git push origin HEAD:main
   ```
   push 실패 시 `git pull --rebase origin main` 후 재시도(네트워크 오류는 2·4·8·16초 간격 최대 4회).
3. 사용자에게 요약(시장 판정 한 줄, 매도 검토 종목, 3종목과 매수 구간)과 리포트 링크
   `https://github.com/alephnull-hub/stock/blob/main/<리포트 경로>` 를 알린다.
