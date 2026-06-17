"""매일 오전 6시: 오늘의말씀 본문 → 고퀄리티 음악 영상 카드 8장 → garden___church 인스타+페이스북"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, re
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

TODAY = datetime.now()
DATE_STR = TODAY.strftime("%Y-%m-%d")
DATE_KR = TODAY.strftime("%m/%d")
WEEKDAYS = ['월','화','수','목','금','토','일']
DAY_KR = WEEKDAYS[TODAY.weekday()]

W, H = 1080, 1350
FPS = 2

# === 폰트 (감성 글씨체) ===
def gf(size, bold=False):
    # 나눔명조 > 바탕체 > 맑은고딕 순서로 시도
    fonts_bold = [
        "C:/Windows/Fonts/NanumMyeongjoBold.ttf",
        "C:/Windows/Fonts/batangb.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
    ]
    fonts_reg = [
        "C:/Windows/Fonts/NanumMyeongjo.ttf",
        "C:/Windows/Fonts/batang.ttc",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in (fonts_bold if bold else fonts_reg):
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

def wrap_text(text, max_chars=22):
    """긴 텍스트를 줄바꿈"""
    lines = []
    for line in text.split("\n"):
        while len(line) > max_chars:
            lines.append(line[:max_chars])
            line = line[max_chars:]
        lines.append(line)
    return "\n".join(lines)

# === 오늘의 말씀 파일 읽기 ===
def load_today_word():
    paths = [
        os.path.join(HOME, "Documents", "오늘의말씀", f"{DATE_STR}.txt"),
        os.path.join(HOME, "OneDrive", "바탕 화면", "오늘의말씀", f"{DATE_STR}.txt"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return f.read()
    return None

def parse_word(content):
    """말씀 본문을 섹션별로 파싱"""
    sections = {
        "header": "", "ref": "", "title": "", "verse": "",
        "meditation_title": "", "meditation": "",
        "questions": [], "practice": "", "prayer": ""
    }

    # 성경 구절 참조 (예: 사무엘상 31:7-13)
    ref_match = re.search(r'(창세기|출애굽기|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘상|사무엘하|열왕기상|열왕기하|역대상|역대하|에스라|느헤미야|에스더|욥기|시편|잠언|전도서|아가|이사야|예레미야|예레미야애가|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태복음|마가복음|누가복음|요한복음|사도행전|로마서|고린도전서|고린도후서|갈라디아서|에베소서|빌립보서|골로새서|데살로니가전서|데살로니가후서|디모데전서|디모데후서|디도서|빌레몬서|히브리서|야고보서|베드로전서|베드로후서|요한일서|요한이서|요한삼서|유다서|요한계시록)\s*\d+[:\s]*\d+[\-–~]*\d*', content)
    if ref_match:
        sections["ref"] = ref_match.group().strip()

    # 소제목 (** 사이)
    title_match = re.search(r'\*\*(.+?)\*\*', content)
    if title_match:
        sections["title"] = title_match.group(1).strip()

    # 본문 (절 번호가 있는 부분)
    verse_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if re.match(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹]+', line) or re.match(r'^\d+[.\s]', line):
            verse_lines.append(line)
    sections["verse"] = "\n".join(verse_lines) if verse_lines else ""

    # 묵상
    med_match = re.search(r'\*오늘의 묵상\s*\n"?(.+?)"?\n\n(.+?)(?=\*묵상을 위한 질문|\*오늘의 실천|\*오늘의 기도|$)', content, re.DOTALL)
    if med_match:
        sections["meditation_title"] = med_match.group(1).strip().strip('"')
        sections["meditation"] = med_match.group(2).strip()

    # 질문
    q_match = re.search(r'\*묵상을 위한 질문\s*\n(.+?)(?=\*오늘의 실천|\*오늘의 기도|$)', content, re.DOTALL)
    if q_match:
        for line in q_match.group(1).strip().split("\n"):
            line = line.strip().lstrip('-').strip()
            if line and not line.startswith('※'):
                sections["questions"].append(line)

    # 실천
    pr_match = re.search(r'\*오늘의 실천\s*\n(.+?)(?=\*오늘의 기도|$)', content, re.DOTALL)
    if pr_match:
        sections["practice"] = pr_match.group(1).strip()

    # 기도
    pray_match = re.search(r'\*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray_match:
        sections["prayer"] = pray_match.group(1).strip()

    return sections

# === 고퀄리티 카드 생성 ===
CREAM = (252, 249, 242)
WARM = (245, 238, 225)
OLIVE = (85, 95, 70)
BROWN = (139, 100, 60)
GOLD = (180, 140, 70)
DARK_TEXT = (45, 40, 35)
BODY_TEXT = (80, 75, 65)
LIGHT_TEXT = (150, 140, 125)

def make_card(card_type, data, page, total):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # 미묘한 텍스처 (그레인 효과)
    import random
    random.seed(page * 100)
    for _ in range(3000):
        x, y2 = random.randint(0,W), random.randint(0,H)
        v = random.randint(-5, 5)
        c = tuple(max(0,min(255,CREAM[i]+v)) for i in range(3))
        d.point((x,y2), fill=c)

    # 상단 얇은 골드 라인
    d.rectangle([0, 0, W, 2], fill=GOLD)

    # 십자가 (미니멀)
    cx = W // 2
    d.rectangle([cx-1, 40, cx+1, 75], fill=(*GOLD, 120))
    d.rectangle([cx-12, 55, cx+12, 57], fill=(*GOLD, 120))

    # 날짜 + 교회명
    d.text((60, 45), "동산감리교회", font=gf_sans(14), fill=LIGHT_TEXT)
    date_txt = f"{DATE_KR} ({DAY_KR})"
    bb = d.textbbox((0,0), date_txt, font=gf_sans(14))
    d.text((W-(bb[2]-bb[0])-60, 45), date_txt, font=gf_sans(14), fill=LIGHT_TEXT)

    if card_type == "cover":
        # 표지
        y = 350
        y = tc(d, y, "오늘의 말씀", gf_sans(18), LIGHT_TEXT, 20)
        y += 20
        d.rectangle([W//2-40, y, W//2+40, y+1], fill=GOLD)
        y += 30
        y = tc(d, y, data.get("ref",""), gf(36, True), DARK_TEXT, 16)
        y += 20
        y = tc(d, y, data.get("title",""), gf(28), BROWN, 12)
        y += 40
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 30
        y = tc(d, y, f"{DATE_KR} {DAY_KR}요일", gf_sans(16), LIGHT_TEXT)

    elif card_type == "verse":
        # 말씀 본문
        y = 140
        y = tc(d, y, data.get("ref",""), gf_sans(16), GOLD, 15)
        y += 10
        d.rectangle([W//2-30, y, W//2+30, y+1], fill=GOLD)
        y += 25

        # 큰 따옴표
        tc(d, y-5, "\u201C", gf(50), (*GOLD, 80))
        y += 30

        verse = data.get("text","")
        verse_wrapped = wrap_text(verse, 24)
        for ln in verse_wrapped.split("\n")[:16]:
            if not ln.strip(): y += 10; continue
            y = tc(d, y, ln, gf(22), DARK_TEXT, 12)

        y += 5
        bb = d.textbbox((0,0), "\u201D", font=gf(50))
        d.text(((W-(bb[2]-bb[0]))/2, y), "\u201D", font=gf(50), fill=(*GOLD, 80))

    elif card_type == "meditation":
        # 묵상
        y = 150
        y = tc(d, y, "묵상", gf_sans(14), GOLD, 15)
        y += 5
        y = tc(d, y, data.get("title",""), gf(32, True), DARK_TEXT, 14)
        y += 15
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 25

        med = data.get("body","")
        med_wrapped = wrap_text(med, 26)
        for ln in med_wrapped.split("\n")[:20]:
            if not ln.strip(): y += 10; continue
            y = tc(d, y, ln, gf(20), BODY_TEXT, 11)

    elif card_type == "question":
        # 질문
        y = 280
        y = tc(d, y, "묵상을 위한 질문", gf_sans(14), GOLD, 25)
        y += 10
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 35

        for q in data.get("questions", [])[:2]:
            q_wrapped = wrap_text(q, 24)
            for ln in q_wrapped.split("\n"):
                y = tc(d, y, ln, gf(22), DARK_TEXT, 12)
            y += 30

    elif card_type == "practice":
        # 실천
        y = 280
        y = tc(d, y, "오늘의 실천", gf_sans(14), GOLD, 25)
        y += 10
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 35

        prac = data.get("text","")
        prac_wrapped = wrap_text(prac, 24)
        for ln in prac_wrapped.split("\n")[:12]:
            if not ln.strip(): y += 10; continue
            y = tc(d, y, ln, gf(22), DARK_TEXT, 13)

    elif card_type == "prayer":
        # 기도 (어두운 배경)
        img = Image.new("RGB", (W, H), (30, 28, 38))
        d = ImageDraw.Draw(img)
        random.seed(700)
        for _ in range(2000):
            x, y2 = random.randint(0,W), random.randint(0,H)
            v = random.randint(-3, 3)
            d.point((x,y2), fill=(30+v, 28+v, 38+v))

        d.rectangle([0, 0, W, 2], fill=GOLD)
        d.rectangle([W//2-1, 40, W//2+1, 75], fill=(*GOLD, 80))
        d.rectangle([W//2-12, 55, W//2+12, 57], fill=(*GOLD, 80))

        y = 200
        y = tc(d, y, "오늘의 기도", gf_sans(14), GOLD, 25)
        y += 10
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 30

        prayer = data.get("text","")
        prayer_wrapped = wrap_text(prayer, 24)
        for ln in prayer_wrapped.split("\n")[:18]:
            if not ln.strip(): y += 10; continue
            y = tc(d, y, ln, gf(21), (220, 215, 205), 12)

    elif card_type == "closing":
        # 마무리
        y = 400
        verse = data.get("verse","")
        verse_wrapped = wrap_text(verse, 20)
        y = tc(d, y, verse_wrapped, gf(28, True), DARK_TEXT, 14)
        y += 30
        d.rectangle([W//2-25, y, W//2+25, y+1], fill=GOLD)
        y += 25
        y = tc(d, y, data.get("ref",""), gf_sans(18), GOLD, 15)
        y += 40
        y = tc(d, y, "동산감리교회", gf_sans(18), LIGHT_TEXT)
        y = tc(d, y+5, "@garden___church", gf_sans(14), LIGHT_TEXT)

    # 하단 (기도 카드 제외)
    if card_type != "prayer":
        d.rectangle([W//2-20, H-70, W//2+20, H-68], fill=GOLD)
    tc(d, H-55, f"{page}/{total}", gf_sans(12), LIGHT_TEXT if card_type != "prayer" else (100,95,85))

    return img

# === 메인 ===
def main():
    print("=" * 50)
    print(f"  Bible Card - {DATE_KR} ({DAY_KR})")
    print("=" * 50)

    # 1. 오늘의 말씀 읽기
    print("\n[1/4] Loading today's word...")
    content = load_today_word()
    if not content:
        print("  No file found for today. Using AI generation.")
        API_KEY = ""
        for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
            if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]
        r = requests.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
        }, json={"model": "claude-sonnet-4-6", "max_tokens": 2000, "messages": [{"role":"user","content":f"오늘({DATE_STR} {DAY_KR}요일) 성경 묵상을 작성해줘. 형식: 말씀 본문(새번역) + 묵상 + 질문2개 + 실천 + 기도"}]})
        content = r.json()["content"][0]["text"]

    sections = parse_word(content)
    print(f"  {sections['ref']} - {sections['meditation_title']}")

    # 2. 카드 8장 생성
    print("\n[2/4] Creating 8 premium cards...")
    verse_text = sections['verse'] if sections['verse'] else content[content.find('⁷'):content.find('*오늘의 묵상')][:500]
    med_text = sections['meditation']
    med_half = len(med_text)//2 if med_text else 0
    closing_verse = sections['questions'][0] if sections['questions'] else sections['ref']

    cards = [
        ("cover", {"ref": sections['ref'], "title": sections['meditation_title']}),
        ("verse", {"ref": sections['ref'], "text": verse_text[:350]}),
        ("verse", {"ref": sections['ref'], "text": verse_text[350:]}) if len(verse_text) > 350 else ("verse", {"ref": sections['ref'], "text": verse_text}),
        ("meditation", {"title": sections['meditation_title'], "body": med_text[:400]}),
        ("meditation", {"title": "", "body": med_text[400:]}) if len(med_text) > 400 else ("question", {"questions": sections['questions']}),
        ("question", {"questions": sections['questions']}),
        ("practice", {"text": sections['practice']}),
        ("prayer", {"text": sections['prayer']}),
    ]

    # 중복 제거
    if len(verse_text) <= 350:
        cards[2] = ("meditation", {"title": sections['meditation_title'], "body": med_text[:400]})
        cards[3] = ("meditation", {"title": "", "body": med_text[400:800]})
        cards[4] = ("question", {"questions": sections['questions']})
        cards[5] = ("practice", {"text": sections['practice']})
        cards[6] = ("prayer", {"text": sections['prayer']})
        cards[7] = ("closing", {"verse": sections['ref'], "ref": "동산감리교회"})

    OUT = os.path.join(HOME, "lighthouse-media", "output", "bible-cards")
    os.makedirs(OUT, exist_ok=True)
    FRAMES = os.path.join(OUT, "frames")

    img_urls = []
    for i, (ctype, cdata) in enumerate(cards):
        img = make_card(ctype, cdata, i+1, 8)
        path = os.path.join(OUT, f"card_{i+1}.jpg")
        img.save(path, "JPEG", quality=95)

        with open(path, 'rb') as f:
            enc = base64.b64encode(f.read()).decode()
        ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': enc, 'type': 'base64'})
        url = ir.json().get('data',{}).get('link')
        if url: img_urls.append(url)
        print(f"  {i+1}/8 [{ctype}]: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    # 3. 음악 포함 영상 생성
    print("\n[3/4] Creating video with BGM...")
    os.makedirs(FRAMES, exist_ok=True)
    fnum = 0
    for i, (ctype, cdata) in enumerate(cards):
        img = make_card(ctype, cdata, i+1, 8)
        dur = 6 if ctype in ['cover','closing'] else 8
        for f in range(dur * FPS):
            img.save(os.path.join(FRAMES, f"frame_{fnum:05d}.png"))
            fnum += 1

    bgm = os.path.join(BGM_DIR, "calm-piano.mp3")
    total_dur = sum(6 if c[0] in ['cover','closing'] else 8 for c in cards)
    vpath = os.path.join(OUT, f"bible_{DATE_STR}.mp4")

    subprocess.run([FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "frame_%05d.png"),
                    "-i", bgm, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k",
                    "-filter_complex", f"[1:a]afade=t=in:d=2,afade=t=out:st={total_dur-3}:d=3,volume=0.25[a]",
                    "-map", "0:v", "-map", "[a]",
                    "-vf", f"scale={W}:{H},fps=30", "-t", str(total_dur), "-shortest", vpath],
                   capture_output=True, timeout=120)
    shutil.rmtree(FRAMES, ignore_errors=True)

    if os.path.exists(vpath):
        sz = os.path.getsize(vpath)/(1024*1024)
        print(f"  Video: {sz:.1f}MB ({total_dur}s)")
    else:
        print("  Video FAIL")

    # 4. 인스타 + 페이스북 게시
    print("\n[4/4] Posting...")
    caption = f"오늘의 말씀 | {DATE_KR} ({DAY_KR})\n\n{sections['ref']}\n\n\"{sections['meditation_title']}\"\n\n{sections['meditation'][:150]}...\n\n오늘의 실천:\n{sections['practice'][:100]}\n\n동산감리교회\n@garden___church\n\n#오늘의말씀 #성경말씀 #묵상 #기도 #교회 #말씀카드 #동산감리교회 #매일묵상 #성경 #은혜 #감사 #예배 #기독교 #새벽기도 #하나님"

    # 인스타 캐러셀
    if len(img_urls) >= 2 and CHURCH_IG_ID:
        ids = []
        for u in img_urls:
            r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'image_url': u, 'is_carousel_item': 'true', 'access_token': CHURCH_TOKEN})
            if 'id' in r.json(): ids.append(r.json()['id'])
            time.sleep(2)
        if len(ids) >= 2:
            r = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media', data={'media_type': 'CAROUSEL', 'children': ','.join(ids), 'caption': caption, 'access_token': CHURCH_TOKEN})
            if 'id' in r.json():
                time.sleep(8)
                r2 = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_IG_ID}/media_publish', data={'creation_id': r.json()['id'], 'access_token': CHURCH_TOKEN})
                print(f"  IG: {'OK' if 'id' in r2.json() else 'FAIL'}")

    # 페이스북
    if img_urls and CHURCH_PAGE_ID:
        fb_msg = f"오늘의 말씀 | {DATE_KR} ({DAY_KR})\n\n{sections['ref']}\n\n{sections['meditation_title']}\n\n{sections['meditation'][:300]}\n\n오늘의 실천: {sections['practice'][:150]}\n\n기도: {sections['prayer'][:200]}\n\n동산감리교회"
        fb = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/photos', data={'url': img_urls[0], 'message': fb_msg, 'access_token': CHURCH_TOKEN})
        print(f"  FB: {'OK' if 'id' in fb.json() else fb.json()}")

    # 영상도 페이스북에
    if os.path.exists(vpath) and CHURCH_PAGE_ID:
        with open(vpath, 'rb') as f:
            fb_v = requests.post(f'https://graph.facebook.com/v21.0/{CHURCH_PAGE_ID}/videos',
                files={'source': (os.path.basename(vpath), f, 'video/mp4')},
                data={'description': caption[:500], 'access_token': CHURCH_TOKEN})
        print(f"  FB Video: {'OK' if 'id' in fb_v.json() else 'FAIL'}")

    print(f"\n{'='*50}")
    print(f"  Done! @garden___church + FB")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
