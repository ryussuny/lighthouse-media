"""매일 인스타 릴스 1편 자동 생성 + 업로드
- 동기부여/위로/힐링/자기계발 주제 랜덤 선택
- 배경음악 포함 시네마틱 영상 (1080x1920, 30~40초)
- Instagram Reels + Facebook 자동 게시
- Usage:
    python daily-ig-reels.py              # 자동 주제 선택
    python daily-ig-reels.py comfort      # 특정 카테고리
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, random, hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════
HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
CONFIG_DIR = os.path.join(REPO_DIR, "config")
BGM_DIR = os.path.join(REPO_DIR, "assets", "bgm")
OUT_DIR = os.path.join(REPO_DIR, "output", "reels")
os.makedirs(OUT_DIR, exist_ok=True)

tokens = json.load(open(os.path.join(CONFIG_DIR, "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

W, H = 1080, 1920
FPS = 2

# ═══════════════════════════════════════════════════════════════
# 폰트
# ═══════════════════════════════════════════════════════════════
def gf(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size):
    for p in ["C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0, 0), ln, font=font)
        d.text(((W - (bb[2] - bb[0])) / 2, y), ln, font=font, fill=fill)
        y += bb[3] - bb[1] + sp
    return y

# ═══════════════════════════════════════════════════════════════
# 릴스 콘텐츠 풀 (매일 다른 콘텐츠 선택)
# ═══════════════════════════════════════════════════════════════
REEL_POOL = {
    "comfort": [
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "\"You are allowed to be\nboth a masterpiece\nand a work in progress.\"",
                 "title": "당신은 이미\n충분히 아름답고\n동시에 성장 중입니다", "source": "- Sophia Bush"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "오늘 힘들었다면\n그건 약한 게 아니라\n살아있다는 증거입니다",
                 "body": "당신의 하루를\n응원합니다"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Be gentle with yourself.\nYou're doing the best you can.\"",
                 "title": "자신에게\n조금 더\n부드러워지세요", "source": ""},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "내일은 오늘보다\n조금 더 괜찮은\n하루가 될 겁니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "오늘 힘들었다면, 이 영상은 당신을 위한 것입니다.\n\n\"You are allowed to be both a masterpiece and a work in progress.\"\n\n자신에게 조금 더 부드러워지세요.\n내일은 조금 더 괜찮을 겁니다.\n\n이 글이 필요한 사람에게 보내주세요.\n\n#위로 #힐링 #오늘도수고했어 #직장인공감 #마음관리 #자기계발 #명언 #공감 #응원 #번아웃 #마음챙김 #당신은소중합니다 #selfcare #motivation #healing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "rain", "accent": (155, 89, 182),
                 "quote_en": "\"You don't have to be\nperfect to be amazing.\"",
                 "title": "완벽하지 않아도\n당신은 이미\n대단한 사람입니다", "source": ""},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"It's okay to not be okay.\"",
                 "title": "괜찮지 않아도\n괜찮습니다",
                 "body": "모든 감정은\n있는 그대로\n존중받을 자격이 있습니다"},
                {"dur": 7, "style": "golden", "accent": (29, 158, 117),
                 "quote_en": "", "title": "지금 이 순간에도\n당신을 응원하는\n사람이 있습니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신은 혼자가\n아닙니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "완벽하지 않아도 괜찮습니다.\n\n\"You don't have to be perfect to be amazing.\"\n\n괜찮지 않아도 괜찮아요.\n모든 감정은 있는 그대로 존중받을 자격이 있습니다.\n\n이 영상을 저장해두세요.\n\n#위로 #힘내 #괜찮아 #직장인힐링 #마음관리 #공감 #응원 #자존감 #selfcare #youarenotalone #mentalhealth #healing #motivation #keepgoing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The wound is the place\nwhere the light enters you.\"",
                 "title": "상처받은 곳으로\n빛이 들어옵니다", "source": "- Rumi"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "울어도 됩니다\n쉬어도 됩니다\n다만 포기하지 마세요",
                 "body": ""},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "\"Stars can't shine\nwithout darkness.\"",
                 "title": "어둠이 없으면\n별도 빛나지\n못합니다", "source": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "어두운 밤이 지나면\n반드시 새벽이 옵니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "상처받은 곳으로 빛이 들어옵니다.\n- Rumi\n\n울어도 됩니다. 쉬어도 됩니다.\n다만 포기하지 마세요.\n\n어둠이 없으면 별도 빛나지 못합니다.\n어두운 밤이 지나면 반드시 새벽이 옵니다.\n\n#힐링 #위로 #명언 #루미 #공감 #응원 #마음챙김 #자기계발 #직장인 #새벽 #희망 #healing #rumi #motivation #keepgoing",
        },
    ],
    "motivation": [
        {
            "scenes": [
                {"dur": 7, "style": "dawn", "accent": (231, 76, 60),
                 "quote_en": "\"The only limit to our\nrealization of tomorrow\nis our doubts of today.\"",
                 "title": "내일의 가능성을\n제한하는 것은\n오늘의 의심뿐입니다", "source": "- F.D. Roosevelt"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Don't watch the clock.\nDo what it does. Keep going.\"",
                 "title": "시계를 보지 마세요\n시계처럼 하세요\n계속 가세요", "source": "- Sam Levenson"},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "1%의 변화가\n365일이면\n37배가 됩니다",
                 "body": "오늘 작은 한 걸음이\n내일의 큰 변화가 됩니다"},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "지금 이 순간이\n시작하기에\n가장 좋은 때입니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "멈추지 마세요.\n\n\"Don't watch the clock. Do what it does. Keep going.\"\n- Sam Levenson\n\n1%의 변화가 365일이면 37배가 됩니다.\n오늘 작은 한 걸음이 내일의 큰 변화가 됩니다.\n\n지금이 시작하기에 가장 좋은 때입니다.\n\n#동기부여 #명언 #도전 #성장 #자기계발 #직장인 #변화 #시작 #1퍼센트 #습관 #motivation #keepgoing #growth #nevergiveup #dailymotivation",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Fall seven times,\nstand up eight.\"",
                 "title": "일곱 번 넘어지면\n여덟 번\n일어나면 됩니다", "source": "- 일본 속담"},
                {"dur": 7, "style": "dawn", "accent": (231, 76, 60),
                 "quote_en": "\"Strength doesn't come from\nwhat you can do.\nIt comes from overcoming what\nyou thought you couldn't.\"",
                 "title": "진짜 강함은\n못한다고 생각한 것을\n해냈을 때 옵니다", "source": ""},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "실패는 끝이 아닙니다\n다시 시작할\n용기만 있다면",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신은 생각보다\n강한 사람입니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "넘어져도 괜찮습니다.\n\n\"Fall seven times, stand up eight.\"\n\n진짜 강함은 못한다고 생각한 것을 해냈을 때 옵니다.\n실패는 끝이 아닙니다. 다시 시작할 용기만 있다면.\n\n당신은 생각보다 강한 사람입니다.\n\n#동기부여 #명언 #도전 #실패 #성장 #자기계발 #용기 #강함 #직장인 #힘내 #motivation #strength #nevergiveup #resilience #keepgoing",
        },
        {
            "scenes": [
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Your time is limited.\nDon't waste it living\nsomeone else's life.\"",
                 "title": "당신의 시간은\n한정되어 있습니다\n남의 인생을\n살지 마세요", "source": "- Steve Jobs"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The future belongs to those\nwho believe in the beauty\nof their dreams.\"",
                 "title": "꿈의 아름다움을\n믿는 사람에게\n미래가 열립니다", "source": "- Eleanor Roosevelt"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "남들과 비교하지 마세요\n어제의 나와\n비교하세요",
                 "body": "당신만의 속도가 있습니다"},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신의 꿈을\n포기하지 마세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "남의 인생을 살지 마세요.\n\n\"Your time is limited. Don't waste it living someone else's life.\"\n- Steve Jobs\n\n남들과 비교하지 마세요. 어제의 나와 비교하세요.\n당신만의 속도가 있습니다.\n\n#동기부여 #스티브잡스 #명언 #꿈 #자기계발 #나만의속도 #비교 #성장 #직장인 #도전 #motivation #stevejobs #dreams #growthmindset #believeinyourself",
        },
    ],
    "growth": [
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Small daily improvements\nare the key to staggering\nlong-term results.\"",
                 "title": "매일의 작은 개선이\n놀라운 결과를\n만들어냅니다", "source": ""},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "습관이 바뀌면\n인생이 바뀝니다",
                 "body": "아침 5분의 루틴이\n하루 전체를 바꿉니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"We are what we\nrepeatedly do.\nExcellence is not an act\nbut a habit.\"",
                 "title": "탁월함은\n행동이 아니라\n습관입니다", "source": "- Aristotle"},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘부터\n작게 시작하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "매일 1%씩 성장하세요.\n\n\"Small daily improvements are the key to staggering long-term results.\"\n\n습관이 바뀌면 인생이 바뀝니다.\n아침 5분의 루틴이 하루 전체를 바꿉니다.\n\n오늘부터 작게 시작하세요.\n\n#자기계발 #습관 #성장 #아침루틴 #1퍼센트 #아리스토텔레스 #명언 #직장인 #자기관리 #변화 #dailyhabits #growth #selfdevelopment #morningroutine #habits",
        },
        {
            "scenes": [
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The only person you are\ndestined to become\nis the person you decide\nto be.\"",
                 "title": "당신이 될 수 있는\n유일한 사람은\n당신이 되기로\n결심한 사람입니다", "source": "- Ralph W. Emerson"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "독서 10분\n운동 20분\n감사 5분",
                 "body": "이 35분이\n1년 후 당신을\n완전히 바꿉니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Invest in yourself.\nIt pays the best interest.\"",
                 "title": "자기 자신에게\n투자하세요\n그것이 최고의\n이자를 줍니다", "source": "- Benjamin Franklin"},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "성장은 선택입니다\n오늘 선택하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "자기 자신에게 투자하세요.\n\n\"Invest in yourself. It pays the best interest.\"\n- Benjamin Franklin\n\n독서 10분, 운동 20분, 감사 5분.\n이 35분이 1년 후 당신을 완전히 바꿉니다.\n\n성장은 선택입니다. 오늘 선택하세요.\n\n#자기계발 #자기투자 #성장 #독서 #운동 #감사 #벤자민프랭클린 #명언 #습관 #루틴 #selfdevelopment #investinyourself #reading #growth #dailyroutine",
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 프레임 생성
# ═══════════════════════════════════════════════════════════════
def make_frames(scenes, name):
    frames_dir = os.path.join(OUT_DIR, f"frames_{name}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    fnum = 0
    total_dur = sum(s.get("dur", 8) for s in scenes)

    for si, sc in enumerate(scenes):
        dur = sc.get("dur", 8)
        style = sc.get("style", "dark")
        accent = sc.get("accent", (29, 158, 117))
        elapsed = sum(scenes[j].get("dur", 8) for j in range(si))

        for f in range(dur * FPS):
            fp = f / max(dur * FPS, 1)
            tp = (elapsed + dur * fp) / total_dur
            fade = min(1.0, fp * 4)
            if fp > 0.8:
                fade = max(0, (1 - fp) * 5)

            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)

            # 배경
            seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
            if style == "dawn":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(10 + p * 40), int(15 + p * 30), int(35 + p * 45)))
            elif style == "night":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(5 + p * 3), int(5 + p * 5), int(15 + p * 10)))
                random.seed(seed)
                for _ in range(80):
                    x, y2 = random.randint(0, W), random.randint(0, H // 2)
                    br = random.randint(150, 255)
                    d.ellipse([x - 1, y2 - 1, x + 1, y2 + 1], fill=(br, br, br))
            elif style == "golden":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(25 + p * 30), int(15 + p * 18), int(5 + p * 8)))
            elif style == "rain":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(8 + p * 4), int(10 + p * 6), int(18 + p * 10)))
                random.seed(int(fp * 100) + seed)
                for _ in range(30):
                    x = random.randint(0, W)
                    ys = random.randint(0, H - 80)
                    d.line([(x, ys), (x - 3, ys + 60)], fill=(50, 55, 70), width=1)
            else:
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(8 + p * 6), int(10 + p * 8), int(20 + p * 12)))

            # 시네마틱 바
            d.rectangle([0, 0, W, 70], fill=(0, 0, 0))
            d.rectangle([0, H - 70, W, H], fill=(0, 0, 0))

            bc = tuple(int(c * fade) for c in accent)
            d.rectangle([0, 70, W, 73], fill=bc)

            # 브랜드
            d.text((60, 85), "LIGHTHOUSE MEDIA", font=gf(18), fill=tuple(int(c * fade * 0.5) for c in accent))

            # 영어 명언
            qe = sc.get("quote_en", "")
            if qe:
                tc(d, 320, qe, gf_en(26), tuple(int(140 * fade) for _ in range(3)), 6)

            # 구분선
            lw = int(100 * min(1, fp * 3))
            if lw > 0:
                d.rectangle([W // 2 - lw, 490, W // 2 + lw, 492], fill=bc)

            # 한글 제목
            title = sc.get("title", "")
            tc(d, 540, title, gf(52, True), tuple(int(255 * fade) for _ in range(3)), 20)

            # 부제
            body = sc.get("body", "")
            if body:
                tc(d, 880, body, gf(26, False), tuple(int(160 * fade) for _ in range(3)), 10)

            # 출처
            src = sc.get("source", "")
            if src:
                tc(d, H - 220, src, gf(20, False), tuple(int(c * fade * 0.5) for c in accent))

            # 하단 장식
            d.rectangle([W // 2 - 25, H - 140, W // 2 + 25, H - 137], fill=bc)
            tc(d, H - 120, "@lighthouse_media77", gf(14, False), tuple(int(50 * fade) for _ in range(3)))

            # 진행바
            d.rectangle([0, H - 70, int(W * tp), H - 67], fill=bc)

            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    return frames_dir, total_dur, fnum


# ═══════════════════════════════════════════════════════════════
# 영상 인코딩
# ═══════════════════════════════════════════════════════════════
def encode_video(frames_dir, total_dur, bgm_file, output_name):
    vpath = os.path.join(OUT_DIR, f"{output_name}.mp4")
    bgm_path = os.path.join(BGM_DIR, bgm_file)

    cmd = [FFMPEG, "-y",
           "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
           "-i", bgm_path,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k",
           "-filter_complex", f"[1:a]afade=t=in:d=1,afade=t=out:st={max(1, total_dur - 2)}:d=2,volume=0.3[a]",
           "-map", "0:v", "-map", "[a]",
           "-vf", f"scale={W}:{H},fps=30",
           "-t", str(total_dur), "-shortest",
           vpath]

    subprocess.run(cmd, capture_output=True, timeout=120)
    shutil.rmtree(frames_dir, ignore_errors=True)

    return vpath if os.path.exists(vpath) else None


# ═══════════════════════════════════════════════════════════════
# 업로드 (Instagram Reels + Facebook)
# ═══════════════════════════════════════════════════════════════
def upload_ig_reels(vpath, caption):
    # Imgur에 영상 업로드
    with open(vpath, 'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/upload',
                       headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                       data={'video': enc, 'type': 'base64'}, timeout=120)
    vid_url = ir.json().get('data', {}).get('link')
    if not vid_url:
        print("    Imgur upload failed")
        return None

    print(f"    Imgur OK: {vid_url}")

    # 릴스 컨테이너 생성
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
        'video_url': vid_url,
        'media_type': 'REELS',
        'caption': caption,
        'access_token': IG_TOKEN,
    }, timeout=30)
    d = r.json()
    if 'id' not in d:
        print(f"    IG container failed: {d}")
        return None

    container_id = d['id']
    print(f"    IG container: {container_id}")

    # 처리 대기
    for attempt in range(18):  # 최대 3분
        time.sleep(10)
        check = requests.get(
            f'https://graph.facebook.com/v21.0/{container_id}?fields=status_code&access_token={IG_TOKEN}',
            timeout=10)
        status = check.json().get('status_code', '')
        if status == 'FINISHED':
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
                               data={'creation_id': container_id, 'access_token': IG_TOKEN}, timeout=30)
            return r2.json().get('id')
        elif status == 'ERROR':
            print(f"    IG processing error")
            return None
        print(f"    Processing... ({(attempt + 1) * 10}s)")
    return None


def upload_fb_video(vpath, description):
    with open(vpath, 'rb') as f:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/videos',
                          files={'source': (os.path.basename(vpath), f, 'video/mp4')},
                          data={'description': description[:500], 'access_token': FB_TOKEN}, timeout=120)
    return r.json()


# ═══════════════════════════════════════════════════════════════
# 오늘의 릴스 선택 (날짜 기반 결정적 랜덤)
# ═══════════════════════════════════════════════════════════════
def pick_today_reel(category=None):
    today = datetime.now().strftime("%Y-%m-%d")
    categories = list(REEL_POOL.keys())

    if category and category in REEL_POOL:
        cat = category
    else:
        # 날짜 기반으로 카테고리 순환
        day_num = int(datetime.now().strftime("%j"))  # 1~366
        cat = categories[day_num % len(categories)]

    pool = REEL_POOL[cat]
    # 날짜 기반으로 풀 내 선택
    seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
    idx = seed % len(pool)

    return cat, pool[idx], today


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def main():
    category = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("  DAILY INSTAGRAM REELS")
    print("=" * 60)

    cat, reel, today = pick_today_reel(category)
    name = f"daily-{today}-{cat}"

    print(f"\n  Date: {today}")
    print(f"  Category: {cat}")

    # BGM 선택
    bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
    bgm = random.choice(bgm_files)
    print(f"  BGM: {bgm}")

    # 프레임 생성
    print("\n  Generating frames...")
    frames_dir, total_dur, fnum = make_frames(reel["scenes"], name)
    print(f"  {fnum} frames ({total_dur}s)")

    # 영상 인코딩
    print("  Encoding video...")
    vpath = encode_video(frames_dir, total_dur, bgm, name)
    if not vpath:
        print("  ENCODE FAILED!")
        return
    sz = os.path.getsize(vpath) / (1024 * 1024)
    print(f"  Video: {vpath} ({sz:.1f}MB)")

    # Facebook 업로드
    print("\n  Uploading to Facebook...")
    fb = upload_fb_video(vpath, reel["cap"])
    print(f"  FB: {'OK (' + str(fb.get('id', '')) + ')' if 'id' in fb else fb}")
    time.sleep(3)

    # Instagram Reels 업로드
    print("\n  Uploading to Instagram Reels...")
    ig = upload_ig_reels(vpath, reel["cap"])
    print(f"  IG Reels: {'OK (' + str(ig) + ')' if ig else 'Failed or processing'}")

    print(f"\n{'=' * 60}")
    print(f"  DAILY REELS DONE!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
