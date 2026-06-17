"""자기개발/도전/위로 + 세계 명언 + 영화적 연출 숏츠 5편 제작"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, subprocess, shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HOME = os.path.expanduser("~")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT = os.path.join(HOME, "lighthouse-media", "output", TODAY, "motivation-shorts")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1920
FPS = 2
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size, bold=False):
    p = "C:/Windows/Fonts/times.ttf" if not bold else "C:/Windows/Fonts/timesbd.ttf"
    if not os.path.exists(p): p = "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(draw, y, text, font, fill, W=1080, sp=0):
    for ln in text.split("\n"):
        bb = draw.textbbox((0,0), ln, font=font)
        draw.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

# 영화적 장면 스타일
def make_cinematic_frame(scene, frame_progress, total_progress):
    style = scene.get("style", "dark")

    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)

    if style == "dawn":
        # 새벽 그라디언트
        for row in range(H):
            p = row / H
            r = int(10 + p * 40)
            g = int(15 + p * 30)
            b = int(35 + p * 45)
            d.line([(0,row),(W,row)], fill=(r, g, b))
        # 수평선 빛
        for row in range(H//2 - 80, H//2 + 80):
            p = 1 - abs(row - H//2) / 80
            r = int(180 * p * 0.3)
            g = int(120 * p * 0.3)
            b = int(60 * p * 0.2)
            d.line([(0,row),(W,row)], fill=(r+10, g+15, b+35))

    elif style == "rain":
        # 비 오는 도시
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(8+int(p*4), 10+int(p*6), 18+int(p*10)))
        # 빗줄기
        import random
        random.seed(int(frame_progress * 100))
        for _ in range(40):
            x = random.randint(0, W)
            y_start = random.randint(0, H-100)
            length = random.randint(30, 80)
            d.line([(x, y_start), (x-5, y_start+length)], fill=(60, 65, 80), width=1)

    elif style == "golden":
        # 골든아워
        for row in range(H):
            p = row / H
            r = int(25 + p * 35)
            g = int(15 + p * 20)
            b = int(5 + p * 10)
            d.line([(0,row),(W,row)], fill=(r, g, b))
        # 빛 줄기
        d.ellipse([W//2-300, H//3-200, W//2+300, H//3+200], fill=(50, 35, 15))

    elif style == "night":
        # 별이 빛나는 밤
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(5+int(p*3), 5+int(p*5), 15+int(p*10)))
        import random
        random.seed(42)
        for _ in range(100):
            x = random.randint(0, W)
            y = random.randint(0, H//2)
            brightness = random.randint(100, 255)
            d.ellipse([x-1, y-1, x+1, y+1], fill=(brightness, brightness, brightness))

    elif style == "mountain":
        # 산 실루엣
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(12+int(p*8), 18+int(p*10), 30+int(p*15)))
        # 산
        peaks = [(0,H*0.55), (200,H*0.4), (400,H*0.45), (540,H*0.35), (700,H*0.42), (900,H*0.38), (W,H*0.5)]
        for i in range(len(peaks)-1):
            x1, y1 = peaks[i]
            x2, y2 = peaks[i+1]
            for x in range(int(x1), int(x2)):
                t = (x - x1) / max(x2 - x1, 1)
                y = y1 + t * (y2 - y1)
                d.line([(x, int(y)), (x, H)], fill=(8, 10, 18))

    else:  # dark
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(8+int(p*6), 10+int(p*8), 20+int(p*12)))

    # 시네마틱 레터박스 (상하 검은 바)
    bar_h = 80
    d.rectangle([0, 0, W, bar_h], fill=(0,0,0))
    d.rectangle([0, H-bar_h, W, H], fill=(0,0,0))

    # 페이드 효과
    fade = min(1.0, frame_progress * 4)  # 0.25초 페이드인
    if frame_progress > 0.8:
        fade = max(0, (1 - frame_progress) * 5)  # 0.2초 페이드아웃

    # 명언 (영어) - 위
    quote_en = scene.get("quote_en", "")
    if quote_en:
        en_color = tuple(int(160 * fade) for _ in range(3))
        tc(d, 350, quote_en, gf_en(28), en_color, W, 8)

    # 명언 구분선
    line_color = scene.get("accent", (29, 158, 117))
    lc = tuple(int(c * fade) for c in line_color)
    lw = int(100 * min(1, frame_progress * 3))
    if lw > 0:
        d.rectangle([W//2-lw, 500, W//2+lw, 502], fill=lc)

    # 메인 텍스트 (한글)
    title = scene.get("title", "")
    tc_color = tuple(int(255 * fade) for _ in range(3))
    y = 560
    for ln in title.split("\n"):
        y = tc(d, y, ln, gf(56, True), tc_color, W, 22)

    # 부제/설명
    body = scene.get("body", "")
    body_color = tuple(int(170 * fade) for _ in range(3))
    y += 30
    for ln in body.split("\n"):
        if not ln.strip(): y += 12; continue
        y = tc(d, y, ln, gf(28), body_color, W, 12)

    # 명언 출처
    source = scene.get("source", "")
    if source:
        src_color = tuple(int(c * fade * 0.6) for c in line_color)
        tc(d, H - 250, source, gf(22), src_color, W)

    # 브랜드
    brand_color = tuple(int(c * fade * 0.4) for c in line_color)
    tc(d, H - 160, "LIGHTHOUSE MEDIA", gf(16), brand_color, W)

    # 진행바
    bar_color = tuple(int(c * fade * 0.5) for c in line_color)
    bar_w = int(W * total_progress)
    d.rectangle([0, H-bar_h, bar_w, H-bar_h+3], fill=bar_color)

    return img


def make_video(video_data, filename):
    scenes = video_data["scenes"]
    frames_dir = os.path.join(OUT, f"frames_{filename}")
    os.makedirs(frames_dir, exist_ok=True)

    fnum = 0
    total_dur = sum(s.get("dur", 8) for s in scenes)

    for si, scene in enumerate(scenes):
        dur = scene.get("dur", 8)
        elapsed_before = sum(scenes[j].get("dur", 8) for j in range(si))

        for f in range(dur * FPS):
            fp = f / max(dur * FPS, 1)
            tp = (elapsed_before + dur * fp) / total_dur

            img = make_cinematic_frame(scene, fp, tp)
            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    # ffmpeg
    vpath = os.path.join(OUT, f"{filename}.mp4")
    subprocess.run([FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-vf", f"scale={W}:{H},fps=30", "-t", str(total_dur), vpath],
                   capture_output=True, timeout=120)
    shutil.rmtree(frames_dir, ignore_errors=True)

    if os.path.exists(vpath):
        return vpath
    return None


print("=" * 60)
print("  MOTIVATION SHORTS FACTORY")
print("  Cinematic Style + World Quotes")
print("=" * 60)

# 5편 정의
videos = [
    {
        "name": "never-give-up",
        "title": "포기하지 마세요 #shorts #명언 #동기부여",
        "scenes": [
            {"dur": 7, "style": "rain", "accent": (52,152,219),
             "quote_en": "\"The only way to do great work\nis to love what you do.\"",
             "title": "위대한 일을 하는\n유일한 방법은\n하는 일을 사랑하는 것이다",
             "source": "- Steve Jobs", "body": ""},
            {"dur": 7, "style": "dawn", "accent": (186,117,23),
             "quote_en": "\"It does not matter how slowly you go\nas long as you do not stop.\"",
             "title": "얼마나 천천히 가는지는\n중요하지 않다\n멈추지만 않는다면",
             "source": "- Confucius (공자)", "body": ""},
            {"dur": 7, "style": "mountain", "accent": (29,158,117),
             "quote_en": "\"Fall seven times,\nstand up eight.\"",
             "title": "일곱 번 넘어져도\n여덟 번째 일어서라",
             "source": "- Japanese Proverb (일본 속담)", "body": ""},
            {"dur": 7, "style": "golden", "accent": (186,117,23),
             "quote_en": "\"The darkest hour has\nonly sixty minutes.\"",
             "title": "가장 어두운 시간도\n60분뿐이다",
             "source": "- Morris Mandel", "body": "\n당신은 지금\n그 60분을 지나고 있습니다"},
            {"dur": 7, "style": "dawn", "accent": (29,158,117),
             "quote_en": "", "title": "포기하지 마세요\n\n당신의 새벽은\n반드시 옵니다",
             "source": "-Lighthouse Media", "body": "\nLighthouse Media\n@lighthouse_media77"},
        ],
    },
    {
        "name": "you-are-enough",
        "title": "당신은 충분합니다 #shorts #위로 #힐링",
        "scenes": [
            {"dur": 8, "style": "night", "accent": (155,89,182),
             "quote_en": "\"You are enough\njust as you are.\"",
             "title": "지금 그대로의\n당신으로 충분합니다",
             "source": "- Meghan Markle", "body": ""},
            {"dur": 7, "style": "rain", "accent": (52,152,219),
             "quote_en": "\"You don't have to be perfect\nto be amazing.\"",
             "title": "완벽하지 않아도\n놀라운 사람이 될 수 있습니다",
             "source": "", "body": ""},
            {"dur": 8, "style": "golden", "accent": (186,117,23),
             "quote_en": "\"Be yourself;\neveryone else is already taken.\"",
             "title": "당신 자신이 되세요\n다른 사람은\n이미 다 있으니까요",
             "source": "- Oscar Wilde", "body": ""},
            {"dur": 7, "style": "dawn", "accent": (29,158,117),
             "quote_en": "", "title": "오늘 하루도\n충분히 잘 살았습니다\n\n수고했어요",
             "source": "-Lighthouse Media", "body": "\nLighthouse Media\n@lighthouse_media77"},
        ],
    },
    {
        "name": "morning-motivation",
        "title": "아침에 듣는 동기부여 #shorts #아침 #동기부여",
        "scenes": [
            {"dur": 6, "style": "dawn", "accent": (186,117,23),
             "quote_en": "\"Every morning brings\nnew potential.\"",
             "title": "매일 아침은\n새로운 가능성을\n가져옵니다",
             "source": "", "body": ""},
            {"dur": 7, "style": "golden", "accent": (29,158,117),
             "quote_en": "\"The secret of getting ahead\nis getting started.\"",
             "title": "앞서가는 비밀은\n시작하는 것입니다",
             "source": "- Mark Twain", "body": ""},
            {"dur": 7, "style": "mountain", "accent": (52,152,219),
             "quote_en": "\"Believe you can\nand you're halfway there.\"",
             "title": "할 수 있다고 믿으면\n이미 반은 온 것입니다",
             "source": "- Theodore Roosevelt", "body": ""},
            {"dur": 7, "style": "dawn", "accent": (186,117,23),
             "quote_en": "\"Today is a good day\nto have a good day.\"",
             "title": "오늘은\n좋은 하루를 보내기에\n좋은 날입니다",
             "source": "", "body": "\n지금 이 순간부터\n시작하세요"},
            {"dur": 5, "style": "golden", "accent": (29,158,117),
             "quote_en": "", "title": "좋은 아침\n오늘도 파이팅!",
             "source": "-Lighthouse Media", "body": "\n@lighthouse_media77"},
        ],
    },
    {
        "name": "courage-to-change",
        "title": "변화의 용기 #shorts #도전 #성장",
        "scenes": [
            {"dur": 7, "style": "mountain", "accent": (231,76,60),
             "quote_en": "\"Life begins at the end\nof your comfort zone.\"",
             "title": "인생은\n당신의 안전지대가\n끝나는 곳에서\n시작됩니다",
             "source": "- Neale Donald Walsch", "body": ""},
            {"dur": 7, "style": "rain", "accent": (52,152,219),
             "quote_en": "\"The only impossible journey\nis the one you never begin.\"",
             "title": "유일하게 불가능한 여행은\n시작하지 않는\n여행입니다",
             "source": "- Tony Robbins", "body": ""},
            {"dur": 7, "style": "golden", "accent": (186,117,23),
             "quote_en": "\"A year from now you may wish\nyou had started today.\"",
             "title": "1년 뒤에 당신은\n오늘 시작했으면\n좋았을 거라\n생각할 것입니다",
             "source": "- Karen Lamb", "body": ""},
            {"dur": 7, "style": "dawn", "accent": (29,158,117),
             "quote_en": "", "title": "변화는\n두려운 게 아니라\n성장하는 겁니다\n\n도전하세요",
             "source": "-Lighthouse Media", "body": "\nLighthouse Media\n@lighthouse_media77"},
        ],
    },
    {
        "name": "heal-your-heart",
        "title": "지친 마음에 전하는 위로 #shorts #힐링 #위로",
        "scenes": [
            {"dur": 7, "style": "night", "accent": (155,89,182),
             "quote_en": "\"The wound is the place\nwhere the Light enters you.\"",
             "title": "상처는\n빛이 당신에게\n들어오는 곳입니다",
             "source": "- Rumi (루미)", "body": ""},
            {"dur": 7, "style": "rain", "accent": (52,152,219),
             "quote_en": "\"After the rain,\nthe sun will reappear.\"",
             "title": "비가 온 뒤에\n태양은 다시 나타납니다",
             "source": "", "body": "\n지금 비가 오고 있다면\n곧 그칠 겁니다"},
            {"dur": 7, "style": "golden", "accent": (186,117,23),
             "quote_en": "\"Stars can't shine\nwithout darkness.\"",
             "title": "어둠이 없으면\n별은 빛날 수 없습니다",
             "source": "", "body": "\n당신의 어둠은\n빛나기 위한 과정입니다"},
            {"dur": 7, "style": "dawn", "accent": (29,158,117),
             "quote_en": "\"This too shall pass.\"",
             "title": "이것 또한\n지나가리라",
             "source": "- Persian Proverb (페르시아 속담)", "body": ""},
            {"dur": 5, "style": "golden", "accent": (29,158,117),
             "quote_en": "", "title": "당신의 마음에\n평안이 깃들기를",
             "source": "-Lighthouse Media", "body": "\nLighthouse Media\n@lighthouse_media77"},
        ],
    },
]

for i, v in enumerate(videos):
    print(f"\n[{i+1}/5] {v['name']}")
    vpath = make_video(v, v['name'])
    if vpath:
        sz = os.path.getsize(vpath) / (1024*1024)
        print(f"  OK! {sz:.1f}MB")
    else:
        print(f"  FAIL")

# 업로드 대기 목록에 추가
pending = os.path.join(OUT, "pending-uploads.json")
with open(pending, 'w', encoding='utf-8') as f:
    json.dump([{"name": v["name"], "title": v["title"], "path": os.path.join(OUT, f"{v['name']}.mp4"),
                "category": "motivation"} for v in videos], f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"  5 cinematic motivation shorts created!")
print(f"  Location: {OUT}")
print(f"  (Upload when YouTube quota resets)")
print(f"{'='*60}")
