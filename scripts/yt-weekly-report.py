"""Lighthouse Media 유튜브 주간 점검 (읽기 전용 — 아무것도 업로드·수정하지 않음)
- 채널 구독자·누적 조회·영상 수, 최근 7일 업로드 영상별 조회·좋아요·공개 범위, 조회 상위 3개 제목
- data/yt-stats.json 에 주간 스냅샷 누적, 지난 기록과 비교해 한글 요약을 stdout 으로 출력
  (ig-weekly-report.bat 이 logs/yt-weekly.log 로 리다이렉트)
- 토큰은 daily-video.py 와 같은 token_lighthouse.json (값은 출력하지 않는다)
- Usage: py scripts/yt-weekly-report.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
STATS = os.path.join(REPO, "data", "yt-stats.json")
PRIVACY_KO = {"public": "공개", "unlisted": "일부공개", "private": "비공개"}


def youtube():
    c = Credentials.from_authorized_user_file(TOKEN)
    if c.expired and c.refresh_token:
        c.refresh(Request())
        tmp = TOKEN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(c.to_json())
        os.replace(tmp, TOKEN)
    return build("youtube", "v3", credentials=c)


def main():
    yt = youtube()
    ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute().get("items", [])
    if not ch:
        print("채널 조회 실패: 토큰이 가리키는 채널이 없다")
        return 1
    ch = ch[0]
    st = ch["statistics"]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    since = datetime.now(timezone.utc) - timedelta(days=7)

    # 업로드 재생목록(소유자에게는 일부공개·비공개도 보인다)에서 최대 200개를 가져와 영상 정보로 날짜를 거른다
    # (재생목록 항목의 videoPublishedAt 은 일부 영상에 없어 snippet.publishedAt 을 쓴다)
    allv, token = [], None
    while len(allv) < 200:
        res = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token).execute()
        allv += [it["contentDetails"]["videoId"] for it in res.get("items", [])]
        token = res.get("nextPageToken")
        if not token:
            break
    vids = []
    for i in range(0, len(allv), 50):
        vids += yt.videos().list(part="snippet,statistics,status", id=",".join(allv[i:i + 50])).execute().get("items", [])
    rows = []
    for v in vids:
        pub = datetime.strptime(v["snippet"]["publishedAt"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        if pub < since:
            continue
        s = v["statistics"]
        rows.append({"id": v["id"], "date": v["snippet"]["publishedAt"][:10], "title": v["snippet"]["title"],
                     "privacy": v["status"]["privacyStatus"], "views": int(s.get("viewCount", 0)),
                     "likes": int(s.get("likeCount", 0) or 0), "comments": int(s.get("commentCount", 0) or 0)})
    rows.sort(key=lambda r: r["date"])
    best = sorted(((int(v["statistics"].get("viewCount", 0)), v["snippet"]["title"], v["status"]["privacyStatus"]) for v in vids), reverse=True)

    snap = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "subscribers": int(st.get("subscriberCount", 0)),
        "total_views": int(st.get("viewCount", 0)),
        "video_count": int(st.get("videoCount", 0)),
        "uploads_7d": len(rows),
        "public_7d": sum(1 for r in rows if r["privacy"] == "public"),
        "views_7d_videos": sum(r["views"] for r in rows),
        "videos_7d": rows,
        "top": sorted(rows, key=lambda r: -r["views"])[:3],
    }
    snap["top_all_time"] = [{"views": b[0], "title": b[1], "privacy": b[2]} for b in best[:3]]
    hist, can_write = [], True
    if os.path.exists(STATS):
        try:
            hist = json.load(open(STATS, encoding="utf-8"))
            if not isinstance(hist, list):
                raise ValueError("목록이 아님")
        except (OSError, ValueError):   # 깨진 기록은 덮어쓰지 않는다(보고는 계속)
            hist, can_write = [], False
            print(f"  ⚠ {STATS} 를 읽을 수 없어 이번 스냅샷은 저장하지 않는다(기존 파일 보존)")
    past = [h for h in hist if h.get("date") != snap["date"]]   # 같은 날 재실행은 덮어쓴다
    prev = past[-1] if past else None
    if can_write:
        os.makedirs(os.path.dirname(STATS), exist_ok=True)
        tmp = STATS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(past + [snap], f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATS)

    def diff(k):
        return f" ({snap[k] - prev[k]:+d})" if prev and k in prev else ""

    print(f"[{snap['date']}] {ch['snippet']['title']} 유튜브 주간 점검")
    print(f"  구독자 {snap['subscribers']}{diff('subscribers')} · 누적 조회 {snap['total_views']}{diff('total_views')} · 영상 {snap['video_count']}개{diff('video_count')}")
    print(f"  최근 7일 업로드 {snap['uploads_7d']}개 (공개 {snap['public_7d']}개) · 이 영상들의 조회 합계 {snap['views_7d_videos']}")
    for r in rows:
        print(f"   - {r['date']} [{PRIVACY_KO.get(r['privacy'], r['privacy'])}] 조회 {r['views']} · 좋아요 {r['likes']} | {r['title'][:50]}")
    if not rows:
        print("   (최근 7일 업로드 없음)")
    print("  채널 전체 조회 상위 3개")
    for b in best[:3]:
        print(f"   - 조회 {b[0]} [{PRIVACY_KO.get(b[2], b[2])}] | {b[1][:50]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:   # 토큰 만료 등 — 트레이스백 대신 한 줄 사유
        print(f"유튜브 주간 점검 실패: {type(e).__name__}: {e}")
        sys.exit(1)
