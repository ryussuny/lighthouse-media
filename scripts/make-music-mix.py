"""EP01 장시간 믹스 영상 제작 + 업로드
1) 전곡 연속재생 (11곡, ~40분) — 챕터 타임스탬프 포함
2) 2시간 반복 버전 (수면/기도/공부 BGM)
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os, subprocess, tempfile

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
PLAYLIST_URL = "https://youtube.com/playlist?list=PLTt-NE3XVRRs"
PLAYLIST_ID = "PLTt-NE3XVRRs"

CANON = {1:"01-be-still", 2:"02-anchor-for-my-soul", 3:"03-rest-in-you",
         4:"04-quiet-waters", 5:"05-morning-light", 6:"06-carry-me-home",
         7:"07-shim", 8:"08-janjanhan-mulga", 9:"09-dasi-ireona",
         10:"10-pyeongon", 0:"quiet-before-you"}

def wav_for(no):
    """보드 순서대로 원본 오디오 파일 찾기 (파일명 자유형 지원)"""
    import re as _re
    cands = []
    for f in os.listdir(AUDIO):
        b, ext = os.path.splitext(f)
        if ext.lower() not in (".wav", ".mp3"): continue
        m = _re.match(r"^\s*(\d{1,2})[.\s\-_]", b)
        if m and int(m.group(1)) == no: return os.path.join(AUDIO, f)
        cands.append((b, f))
    slug = CANON[no].split("-", 1)[1].replace("-", "")
    for b, f in cands:
        nb = _re.sub(r"[^0-9a-z가-힣]", "", b.lower())
        if slug in nb or nb in slug: return os.path.join(AUDIO, f)
    return None

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(out.stdout.strip())

def hms(t):
    h, m, s = int(t//3600), int(t%3600//60), int(t%60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def main():
    board = json.load(open(BOARD, encoding="utf-8"))
    order = [t for t in sorted(board["music"]["tracks"], key=lambda t: (t["no"]==0, t["no"]))]

    files, chapters, cum = [], [], 0.0
    for t in order:
        p = wav_for(t["no"])
        if not p: print(f"⚠️ 파일 없음: {t['title']}"); continue
        files.append(p)
        chapters.append((cum, t["title"]))
        cum += dur(p)
    total = cum
    print(f"곡 {len(files)}개, 총 {hms(total)}")

    # 1) 오디오 이어붙이기
    mix_wav = os.path.join(AUDIO, "_mix-ep01.wav")
    lst = os.path.join(AUDIO, "_mix-list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in files: f.write(f"file '{p.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-ar", "44100", "-ac", "2", mix_wav], check=True, capture_output=True)

    # 2) 40분 전곡 영상 (저프레임 → 인코딩/용량 절약)
    mix_mp4 = os.path.join(AUDIO, "_mix-ep01.mp4")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "2", "-i", COVER, "-i", mix_wav,
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "2", "-c:a", "aac", "-b:a", "256k",
                    "-pix_fmt", "yuv420p", "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                    "-shortest", mix_mp4], check=True, capture_output=True)
    print("믹스 영상 생성 완료")

    # 3) 2시간 반복 버전
    loops = max(2, int(7200 // total) + 1)
    mix2h = os.path.join(AUDIO, "_mix-ep01-2h.mp4")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "2", "-i", COVER,
                    "-stream_loop", str(loops - 1), "-i", mix_wav,
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "2", "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                    "-t", "7200", "-shortest", mix2h], check=True, capture_output=True)
    print("2시간 버전 생성 완료")

    # 4) 업로드
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)

    chap_txt = "\n".join(f"{hms(s)} {title}" for s, title in chapters)
    common = (f"\n\n🎧 곡별 영상: {PLAYLIST_URL}\n"
              f"🔔 구독하시면 새로운 묵상 워십을 가장 먼저 들으실 수 있습니다.\n\n"
              f"* 본 음원은 AI 작곡 도구의 도움을 받아 제작되었습니다.\n\n"
              f"#worship #ccm #찬양연속듣기 #묵상음악 #수면음악 #기도음악 #새벽기도 #공부음악 #LighthouseWorship")

    uploads = [
        (mix_mp4,
         f"잔잔한 워십 전곡 연속듣기 ({hms(total)}) — EP01 「Rest / 안식」 | Calm Worship Mix for Sleep & Prayer",
         f"쉼이 필요한 당신을 위한 묵상 워십 앨범 전곡 연속재생.\nCalm worship for sleep, prayer, and quiet moments.\n\n[Tracklist]\n{chap_txt}" + common),
        (mix2h,
         "2시간 잔잔한 CCM 연속재생 — 수면·기도·묵상 BGM | 2 Hours Calm Worship Music",
         f"잠들기 전, 기도할 때, 조용히 집중하고 싶을 때 틀어두세요.\n2 hours of calm worship — EP01 「Rest / 안식」 on repeat.\n\n[Tracklist 1회차]\n{chap_txt}" + common),
    ]
    for path, title, desc in uploads:
        print(f"📤 업로드: {title[:50]}...")
        body = {"snippet": {"title": title[:100], "description": desc[:4900],
                            "tags": ["worship","ccm","찬양 연속듣기","묵상음악","수면음악","기도음악","calm worship","sleep music","2 hours worship"],
                            "categoryId": "10", "defaultLanguage": "ko"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        media = MediaFileUpload(path, mimetype="video/mp4", resumable=True, chunksize=8*1024*1024)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None: _, resp = req.next_chunk()
        vid = resp["id"]
        print(f"   ✅ https://youtu.be/{vid}")
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": PLAYLIST_ID, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()

    print("\n믹스 2종 업로드 + 재생목록 추가 완료")

if __name__ == "__main__":
    main()
