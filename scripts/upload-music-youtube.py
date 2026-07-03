"""Lighthouse Worship 음원 → YouTube 자동 업로드
사용법:
  py scripts/upload-music-youtube.py            # WAV→MP4 변환 + 업로드 (신규만)
  py scripts/upload-music-youtube.py --dry-run  # 실제 업로드 없이 대상만 확인

흐름: lighthouse-biz/music/pilot-ep01/audio/*.wav
  → (mp4 없으면) 커버 이미지 + 오디오로 mp4 생성 (ffmpeg)
  → YouTube 업로드 (공개)
  → config/jarvis-board.json 트랙 상태 갱신 (관제탑 반영은 git push 후)
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, subprocess, re, argparse

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HOME = os.path.expanduser("~")
MUSIC = os.path.join(HOME, "lighthouse-biz", "music", "pilot-ep01")
AUDIO = os.path.join(MUSIC, "audio")
COVER = os.path.join(MUSIC, "cover", "cover.png")
BOARD = os.path.join(HOME, "lighthouse-media", "config", "jarvis-board.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")

# 파일명 → 보드 트랙 매칭 (슬러그 또는 곡 제목 어느 쪽으로 저장해도 인식)
SLUGS = {
    "01-be-still": 1, "02-anchor-for-my-soul": 2, "03-rest-in-you": 3,
    "04-quiet-waters": 4, "05-morning-light": 5, "06-carry-me-home": 6,
    "07-shim": 7, "08-janjanhan-mulga": 8, "08-janjahan-mulga": 8,
    "09-dasi-ireona": 9, "10-pyeongon": 10,
    "quiet-before-you": 0,
}
CANON = {1:"01-be-still", 2:"02-anchor-for-my-soul", 3:"03-rest-in-you",
         4:"04-quiet-waters", 5:"05-morning-light", 6:"06-carry-me-home",
         7:"07-shim", 8:"08-janjanhan-mulga", 9:"09-dasi-ireona",
         10:"10-pyeongon", 0:"quiet-before-you"}
TITLES = {  # 정규화된 제목 → 트랙 번호
    "bestill": 1, "anchorformysoul": 2, "restinyou": 3, "quietwaters": 4,
    "morninglight": 5, "carrymehome": 6, "쉼": 7, "잔잔한물가": 8,
    "다시일어나": 9, "평온": 10, "quietbeforeyou": 0,
}

def norm(s):
    """소문자화 + 공백/구두점 제거 (한글 유지)"""
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())

def match_no(base):
    b = base.replace("-youtube", "")
    if b in SLUGS: return SLUGS[b]
    n = norm(b)
    if n in TITLES: return TITLES[n]
    # 부분 일치 (Suno가 "Be Still (v2)" 같은 접미사를 붙이는 경우)
    for k, v in TITLES.items():
        if n.startswith(k) or k in n: return v
    return None

def load_board():
    with open(BOARD, encoding="utf-8") as f: return json.load(f)

def save_board(b):
    with open(BOARD, "w", encoding="utf-8") as f: json.dump(b, f, ensure_ascii=False, indent=2)

def track_of(board, no):
    for t in board["music"]["tracks"]:
        if t["no"] == no: return t
    return None

def make_mp4(wav, mp4):
    """커버 정지화면 + 오디오 → 1080p mp4"""
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", COVER, "-i", wav,
           "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "256k",
           "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
           "-shortest", mp4]
    subprocess.run(cmd, check=True, capture_output=True)

def yt_client():
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def lyrics_snippet(no):
    """가사 파일에서 설명용 일부 추출"""
    import glob
    for p in glob.glob(os.path.join(MUSIC, "lyrics", f"{no:02d}-*.md")):
        txt = open(p, encoding="utf-8").read()
        body = re.sub(r"^#.*$", "", txt, flags=re.M).strip()
        return body[:400]
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    board = load_board()
    yt = None
    done, skipped = 0, 0

    for fname in sorted(os.listdir(AUDIO)):
        base, ext = os.path.splitext(fname)
        if ext.lower() not in (".wav", ".mp3", ".m4a"): continue
        no = match_no(base)
        if no is None:
            print(f"⚠️  매칭 안 됨 (건너뜀): {fname}"); continue
        t = track_of(board, no)
        if t is None: continue

        t["suno"] = True; t["wav"] = True

        # 1) MP4 준비 (표준 슬러그 이름으로 생성)
        mp4 = os.path.join(AUDIO, f"{CANON[no]}-youtube.mp4")
        if not os.path.exists(mp4):
            print(f"🎬 MP4 변환: {t['title']}")
            if not args.dry_run: make_mp4(os.path.join(AUDIO, fname), mp4)
        t["mp4"] = True

        # 2) 업로드 (이미 업로드된 트랙은 건너뜀)
        if t.get("youtube"):
            skipped += 1; continue
        title = f"{t['title']} — Lighthouse Worship (Official Audio)"
        desc = (f"{t['title']} · EP01 「Rest / 안식」\n"
                f"Lighthouse Worship — 쉼이 필요한 당신을 위한 묵상 음악\n\n"
                f"{lyrics_snippet(no) if no else ''}\n\n"
                f"#worship #ccm #묵상음악 #찬양 #LighthouseWorship")
        print(f"📤 업로드: {title}")
        if args.dry_run:
            done += 1; continue
        if yt is None: yt = yt_client()
        body = {"snippet": {"title": title, "description": desc,
                            "tags": ["worship","ccm","찬양","묵상음악","기도음악","lighthouse worship"],
                            "categoryId": "10", "defaultLanguage": "ko"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        media = MediaFileUpload(mp4, mimetype="video/mp4", resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None: _, resp = req.next_chunk()
        t["youtube"] = resp["id"]
        print(f"   ✅ https://youtu.be/{resp['id']}")
        done += 1
        save_board(board)  # 곡마다 저장 (중단 대비)

    save_board(board)
    print(f"\n완료: 업로드 {done}곡 · 기존 {skipped}곡 건너뜀")
    print("관제탑 반영: lighthouse-media에서 git add config/jarvis-board.json && git commit && git push")

if __name__ == "__main__":
    main()
