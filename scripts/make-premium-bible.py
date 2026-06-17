"""고퀄리티 말씀 카드 - 감성 디자인 + 음악 영상"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, re, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
CHURCH_TOKEN = tokens.get('church_page', tokens['instagram'])
CHURCH_IG_ID = tokens.get('church_ig_id', '')
CHURCH_PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"
BGM_DIR = os.path.join(HOME, "lighthouse-media", "assets", "bgm")
_bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
BGM = os.path.join(BGM_DIR, random.choice(_bgm_files))
print(f"  BGM selected: {os.path.basename(BGM)}")

W, H = 1080, 1350
FPS = 2

# === 폰트 ===
def font_title(size):
    for p in ["C:/Windows/Fonts/HANBatangB.ttf", "C:/Windows/Fonts/batang.ttc", "C:/Windows/Fonts/malgunbd.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def font_body(size):
    for p in ["C:/Windows/Fonts/HANBatang.ttf", "C:/Windows/Fonts/batang.ttc", "C:/Windows/Fonts/malgun.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def font_sans(size):
    return ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", size) if os.path.exists("C:/Windows/Fonts/malgun.ttf") else ImageFont.load_default()

def font_sans_b(size):
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", size) if os.path.exists("C:/Windows/Fonts/malgunbd.ttf") else ImageFont.load_default()

# === 색상 팔레트 ===
IVORY = (248, 245, 237)
WARM_WHITE = (255, 252, 245)
DEEP_BROWN = (62, 48, 38)
MED_BROWN = (120, 95, 72)
LIGHT_BROWN = (180, 160, 135)
GOLD_DARK = (160, 125, 55)
GOLD_LIGHT = (200, 170, 90)
SAGE = (120, 140, 110)
DARK_BG = (28, 25, 32)

def centered(d, y, text, font, fill, spacing=0):
    for ln in text.split("\n"):
        if not ln.strip():
            y += spacing + 5
            continue
        bb = d.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        d.text(((W - tw) / 2, y), ln, font=font, fill=fill)
        y += bb[3] - bb[1] + spacing
    return y

def wrap(text, mc=22):
    result = []
    for line in text.split("\n"):
        while len(line) > mc:
            # 띄어쓰기 기준 자르기
            cut = mc
            sp = line[:mc].rfind(' ')
            if sp > mc // 2:
                cut = sp
            result.append(line[:cut].strip())
            line = line[cut:].strip()
        result.append(line)
    return "\n".join(result)

def grain(d, w, h, bg, intensity=4):
    random.seed(42)
    for _ in range(4000):
        x, y = random.randint(0, w-1), random.randint(0, h-1)
        v = random.randint(-intensity, intensity)
        c = tuple(max(0, min(255, bg[i] + v)) for i in range(3))
        d.point((x, y), fill=c)

def ornament_cross(d, cx, cy, size=20, color=GOLD_DARK):
    d.rectangle([cx-1, cy-size, cx+1, cy+size], fill=color)
    d.rectangle([cx-size//2, cy-1, cx+size//2, cy+1], fill=color)

def ornament_line(d, y, color=GOLD_DARK, width=80):
    cx = W // 2
    d.rectangle([cx - width, y, cx + width, y + 1], fill=color)

def ornament_dots(d, y, color=GOLD_LIGHT):
    cx = W // 2
    for offset in [-30, -15, 0, 15, 30]:
        d.ellipse([cx + offset - 2, y - 2, cx + offset + 2, y + 2], fill=color)

# === 카드 생성 ===
def make_cover(ref, title, date_kr, day_kr):
    img = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(img)
    grain(d, W, H, IVORY)

    # 상단 장식 라인
    d.rectangle([0, 0, W, 3], fill=GOLD_DARK)
    d.rectangle([100, 60, W-100, 61], fill=(*GOLD_LIGHT, 60))

    # 십자가
    ornament_cross(d, W//2, 120, 25, GOLD_DARK)

    # 날짜
    centered(d, 180, f"{date_kr}  {day_kr}요일", font_sans(16), LIGHT_BROWN)

    # "오늘의 말씀"
    centered(d, 350, "오늘의 말씀", font_sans(20), MED_BROWN, 15)

    # 장식 점
    ornament_dots(d, 400, GOLD_LIGHT)

    # 성경 구절
    y = 440
    y = centered(d, y, ref, font_title(34), DEEP_BROWN, 12)

    # 구분선
    y += 25
    ornament_line(d, y, GOLD_DARK, 60)

    # 묵상 제목
    y += 35
    title_wrapped = wrap(title, 16)
    y = centered(d, y, title_wrapped, font_title(28), MED_BROWN, 10)

    # 하단 장식
    d.rectangle([100, H-100, W-100, H-99], fill=(*GOLD_LIGHT, 60))
    centered(d, H-80, "동산감리교회", font_sans(16), LIGHT_BROWN)

    # 페이지
    centered(d, H-45, "1 / 8", font_sans(12), (*LIGHT_BROWN, 120))

    return img

def make_verse(ref, text, page):
    img = Image.new("RGB", (W, H), WARM_WHITE)
    d = ImageDraw.Draw(img)
    grain(d, W, H, WARM_WHITE, 3)

    d.rectangle([0, 0, W, 2], fill=GOLD_DARK)

    # 구절 참조
    y = 100
    y = centered(d, y, ref, font_sans(15), GOLD_DARK, 15)

    # 장식
    ornament_line(d, y + 5, GOLD_LIGHT, 40)

    # 여는 따옴표
    d.text((100, y + 20), "\u201C", font=font_title(60), fill=(*GOLD_LIGHT, 100))

    # 본문
    y += 60
    text_wrapped = wrap(text, 24)
    for ln in text_wrapped.split("\n")[:18]:
        if not ln.strip():
            y += 8
            continue
        y = centered(d, y, ln, font_body(21), DEEP_BROWN, 11)

    # 닫는 따옴표
    bb = d.textbbox((0, 0), "\u201D", font=font_title(60))
    d.text(((W - (bb[2]-bb[0])) / 2, y + 5), "\u201D", font=font_title(60), fill=(*GOLD_LIGHT, 100))

    # 하단
    ornament_line(d, H - 80, GOLD_LIGHT, 30)
    centered(d, H - 55, f"{page} / 8", font_sans(12), LIGHT_BROWN)

    return img

def make_meditation(title, body, page):
    img = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(img)
    grain(d, W, H, IVORY)

    d.rectangle([0, 0, W, 2], fill=SAGE)

    y = 120
    centered(d, y, "묵 상", font_sans(14), SAGE, 12)

    y = 170
    if title:
        title_w = wrap(title, 18)
        y = centered(d, y, title_w, font_title(28), DEEP_BROWN, 12)
        y += 15
        ornament_dots(d, y, SAGE)
        y += 20

    body_w = wrap(body, 26)
    for ln in body_w.split("\n")[:24]:
        if not ln.strip():
            y += 8
            continue
        y = centered(d, y, ln, font_body(19), MED_BROWN, 10)

    ornament_line(d, H - 80, SAGE, 30)
    centered(d, H - 55, f"{page} / 8", font_sans(12), LIGHT_BROWN)

    return img

def make_question(questions, page):
    img = Image.new("RGB", (W, H), WARM_WHITE)
    d = ImageDraw.Draw(img)
    grain(d, W, H, WARM_WHITE, 3)

    d.rectangle([0, 0, W, 2], fill=GOLD_DARK)

    y = 250
    centered(d, y, "묵상을 위한 질문", font_sans(15), GOLD_DARK, 20)

    y = 310
    ornament_dots(d, y, GOLD_LIGHT)
    y += 35

    for i, q in enumerate(questions[:2]):
        q_w = wrap(q, 22)
        for ln in q_w.split("\n"):
            y = centered(d, y, ln, font_body(22), DEEP_BROWN, 12)
        y += 35

    y += 10
    centered(d, y, "* 하나만 떠올려도 충분합니다.", font_sans(15), LIGHT_BROWN)

    ornament_line(d, H - 80, GOLD_LIGHT, 30)
    centered(d, H - 55, f"{page} / 8", font_sans(12), LIGHT_BROWN)

    return img

def make_practice(text, page):
    img = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(img)
    grain(d, W, H, IVORY)

    d.rectangle([0, 0, W, 2], fill=SAGE)

    y = 280
    centered(d, y, "오늘의 실천", font_sans(15), SAGE, 20)

    y = 340
    ornament_line(d, y, SAGE, 40)
    y += 30

    text_w = wrap(text, 24)
    for ln in text_w.split("\n")[:12]:
        if not ln.strip():
            y += 10
            continue
        y = centered(d, y, ln, font_body(22), DEEP_BROWN, 13)

    ornament_line(d, H - 80, SAGE, 30)
    centered(d, H - 55, f"{page} / 8", font_sans(12), LIGHT_BROWN)

    return img

def make_prayer(text, page):
    img = Image.new("RGB", (W, H), DARK_BG)
    d = ImageDraw.Draw(img)
    grain(d, W, H, DARK_BG, 3)

    d.rectangle([0, 0, W, 2], fill=GOLD_DARK)
    ornament_cross(d, W//2, 100, 20, GOLD_DARK)

    y = 170
    centered(d, y, "오늘의 기도", font_sans(14), GOLD_LIGHT, 20)

    y = 230
    ornament_line(d, y, GOLD_DARK, 40)
    y += 30

    text_w = wrap(text, 24)
    for ln in text_w.split("\n")[:20]:
        if not ln.strip():
            y += 8
            continue
        y = centered(d, y, ln, font_body(20), (225, 220, 210), 11)

    ornament_line(d, H - 80, GOLD_DARK, 30)
    centered(d, H - 55, f"{page} / 8", font_sans(12), (100, 95, 85))

    return img

def make_closing(ref, date_kr, day_kr, page):
    img = Image.new("RGB", (W, H), IVORY)
    d = ImageDraw.Draw(img)
    grain(d, W, H, IVORY)

    d.rectangle([0, 0, W, 2], fill=GOLD_DARK)
    ornament_cross(d, W//2, 350, 30, GOLD_DARK)

    y = 430
    y = centered(d, y, ref, font_title(26), DEEP_BROWN, 14)
    y += 20
    ornament_dots(d, y, GOLD_DARK)
    y += 30
    centered(d, y, f"{date_kr} {day_kr}요일", font_sans(16), LIGHT_BROWN, 15)
    y += 40
    centered(d, y, "동산감리교회", font_title(24), MED_BROWN, 10)
    centered(d, y + 35, "@garden___church", font_sans(15), LIGHT_BROWN)

    d.rectangle([100, H - 100, W - 100, H - 99], fill=(*GOLD_LIGHT, 60))
    centered(d, H - 55, f"{page} / 8", font_sans(12), LIGHT_BROWN)

    return img

def parse_word(content):
    sec = {"ref":"","title":"","verse":"","med_title":"","meditation":"","questions":[],"practice":"","prayer":""}
    ref = re.search(r'사무엘하\s*\d+[:\s]*\d+[\-\u2013~]*\d*', content)
    if ref: sec["ref"] = ref.group().strip()
    titles = re.findall(r'\*\*(.+?)\*\*', content)
    for t in titles:
        if len(t) > 3 and len(t) < 30 and '새번역' not in t and '성경' not in t and '매일' not in t and '오늘' not in t:
            sec["title"] = t.strip()
            break
    vlines = []
    for line in content.split("\n"):
        l = line.strip()
        if re.match(r'^[\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079]+', l):
            vlines.append(l)
    sec["verse"] = "\n".join(vlines)
    med = re.search(r'\*\s*오늘의 묵상\s*\n"?(.+?)"?\s*\n\n(.+?)(?=\*\s*묵상을 위한 질문|\*\s*오늘의 실천|\*\s*오늘의 기도|$)', content, re.DOTALL)
    if med:
        sec["med_title"] = med.group(1).strip().strip('"')
        sec["meditation"] = med.group(2).strip()
    q = re.search(r'\*\s*묵상을 위한 질문\s*\n(.+?)(?=\*\s*오늘의 실천|\*\s*오늘의 기도|\u203b|$)', content, re.DOTALL)
    if q:
        for line in q.group(1).strip().split("\n"):
            l = line.strip().lstrip('-').strip()
            if l and not l.startswith('\u203b') and len(l) > 5:
                sec["questions"].append(l)
    pr = re.search(r'\*\s*오늘의 실천\s*\n(.+?)(?=\*\s*오늘의 기도|$)', content, re.DOTALL)
    if pr: sec["practice"] = pr.group(1).strip()
    pray = re.search(r'\*\s*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray: sec["prayer"] = pray.group(1).strip()
    return sec

def upload_imgur(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-premium", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    for attempt in range(3):
        try:
            with open(path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': enc, 'type': 'base64'})
            url = r.json().get('data', {}).get('link')
            if url:
                return url
        except:
            pass
        time.sleep(5)
    return None

def post_carousel(urls, caption):
    ids = []
    for u in urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'image_url': u, 'is_carousel_item': 'true', 'access_token': CHURCH_TOKEN})
        if 'id' in r.json():
            ids.append(r.json()['id'])
        time.sleep(2)
    if len(ids) < 2:
        return None
    r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'media_type': 'CAROUSEL', 'children': ','.join(ids), 'caption': caption, 'access_token': CHURCH_TOKEN})
    if 'id' not in r.json():
        return None
    time.sleep(8)
    r2 = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media_publish', data={'creation_id': r.json()['id'], 'access_token': CHURCH_TOKEN})
    return r2.json().get('id')

# === MAIN ===
dates = ["2026-04-23", "2026-04-24", "2026-04-25", "2026-04-26"]
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

print("=" * 50)
print("  Premium Bible Cards")
print("=" * 50)

for date_str in dates:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_kr = dt.strftime("%m/%d")
    day_kr = WEEKDAYS[dt.weekday()]

    wp = os.path.join(HOME, "Documents", "\uc624\ub298\uc758\ub9d0\uc500", f"{date_str}.txt")
    if not os.path.exists(wp):
        print(f"\n[{date_str}] SKIP (no file)")
        continue

    with open(wp, 'r', encoding='utf-8') as f:
        content = f.read()
    sec = parse_word(content)
    print(f"\n[{date_str} ({day_kr})] {sec['ref']}")

    verse = sec['verse']
    med = sec['meditation']

    cards = [
        make_cover(sec['ref'], sec['med_title'] or sec['title'], date_kr, day_kr),
        make_verse(sec['ref'], verse[:350] if verse else content[200:550], 2),
        make_verse(sec['ref'], verse[350:] if len(verse) > 350 else verse, 3) if len(verse) > 350 else make_meditation(sec['med_title'], med[:400], 3),
        make_meditation(sec['med_title'] if len(verse) > 350 else "", med[:400] if len(verse) > 350 else med[400:800], 4),
        make_meditation("", med[400:800] if len(verse) > 350 else med[800:], 5) if len(med) > 400 else make_question(sec['questions'], 5),
        make_question(sec['questions'], 6),
        make_practice(sec['practice'], 7),
        make_prayer(sec['prayer'], 8) if sec['prayer'] else make_closing(sec['ref'], date_kr, day_kr, 8),
    ]

    urls = []
    for i, card in enumerate(cards):
        url = upload_imgur(card, f"premium_{date_str}_{i+1}.jpg")
        if url:
            urls.append(url)
        print(f"  {i+1}/8: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    caption = f"\ud83d\udcd6 {sec['ref']}\n\"{sec['med_title']}\"\n\n{sec['meditation'][:200]}\n\n\u2726 \uc624\ub298\uc758 \uc9c8\ubb38\n{sec.get('questions',[''])[0] if sec.get('questions') else ''}\n\n\u2726 \uc624\ub298\uc758 \uc2e4\ucc9c\n{sec.get('practice','')[:120]}\n\n\ud83d\ude4f \uc624\ub298\uc758 \uae30\ub3c4\n{sec.get('prayer','')[:150]}\n\n\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c\n@garden___church\n\n#\uc624\ub298\uc758\ub9d0\uc500 #\uc0ac\ubb34\uc5d8\ud558 #\uc131\uacbd\ub9d0\uc500 #\ubb35\uc0c1 #\uae30\ub3c4 #\uad50\ud68c\n#\ub9d0\uc500\uce74\ub4dc #\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c #\ub9e4\uc77c\ubb35\uc0c1 #\uc131\uacbd #\uc740\ud61c\n#\uac70\ub8e9 #\uc21c\uc885 #\uc608\ubc30 #\uae30\ub3c5\uad50 #\uc0c8\ubcbd\uae30\ub3c4 #\ud558\ub098\ub2d8\n#BibleVerse #DailyDevotional #ChurchLife"

    if len(urls) >= 2:
        pid = post_carousel(urls, caption)
        print(f"  IG: {'OK' if pid else 'FAIL'}")
    time.sleep(3)

    if urls and CHURCH_PAGE_ID:
        fb_msg = f"\ud83d\udcd6 {sec['ref']}\n\"{sec['med_title']}\"\n\n{sec['meditation'][:300]}\n\n\u2726 \uc624\ub298\uc758 \uc2e4\ucc9c\n{sec.get('practice','')[:150]}\n\n\ud83d\ude4f \uc624\ub298\uc758 \uae30\ub3c4\n{sec.get('prayer','')[:200]}\n\n\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c\n@garden___church\n\n#\uc624\ub298\uc758\ub9d0\uc500 #\uc0ac\ubb34\uc5d8\ud558 #\uc131\uacbd\ub9d0\uc500 #\ubb35\uc0c1 #\uae30\ub3c4 #\uad50\ud68c\n#BibleVerse #DailyDevotional #ChurchLife"
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={'url': urls[0], 'message': fb_msg, 'access_token': CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL'}")
    time.sleep(5)

print(f"\n{'=' * 50}")
print("  Premium cards done!")
print(f"{'=' * 50}")
