# -*- coding: utf-8 -*-
"""테마 플레이리스트 영상 (참고: Manna Breeze 카페 워십 포맷)
- ☕ 아침 커피 워십 60분 / 🌙 깊은 밤 묵상 워십 60분
- 테마 커버 + 테마별 곡 순서 + 반복으로 정확히 60분 + 챕터
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os, subprocess

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HOME = os.path.expanduser("~")
MUSIC = os.path.join(HOME, "lighthouse-biz", "music", "pilot-ep01")
AUDIO = os.path.join(MUSIC, "audio")
THEMES = os.path.join(MUSIC, "cover", "themes")
BOARD = os.path.join(HOME, "lighthouse-media", "config", "jarvis-board.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")
PLAYLIST_ID = "PLTt-NE3XVRRs"
PLAYLIST_URL = "https://youtube.com/playlist?list=" + PLAYLIST_ID

def wav_for(no):
    import re
    for f in os.listdir(AUDIO):
        b, ext = os.path.splitext(f)
        if ext.lower() not in (".wav", ".mp3"): continue
        m = re.match(r"^\s*(\d{1,2})[.\s\-_]", b)
        if m and int(m.group(1)) == no: return os.path.join(AUDIO, f)
    if no == 0:
        p = os.path.join(AUDIO, "quiet-before-you.wav")
        return p if os.path.exists(p) else None
    return None

def dur(path):
    out = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",path],
                         capture_output=True, text=True)
    return float(out.stdout.strip())

def hms(t):
    h, m, s = int(t//3600), int(t%3600//60), int(t%60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

THEMES_DEF = [
    {
        "key": "morning",
        "cover": os.path.join(THEMES, "morning-cafe.png"),
        "order": [5, 3, 9, 2, 4, 6, 1, 7, 8, 10, 0],
        "title": "아침 커피와 함께 듣는 워십 1시간 ☕ 하루를 여는 잔잔한 찬양 | Morning Coffee & Calm Worship",
        "desc_head": ("따뜻한 커피 한 잔과 함께, 말씀 안에서 하루를 시작하세요.\n"
                      "출근길·아침 묵상·조용한 카페 시간을 위한 잔잔한 워십입니다.\n"
                      "Start your morning with calm worship — coffee, quiet, and grace."),
        "tags": ["morning worship","아침찬양","카페음악","cafe worship","출근길 찬양","calm worship","ccm","묵상음악"],
    },
    {
        "key": "night",
        "cover": os.path.join(THEMES, "night-rest.png"),
        "order": [10, 1, 7, 8, 4, 0, 3, 6, 2, 5, 9],
        "title": "잠들기 전 듣는 워십 1시간 🌙 마음이 쉬는 밤의 찬양 | Night Worship for Deep Rest & Sleep",
        "desc_head": ("하루의 무게를 내려놓는 시간.\n"
                      "잠들기 전, 기도하며 마음을 정리하는 밤을 위한 고요한 워십입니다.\n"
                      "Let the day go. Rest in His peace tonight."),
        "tags": ["sleep worship","수면음악","밤에 듣는 찬양","잠들기전 찬양","night worship","ccm","기도음악","묵상음악"],
    },
]

def main():
    board = json.load(open(BOARD, encoding="utf-8"))
    tracks = {t["no"]: t for t in board["music"]["tracks"]}

    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)

    for th in THEMES_DEF:
        files, chapters, cum = [], [], 0.0
        for no in th["order"]:
            p = wav_for(no)
            if not p: continue
            files.append(p)
            chapters.append((cum, tracks[no]["title"]))
            cum += dur(p)

        lst = os.path.join(AUDIO, f"_theme-{th['key']}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in files: f.write(f"file '{p}'\n")
        mixw = os.path.join(AUDIO, f"_theme-{th['key']}.wav")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-ar","44100","-ac","2",mixw],
                       check=True, capture_output=True)

        out = os.path.join(AUDIO, f"_theme-{th['key']}.mp4")
        loops = int(3600 // cum) + 1
        subprocess.run(["ffmpeg","-y","-loop","1","-framerate","2","-i",th["cover"],
                        "-stream_loop",str(loops-1),"-i",mixw,
                        "-c:v","libx264","-tune","stillimage","-r","2","-c:a","aac","-b:a","192k",
                        "-pix_fmt","yuv420p","-vf","scale=1920:1080",
                        "-t","3600","-shortest",out], check=True, capture_output=True)
        print(f"🎬 {th['key']} 60분 영상 생성 완료")

        chap = "\n".join(f"{hms(s)} {t}" for s, t in chapters)
        desc = (f"{th['desc_head']}\n\n[Tracklist — 1회차]\n{chap}\n\n"
                f"🎧 곡별 영상·가사: {PLAYLIST_URL}\n"
                f"🔔 구독하시면 새로운 묵상 워십을 가장 먼저 들으실 수 있습니다.\n\n"
                f"* 본 음원은 AI 작곡 도구의 도움을 받아 제작되었습니다.\n\n"
                f"#worship #ccm #찬양 #LighthouseWorship " + " ".join("#"+t.replace(" ","") for t in th["tags"][:4]))
        body = {"snippet": {"title": th["title"][:100], "description": desc[:4900],
                            "tags": th["tags"] + ["lighthouse worship","찬양 연속듣기"],
                            "categoryId": "10", "defaultLanguage": "ko"},
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
        media = MediaFileUpload(out, mimetype="video/mp4", resumable=True, chunksize=8*1024*1024)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        resp = None
        while resp is None: _, resp = req.next_chunk()
        vid = resp["id"]
        print(f"   ✅ https://youtu.be/{vid}")
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": PLAYLIST_ID, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        for p in (lst, mixw, out):
            try: os.remove(p)
            except OSError: pass

    print("\n테마 플레이리스트 2종 발행 완료")

if __name__ == "__main__":
    main()
