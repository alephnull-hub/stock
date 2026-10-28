#!/usr/bin/env python3
"""메르의 블로그(blog.naver.com/ranto28) 새 글 수집기.

사용법:
  python3 scripts/blog_fetch.py <출력폴더>            # data/blog_state.json 의 마지막 글 이후 새 글만
  python3 scripts/blog_fetch.py <출력폴더> --all      # 첫 글부터 전부
  python3 scripts/blog_fetch.py <출력폴더> --update-state   # 수집 후 마지막 글 번호 기록

원문은 저작권 보호를 위해 저장소 밖(<출력폴더>, 예: 스크래치 폴더)에만 저장한다.
저장소에는 data/blog_insights.csv 에 요약·판정·링크만 남긴다.
카테고리: 21 경제/주식/국제정세/사회, 28 피드메이커(경제), 19 주절주절, 17 건강/의학/맛집/일상/역사
"""
import json, os, re, sys, time, html, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

BLOG = "ranto28"
UA = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "blog_state.json")


def fetch(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def list_page(page):
    raw = fetch(f"https://blog.naver.com/PostTitleListAsync.naver?blogId={BLOG}&currentPage={page}&countPerPage=30")
    return json.loads(raw.replace("\\'", "'"))  # 네이버 응답의 비표준 이스케이프 보정


def list_posts(after_logno=0):
    posts, page = [], 1
    while True:
        d = list_page(page)
        batch = d.get("postList", [])
        for x in batch:
            if int(x["logNo"]) > after_logno:
                posts.append({"logNo": x["logNo"], "categoryNo": x["categoryNo"],
                              "title": urllib.parse.unquote_plus(x["title"]), "date": x["addDate"]})
        # 목록은 최신순이지만 공지·고정글 때문에 순서가 약간 섞일 수 있어 한 페이지 여유를 둔다
        if not batch or (after_logno and all(int(x["logNo"]) <= after_logno for x in batch)):
            break
        if page * 30 >= int(d.get("totalCount", 0)):
            break
        page += 1
        time.sleep(0.3)
    return posts


def extract(s):
    d = re.search(r'se_publishDate[^>]*>(.*?)<', s)
    paras = re.findall(r'<p class="se-text-paragraph[^>]*>(.*?)</p>', s, re.S)
    lines = [html.unescape(re.sub(r'<[^>]+>', '', p)).replace('​', '').strip() for p in paras]
    return (d.group(1).strip() if d else ''), '\n'.join(l for l in lines if l)


def save_post(p, outdir):
    fn = os.path.join(outdir, p["logNo"] + ".txt")
    if os.path.exists(fn) and os.path.getsize(fn) > 50:
        return fn
    date, txt = extract(fetch(f"https://blog.naver.com/PostView.naver?blogId={BLOG}&logNo={p['logNo']}"))
    with open(fn, "w") as f:
        f.write(f"TITLE: {p['title']}\nDATE: {date or p['date']}\nCAT: {p['categoryNo']}\n"
                f"URL: https://blog.naver.com/{BLOG}/{p['logNo']}\n\n{txt}\n")
    time.sleep(0.2)
    return fn


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    after = 0 if "--all" in sys.argv else int(state.get("last_logNo", 0))
    posts = list_posts(after)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda p: save_post(p, outdir), posts))
    json.dump(posts, open(os.path.join(outdir, "_index.json"), "w"), ensure_ascii=False, indent=0)
    print(f"새 글 {len(posts)}개 → {outdir} (경제 카테고리 21/28: "
          f"{sum(p['categoryNo'] in ('21', '28') for p in posts)}개)")
    if "--update-state" in sys.argv and posts:
        state["last_logNo"] = max(int(p["logNo"]) for p in posts)
        state["updated"] = time.strftime("%Y-%m-%d %H:%M")
        json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
