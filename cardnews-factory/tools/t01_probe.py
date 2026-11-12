# -*- coding: utf-8 -*-
"""T-01 지표 실측 (읽기 전용).

- 구글 트렌드 KR RSS: 형식·항목 수
- 유튜브 mostPopular KR: 카테고리별 (라이트하우스 OAuth 토큰 읽기 사용, 토큰 파일은 덮어쓰지 않음)
- 원값은 data/raw/<날짜>/ 에 저장한다. 게시·업로드 호출 없음.
"""
import datetime as dt
import json
import os
import sys
import xml.etree.ElementTree as ET

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = dt.datetime.now().astimezone()
RAW = os.path.join(ROOT, "data", "raw", NOW.strftime("%Y-%m-%d"))
os.makedirs(RAW, exist_ok=True)
STAMP = NOW.strftime("%H%M%S")
UA = {"User-Agent": "Mozilla/5.0 (cardnews-factory probe)"}
result = {"measured_at": NOW.isoformat(), "google_trends": [], "youtube": {}}


def save(name, data, binary=False):
    p = os.path.join(RAW, f"{STAMP}_{name}")
    with open(p, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
        f.write(data)
    return p


# 1) Google Trends RSS
for gi, url in enumerate(["https://trends.google.com/trending/rss?geo=KR",
                          "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"]):
    rec = {"url": url}
    try:
        r = requests.get(url, headers=UA, timeout=20)
        rec["status"] = r.status_code
        rec["content_type"] = r.headers.get("content-type")
        rec["raw_path"] = save(f"gtrends_{gi}_" + ("trending_rss" if gi == 0 else "daily_rss_legacy") + ".xml", r.content, binary=True)
        if r.ok:
            root = ET.fromstring(r.content)
            items = root.findall("./channel/item")
            rec["item_count"] = len(items)
            if items:
                rec["item_fields"] = sorted({c.tag for c in items[0]})
                rec["sample"] = [{c.tag.split('}')[-1]: (c.text or "").strip()[:80] for c in it
                                  if c.tag.split('}')[-1] in ("title", "approx_traffic", "pubDate")}
                                 for it in items[:5]]
    except Exception as e:  # noqa: BLE001
        rec["error"] = repr(e)[:300]
    result["google_trends"].append(rec)

# 2) YouTube mostPopular KR
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    home = os.path.expanduser("~")
    tp = os.path.join(home, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
    creds = Credentials.from_authorized_user_file(tp)
    result["youtube"]["token_scopes"] = list(creds.scopes or [])
    if not creds.valid:
        creds.refresh(Request())  # 메모리에서만 갱신, 파일에 쓰지 않음
    H = {"Authorization": f"Bearer {creds.token}"}
    base = "https://www.googleapis.com/youtube/v3"
    r = requests.get(f"{base}/videoCategories", params={"part": "snippet", "regionCode": "KR", "hl": "ko"}, headers=H, timeout=20)
    save("yt_categories_KR.json", r.text)
    cats = []
    if r.ok:
        cats = [(c["id"], c["snippet"]["title"], c["snippet"].get("assignable")) for c in r.json().get("items", [])]
    result["youtube"]["categories_status"] = r.status_code
    result["youtube"]["categories"] = cats
    per = {}
    for cid in ["0", "22", "24", "25", "26", "27", "28"]:
        params = {"part": "snippet,statistics", "chart": "mostPopular", "regionCode": "KR", "maxResults": 50}
        if cid != "0":
            params["videoCategoryId"] = cid
        rr = requests.get(f"{base}/videos", params=params, headers=H, timeout=20)
        save(f"yt_mostPopular_KR_cat{cid}.json", rr.text)
        ent = {"status": rr.status_code}
        if rr.ok:
            j = rr.json()
            items = j.get("items", [])
            ent["count"] = len(items)
            ent["totalResults"] = j.get("pageInfo", {}).get("totalResults")
            ent["has_nextPage"] = bool(j.get("nextPageToken"))
            ent["sample"] = [{"title": i["snippet"]["title"][:60], "views": i.get("statistics", {}).get("viewCount"),
                              "publishedAt": i["snippet"]["publishedAt"]} for i in items[:3]]
        else:
            ent["error"] = rr.text[:300]
        per[cid] = ent
    result["youtube"]["mostPopular"] = per
except Exception as e:  # noqa: BLE001
    result["youtube"]["error"] = repr(e)[:300]

out = save("t01_summary.json", json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
print("SUMMARY:", out, file=sys.stderr)
