# -*- coding: utf-8 -*-
"""T-01 확장: 인스타 해시태그 상위 게시물 반응 실측 (읽기 전용, 공식 Graph API).

- 라이트하우스 IG(17841425580883266) 토큰으로 ig_hashtag_search → top_media 조회만 한다.
- 게시·댓글·좋아요 등 쓰기 호출 없음. 교회 계정 사용 안 함.
- 제약: 계정당 7일에 고유 해시태그 30개 (Meta 문서). 이번 실행은 10개만 쓴다.
- 사진 게시물의 조회 수는 API가 주지 않으므로 like_count·comments_count 를 반응 지표로 쓴다.
"""
import datetime as dt
import json
import os
import statistics as st

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LM = os.path.dirname(ROOT)
NOW = dt.datetime.now().astimezone()
RAW = os.path.join(ROOT, "data", "raw", NOW.strftime("%Y-%m-%d"))
os.makedirs(RAW, exist_ok=True)
STAMP = NOW.strftime("%H%M%S")
IG_ID = "17841425580883266"
TOKEN = json.load(open(os.path.join(LM, "config", "tokens.json"), encoding="utf-8"))["instagram"]
G = "https://graph.facebook.com/v21.0"
TAGS = ["카드뉴스", "정부지원금", "생활꿀팁", "재테크", "건강정보",
        "육아정보", "자기계발", "여행정보", "부동산정보", "시니어"]
FIELDS = "id,media_type,like_count,comments_count,timestamp,caption"

summary = {"measured_at": NOW.isoformat(), "account": "lighthouse(IG_ID only)", "tags": {}}
for tag in TAGS:
    ent = {}
    try:
        r = requests.get(f"{G}/ig_hashtag_search", params={"user_id": IG_ID, "q": tag, "access_token": TOKEN}, timeout=20)
        if not r.ok:
            ent["error"] = r.text[:300]
            summary["tags"][tag] = ent
            continue
        hid = r.json()["data"][0]["id"]
        rr = requests.get(f"{G}/{hid}/top_media", params={"user_id": IG_ID, "fields": FIELDS, "limit": 25, "access_token": TOKEN}, timeout=30)
        with open(os.path.join(RAW, f"{STAMP}_ig_top_{tag}.json"), "w", encoding="utf-8") as f:
            f.write(rr.text)
        if not rr.ok:
            ent["error"] = rr.text[:300]
        else:
            items = rr.json().get("data", [])
            likes = [i.get("like_count") for i in items if isinstance(i.get("like_count"), int)]
            by_type = {}
            for i in items:
                t = i.get("media_type")
                by_type.setdefault(t, []).append(i.get("like_count") or 0)
            ent = {
                "hashtag_id": hid, "n": len(items), "n_like_visible": len(likes),
                "like_median": st.median(likes) if likes else None,
                "like_max": max(likes) if likes else None,
                "comments_median": st.median([i.get("comments_count", 0) for i in items]) if items else None,
                "by_media_type": {k: {"n": len(v), "like_median": st.median(v)} for k, v in by_type.items()},
                "oldest": min((i["timestamp"] for i in items), default=None),
                "newest": max((i["timestamp"] for i in items), default=None),
            }
    except Exception as e:  # noqa: BLE001
        ent["error"] = repr(e)[:300]
    summary["tags"][tag] = ent

p = os.path.join(RAW, f"{STAMP}_ig_hashtag_summary.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(json.dumps(summary, ensure_ascii=False, indent=1))
print("SUMMARY:", p)
