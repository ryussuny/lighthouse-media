"""교회 쪽 숫자 재기 (읽기 전용 — 아무것도 게시·업로드·수정하지 않는다)
- 동산감리교회 유튜브: 구독자·누적 조회·영상 수, 최근 7일 업로드 영상별 조회·좋아요·공개 범위 (token_dongsan.json)
- 매일 한 걸음 유튜브(새 채널): 전용 토큰이 없어 동산 토큰으로 '채널 ID 공개 통계'만 읽는다(구독자·영상 수·누적 조회, 비공개 영상은 안 보임)
- 교회 인스타 @garden___church: 팔로워·최근 7일 게시물 조회/도달/저장/공유 (config/tokens.json 의 church_page 토큰, Graph API GET)
- 결과는 data/church-stats.json 에 날짜별로 누적하고 한글 요약을 stdout 으로 낸다.
- 안전장치: 실행 전 channels().list(mine=True) 로 채널 이름·ID 를 확인해 동산감리교회가 아니면 아무것도 읽지 않고 멈춘다.
  토큰은 갱신이 필요하면 메모리에서만 갱신하고 파일에 다시 쓰지 않는다. 쓰기 API 호출 없음.
- 작업 스케줄러에는 등록하지 않았다(수동 실행용). 주간 배치에 넣는 변경안은 40_수리_결과.md 참고.
- Usage: py scripts/church-stats-report.py [--dry]   (--dry: 파일에 저장하지 않고 출력만)
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_dongsan.json")
STATS = os.path.join(REPO, "data", "church-stats.json")
CHURCH_YT_ID = "UC7SpE9IcyLgiq2_qXiTa_UQ"
CHURCH_YT_NAME = "동산감리교회"
KIDS_YT_ID = "UCRm2McNjUl5NtXRP46P-68A"      # 매일 한 걸음(2026-11-13 신설)
G = "https://graph.facebook.com/v21.0/"
PRIVACY_KO = {"public": "공개", "unlisted": "일부공개", "private": "비공개"}


def youtube():
    c = Credentials.from_authorized_user_file(TOKEN)
    if c.expired and c.refresh_token:
        c.refresh(Request())          # 메모리에서만 갱신(파일 쓰기 없음)
    return build("youtube", "v3", credentials=c)


def num(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def church_youtube(yt):
    """returns (dict, error). 채널 확인 실패면 dict 는 None."""
    ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute().get("items", [])
    if not ch:
        return None, "토큰이 가리키는 채널이 없다"
    ch = ch[0]
    title, cid = ch["snippet"]["title"], ch["id"]
    if cid != CHURCH_YT_ID or title != CHURCH_YT_NAME:
        return None, f"채널 불일치: 토큰 채널은 '{title}'({cid}) — 동산감리교회가 아니라 읽지 않고 멈춤"
    st = ch["statistics"]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    since = datetime.now(timezone.utc) - timedelta(days=7)
    ids, token = [], None
    while len(ids) < 200:
        res = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        token = res.get("nextPageToken")
        if not token:
            break
    vids = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            vids.append({"id": v["id"], "date": v["snippet"]["publishedAt"][:10],
                         "title": v["snippet"]["title"], "privacy": v["status"]["privacyStatus"],
                         "views": num(v["statistics"].get("viewCount")) or 0,
                         "likes": num(v["statistics"].get("likeCount")) or 0,
                         "comments": num(v["statistics"].get("commentCount")) or 0})
    recent = [v for v in vids if datetime.strptime(v["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc) >= since - timedelta(days=1)]
    pub = [v for v in vids if v["privacy"] == "public"]
    return {
        "channel": title, "channel_id": cid,
        "subscribers": num(st.get("subscriberCount")), "subscribers_hidden": bool(st.get("hiddenSubscriberCount")),
        "total_views": num(st.get("viewCount")), "video_count": num(st.get("videoCount")),
        "videos_seen": len(vids), "public_videos": len(pub),
        "uploads_7d": len(recent), "views_7d_videos": sum(v["views"] for v in recent),
        "recent": sorted(recent, key=lambda v: v["date"], reverse=True)[:12],
        "top": sorted(pub, key=lambda v: -v["views"])[:3],
    }, None


def kids_youtube_public(yt):
    """새 채널은 전용 토큰이 없다. 채널 ID 로 읽을 수 있는 공개 통계만."""
    try:
        r = yt.channels().list(part="snippet,statistics", id=KIDS_YT_ID).execute().get("items", [])
    except Exception as e:                      # noqa: BLE001 - 읽기 실패는 '확인 못 함'으로 기록
        return None, f"{type(e).__name__}: {e}"
    if not r:
        return None, "채널 ID 로 조회되지 않음(확인 못 함)"
    st = r[0]["statistics"]
    return {"channel": r[0]["snippet"]["title"], "channel_id": KIDS_YT_ID,
            "subscribers": num(st.get("subscriberCount")), "subscribers_hidden": bool(st.get("hiddenSubscriberCount")),
            "total_views": num(st.get("viewCount")), "video_count_public": num(st.get("videoCount")),
            "note": "공개 통계만(비공개 영상은 영상 수·조회에 안 잡힘). 전용 토큰이 없어 영상별 조회는 못 읽음"}, None


def church_instagram():
    tk = json.load(open(os.path.join(REPO, "config", "tokens.json"), encoding="utf-8"))
    token, ig_id = tk["church_page"], tk["church_ig_id"]

    def get(path, **p):
        p["access_token"] = token
        return requests.get(G + path, params=p, timeout=30).json()

    acct = get(ig_id, fields="username,followers_count,follows_count,media_count")
    if "error" in acct:
        return None, "계정 조회 실패: " + str(acct["error"].get("message"))
    if acct.get("username") != "garden___church":
        return None, f"계정 불일치: {acct.get('username')} — 읽지 않고 멈춤"
    since = datetime.now(timezone.utc) - timedelta(days=7)
    media = get(ig_id + "/media", fields="id,caption,media_product_type,timestamp,like_count,comments_count", limit=50).get("data", [])
    week = [m for m in media if datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc) >= since]
    rows, insight_fail = [], 0
    for m in week:
        ins = get(m["id"] + "/insights", metric="reach,views,saved,shares")
        if "error" in ins:
            ins = get(m["id"] + "/insights", metric="reach,saved")
        if "error" in ins:
            insight_fail += 1
        v = {d["name"]: d["values"][0]["value"] for d in ins.get("data", [])}
        rows.append({"type": m.get("media_product_type"), "date": m["timestamp"][:10],
                     "views": v.get("views"), "reach": v.get("reach"), "saved": v.get("saved"), "shares": v.get("shares"),
                     "likes": m.get("like_count", 0), "comments": m.get("comments_count", 0),
                     "hook": (m.get("caption") or "").split("\n")[0][:40]})
    return {"username": acct["username"], "followers": acct.get("followers_count"),
            "media_count": acct.get("media_count"), "posts_7d": len(rows),
            "likes_7d": sum(r["likes"] for r in rows), "comments_7d": sum(r["comments"] for r in rows),
            "insight_failed": insight_fail, "recent": rows[:12]}, None


def main():
    dry = "--dry" in sys.argv
    snap = {"date": datetime.now().strftime("%Y-%m-%d"), "at": datetime.now().isoformat(timespec="seconds"), "errors": {}}
    try:
        yt = youtube()
    except Exception as e:                      # noqa: BLE001
        yt = None
        snap["errors"]["youtube_token"] = f"{type(e).__name__}: {e}"
    if yt:
        try:
            snap["church_youtube"], err = church_youtube(yt)
            if err:
                snap["errors"]["church_youtube"] = err
        except Exception as e:                  # noqa: BLE001
            snap["errors"]["church_youtube"] = f"{type(e).__name__}: {e}"
        snap["kids_youtube"], err = kids_youtube_public(yt)
        if err:
            snap["errors"]["kids_youtube"] = err
    try:
        snap["church_instagram"], err = church_instagram()
        if err:
            snap["errors"]["church_instagram"] = err
    except Exception as e:                      # noqa: BLE001
        snap["errors"]["church_instagram"] = f"{type(e).__name__}: {e}"

    # ---- 한글 요약
    print(f"[{snap['date']}] 교회 쪽 숫자 (읽기 전용)")
    c = snap.get("church_youtube")
    if c:
        print(f"  동산감리교회 유튜브: 구독자 {c['subscribers']} · 누적 조회 {c['total_views']} · 영상 {c['video_count']}개 "
              f"(공개 {c['public_videos']}) · 최근 7일 업로드 {c['uploads_7d']}개, 그 조회 합계 {c['views_7d_videos']}")
        for v in c["top"]:
            print(f"   - 상위 조회 {v['views']} [{PRIVACY_KO.get(v['privacy'], v['privacy'])}] | {v['title'][:50]}")
    k = snap.get("kids_youtube")
    if k:
        print(f"  매일 한 걸음 유튜브(공개 통계만): 구독자 {k['subscribers']} · 공개 영상 {k['video_count_public']}개 · 누적 조회 {k['total_views']}")
    i = snap.get("church_instagram")
    if i:
        print(f"  교회 인스타 @{i['username']}: 팔로워 {i['followers']} · 게시물 {i['media_count']}개 · 최근 7일 게시 {i['posts_7d']}개 "
              f"(좋아요 합 {i['likes_7d']}, 댓글 합 {i['comments_7d']}, 인사이트 읽기 실패 {i['insight_failed']}건)")
    for k2, v in snap["errors"].items():
        print(f"  확인 못 함 — {k2}: {v}")

    if dry:
        print("  (--dry: 파일에 저장하지 않음)")
        return 0
    hist = []
    if os.path.exists(STATS):
        try:
            hist = json.load(open(STATS, encoding="utf-8"))
        except json.JSONDecodeError:
            hist = []                           # 깨진 기록은 덮어쓰지 않고 새 파일 옆에 둔다
            os.replace(STATS, STATS + ".broken")
    hist.append(snap)
    os.makedirs(os.path.dirname(STATS), exist_ok=True)
    tmp = STATS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATS)
    print(f"  저장: {STATS}")
    return 0 if not snap["errors"] else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                      # noqa: BLE001
        print(f"교회 숫자 재기 실패: {type(e).__name__}: {e}")
        sys.exit(1)
