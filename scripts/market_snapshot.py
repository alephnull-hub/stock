#!/usr/bin/env python3
"""주간 리포트용 시장 데이터 수집기.

사용법:
  python3 scripts/market_snapshot.py                  # 시장 지표만
  python3 scripts/market_snapshot.py 005930.KS NVDA   # + 종목 밸류에이션
  python3 scripts/market_snapshot.py --save ...       # data/market_snapshot.csv 에 한 줄 추가

데이터 출처: Yahoo Finance chart / fundamentals-timeseries API, 네이버 증권 모바일 API.
모든 수치는 '직전 거래일 종가' 기준이며 지연될 수 있다.
"""
import csv, json, os, sys, time, datetime, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKETS = [
    # (심볼, 이름, 구분)
    ("^KS11", "코스피", "지수"), ("^KQ11", "코스닥", "지수"),
    ("^GSPC", "S&P500", "지수"), ("^IXIC", "나스닥", "지수"), ("^SOX", "필라델피아반도체", "지수"),
    ("^N225", "닛케이225", "지수"), ("000001.SS", "상해종합", "지수"), ("^NSEI", "인도 Nifty50", "지수"),
    ("^TWII", "대만가권", "지수"), ("^STOXX50E", "유로스톡스50", "지수"),
    ("KRW=X", "원/달러", "환율"), ("JPYKRW=X", "원/엔(1엔)", "환율"), ("DX-Y.NYB", "달러인덱스", "환율"),
    ("GC=F", "금(달러/온스)", "원자재"), ("HG=F", "구리(달러/파운드)", "원자재"), ("CL=F", "WTI유가", "원자재"),
    ("^TNX", "미국10년물금리(%)", "금리"), ("^IRX", "미국3개월물금리(%)", "금리"), ("^VIX", "VIX", "변동성"),
]


def get_json(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # 네트워크 일시 오류 재시도
            if i == tries - 1:
                print(f"[warn] {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** i)


def history(symbol, rng="5y", interval="1d"):
    d = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={rng}&interval={interval}")
    try:
        r = d["chart"]["result"][0]
        rows = [(t, c) for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None]
        return r["meta"], rows
    except (TypeError, KeyError, IndexError):
        return None, []


def pct(a, b):
    return None if not a or not b else round((a / b - 1) * 100, 1)


def market_row(symbol, name, kind):
    meta, rows = history(symbol)
    if not rows:
        return {"symbol": symbol, "name": name, "kind": kind}
    closes = [c for _, c in rows]
    last = meta.get("regularMarketPrice") or closes[-1]
    y1 = closes[-252:]
    hi, lo = max(y1), min(y1)
    pctile = round(sum(c <= last for c in closes) / len(closes) * 100)  # 5년 중 현재 위치
    ago = lambda n: closes[-n - 1] if len(closes) > n else None
    return {
        "symbol": symbol, "name": name, "kind": kind, "last": round(last, 2),
        "chg_1w": pct(last, ago(5)), "chg_1m": pct(last, ago(21)), "chg_1y": pct(last, ago(252)),
        "high_52w": round(hi, 2), "low_52w": round(lo, 2), "from_high": pct(last, hi),
        "pctile_5y": pctile,
        "asof": datetime.datetime.fromtimestamp(meta.get("regularMarketTime", rows[-1][0])).strftime("%Y-%m-%d"),
    }


def yahoo_fundamentals(symbol):
    types = ["trailingPeRatio", "forwardPeRatio", "trailingPbRatio", "trailingPsRatio",
             "trailingMarketCap", "trailingOperatingCashFlow", "trailingFreeCashFlow"]
    now = int(time.time())
    d = get_json("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
                 f"{urllib.parse.quote(symbol)}?type={','.join(types)}&period1={now - 400 * 86400}&period2={now}")
    out, cur = {}, {}
    for r in (d or {}).get("timeseries", {}).get("result", []) or []:
        t = r["meta"]["type"][0]
        if r.get(t):
            out[t] = r[t][-1]["reportedValue"]["raw"]
            cur[t] = r[t][-1].get("currencyCode")
    # ADR 등은 시총(USD)과 재무제표 통화(TWD, DKK…)가 달라 PCR 계산을 건너뛴다
    mc = out.get("trailingMarketCap")
    for key, cf in (("PCR", "trailingOperatingCashFlow"), ("PFCR", "trailingFreeCashFlow")):
        if mc and out.get(cf, 0) > 0 and cur.get(cf) == cur.get("trailingMarketCap"):
            out[key] = mc / out[cf]
    return out


def naver_kr(code):
    d = get_json(f"https://m.stock.naver.com/api/stock/{code}/integration")
    if not d:
        return {}
    info = {x["code"]: x["value"] for x in d.get("totalInfos", [])}
    num = lambda s: float(s.replace(",", "").replace("배", "").replace("원", "").replace("%", "")) if s and s[0].isdigit() else None
    return {"name": d.get("stockName"), "price": num(info.get("lastClosePrice", "")),
            "per": num(info.get("per", "")), "fwd_per": num(info.get("cnsPer", "")),
            "pbr": num(info.get("pbr", "")), "div_yield": num(info.get("dividendYieldRatio", "")),
            "high_52w": num(info.get("highPriceOf52Weeks", "")), "low_52w": num(info.get("lowPriceOf52Weeks", ""))}


def stock_row(symbol):
    meta, rows = history(symbol, "1y")
    f = yahoo_fundamentals(symbol)
    row = {"symbol": symbol, "price": meta and meta.get("regularMarketPrice"), "currency": meta and meta.get("currency"),
           "per": f.get("trailingPeRatio"), "fwd_per": f.get("forwardPeRatio"), "pbr": f.get("trailingPbRatio"),
           "psr": f.get("trailingPsRatio"), "pcr": f.get("PCR"), "pfcr": f.get("PFCR"),
           "mcap": f.get("trailingMarketCap")}
    if rows:
        closes = [c for _, c in rows]
        row["from_high"] = pct(row["price"] or closes[-1], max(closes))
    if symbol.endswith((".KS", ".KQ")):  # 국내 종목은 네이버 컨센서스로 보강
        n = naver_kr(symbol.split(".")[0])
        row["name"] = n.get("name")
        row["fwd_per"] = row["fwd_per"] or n.get("fwd_per")
        row["pbr"] = row["pbr"] or n.get("pbr")
        row["div_yield"] = n.get("div_yield")
    return row


def fmt(v, nd=1):
    if v is None:
        return "-"
    if isinstance(v, float):
        if abs(v) >= 1e9:
            return f"{v / 1e12:,.2f}T" if abs(v) >= 1e12 else f"{v / 1e9:,.1f}B"
        return f"{v:,.{nd}f}"
    return str(v)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    save = "--save" in sys.argv
    mk = [market_row(*m) for m in MARKETS]
    print("## 시장 지표\n")
    print("| 구분 | 지표 | 종가 | 1주 | 1개월 | 1년 | 52주 고점대비 | 5년 내 위치(%) | 기준일 |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---|")
    for r in mk:
        print(f"| {r['kind']} | {r['name']} | {fmt(r.get('last'), 2)} | {fmt(r.get('chg_1w'))}% | {fmt(r.get('chg_1m'))}% | "
              f"{fmt(r.get('chg_1y'))}% | {fmt(r.get('from_high'))}% | {fmt(r.get('pctile_5y'))} | {r.get('asof', '-')} |")
    st = [stock_row(s) for s in args]
    if st:
        print("\n## 종목 밸류에이션 (TTM, 직전 거래일)\n")
        print("| 종목 | 가격 | PER | 예상PER | PBR | PSR | PCR | P/FCF | 52주 고점대비 | 시총 |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in st:
            print(f"| {r.get('name') or r['symbol']} ({r['symbol']}) | {fmt(r['price'], 2)} {r.get('currency') or ''} | {fmt(r['per'])} | "
                  f"{fmt(r['fwd_per'])} | {fmt(r['pbr'], 2)} | {fmt(r['psr'], 2)} | {fmt(r['pcr'])} | {fmt(r['pfcr'])} | "
                  f"{fmt(r.get('from_high'))}% | {fmt(r['mcap'])} |")
    json.dump({"markets": mk, "stocks": st}, open(os.path.join(ROOT, "data", "latest_snapshot.json"), "w"),
              ensure_ascii=False, indent=1)
    if save:
        path = os.path.join(ROOT, "data", "market_snapshot.csv")
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "symbol", "name", "last", "chg_1w", "chg_1m", "chg_1y", "from_high", "pctile_5y"])
            today = datetime.date.today().isoformat()
            for r in mk:
                w.writerow([today, r["symbol"], r["name"], r.get("last"), r.get("chg_1w"), r.get("chg_1m"),
                            r.get("chg_1y"), r.get("from_high"), r.get("pctile_5y")])


if __name__ == "__main__":
    main()
