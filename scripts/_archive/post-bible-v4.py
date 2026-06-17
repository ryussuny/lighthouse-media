"""말씀 카드 v4 — Premium Design with gradients, bokeh, grain, frames"""
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

def claude(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 500, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

W, H = 1080, 1350

# ── Fonts ──
def ft(size):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf', 'C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def ft_l(size):
    for p in ['C:/Windows/Fonts/HANBatang.ttf', 'C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def ft_s(size):
    for p in ['C:/Windows/Fonts/malgunbd.ttf', 'C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

# ── Design Effects ──
def gradient_bg(img, c1, c2, direction='vertical'):
    """Fill image with a smooth gradient from c1 to c2."""
    d = ImageDraw.Draw(img)
    if direction == 'vertical':
        for y in range(H):
            t = y / H
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            d.line([(0, y), (W, y)], fill=(r, g, b))

def glow(img, cx, cy, radius, color, opacity=30):
    """Draw a soft elliptical glow (bokeh light effect)."""
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(radius, 0, -3):
        a = int(opacity * (i / radius))
        od.ellipse([cx - i, cy - i, cx + i, cy + int(i * 0.7)],
                   fill=(color[0], color[1], color[2], a))
    img.paste(Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB'))

def grain(img, seed=42, intensity=8):
    """Apply fine grain texture."""
    rng = random.Random(seed)
    pixels = img.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            v = rng.randint(-intensity, intensity)
            r, g, b = pixels[x, y]
            pixels[x, y] = (max(0, min(255, r + v)),
                            max(0, min(255, g + v)),
                            max(0, min(255, b + v)))

def frame(d, margin=40, color=(180, 160, 120), width=1):
    """Draw a thin rectangular frame inside margins."""
    m = margin
    d.rectangle([m, m, W - m, H - m], outline=color, width=width)

def corners(d, margin=40, size=12, color=(180, 160, 120)):
    """Draw small cross-line decorations at frame corners."""
    m = margin
    pts = [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]
    for (cx, cy) in pts:
        d.line([(cx - size, cy), (cx + size, cy)], fill=color, width=1)
        d.line([(cx, cy - size), (cx, cy + size)], fill=color, width=1)

def text_shadow(d, pos, text, font, fill, shadow_color=None, offset=1):
    """Draw text with shadow (draw twice: shadow offset, then main)."""
    x, y = pos
    if shadow_color is None:
        shadow_color = tuple(max(0, c - 40) for c in fill)
    d.text((x + offset, y + offset), text, font=font, fill=shadow_color)
    d.text((x, y), text, font=font, fill=fill)

def ctr(d, y, text, font, fill, sp=0, shadow=False, shadow_color=None):
    """Center text, optional shadow."""
    for ln in text.split("\n"):
        if not ln.strip():
            y += sp + 5
            continue
        bb = d.textbbox((0, 0), ln, font=font)
        tw = bb[2] - bb[0]
        x = (W - tw) / 2
        if shadow:
            text_shadow(d, (x, y), ln, font, fill, shadow_color)
        else:
            d.text((x, y), ln, font=font, fill=fill)
        y += bb[3] - bb[1] + sp
    return y

def dots(d, y, color=(220, 200, 150)):
    """5 decorative dots in a row."""
    cx = W // 2
    for off in [-24, -10, 0, 10, 24]:
        d.ellipse([cx + off - 3, y, cx + off + 3, y + 6], fill=color)

def cross_symbol(d, y, color=(220, 200, 150)):
    cx = W // 2
    d.rectangle([cx - 1, y, cx + 1, y + 40], fill=color)
    d.rectangle([cx - 16, y + 17, cx + 16, y + 19], fill=color)

def wrap(text, mc=14):
    result = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        while len(ln) > mc:
            sp = ln[:mc].rfind(' ')
            cut = sp if sp > mc // 3 else mc
            result.append(ln[:cut].strip())
            ln = ln[cut:].strip()
        if ln.strip():
            result.append(ln)
    return result

def footer(d, page, color=(120, 110, 95)):
    """Footer: only '동산감리교회' + page number."""
    f = ft_s(15)
    bb = d.textbbox((0, 0), "동산감리교회", font=f)
    d.text(((W - (bb[2] - bb[0])) / 2, H - 85), "동산감리교회", font=f, fill=color)
    pf = ft_s(12)
    pt = f"{page} / 8"
    bb2 = d.textbbox((0, 0), pt, font=pf)
    d.text(((W - (bb2[2] - bb2[0])) / 2, H - 55), pt, font=pf, fill=color)

def footer_dark(d, page):
    footer(d, page, color=(90, 85, 70))

def footer_light(d, page):
    footer(d, page, color=(160, 150, 130))


# ══════════════════════════════════════════
#  CARD 1: COVER (dark)
# ══════════════════════════════════════════
def card_cover(ref, title, date_kr, day_kr, seed=1):
    img = Image.new('RGB', (W, H), (40, 35, 50))
    gradient_bg(img, (40, 35, 50), (65, 55, 65))
    glow(img, W // 2, 150, 400, (255, 230, 180), opacity=18)
    glow(img, W // 3, 200, 200, (200, 180, 130), opacity=10)
    grain(img, seed=seed, intensity=6)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(120, 105, 75, 80), width=1)
    corners(d, margin=45, size=14, color=(180, 160, 120))

    ctr(d, 120, f'{date_kr}  {day_kr}요일', ft_s(18), (170, 160, 135), shadow=True, shadow_color=(30, 25, 40))
    cross_symbol(d, 200, (220, 200, 150))
    ctr(d, 310, '오늘의 말씀', ft_s(22), (200, 185, 150), shadow=True, shadow_color=(30, 25, 40))

    # Reference (large golden)
    ctr(d, 440, ref, ft(48), (220, 200, 150), sp=10, shadow=True, shadow_color=(30, 25, 40))

    # Dotted divider
    dots(d, 550, (200, 180, 140))

    # Title
    y = 630
    for ln in wrap(title, 12):
        y = ctr(d, y, ln, ft(38), (240, 230, 210), sp=20, shadow=True, shadow_color=(30, 25, 40))

    footer_dark(d, 1)
    return img


# ══════════════════════════════════════════
#  CARD 2: VERSE1 (light)
# ══════════════════════════════════════════
def card_verse(ref, lines, page, seed=2):
    img = Image.new('RGB', (W, H), (248, 245, 237))
    gradient_bg(img, (248, 245, 237), (244, 240, 230))
    # Soft light spots
    glow(img, W // 3, H // 4, 300, (255, 250, 230), opacity=12)
    glow(img, int(W * 0.7), int(H * 0.6), 250, (255, 245, 220), opacity=8)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(200, 185, 160), width=1)
    corners(d, margin=45, size=12, color=(190, 175, 150))

    ctr(d, 100, ref, ft_s(18), (150, 135, 115))

    # Large decorative quote marks
    d.text((100, 180), '「', font=ft(80), fill=(220, 210, 190))

    y = 310
    for ln in lines[:7]:
        y = ctr(d, y, ln, ft(34), (55, 45, 35), sp=24, shadow=True, shadow_color=(230, 225, 215))

    # Closing quote
    bb = d.textbbox((0, 0), '」', font=ft(80))
    d.text(((W - (bb[2] - bb[0])) / 2, y + 15), '」', font=ft(80), fill=(220, 210, 190))

    footer_light(d, page)
    return img


# ══════════════════════════════════════════
#  CARD 4: MEDITATION (dark)
# ══════════════════════════════════════════
def card_meditation(lines, page, subtitle="", seed=4):
    img = Image.new('RGB', (W, H), (25, 22, 32))
    gradient_bg(img, (25, 22, 32), (35, 30, 40))
    # Top light rays
    glow(img, W // 2, 0, 500, (200, 180, 130), opacity=15)
    glow(img, int(W * 0.3), 100, 250, (180, 160, 110), opacity=8)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(90, 80, 60), width=1)
    corners(d, margin=45, size=12, color=(140, 125, 90))

    ctr(d, 110, '묵 상', ft_s(18), (180, 165, 130), shadow=True, shadow_color=(15, 12, 22))

    # Golden dots
    dots(d, 165, (180, 165, 130))

    if subtitle:
        ctr(d, 220, subtitle, ft_s(16), (140, 130, 100), shadow=True, shadow_color=(15, 12, 22))

    if subtitle:
        ctr(d, 220, subtitle, ft_s(16), (140, 130, 100), shadow=True, shadow_color=(15, 12, 22))

    y = 380
    for ln in lines[:5]:
        y = ctr(d, y, ln, ft(44), (235, 225, 205), sp=35, shadow=True, shadow_color=(15, 12, 22))

    footer_dark(d, page)
    return img


# ══════════════════════════════════════════
#  CARD 5: MEDITATION2 (dark variant)
# ══════════════════════════════════════════
def card_meditation2(lines, page, seed=5):
    img = Image.new('RGB', (W, H), (30, 25, 35))
    gradient_bg(img, (30, 25, 35), (40, 35, 45))
    glow(img, int(W * 0.6), int(H * 0.3), 350, (190, 170, 120), opacity=12)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(85, 75, 55), width=1)
    corners(d, margin=45, size=12, color=(130, 115, 85))

    dots(d, 200, (160, 145, 110))

    y = 380
    for ln in lines[:5]:
        y = ctr(d, y, ln, ft(44), (230, 220, 200), sp=35, shadow=True, shadow_color=(15, 12, 22))

    footer_dark(d, page)
    return img


# ══════════════════════════════════════════
#  CARD 6: QUESTION (light warm)
# ══════════════════════════════════════════
def card_question(q1, q2, page, seed=6):
    img = Image.new('RGB', (W, H), (250, 247, 240))
    gradient_bg(img, (250, 247, 240), (248, 243, 233))
    glow(img, W // 2, H // 3, 350, (255, 240, 200), opacity=15)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(200, 180, 140), width=1)
    corners(d, margin=45, size=12, color=(200, 180, 140))

    ctr(d, 150, '묵상을 위한 질문', ft_s(18), (180, 160, 110), shadow=True, shadow_color=(240, 237, 230))
    dots(d, 205, (200, 180, 140))

    y = 320
    for ln in wrap(q1, 22):
        y = ctr(d, y, ln, ft(30), (55, 45, 35), sp=20, shadow=True, shadow_color=(240, 237, 230))
    y += 60
    for ln in wrap(q2, 22):
        y = ctr(d, y, ln, ft(30), (55, 45, 35), sp=20, shadow=True, shadow_color=(240, 237, 230))

    y += 40
    ctr(d, y, '* 하나만 떠올려도 충분합니다', ft_s(15), (170, 155, 130))

    footer_light(d, page)
    return img


# ══════════════════════════════════════════
#  CARD 7: PRACTICE (light sage)
# ══════════════════════════════════════════
def card_practice(text, page, seed=7):
    img = Image.new('RGB', (W, H), (242, 245, 238))
    gradient_bg(img, (242, 245, 238), (238, 242, 233))
    glow(img, W // 2, H // 3, 350, (220, 240, 210), opacity=12)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(150, 170, 140), width=1)
    corners(d, margin=45, size=12, color=(120, 140, 110))

    ctr(d, 200, '오늘의 실천', ft_s(18), (120, 140, 110), shadow=True, shadow_color=(235, 238, 230))
    dots(d, 255, (140, 160, 125))

    y = 380
    for ln in wrap(text, 22)[:6]:
        y = ctr(d, y, ln, ft(32), (55, 50, 40), sp=26, shadow=True, shadow_color=(235, 238, 230))

    footer(d, page, color=(140, 150, 125))
    return img


# ══════════════════════════════════════════
#  CARD 8: PRAYER (dark)
# ══════════════════════════════════════════
def card_prayer(text, page, seed=8):
    img = Image.new('RGB', (W, H), (28, 25, 32))
    gradient_bg(img, (28, 25, 32), (38, 33, 40))
    # Golden cross glow from center
    glow(img, W // 2, H // 3, 400, (200, 180, 130), opacity=14)
    glow(img, W // 2, 200, 250, (220, 200, 150), opacity=10)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(90, 80, 60), width=1)
    corners(d, margin=45, size=12, color=(140, 125, 90))

    cross_symbol(d, 100, (200, 180, 140))
    ctr(d, 185, '오늘의 기도', ft_s(18), (180, 170, 130), shadow=True, shadow_color=(18, 15, 22))
    dots(d, 235, (160, 145, 110))

    y = 330
    for ln in wrap(text, 22)[:8]:
        y = ctr(d, y, ln, ft_l(28), (225, 220, 210), sp=22, shadow=True, shadow_color=(18, 15, 22))

    footer_dark(d, page)
    return img


# ══════════════════════════════════════════
#  CARD 8 alt: CLOSING (dark warm)
# ══════════════════════════════════════════
def card_closing(ref, date_kr, day_kr, seed=8):
    img = Image.new('RGB', (W, H), (35, 30, 25))
    gradient_bg(img, (35, 30, 25), (50, 42, 35))
    glow(img, W // 2, H // 2, 450, (220, 190, 130), opacity=16)
    grain(img, seed=seed, intensity=5)
    d = ImageDraw.Draw(img)
    frame(d, margin=45, color=(160, 140, 100), width=1)
    corners(d, margin=45, size=14, color=(180, 160, 120))

    cross_symbol(d, 320, (220, 200, 150))
    ctr(d, 420, ref, ft(32), (230, 220, 200), sp=14, shadow=True, shadow_color=(25, 20, 15))

    dots(d, 510, (200, 180, 140))
    ctr(d, 560, f'{date_kr}  {day_kr}요일', ft_s(18), (170, 160, 135), shadow=True, shadow_color=(25, 20, 15))

    # 동산감리교회 prominent
    ctr(d, 650, '동산감리교회', ft_s(22), (220, 200, 150), shadow=True, shadow_color=(25, 20, 15))

    footer_dark(d, 8)
    return img


# ── Parse devotion file ──
def parse_word(content):
    sec = {
        "ref": "", "title": "", "verse": "",
        "med_title": "", "meditation": "",
        "questions": [], "practice": "", "prayer": ""
    }

    ref = re.search(r'(사무엘하|삼하)\s*\d+[:\s]*\d+[\-\u2013~]*\d*', content)
    if ref:
        sec["ref"] = ref.group().strip()

    titles = re.findall(r'\*\*(.+?)\*\*', content)
    for t in titles:
        if 3 < len(t) < 30 and not any(k in t for k in ['새번역', '성경', '매일', '오늘', '말씀']):
            sec["title"] = t.strip()
            break

    vlines = []
    for l in content.split("\n"):
        ls = l.strip()
        if re.match(r'^[\u00b9\u00b2\u00b3\u2070-\u2079\u00b0]+', ls):
            vlines.append(ls)
    sec["verse"] = "\n".join(vlines)

    med = re.search(
        r'\*\s*오늘의 묵상\s*\n"?(.+?)"?\s*\n\n(.+?)(?=\*\s*묵상을 위한 질문|\*\s*오늘의 실천|\*\s*오늘의 기도|$)',
        content, re.DOTALL
    )
    if med:
        sec["med_title"] = med.group(1).strip().strip('"')
        sec["meditation"] = med.group(2).strip()

    q = re.search(
        r'\*\s*묵상을 위한 질문\s*\n(.+?)(?=\*\s*오늘의 실천|\*\s*오늘의 기도|\u203b|$)',
        content, re.DOTALL
    )
    if q:
        for l in q.group(1).strip().split("\n"):
            ls = l.strip().lstrip('-').strip()
            if ls and not ls.startswith('\u203b') and len(ls) > 5:
                sec["questions"].append(ls)

    pr = re.search(r'\*\s*오늘의 실천\s*\n(.+?)(?=\*\s*오늘의 기도|$)', content, re.DOTALL)
    if pr:
        sec["practice"] = pr.group(1).strip()

    pray = re.search(r'\*\s*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray:
        sec["prayer"] = pray.group(1).strip()

    return sec


# ── Upload to Imgur ──
def upload(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-v4", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    for attempt in range(3):
        try:
            with open(path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post(
                'https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                data={'image': enc, 'type': 'base64'}
            )
            url = r.json().get('data', {}).get('link')
            if url:
                return url
        except Exception as e:
            print(f"    Upload retry {attempt+1}: {e}")
        time.sleep(5)
    return None


# ── Post to Instagram ──
def post_ig(urls, caption):
    ids = []
    for u in urls:
        r = requests.post(
            f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media',
            data={'image_url': u, 'is_carousel_item': 'true', 'access_token': CHURCH_TOKEN}
        )
        if 'id' in r.json():
            ids.append(r.json()['id'])
        else:
            print(f"    IG media err: {r.json()}")
        time.sleep(2)
    if len(ids) < 2:
        return None
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media',
        data={
            'media_type': 'CAROUSEL',
            'children': ','.join(ids),
            'caption': caption,
            'access_token': CHURCH_TOKEN
        }
    )
    if 'id' not in r.json():
        print(f"    IG carousel err: {r.json()}")
        return None
    time.sleep(8)
    r2 = requests.post(
        f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media_publish',
        data={'creation_id': r.json()['id'], 'access_token': CHURCH_TOKEN}
    )
    return r2.json().get('id')


# ══════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════
dates = ["2026-04-23", "2026-04-24", "2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30"]
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

print("=" * 55)
print("  Bible Cards v4 — Premium Design")
print("=" * 55)

for ds in dates:
    dt = datetime.strptime(ds, "%Y-%m-%d")
    dk = dt.strftime("%m/%d")
    dw = WEEKDAYS[dt.weekday()]
    seed_base = int(ds.replace("-", ""))

    wp = os.path.join(HOME, "Documents", "오늘의말씀", f"{ds}.txt")
    if not os.path.exists(wp):
        print(f"\n[{ds}] SKIP — file not found")
        continue

    with open(wp, 'r', encoding='utf-8') as f:
        content = f.read()
    sec = parse_word(content)
    print(f"\n[{ds} ({dw})] {sec['ref']} — {sec['title']}")

    # ── Split verse into 2 chunks ──
    verse = sec['verse']
    v_lines = [l.strip() for l in verse.split("\n") if l.strip()]
    mid = max(3, len(v_lines) // 2)
    v_chunk1 = wrap("\n".join(v_lines[:mid]), 22) if v_lines else [""]
    v_chunk2 = wrap("\n".join(v_lines[mid:]), 22) if len(v_lines) > mid else []

    # ── AI로 묵상을 카드용 핵심 문장으로 압축 ──
    med = sec['meditation']
    med_title = sec.get('med_title', sec.get('title', ''))
    try:
        condensed = claude(
            "다음 묵상을 인스타 카드용으로 압축해줘.\n\n"
            "[제목] " + med_title + "\n\n"
            "[원본]\n" + med + "\n\n"
            "[규칙]\n"
            "- 카드 3장으로 나누기\n"
            "- 각 카드에 핵심 2~3줄\n"
            "- 한 줄 최대 10자\n"
            "- JSON: {\"cards\": [\"줄1\\n줄2\\n줄3\", \"줄1\\n줄2\", \"줄1\\n줄2\\n줄3\"]}\n"
            "- 감동적이고 임팩트 있게\n"
            "- 마지막 카드는 예수님과의 연결"
        )
        cs = condensed.find("{")
        ce = condensed.rfind("}") + 1
        med_data = json.loads(condensed[cs:ce])
        med_card_texts = med_data.get("cards", [])
    except:
        # 압축 실패 시 원본에서 핵심 문장 추출
        med_card_texts = [med[:60], med[60:120], med[120:180]]

    while len(med_card_texts) < 3:
        med_card_texts.append("")

    med1 = med_card_texts[0].split("\n") if med_card_texts[0] else [""]
    med2 = med_card_texts[1].split("\n") if med_card_texts[1] else [""]
    med3 = med_card_texts[2].split("\n") if med_card_texts[2] else [""]
    med4 = []

    # ── Prayer text (truncated for card) ──
    prayer = sec['prayer']
    pray_short = prayer[:180] if prayer else ""

    # ── Build 8 cards ──
    cards = []

    # Card 1: COVER
    cards.append(card_cover(
        sec['ref'], sec['med_title'] or sec['title'], dk, dw,
        seed=seed_base
    ))

    # Card 2: VERSE1
    cards.append(card_verse(sec['ref'], v_chunk1, 2, seed=seed_base + 1))

    # Card 3: VERSE2 or MEDITATION1
    if v_chunk2:
        cards.append(card_verse(sec['ref'], v_chunk2, 3, seed=seed_base + 2))
    else:
        cards.append(card_meditation(med1, 3, subtitle=sec.get('med_title', ''), seed=seed_base + 2))

    # Card 4: MEDITATION (key sentence)
    if v_chunk2:
        cards.append(card_meditation(med1, 4, subtitle=sec.get('med_title', ''), seed=seed_base + 3))
    else:
        cards.append(card_meditation2(med2, 4, seed=seed_base + 3))

    # Card 5: MEDITATION2
    if v_chunk2:
        cards.append(card_meditation2(med2, 5, seed=seed_base + 4))
    else:
        cards.append(card_meditation2(med3, 5, seed=seed_base + 4))

    # Card 6: MEDITATION3 (추가 묵상)
    if med3:
        cards.append(card_meditation2(med3 if v_chunk2 else med4, 6, seed=seed_base + 5))

    # Card 7: QUESTION
    q1 = sec['questions'][0] if sec['questions'] else ""
    q2 = sec['questions'][1] if len(sec['questions']) > 1 else ""
    cards.append(card_question(q1, q2, len(cards) + 1, seed=seed_base + 6))

    # Card 8: PRACTICE
    cards.append(card_practice(sec['practice'], len(cards) + 1, seed=seed_base + 7))

    # Card 9: PRAYER
    if prayer:
        cards.append(card_prayer(pray_short, len(cards) + 1, seed=seed_base + 8))

    # Card 10: CLOSING
    cards.append(card_closing(sec['ref'], dk, dw, seed=seed_base + 9))

    # ── Upload all cards ──
    urls = []
    for i, card in enumerate(cards):
        url = upload(card, f"v4_{ds}_{i+1}.jpg")
        if url:
            urls.append(url)
        print(f"  {i+1}/8: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    # ── Caption ──
    caption = (
        f"📖 {sec['ref']}\n"
        f"\"{sec['med_title'] or sec['title']}\"\n\n"
        f"{sec['meditation'][:200]}\n\n"
        f"✦ 오늘의 질문\n{sec['questions'][0] if sec.get('questions') else ''}\n\n"
        f"✦ 오늘의 실천\n{sec.get('practice','')[:120]}\n\n"
        f"🙏 오늘의 기도\n{sec.get('prayer','')[:150]}\n\n"
        f"동산감리교회\n@garden___church\n\n"
        f"#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n"
        f"#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n"
        f"#거룩 #순종 #예배 #기독교 #새벽기도 #하나님\n"
        f"#BibleVerse #DailyDevotional #ChurchLife"
    )

    # ── Post to Instagram ──
    if len(urls) >= 2:
        pid = post_ig(urls, caption)
        print(f"  IG: {'OK — ' + str(pid) if pid else 'FAIL'}")
    else:
        print(f"  IG: SKIP — only {len(urls)} images uploaded")
    time.sleep(3)

    # ── Post to Facebook ──
    if urls and CHURCH_PAGE_ID:
        fb_msg = (
            f"📖 {sec['ref']}\n"
            f"\"{sec['med_title'] or sec['title']}\"\n\n"
            f"{sec['meditation'][:300]}\n\n"
            f"✦ 오늘의 실천\n{sec.get('practice','')[:150]}\n\n"
            f"🙏 오늘의 기도\n{sec.get('prayer','')[:200]}\n\n"
            f"동산감리교회\n@garden___church\n\n"
            f"#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n"
            f"#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n"
            f"#BibleVerse #DailyDevotional #ChurchLife"
        )
        fb = requests.post(
            f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos',
            data={'url': urls[0], 'message': fb_msg, 'access_token': CHURCH_TOKEN}
        )
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL — ' + str(fb.json())}")
    time.sleep(5)

print(f"\n{'=' * 55}")
print("  v4 Premium cards done!")
print(f"{'=' * 55}")
