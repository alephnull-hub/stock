#!/usr/bin/env python3
"""웹 대시보드용 데이터 파일(JSON)을 만든다.

사용법:
  python3 scripts/build_dashboard.py <출력폴더>

입력: data/dashboard_inputs.json(리포트별 판단), data/latest_snapshot.json(market_snapshot.py 결과),
      data/recommendations.csv, data/position_reviews.csv, data/blog_insights.csv, README.md 리포트 목록
출력: <출력폴더>/<dataset>.json  — 각 파일을 대시보드에 올리고 datasets/<id> 의 url·updated 를 갱신한다.
"""
import csv, json, os, re, sys, time, datetime, urllib.request, urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}


def get_json(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(2 ** i)
    return None


def num(s):
    try:
        return float(str(s).replace(",", "").replace("원", "").replace("배", "").replace("%", ""))
    except ValueError:
        return None


def naver_price(code):
    """네이버 basic 은 현재가(장중) / integration 의 lastClosePrice 는 전일 종가라 basic 을 쓴다."""
    d = get_json(f"https://m.stock.naver.com/api/stock/{code}/basic") or {}
    return num(d.get("closePrice", ""))


def history(symbols):
    rows = []
    for sym, label in symbols:
        d = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=1y&interval=1wk")
        try:
            r = d["chart"]["result"][0]
            for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
                if c is not None:
                    rows.append({"date": datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d"),
                                 "series": label, "close": round(c, 2)})
        except (TypeError, KeyError, IndexError):
            print(f"[warn] history {sym}", file=sys.stderr)
    return rows


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    inp = json.load(open(os.path.join(ROOT, "data", "dashboard_inputs.json")))
    snap = json.load(open(os.path.join(ROOT, "data", "latest_snapshot.json")))
    mk = {m["symbol"]: m for m in snap["markets"]}
    ds = {}

    ds["market"] = [{k: m.get(k) for k in ("kind", "name", "symbol", "last", "chg_1w", "chg_1m", "chg_1y", "from_high", "pctile_5y", "asof")}
                    for m in snap["markets"] if m.get("last") is not None]
    ds["history"] = history([("^KS11", "코스피"), ("^GSPC", "S&P500"), ("GC=F", "금"), ("KRW=X", "원/달러")])
    ds["facts"] = inp["facts"]
    ds["thermometer"] = inp["thermometer"]
    ds["macro"] = inp["macro"]
    ds["pricedin"] = inp["pricedin"]
    ds["events"] = inp["events"]
    ds["watchouts"] = inp["watchouts"]
    ds["sectors"] = inp["sectors"]

    # 추천: 종목별 마지막 추천 행 중 마지막 점검 판정이 '매도'가 아닌 것(최대 5개) + 현재가·수익률
    recs = list(csv.DictReader(open(os.path.join(ROOT, "data", "recommendations.csv"))))
    revs = list(csv.DictReader(open(os.path.join(ROOT, "data", "position_reviews.csv"))))
    last_status = {}
    for v in sorted(revs, key=lambda v: v["date"]):
        last_status[v["ticker"]] = v["status"]
    latest = {}
    for r in recs:
        latest[r["ticker"]] = r
    active = [r for t, r in latest.items() if last_status.get(t) not in ("매도", "교체")]
    active = sorted(active, key=lambda r: (r["date"], -int(r["rank"])), reverse=True)[:5]
    gold_g = mk["GC=F"]["last"] * mk["KRW=X"]["last"] / 31.1035
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import market_snapshot as ms

    def now_price(r, det):
        t = r["ticker"]
        if t == "KRX-GOLD":
            return round(gold_g)
        if t.endswith((".KS", ".KQ")):
            return naver_price(det.get("now_symbol", t.split(".")[0]))
        meta, _ = ms.history(t, "5d")
        return meta and meta.get("regularMarketPrice")

    picks = []
    for r in active:
        det = inp["picks_detail"].get(r["ticker"], {})
        now = now_price(r, det)
        rec = float(r["price"])
        picks.append({"rank": int(r["rank"]), "name": r["name"], "ticker": r["ticker"], "sector": r["sector"], "kind": r["type"],
                      "rec_date": r["date"], "rec_price": rec, "now_price": now, "unit": r["currency"],
                      "ret_pct": round((now / rec - 1) * 100, 1) if now else None,
                      "buy1": float(r["buy_zone_1"]), "buy2": float(r["buy_zone_2"]), "buy3": float(r["buy_zone_3"]),
                      "in_zone": "1차 구간 안" if now and now <= float(r["buy_zone_1"]) else "1차 구간 위",
                      "per": det.get("per"), "fwd_per": det.get("fwd_per"), "pbr": det.get("pbr"), "pcr": det.get("pcr"), "psr": det.get("psr"),
                      "thesis": r["thesis"], "risk": r["key_risk"], "sell_trigger": r["sell_trigger"], "action": det.get("action", "")})
    ds["picks"] = sorted(picks, key=lambda p: p["rank"])

    ds["reviews"] = [{"at": r["date"], "ticker": r["ticker"], "name": r["name"], "price": float(r["price"]),
                      "ret_pct": float(r["return_pct"]), "status": r["status"], "reason": r["reason"], "key": f"{r['date']}|{r['ticker']}"}
                     for r in csv.DictReader(open(os.path.join(ROOT, "data", "position_reviews.csv")))]

    # 블로그: 반기별 판정·적중 집계 + 최근 30일 주요 글
    blog = list(csv.DictReader(open(os.path.join(ROOT, "data", "blog_insights.csv"))))
    per = defaultdict(Counter)
    for b in blog:
        y, m = int(b["date"][:4]), int(b["date"][5:7])
        p = f"{y} {'상' if m <= 6 else '하'}반기"
        per[p]["posts"] += 1
        per[p][b["verdict"]] += 1
        o = re.match(r"(적중|부분적중|빗나감)", b["outcome"] or "")
        if o:
            per[p][o.group(1)] += 1
    ds["blog_periods"] = [{"period": p, "posts": c["posts"], "accept": c["반영"], "partial": c["일부반영"], "counter": c["반론"],
                           "info": c["참고"], "hit": c["적중"], "partial_hit": c["부분적중"], "miss": c["빗나감"]}
                          for p, c in sorted(per.items())]
    cutoff = (datetime.date.fromisoformat(max(b["date"] for b in blog)) - datetime.timedelta(days=30)).isoformat()
    ds["blog_recent"] = [{"date": b["date"], "logNo": b["logNo"], "title": b["title"], "claim": b["claim"], "verdict": b["verdict"],
                          "rationale": b["rationale"], "url": f"https://blog.naver.com/ranto28/{b['logNo']}"}
                         for b in sorted(blog, key=lambda b: b["date"], reverse=True)
                         if b["date"] >= cutoff and b["verdict"] != "참고"]

    # 미국 후보: 판단은 inputs, 가격·밸류에이션은 market_snapshot 의 수집 함수로 새로 가져온다
    us = []
    for c in inp.get("us_candidates", []):
        r = ms.stock_row(c["ticker"])
        price = r.get("price")
        us.append({**c, "price": price, "from_high": r.get("from_high"), "per": r.get("per") and round(r["per"], 1),
                   "pcr": r.get("pcr") and round(r["pcr"], 1), "psr": r.get("psr") and round(r["psr"], 1),
                   "zone": ("1차 구간 안" if price and price <= c["buy1"] else "1차 구간 위") if price else "-"})
    ds["us_candidates"] = us

    # 세부 업종 내 성장성 비교(METHODOLOGY 4-6): growth_compare.py --json 결과 + 지속성 필터 메모
    gpath = os.path.join(ROOT, "data", "growth_compare_raw.json")
    picked = {p["ticker"] for p in ds["picks"]}
    growth = []
    if os.path.exists(gpath):
        filt = inp.get("growth_filters", {})
        for group, rows in json.load(open(gpath)).items():
            g = []
            for r in rows:
                two = lambda a, b: (1 + a) * (1 + b) - 1 if a is not None and b is not None else None
                g.append({"key": f"{group}|{r['symbol']}", "group": group, "ticker": r["symbol"], "name": r["name"],
                          "rev2y": two(r["rev_g_cy"], r["rev_g_ny"]), "eps2y": two(r["eps_g_cy"], r["eps_g_ny"]),
                          "roe": r["roe"], "peg": r["peg"], "fwd_pe": r["fwd_pe"], "filter": filt.get(r["symbol"], ""),
                          "picked": "추천" if r["symbol"] in picked else ""})
            for f in ("rev2y", "eps2y", "roe"):
                order = sorted([x for x in g if x[f] is not None], key=lambda x: -x[f])
                for i, x in enumerate(order):
                    x["rank_" + f] = i + 1
            for x in g:
                x["rank_sum"] = sum(x.get("rank_" + f, len(g)) for f in ("rev2y", "eps2y", "roe"))
            growth += sorted(g, key=lambda x: (x["rank_sum"], x["peg"] if x["peg"] is not None else 99))
    ds["growth"] = growth

    # 리포트 목록: README 표에서 읽는다
    reps = []
    for line in open(os.path.join(ROOT, "README.md")):
        m = re.match(r"\| \[([^\]]+)\]\(([^)]+)\) \| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\|", line)
        if m:
            reps.append({"date": m.group(1), "kind": m.group(3).strip(), "temp": m.group(4).strip(), "picks": m.group(5).strip(),
                         "sell": m.group(6).strip(), "url": "https://github.com/alephnull-hub/stock/blob/main/" + m.group(2)})
    ds["reports"] = reps

    for k, v in ds.items():
        json.dump(v, open(os.path.join(out, f"{k}.json"), "w"), ensure_ascii=False)
        print(k, len(v))


if __name__ == "__main__":
    main()
