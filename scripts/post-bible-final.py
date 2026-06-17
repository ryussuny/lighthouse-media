"""말씀 카드 FINAL — 품질 검증 + 중복 방지 + AI 압축 묵상"""
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

# 중복 방지: 이미 게시한 날짜 추적
POSTED_FILE = os.path.join(HOME, "lighthouse-media", "data", "posted-bible-dates.json")
def load_posted():
    if os.path.exists(POSTED_FILE): return json.load(open(POSTED_FILE, encoding='utf-8'))
    return []
def save_posted(dates):
    os.makedirs(os.path.dirname(POSTED_FILE), exist_ok=True)
    with open(POSTED_FILE, 'w', encoding='utf-8') as f: json.dump(dates, f)

def ai_call(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 600, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

# === 폰트 ===
def f_t(sz):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def f_b(sz):
    for p in ['C:/Windows/Fonts/HANBatang.ttf','C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def f_s(sz):
    return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', sz) if os.path.exists('C:/Windows/Fonts/malgunbd.ttf') else ImageFont.load_default()

def f_sl(sz):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', sz) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

# === 그리기 ===
def ct(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp + 5; continue
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def st(d, y, text, font, fill, sfill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp + 5; continue
        bb = d.textbbox((0,0), ln, font=font)
        x = (W-(bb[2]-bb[0]))/2
        d.text((x+1, y+1), ln, font=font, fill=sfill)
        d.text((x, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def mk_light(img, seed=0):
    d = ImageDraw.Draw(img)
    for row in range(H):
        p = row/H
        d.line([(0,row),(W,row)], fill=(int(248-p*6),int(245-p*8),int(237-p*10)))
    for i in range(30):
        r = 120+i*7
        d.ellipse([W-180-r,-60-r//2,W-180+r,-60+r//2], fill=(255,250,240,int(5*(1-i/30))))
    random.seed(seed)
    for _ in range(2000):
        x,y2 = random.randint(0,W-1), random.randint(0,H-1)
        px = img.getpixel((x,y2)); v = random.randint(-2,2)
        img.putpixel((x,y2), tuple(max(0,min(255,c+v)) for c in px))

def mk_dark(img, seed=0):
    d = ImageDraw.Draw(img)
    for row in range(H):
        p = row/H
        d.line([(0,row),(W,row)], fill=(int(30+p*8+math.sin(p*3.14)*6),int(27+p*6+math.sin(p*3.14)*5),int(38+p*10)))
    for i in range(40):
        r = 80+i*6
        d.ellipse([W//2-r,-20-r//2,W//2+r,-20+r//2], fill=(200,180,140,int(5*(1-i/40))))
    random.seed(seed)
    for _ in range(1500):
        x,y2 = random.randint(0,W-1), random.randint(0,H-1)
        px = img.getpixel((x,y2)); v = random.randint(-2,2)
        img.putpixel((x,y2), tuple(max(0,min(255,c+v)) for c in px))

def frame(d, light=True):
    c = (210,200,180) if light else (75,65,50)
    d.rectangle([50,50,W-50,H-50], outline=c, width=1)
    for cx,cy in [(50,50),(W-50,50),(50,H-50),(W-50,H-50)]:
        d.line([(cx-8,cy),(cx+8,cy)], fill=c); d.line([(cx,cy-8),(cx,cy+8)], fill=c)

def dots(d, y, light=True):
    c = (200,185,155) if light else (130,115,85)
    cx = W//2
    for off in [-18,-6,0,6,18]: d.ellipse([cx+off-2,y,cx+off+2,y+4], fill=c)

def cross(d, y, light=True):
    c = (200,180,140) if light else (150,130,95)
    cx = W//2
    d.rectangle([cx-1,y,cx+1,y+28], fill=c); d.rectangle([cx-10,y+11,cx+10,y+13], fill=c)

def foot(d, page, total, light=True):
    c = (165,155,135) if light else (90,85,70)
    lc = (200,185,155) if light else (70,60,45)
    d.rectangle([W//2-22,H-85,W//2+22,H-83], fill=lc)
    ct(d, H-72, "동산감리교회", f_sl(13), c)
    ct(d, H-50, f"{page}/{total}", f_sl(10), (180,170,150) if light else (65,60,50))

# === 카드 함수 ===
def c_cover(ref, title, dk, dw, sd):
    img = Image.new('RGB',(W,H),(35,30,45)); mk_dark(img,sd); d = ImageDraw.Draw(img)
    frame(d,False); cross(d,100,False)
    ct(d,165,f"{dk} {dw}요일",f_sl(15),(155,145,125))
    dots(d,210,False)
    st(d,430,ref,f_t(42),(230,220,200),(20,17,28),12)
    d.rectangle([W//2-45,530,W//2+45,531],fill=(170,150,110))
    st(d,570,title,f_t(34),(205,195,175),(20,17,28),14)
    foot(d,1,8,False)
    return img

def c_verse(ref, lines, page, sd):
    img = Image.new('RGB',(W,H),(248,245,237)); mk_light(img,sd); d = ImageDraw.Draw(img)
    frame(d,True)
    ct(d,95,ref,f_sl(14),(175,160,135))
    d.rectangle([W//2-30,130,W//2+30,131],fill=(200,185,155))
    y = 190
    for ln in lines:
        if not ln.strip(): y+=6; continue
        y = ct(d,y,ln,f_b(23),(50,42,32),14)
        if y > H-130: break
    foot(d,page,8,True)
    return img

def c_med(lines, page, sd):
    img = Image.new('RGB',(W,H),(28,25,35)); mk_dark(img,sd); d = ImageDraw.Draw(img)
    frame(d,False); dots(d,280,False)
    y = 400
    for ln in lines:
        if not ln.strip(): y+=15; continue
        y = st(d,y,ln,f_t(42),(232,222,202),(18,15,25),32)
    foot(d,page,8,False)
    return img

def c_prayer(lines, page, sd):
    img = Image.new('RGB',(W,H),(25,22,30)); mk_dark(img,sd+99); d = ImageDraw.Draw(img)
    frame(d,False); cross(d,160,False)
    ct(d,225,"기 도",f_sl(14),(155,140,105))
    d.rectangle([W//2-25,260,W//2+25,261],fill=(110,100,75))
    y = 340
    for ln in lines:
        if not ln.strip(): y+=8; continue
        y = ct(d,y,ln,f_b(25),(218,212,202),16)
        if y > H-130: break
    foot(d,page,8,False)
    return img

def c_close(ref, dk, dw, sd):
    img = Image.new('RGB',(W,H),(248,245,237)); mk_light(img,sd+199); d = ImageDraw.Draw(img)
    frame(d,True); cross(d,370,True)
    st(d,450,ref,f_t(28),(50,42,32),(238,235,228),10)
    dots(d,520,True)
    ct(d,565,f"{dk} {dw}요일",f_sl(15),(165,150,130))
    ct(d,610,"동산감리교회",f_t(22),(95,80,60))
    foot(d,8,8,True)
    return img

# === 파싱 ===
def parse(content):
    sec = {"ref":"","title":"","verse":"","meditation":"","med_title":"","prayer":""}
    ref = re.search(r'(사무엘하|삼하)\s*\d+[:\s]*\d+[\-\u2013~]*\d*', content)
    if ref: sec["ref"] = ref.group().strip()
    titles = re.findall(r'\*\*(.+?)\*\*', content)
    for t in titles:
        if 3 < len(t) < 30 and not any(k in t for k in ['새번역','성경','매일','오늘','말씀']):
            sec["title"] = t.strip(); break
    vlines = []
    for l in content.split("\n"):
        ls = l.strip()
        if re.match(r'^[\u00b9\u00b2\u00b3\u2070-\u2079\u00b0]+', ls): vlines.append(ls)
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
            sp = ln[:mc].rfind(' '); cut = sp if sp > mc//2 else mc
            result.append(ln[:cut].strip()); ln = ln[cut:].strip()
        if ln.strip(): result.append(ln.strip())
    return result

def upload(img, name):
    path = os.path.join(HOME, "lighthouse-media", "output", "bible-final", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "JPEG", quality=95)
    for _ in range(3):
        try:
            with open(path,'rb') as f: enc = base64.b64encode(f.read()).decode()
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
dates = ["2026-04-28"]  # 변경 가능
WEEKDAYS = ['월','화','수','목','금','토','일']

print("=" * 50)
print("  Bible Cards FINAL — Quality Verified")
print("=" * 50)

posted = load_posted()

for ds in dates:
    # === 중복 방지 ===
    if ds in posted:
        print(f"\n[{ds}] SKIP — already posted")
        continue

    dt = datetime.strptime(ds, "%Y-%m-%d")
    dk = dt.strftime("%m/%d"); dw = WEEKDAYS[dt.weekday()]; sd = int(ds.replace("-",""))

    wp = os.path.join(HOME, "Documents", "오늘의말씀", f"{ds}.txt")
    if not os.path.exists(wp):
        print(f"\n[{ds}] SKIP — no file"); continue

    with open(wp, 'r', encoding='utf-8') as f: content = f.read()
    sec = parse(content)

    # === 품질 검증 ===
    if not sec['ref']:
        print(f"\n[{ds}] SKIP — no bible reference"); continue
    if not sec['title'] and not sec['med_title']:
        print(f"\n[{ds}] SKIP — no title"); continue
    if not sec['meditation']:
        print(f"\n[{ds}] SKIP — no meditation"); continue

    title = sec.get('med_title','') or sec['title']
    print(f"\n[{ds} ({dw})] {sec['ref']} — {title}")

    # === 성경 본문 나누기 ===
    v_all = wrap_lines(sec['verse'], 20)
    mid = len(v_all) // 2
    v1 = v_all[:mid] if v_all else []
    v2 = v_all[mid:] if len(v_all) > mid else []

    # === AI 묵상 압축 (품질 검증 포함) ===
    print("  AI condensing...")
    try:
        raw = ai_call(
            "다음 묵상을 인스타 카드용으로 압축해줘.\n\n"
            "[제목] " + title + "\n\n"
            "[원본]\n" + sec['meditation'] + "\n\n"
            "[규칙]\n"
            "- 카드 3장으로\n"
            "- 각 카드 2~3줄\n"
            "- 한 줄 최대 10자\n"
            "- 1장: 본문의 핵심 장면/상황\n"
            "- 2장: 우리 삶에의 깊은 적용\n"
            "- 3장: 예수님과의 연결\n"
            "- JSON: {\"cards\":[\"줄1\\n줄2\\n줄3\",\"줄1\\n줄2\",\"줄1\\n줄2\\n줄3\"]}\n"
            "- 묵상이 깊어지는 문장으로\n"
            "- 한 줄 절대 10자 이하"
        )
        cs = raw.find("{"); ce = raw.rfind("}")+1
        med_cards = json.loads(raw[cs:ce]).get("cards",[])
        # 품질 검증: 각 카드에 내용이 있는지
        med_cards = [c for c in med_cards if c.strip()]
    except:
        med_cards = []

    if len(med_cards) < 3:
        print("  AI fail — using fallback")
        med_cards = [
            title,
            "오늘 이 말씀이\n당신에게 전합니다",
            "예수님 안에서\n새 힘을 얻습니다"
        ]

    m1 = med_cards[0].split("\n")
    m2 = med_cards[1].split("\n")
    m3 = med_cards[2].split("\n")

    # === 기도문 압축 ===
    prayer = sec.get('prayer','')
    pray_lines = wrap_lines(prayer[:120], 18) if prayer else ["하나님 아버지,","오늘 이 말씀으로","살게 하소서. 아멘."]

    # === 카드 8장 생성 ===
    print("  Creating cards...")
    cards = [c_cover(sec['ref'], title, dk, dw, sd)]

    if v1: cards.append(c_verse(sec['ref'], v1, 2, sd+1))
    if v2: cards.append(c_verse(sec['ref'], v2, 3, sd+2))
    else: cards.append(c_med(m1, 3, sd+2))

    cards.append(c_med(m1 if v2 else m2, len(cards)+1, sd+3))
    cards.append(c_med(m2 if v2 else m3, len(cards)+1, sd+4))
    if v2 and m3: cards.append(c_med(m3, len(cards)+1, sd+5))
    cards.append(c_prayer(pray_lines, len(cards)+1, sd+6))
    cards.append(c_close(sec['ref'], dk, dw, sd+7))

    total = len(cards)
    # 페이지 번호 재조정은 이미 foot()에서 처리

    # === 업로드 ===
    urls = []
    for i, card in enumerate(cards):
        url = upload(card, f"final_{ds}_{i+1}.jpg")
        if url: urls.append(url)
        print(f"  {i+1}/{total}: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    # === 게시 전 최종 검증 ===
    if len(urls) < 4:
        print(f"  ABORT — only {len(urls)} images uploaded (minimum 4)")
        continue

    caption = (
        f"📖 {sec['ref']}\n"
        f"\"{title}\"\n\n"
        f"{sec['meditation'][:200]}\n\n"
        f"✦ 오늘의 질문\n{sec.get('questions',[''])[0] if sec.get('questions') else ''}\n\n"
        f"✦ 오늘의 실천\n{sec.get('practice','')[:120]}\n\n"
        f"🙏 오늘의 기도\n{sec.get('prayer','')[:150]}\n\n"
        f"동산감리교회\n@garden___church\n\n"
        f"#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n"
        f"#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n"
        f"#거룩 #순종 #예배 #기독교 #새벽기도 #하나님\n"
        f"#BibleVerse #DailyDevotional #ChurchLife"
    )

    pid = post_ig(urls, caption)
    print(f"  IG: {'OK — ' + str(pid) if pid else 'FAIL'}")

    if urls and CHURCH_PAGE_ID:
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={
            'url': urls[0], 'message': caption[:500], 'access_token': CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else 'FAIL'}")

    # === 게시 성공 시 기록 ===
    if pid:
        posted.append(ds)
        save_posted(posted)
        print(f"  Recorded: {ds}")

    time.sleep(5)

print(f"\n{'='*50}")
print("  FINAL done!")
print(f"{'='*50}")
