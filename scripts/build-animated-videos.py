# -*- coding: utf-8 -*-
r"""전 영상 애니메이션 리마스터 — 곡 11 + 테마 2 + 믹스 2
정지 커버 → 살아있는 장면 (심리스 루프), 기존 메타데이터 승계, 구버전 비공개
사용법: py -X utf8 scripts/build-animated-videos.py [--only track|theme|mix] [--sample N]
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, math, random, subprocess, argparse, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scene_engine as SE
from scene_engine import (gradient, vignette, Bokeh, Stars, Rays, Steam, Embers,
                          CandleGlow, WaveLines, Moon, SunGlow, text_overlay,
                          playlist_overlay, render_loop, W, H)
from PIL import Image, ImageDraw, ImageFilter

HOME = os.path.expanduser("~")
MUSIC = os.path.join(HOME, "lighthouse-biz", "music", "pilot-ep01")
AUDIO = os.path.join(MUSIC, "audio")
LOOPS = os.path.join(MUSIC, "loops")
BOARD = os.path.join(HOME, "lighthouse-media", "config", "jarvis-board.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")
STATE = os.path.join(MUSIC, "remaster-state.json")
PLAYLIST_ID = "PLTt-NE3XVRRs"
os.makedirs(LOOPS, exist_ok=True)

CANON = {1:"01-be-still",2:"02-anchor-for-my-soul",3:"03-rest-in-you",4:"04-quiet-waters",
         5:"05-morning-light",6:"06-carry-me-home",7:"07-shim",8:"08-janjanhan-mulga",
         9:"09-dasi-ireona",10:"10-pyeongon",0:"quiet-before-you"}

PAL = {
    1: [(6,10,26),(12,22,52),(28,44,88),(70,90,130),(140,150,175)],
    2: [(8,20,24),(10,42,52),(16,74,84),(40,110,110),(196,168,120)],
    3: [(30,14,10),(70,30,18),(140,70,34),(210,130,60),(250,200,140)],
    4: [(4,24,22),(8,52,46),(16,90,76),(60,140,110),(180,220,190)],
    5: [(40,26,44),(90,50,70),(190,100,80),(240,160,90),(255,225,160)],
    6: [(14,8,30),(36,20,62),(76,44,104),(130,84,140),(220,160,150)],
    7: [(10,20,14),(22,44,30),(44,78,52),(90,120,84),(200,210,170)],
    8: [(6,18,32),(10,40,64),(20,72,104),(60,120,150),(190,215,220)],
    9: [(24,6,10),(62,16,20),(130,40,26),(210,90,40),(255,180,90)],
    10:[(20,26,38),(44,56,74),(84,100,122),(140,156,175),(225,228,230)],
    0: [(8,8,20),(18,20,44),(36,42,80),(80,88,128),(170,175,200)],
}

def scene_for(no, rng):
    """곡별 애니메이션 장면 구성"""
    bg = vignette(gradient(list(reversed(PAL[no]))))
    cx, cy = W//2, int(H*0.3)
    els = []
    if no == 1:   els = [Stars(rng), Rays(cx, int(H*0.18)), Bokeh(rng, 12, ((200,215,255),(255,245,225)), amax=46)]
    elif no == 2: els = [Stars(rng, 60, 0.45), Rays(int(W*0.74), int(H*0.2), (255,244,200), 2), WaveLines(int(H*0.66)), Bokeh(rng, 10, ((210,235,235),), amax=40)]
    elif no == 3: els = [SunGlow(cx, int(H*0.34)), Bokeh(rng, 16, ((255,215,160),(255,240,200)), amax=55), Embers(rng, 12)]
    elif no == 4: els = [Stars(rng, 40, 0.4), WaveLines(int(H*0.58), 8, (210,245,235)), Bokeh(rng, 14, ((190,235,215),), amax=48)]
    elif no == 5: els = [SunGlow(cx, int(H*0.42), (255,190,120), 380, 150), Bokeh(rng, 18, ((255,220,170),(255,200,140)), amax=58), Rays(cx, int(H*0.3), (255,225,170), 2)]
    elif no == 6: els = [Stars(rng, 90), Rays(cx, int(H*0.16), (250,215,195), 2), Bokeh(rng, 14, ((235,195,185),(200,170,220)), amax=50)]
    elif no == 7: els = [Bokeh(rng, 20, ((225,238,222),(200,220,195)), 26, 90, amax=34), Stars(rng, 30, 0.35)]
    elif no == 8: els = [Stars(rng, 50, 0.42), WaveLines(int(H*0.6), 8, (215,235,245)), Bokeh(rng, 12, ((200,225,240),), amax=44)]
    elif no == 9: els = [SunGlow(cx, int(H*0.32), (255,170,90), 420, 130), Embers(rng, 40), Rays(cx, int(H*0.2), (255,200,130), 3)]
    elif no == 10:els = [Moon(int(W*0.72), int(H*0.24)), Stars(rng, 100), Bokeh(rng, 12, ((220,228,238),), amax=36)]
    else:         els = [Stars(rng, 120), Rays(cx, int(H*0.15)), Bokeh(rng, 10, ((205,215,245),), amax=40), CandleGlow(int(W*0.2), int(H*0.8), r=180)]
    return bg, els

def cafe_bg():
    bg = gradient([(252,214,150),(244,186,120),(212,140,86),(126,74,44)])
    d = ImageDraw.Draw(bg, "RGBA")
    cx, cy = int(W*0.76), int(H*0.74)
    cup = (58, 36, 24, 235)
    d.rounded_rectangle([cx-120, cy-70, cx+120, cy+90], radius=34, fill=cup)
    d.ellipse([cx+96, cy-46, cx+186, cy+44], outline=cup, width=26)
    d.ellipse([cx-108, cy-84, cx+108, cy-52], fill=(94,62,40,255))
    d.ellipse([cx-92, cy-78, cx+92, cy-58], fill=(140,96,62,255))
    return vignette(bg), cx, cy

def night_bg():
    bg = gradient([(10,14,36),(16,22,52),(24,30,66),(8,10,24)])
    d = ImageDraw.Draw(bg, "RGBA")
    cx, cy = int(W*0.17), int(H*0.8)
    d.rounded_rectangle([cx-46, cy-40, cx+46, cy+120], radius=20, fill=(232,222,206,235))
    d.line([(cx, cy-70),(cx, cy-42)], fill=(60,44,30,255), width=7)
    return vignette(bg), cx, cy

def load_state():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def yt_client():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def wav_for(no):
    import re
    for f in os.listdir(AUDIO):
        b, ext = os.path.splitext(f)
        if ext.lower() not in (".wav", ".mp3"): continue
        m = re.match(r"^\s*(\d{1,2})[.\s\-_]", b)
        if m and int(m.group(1)) == no: return os.path.join(AUDIO, f)
    if no == 0:
        p = os.path.join(AUDIO, "quiet-before-you.wav")
        if os.path.exists(p): return p
    return None

def encode_with_audio(loop_mp4, audio_in, out, dur=None, ass_name=None):
    vf = "scale=1920:1080"
    if ass_name: vf += f",ass={ass_name}"
    cmd = ["ffmpeg","-y","-stream_loop","-1","-i",loop_mp4]
    cmd += audio_in
    cmd += ["-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","21",
            "-r","24","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-vf",vf]
    if dur: cmd += ["-t", str(dur)]
    cmd += ["-shortest", out]
    subprocess.run(cmd, check=True, capture_output=True, cwd=AUDIO)

def swap_video(yt, old_id, new_path, state_key, state, playlist=True):
    """기존 영상 메타 승계 → 새 영상 업로드 → 구버전 비공개 → 재생목록 교체"""
    from googleapiclient.http import MediaFileUpload
    old = yt.videos().list(part="snippet", id=old_id).execute()["items"]
    if not old:
        print(f"   ⚠️ 구영상 없음: {old_id}"); return None
    sn = old[0]["snippet"]
    body = {"snippet": {"title": sn["title"], "description": sn["description"],
                        "tags": sn.get("tags", []), "categoryId": sn.get("categoryId", "10"),
                        "defaultLanguage": sn.get("defaultLanguage", "ko")},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(new_path, mimetype="video/mp4", resumable=True, chunksize=8*1024*1024)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None: _, resp = req.next_chunk()
    new_id = resp["id"]
    yt.videos().update(part="status", body={"id": old_id, "status": {
        "privacyStatus": "private", "selfDeclaredMadeForKids": False}}).execute()
    if playlist:
        items = yt.playlistItems().list(part="id,snippet", playlistId=PLAYLIST_ID, maxResults=50).execute()["items"]
        for it in items:
            if it["snippet"]["resourceId"].get("videoId") == old_id:
                yt.playlistItems().delete(id=it["id"]).execute()
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": PLAYLIST_ID, "resourceId": {"kind": "youtube#video", "videoId": new_id}}}).execute()
    state[state_key] = new_id
    save_state(state)
    print(f"   ✅ 교체 완료: {old_id} → https://youtu.be/{new_id}")
    return new_id

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["track","theme","mix"])
    ap.add_argument("--sample", type=int, help="트랙 N 루프만 생성 (업로드 안 함)")
    args = ap.parse_args()

    board = json.load(open(BOARD, encoding="utf-8"))
    tracks = {t["no"]: t for t in board["music"]["tracks"]}
    state = load_state()

    if args.sample is not None:
        no = args.sample
        rng = random.Random(no*7+1)
        bg, els = scene_for(no, rng)
        ov = text_overlay(tracks[no]["title"], tracks[no]["lang"])
        out = os.path.join(LOOPS, f"{CANON[no]}-loop.mp4")
        print(f"샘플 루프 렌더링: {tracks[no]['title']}")
        render_loop(bg, els, ov, out)
        print("OK:", out); return

    yt = yt_client()

    # ── 1) 곡 영상 11개
    if args.only in (None, "track"):
        for no in [1,2,3,4,5,6,7,8,9,10,0]:
            key = f"track-{no}"
            if state.get(key): print(f"↷ 이미 완료: {tracks[no]['title']}"); continue
            t = tracks[no]
            if not t.get("youtube"): continue
            wav = wav_for(no)
            if not wav: print(f"⚠️ 오디오 없음: {t['title']}"); continue
            print(f"🎬 [{no}] {t['title']} — 장면 렌더링")
            rng = random.Random(no*7+1)
            bg, els = scene_for(no, rng)
            loop = os.path.join(LOOPS, f"{CANON[no]}-loop.mp4")
            if not os.path.exists(loop):
                render_loop(bg, els, text_overlay(t["title"], t["lang"]), loop)
            ass = f"{CANON[no]}.ass"
            ass_ok = os.path.exists(os.path.join(AUDIO, ass))
            final = os.path.join(LOOPS, f"{CANON[no]}-final.mp4")
            print("   인코딩…")
            encode_with_audio(loop, ["-i", wav], final, ass_name=ass if ass_ok else None)
            new_id = swap_video(yt, t["youtube"], final, key, state)
            if new_id:
                t["youtube"] = new_id
                json.dump(board, open(BOARD, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            try: os.remove(final)
            except OSError: pass

    # ── 2) 테마 플레이리스트 2개 (60분)
    THEME_META = [
        ("theme-morning", "RVzfMGsUarE", "cafe", [5,3,9,2,4,6,1,7,8,10,0],
         "아침 커피와 함께 듣는 워십", "Morning Coffee & Calm Worship", (120,64,30)),
        ("theme-night", "8Ptho_8TjF4", "night", [10,1,7,8,4,0,3,6,2,5,9],
         "잠들기 전, 마음이 쉬는 워십", "Night Worship for Deep Rest", (150,170,235)),
    ]
    if args.only in (None, "theme"):
        for key, old_id, kind, order, main_t, sub_t, accent in THEME_META:
            if state.get(key): print(f"↷ 이미 완료: {key}"); continue
            print(f"🎬 {key} — 장면 렌더링")
            rng = random.Random(99)
            if kind == "cafe":
                bg, cx, cy = cafe_bg()
                els = [Rays(int(W*0.18), 0, (255,236,200), 2, 200, 1), Steam(rng, cx, cy-90),
                       Bokeh(rng, 26, ((255,220,160),(255,240,210),(240,180,120)), amax=52)]
            else:
                bg, cx, cy = night_bg()
                els = [Stars(rng, 120), Moon(int(W*0.78), int(H*0.26)), CandleGlow(cx, cy-92),
                       Bokeh(rng, 12, ((180,200,255),(140,160,230)), amax=40)]
            loop = os.path.join(LOOPS, f"{key}-loop.mp4")
            if not os.path.exists(loop):
                render_loop(bg, els, playlist_overlay(main_t, sub_t, accent), loop)
            lst = os.path.join(AUDIO, f"_{key}.txt")
            with open(lst, "w", encoding="utf-8") as f:
                for no in order:
                    p = wav_for(no)
                    if p: f.write(f"file '{p}'\n")
            mixw = os.path.join(AUDIO, f"_{key}.wav")
            subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-ar","44100","-ac","2",mixw],
                           check=True, capture_output=True)
            final = os.path.join(LOOPS, f"{key}-final.mp4")
            print("   60분 인코딩…")
            encode_with_audio(loop, ["-stream_loop","2","-i",mixw], final, dur=3600)
            swap_video(yt, old_id, final, key, state)
            for p in (lst, mixw, final):
                try: os.remove(p)
                except OSError: pass

    # ── 3) 믹스 2개 (43분 / 2시간)
    MIX_META = [("mix-full", "hNReqx_Mgdc", None), ("mix-2h", "jxkZ_1aD5Tc", 7200)]
    if args.only in (None, "mix"):
        rng = random.Random(5)
        bg, els = scene_for(1, rng)  # 앨범 대표 무드
        ov = playlist_overlay("Rest / 안식", "EP01 Full Album — Lighthouse Worship", (150,170,235))
        loop = os.path.join(LOOPS, "album-loop.mp4")
        if not os.path.exists(loop):
            print("🎬 앨범 장면 렌더링")
            render_loop(bg, els, ov, loop)
        lst = os.path.join(AUDIO, "_album.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for no in [1,2,3,4,5,6,7,8,9,10,0]:
                p = wav_for(no)
                if p: f.write(f"file '{p}'\n")
        mixw = os.path.join(AUDIO, "_album.wav")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",lst,"-ar","44100","-ac","2",mixw],
                       check=True, capture_output=True)
        for key, old_id, dur in MIX_META:
            if state.get(key): print(f"↷ 이미 완료: {key}"); continue
            final = os.path.join(LOOPS, f"{key}-final.mp4")
            print(f"   {key} 인코딩…")
            audio_in = (["-stream_loop","3","-i",mixw] if dur else ["-i",mixw])
            encode_with_audio(loop, audio_in, final, dur=dur)
            swap_video(yt, old_id, final, key, state)
            try: os.remove(final)
            except OSError: pass
        for p in (lst, mixw):
            try: os.remove(p)
            except OSError: pass

    print("\n🌙 전 영상 애니메이션 리마스터 완료")

if __name__ == "__main__":
    main()
