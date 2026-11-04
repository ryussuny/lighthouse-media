"""동산감리교회 유튜브에 '공개'된 영상을 교회 인스타 @garden___church 릴스로 자동으로 함께 올린다.

2026-11-04 오너 지시: "교회 인스타 여기에 유투브 동산교회 올릴때 함께 올려줘 / 자동으로".

- 공개(public)된 영상만 올린다. 비공개로 올린 말씀 쇼츠는 오너가 유튜브에서 공개로 바꾼 뒤 다음 실행 때 올라간다.
- 인스타에 올릴 원본 mp4 는 로컬 파일이 있어야 한다(유튜브에서 내려받지 않는다):
    · 말씀 쇼츠: D:\\동산교회\\유튜브\\output\\업로드기록.json (video_id → file)
    · 그 밖의 영상(성경 인물 찬양 등): config/church-yt-local-files.json  {"<video_id>": {"file": "...", "caption_file": "..."}}
- 게시는 post-video-to-ig.py --account church --key yt-<video_id> (같은 키는 두 번 올리지 않는다).
- 한 영상당 최대 3번 시도. 3번 모두 실패하면 더 시도하지 않고, 폰에서 직접 올리도록
  OneDrive\\인스타 올릴 영상\\ 에 영상과 글을 넣어 둔다(2026-11-04 교회 계정 API 릴스 2207085 대비).
- 토큰 값은 출력하지 않는다.

  py scripts/church-yt-to-ig.py            # 실제 게시
  py scripts/church-yt-to-ig.py --dry-run  # 무엇을 올릴지만 보기
"""
import os, sys, json, shutil, subprocess, datetime

sys.stdout.reconfigure(encoding="utf-8")
HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
CONFIG = os.path.join(REPO, "config")
LEDGER = os.path.join(CONFIG, "ig-video-posts.json")
STATE = os.path.join(CONFIG, "church-yt-ig-state.json")
LOCAL_MAP = os.path.join(CONFIG, "church-yt-local-files.json")
WORD_DIR = r"D:\동산교회\유튜브\output"
WORD_LOG = os.path.join(WORD_DIR, "업로드기록.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_dongsan.json")
CH_TITLE, CH_ID = "동산감리교회", "UC7SpE9IcyLgiq2_qXiTa_UQ"
MANUAL_DIR = os.path.join(HOME, "OneDrive", "인스타 올릴 영상")
WORK = os.path.join(REPO, "output", "church-ig")
MAX_TRIES = 3


def jload(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        return default


def youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN, encoding="utf-8")))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        open(TOKEN, "w", encoding="utf-8").write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    ch = yt.channels().list(part="snippet", mine=True).execute()["items"][0]
    if ch["snippet"]["title"] != CH_TITLE or ch["id"] != CH_ID:
        raise SystemExit(f"  중단: 토큰 채널이 '{ch['snippet']['title']}'({ch['id']}) — 동산감리교회가 아니다")
    return yt


def candidates():
    """video_id → {file, caption_file?}"""
    out = {}
    for date, e in jload(WORD_LOG, {}).items():
        if e.get("video_id") and e.get("file"):
            out[e["video_id"]] = {"file": os.path.join(WORD_DIR, e["file"]), "kind": "word"}
    for vid, e in jload(LOCAL_MAP, {}).items():
        out[vid] = dict(e, kind=e.get("kind", "other"))
    return out


def caption_from_youtube(sn, vid):
    title = sn["title"].replace("#shorts", "").strip()
    desc = sn.get("description", "").replace("#shorts", "").strip()
    tags = "#동산감리교회 #오늘의말씀 #말씀 #성경 #교회 #릴스"
    text = f"{title}\n\n{desc}\n\n▶ 유튜브: https://youtu.be/{vid}\n\n{tags}"
    return text[:2200]


def main():
    dry = "--dry-run" in sys.argv[1:]
    ledger, state = jload(LEDGER, {}), jload(STATE, {})
    cand = {v: e for v, e in candidates().items() if f"yt-{v}" not in ledger}
    if not cand:
        print("  올릴 후보 없음")
        return 0
    yt = youtube()
    items = yt.videos().list(part="snippet,status", id=",".join(list(cand)[:50])).execute().get("items", [])
    os.makedirs(WORK, exist_ok=True)
    rc = 0
    for it in items:
        vid, sn, st = it["id"], it["snippet"], it["status"]
        e = cand[vid]
        if st.get("privacyStatus") != "public":
            print(f"  [{vid}] {st.get('privacyStatus')} — 공개 전이라 건너뜀 ({sn['title'][:40]})")
            continue
        s = state.get(vid, {"tries": 0})
        if s.get("gave_up"):
            continue
        if not os.path.exists(e["file"]):
            print(f"  [{vid}] 로컬 영상 없음: {e['file']} — 건너뜀")
            continue
        cap = e.get("caption_file")
        if not cap:
            cap = os.path.join(WORK, f"{vid}_caption.txt")
            open(cap, "w", encoding="utf-8").write(caption_from_youtube(sn, vid))
        print(f"  [{vid}] 공개됨 → 인스타 게시 {'(dry-run)' if dry else ''}: {sn['title'][:50]}")
        cmd = [sys.executable, "-u", os.path.join(REPO, "scripts", "post-video-to-ig.py"), e["file"],
               "--caption-file", cap, "--account", "church", "--key", f"yt-{vid}"] + (["--dry-run"] if dry else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(r.stdout.rstrip())
        if dry:
            continue
        if r.returncode == 0:
            state.pop(vid, None)
            continue
        rc = 1
        s["tries"] = s.get("tries", 0) + 1
        s["last"] = datetime.datetime.now().isoformat(timespec="seconds")
        if s["tries"] >= MAX_TRIES:
            s["gave_up"] = True
            os.makedirs(MANUAL_DIR, exist_ok=True)
            base = sn["title"][:30].replace("/", " ").replace("\\", " ").replace(":", " ").replace("?", "").replace("|", " ").strip()
            shutil.copy2(e["file"], os.path.join(MANUAL_DIR, f"{base}_{vid}.mp4"))
            shutil.copy2(cap, os.path.join(MANUAL_DIR, f"{base}_{vid}_인스타글.txt"))
            print(f"  [{vid}] {MAX_TRIES}번 실패 — 폰에서 올리도록 {MANUAL_DIR} 에 넣어 둠")
        state[vid] = s
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
