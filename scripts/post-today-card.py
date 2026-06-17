"""
오늘의 말씀 카드 1장 생성 → Instagram + Facebook 포스팅
Usage:
  python post-today-card.py                  # 오늘 날짜
  python post-today-card.py 2026-05-07       # 특정 날짜
  python post-today-card.py 2026-05-06 2026-05-07  # 여러 날짜
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, time, base64, subprocess, math
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import requests

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════
HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
CONFIG_DIR = os.path.join(REPO_DIR, "config")
OUTPUT_DIR = os.path.join(REPO_DIR, "output", "today-cards")
DASHBOARD_PUBLIC = os.path.join(REPO_DIR, "dashboard", "public")
WORD_DIR = os.path.join(HOME, "Documents", "오늘의말씀")

tokens = json.load(open(os.path.join(CONFIG_DIR, "tokens.json"), encoding='utf-8'))
TOKEN = tokens.get('church_page', tokens.get('instagram', ''))
IG_ID = tokens.get('church_ig_id', '')
PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"

WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']
W, H = 1080, 1350

# ═══════════════════════════════════════════════════════════════
# 색상 팔레트
# ═══════════════════════════════════════════════════════════════
BG_TOP = (22, 20, 38)
BG_BOTTOM = (12, 10, 22)
GOLD = (230, 195, 60)
GOLD_BAR = (210, 178, 55)
WHITE = (255, 255, 255)
LIGHT_GRAY = (160, 160, 170)
MUTED_GRAY = (95, 95, 108)
DIM_GRAY = (50, 48, 62)
BOX_BG = (32, 30, 48)
BOX_BORDER = (65, 62, 82)

# ═══════════════════════════════════════════════════════════════
# 폰트
# ═══════════════════════════════════════════════════════════════
def font(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def text_size(draw, text, fnt):
    bb = draw.textbbox((0, 0), text, font=fnt)
    return bb[2] - bb[0], bb[3] - bb[1]

# ═══════════════════════════════════════════════════════════════
# 스케줄 로드
# ═══════════════════════════════════════════════════════════════
def load_schedule():
    path = os.path.join(CONFIG_DIR, "bible-schedule.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_entry(schedule, date_str):
    for entry in schedule:
        if entry['date'] == date_str:
            return entry
    return None

def get_series_number(schedule, date_str):
    for i, entry in enumerate(schedule):
        if entry['date'] == date_str:
            return i + 1
    return 1

def get_series_book(ref):
    """성경 참조에서 책 이름 추출"""
    m = re.match(r'(삼하|삼상|왕상|왕하|대상|대하|사무엘상|사무엘하|열왕기상|열왕기하|역대상|역대하|\S+)', ref)
    book_map = {
        '삼하': '사무엘하', '삼상': '사무엘상',
        '왕상': '열왕기상', '왕하': '열왕기하',
        '대상': '역대상', '대하': '역대하',
    }
    if m:
        short = m.group(1)
        return book_map.get(short, short)
    return '사무엘하'

# ═══════════════════════════════════════════════════════════════
# 말씀 파일 로드 & 파싱
# ═══════════════════════════════════════════════════════════════
def load_devotional(date_str):
    path = os.path.join(WORD_DIR, f"{date_str}.txt")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def parse_title_from_text(content):
    """본문에서 제목(인용구) 추출 — 📖 다음 줄의 따옴표 안 텍스트"""
    lines = content.strip().split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        # 📖 줄 다음의 따옴표 텍스트
        if line.startswith('📖') and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            m = re.match(r'["\u201c](.+?)["\u201d]', next_line)
            if m:
                return m.group(1)
            if next_line.startswith('"') or next_line.startswith('\u201c'):
                return next_line.strip('""\u201c\u201d')
        # 현재 줄에 📖과 따옴표가 같이 있는 경우
        m = re.search(r'["\u201c](.+?)["\u201d]', line)
        if m and '📖' in line:
            return m.group(1)
    # 두 번째 줄이 따옴표인 경우
    if len(lines) > 1:
        second = lines[1].strip()
        m = re.match(r'["\u201c](.+?)["\u201d]', second)
        if m:
            return m.group(1)
    return None

def parse_ref_from_text(content):
    """본문에서 성경 참조 추출"""
    m = re.search(
        r'(삼하|삼상|왕상|왕하|대상|대하|사무엘상|사무엘하|열왕기상|열왕기하|'
        r'역대상|역대하|창세기|출애굽기|시편|잠언|이사야|마태복음|요한복음|'
        r'로마서|히브리서|\S+기|\S+서)\s*\d+[:\s]*\d+[\-–~]*\d*',
        content
    )
    return m.group().strip() if m else None

def split_title(title):
    """제목을 2줄로 분할: (흰색 줄, 금색 줄)
    짧으면 금색 1줄만"""
    if not title:
        return ('', '오늘의 말씀')

    # 20자 이하면 1줄 (금색만)
    if len(title) <= 12:
        return ('', title)

    # — 또는 , 로 나뉘는 경우
    for sep in [' — ', '—', ', ', ' – ']:
        if sep in title:
            parts = title.split(sep, 1)
            return (parts[0].strip(), parts[1].strip())

    # 중간 지점 공백으로 나누기
    mid = len(title) // 2
    # 중간 근처에서 공백 찾기
    best = -1
    for i in range(max(0, mid - 5), min(len(title), mid + 5)):
        if i < len(title) and title[i] == ' ':
            best = i
            break
    if best == -1:
        # 조사/어미 앞에서 나누기
        for i in range(mid - 3, mid + 5):
            if i > 0 and i < len(title):
                best = i
                break
    if best > 0:
        return (title[:best].strip(), title[best:].strip())

    return (title[:mid], title[mid:])

# ═══════════════════════════════════════════════════════════════
# 카드 생성
# ═══════════════════════════════════════════════════════════════
def create_gradient_bg():
    """프리미엄 다크 배경 — 빛 번짐 + 별 + 미세 텍스처"""
    import random as _rnd
    img = Image.new('RGB', (W, H))
    pixels = img.load()

    # 1) 기본 그라디언트
    for y in range(H):
        ratio = y / H
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * ratio)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * ratio)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * ratio)
        for x in range(W):
            pixels[x, y] = (r, g, b)

    # 2) 우측 상단 은은한 빛 번짐 (고급스러운 비네트)
    cx, cy = int(W * 0.75), int(H * 0.15)
    max_dist = 500
    for y in range(max(0, cy - max_dist), min(H, cy + max_dist)):
        for x in range(max(0, cx - max_dist), min(W, cx + max_dist)):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < max_dist:
                intensity = (1 - dist / max_dist) ** 2.5
                pr, pg, pb = pixels[x, y]
                pixels[x, y] = (
                    min(255, pr + int(18 * intensity)),
                    min(255, pg + int(16 * intensity)),
                    min(255, pb + int(28 * intensity))
                )

    # 3) 좌측 하단 따뜻한 빛 번짐
    cx2, cy2 = int(W * 0.1), int(H * 0.85)
    max_dist2 = 350
    for y in range(max(0, cy2 - max_dist2), min(H, cy2 + max_dist2)):
        for x in range(max(0, cx2 - max_dist2), min(W, cx2 + max_dist2)):
            dist = math.sqrt((x - cx2) ** 2 + (y - cy2) ** 2)
            if dist < max_dist2:
                intensity = (1 - dist / max_dist2) ** 3
                pr, pg, pb = pixels[x, y]
                pixels[x, y] = (
                    min(255, pr + int(12 * intensity)),
                    min(255, pg + int(8 * intensity)),
                    min(255, pb + int(5 * intensity))
                )

    # 4) 별/입자 (은은하게)
    _rnd.seed(42)
    for _ in range(180):
        sx = _rnd.randint(0, W - 1)
        sy = _rnd.randint(0, H - 1)
        brightness = _rnd.randint(30, 65)
        size = _rnd.choice([1, 1, 1, 1, 2])
        for dx in range(size):
            for dy in range(size):
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < W and 0 <= ny < H:
                    pr, pg, pb = pixels[nx, ny]
                    pixels[nx, ny] = (min(255, pr + brightness), min(255, pg + brightness), min(255, pb + brightness + 5))

    # 5) 미세 노이즈 텍스처
    _rnd.seed(123)
    for _ in range(W * H // 12):
        x = _rnd.randint(0, W - 1)
        y = _rnd.randint(0, H - 1)
        v = _rnd.randint(-3, 3)
        pr, pg, pb = pixels[x, y]
        pixels[x, y] = (max(0, min(255, pr + v)), max(0, min(255, pg + v)), max(0, min(255, pb + v)))

    return img

def get_chapter(ref):
    """성경 참조에서 장 번호 추출"""
    m = re.search(r'(\d+):', ref)
    return m.group(1) if m else re.search(r'(\d+)', ref).group(1) if re.search(r'(\d+)', ref) else ''

def get_key_message(content, schedule_title):
    """본문에서 KEY MESSAGE 추출 (📖 다음의 인용구 또는 스케줄 제목)"""
    if content:
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('📖') and i + 1 < len(lines):
                nxt = lines[i + 1].strip().strip('"\u201c\u201d"')
                if nxt:
                    return nxt
        # 두 번째 줄 시도
        if len(lines) > 1:
            second = lines[1].strip().strip('"\u201c\u201d"')
            if second and not second.startswith('#'):
                return second
    return schedule_title

def build_caption(date_str, entry, series_num, content):
    """인스타 캡션 — 오늘의말씀 전체 묵상 내용 포함"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]
    ref = entry['ref']
    title = entry['title']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)

    ref_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하'}
    ref_full = ref
    for short, full in ref_map.items():
        if ref.startswith(short + ' '):
            ref_full = ref.replace(short, full, 1)
            break

    # 오늘의말씀 텍스트에서 전체 묵상 내용 추출
    devotional_body = ''
    if content:
        lines = content.strip().split('\n')
        body_lines = []
        for line in lines:
            line = line.strip()
            # 헤더(📖), 해시태그(#으로만 구성), 계정(@garden), 교회명 제외
            if not line:
                body_lines.append('')
            elif line.startswith('📖'):
                continue
            elif line.startswith('@garden') or line.startswith('동산감리교회') or line.startswith('동산교회'):
                continue
            elif line.startswith('#') and all(c in '#_가-힣a-zA-Z0-9 ' for c in line):
                # 해시태그 줄은 제외 (마지막에 별도로 추가)
                continue
            else:
                body_lines.append(line)
        # 앞뒤 빈줄 제거
        while body_lines and not body_lines[0]:
            body_lines.pop(0)
        while body_lines and not body_lines[-1]:
            body_lines.pop()
        devotional_body = '\n'.join(body_lines)

    caption = f'오늘의 말씀 | {dt.strftime("%m/%d")} ({day_kr})\n'
    caption += f'📖 {ref_full}\n\n'

    if devotional_body:
        caption += f'{devotional_body}\n\n'
    else:
        key_msg = get_key_message(content, title)
        caption += f'"{key_msg}"\n\n'

    caption += f'{book_name}를 하루 한 장씩 읽으며,\n'
    caption += f'다윗의 이야기 속에서 하나님의 마음을 만납니다.\n\n'
    caption += f'✦ {book_name} 시리즈 #{series_num}\n\n'
    caption += f'동산감리교회\n'
    caption += f'@garden___church\n\n'
    caption += f'#오늘의말씀 #{book_name} #{book_name}{chapter}장 #성경말씀 #묵상\n'
    caption += f'#기도 #교회 #말씀카드 #동산감리교회 #매일묵상\n'
    caption += f'#성경 #은혜 #다윗 #기독교 #하나님 #예배\n'
    caption += f'#BibleVerse #DailyDevotional'

    # 인스타 캡션 2200자 제한 체크
    if len(caption) > 2200:
        # 해시태그 부분 보존하며 묵상 본문 줄임
        hashtag_start = caption.rfind('#오늘의말씀')
        if hashtag_start > 0:
            tail = caption[hashtag_start:]
            head = caption[:hashtag_start].rstrip()
            max_head = 2200 - len(tail) - 10
            if len(head) > max_head:
                head = head[:max_head].rsplit('\n', 1)[0] + '\n\n'
            caption = head + '\n\n' + tail

    return caption

def generate_card(date_str, entry, next_entry, series_num, content):
    """인스타 @garden___church 피드와 완전 동일한 스타일 카드"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]
    date_full = f"{dt.strftime('%Y')} . {dt.strftime('%m/%d')}  {day_kr}요일  매일 묵상"

    ref = entry['ref']
    schedule_title = entry['title']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)

    display_title = schedule_title
    line1, line2 = split_title(display_title)

    ref_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하'}
    ref_full = ref
    for short, full in ref_map.items():
        if ref.startswith(short + ' '):
            ref_full = ref.replace(short, full, 1)
            break

    key_msg = get_key_message(content, schedule_title)

    # --- 이미지 생성 ---
    img = create_gradient_bg()
    d = ImageDraw.Draw(img)

    PAD_L = 60
    PAD_R = 60

    # ── 최상단 골드 바 (두껍게) ──
    d.rectangle([0, 0, W, 6], fill=GOLD_BAR)

    # ── 상단: 시리즈 라벨 (더 굵고 크게) ──
    y = 40
    series_label = f"{book_name} \u00b7 SERMON SERIES {series_num:02d}"
    d.text((PAD_L, y), series_label, font=font(16, True), fill=LIGHT_GRAY)

    # ── 장 번호 (더 크게) ──
    y += 32
    chapter_label = f"{book_name} {chapter}장"
    d.text((PAD_L, y), chapter_label, font=font(19, False), fill=MUTED_GRAY)

    # ── 오른쪽 상단: 십자가 장식 (더 선명) ──
    cx, cy = W - 140, 115
    cross_size = 70
    cross_color = (85, 82, 105)
    d.line([(cx, cy - cross_size), (cx, cy + cross_size)], fill=cross_color, width=2)
    d.line([(cx - int(cross_size * 0.6), cy - cross_size * 0.15),
            (cx + int(cross_size * 0.6), cy - cross_size * 0.15)], fill=cross_color, width=2)

    # ── 메인 타이틀 (더 크고 굵게 — 82pt) ──
    f_big = font(82, True)
    title_lines = []
    if line1 and line2:
        if len(line1) > 7:
            parts = line1.split(' ', 1)
            if len(parts) == 2 and len(parts[0]) >= 2:
                title_lines = [parts[0], parts[1], line2]
            else:
                title_lines = [line1, line2]
        else:
            title_lines = [line1, line2]
    elif line2:
        if len(line2) > 7:
            mid = len(line2) // 2
            sp = line2.rfind(' ', 0, mid + 4)
            if sp > 0:
                title_lines = [line2[:sp], line2[sp+1:]]
            else:
                title_lines = [line2]
        else:
            title_lines = [line2]

    y_title = 155
    last_line_idx = len(title_lines) - 1
    for i, tl in enumerate(title_lines):
        color = GOLD if i == last_line_idx else WHITE
        d.text((PAD_L, y_title), tl, font=f_big, fill=color)
        _, th = text_size(d, tl, f_big)
        y_title += th + 18  # 줄 간격 넓힘

    # ── 좌측: BIBLE TEXT + 구절 + 날짜 (더 크게) ──
    y_bt = y_title + 70
    d.text((PAD_L, y_bt), "BIBLE TEXT", font=font(16, True), fill=MUTED_GRAY)
    y_bt += 32
    d.text((PAD_L, y_bt), ref_full, font=font(32, True), fill=WHITE)
    y_bt += 46
    d.text((PAD_L, y_bt), date_full, font=font(16, False), fill=MUTED_GRAY)

    # ── 오른쪽: KEY MESSAGE 박스 (더 크게) ──
    box_x = 400
    box_y = y_bt - 82
    box_w = W - PAD_R - box_x
    box_h = 150

    d.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=5, fill=(25, 23, 38), outline=DIM_GRAY, width=1
    )

    bp = 20
    quote_text = key_msg if len(key_msg) <= 20 else key_msg[:20]
    d.text((box_x + bp, box_y + 22), f'"{quote_text}"', font=font(18, False), fill=LIGHT_GRAY)

    summary2 = ''
    if content:
        for ln in content.split('\n'):
            ln = ln.strip()
            if ln and not ln.startswith('📖') and not ln.startswith('#') and not ln.startswith('✦') and not ln.startswith('🙏') and not ln.startswith('동산') and not ln.startswith('@') and not ln.startswith('"') and not ln.startswith('\u201c') and len(ln) > 10:
                summary2 = ln[:34]
                break
    if summary2:
        d.text((box_x + bp, box_y + 58), summary2, font=font(17, False), fill=LIGHT_GRAY)

    d.text((box_x + bp, box_y + box_h - 35), "— KEY MESSAGE", font=font(14, True), fill=MUTED_GRAY)

    # ── 중앙: 묵상 핵심 + 질문 ──
    if content:
        y_mid = box_y + box_h + 50
        d.line([(PAD_L, y_mid), (PAD_L + 60, y_mid)], fill=GOLD_BAR, width=2)
        y_mid += 20

        # 묵상 본문에서 첫 문단 추출
        med_text = ''
        in_med = False
        skip_title = True
        for ln in content.split('\n'):
            ln = ln.strip()
            if '오늘의 묵상' in ln:
                in_med = True; continue
            if in_med:
                if skip_title and (ln.startswith('"') or ln.startswith('\u201c') or not ln):
                    skip_title = False; continue
                if ln and not any(ln.startswith(c) for c in ['✦', '🙏']):
                    med_text = ln; break

        if med_text:
            f_med = font(19, False)
            max_chars = 25
            remaining = med_text[:150]
            line_count = 0
            while remaining and line_count < 5:
                if len(remaining) <= max_chars:
                    d.text((PAD_L, y_mid), remaining, font=f_med, fill=(180, 178, 190))
                    y_mid += 32; break
                cut = remaining[:max_chars].rfind(' ')
                if cut < 8: cut = max_chars
                d.text((PAD_L, y_mid), remaining[:cut], font=f_med, fill=(180, 178, 190))
                y_mid += 32
                remaining = remaining[cut:].lstrip()
                line_count += 1

        y_mid += 25

        # 오늘의 질문
        question = ''
        found_q = False
        for ln in content.split('\n'):
            ln = ln.strip()
            if '오늘의 질문' in ln: found_q = True; continue
            if found_q and ln and not ln.startswith('✦'):
                question = ln.strip().strip('"\u201c\u201d"'); break

        if question:
            d.line([(PAD_L, y_mid), (PAD_L + 40, y_mid)], fill=DIM_GRAY, width=1)
            y_mid += 18
            d.text((PAD_L, y_mid), "TODAY'S QUESTION", font=font(13, True), fill=MUTED_GRAY)
            y_mid += 28
            f_q = font(17, False)
            qr = question[:80]
            q_count = 0
            while qr and q_count < 3:
                if len(qr) <= 26:
                    d.text((PAD_L, y_mid), qr, font=f_q, fill=(140, 138, 155))
                    break
                cut = qr[:26].rfind(' ')
                if cut < 8: cut = 26
                d.text((PAD_L, y_mid), qr[:cut], font=f_q, fill=(140, 138, 155))
                y_mid += 28; qr = qr[cut:].lstrip(); q_count += 1

    # ── 최하단: 교회 이름 + 하단 골드 바 ──
    d.rectangle([0, H - 4, W, H], fill=GOLD_BAR)  # 하단 골드 바
    y_church = H - 95
    d.text((PAD_L, y_church), "동산감리교회", font=font(18, True), fill=LIGHT_GRAY)
    d.text((PAD_L, y_church + 28), "@garden___church", font=font(14, False), fill=MUTED_GRAY)

    # 우측 하단: 시리즈 정보
    series_info = f"#{series_num:02d} of {book_name}"
    sw, _ = text_size(d, series_info, font(13, False))
    d.text((W - PAD_R - sw, y_church + 28), series_info, font=font(13, False), fill=MUTED_GRAY)

    return img

# ═══════════════════════════════════════════════════════════════
# 업로드 & 포스팅
# ═══════════════════════════════════════════════════════════════
def upload_imgur(image_path):
    """Imgur 업로드 (3회 재시도)"""
    for attempt in range(3):
        try:
            with open(image_path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post(
                'https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                data={'image': enc, 'type': 'base64'},
                timeout=30
            )
            url = r.json().get('data', {}).get('link')
            if url:
                print(f"  Imgur OK: {url}")
                return url
            print(f"  Imgur attempt {attempt+1} failed: {r.json()}")
        except Exception as e:
            print(f"  Imgur attempt {attempt+1} error: {e}")
        time.sleep(5)
    return None

def fallback_github_url(image_path, date_str):
    """Imgur 실패 시 GitHub Pages / Render 폴백"""
    filename = os.path.basename(image_path)

    # dashboard/public 에 복사
    os.makedirs(DASHBOARD_PUBLIC, exist_ok=True)
    dst = os.path.join(DASHBOARD_PUBLIC, filename)
    with open(image_path, 'rb') as src_f:
        with open(dst, 'wb') as dst_f:
            dst_f.write(src_f.read())

    # Git push
    try:
        subprocess.run(['git', 'add', filename], cwd=DASHBOARD_PUBLIC, timeout=30)
        subprocess.run(
            ['git', 'commit', '-m', f'card {date_str}'],
            cwd=REPO_DIR, timeout=30
        )
        subprocess.run(
            ['git', 'push', 'origin', 'master'],
            cwd=REPO_DIR, timeout=60
        )
        print(f"  Git pushed. Waiting 10s for deploy...")
        time.sleep(10)
        url = f'https://lighthouse-media.onrender.com/{filename}'
        print(f"  Fallback URL: {url}")
        return url
    except Exception as e:
        print(f"  Git fallback failed: {e}")
        return None

def get_image_url(image_path, date_str):
    """이미지 URL 확보 (Imgur → GitHub fallback)"""
    url = upload_imgur(image_path)
    if url:
        return url
    print("  Imgur failed, trying GitHub fallback...")
    return fallback_github_url(image_path, date_str)

def post_instagram(image_url, caption):
    """Instagram 단일 이미지 포스팅"""
    if not IG_ID or not TOKEN:
        print("  IG: Missing credentials")
        return None
    try:
        # 컨테이너 생성
        r = requests.post(
            f'https://graph.facebook.com/v21.0/{IG_ID}/media',
            data={
                'image_url': image_url,
                'caption': caption,
                'access_token': TOKEN
            },
            timeout=30
        )
        data = r.json()
        if 'id' not in data:
            print(f"  IG container fail: {data}")
            return None
        container_id = data['id']

        # 퍼블리시 대기
        time.sleep(8)

        r2 = requests.post(
            f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
            data={
                'creation_id': container_id,
                'access_token': TOKEN
            },
            timeout=30
        )
        result = r2.json()
        if 'id' in result:
            print(f"  IG OK: {result['id']}")
            return result['id']
        print(f"  IG publish fail: {result}")
        return None
    except Exception as e:
        print(f"  IG error: {e}")
        return None

def post_facebook(image_url, caption):
    """Facebook 페이지 포스팅"""
    if not PAGE_ID or not TOKEN:
        print("  FB: Missing credentials")
        return None
    try:
        r = requests.post(
            f'https://graph.facebook.com/v21.0/{PAGE_ID}/photos',
            data={
                'url': image_url,
                'message': caption[:500],
                'access_token': TOKEN
            },
            timeout=30
        )
        data = r.json()
        if 'id' in data:
            print(f"  FB OK: {data['id']}")
            return data['id']
        print(f"  FB fail: {data}")
        return None
    except Exception as e:
        print(f"  FB error: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def process_date(date_str, schedule):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]

    print(f"\n{'─' * 50}")
    print(f"  {date_str} ({day_kr})")
    print(f"{'─' * 50}")

    # 스케줄 확인
    entry = get_entry(schedule, date_str)
    if not entry:
        print(f"  SKIP: 스케줄에 {date_str} 없음")
        return

    # 다음 날 엔트리
    next_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
    next_entry = get_entry(schedule, next_date)

    series_num = get_series_number(schedule, date_str)
    print(f"  {entry['ref']} — {entry['title']}")
    print(f"  Series #{series_num:02d}")

    # 말씀 파일 로드
    content = load_devotional(date_str)
    if not content:
        print(f"  WARNING: 말씀 파일 없음 ({date_str}.txt)")
        print(f"  스케줄 제목으로 카드 생성")

    # 카드 생성
    print("  Generating card...")
    card = generate_card(date_str, entry, next_entry, series_num, content)

    # 저장
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = f"today_{date_str}.jpg"
    save_path = os.path.join(OUTPUT_DIR, filename)
    card.save(save_path, "JPEG", quality=95)
    print(f"  Saved: {save_path}")

    # 캡션: 스크린샷과 동일한 구조
    caption = build_caption(date_str, entry, series_num, content)

    # 업로드
    image_url = get_image_url(save_path, date_str)
    if not image_url:
        print("  FAIL: Could not get image URL")
        return

    # Instagram
    post_instagram(image_url, caption)
    time.sleep(3)

    # Facebook
    post_facebook(image_url, caption)

    print(f"  Done: {date_str}")


def main():
    # 날짜 인자 파싱
    if len(sys.argv) > 1:
        dates = sys.argv[1:]
    else:
        dates = [datetime.now().strftime("%Y-%m-%d")]

    schedule = load_schedule()

    print("=" * 50)
    print("  오늘의 말씀 카드 — Instagram + Facebook")
    print(f"  Dates: {', '.join(dates)}")
    print("=" * 50)

    for date_str in dates:
        # 날짜 형식 검증
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"\n  SKIP: Invalid date format '{date_str}' (use YYYY-MM-DD)")
            continue
        process_date(date_str, schedule)

    print(f"\n{'=' * 50}")
    print("  Complete!")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
