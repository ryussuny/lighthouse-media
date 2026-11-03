"""아침 뉴스 브리핑 (매일 08:00 스케줄러 실행)
네이버 뉴스 검색 → 겹치는 기사 묶기 → 기사마다 세 줄 요약 → data/news-briefing.json
관제탑 표시는 send-heartbeat.py가 이 파일을 하트비트에 실어 보낸다.

뉴스 조회 경로:
  .env에 NAVER_HUB_CLIENT_ID / NAVER_HUB_CLIENT_SECRET 가 있으면 NAVER API HUB(본인 키)
  없으면 k-skill-proxy(키 없이 조회되는 공개 중계 서버)
옵션: --dry-run (요약 API 호출·파일 저장 없이 수집 결과만 출력)
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, datetime, email.utils, urllib.request, urllib.parse
import requests
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, ".env"), override=True)  # 빈 환경변수가 .env 값을 가리지 않게
CONFIG = os.path.join(BASE, "config", "news-briefing.json")
OUT = os.path.join(BASE, "data", "news-briefing.json")
ARCHIVE_DIR = os.path.join(BASE, "logs", "news-briefing")

HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
PROXY_URL = os.environ.get("KSKILL_PROXY_BASE_URL", "https://k-skill-proxy.nomadamas.org") + "/v1/naver-news/search"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
KST = datetime.timezone(datetime.timedelta(hours=9))


def strip_tags(s):
    s = re.sub(r"</?b>", "", s or "")
    for a, b in (("&quot;", '"'), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&apos;", "'"), ("&#39;", "'")):
        s = s.replace(a, b)
    return s.strip()


def fetch_news(query, display=30):
    """검색어 1개 → [{title, desc, link, origin, pub(datetime)}]"""
    cid, sec = os.environ.get("NAVER_HUB_CLIENT_ID"), os.environ.get("NAVER_HUB_CLIENT_SECRET")
    params = urllib.parse.urlencode({"query": query, "display": display, "sort": "date"})
    if cid and sec:
        req = urllib.request.Request(f"{HUB_URL}?{params}", headers={
            "X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec})
        source = "hub"
    else:
        req = urllib.request.Request(f"{PROXY_URL}?{params}", headers={"User-Agent": "lighthouse-news-briefing"})
        source = "proxy"
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    items = []
    for it in data.get("items", []):
        raw_pub = it.get("pub_date_iso") or it.get("pubDate") or it.get("pub_date") or ""
        try:
            if raw_pub.endswith("Z") or "T" in raw_pub:
                pub = datetime.datetime.fromisoformat(raw_pub.replace("Z", "+00:00"))
            else:
                pub = email.utils.parsedate_to_datetime(raw_pub)
        except Exception:
            pub = None
        items.append({
            "title": strip_tags(it.get("title")),
            "desc": strip_tags(it.get("description")),
            "link": it.get("link") or "",
            "origin": it.get("original_link") or it.get("originallink") or "",
            "pub": pub,
        })
    return items, source


def collect(keywords, hours):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    seen_link, seen_title, out, errors, sources = set(), set(), [], [], set()
    for kw in keywords:
        try:
            items, src = fetch_news(kw)
            sources.add(src)
        except Exception as e:
            errors.append(f"{kw}: {str(e)[:80]}")
            continue
        taken = 0
        for it in items:
            if taken >= 12:  # 검색어마다 고르게 — 한 검색어가 후보를 독식하지 않게
                break
            if not it["pub"] or it["pub"] < cutoff:
                continue
            tkey = re.sub(r"\W", "", it["title"])[:30]
            if it["link"] in seen_link or tkey in seen_title:
                continue
            seen_link.add(it["link"]); seen_title.add(tkey)
            it["keyword"] = kw
            out.append(it)
            taken += 1
    out.sort(key=lambda x: x["pub"], reverse=True)
    return out[:60], errors, sorted(sources)


def summarize(name, articles, max_items):
    """Claude로 겹치는 기사 묶기 + 세 줄 요약. 근거는 제목·요약문뿐 — 지어내지 않게 지시한다."""
    lines = [f"[{i}] ({a['keyword']}) {a['title']} — {a['desc']}" for i, a in enumerate(articles)]
    prompt = f"""다음은 '{name}' 주제로 최근 하루 동안 나온 네이버 뉴스 목록이다(번호·검색어·제목·요약문).

{chr(10).join(lines)}

할 일:
1. 같은 사건을 다룬 기사는 하나로 묶는다.
2. 이 주제를 매일 챙겨보는 목사님·1인 미디어 사업가에게 중요한 순서로 최대 {max_items}건을 고른다. 주제와 무관한 기사(검색어가 우연히 겹친 연예·광고 기사 등)는 버린다.
3. 각 건마다 세 줄 요약을 쓴다. 한 줄은 한 문장, 40자 안팎.
4. 요약은 위 제목·요약문에 있는 내용만 쓴다. 없는 수치·인물·사실을 지어내지 않는다. 정보가 부족하면 짧게 쓴다.

JSON만 출력한다(설명 문장·코드블록 표시 금지):
{{"items":[{{"title":"대표 제목","summary":["첫 줄","둘째 줄","셋째 줄"],"ids":[0,3]}}]}}"""
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 3000, "messages": [{"role": "user", "content": prompt}]}, timeout=120)
    r.raise_for_status()
    text = r.json()["content"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    result = []
    for it in data.get("items", [])[:max_items]:
        ids = [i for i in it.get("ids", []) if isinstance(i, int) and 0 <= i < len(articles)]
        if not ids:
            continue  # 원문과 연결 안 되는 항목은 버린다(링크 없는 요약 금지)
        first = articles[ids[0]]
        result.append({
            "title": str(it.get("title") or first["title"]),
            "summary": [str(s) for s in it.get("summary", [])][:3],
            "link": first["link"],
            "pub": first["pub"].astimezone(KST).strftime("%m/%d %H:%M"),
            "count": len(ids),
        })
    return result


def fallback(articles, max_items):
    """요약 실패 시: 최신순 원문 제목·요약문 그대로(가공 없음)"""
    return [{"title": a["title"], "summary": [a["desc"][:120]] if a["desc"] else [],
             "link": a["link"], "pub": a["pub"].astimezone(KST).strftime("%m/%d %H:%M"), "count": 1}
            for a in articles[:max_items]]


def main():
    dry = "--dry-run" in sys.argv
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    now = datetime.datetime.now(KST)
    out = {"generated": now.isoformat(timespec="seconds"), "briefings": []}
    for b in cfg["briefings"]:
        articles, errors, sources = collect(b["keywords"], cfg.get("hours", 26))
        entry = {"id": b["id"], "name": b["name"], "keywords": b["keywords"],
                 "candidates": len(articles), "source": "+".join(sources), "errors": errors, "summarized": False}
        print(f"[{b['id']}] 후보 {len(articles)}건 (경로 {entry['source'] or '-'}) 오류 {len(errors)}건")
        for e in errors:
            print("   ⚠", e)
        if dry:
            for a in articles[:10]:
                print("   -", a["pub"].astimezone(KST).strftime("%m/%d %H:%M"), a["title"])
            continue
        if not articles:
            entry["items"] = []
        elif not API_KEY:
            entry["items"] = fallback(articles, cfg.get("max_items", 7))
            entry["errors"].append("ANTHROPIC_API_KEY 없음 — 요약 없이 원문 제목만 표시")
        else:
            try:
                entry["items"] = summarize(b["name"], articles, cfg.get("max_items", 7))
                entry["summarized"] = True
            except Exception as e:
                entry["items"] = fallback(articles, cfg.get("max_items", 7))
                entry["errors"].append(f"요약 실패 — 원문 제목만 표시: {str(e)[:80]}")
        print(f"   → 브리핑 {len(entry['items'])}건 (요약 {'성공' if entry['summarized'] else '안 됨'})")
        out["briefings"].append(entry)
    if dry:
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    for path in (OUT, os.path.join(ARCHIVE_DIR, now.strftime("%Y-%m-%d") + ".json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[{now:%Y-%m-%d %H:%M}] 저장 완료 → {OUT}")


if __name__ == "__main__":
    main()
