"""@lighthouse_media77 주간 성과 점검 (읽기 전용 — 아무것도 게시하지 않음)
- 팔로워·최근 7일 게시물의 조회/도달/저장/공유를 모아 data/ig-stats.json 에 누적
- 지난 기록과 비교해 logs/ig-weekly.log 에 한글 요약
- Usage: py scripts/ig-weekly-report.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
TOKEN = json.load(open(os.path.join(REPO, "config", "tokens.json"), encoding='utf-8'))['instagram']
IG_ID = "17841425580883266"
G = "https://graph.facebook.com/v21.0/"
STATS = os.path.join(REPO, "data", "ig-stats.json")


def get(path, **p):
    p["access_token"] = TOKEN
    r = requests.get(G + path, params=p, timeout=30)
    return r.json()


def main():
    acct = get(IG_ID, fields="followers_count,follows_count,media_count")
    if "error" in acct:
        print("계정 조회 실패:", acct["error"].get("message"))
        return
    since = datetime.now(timezone.utc) - timedelta(days=7)
    media = get(IG_ID + "/media", fields="id,caption,media_product_type,timestamp,like_count,comments_count", limit=50).get("data", [])
    week = [m for m in media if datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) >= since]
    rows = []
    for m in week:
        ins = get(m["id"] + "/insights", metric="reach,views,saved,shares")
        if "error" in ins:
            ins = get(m["id"] + "/insights", metric="reach,saved")
        v = {d["name"]: d["values"][0]["value"] for d in ins.get("data", [])}
        rows.append({"type": m.get("media_product_type"), "date": m["timestamp"][:10],
                     "views": v.get("views", 0), "reach": v.get("reach", 0), "saved": v.get("saved", 0),
                     "shares": v.get("shares", 0), "likes": m.get("like_count", 0),
                     "hook": (m.get("caption") or "").split("\n")[0][:40]})
    reels = [r for r in rows if r["type"] == "REELS"]
    snap = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "followers": acct.get("followers_count", 0),
        "posts_7d": len(rows), "reels_7d": len(reels),
        "reel_views_avg": round(sum(r["views"] for r in reels) / len(reels)) if reels else 0,
        "reel_views_max": max((r["views"] for r in reels), default=0),
        "saves_7d": sum(r["saved"] for r in rows), "shares_7d": sum(r["shares"] for r in rows),
        "top": sorted(rows, key=lambda r: -r["views"])[:3],
    }
    hist = []
    if os.path.exists(STATS):
        try: hist = json.load(open(STATS, encoding='utf-8'))
        except json.JSONDecodeError: hist = []
    prev = hist[-1] if hist else None
    hist.append(snap)
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    json.dump(hist, open(STATS, "w", encoding='utf-8'), ensure_ascii=False, indent=1)

    def diff(k):
        return f" ({snap[k] - prev[k]:+d})" if prev and k in prev else ""
    print(f"[{snap['date']}] @lighthouse_media77 주간 점검")
    print(f"  팔로워 {snap['followers']}{diff('followers')}")
    print(f"  최근 7일 게시 {snap['posts_7d']}개 (릴스 {snap['reels_7d']}개)")
    print(f"  릴스 평균 조회 {snap['reel_views_avg']}{diff('reel_views_avg')} · 최고 {snap['reel_views_max']}")
    print(f"  저장 {snap['saves_7d']} · 공유 {snap['shares_7d']}")
    for t in snap["top"]:
        print(f"   - {t['date']} {t['type']} 조회 {t['views']} | {t['hook']}")


if __name__ == "__main__":
    main()
