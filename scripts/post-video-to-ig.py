"""완성된 세로 영상(유튜브에 올린 애니메이션 등)을 @lighthouse_media77 인스타 릴스로 게시한다.

2026-11-04 오너 지시: "유튜브에 올린 '괜찮아, 오늘도' 같은 애니메이션 영상이 만들어지면 인스타에도 올려줘".

사용:
  py scripts/post-video-to-ig.py <영상.mp4> --caption-file <캡션.txt> [--key <중복방지 키>] [--dry-run]

- 인스타 규격에 맞춘다: 오디오 48kHz 초과면 오디오만 AAC 48kHz로 다시 인코딩(화면은 복사).
- 업로드 방식은 daily-ig-reels.py upload_ig_reels 와 같다(Imgur multipart → 변환 완료 대기 → REELS 컨테이너 → 게시).
- 같은 키(기본: 파일명)로 두 번 게시하지 않는다: config/ig-video-posts.json 에 기록.
- 토큰 값은 출력하지 않는다.
"""
import os, sys, json, time, argparse, subprocess, datetime
import requests

sys.stdout.reconfigure(encoding="utf-8")
HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
CONFIG = os.path.join(REPO, "config")
LEDGER = os.path.join(CONFIG, "ig-video-posts.json")
IG_ID = "17841425580883266"          # @lighthouse_media77
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG.endswith(".exe") else "ffprobe"


def probe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def prepare(path):
    """인스타 릴스 규격 확인. 오디오가 48kHz 초과면 오디오만 다시 인코딩한 사본을 돌려준다."""
    info = probe(path)
    dur = float(info["format"]["duration"])
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    print(f"  원본: {v['width']}x{v['height']} {v['codec_name']} · {dur:.1f}초 · 오디오 {a and a.get('sample_rate')}Hz")
    if not (3 <= dur <= 900):
        raise SystemExit(f"  중단: 길이 {dur:.1f}초는 릴스 범위(3~900초) 밖")
    if a and int(a.get("sample_rate", 0)) > 48000:
        fixed = os.path.splitext(path)[0] + "_ig.mp4"
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", path, "-c:v", "copy", "-c:a", "aac", "-ar", "48000",
                        "-b:a", "192k", "-movflags", "+faststart", fixed], check=True)
        print(f"  오디오 48kHz로 변환: {fixed}")
        return fixed
    return path


def load_ledger():
    try:
        return json.load(open(LEDGER, encoding="utf-8"))
    except FileNotFoundError:
        return {}


def upload_ig_reels(vpath, caption, token):
    with open(vpath, "rb") as f:
        ir = requests.post("https://api.imgur.com/3/upload", headers={"Authorization": f"Client-ID {IMGUR_ID}"},
                           files={"video": (os.path.basename(vpath), f, "video/mp4")}, data={"type": "file"}, timeout=300)
    data = ir.json().get("data", {})
    vid_url = data.get("link")
    if not vid_url:
        print(f"  Imgur 업로드 실패: {str(data)[:200]}")
        return None
    print(f"  Imgur OK: {vid_url}")
    t0 = time.time()
    while time.time() - t0 < 240:
        try:
            info = requests.get(f"https://api.imgur.com/3/image/{data.get('id')}",
                                headers={"Authorization": f"Client-ID {IMGUR_ID}"}, timeout=30).json().get("data", {})
            st = (info.get("processing") or {}).get("status")
            if st == "completed" or (st is None and info.get("mp4_size")):
                print(f"  Imgur 영상 변환 완료({time.time() - t0:.0f}초)")
                break
        except Exception:
            pass
        time.sleep(10)
    r = requests.post(f"https://graph.facebook.com/v21.0/{IG_ID}/media",
                      data={"video_url": vid_url, "media_type": "REELS", "caption": caption, "access_token": token}, timeout=30)
    d = r.json()
    if "id" not in d:
        print(f"  IG 컨테이너 실패: {d.get('error', d)}")
        return None
    cid = d["id"]
    print(f"  IG 컨테이너: {cid}")
    for attempt in range(18):
        time.sleep(10)
        st = requests.get(f"https://graph.facebook.com/v21.0/{cid}",
                          params={"fields": "status_code", "access_token": token}, timeout=10).json().get("status_code", "")
        if st == "FINISHED":
            r2 = requests.post(f"https://graph.facebook.com/v21.0/{IG_ID}/media_publish",
                               data={"creation_id": cid, "access_token": token}, timeout=30).json()
            return r2.get("id")
        if st == "ERROR":
            print("  IG 처리 오류")
            return None
        print(f"  처리 중... ({(attempt + 1) * 10}s)")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--key", help="중복 방지 키(기본: 영상 파일명)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    key = a.key or os.path.basename(a.video)
    caption = open(a.caption_file, encoding="utf-8").read().strip()
    if len(caption) > 2200:
        raise SystemExit(f"  중단: 캡션 {len(caption)}자(인스타 한도 2200자)")
    ledger = load_ledger()
    if key in ledger:
        print(f"  이미 게시됨({ledger[key]['at']}, media {ledger[key]['media_id']}) — 건너뜀")
        return 0
    print(f"[인스타 릴스 게시] {key}")
    vpath = prepare(a.video)
    print(f"  캡션 첫 줄: {caption.splitlines()[0]}  ({len(caption)}자)")
    if a.dry_run:
        print("  --dry-run: 게시하지 않음")
        return 0
    token = json.load(open(os.path.join(CONFIG, "tokens.json"), encoding="utf-8"))["instagram"]
    mid = upload_ig_reels(vpath, caption, token)
    if not mid:
        print("  게시 실패")
        return 1
    link = requests.get(f"https://graph.facebook.com/v21.0/{mid}",
                        params={"fields": "permalink", "access_token": token}, timeout=10).json().get("permalink", "")
    ledger[key] = {"media_id": mid, "permalink": link, "video": a.video,
                   "at": datetime.datetime.now().isoformat(timespec="seconds")}
    json.dump(ledger, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  IG Reels: OK ({mid}) {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
