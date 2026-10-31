#!/usr/bin/env python3
"""추천 종목의 52주 고점 대비 하락폭.

사용법:
  python3 scripts/pick_drawdown.py              # data/dashboard_inputs.json 의 portfolio 10종목
  python3 scripts/pick_drawdown.py MSFT 000660.KS

52주 고점은 최근 1년 일간 종가 중 최고값이다(장중 고가가 아님). 현재가가 더 높으면 현재가를 고점으로 본다.
KRX-GOLD 는 국제 금(GC=F) × 원/달러(KRW=X) ÷ 31.1035 로 원/g 시계열을 만들어 계산한다.
"""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import market_snapshot as ms

ROOT = ms.ROOT


def _day(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d")


def daily_closes(ticker):
    """[(날짜, 종가)] 최근 1년."""
    if ticker == "KRX-GOLD":
        _, gold = ms.history("GC=F", "1y")
        _, fx = ms.history("KRW=X", "1y")
        fxd = {_day(t): c for t, c in fx}
        return [(_day(t), c * fxd[_day(t)] / 31.1035) for t, c in gold if _day(t) in fxd]
    _, rows = ms.history(ticker, "1y")
    return [(_day(t), c) for t, c in rows]


def drawdown(ticker, now=None):
    rows = daily_closes(ticker)
    if not rows:
        return {"high_52w": None, "high_date": None, "from_high": None}
    hi_date, hi = max(rows, key=lambda r: r[1])
    now = now or rows[-1][1]
    if now > hi:
        hi_date, hi = "현재", now
    fh = ms.pct(now, hi)
    return {"high_52w": round(hi, 2), "high_date": hi_date, "from_high": None if fh is None else fh + 0.0}  # -0.0 방지


def now_price(ticker):
    """한국 종목은 네이버 현재가(야후 일봉 마지막 값은 장 마감 전 값일 수 있다), 그 외는 일봉 마지막 종가."""
    if ticker.endswith((".KS", ".KQ")):
        d = ms.get_json(f"https://m.stock.naver.com/api/stock/{ticker.split('.')[0]}/basic") or {}
        v = d.get("closePrice", "").replace(",", "")
        return float(v) if v else None
    return None


def main():
    tickers = sys.argv[1:]
    if not tickers:
        inp = json.load(open(os.path.join(ROOT, "data", "dashboard_inputs.json")))
        tickers = [p["ticker"] for p in inp["portfolio"]]
    print("| 종목 | 현재가(종가) | 52주 고점(종가) | 고점일 | 고점 대비 |")
    print("|---|---:|---:|---|---:|")
    for t in tickers:
        rows = daily_closes(t)
        last = now_price(t) or (rows[-1][1] if rows else None)
        d = drawdown(t, last)
        print(f"| {t} | {ms.fmt(last)} | {ms.fmt(d['high_52w'])} | {d['high_date'] or '-'} | {ms.fmt(d['from_high'])}% |")


if __name__ == "__main__":
    main()
