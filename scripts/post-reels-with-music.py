"""배경음악 포함 릴스 영상 5편 제작 + 인스타/페이스북 업로드"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, random
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"
BGM_DIR = os.path.join(HOME, "lighthouse-media", "assets", "bgm")
OUT = os.path.join(HOME, "lighthouse-media", "output", "reels")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1920
FPS = 2

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size):
    p = "C:/Windows/Fonts/timesbd.ttf"
    if not os.path.exists(p): p = "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def make_frames(scenes, name):
    frames_dir = os.path.join(OUT, f"frames_{name}")
    os.makedirs(frames_dir, exist_ok=True)
    fnum = 0
    total_dur = sum(s.get("dur",8) for s in scenes)

    for si, sc in enumerate(scenes):
        dur = sc.get("dur", 8)
        style = sc.get("style", "dark")
        accent = sc.get("accent", (29,158,117))
        elapsed = sum(scenes[j].get("dur",8) for j in range(si))

        for f in range(dur * FPS):
            fp = f / max(dur*FPS, 1)
            tp = (elapsed + dur*fp) / total_dur
            fade = min(1.0, fp*4)
            if fp > 0.8: fade = max(0, (1-fp)*5)

            img = Image.new("RGB", (W, H), (0,0,0))
            d = ImageDraw.Draw(img)

            # 배경
            if style == "dawn":
                for row in range(H):
                    p = row/H
                    d.line([(0,row),(W,row)], fill=(int(10+p*40),int(15+p*30),int(35+p*45)))
            elif style == "night":
                for row in range(H):
                    p = row/H
                    d.line([(0,row),(W,row)], fill=(int(5+p*3),int(5+p*5),int(15+p*10)))
                import random; random.seed(42)
                for _ in range(80):
                    x,y2 = random.randint(0,W), random.randint(0,H//2)
                    d.ellipse([x-1,y2-1,x+1,y2+1], fill=(200,200,200))
            elif style == "golden":
                for row in range(H):
                    p = row/H
                    d.line([(0,row),(W,row)], fill=(int(25+p*30),int(15+p*18),int(5+p*8)))
            elif style == "rain":
                for row in range(H):
                    p = row/H
                    d.line([(0,row),(W,row)], fill=(int(8+p*4),int(10+p*6),int(18+p*10)))
                import random; random.seed(int(fp*100))
                for _ in range(30):
                    x = random.randint(0,W)
                    ys = random.randint(0,H-80)
                    d.line([(x,ys),(x-3,ys+60)], fill=(50,55,70), width=1)
            else:
                for row in range(H):
                    p = row/H
                    d.line([(0,row),(W,row)], fill=(int(8+p*6),int(10+p*8),int(20+p*12)))

            # 시네마틱 바
            d.rectangle([0,0,W,70], fill=(0,0,0))
            d.rectangle([0,H-70,W,H], fill=(0,0,0))

            bc = tuple(int(c*fade) for c in accent)
            d.rectangle([0,70,W,73], fill=bc)

            # 브랜드
            d.text((60,85), "LIGHTHOUSE MEDIA", font=gf(18), fill=tuple(int(c*fade*0.5) for c in accent))

            # 영어 명언
            qe = sc.get("quote_en","")
            if qe:
                tc(d, 320, qe, gf_en(26), tuple(int(140*fade) for _ in range(3)), 6)

            # 구분선
            lw = int(100*min(1,fp*3))
            if lw > 0: d.rectangle([W//2-lw,490,W//2+lw,492], fill=bc)

            # 한글
            title = sc.get("title","")
            tc(d, 540, title, gf(52,True), tuple(int(255*fade) for _ in range(3)), 20)

            # 부제
            body = sc.get("body","")
            if body:
                tc(d, 880, body, gf(26), tuple(int(160*fade) for _ in range(3)), 10)

            # 출처
            src = sc.get("source","")
            if src:
                tc(d, H-220, src, gf(20), tuple(int(c*fade*0.5) for c in accent))

            # 하단
            d.rectangle([W//2-25,H-140,W//2+25,H-137], fill=bc)
            tc(d, H-120, "@lighthouse_media77", gf(14), tuple(int(50*fade) for _ in range(3)))

            # 진행바
            d.rectangle([0,H-70,int(W*tp),H-67], fill=bc)

            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    return frames_dir, total_dur, fnum

def encode_video(frames_dir, total_dur, bgm_file, output_name):
    vpath = os.path.join(OUT, f"{output_name}.mp4")
    bgm_path = os.path.join(BGM_DIR, bgm_file)
    print(f"    BGM: {bgm_file}")

    # 영상 + 음악 합성
    cmd = [FFMPEG, "-y",
           "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
           "-i", bgm_path,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k",
           "-filter_complex", f"[1:a]afade=t=in:d=1,afade=t=out:st={total_dur-2}:d=2,volume=0.3[a]",
           "-map", "0:v", "-map", "[a]",
           "-vf", f"scale={W}:{H},fps=30",
           "-t", str(total_dur), "-shortest",
           vpath]

    subprocess.run(cmd, capture_output=True, timeout=60)
    shutil.rmtree(frames_dir, ignore_errors=True)

    if os.path.exists(vpath):
        return vpath
    return None

def upload_video_ig(vpath, caption):
    """인스타 릴스로 업로드 (동영상)"""
    # 먼저 Imgur에 영상 업로드 (인스타는 공개 URL 필요)
    with open(vpath, 'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/upload', headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                       data={'video': enc, 'type': 'base64'})
    vid_url = ir.json().get('data',{}).get('link')

    if not vid_url:
        # Imgur 영상 업로드 실패 시 썸네일로 게시
        return None

    # 릴스로 게시
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
        'video_url': vid_url,
        'media_type': 'REELS',
        'caption': caption,
        'access_token': IG_TOKEN,
    })
    d = r.json()
    if 'id' not in d:
        return None

    # 처리 대기 (영상은 시간 걸림)
    container_id = d['id']
    for _ in range(12):
        time.sleep(10)
        check = requests.get(f'https://graph.facebook.com/v21.0/{container_id}?fields=status_code&access_token={IG_TOKEN}')
        status = check.json().get('status_code','')
        if status == 'FINISHED':
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={
                'creation_id': container_id, 'access_token': IG_TOKEN
            })
            return r2.json().get('id')
        elif status == 'ERROR':
            return None
    return None

def upload_video_fb(vpath, description):
    """페이스북 페이지에 동영상 업로드"""
    with open(vpath, 'rb') as f:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/videos',
                          files={'source': (os.path.basename(vpath), f, 'video/mp4')},
                          data={'description': description, 'access_token': FB_TOKEN})
    return r.json()

print("=" * 60)
print("  REELS WITH MUSIC FACTORY")
print("=" * 60)

_all_bgm = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]

reels = [
    {
        "name": "comfort-music",
        "bgm": random.choice(_all_bgm),
        "title_yt": "오늘 하루 수고한 당신에게 #shorts #힐링",
        "scenes": [
            {"dur":8, "style":"night", "accent":(29,158,117),
             "quote_en":"\"You are braver than you believe,\nstronger than you seem.\"",
             "title":"당신은 생각보다\n용감하고\n보이는 것보다\n강합니다", "source":"- A.A. Milne"},
            {"dur":8, "style":"rain", "accent":(52,152,219),
             "quote_en":"", "title":"오늘 하루도\n잘 버텼습니다", "body":"아무도 모르는\n당신의 노력을\n저는 압니다"},
            {"dur":8, "style":"golden", "accent":(186,117,23),
             "quote_en":"\"Rest when you're weary.\nRefresh and renew yourself.\"",
             "title":"지치면 쉬세요\n그리고 다시\n시작하세요", "source":""},
            {"dur":6, "style":"dawn", "accent":(29,158,117),
             "quote_en":"", "title":"내일은 오늘보다\n조금 더 나은\n하루가 될 겁니다",
             "body":"Lighthouse Media\n@lighthouse_media77"},
        ],
        "cap": "오늘 하루 수고한 당신에게.\n\n당신은 생각보다 용감하고\n보이는 것보다 강합니다.\n\n지치면 쉬세요. 그리고 다시 시작하세요.\n내일은 조금 나을 겁니다.\n\n이 글이 필요한 사람에게 보내주세요.\n\nLighthouse Media\n\n#위로 #힐링 #오늘도수고했어 #직장인공감 #마음관리 #자기계발 #명언 #공감 #응원 #번아웃 #직장인 #마음챙김 #위로한마디 #당신은소중합니다 #라이트하우스미디어",
    },
    {
        "name": "motivation-music",
        "bgm": random.choice(_all_bgm),
        "title_yt": "포기하려는 당신에게 #shorts #동기부여",
        "scenes": [
            {"dur":7, "style":"mountain", "accent":(231,76,60),
             "quote_en":"\"It always seems impossible\nuntil it's done.\"",
             "title":"불가능해 보이는 것도\n해내고 나면\n아무것도 아닙니다", "source":"- Nelson Mandela"},
            {"dur":7, "style":"dawn", "accent":(186,117,23),
             "quote_en":"\"Success is not final,\nfailure is not fatal.\"",
             "title":"성공이 끝이 아니고\n실패가 치명적인\n것도 아닙니다", "source":"- Winston Churchill"},
            {"dur":7, "style":"golden", "accent":(29,158,117),
             "quote_en":"\"The best time to plant a tree\nwas 20 years ago.\nThe second best time is now.\"",
             "title":"나무를 심기\n가장 좋은 때는\n20년 전이었고\n그다음은 바로 지금입니다", "source":"- Chinese Proverb"},
            {"dur":5, "style":"dawn", "accent":(29,158,117),
             "quote_en":"", "title":"지금 시작하세요\n늦지 않았습니다",
             "body":"@lighthouse_media77"},
        ],
        "cap": "포기하려는 당신에게.\n\n\"불가능해 보이는 것도 해내고 나면 아무것도 아닙니다.\"\n- Nelson Mandela\n\n\"성공이 끝이 아니고 실패가 치명적인 것도 아닙니다.\"\n- Winston Churchill\n\n지금 시작하세요. 늦지 않았습니다.\n\n#동기부여 #명언 #만델라 #처칠 #도전 #성장 #자기계발 #직장인 #힐링 #포기하지마 #인생명언 #세계명언 #영감 #라이트하우스미디어 #마음관리",
    },
    {
        "name": "healing-rain",
        "bgm": random.choice(_all_bgm),
        "title_yt": "비 오는 날의 위로 #shorts #힐링 #비",
        "scenes": [
            {"dur":8, "style":"rain", "accent":(52,152,219),
             "quote_en":"\"After the rain,\nthe sun will reappear.\"",
             "title":"비가 온 뒤에\n태양은 반드시\n다시 나타납니다", "source":""},
            {"dur":8, "style":"rain", "accent":(155,89,182),
             "quote_en":"\"The soul would have\nno rainbow\nhad the eyes no tears.\"",
             "title":"눈물이 없었다면\n영혼에 무지개도\n없었을 것입니다", "source":"- John Vance Cheney"},
            {"dur":7, "style":"dawn", "accent":(186,117,23),
             "quote_en":"\"Every storm runs out\nof rain.\"",
             "title":"모든 폭풍에는\n비가 그치는\n순간이 옵니다", "source":"- Maya Angelou"},
            {"dur":5, "style":"golden", "accent":(29,158,117),
             "quote_en":"", "title":"지금 비가 오고 있다면\n곧 그칠 겁니다",
             "body":"@lighthouse_media77"},
        ],
        "cap": "비 오는 날의 위로.\n\n비가 온 뒤에 태양은 반드시 다시 나타납니다.\n모든 폭풍에는 비가 그치는 순간이 옵니다.\n\n지금 힘든 시간을 보내고 있다면\n이 글을 저장해두세요.\n\n#비오는날 #위로 #힐링 #명언 #마음관리 #직장인공감 #공감 #응원 #자기계발 #번아웃 #마음챙김 #세계명언 #인생명언 #라이트하우스미디어 #희망",
    },
]

for i, reel in enumerate(reels):
    print(f"\n[{i+1}/3] {reel['name']}")

    # 프레임 생성
    print("  Frames...")
    frames_dir, total_dur, fnum = make_frames(reel["scenes"], reel["name"])
    print(f"  {fnum} frames ({total_dur}s)")

    # 음악 합성
    print("  Encoding with BGM...")
    vpath = encode_video(frames_dir, total_dur, reel["bgm"], reel["name"])
    if not vpath:
        print("  ENCODE FAIL"); continue
    sz = os.path.getsize(vpath)/(1024*1024)
    print(f"  Video: {sz:.1f}MB")

    # 페이스북 영상 업로드
    print("  Uploading to Facebook...")
    fb = upload_video_fb(vpath, reel["cap"][:500])
    print(f"  FB: {'OK' if 'id' in fb else fb}")
    time.sleep(3)

    # 인스타 릴스 시도
    print("  Uploading to Instagram Reels...")
    ig = upload_video_ig(vpath, reel["cap"])
    print(f"  IG: {'OK' if ig else 'API limit or processing'}")
    time.sleep(5)

print(f"\n{'='*60}")
print("  REELS WITH MUSIC DONE!")
print(f"  Videos saved in: {OUT}")
print(f"{'='*60}")
