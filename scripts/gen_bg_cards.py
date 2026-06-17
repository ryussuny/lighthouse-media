"""6일분 배경 이미지 적용 카드 생성 + SNS 게시"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, math, random, time, base64
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
CONFIG_DIR = os.path.join(REPO_DIR, "config")
OUTPUT_DIR = os.path.join(REPO_DIR, "output", "today-cards")
WORD_DIR = os.path.join(HOME, "Documents", "오늘의말씀")
import requests

tokens = json.load(open(os.path.join(CONFIG_DIR, "tokens.json"), encoding='utf-8'))
TOKEN = tokens.get('church_page', tokens.get('instagram', ''))
IG_ID = tokens.get('church_ig_id', '')
PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"

WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']
W, H = 1080, 1350

def font(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def text_size(draw, text, fnt):
    bb = draw.textbbox((0, 0), text, font=fnt)
    return bb[2] - bb[0], bb[3] - bb[1]

def load_schedule():
    with open(os.path.join(CONFIG_DIR, "bible-schedule.json"), 'r', encoding='utf-8') as f:
        return json.load(f)

def get_entry(schedule, date_str):
    for e in schedule:
        if e['date'] == date_str: return e
    return None

def get_series_number(schedule, date_str):
    for i, e in enumerate(schedule):
        if e['date'] == date_str: return i + 1
    return 1

def get_series_book(ref):
    m = re.match(r'(삼하|삼상|왕상|왕하|대상|대하|사무엘상|사무엘하|\S+)', ref)
    book_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하', '대상': '역대상', '대하': '역대하'}
    if m:
        return book_map.get(m.group(1), m.group(1))
    return '사무엘하'

def get_chapter(ref):
    m = re.search(r'(\d+):', ref)
    return m.group(1) if m else ''

def load_devotional(date_str):
    path = os.path.join(WORD_DIR, f"{date_str}.txt")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def get_key_message(content, schedule_title):
    if content:
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('📖') and i + 1 < len(lines):
                nxt = lines[i+1].strip().strip('"\u201c\u201d"')
                if nxt: return nxt
        if len(lines) > 1:
            second = lines[1].strip().strip('"\u201c\u201d"')
            if second and not second.startswith('#'): return second
    return schedule_title

def split_title(title):
    if not title: return ('', '오늘의 말씀')
    if len(title) <= 12: return ('', title)
    for sep in [' — ', '—', ', ', ' – ']:
        if sep in title:
            parts = title.split(sep, 1)
            return (parts[0].strip(), parts[1].strip())
    mid = len(title) // 2
    best = -1
    for i in range(max(0, mid - 5), min(len(title), mid + 5)):
        if i < len(title) and title[i] == ' ':
            best = i
            break
    if best > 0: return (title[:best].strip(), title[best:].strip())
    return (title[:mid], title[mid:])

# ═══════════════════════════════════════════════════════
# 배경 이미지 생성
# ═══════════════════════════════════════════════════════
def create_bible_bg(seed=0):
    random.seed(seed)
    img = Image.new('RGB', (W, H))
    px = img.load()
    for y in range(H):
        ratio = y / H
        if ratio < 0.4:
            t = ratio / 0.4
            r, g, b = int(12+18*t), int(8+14*t), int(32+20*t)
        elif ratio < 0.65:
            t = (ratio-0.4)/0.25
            r, g, b = int(30+45*t), int(22+20*t), int(52+15*t)
        else:
            t = (ratio-0.65)/0.35
            r, g, b = int(75-35*t), int(42-15*t), int(67-30*t)
        for x in range(W):
            px[x, y] = (r, g, b)
    # 빛줄기
    cx, cy = W//2, int(H*0.28)
    for y in range(H):
        for x in range(W):
            dx, dy = x-cx, y-cy
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 600:
                intensity = (1-dist/600)**3
                if dy > -50:
                    af = max(0, 1-abs(dx)/(300+dy*0.8))
                    intensity *= af
                r2, g2, b2 = px[x, y]
                px[x, y] = (min(255,r2+int(55*intensity)), min(255,g2+int(45*intensity)), min(255,b2+int(65*intensity)))
    # 산
    d = ImageDraw.Draw(img)
    my_base = int(H*0.78)
    pts = [(0, H)]
    for x in range(0, W+20, 20):
        h = abs(math.sin(x*0.005+seed)*60 + math.sin(x*0.012+seed*2)*30 + math.sin(x*0.003+seed*0.5)*80)
        pts.append((x, int(my_base - h)))
    pts.append((W, H))
    d.polygon(pts, fill=(15, 12, 22))
    # 별
    for _ in range(120):
        sx, sy = random.randint(20,W-20), random.randint(20,int(H*0.7))
        br = random.randint(20, 70)
        sz = random.choice([1,1,1,2])
        for ddx in range(sz):
            for ddy in range(sz):
                nx, ny = sx+ddx, sy+ddy
                if 0<=nx<W and 0<=ny<H:
                    r3,g3,b3 = px[nx,ny]
                    px[nx,ny] = (min(255,r3+br),min(255,g3+br),min(255,b3+br+5))
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    return img

# ═══════════════════════════════════════════════════════
# 카드 생성
# ═══════════════════════════════════════════════════════
def generate_card(date_str, entry, series_num, content, bg_seed):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_kr = WEEKDAYS[dt.weekday()]
    date_full = f"{dt.strftime('%Y')} . {dt.strftime('%m/%d')}  {day_kr}요일  매일 묵상"
    ref = entry['ref']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)
    line1, line2 = split_title(entry['title'])
    ref_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하'}
    ref_full = ref
    for short, full in ref_map.items():
        if ref.startswith(short + ' '): ref_full = ref.replace(short, full, 1); break
    key_msg = get_key_message(content, entry['title'])

    # 배경
    img = create_bible_bg(bg_seed)
    # 반투명 오버레이
    overlay = Image.new('RGBA', (W, H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    for y in range(500):
        a = max(60, min(180, int(160-y*0.12)))
        od.line([(0,y),(W,y)], fill=(0,0,0,a))
    for y in range(500, 900):
        od.line([(0,y),(W,y)], fill=(0,0,0,100))
    for y in range(900, H):
        a = min(190, int(100+(y-900)*0.15))
        od.line([(0,y),(W,y)], fill=(0,0,0,a))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

    d = ImageDraw.Draw(img)
    PAD_L, PAD_R = 60, 60
    GOLD = (230,195,60)
    GOLD_BAR = (210,178,55)
    WHITE = (255,255,255)
    LIGHT_GRAY = (200,200,210)
    MUTED_GRAY = (120,120,135)
    DIM_GRAY = (65,62,82)

    # 골드 바
    d.rectangle([0,0,W,6], fill=GOLD_BAR)
    d.rectangle([0,H-4,W,H], fill=GOLD_BAR)

    # 시리즈 라벨
    y = 40
    d.text((PAD_L, y), f"{book_name} \u00b7 SERMON SERIES {series_num:02d}", font=font(16,True), fill=LIGHT_GRAY)
    y += 32
    d.text((PAD_L, y), f"{book_name} {chapter}장", font=font(19,False), fill=MUTED_GRAY)

    # 십자가
    cx_c, cy_c = W-140, 115
    d.line([(cx_c,cy_c-70),(cx_c,cy_c+70)], fill=(120,115,145), width=2)
    d.line([(cx_c-42,cy_c-11),(cx_c+42,cy_c-11)], fill=(120,115,145), width=2)

    # 메인 타이틀
    f_big = font(82, True)
    title_lines = []
    if line1 and line2:
        if len(line1) > 7:
            parts = line1.split(' ', 1)
            if len(parts)==2 and len(parts[0])>=2: title_lines = [parts[0], parts[1], line2]
            else: title_lines = [line1, line2]
        else: title_lines = [line1, line2]
    elif line2:
        if len(line2) > 7:
            mid = len(line2)//2; sp = line2.rfind(' ',0,mid+4)
            if sp > 0: title_lines = [line2[:sp], line2[sp+1:]]
            else: title_lines = [line2]
        else: title_lines = [line2]

    y_t = 155
    last_idx = len(title_lines) - 1
    for i, tl in enumerate(title_lines):
        color = GOLD if i == last_idx else WHITE
        d.text((PAD_L+3, y_t+3), tl, font=f_big, fill=(0,0,0))
        d.text((PAD_L, y_t), tl, font=f_big, fill=color)
        _, th = text_size(d, tl, f_big)
        y_t += th + 18

    # BIBLE TEXT
    y_bt = y_t + 70
    d.text((PAD_L, y_bt), "BIBLE TEXT", font=font(16,True), fill=MUTED_GRAY)
    y_bt += 32
    d.text((PAD_L+2, y_bt+2), ref_full, font=font(32,True), fill=(0,0,0))
    d.text((PAD_L, y_bt), ref_full, font=font(32,True), fill=WHITE)
    y_bt += 46
    d.text((PAD_L, y_bt), date_full, font=font(16,False), fill=MUTED_GRAY)

    # KEY MESSAGE 박스
    box_x, box_y = 400, y_bt-82
    box_w = W-PAD_R-400
    bp = 20
    qt = key_msg if len(key_msg)<=20 else key_msg[:20]
    # 본문 첫 문장 2개 (마침표까지) — 절대 끊기지 않게
    sm_text = ''
    if content:
        for ln in content.split('\n'):
            ln = ln.strip()
            if ln and not any(ln.startswith(c) for c in ['📖','#','✦','🙏','동산','@','"','\u201c']) and len(ln)>10:
                # 첫 2문장 추출
                sents = re.split(r'(?<=[.!?])\s+', ln)
                picked = ''
                for s in sents[:2]:
                    if len(picked) + len(s) + 1 <= 65:
                        picked = (picked + ' ' + s).strip()
                    else:
                        break
                sm_text = picked if picked else sents[0][:55]
                break
    # 박스 안에 3줄까지
    sm_lines = []
    if sm_text:
        remaining = sm_text
        while remaining:
            if len(remaining) <= 28:
                sm_lines.append(remaining); break
            cut = remaining[:28].rfind(' ')
            if cut < 8: cut = 28
            sm_lines.append(remaining[:cut])
            remaining = remaining[cut:].lstrip()
    sm_lines = sm_lines[:3]
    box_h = 110 + len(sm_lines) * 26
    d.rounded_rectangle([box_x,box_y,box_x+box_w,box_y+box_h], radius=5, fill=(20,18,32), outline=DIM_GRAY, width=1)
    d.text((box_x+bp, box_y+22), f'"{qt}"', font=font(18,False), fill=LIGHT_GRAY)
    sm_y = box_y + 56
    for sl in sm_lines:
        d.text((box_x+bp, sm_y), sl, font=font(16,False), fill=LIGHT_GRAY)
        sm_y += 26
    d.text((box_x+bp, box_y+box_h-32), "— KEY MESSAGE", font=font(14,True), fill=MUTED_GRAY)

    # 묵상 + 질문
    if content:
        y_mid = box_y + box_h + 50
        d.line([(PAD_L, y_mid), (PAD_L+60, y_mid)], fill=GOLD_BAR, width=2)
        y_mid += 20

        # 묵상: 완결된 문장들만 추출 (마침표로 끝나는 것)
        med_text = ''
        in_med = False
        skip_title = True
        for ln in content.split('\n'):
            ln = ln.strip()
            if '오늘의 묵상' in ln: in_med = True; continue
            if in_med:
                if skip_title and (ln.startswith('"') or ln.startswith('\u201c') or not ln):
                    skip_title = False; continue
                if ln and not any(ln.startswith(c) for c in ['✦','🙏']):
                    med_text = ln; break

        if med_text:
            # 문장 단위로 분리 (마침표/다./요./니다. 등)
            sentences = re.split(r'(?<=[.!?])\s+', med_text)

            # 6줄 * 32자 = 넓게 활용
            f_med = font(19, False)
            max_chars = 32
            max_lines = 6

            # 문장을 하나씩 추가하면서 줄 수 계산
            display = ''
            for s in sentences:
                s = s.strip()
                if not s: continue
                test = (display + ' ' + s).strip() if display else s
                # 이 텍스트가 몇 줄 차지하는지 계산
                lines_needed = 0
                temp = test
                while temp:
                    if len(temp) <= max_chars:
                        lines_needed += 1; break
                    cut = temp[:max_chars].rfind(' ')
                    if cut < 8: cut = max_chars
                    lines_needed += 1
                    temp = temp[cut:].lstrip()
                if lines_needed <= max_lines:
                    display = test
                else:
                    break  # 이 문장 추가하면 넘치므로 중단

            if not display:
                display = sentences[0][:120] if sentences else med_text[:100]

            # 렌더링
            remaining = display
            line_count = 0
            while remaining and line_count < max_lines:
                if len(remaining) <= max_chars:
                    d.text((PAD_L+2,y_mid+2), remaining, font=f_med, fill=(0,0,0))
                    d.text((PAD_L,y_mid), remaining, font=f_med, fill=(200,198,210))
                    y_mid += 32; break
                cut = remaining[:max_chars].rfind(' ')
                if cut < 8: cut = max_chars
                d.text((PAD_L+2,y_mid+2), remaining[:cut], font=f_med, fill=(0,0,0))
                d.text((PAD_L,y_mid), remaining[:cut], font=f_med, fill=(200,198,210))
                y_mid += 32; remaining = remaining[cut:].lstrip(); line_count += 1

        y_mid += 25

        # 질문: 완결된 질문만 (? 로 끝나는 것)
        question = ''
        found_q = False
        for ln in content.split('\n'):
            ln = ln.strip()
            if '오늘의 질문' in ln: found_q = True; continue
            if found_q and ln and not ln.startswith('✦'):
                # 첫 번째 ? 까지만
                qi = ln.find('?')
                if qi > 0:
                    question = ln[:qi+1]
                else:
                    question = ln
                break
        if question:
            d.line([(PAD_L,y_mid),(PAD_L+40,y_mid)], fill=DIM_GRAY, width=1)
            y_mid += 18
            d.text((PAD_L,y_mid), "TODAY'S QUESTION", font=font(13,True), fill=MUTED_GRAY)
            y_mid += 28
            f_q = font(17, False)
            qr = question
            q_count = 0
            while qr and q_count < 3:
                if len(qr) <= 34:
                    d.text((PAD_L,y_mid), qr, font=f_q, fill=(160,158,175))
                    break
                cut = qr[:34].rfind(' ')
                if cut < 8: cut = 34
                d.text((PAD_L,y_mid), qr[:cut], font=f_q, fill=(160,158,175))
                y_mid += 28; qr = qr[cut:].lstrip(); q_count += 1

    # 하단
    y_ch = H - 95
    d.text((PAD_L,y_ch), "동산감리교회", font=font(18,True), fill=LIGHT_GRAY)
    d.text((PAD_L,y_ch+28), "@garden___church", font=font(14,False), fill=MUTED_GRAY)
    si = f"#{series_num:02d} of {book_name}"
    sw,_ = text_size(d, si, font(13,False))
    d.text((W-PAD_R-sw, y_ch+28), si, font=font(13,False), fill=MUTED_GRAY)

    return img

# ═══════════════════════════════════════════════════════
# 캡션 생성
# ═══════════════════════════════════════════════════════
def build_caption(date_str, entry, series_num, content):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]
    ref = entry['ref']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)
    ref_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하'}
    ref_full = ref
    for short, full in ref_map.items():
        if ref.startswith(short+' '): ref_full = ref.replace(short, full, 1); break
    key_msg = get_key_message(content, entry['title'])
    summary = ''
    if content:
        for line in content.split('\n'):
            line = line.strip()
            if line and not any(line.startswith(c) for c in ['📖','#','✦','🙏','동산','@','"','\u201c']) and len(line)>15:
                summary = line[:60]; break
    caption = f"오늘의 말씀 | {dt.strftime('%m/%d')} ({day_kr})\n"
    caption += f"📖 {ref_full}\n"
    caption += f'"{key_msg}"\n\n'
    if summary: caption += f"{summary}\n\n"
    caption += f"{book_name}를 하루 한 장씩 읽으며,\n"
    caption += f"다윗의 이야기 속에서 하나님의 마음을 만납니다.\n\n"
    caption += f"✦ {book_name} 시리즈 #{series_num}\n\n"
    caption += f"동산감리교회\n@garden___church\n\n"
    caption += f"#오늘의말씀 #{book_name} #{book_name}{chapter}장 #성경말씀 #묵상\n"
    caption += f"#기도 #교회 #말씀카드 #동산감리교회 #매일묵상\n"
    caption += f"#성경 #은혜 #다윗 #기독교 #하나님 #예배\n"
    caption += f"#BibleVerse #DailyDevotional"
    return caption

# ═══════════════════════════════════════════════════════
# 업로드 & 포스팅
# ═══════════════════════════════════════════════════════
def upload_imgur(image_path):
    for attempt in range(3):
        try:
            with open(image_path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                data={'image': enc, 'type': 'base64'}, timeout=30)
            url = r.json().get('data',{}).get('link')
            if url:
                print(f"    Imgur OK")
                return url
        except Exception as e:
            print(f"    Imgur attempt {attempt+1}: {e}")
        time.sleep(5)
    return None

def post_instagram(image_url, caption):
    if not IG_ID or not TOKEN: return None
    try:
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media',
            data={'image_url': image_url, 'caption': caption, 'access_token': TOKEN}, timeout=30)
        cid = r.json().get('id')
        if not cid: print(f"    IG container fail: {r.json()}"); return None
        time.sleep(8)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
            data={'creation_id': cid, 'access_token': TOKEN}, timeout=30)
        result = r2.json()
        if 'id' in result: print(f"    IG OK: {result['id']}"); return result['id']
        print(f"    IG fail: {result}"); return None
    except Exception as e:
        print(f"    IG error: {e}"); return None

def post_facebook(image_url, caption):
    if not PAGE_ID or not TOKEN: return None
    try:
        r = requests.post(f'https://graph.facebook.com/v21.0/{PAGE_ID}/photos',
            data={'url': image_url, 'message': caption[:500], 'access_token': TOKEN}, timeout=30)
        data = r.json()
        if 'id' in data: print(f"    FB OK: {data['id']}"); return data['id']
        print(f"    FB fail: {data}"); return None
    except Exception as e:
        print(f"    FB error: {e}"); return None

# ═══════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════
def main():
    schedule = load_schedule()
    dates = ['2026-05-10','2026-05-11','2026-05-12','2026-05-13','2026-05-14','2026-05-15']
    seeds = [10, 25, 42, 60, 77, 95]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 55)
    print("  오늘의 말씀 카드 6일분 — 배경 이미지 적용 + SNS 게시")
    print("=" * 55)

    for idx, date_str in enumerate(dates):
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        day_kr = WEEKDAYS[dt.weekday()]
        entry = get_entry(schedule, date_str)
        if not entry: continue
        series_num = get_series_number(schedule, date_str)
        content = load_devotional(date_str)

        print(f"\n  [{idx+1}/6] {date_str} ({day_kr}) — {entry['ref']} {entry['title']}")

        # 카드 생성
        card = generate_card(date_str, entry, series_num, content, seeds[idx])
        save_path = os.path.join(OUTPUT_DIR, f"today_{date_str}.jpg")
        card.save(save_path, "JPEG", quality=95)
        print(f"    Card saved")

        # 캡션
        caption = build_caption(date_str, entry, series_num, content)

        # Imgur 업로드
        image_url = upload_imgur(save_path)
        if not image_url:
            print(f"    SKIP posting: Imgur failed")
            continue

        # Instagram 게시
        post_instagram(image_url, caption)
        time.sleep(3)

        # Facebook 게시
        post_facebook(image_url, caption)
        time.sleep(5)

        print(f"    Done: {date_str}")

    print(f"\n{'=' * 55}")
    print("  Complete! 6 cards posted.")
    print(f"{'=' * 55}")

if __name__ == '__main__':
    main()
