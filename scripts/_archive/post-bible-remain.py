"""4/23~4/26 말씀 카드 일괄 게시 (garden___church + 동산감리교회 FB)"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, re, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

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
CREAM = (252, 249, 242)
GOLD = (180, 140, 70)
DARK_TEXT = (45, 40, 35)
BODY_TEXT = (80, 75, 65)
LIGHT_TEXT = (150, 140, 125)
BROWN = (139, 100, 60)

def gf(size, bold=False):
    fonts = [
        ("C:/Windows/Fonts/NanumMyeongjoBold.ttf" if bold else "C:/Windows/Fonts/NanumMyeongjo.ttf"),
        ("C:/Windows/Fonts/batangb.ttc" if bold else "C:/Windows/Fonts/batang.ttc"),
        ("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
    ]
    for p in fonts:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def gf_sans(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def wrap_text(text, mc=24):
    lines = []
    for line in text.split("\n"):
        while len(line) > mc:
            lines.append(line[:mc])
            line = line[mc:]
        lines.append(line)
    return "\n".join(lines)

def parse_word(content):
    sections = {"ref":"","title":"","verse":"","med_title":"","meditation":"","questions":[],"practice":"","prayer":""}
    ref_match = re.search(r'사무엘하\s*\d+[:\s]*\d+[\-–~]*\d*', content)
    if ref_match: sections["ref"] = ref_match.group().strip()
    title_match = re.search(r'\*\*(.+?)\*\*', content)
    if title_match: sections["title"] = title_match.group(1).strip()
    # 본문 (절번호 있는 줄)
    vlines = []
    for line in content.split("\n"):
        l = line.strip()
        if re.match(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹]+', l) or (re.match(r'^\d+\s', l) and len(l) > 20):
            vlines.append(l)
    sections["verse"] = "\n".join(vlines)
    med = re.search(r'\*오늘의 묵상\s*\n"?(.+?)"?\n\n(.+?)(?=\*묵상을 위한 질문|\*오늘의 실천|\*오늘의 기도|$)', content, re.DOTALL)
    if med:
        sections["med_title"] = med.group(1).strip().strip('"')
        sections["meditation"] = med.group(2).strip()
    q = re.search(r'\*묵상을 위한 질문\s*\n(.+?)(?=\*오늘의 실천|\*오늘의 기도|※|$)', content, re.DOTALL)
    if q:
        for line in q.group(1).strip().split("\n"):
            l = line.strip().lstrip('-').strip()
            if l and not l.startswith('※'): sections["questions"].append(l)
    pr = re.search(r'\*오늘의 실천\s*\n(.+?)(?=\*오늘의 기도|$)', content, re.DOTALL)
    if pr: sections["practice"] = pr.group(1).strip()
    pray = re.search(r'\*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray: sections["prayer"] = pray.group(1).strip()
    return sections

def make_card(card_type, data, page, total, date_kr, day_kr):
    import random
    bg = CREAM if card_type != "prayer" else (30, 28, 38)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    random.seed(page * 100 + hash(date_kr))
    for _ in range(3000):
        x, y2 = random.randint(0,W), random.randint(0,H)
        v = random.randint(-4, 4)
        c = tuple(max(0,min(255,bg[i]+v)) for i in range(3))
        d.point((x,y2), fill=c)

    d.rectangle([0, 0, W, 2], fill=GOLD)
    cx = W//2
    d.rectangle([cx-1, 40, cx+1, 75], fill=(*GOLD, 80))
    d.rectangle([cx-12, 55, cx+12, 57], fill=(*GOLD, 80))
    tc_color = LIGHT_TEXT if card_type != "prayer" else (100,95,85)
    d.text((60, 45), "동산감리교회", font=gf_sans(14), fill=tc_color)
    bb = d.textbbox((0,0), f"{date_kr} ({day_kr})", font=gf_sans(14))
    d.text((W-(bb[2]-bb[0])-60, 45), f"{date_kr} ({day_kr})", font=gf_sans(14), fill=tc_color)

    if card_type == "cover":
        y = 350
        tc(d, y, "오늘의 말씀", gf_sans(18), LIGHT_TEXT, 20)
        y += 60; d.rectangle([cx-40,y,cx+40,y+1], fill=GOLD); y += 30
        tc(d, y, data.get("ref",""), gf(36,True), DARK_TEXT, 16); y += 80
        tc(d, y, data.get("title",""), gf(28), BROWN, 12)
    elif card_type == "verse":
        y = 140
        tc(d, y, data.get("ref",""), gf_sans(16), GOLD, 15); y += 30
        d.rectangle([cx-30,y,cx+30,y+1], fill=GOLD); y += 20
        tc(d, y, "\u201C", gf(50), (*GOLD,80)); y += 35
        for ln in wrap_text(data.get("text",""), 24).split("\n")[:16]:
            if not ln.strip(): y += 8; continue
            y = tc(d, y, ln, gf(22), DARK_TEXT, 11)
    elif card_type == "meditation":
        y = 150
        tc(d, y, "묵상", gf_sans(14), GOLD, 15); y += 25
        if data.get("title"):
            tc(d, y, data["title"], gf(30,True), DARK_TEXT, 14); y += 50
        d.rectangle([cx-25,y,cx+25,y+1], fill=GOLD); y += 20
        for ln in wrap_text(data.get("body",""), 26).split("\n")[:22]:
            if not ln.strip(): y += 8; continue
            y = tc(d, y, ln, gf(20), BODY_TEXT, 10)
    elif card_type == "question":
        y = 280
        tc(d, y, "묵상을 위한 질문", gf_sans(14), GOLD, 25); y += 30
        d.rectangle([cx-25,y,cx+25,y+1], fill=GOLD); y += 30
        for q in data.get("questions",[])[:2]:
            for ln in wrap_text(q, 24).split("\n"):
                y = tc(d, y, ln, gf(22), DARK_TEXT, 12)
            y += 25
    elif card_type == "practice":
        y = 280
        tc(d, y, "오늘의 실천", gf_sans(14), GOLD, 25); y += 30
        d.rectangle([cx-25,y,cx+25,y+1], fill=GOLD); y += 30
        for ln in wrap_text(data.get("text",""), 24).split("\n")[:12]:
            if not ln.strip(): y += 8; continue
            y = tc(d, y, ln, gf(22), DARK_TEXT, 13)
    elif card_type == "prayer":
        y = 200
        tc(d, y, "오늘의 기도", gf_sans(14), GOLD, 25); y += 30
        d.rectangle([cx-25,y,cx+25,y+1], fill=GOLD); y += 25
        for ln in wrap_text(data.get("text",""), 24).split("\n")[:18]:
            if not ln.strip(): y += 8; continue
            y = tc(d, y, ln, gf(21), (220,215,205), 12)
    elif card_type == "closing":
        y = 400
        for ln in wrap_text(data.get("verse",""), 20).split("\n"):
            y = tc(d, y, ln, gf(28,True), DARK_TEXT if card_type != "prayer" else (220,215,205), 14)
        y += 30; d.rectangle([cx-25,y,cx+25,y+1], fill=GOLD); y += 20
        tc(d, y, data.get("ref",""), gf_sans(18), GOLD, 15); y += 40
        tc(d, y, "동산감리교회", gf_sans(18), LIGHT_TEXT)
        tc(d, y+25, "@garden___church", gf_sans(14), LIGHT_TEXT)

    d.rectangle([cx-20, H-70, cx+20, H-68], fill=GOLD)
    ft_c = LIGHT_TEXT if card_type != "prayer" else (80,75,65)
    tc(d, H-55, f"{page}/{total}", gf_sans(12), ft_c)
    return img

def upload_imgur(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-cards", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    with open(path,'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    r = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':enc,'type':'base64'})
    return r.json().get('data',{}).get('link')

def post_carousel(urls, caption):
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
dates = ["2026-04-24","2026-04-25","2026-04-26"]
WEEKDAYS = ['월','화','수','목','금','토','일']

print("=" * 50)
print("  Bible Cards 4/23 ~ 4/26")
print("=" * 50)

for date_str in dates:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    date_kr = dt.strftime("%m/%d")
    day_kr = WEEKDAYS[dt.weekday()]

    wp = os.path.join(HOME, "Documents", "오늘의말씀", f"{date_str}.txt")
    if not os.path.exists(wp):
        print(f"\n[{date_str}] File not found, skip"); continue

    with open(wp, 'r', encoding='utf-8') as f:
        content = f.read()
    sec = parse_word(content)
    print(f"\n[{date_str} ({day_kr})] {sec['ref']} - {sec['med_title']}")

    verse = sec['verse'] if sec['verse'] else ""
    med = sec['meditation']
    cards_data = [
        ("cover", {"ref": sec['ref'], "title": sec['med_title'] or sec['title']}),
        ("verse", {"ref": sec['ref'], "text": verse[:350]}),
        ("verse", {"ref": sec['ref'], "text": verse[350:]}) if len(verse) > 350 else ("meditation", {"title": sec['med_title'], "body": med[:400]}),
        ("meditation", {"title": sec['med_title'] if len(verse) > 350 else "", "body": med[:400] if len(verse) > 350 else med[400:800]}),
        ("meditation", {"title": "", "body": med[400:800] if len(verse) > 350 else med[800:]}),
        ("question", {"questions": sec['questions']}),
        ("practice", {"text": sec['practice']}),
        ("prayer", {"text": sec['prayer']}),
    ]

    urls = []
    for i, (ct, cd) in enumerate(cards_data):
        img = make_card(ct, cd, i+1, 8, date_kr, day_kr)
        url = upload_imgur(img, f"bible_{date_str}_{i+1}.jpg")
        if url: urls.append(url)
        time.sleep(1)
    print(f"  Images: {len(urls)}/8")

    # IG
    caption = f"📖 {sec['ref']}\n\"{sec['med_title']}\"\n\n{sec['meditation'][:200]}\n\n✦ 오늘의 질문\n{sec.get('questions',[''])[0] if sec.get('questions') else ''}\n\n✦ 오늘의 실천\n{sec.get('practice','')[:120]}\n\n🙏 오늘의 기도\n{sec.get('prayer','')[:150]}\n\n동산감리교회\n@garden___church\n\n#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n#거룩 #순종 #예배 #기독교 #새벽기도 #하나님\n#BibleVerse #DailyDevotional #ChurchLife"
    if len(urls) >= 2:
        pid = post_carousel(urls, caption)
        print(f"  IG: {'OK' if pid else 'FAIL'}")
    time.sleep(3)

    # FB
    if urls and CHURCH_PAGE_ID:
        fb_msg = f"📖 {sec['ref']}\n\"{sec['med_title']}\"\n\n{sec['meditation'][:300]}\n\n✦ 오늘의 실천\n{sec.get('practice','')[:150]}\n\n🙏 오늘의 기도\n{sec.get('prayer','')[:200]}\n\n동산감리교회\n@garden___church\n\n#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n#BibleVerse #DailyDevotional #ChurchLife"
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={'url':urls[0],'message':fb_msg,'access_token':CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL'}")
    time.sleep(5)

print(f"\n{'='*50}")
print(f"  4 days posted!")
print(f"{'='*50}")
