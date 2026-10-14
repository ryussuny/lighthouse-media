"""유튜브 벤치마크 수집 — 같은 분야(위로·번아웃·자존감·직장인 공감) 고조회 영상 데이터
- 최근 1년, 한국 지역, 조회수 순 상위 영상을 키워드별로 모아 data/yt-benchmark.json 저장(읽기 전용)
- Usage: py scripts/yt-benchmark.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
OUT = os.path.join(HOME, "lighthouse-media", "data", "yt-benchmark.json")
QUERIES = ["힘들 때 듣는 말", "번아웃 위로", "직장인 위로", "자존감 높이는 말", "지친 당신에게", "오늘 하루 위로", "마음이 편해지는 말", "인생 조언 명언"]


def secs(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    h, mi, s = (int(x) if x else 0 for x in m.groups()) if m else (0, 0, 0)
    return h * 3600 + mi * 60 + s


def main():
    c = Credentials.from_authorized_user_file(TOKEN)
    if c.expired and c.refresh_token:
        c.refresh(Request())
    yt = build("youtube", "v3", credentials=c)
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen, rows = set(), []
    for q in QUERIES:
        res = yt.search().list(part="id", q=q, type="video", order="viewCount", regionCode="KR",
                               relevanceLanguage="ko", publishedAfter=since, maxResults=15).execute()
        ids = [i["id"]["videoId"] for i in res.get("items", []) if i["id"]["videoId"] not in seen]
        seen.update(ids)
        if not ids:
            continue
        for v in yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute()["items"]:
            st, sn = v["statistics"], v["snippet"]
            rows.append({
                "query": q, "id": v["id"], "url": f"https://youtu.be/{v['id']}",
                "title": sn["title"], "channel": sn["channelTitle"], "published": sn["publishedAt"][:10],
                "seconds": secs(v["contentDetails"]["duration"]),
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0) or 0),
                "comments": int(st.get("commentCount", 0) or 0),
                "tags": sn.get("tags", [])[:15], "description": sn.get("description", "")[:400],
                "thumbnail": sn["thumbnails"].get("high", {}).get("url"),
            })
    rows.sort(key=lambda r: -r["views"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shorts = [r for r in rows if r["seconds"] <= 60]
    longs = [r for r in rows if r["seconds"] > 60]
    print(f"수집 {len(rows)}개 (쇼츠 {len(shorts)} · 롱폼 {len(longs)}) → {OUT}")
    for label, group in (("쇼츠 상위", shorts), ("롱폼 상위", longs)):
        print(f"\n[{label}]")
        for r in group[:10]:
            print(f"  {r['views']:>10,}회 {r['seconds']:>5}초 | {r['channel'][:14]} | {r['title'][:50]}")


if __name__ == "__main__":
    main()
