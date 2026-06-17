"""고퀄리티 말씀 카드 v3 — 큰 글씨, 여백 많이, 감성 디자인"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
CHURCH_TOKEN = tokens.get('church_page', tokens['instagram'])
CHURCH_IG_ID = tokens.get('church_ig_id', '')
CHURCH_PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"

W, H = 1080, 1350

def ft(size):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def ft_light(size):
    for p in ['C:/Windows/Fonts/HANBatang.ttf','C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def ft_sans(size):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', size) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

GOLD = (180, 150, 80)
GOLD_L = (210, 195, 170)
SAGE = (120, 140, 110)
DEEP = (55, 45, 35)
MED = (100, 80, 60)
LIGHT = (170, 155, 135)
FAINT = (200, 185, 160)

def ctr(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp + 5; continue
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def dots(d, y, color=GOLD):
    cx = W//2
    for off in [-20,-7,0,7,20]:
        d.ellipse([cx+off-2, y, cx+off+2, y+4], fill=color)

def cross(d, y, color=GOLD):
    cx = W//2
    d.rectangle([cx-1, y, cx+1, y+35], fill=color)
    d.rectangle([cx-13, y+15, cx+13, y+17], fill=color)

def line(d, y, color=FAINT, w=100):
    d.rectangle([W//2-w, y, W//2+w, y+1], fill=color)

def wrap(text, mc=16):
    result = []
    for ln in text.split("\n"):
        while len(ln) > mc:
            sp = ln[:mc].rfind(' ')
            cut = sp if sp > mc//2 else mc
            result.append(ln[:cut].strip())
            ln = ln[cut:].strip()
        if ln.strip(): result.append(ln)
    return result

# === 카드 생성 ===
def card_cover(ref, title, date_kr, day_kr):
    img = Image.new('RGB', (W,H), (245,240,230))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=GOLD)
    cross(d, 80, GOLD)
    ctr(d, 150, f'{date_kr}  {day_kr}요일', ft_sans(18), LIGHT)
    ctr(d, 380, '오늘의 말씀', ft_sans(22), (160,140,115), 15)
    ctr(d, 480, ref, ft(42), DEEP, 10)
    dots(d, 570, GOLD)
    for ln in wrap(title, 12):
        pass
    y = 630
    for ln in wrap(title, 12):
        y = ctr(d, y, ln, ft(36), MED, 18)
    line(d, H-130, FAINT, 150)
    ctr(d, H-105, '동산감리교회', ft_sans(18), LIGHT)
    ctr(d, H-45, '1 / 8', ft_sans(12), (190,175,155))
    return img

def card_verse(ref, lines, page):
    img = Image.new('RGB', (W,H), (250,247,240))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=GOLD)
    ctr(d, 100, ref, ft_sans(18), LIGHT)
    line(d, 150, FAINT, 50)
    d.text((120, 200), '\u201C', font=ft(70), fill=GOLD_L)
    y = 310
    for ln in lines[:7]:
        y = ctr(d, y, ln, ft(32), DEEP, 22)
    bb = d.textbbox((0,0), '\u201D', font=ft(70))
    d.text(((W-(bb[2]-bb[0]))/2, y+10), '\u201D', font=ft(70), fill=GOLD_L)
    line(d, H-80, FAINT, 40)
    ctr(d, H-55, f'{page} / 8', ft_sans(14), (190,175,155))
    return img

def card_meditation(lines, page):
    img = Image.new('RGB', (W,H), (245,242,232))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=SAGE)
    ctr(d, 100, '묵 상', ft_sans(16), SAGE)
    line(d, 145, SAGE, 35)
    y = 350
    for ln in lines[:5]:
        y = ctr(d, y, ln, ft(38), DEEP, 28)
    line(d, H-80, SAGE, 35)
    ctr(d, H-55, f'{page} / 8', ft_sans(14), LIGHT)
    return img

def card_question(q1, q2, page):
    img = Image.new('RGB', (W,H), (250,247,240))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=GOLD)
    ctr(d, 150, '묵상을 위한 질문', ft_sans(16), GOLD)
    dots(d, 200, GOLD)
    y = 320
    for ln in wrap(q1, 16):
        y = ctr(d, y, ln, ft(30), DEEP, 20)
    y += 50
    for ln in wrap(q2, 16):
        y = ctr(d, y, ln, ft(30), DEEP, 20)
    y += 30
    ctr(d, y, '* 하나만 떠올려도 충분합니다', ft_sans(16), LIGHT)
    line(d, H-80, FAINT, 40)
    ctr(d, H-55, f'{page} / 8', ft_sans(14), (190,175,155))
    return img

def card_practice(text, page):
    img = Image.new('RGB', (W,H), (245,242,232))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=SAGE)
    ctr(d, 200, '오늘의 실천', ft_sans(16), SAGE)
    line(d, 250, SAGE, 40)
    y = 380
    for ln in wrap(text, 16)[:5]:
        y = ctr(d, y, ln, ft(32), DEEP, 24)
    line(d, H-80, SAGE, 35)
    ctr(d, H-55, f'{page} / 8', ft_sans(14), LIGHT)
    return img

def card_prayer(text, page):
    img = Image.new('RGB', (W,H), (28,25,32))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=GOLD)
    cross(d, 80, GOLD)
    ctr(d, 160, '오늘의 기도', ft_sans(16), (180,170,130))
    line(d, 210, (80,70,55), 40)
    y = 320
    for ln in wrap(text, 18)[:8]:
        y = ctr(d, y, ln, ft_light(28), (225,220,210), 20)
    line(d, H-80, (80,70,55), 35)
    ctr(d, H-55, f'{page} / 8', ft_sans(14), (100,95,85))
    return img

def card_closing(ref, date_kr, day_kr):
    img = Image.new('RGB', (W,H), (245,240,230))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,2], fill=GOLD)
    cross(d, 300, GOLD)
    ctr(d, 420, ref, ft(30), DEEP, 14)
    y = 500
    dots(d, y, GOLD)
    ctr(d, y+40, f'{date_kr}  {day_kr}요일', ft_sans(18), LIGHT, 15)
    ctr(d, y+80, 'Lighthouse Media', ft_sb(20), pal_accent if 'pal_accent' in dir() else (180,150,80), 10)
    line(d, H-100, FAINT, 150)
    ctr(d, H-55, '8 / 8', ft_sans(14), (190,175,155))
    return img

def parse_word(content):
    sec = {"ref":"","title":"","verse":"","med_title":"","meditation":"","questions":[],"practice":"","prayer":""}
    ref = re.search(r'사무엘하|삼하\s*\d+[:\s]*\d+[\-\u2013~]*\d*', content)
    if ref: sec["ref"] = ref.group().strip()
    titles = re.findall(r'\*\*(.+?)\*\*', content)
    for t in titles:
        if len(t) > 3 and len(t) < 30 and not any(k in t for k in ['새번역','성경','매일','오늘','말씀']):
            sec["title"] = t.strip(); break
    vlines = []
    for l in content.split("\n"):
        ls = l.strip()
        if re.match(r'^[\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+', ls):
            vlines.append(ls)
    sec["verse"] = "\n".join(vlines)
    med = re.search(r'\*\s*오늘의 묵상\s*\n"?(.+?)"?\s*\n\n(.+?)(?=\*\s*묵상을 위한 질문|\*\s*오늘의 실천|\*\s*오늘의 기도|$)', content, re.DOTALL)
    if med:
        sec["med_title"] = med.group(1).strip().strip('"')
        sec["meditation"] = med.group(2).strip()
    q = re.search(r'\*\s*묵상을 위한 질문\s*\n(.+?)(?=\*\s*오늘의 실천|\*\s*오늘의 기도|\u203b|$)', content, re.DOTALL)
    if q:
        for l in q.group(1).strip().split("\n"):
            ls = l.strip().lstrip('-').strip()
            if ls and not ls.startswith('\u203b') and len(ls) > 5: sec["questions"].append(ls)
    pr = re.search(r'\*\s*오늘의 실천\s*\n(.+?)(?=\*\s*오늘의 기도|$)', content, re.DOTALL)
    if pr: sec["practice"] = pr.group(1).strip()
    pray = re.search(r'\*\s*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray: sec["prayer"] = pray.group(1).strip()
    return sec

def upload(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-v3", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    for _ in range(3):
        try:
            with open(path,'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':enc,'type':'base64'})
            url = r.json().get('data',{}).get('link')
            if url: return url
        except: pass
        time.sleep(5)
    return None

def post_ig(urls, caption):
    ids = []
    for u in urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'image_url':u,'is_carousel_item':'true','access_token':CHURCH_TOKEN})
        if 'id' in r.json(): ids.append(r.json()['id'])
        time.sleep(2)
    if len(ids) < 2: return None
    r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'media_type':'CAROUSEL','children':','.join(ids),'caption':caption,'access_token':CHURCH_TOKEN})
    if 'id' not in r.json(): return None
    time.sleep(8)
    r2 = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media_publish', data={'creation_id':r.json()['id'],'access_token':CHURCH_TOKEN})
    return r2.json().get('id')

# === MAIN ===
dates = ["2026-04-23","2026-04-24","2026-04-27","2026-04-28","2026-04-29","2026-04-30"]
WEEKDAYS = ['월','화','수','목','금','토','일']

print("=" * 50)
print("  Bible Cards v3 - Premium Design")
print("=" * 50)

for ds in dates:
    dt = datetime.strptime(ds, "%Y-%m-%d")
    dk = dt.strftime("%m/%d")
    dw = WEEKDAYS[dt.weekday()]

    wp = os.path.join(HOME, "Documents", "\uc624\ub298\uc758\ub9d0\uc500", f"{ds}.txt")
    if not os.path.exists(wp): print(f"\n[{ds}] SKIP"); continue

    with open(wp,'r',encoding='utf-8') as f: content = f.read()
    sec = parse_word(content)
    print(f"\n[{ds} ({dw})] {sec['ref']}")

    # 말씀 본문을 2~3절씩 나누기
    verse = sec['verse']
    v_lines = [l.strip() for l in verse.split("\n") if l.strip()]
    v_chunk1 = wrap("\n".join(v_lines[:3]), 18) if v_lines else [""]
    v_chunk2 = wrap("\n".join(v_lines[3:6]), 18) if len(v_lines) > 3 else [""]

    # 묵상에서 문단별로 나누기
    med = sec['meditation']
    med_paras = [p.strip() for p in med.split("\n\n") if p.strip()]
    if not med_paras:
        med_paras = [med[:150], med[150:300], med[300:450]]
    # 각 문단에서 핵심만 (카드 1장에 3~4줄)
    med1 = wrap(med_paras[0][:120] if len(med_paras) > 0 else '', 14)
    med2 = wrap(med_paras[1][:120] if len(med_paras) > 1 else '', 14)

    # 기도문도 핵심만
    prayer = sec['prayer']
    pray_short = prayer[:150] if prayer else ""

    cards = [
        card_cover(sec['ref'], sec['med_title'] or sec['title'], dk, dw),
        card_verse(sec['ref'], v_chunk1, 2),
        card_verse(sec['ref'], v_chunk2, 3) if v_chunk2 != [""] else card_meditation(med1, 3),
        card_meditation(med1 if v_chunk2 != [""] else med2, 4),
        card_meditation(med2 if med2 else wrap(med_paras[2][:120] if len(med_paras)>2 else med[:120], 14), 5),
        card_question(sec['questions'][0] if sec['questions'] else "", sec['questions'][1] if len(sec['questions'])>1 else "", 6),
        card_practice(sec['practice'], 7),
        card_prayer(pray_short, 8) if prayer else card_closing(sec['ref'], dk, dw),
    ]

    urls = []
    for i, card in enumerate(cards):
        url = upload(card, f"v3_{ds}_{i+1}.jpg")
        if url: urls.append(url)
        print(f"  {i+1}/8: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    caption = f"\uc624\ub298\uc758 \ub9d0\uc500 | {dk} ({dw})\n\n{sec['ref']}\n\n\"{sec['med_title']}\"\n\n\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c\n@garden___church\n\n#\uc624\ub298\uc758\ub9d0\uc500 #\uc131\uacbd\ub9d0\uc500 #\ubb35\uc0c1 #\uc0ac\ubb34\uc5d8\ud558 #\uae30\ub3c4 #\uad50\ud68c #\ub9d0\uc500\uce74\ub4dc #\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c #\ub9e4\uc77c\ubb35\uc0c1 #\uc131\uacbd #\uc740\ud61c #\uac10\uc0ac #\uc608\ubc30 #\uae30\ub3c5\uad50 #\ud558\ub098\ub2d8"

    if len(urls) >= 2:
        pid = post_ig(urls, caption)
        print(f"  IG: {'OK' if pid else 'FAIL'}")
    time.sleep(3)

    if urls and CHURCH_PAGE_ID:
        fb_msg = f"\uc624\ub298\uc758 \ub9d0\uc500 | {dk} ({dw})\n\n{sec['ref']}\n\n{sec['med_title']}\n\n{med_paras[0][:200] if med_paras else ''}\n\n\ub3d9\uc0b0\uac10\ub9ac\uad50\ud68c"
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={'url':urls[0],'message':fb_msg,'access_token':CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL'}")
    time.sleep(5)

print(f"\n{'='*50}")
print("  v3 cards done!")
print(f"{'='*50}")
