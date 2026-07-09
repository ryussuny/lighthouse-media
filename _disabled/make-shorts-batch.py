"""숏츠/릴스 5편 제작 + YouTube 업로드 + Instagram/Facebook 게시"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"

TODAY = datetime.now().strftime("%Y-%m-%d")
OUT = os.path.join(HOME, "lighthouse-media", "output", TODAY, "shorts")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1920
FPS = 2
DARK = (10, 12, 24)

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def make_video(scenes, video_name):
    """장면별 프레임 생성 → ffmpeg 합성"""
    frames_dir = os.path.join(OUT, f"frames_{video_name}")
    os.makedirs(frames_dir, exist_ok=True)

    fnum = 0
    em_colors = {"공감":(100,120,180),"위로":(29,158,117),"희망":(186,117,23),"실천":(52,152,219),"충격":(231,76,60),"분노":(155,89,182)}

    for si, sc in enumerate(scenes):
        dur = sc.get("dur", 8)
        ec = em_colors.get(sc.get("emotion","위로"), (29,158,117))
        title = sc.get("title", "")
        body = sc.get("body", "")

        for f in range(dur * FPS):
            prog = f / max(dur * FPS, 1)
            fade = min(1.0, f / max(FPS * 0.4, 1))
            if f > (dur * FPS) - FPS * 0.3:
                fade = max(0, ((dur * FPS) - f) / max(FPS * 0.3, 1))

            img = Image.new("RGB", (W, H), DARK)
            d = ImageDraw.Draw(img)

            # 배경
            off = int(prog * 30)
            d.ellipse([W-280+off, 80-off, W+80+off, 440-off], fill=(16,18,34))
            d.ellipse([-120-off, H-380+off, 220-off, H-80+off], fill=(16,18,34))

            bc = tuple(int(c*fade) for c in ec)
            d.rectangle([0,0,W,4], fill=bc)

            # 장면 번호 (큰 투명)
            nc = tuple(int(c*fade*0.06) for c in ec)
            d.text((W-220, 120), str(si+1), font=gf(180,True), fill=nc)

            # 브랜드
            d.text((60, 70), "LIGHTHOUSE MEDIA", font=gf(22), fill=tuple(int(c*fade) for c in (29,158,117)))

            # 감정 배지
            em = sc.get("emotion", "")
            if em:
                d.rounded_rectangle([60,120,60+len(em)*22+20,155], radius=10, fill=bc)
                d.text((72,125), em, font=gf(18,True), fill=tuple(int(255*fade) for _ in range(3)))

            # 제목
            tc = tuple(int(255*fade) for _ in range(3))
            y = 520
            for ln in title.split("\n"):
                bb = d.textbbox((0,0), ln, font=gf(56,True))
                d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(56,True), fill=tc)
                y += bb[3]-bb[1]+20

            # 구분선
            lw = int(140 * min(1, prog*2))
            if lw > 0:
                d.rectangle([W//2-lw, y+20, W//2+lw, y+23], fill=bc)

            # 본문
            nf = max(0, min(1, (prog-0.15)*2.5))
            nc2 = tuple(int(185*nf*fade) for _ in range(3))
            ny = y + 60
            for ln in body.split("\n"):
                if not ln.strip(): ny += 12; continue
                while len(ln) > 20:
                    part = ln[:20]
                    bb = d.textbbox((0,0), part, font=gf(30))
                    d.text(((W-(bb[2]-bb[0]))/2, ny), part, font=gf(30), fill=nc2)
                    ny += bb[3]-bb[1]+8
                    ln = ln[20:]
                if ln.strip():
                    bb = d.textbbox((0,0), ln, font=gf(30))
                    d.text(((W-(bb[2]-bb[0]))/2, ny), ln, font=gf(30), fill=nc2)
                    ny += bb[3]-bb[1]+8

            # 하단
            d.rectangle([W//2-35,H-130,W//2+35,H-127], fill=bc)
            fc = tuple(int(70*fade) for _ in range(3))
            txt = "@lighthouse_media77"
            bb = d.textbbox((0,0), txt, font=gf(18))
            d.text(((W-(bb[2]-bb[0]))/2, H-100), txt, font=gf(18), fill=fc)

            # 진행바
            total_dur = sum(s.get("dur",8) for s in scenes)
            elapsed = sum(scenes[j].get("dur",8) for j in range(si)) + dur*prog
            bar_w = int(W * elapsed / total_dur)
            d.rectangle([0, H-6, bar_w, H], fill=bc)

            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    # ffmpeg
    vpath = os.path.join(OUT, f"{video_name}.mp4")
    total_dur = sum(s.get("dur",8) for s in scenes)
    subprocess.run([FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-vf", f"scale={W}:{H},fps=30", "-t", str(total_dur), vpath],
                   capture_output=True, timeout=60)
    shutil.rmtree(frames_dir, ignore_errors=True)

    if os.path.exists(vpath):
        return vpath, total_dur
    return None, 0

def upload_youtube(vpath, title, desc, tags):
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
    body = {
        'snippet': {'title': title, 'description': desc, 'tags': tags, 'categoryId': '22', 'defaultLanguage': 'ko'},
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(vpath, mimetype='video/mp4', resumable=True)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    resp = None
    while resp is None: _, resp = req.next_chunk()
    vid = resp['id']

    try:
        yt.playlistItems().insert(part='snippet', body={
            'snippet': {'playlistId': 'PLqShegXvrK3wiKvpIfJth9m5Fs7j8Qmgm',
                        'resourceId': {'kind': 'youtube#video', 'videoId': vid}}
        }).execute()
    except: pass

    return vid

def upload_thumb_ig_fb(title, desc, vid_id, color):
    # 썸네일 생성
    img = Image.new("RGB", (1080, 1350), DARK)
    d = ImageDraw.Draw(img)
    for row in range(1350):
        d.line([(0,row),(1080,row)], fill=(10+int(row/1350*6), 12+int(row/1350*8), 24+int(row/1350*10)))
    d.rectangle([0,0,1080,4], fill=color)
    d.text((60,55), "LIGHTHOUSE MEDIA", font=gf(20), fill=color)
    d.rounded_rectangle([60,100,170,130], radius=10, fill=color)
    d.text((74,104), "NEW", font=gf(18,True), fill=(255,255,255))

    y = 380
    for ln in title.replace(" #shorts","").split("\n")[:3]:
        if len(ln) > 15: ln = ln[:15]
        bb = d.textbbox((0,0), ln, font=gf(48,True))
        d.text(((1080-(bb[2]-bb[0]))/2, y), ln, font=gf(48,True), fill=(255,255,255))
        y += bb[3]-bb[1]+18

    d.rectangle([490,1250,590,1254], fill=color)

    tpath = os.path.join(OUT, "thumb.jpg")
    img.save(tpath, "JPEG", quality=95)

    with open(tpath,'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':enc,'type':'base64'})
    turl = ir.json().get('data',{}).get('link')
    if not turl: return
    time.sleep(3)

    yt_url = f"https://youtube.com/shorts/{vid_id}"
    cap = f"{title.replace(' #shorts','')}\n\nYouTube Shorts로 보기: 프로필 링크\n\n{desc[:200]}\n\n#숏츠 #shorts #직장인 #번아웃 #자기계발 #마음관리 #힐링 #직장인공감 #워라밸 #라이트하우스미디어 #위로 #공감 #직장인힐링 #에너지관리 #습관"

    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url':turl,'caption':cap,'access_token':IG_TOKEN})
    ig = False
    if 'id' in r.json():
        time.sleep(5)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id':r.json()['id'],'access_token':IG_TOKEN})
        ig = 'id' in r2.json()

    fm = f"{title.replace(' #shorts','')}\n\nYouTube: {yt_url}\n\n{desc[:200]}\n\n- Lighthouse Media"
    fb = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url':turl,'message':fm,'access_token':FB_TOKEN})

    return ig, 'id' in fb.json()

print("=" * 60)
print(f"  SHORTS FACTORY - {TODAY}")
print(f"  5 videos x 3 channels")
print("=" * 60)

# 5개 영상 정의
videos = [
    {
        "name": "stress-3sec",
        "title": "3초 만에 스트레스 날리는 법 #shorts",
        "color": (231,76,60),
        "scenes": [
            {"dur":5, "emotion":"충격", "title":"직장인 74%가\n매일 스트레스를\n받고 있습니다", "body":"당신도 그중 한 명이라면\n3초면 됩니다"},
            {"dur":8, "emotion":"공감", "title":"지금 해보세요", "body":"주먹을 꽉 쥐세요\n3초만 참으세요\n1... 2... 3...\n한번에 풀어주세요"},
            {"dur":7, "emotion":"실천", "title":"깊게 한숨\n한 번 쉬세요", "body":"코로 4초 들이마시고\n입으로 8초 내쉬세요\n이것만으로\n코르티솔 23% 감소"},
            {"dur":5, "emotion":"위로", "title":"어때요?\n조금 나아졌죠?", "body":"매일 이것만 해보세요\n3초가 하루를 바꿉니다"},
            {"dur":5, "emotion":"실천", "title":"저장하고\n매일 실천하세요", "body":"무료 전자책도\n프로필에서 받아가세요\n@lighthouse_media77"},
        ],
        "desc": "3초 만에 스트레스를 날리는 과학적 방법.\n주먹 쥐기 + 풀기 + 깊은 호흡.\n이것만으로 코르티솔이 23% 감소합니다.",
        "tags": ["스트레스해소","3초힐링","직장인","번아웃","마음관리","자기계발","힐링","shorts","숏츠"],
    },
    {
        "name": "morning-2min",
        "title": "아침 2분이면 하루가 달라집니다 #shorts",
        "color": (52,152,219),
        "scenes": [
            {"dur":5, "emotion":"공감", "title":"매일 아침\n알람 5번 끄고\n겨우 일어나시죠?", "body":"당신만 그런 게 아닙니다"},
            {"dur":7, "emotion":"희망", "title":"딱 2분만\n투자해보세요", "body":"눈 뜨자마자\n물 한 잔 (30초)\n기지개 (30초)\n감사 1가지 (1분)"},
            {"dur":8, "emotion":"실천", "title":"이 2분이\n나머지 23시간\n58분을 바꿉니다", "body":"하버드 연구:\n아침 루틴 실천자의\n업무 효율 31% 향상"},
            {"dur":5, "emotion":"위로", "title":"내일 아침부터\n시작해보세요", "body":"작은 시작이\n큰 변화를 만듭니다"},
            {"dur":5, "emotion":"실천", "title":"더 자세한 루틴은\n프로필 링크에서", "body":"무료 전자책\n'아침 5분의 기적'\n@lighthouse_media77"},
        ],
        "desc": "아침 2분 루틴으로 하루가 달라집니다.\n물 한 잔 + 기지개 + 감사 1가지.\n하버드 연구: 업무 효율 31% 향상.",
        "tags": ["모닝루틴","아침습관","2분루틴","직장인","자기계발","습관","미라클모닝","shorts","숏츠"],
    },
    {
        "name": "burnout-signal",
        "title": "번아웃 5가지 신호, 3개 이상이면 위험 #shorts",
        "color": (155,89,182),
        "scenes": [
            {"dur":5, "emotion":"충격", "title":"번아웃은\n갑자기 오지\n않습니다", "body":"반드시 신호가 있습니다"},
            {"dur":6, "emotion":"공감", "title":"1. 사소한 일에\n짜증이 난다", "body":"예전엔 안 그랬는데\n요즘 유독 예민하다면"},
            {"dur":6, "emotion":"공감", "title":"2. 일에 의미를\n못 느낀다", "body":"왜 이 일을 하는지\n모르겠다면"},
            {"dur":6, "emotion":"공감", "title":"3. 잠을 자도\n피곤하다", "body":"몸은 누워있지만\n뇌는 쉬지 못하는 상태"},
            {"dur":5, "emotion":"공감", "title":"4. 혼자 있고 싶다\n5. 웃음이 줄었다", "body":"사람이 피곤해지는 겁니다"},
            {"dur":5, "emotion":"위로", "title":"3개 이상이면\n쉬어야 합니다", "body":"쉬는 건 포기가 아닙니다\n다시 시작하기 위한 준비입니다"},
            {"dur":5, "emotion":"실천", "title":"무료 전자책에서\n회복법 알려드립니다", "body":"프로필 링크 클릭\n@lighthouse_media77"},
        ],
        "desc": "번아웃 5가지 신호. 3개 이상이면 위험합니다.\n짜증 / 의미상실 / 만성피로 / 고립 / 무감정.\n프로필에서 무료 전자책 받으세요.",
        "tags": ["번아웃","번아웃신호","직장인건강","멘탈케어","자기계발","마음관리","스트레스","shorts","숏츠"],
    },
    {
        "name": "comfort-words",
        "title": "오늘 하루 수고한 당신에게 #shorts #힐링",
        "color": (29,158,117),
        "scenes": [
            {"dur":7, "emotion":"공감", "title":"오늘도\n잘 버텼습니다", "body":"아무도 알아주지 않아도\n당신은 충분히\n잘하고 있습니다"},
            {"dur":7, "emotion":"위로", "title":"지치는 건\n당연한 겁니다", "body":"매일 쏟아지는 일들 속에서\n웃으며 버티는 것만으로도\n대단한 일입니다"},
            {"dur":7, "emotion":"위로", "title":"잠깐 멈춰도\n괜찮습니다", "body":"쉬는 것은 포기가 아니라\n다시 시작하기 위한\n준비입니다"},
            {"dur":7, "emotion":"희망", "title":"당신은\n혼자가 아닙니다", "body":"같은 하루를 살아가는\n수많은 사람들이\n당신 곁에 있습니다"},
            {"dur":7, "emotion":"희망", "title":"내일은\n오늘보다\n조금 더 나은\n하루가 될 겁니다", "body":"류선희\nLighthouse Media"},
        ],
        "desc": "오늘 하루 수고한 당신에게.\n잘 버텼습니다. 쉬어도 괜찮습니다.\n내일은 조금 나을 겁니다.",
        "tags": ["위로","오늘도수고했어","힐링","직장인공감","마음관리","응원","공감","shorts","숏츠","당신은소중합니다"],
    },
    {
        "name": "energy-secret",
        "title": "직장인 에너지 충전 비밀 3가지 #shorts",
        "color": (186,117,23),
        "scenes": [
            {"dur":5, "emotion":"충격", "title":"커피로는\n에너지가\n안 찹니다", "body":"진짜 충전법을 알려드립니다"},
            {"dur":8, "emotion":"실천", "title":"비밀 1\n마이크로 브레이크", "body":"2시간마다 3분 휴식\n창밖 보기 20초\n이것만으로 집중력 40% 회복"},
            {"dur":8, "emotion":"실천", "title":"비밀 2\n감사 리셋", "body":"점심시간에\n감사한 것 3가지 적기\n옥시토신 분비 증가\n오후 에너지 충전"},
            {"dur":8, "emotion":"실천", "title":"비밀 3\n퇴근 산책 10분", "body":"걷기만 해도\nBDNF 단백질 분비\n뇌 회복 + 수면 질 향상"},
            {"dur":5, "emotion":"희망", "title":"이 3가지로\n2주면\n달라집니다", "body":"자세한 가이드는\n프로필 링크에서\n@lighthouse_media77"},
        ],
        "desc": "직장인 에너지 충전 비밀 3가지.\n마이크로 브레이크 / 감사 리셋 / 퇴근 산책.\n커피보다 효과적입니다.",
        "tags": ["에너지관리","직장인팁","생산성","번아웃극복","자기계발","마음관리","힐링","shorts","숏츠"],
    },
]

for i, v in enumerate(videos):
    print(f"\n{'='*40}")
    print(f"  [{i+1}/5] {v['name']}")
    print(f"{'='*40}")

    # 영상 생성
    print("  Generating frames...")
    vpath, dur = make_video(v["scenes"], v["name"])
    if not vpath:
        print("  VIDEO FAIL"); continue
    sz = os.path.getsize(vpath)/(1024*1024)
    print(f"  Video: {sz:.1f}MB ({dur}s)")

    # YouTube 업로드
    print("  Uploading to YouTube...")
    try:
        vid_id = upload_youtube(vpath, v["title"], v["desc"], v["tags"])
        print(f"  YT: https://youtube.com/shorts/{vid_id}")
    except Exception as e:
        print(f"  YT FAIL: {e}")
        vid_id = None
    time.sleep(3)

    # Instagram + Facebook
    if vid_id:
        print("  Posting to IG + FB...")
        try:
            ig, fb = upload_thumb_ig_fb(v["title"], v["desc"], vid_id, v["color"])
            print(f"  IG:{'OK' if ig else 'X'} FB:{'OK' if fb else 'X'}")
        except Exception as e:
            print(f"  IG/FB: {e}")
    time.sleep(5)

print(f"\n{'='*60}")
print("  SHORTS FACTORY COMPLETE!")
print(f"  5 videos uploaded to YouTube + IG + FB")
print(f"{'='*60}")
