"""말씀 카드 v5 — 깔끔한 타이포그래피, 핵심 묵상, 성경 본문만"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, re, random, math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
CHURCH_TOKEN = tokens.get('church_page', tokens['instagram'])
CHURCH_IG_ID = tokens.get('church_ig_id', '')
CHURCH_PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"
W, H = 1080, 1350

def ai_call(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 600, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

# === 폰트 ===
def f_title(sz):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def f_body(sz):
    for p in ['C:/Windows/Fonts/HANBatang.ttf','C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def f_sans(sz):
    return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', sz) if os.path.exists('C:/Windows/Fonts/malgunbd.ttf') else ImageFont.load_default()

def f_sans_l(sz):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', sz) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

# === 그리기 유틸 ===
def center_text(d, y, text, font, fill, line_sp=0):
    """가운데 정렬 텍스트. 줄 맞춤 깔끔하게."""
    for ln in text.split("\n"):
        if not ln.strip():
            y += line_sp + 5
            continue
        bb = d.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        d.text(((W - tw) / 2, y), ln, font=font, fill=fill)
        y += th + line_sp
    return y

def shadow_text(d, y, text, font, fill, shadow_fill, line_sp=0):
    """그림자 있는 가운데 정렬 텍스트"""
    for ln in text.split("\n"):
        if not ln.strip():
            y += line_sp + 5
            continue
        bb = d.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (W - tw) / 2
        d.text((x + 1, y + 1), ln, font=font, fill=shadow_fill)
        d.text((x, y), ln, font=font, fill=fill)
        y += th + line_sp
    return y

def bg_light(img, seed=0):
    """밝은 배경 (크림 + 빛 + 텍스처)"""
    d = ImageDraw.Draw(img)
    # 그라디언트
    for row in range(H):
        p = row / H
        d.line([(0, row), (W, row)], fill=(
            int(248 - p * 6), int(245 - p * 8), int(237 - p * 10)))
    # 빛
    for i in range(40):
        r = 150 + i * 8
        d.ellipse([W - 200 - r, -80 - r // 2, W - 200 + r, -80 + r // 2],
                  fill=(255, 250, 240, int(6 * (1 - i / 40))))
    # 텍스처
    random.seed(seed)
    for _ in range(3000):
        x, y2 = random.randint(0, W - 1), random.randint(0, H - 1)
        px = img.getpixel((x, y2))
        v = random.randint(-3, 3)
        img.putpixel((x, y2), tuple(max(0, min(255, c + v)) for c in px))

def bg_dark(img, seed=0):
    """어두운 배경 (네이비 + 빛)"""
    d = ImageDraw.Draw(img)
    for row in range(H):
        p = row / H
        d.line([(0, row), (W, row)], fill=(
            int(30 + p * 10 + math.sin(p * 3.14) * 8),
            int(27 + p * 8 + math.sin(p * 3.14) * 6),
            int(38 + p * 12)))
    # 빛줄기
    for i in range(50):
        r = 100 + i * 7
        d.ellipse([W // 2 - r, -30 - r // 2, W // 2 + r, -30 + r // 2],
                  fill=(200, 180, 140, int(6 * (1 - i / 50))))
    random.seed(seed)
    for _ in range(2000):
        x, y2 = random.randint(0, W - 1), random.randint(0, H - 1)
        px = img.getpixel((x, y2))
        v = random.randint(-2, 2)
        img.putpixel((x, y2), tuple(max(0, min(255, c + v)) for c in px))

def decor_frame(d, light=True):
    """테두리 + 코너"""
    c = (210, 200, 180) if light else (80, 70, 55)
    m = 50
    d.rectangle([m, m, W - m, H - m], outline=c, width=1)
    for cx, cy in [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]:
        d.line([(cx - 10, cy), (cx + 10, cy)], fill=c, width=1)
        d.line([(cx, cy - 10), (cx, cy + 10)], fill=c, width=1)

def decor_cross(d, y, light=True):
    """미니멀 십자가"""
    c = (200, 180, 140) if light else (160, 140, 100)
    cx = W // 2
    d.rectangle([cx - 1, y, cx + 1, y + 30], fill=c)
    d.rectangle([cx - 12, y + 12, cx + 12, y + 14], fill=c)

def decor_dots(d, y, light=True):
    """장식 점 5개"""
    c = (200, 185, 155) if light else (140, 125, 95)
    cx = W // 2
    for off in [-20, -7, 0, 7, 20]:
        d.ellipse([cx + off - 2, y, cx + off + 2, y + 4], fill=c)

def footer(d, page, total, light=True):
    """하단: 동산감리교회 + 페이지"""
    c = (170, 160, 140) if light else (100, 95, 80)
    lc = (200, 185, 155) if light else (80, 70, 55)
    d.rectangle([W // 2 - 25, H - 90, W // 2 + 25, H - 88], fill=lc)
    center_text(d, H - 75, "동산감리교회", f_sans_l(14), c)
    center_text(d, H - 50, f"{page} / {total}", f_sans_l(11), (180, 170, 150) if light else (70, 65, 55))

# === 카드 생성 ===
def card_cover(ref, title, date_kr, day_kr, seed=0):
    img = Image.new('RGB', (W, H), (40, 35, 50))
    bg_dark(img, seed)
    d = ImageDraw.Draw(img)
    decor_frame(d, False)
    decor_cross(d, 100, False)
    center_text(d, 170, f"{date_kr}  {day_kr}요일", f_sans_l(16), (160, 150, 130))
    decor_dots(d, 220, False)
    shadow_text(d, 450, ref, f_title(44), (235, 225, 205), (25, 20, 30), 15)
    y = 560
    d.rectangle([W // 2 - 50, y, W // 2 + 50, y + 1], fill=(180, 160, 120))
    shadow_text(d, y + 35, title, f_title(36), (210, 200, 180), (25, 20, 30), 15)
    footer(d, 1, 8, False)
    return img

def card_verse(ref, text, page, seed=0):
    img = Image.new('RGB', (W, H), (248, 245, 237))
    bg_light(img, seed)
    d = ImageDraw.Draw(img)
    decor_frame(d, True)
    center_text(d, 100, ref, f_sans_l(15), (180, 165, 140))
    d.rectangle([W // 2 - 35, 140, W // 2 + 35, 141], fill=(200, 185, 155))
    # 본문만 (말씀 라벨 없이)
    y = 200
    for ln in text:
        if not ln.strip():
            y += 8
            continue
        y = center_text(d, y, ln, f_body(24), (55, 45, 35), 16)
        if y > H - 130:
            break
    footer(d, page, 8, True)
    return img

def card_meditation(lines, page, seed=0):
    img = Image.new('RGB', (W, H), (30, 27, 38))
    bg_dark(img, seed)
    d = ImageDraw.Draw(img)
    decor_frame(d, False)
    decor_dots(d, 250, False)
    y = 400
    for ln in lines:
        if not ln.strip():
            y += 15
            continue
        y = shadow_text(d, y, ln, f_title(42), (235, 225, 205), (20, 17, 28), 30)
    footer(d, page, 8, False)
    return img

def card_prayer(text, page, seed=0):
    img = Image.new('RGB', (W, H), (28, 25, 32))
    bg_dark(img, seed + 100)
    d = ImageDraw.Draw(img)
    decor_frame(d, False)
    decor_cross(d, 150, False)
    center_text(d, 220, "기 도", f_sans_l(15), (160, 145, 110))
    d.rectangle([W // 2 - 30, 260, W // 2 + 30, 261], fill=(120, 110, 80))
    y = 350
    for ln in text:
        if not ln.strip():
            y += 10
            continue
        y = center_text(d, y, ln, f_body(26), (220, 215, 205), 18)
        if y > H - 130:
            break
    footer(d, page, 8, False)
    return img

def card_closing(ref, date_kr, day_kr, seed=0):
    img = Image.new('RGB', (W, H), (248, 245, 237))
    bg_light(img, seed + 200)
    d = ImageDraw.Draw(img)
    decor_frame(d, True)
    decor_cross(d, 350, True)
    shadow_text(d, 440, ref, f_title(30), (55, 45, 35), (240, 237, 230), 12)
    decor_dots(d, 520, True)
    center_text(d, 570, f"{date_kr}  {day_kr}요일", f_sans_l(16), (170, 155, 135))
    center_text(d, 620, "동산감리교회", f_title(24), (100, 85, 65))
    footer(d, 8, 8, True)
    return img

# === 파싱 ===
def parse(content):
    sec = {"ref": "", "title": "", "verse": "", "meditation": "", "questions": [], "practice": "", "prayer": ""}
    ref = re.search(r'(사무엘하|삼하)\s*\d+[:\s]*\d+[\-\u2013~]*\d*', content)
    if ref: sec["ref"] = ref.group().strip()
    titles = re.findall(r'\*\*(.+?)\*\*', content)
    for t in titles:
        if 3 < len(t) < 30 and not any(k in t for k in ['새번역', '성경', '매일', '오늘', '말씀']):
            sec["title"] = t.strip(); break
    vlines = []
    for l in content.split("\n"):
        ls = l.strip()
        if re.match(r'^[\u00b9\u00b2\u00b3\u2070-\u2079\u00b0]+', ls):
            vlines.append(ls)
    sec["verse"] = "\n".join(vlines)
    med = re.search(r'\*\s*오늘의 묵상.*?\n"?(.+?)"?\s*\n\n(.+?)(?=\*\s*묵상을 위한 질문|\*\s*오늘의 실천|\*\s*오늘의 기도|$)', content, re.DOTALL)
    if med:
        sec["med_title"] = med.group(1).strip().strip('"')
        sec["meditation"] = med.group(2).strip()
    pray = re.search(r'\*\s*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray: sec["prayer"] = pray.group(1).strip()
    return sec

def wrap_lines(text, mc=20):
    result = []
    for ln in text.split("\n"):
        while len(ln) > mc:
            sp = ln[:mc].rfind(' ')
            cut = sp if sp > mc // 2 else mc
            result.append(ln[:cut].strip())
            ln = ln[cut:].strip()
        if ln.strip():
            result.append(ln.strip())
    return result

def upload(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-v5", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    for _ in range(3):
        try:
            with open(path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': enc, 'type': 'base64'})
            url = r.json().get('data', {}).get('link')
            if url: return url
        except: pass
        time.sleep(5)
    return None

def post_ig(urls, caption):
    ids = []
    for u in urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'image_url': u, 'is_carousel_item': 'true', 'access_token': CHURCH_TOKEN})
        if 'id' in r.json(): ids.append(r.json()['id'])
        time.sleep(2)
    if len(ids) < 2: return None
    r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'media_type': 'CAROUSEL', 'children': ','.join(ids), 'caption': caption, 'access_token': CHURCH_TOKEN})
    if 'id' not in r.json(): return None
    time.sleep(8)
    r2 = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media_publish', data={'creation_id': r.json()['id'], 'access_token': CHURCH_TOKEN})
    return r2.json().get('id')

# === MAIN ===
dates = ["2026-04-28"]
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

print("=" * 50)
print("  Bible Cards v5 — Clean & Deep")
print("=" * 50)

for ds in dates:
    dt = datetime.strptime(ds, "%Y-%m-%d")
    dk = dt.strftime("%m/%d")
    dw = WEEKDAYS[dt.weekday()]
    sd = int(ds.replace("-", ""))

    wp = os.path.join(HOME, "Documents", "오늘의말씀", f"{ds}.txt")
    if not os.path.exists(wp):
        print(f"\n[{ds}] SKIP"); continue

    with open(wp, 'r', encoding='utf-8') as f:
        content = f.read()
    sec = parse(content)
    print(f"\n[{ds} ({dw})] {sec['ref']} — {sec['title']}")

    # 성경 본문 나누기 (말씀 라벨 없이 본문만)
    v_lines = wrap_lines(sec['verse'], 20)
    mid = len(v_lines) // 2
    v1 = v_lines[:mid] if v_lines else [""]
    v2 = v_lines[mid:] if len(v_lines) > mid else []

    # AI로 묵상 압축 (깊이 있되 간결하게)
    print("  AI condensing meditation...")
    try:
        condensed = ai_call(
            "다음 묵상을 인스타 카드용으로 압축해줘.\n\n"
            "[제목] " + (sec.get('med_title', '') or sec['title']) + "\n\n"
            "[원본]\n" + sec['meditation'] + "\n\n"
            "[규칙]\n"
            "- 카드 3장으로 나누기\n"
            "- 각 카드에 핵심 2~3줄\n"
            "- 한 줄 최대 10자\n"
            "- 1장: 본문 배경/상황의 핵심\n"
            "- 2장: 우리 삶에의 적용\n"
            "- 3장: 예수님과의 연결 (복음)\n"
            "- JSON: {\"cards\": [\"줄1\\n줄2\\n줄3\", \"줄1\\n줄2\", \"줄1\\n줄2\\n줄3\"]}\n"
            "- 깊이 있되 간결하게. 묵상이 깊어지는 문장으로.\n"
            "- 절대 10자 넘기지 말 것"
        )
        cs = condensed.find("{")
        ce = condensed.rfind("}") + 1
        med_cards = json.loads(condensed[cs:ce]).get("cards", [])
    except Exception as e:
        print(f"  AI fail: {e}")
        med_cards = ["멈출 수 있는 사람이\n진짜 용기 있는\n사람입니다", "우리 삶에도\n멈춰야 할 순간이\n있습니다", "예수님은\n용서로 멈추셨습니다"]

    while len(med_cards) < 3:
        med_cards.append("")

    m1 = med_cards[0].split("\n")
    m2 = med_cards[1].split("\n")
    m3 = med_cards[2].split("\n")

    # 기도문 압축
    prayer_lines = wrap_lines(sec['prayer'][:120], 18) if sec['prayer'] else [""]

    # 카드 8장 생성
    cards = [
        card_cover(sec['ref'], sec.get('med_title', '') or sec['title'], dk, dw, sd),
        card_verse(sec['ref'], v1, 2, sd + 1),
        card_verse(sec['ref'], v2, 3, sd + 2) if v2 else card_meditation(m1, 3, sd + 2),
        card_meditation(m1 if v2 else m2, 4, sd + 3),
        card_meditation(m2 if v2 else m3, 5, sd + 4),
        card_meditation(m3 if v2 else [], 6, sd + 5) if (v2 and m3) else card_prayer(prayer_lines, 6, sd + 5),
        card_prayer(prayer_lines, 7, sd + 6) if v2 and m3 else card_closing(sec['ref'], dk, dw, sd + 6),
        card_closing(sec['ref'], dk, dw, sd + 7),
    ]

    # 빈 카드 제거
    cards = [c for c in cards if c is not None][:8]

    # 업로드
    urls = []
    for i, card in enumerate(cards):
        url = upload(card, f"v5_{ds}_{i + 1}.jpg")
        if url: urls.append(url)
        print(f"  {i + 1}/{len(cards)}: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    caption = (
        f"📖 {sec['ref']}\n"
        f"\"{sec.get('med_title', '') or sec['title']}\"\n\n"
        f"{sec.get('meditation','')[:200]}\n\n"
        f"✦ 오늘의 질문\n{sec.get('questions',[''])[0] if sec.get('questions') else ''}\n\n"
        f"✦ 오늘의 실천\n{sec.get('practice','')[:120]}\n\n"
        f"🙏 오늘의 기도\n{sec.get('prayer','')[:150]}\n\n"
        f"동산감리교회\n@garden___church\n\n"
        f"#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n"
        f"#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n"
        f"#거룩 #순종 #예배 #기독교 #새벽기도 #하나님\n"
        f"#BibleVerse #DailyDevotional #ChurchLife"
    )

    if len(urls) >= 2:
        pid = post_ig(urls, caption)
        print(f"  IG: {'OK — ' + str(pid) if pid else 'FAIL'}")

    if urls and CHURCH_PAGE_ID:
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={
            'url': urls[0], 'message': caption[:500], 'access_token': CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL'}")

    time.sleep(5)

print(f"\n{'=' * 50}")
print("  v5 done!")
print(f"{'=' * 50}")
