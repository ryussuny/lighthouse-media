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
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import fb_post  # noqa: E402  (2026-11-04 페이스북 교차게시)

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
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate,pix_fmt",
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
    # 2026-11-04: yuv444p(High 4:4:4) 영상은 컨테이너는 FINISHED 인데 media_publish 가 2207085 로 거절됐다 → 영상도 yuv420p 로
    if v.get("pix_fmt") != "yuv420p":
        fixed = os.path.splitext(path)[0] + "_ig.mp4"
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", path, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                        "-crf", "20", "-preset", "medium", "-r", "30", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                        "-movflags", "+faststart", fixed], check=True)
        print(f"  영상 yuv420p·오디오 48kHz로 변환: {fixed}")
        return fixed
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
    return _publish_container(d["id"], token)


def _publish_container(cid, token):
    """컨테이너가 FINISHED 가 될 때까지 기다렸다가 게시한다(Imgur 길·재개 업로드 길 공통)."""
    print(f"  IG 컨테이너: {cid}")
    for attempt in range(18):
        time.sleep(10)
        st = requests.get(f"https://graph.facebook.com/v21.0/{cid}",
                          params={"fields": "status_code", "access_token": token}, timeout=10).json().get("status_code", "")
        if st == "FINISHED":
            r2 = requests.post(f"https://graph.facebook.com/v21.0/{IG_ID}/media_publish",
                               data={"creation_id": cid, "access_token": token}, timeout=30).json()
            if "id" not in r2:
                print(f"  게시(publish) 거절: {r2.get('error', r2)}")
            return r2.get("id")
        if st == "ERROR":
            print("  IG 처리 오류")
            return None
        print(f"  처리 중... ({(attempt + 1) * 10}s)")
    return None


def upload_ig_reels_resumable(vpath, caption, token):
    """60초 넘는 영상용(2026-11-14 변경안): Imgur 를 거치지 않고 인스타 공식 재개 가능 업로드로 올린다.
    docs: developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing
    (upload_type=resumable → POST rupload.facebook.com/ig-api-upload/<버전>/<컨테이너 id>, 헤더 Authorization: OAuth · offset · file_size)
    주의: 문서에 '페이스북 로그인 for Business 를 구현한 앱 전용'이라고 적혀 있다 — 우리 앱에서 되는지는 실계정 시험 전까지 확인 못 함.
    """
    size = os.path.getsize(vpath)
    r = requests.post(f"https://graph.facebook.com/v21.0/{IG_ID}/media",
                      data={"media_type": "REELS", "upload_type": "resumable", "caption": caption, "access_token": token}, timeout=30)
    d = r.json()
    if "id" not in d:
        print(f"  재개 업로드 세션 실패: {d.get('error', d)}")
        return None
    cid = d["id"]
    with open(vpath, "rb") as f:
        ur = requests.post(f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}",
                           headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
                           data=f, timeout=900)
    ud = ur.json() if ur.content else {}
    if not ud.get("success"):
        print(f"  재개 업로드 실패: HTTP {ur.status_code} {str(ud)[:200]}")
        return None
    print(f"  재개 업로드 OK ({size / 1e6:.1f}MB)")
    return _publish_container(cid, token)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--key", help="중복 방지 키(기본: 영상 파일명)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--account", choices=["lighthouse", "church"], default="lighthouse",
                    help="church = 동산교회 @garden___church (2026-11-04)")
    ap.add_argument("--no-facebook", action="store_true", help="같은 계정의 페이스북 페이지에는 올리지 않음")
    a = ap.parse_args()
    global IG_ID
    tokens = json.load(open(os.path.join(CONFIG, "tokens.json"), encoding="utf-8"))
    if a.account == "church":
        IG_ID, token = tokens["church_ig_id"], tokens["church_page"]
    else:
        token = tokens["instagram"]
    key = a.key or os.path.basename(a.video)
    caption = open(a.caption_file, encoding="utf-8").read().strip()
    if len(caption) > 2200:
        raise SystemExit(f"  중단: 캡션 {len(caption)}자(인스타 한도 2200자)")
    ledger = load_ledger()
    # 2026-11-04 오너 지시: 인스타에 올리는 영상은 같은 계정의 페이스북 페이지에도(교회→교회 페이지, 라이트하우스→라이트하우스 페이지).
    # 인스타 성공 여부와 따로 간다(교회 인스타 릴스가 API 2207085 로 막혀도 페북은 올라가게). 중복은 fb-posts.json 이 막는다.
    if not a.no_facebook:
        try:
            fb_post.post_video(a.account, a.video, caption, f"fb-{a.account}-{key}", dry=a.dry_run)
        except Exception as e:
            print(f"  [페북] 오류(인스타 게시와 무관): {e}")
    if key in ledger:
        print(f"  이미 게시됨({ledger[key]['at']}, media {ledger[key]['media_id']}) — 건너뜀")
        return 0
    print(f"[인스타 릴스 게시] {key}")
    vpath = prepare(a.video)
    print(f"  캡션 첫 줄: {caption.splitlines()[0]}  ({len(caption)}자)")
    if a.dry_run:
        print("  --dry-run: 게시하지 않음")
        return 0
    dur = float(probe(vpath)["format"]["duration"])
    if dur > 60:       # Imgur 는 1분 넘는 영상을 거절한다("Video exceeds maximum duration of 1 minute")
        print(f"  {dur:.1f}초 > 60초: Imgur 대신 인스타 재개 업로드 사용")
        mid = upload_ig_reels_resumable(vpath, caption, token)
    else:
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
