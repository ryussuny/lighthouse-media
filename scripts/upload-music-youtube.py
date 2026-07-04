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
COVER = os.path.join(MUSIC, "cover", "cover.png")            # 폴백 커버
COVERS = os.path.join(MUSIC, "cover", "tracks")               # 곡별 커버
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
    "morninglight": 5, "carrymehome": 6, "쉼": 7, "잠잠하라": 7, "잔잔한물가": 8,
    "다시일어나": 9, "평온": 10, "quietbeforeyou": 0,
}

def norm(s):
    """소문자화 + 공백/구두점 제거 (한글 유지)"""
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())

def match_no(base):
    b = base.replace("-youtube", "")
    if b in SLUGS: return SLUGS[b]
    # "3. Rest in You" / "07 쉼" 같은 번호 접두사 우선 인식
    m = re.match(r"^\s*(\d{1,2})[.\s\-_]", b)
    if m and 1 <= int(m.group(1)) <= 10: return int(m.group(1))
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

def cover_for(no):
    """곡별 커버 (없으면 공용 커버)"""
    p = os.path.join(COVERS, f"{CANON[no]}.png")
    return p if os.path.exists(p) else COVER

def parse_lyric_lines(no):
    """가사 md → 순수 가사 라인 목록 ([섹션] 마커·frontmatter 제외)"""
    import glob
    pats = glob.glob(os.path.join(MUSIC, "lyrics", f"{no:02d}-*.md"))
    if not pats: return []
    lines, in_fm = [], False
    for raw in open(pats[0], encoding="utf-8").read().splitlines():
        s = raw.strip()
        if s == "---": in_fm = not in_fm; continue
        if in_fm or not s or s.startswith("[") or s.startswith("#"): continue
        lines.append(s)
    return lines

def _norm_txt(s):
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())

_WHISPER = None
def make_subs(wav, no, ass_path):
    """Whisper로 보컬 타이밍 추출 → 가사 라인과 매칭 → ASS 자막 생성"""
    global _WHISPER
    import difflib
    from faster_whisper import WhisperModel
    if _WHISPER is None:
        _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = _WHISPER.transcribe(wav, vad_filter=False)  # VAD는 노래를 음성 아님으로 오판

    lines = parse_lyric_lines(no)
    events, li = [], 0
    for seg in segments:
        text = seg.text.strip()
        if not text: continue
        if lines:
            best, bscore = None, 0.0
            for j in range(max(0, li - 1), min(li + 5, len(lines))):
                r = difflib.SequenceMatcher(None, _norm_txt(text), _norm_txt(lines[j])).ratio()
                if r > bscore: bscore, best = r, j
            if bscore >= 0.30:
                text, li = lines[best], best
        events.append([seg.start, seg.end, text])
    if not events: return False

    # 같은 문장 연속 구간 병합
    merged = [events[0]]
    for s, e, t in events[1:]:
        if t == merged[-1][2] and s - merged[-1][1] < 2.0: merged[-1][1] = e
        else: merged.append([s, e, t])

    def ts(t):
        h = int(t // 3600); m = int(t % 3600 // 60); sec = t % 60
        return f"{h}:{m:02d}:{sec:05.2f}"

    style = ("[Script Info]\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n\n"
             "[V4+ Styles]\n"
             "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
             "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
             "Style: Lyric,Malgun Gothic,58,&H00FFFFFF,&H00000000,&H96000000,-1,1,0,2,2,80,80,64,1\n\n"
             "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(style)
        for s, e, t in merged:
            t = t.replace("{", "").replace("}", "")
            f.write(f"Dialogue: 0,{ts(s)},{ts(e)},Lyric,{{\\fad(250,250)}}{t}\n")
    return True

def make_mp4(wav, mp4, no):
    """곡별 커버 정지화면 + 오디오 + 가사 자막 → 1080p mp4"""
    vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    ass_name = f"{CANON[no]}.ass"
    ass_path = os.path.join(AUDIO, ass_name)
    try:
        if make_subs(wav, no, ass_path):
            vf += f",ass={ass_name}"  # 상대경로 (cwd=AUDIO) — 윈도우 경로 이스케이프 회피
    except Exception as e:
        print(f"   ⚠️ 자막 생성 실패(자막 없이 진행): {e}")
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", cover_for(no), "-i", wav,
           "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "256k",
           "-pix_fmt", "yuv420p", "-vf", vf, "-shortest", mp4]
    subprocess.run(cmd, check=True, capture_output=True, cwd=AUDIO)

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
    ap.add_argument("--rebuild", action="store_true", help="기존 업로드 영상을 새 커버+자막 버전으로 교체 (구버전은 비공개 전환)")
    args = ap.parse_args()

    board = load_board()
    yt = None
    done, skipped = 0, 0

    if args.rebuild and not args.dry_run:
        yt = yt_client()
        for t in board["music"]["tracks"]:
            if t.get("youtube"):
                old = t["youtube"]
                print(f"🔒 구버전 비공개 전환: {t['title']} ({old})")
                yt.videos().update(part="status", body={
                    "id": old, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}).execute()
                t["youtube"] = None
                mp4 = os.path.join(AUDIO, f"{CANON[t['no']]}-youtube.mp4")
                if os.path.exists(mp4): os.remove(mp4)
        save_board(board)

    for fname in sorted(os.listdir(AUDIO)):
        base, ext = os.path.splitext(fname)
        if ext.lower() not in (".wav", ".mp3", ".m4a"): continue
        no = match_no(base)
        if no is None:
            print(f"⚠️  매칭 안 됨 (건너뜀): {fname}"); continue
        t = track_of(board, no)
        if t is None: continue

        t["suno"] = True; t["wav"] = True

        # 1) MP4 준비 (표준 슬러그 이름으로 생성 — 곡별 커버 + 가사 자막)
        mp4 = os.path.join(AUDIO, f"{CANON[no]}-youtube.mp4")
        if not os.path.exists(mp4):
            print(f"🎬 MP4 변환 (커버+자막): {t['title']}")
            if not args.dry_run: make_mp4(os.path.join(AUDIO, fname), mp4, no)
        t["mp4"] = True

        # 2) 업로드 (이미 업로드된 트랙은 건너뜀)
        if t.get("youtube"):
            skipped += 1; continue
        title = f"{t['title']} — Lighthouse Worship (Official Audio)"
        desc = (f"{t['title']} · EP01 「Rest / 안식」 — Lighthouse Worship\n"
                f"쉼이 필요한 당신을 위한 묵상 워십\n\n"
                f"🎧 전곡 연속듣기: https://youtube.com/playlist?list=PLTt-NE3XVRRs\n"
                f"🔔 구독하시면 새로운 묵상 워십을 가장 먼저 들으실 수 있습니다.\n\n"
                f"[가사]\n{lyrics_snippet(no) if no else ''}\n\n"
                f"* 본 음원은 AI 작곡 도구의 도움을 받아 제작되었습니다.\n\n"
                f"#worship #ccm #찬양 #묵상음악 #수면음악 #기도음악 #LighthouseWorship")
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
