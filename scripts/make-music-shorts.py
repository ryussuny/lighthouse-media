"""곡 하이라이트 쇼츠 생성 (세로 1080x1920, 커버 슬로우 줌 + 가사 자막)
사용법:
  py scripts/make-music-shorts.py --track 1 --start 52 --dur 30 --sample  # 샘플만 생성 (업로드 X)
  py scripts/make-music-shorts.py --all                                    # 전 곡 쇼츠 생성+업로드
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os, re, subprocess, argparse, glob

HOME = os.path.expanduser("~")
MUSIC = os.path.join(HOME, "lighthouse-biz", "music", "pilot-ep01")
AUDIO = os.path.join(MUSIC, "audio")
COVERS = os.path.join(MUSIC, "cover", "tracks")
SHORTS = os.path.join(MUSIC, "shorts")
BOARD = os.path.join(HOME, "lighthouse-media", "config", "jarvis-board.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")
PLAYLIST_URL = "https://youtube.com/playlist?list=PLTt-NE3XVRRs"
os.makedirs(SHORTS, exist_ok=True)

CANON = {1:"01-be-still", 2:"02-anchor-for-my-soul", 3:"03-rest-in-you",
         4:"04-quiet-waters", 5:"05-morning-light", 6:"06-carry-me-home",
         7:"07-shim", 8:"08-janjanhan-mulga", 9:"09-dasi-ireona",
         10:"10-pyeongon", 0:"quiet-before-you"}

# 곡별 하이라이트 구간 (초) — 기본은 후렴 추정 55s
HIGHLIGHT = {1: 52, 2: 55, 3: 55, 4: 55, 5: 55, 6: 55, 7: 55, 8: 55, 9: 55, 10: 55, 0: 40}
CLIP = 34  # 쇼츠 길이

def wav_for(no):
    for f in os.listdir(AUDIO):
        b, ext = os.path.splitext(f)
        if ext.lower() not in (".wav", ".mp3"): continue
        m = re.match(r"^\s*(\d{1,2})[.\s\-_]", b)
        if m and int(m.group(1)) == no: return os.path.join(AUDIO, f)
        nb = re.sub(r"[^0-9a-z가-힣]", "", b.lower())
        slug = CANON[no].split("-", 1)[1].replace("-", "")
        if slug and (slug in nb or nb == slug): return os.path.join(AUDIO, f)
    return None

_WHISPER = None
def make_vert_subs(wav_seg, no, ass_path):
    """구간 오디오 → 세로 쇼츠용 가사 자막 (크게, 중앙 하단)"""
    global _WHISPER
    import difflib
    from faster_whisper import WhisperModel
    if _WHISPER is None:
        _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = _WHISPER.transcribe(wav_seg, vad_filter=False)

    lines = []
    for p in glob.glob(os.path.join(MUSIC, "lyrics", f"{no:02d}-*.md")):
        in_fm = False
        for raw in open(p, encoding="utf-8").read().splitlines():
            s = raw.strip()
            if s == "---": in_fm = not in_fm; continue
            if in_fm or not s or s.startswith("[") or s.startswith("#"): continue
            lines.append(s)

    def nt(s): return re.sub(r"[^0-9a-z가-힣]", "", s.lower())
    events = []
    for seg in segments:
        text = seg.text.strip()
        if not text: continue
        if lines:
            best, bs = None, 0.0
            for ln in lines:
                r = difflib.SequenceMatcher(None, nt(text), nt(ln)).ratio()
                if r > bs: bs, best = r, ln
            if bs >= 0.3: text = best
        events.append([seg.start, seg.end, text])
    if not events: return False
    merged = [events[0]]
    for s, e, t in events[1:]:
        if t == merged[-1][2] and s - merged[-1][1] < 2.0: merged[-1][1] = e
        else: merged.append([s, e, t])

    def ts(t):
        return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
    hdr = ("[Script Info]\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
           "[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
           "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           "Style: Big,Malgun Gothic,76,&H00FFFFFF,&H00000000,&H78000000,-1,1,0,2,8,60,60,300,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(hdr)
        for s, e, t in merged:
            f.write(f"Dialogue: 0,{ts(s)},{ts(e)},Big,{{\\fad(300,300)}}{t.replace(chr(123),'').replace(chr(125),'')}\n")
    return True

def make_short(no, title, start, dur=CLIP):
    wav = wav_for(no)
    if not wav: print(f"⚠️ 오디오 없음: {title}"); return None
    cover = os.path.join(COVERS, f"{CANON[no]}.png")
    seg = os.path.join(SHORTS, f"_seg{no:02d}.wav")
    subprocess.run(["ffmpeg", "-y", "-ss", str(start), "-t", str(dur), "-i", wav,
                    "-ar", "44100", "-ac", "2",
                    "-af", f"afade=t=in:d=0.8,afade=t=out:st={dur-1.2}:d=1.2", seg],
                   check=True, capture_output=True)
    ass = os.path.join(SHORTS, f"{CANON[no]}-short.ass")
    has_subs = False
    try: has_subs = make_vert_subs(seg, no, ass)
    except Exception as e: print(f"   자막 스킵: {e}")

    out = os.path.join(SHORTS, f"{CANON[no]}-short.mp4")
    frames = dur * 30
    vf = (f"scale=2400:2400,zoompan=z='1.0+0.10*on/{frames}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2'"
          f":d={frames}:s=1080x1920:fps=30")
    if has_subs: vf += f",ass={os.path.basename(ass)}"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", cover, "-i", seg,
                    "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                    "-vf", vf, "-t", str(dur), "-shortest", out],
                   check=True, capture_output=True, cwd=SHORTS)
    os.remove(seg)
    print(f"✅ 쇼츠 생성: {title} → {out}")
    return out

def upload(path, title_txt, no):
    import json as _json
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials.from_authorized_user_info(_json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    title = f"{title_txt} #shorts"
    desc = (f"{title_txt} — Lighthouse Worship\n\n"
            f"🎧 풀버전과 전곡 듣기: {PLAYLIST_URL}\n\n"
            f"* 본 음원은 AI 작곡 도구의 도움을 받아 제작되었습니다.\n"
            f"#worship #ccm #찬양 #묵상음악 #shorts")
    body = {"snippet": {"title": title[:100], "description": desc,
                        "tags": ["shorts","worship","ccm","찬양","묵상음악"],
                        "categoryId": "10", "defaultLanguage": "ko"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None: _, resp = req.next_chunk()
    print(f"   📤 https://youtube.com/shorts/{resp['id']}")
    return resp["id"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", type=int)
    ap.add_argument("--start", type=int)
    ap.add_argument("--dur", type=int, default=CLIP)
    ap.add_argument("--sample", action="store_true", help="생성만, 업로드 안 함")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    board = json.load(open(BOARD, encoding="utf-8"))
    tracks = {t["no"]: t for t in board["music"]["tracks"]}

    todo = sorted([n for n in tracks if tracks[n].get("youtube")]) if args.all else [args.track]
    for no in todo:
        t = tracks[no]
        start = args.start if args.start is not None else HIGHLIGHT.get(no, 55)
        path = make_short(no, t["title"], start, args.dur)
        if path and not args.sample:
            hook = {1:"잠들기 전, 마음이 잠잠해지는 순간",2:"불안할 때 붙들 수 있는 한 곡",
                    3:"지친 하루의 끝에",4:"묵상할 때 틀어놓는 곡",5:"아침을 여는 찬양",
                    6:"위로가 필요한 밤",7:"시편 46편, 잠잠하라",8:"시편 23편, 잔잔한 물가로",
                    9:"다시 일어날 힘",10:"마음의 평온",0:"새벽, 고요히 그분 앞에"}.get(no, t["title"])
            upload(path, f"{hook} | {t['title']}", no)

if __name__ == "__main__":
    main()
