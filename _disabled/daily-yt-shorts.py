"""매일 유튜브 숏츠 2편 (말씀+동기부여) + 음악 + 자동 업로드"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, subprocess, shutil, re, time, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT = os.path.join(HOME, "lighthouse-media", "output", TODAY, "shorts")
os.makedirs(OUT, exist_ok=True)
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"
BGM_DIR = os.path.join(HOME, "lighthouse-media", "assets", "bgm")
_bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
BGM = os.path.join(BGM_DIR, random.choice(_bgm_files))
print(f"  BGM selected: {os.path.basename(BGM)}")

W, H = 1080, 1920
FPS = 2

def ft(s):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, s)
            except: pass
    return ImageFont.load_default()

def ft_l(s):
    for p in ['C:/Windows/Fonts/HANBatang.ttf','C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, s)
            except: pass
    return ImageFont.load_default()

def ft_s(s):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', s) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

IVORY = (248,245,237)
GOLD = (180,150,80)
DEEP = (55,45,35)
MED = (100,80,60)
DARK = (28,25,32)

def ctr(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp + 5; continue
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def make_video(scenes, name, bgm_vol=0.2):
    frames = os.path.join(OUT, "f_" + name)
    os.makedirs(frames, exist_ok=True)
    fn = 0
    for si, sc in enumerate(scenes):
        dur = sc['dur']
        bg = sc.get('bg', IVORY)
        for f in range(dur * FPS):
            fp = f / max(dur*FPS,1)
            fade = min(1.0, fp*4)
            if fp > 0.8: fade = max(0,(1-fp)*5)
            img = Image.new('RGB', (W,H), bg)
            d = ImageDraw.Draw(img)
            d.rectangle([0,0,W,2], fill=GOLD)
            cx = W//2
            gc = tuple(int(c*fade) for c in GOLD)
            d.rectangle([cx-1,60,cx+1,90], fill=gc)
            d.rectangle([cx-12,72,cx+12,74], fill=gc)
            y = sc.get('y_start', 550)
            for text, size, color, bold in sc['items']:
                if not text: y += 25; continue
                fc = tuple(int(c*fade) for c in color)
                f2 = ft(size) if bold else ft_l(size)
                while len(text) > 14:
                    part = text[:14]
                    bb = d.textbbox((0,0), part, font=f2)
                    d.text(((W-(bb[2]-bb[0]))/2, y), part, font=f2, fill=fc)
                    y += bb[3]-bb[1]+12
                    text = text[14:]
                if text:
                    bb = d.textbbox((0,0), text, font=f2)
                    d.text(((W-(bb[2]-bb[0]))/2, y), text, font=f2, fill=fc)
                    y += bb[3]-bb[1]+20
            d.rectangle([cx-20,H-110,cx+20,H-108], fill=gc)
            img.save(os.path.join(frames, f"f_{fn:05d}.png"))
            fn += 1
    td = sum(s['dur'] for s in scenes)
    vp = os.path.join(OUT, name + ".mp4")
    subprocess.run([FFMPEG,"-y","-framerate",str(FPS),"-i",os.path.join(frames,"f_%05d.png"),
                    "-i",BGM,"-c:v","libx264","-preset","fast","-crf","23","-pix_fmt","yuv420p",
                    "-c:a","aac","-b:a","128k",
                    "-filter_complex",f"[1:a]afade=t=in:d=2,afade=t=out:st={td-3}:d=3,volume={bgm_vol}[a]",
                    "-map","0:v","-map","[a]","-vf",f"scale={W}:{H},fps=30","-t",str(td),"-shortest",vp],
                   capture_output=True, timeout=60)
    shutil.rmtree(frames, ignore_errors=True)
    return vp if os.path.exists(vp) else None

# 오늘의 말씀 일정 찾기
schedule = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "bible-schedule.json"), encoding='utf-8'))
today_item = None
for s in schedule:
    if s['date'] >= TODAY:
        today_item = s
        break
if not today_item:
    today_item = {"ref": "삼하 2:18-32", "title": "멈출 수 있는 용기"}

ref = today_item['ref']
title = today_item['title']

print("=" * 50)
print(f"  Daily YouTube Shorts ({TODAY})")
print("=" * 50)

# 1. 말씀 숏츠
print(f"\n[1/2] Bible: {ref} - {title}")
bible_scenes = [
    {"dur":7, "bg":IVORY, "y_start":450,
     "items": [("오늘의 말씀",20,MED,False), ("",0,DEEP,False),
               (ref,44,DEEP,True), ("",0,DEEP,False), (title,34,MED,True)]},
    {"dur":8, "bg":IVORY, "y_start":550,
     "items": [(title,40,DEEP,True)]},
    {"dur":8, "bg":(245,242,232), "y_start":500,
     "items": [("묵 상",18,(120,140,110),False), ("",0,DEEP,False),
               ("오늘 이 말씀이",36,DEEP,True), ("당신에게",36,DEEP,True),
               ("전합니다",36,DEEP,True)]},
    {"dur":7, "bg":DARK, "y_start":500,
     "items": [("오늘의 기도",18,GOLD,False), ("",0,DEEP,False),
               ("하나님 아버지,",30,(220,215,205),False), ("",0,DEEP,False),
               ("이 말씀을 마음에 새기고",28,(200,195,185),False),
               ("순종하며 살게 하소서",28,(200,195,185),False)]},
    {"dur":5, "bg":IVORY, "y_start":600,
     "items": [(ref,28,DEEP,True), ("",0,DEEP,False),
               ("Lighthouse Media",22,MED,True), ("@lighthouse_media77",16,(170,155,135),False)]},
]
v1 = make_video(bible_scenes, f"bible_{TODAY}")
print(f"  {'OK: ' + str(round(os.path.getsize(v1)/(1024*1024),1)) + 'MB' if v1 else 'FAIL'}")

# 2. 동기부여 숏츠
print(f"\n[2/2] Motivation")
mot_scenes = [
    {"dur":7, "bg":IVORY, "y_start":550,
     "items": [("멈출 수 있는 사람이",42,DEEP,True), ("진짜 용기 있는",42,DEEP,True),
               ("사람입니다",42,DEEP,True)]},
    {"dur":7, "bg":(245,240,230), "y_start":550,
     "items": [("달리는 것보다",36,DEEP,True), ("멈추는 것이",36,DEEP,True),
               ("더 어렵습니다",36,DEEP,True)]},
    {"dur":7, "bg":DARK, "y_start":550,
     "items": [("쉬어도 괜찮습니다",38,(220,215,205),True), ("",0,DEEP,False),
               ("당신은 충분히",32,(200,195,185),True), ("잘하고 있습니다",32,(200,195,185),True)]},
    {"dur":5, "bg":IVORY, "y_start":650,
     "items": [("Lighthouse Media",20,(170,155,135),False),
               ("@lighthouse_media77",16,(190,175,155),False)]},
]
v2 = make_video(mot_scenes, f"motivation_{TODAY}")
print(f"  {'OK: ' + str(round(os.path.getsize(v2)/(1024*1024),1)) + 'MB' if v2 else 'FAIL'}")

# 3. YouTube 업로드 시도
print("\n[Upload] YouTube...")
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    ytp = os.path.join(HOME, "OneDrive", "\ubc14\ud0d5 \ud654\uba74", "lighthouse_media", "token_lighthouse.json")
    ytk = json.load(open(ytp))
    creds = Credentials.from_authorized_user_info(ytk)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(ytp, 'w') as f: f.write(creds.to_json())
    yt = build('youtube', 'v3', credentials=creds)

    for vpath, vtitle, vtags in [
        (v1, f"{ref} {title} #shorts #말씀 #묵상", ['말씀','묵상','사무엘하','교회','기독교','shorts']),
        (v2, "멈출 수 있는 용기 #shorts #동기부여 #힐링", ['동기부여','힐링','위로','shorts','자기계발']),
    ]:
        if not vpath: continue
        body = {
            'snippet': {'title': vtitle, 'description': vtitle + '\n\nLighthouse Media | Lighthouse Media\n@lighthouse_media77',
                        'tags': vtags, 'categoryId': '22', 'defaultLanguage': 'ko'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(vpath, mimetype='video/mp4', resumable=True)
        req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
        resp = None
        while resp is None: _, resp = req.next_chunk()
        vid = resp['id']
        print(f"  YT: https://youtube.com/shorts/{vid}")
        time.sleep(3)
except Exception as e:
    err = str(e)[:80]
    if 'quota' in err.lower():
        print(f"  Quota exceeded - videos saved for later upload")
    else:
        print(f"  Error: {err}")

print(f"\n{'='*50}")
print(f"  Videos: {OUT}/")
print(f"{'='*50}")
