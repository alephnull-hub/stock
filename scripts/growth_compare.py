#!/usr/bin/env python3
"""같은 세부 업종 후보들의 성장성 비교표.

사용법:
  python3 scripts/growth_compare.py 005930.KS 000660.KS MU
  python3 scripts/growth_compare.py 메모리=005930.KS,000660.KS,MU 클라우드=AMZN,MSFT --json 2>out.json

출력: 과거 매출 성장(3년 연평균), 올해·내년 컨센서스 매출·EPS 성장률, 영업이익률, ROE,
      예상 PER, PEG(예상 PER ÷ 내년 EPS 성장률%)
데이터: Yahoo Finance quoteSummary(earningsTrend, financialData, defaultKeyStatistics)와
        fundamentals-timeseries. 컨센서스는 애널리스트 평균이며 바뀔 수 있다.
"""
import http.cookiejar, json, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0"}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(url, as_json=True):
    for i in range(4):
        try:
            with opener.open(urllib.request.Request(url, headers=UA), timeout=30) as r:
                body = r.read().decode("utf-8")
                return json.loads(body) if as_json else body
        except Exception as e:
            if i == 3:
                print(f"[warn] {url[:80]}: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** i)


def crumb():
    for i in range(5):
        try:
            opener.open(urllib.request.Request("https://fc.yahoo.com", headers=UA), timeout=30)
        except Exception:
            pass  # 쿠키만 받으면 되므로 응답 오류는 무시
        c = get("https://query2.finance.yahoo.com/v1/test/getcrumb", as_json=False)
        if c:
            return c
        time.sleep(5 * (i + 1))  # 429(요청 과다) 대비
    sys.exit("Yahoo crumb 을 받지 못했다. 잠시 뒤 다시 실행한다.")


def raw(d, *keys):
    for k in keys:
        d = (d or {}).get(k)
    return d.get("raw") if isinstance(d, dict) else d


def row(sym, cr):
    q = get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(sym)}"
            f"?modules=earningsTrend,financialData,defaultKeyStatistics,price&crumb={urllib.parse.quote(cr)}")
    res = ((q or {}).get("quoteSummary") or {}).get("result") or [{}]
    r = res[0]
    trend = {t["period"]: t for t in (r.get("earningsTrend") or {}).get("trend", [])}
    fd, ks = r.get("financialData") or {}, r.get("defaultKeyStatistics") or {}
    now = int(time.time())
    ts = get("https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
             f"{urllib.parse.quote(sym)}?type=annualTotalRevenue&period1={now - 6 * 365 * 86400}&period2={now}")
    revs = []
    for x in ((ts or {}).get("timeseries") or {}).get("result") or []:
        revs = [v["reportedValue"]["raw"] for v in (x.get("annualTotalRevenue") or []) if v]
    cagr = ((revs[-1] / revs[-4]) ** (1 / 3) - 1) * 100 if len(revs) >= 4 and revs[-4] > 0 else None
    eps_ny = raw(trend.get("+1y"), "growth")
    fpe = raw(ks, "forwardPE")
    return {
        "symbol": sym, "name": raw(r.get("price"), "shortName") or sym,
        "rev_cagr3": cagr,
        "rev_g_cy": raw(trend.get("0y"), "revenueEstimate", "growth"), "rev_g_ny": raw(trend.get("+1y"), "revenueEstimate", "growth"),
        "eps_g_cy": raw(trend.get("0y"), "growth"), "eps_g_ny": eps_ny,
        "op_margin": raw(fd, "operatingMargins"), "roe": raw(fd, "returnOnEquity"),
        "fwd_pe": fpe, "peg": (fpe / (eps_ny * 100)) if fpe and eps_ny and eps_ny > 0 else None,
        "analysts": raw(trend.get("+1y"), "earningsEstimate", "numberOfAnalysts"),
    }


def pct(v, mult=100):
    return "-" if v is None else f"{v * mult:+.0f}%" if mult == 100 else f"{v:+.0f}%"


def table(rows):
    print("| 종목 | 매출 3년 연평균 | 올해 매출 성장(E) | 내년 매출 성장(E) | 올해 EPS 성장(E) | 내년 EPS 성장(E) | 영업이익률 | ROE | 예상 PER | PEG | 애널리스트 수 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        f = lambda v: "-" if v is None else f"{v:.1f}"
        print(f"| {r['name']} ({r['symbol']}) | {pct(r['rev_cagr3'], 1)} | {pct(r['rev_g_cy'])} | {pct(r['rev_g_ny'])} | "
              f"{pct(r['eps_g_cy'])} | {pct(r['eps_g_ny'])} | {pct(r['op_margin'])} | {pct(r['roe'])} | {f(r['fwd_pe'])} | {f(r['peg'])} | {r['analysts'] or '-'} |")


def main():
    """인자: 티커들, 또는 '그룹이름=티커,티커' 를 여러 개(한 번의 crumb 로 모두 조회)."""
    cr = crumb()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    groups = [a.split("=", 1) for a in args if "=" in a] or [("", ",".join(args))]
    out = {}
    for name, tickers in groups:
        rows = [row(t, cr) for t in tickers.split(",") if t]
        if name:
            print(f"\n### {name}\n")
        table(rows)
        out[name] = rows
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
