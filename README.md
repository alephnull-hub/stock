# 10년 장기투자 리포트

현재 국제 정세와 과학기술 발전 방향으로 **10년 뒤 성장 가능성이 높은 업종**을 고르고, 그 업종의 유망 기업·ETF·금현물을 매주 5개씩 추천하는 리포트 저장소입니다.

- **주간 리포트**: 매주 일요일 07:30(한국시간) 자동 작성 → `reports/weekly/`
- **수시 리포트**: 요청할 때 작성 → `reports/adhoc/`
- **판단 기준**: [METHODOLOGY.md](METHODOLOGY.md) (시장 온도계, 업종 점수, 매수 구간, 매도 신호, 블로그 검토 규칙)

> ⚠️ 공개 정보 기반 개인 참고용 분석이며 투자 자문이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.

## 최신 리포트
<!-- latest -->
**[2026-10-29 수시](reports/adhoc/2026-10-29-0900.md)**: 한국 ⚪적정 / 미국 🟠고평가 · **5종목**: 삼성전자 · HD현대일렉트릭 · 금현물 · 아마존🆕 · 인도 Nifty50 ETF🆕 · [웹 대시보드](https://claude.ai/artifact/U2fNy5KyG9QKSqPnfaPX5v)

## 리포트 목록
| 날짜 | 종류 | 시장 온도(한국/미국) | 추천 종목 | 매도 검토 |
|---|---|---|---|---|
| [2026-10-29 15:40](reports/adhoc/2026-10-29-0900.md) | 수시(5종목 확대) | ⚪적정 / 🟠고평가 | 삼성전자 · HD현대일렉트릭 · 금현물(KRX) · 아마존🆕 · 인도 Nifty50 ETF🆕 | 없음(삼성전자 관찰→유지 복귀) |
| [2026-10-29 09:00](reports/adhoc/2026-10-29-0900.md) | 수시(점검) | ⚪적정 / 🟠고평가 | 유지: 삼성전자 · HD현대일렉트릭 · 금현물(KRX) | 삼성전자 🟡관찰(빅테크 설비투자 예상 하회) |
| [2026-10-28 14:30](reports/adhoc/2026-10-28-1430.md) | 수시(점검) | ⚪적정 / 🟠고평가 | 유지: 삼성전자 · HD현대일렉트릭 · 금현물(KRX) | 없음(3종목 🟢유지) |
| [2026-10-28 14:00](reports/adhoc/2026-10-28-1400.md) | 수시(기준) | ⚪적정 / 🟠고평가 | 삼성전자 · HD현대일렉트릭 · 금현물(KRX) | 해당 없음(첫 리포트) |

## 누적 데이터
| 파일 | 내용 |
|---|---|
| [data/recommendations.csv](data/recommendations.csv) | 추천 이력(추천가, 매수 구간, 투자 논리, 매도 신호) |
| [data/position_reviews.csv](data/position_reviews.csv) | 지난 추천 종목의 매주 판정(유지/관찰/비중 축소/매도) |
| [data/market_snapshot.csv](data/market_snapshot.csv) | 주간 시장 지표 기록 |
| [data/blog_insights.csv](data/blog_insights.csv) | [메르의 블로그](https://blog.naver.com/ranto28) 글별 핵심 주장·판정(요약과 링크만) |
| [data/blog_themes.md](data/blog_themes.md) | 블로그 전체(2022.3~) 시기별 핵심 주제와 적중 여부 |

## 도구
```bash
python3 scripts/market_snapshot.py --save 005930.KS NVDA   # 시장 지표 + 종목 밸류에이션(PER/PBR/PCR/PSR)
python3 scripts/blog_fetch.py /tmp/blog --update-state      # 블로그 새 글 수집(원문은 저장소 밖에 저장)
```
작성 절차는 [.claude/skills/stock-report/SKILL.md](.claude/skills/stock-report/SKILL.md)에 있습니다.
