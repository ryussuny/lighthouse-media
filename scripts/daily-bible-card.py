"""매일 오전 6시: 오늘의말씀 본문 → 프리미엄 디자인 카드 8장 → garden___church 인스타+페이스북"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, subprocess, shutil, re, math, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
CHURCH_TOKEN = tokens.get('church_page', tokens['instagram'])
CHURCH_IG_ID = tokens.get('church_ig_id', '')
CHURCH_PAGE_ID = tokens.get('church_page_id', '')
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

# ═══════════════════════════════════════════════════════════════
# 폰트 시스템
# ═══════════════════════════════════════════════════════════════
def gf(size, bold=False):
    """감성 세리프 폰트"""
    fonts_bold = ["C:/Windows/Fonts/NanumMyeongjoBold.ttf", "C:/Windows/Fonts/batang.ttc", "C:/Windows/Fonts/malgunbd.ttf"]
    fonts_reg = ["C:/Windows/Fonts/NanumMyeongjo.ttf", "C:/Windows/Fonts/batang.ttc", "C:/Windows/Fonts/malgun.ttf"]
    for p in (fonts_bold if bold else fonts_reg):
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def gf_sans(size, bold=False):
    """산세리프 폰트"""
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    """텍스트 중앙 정렬"""
    for ln in text.split("\n"):
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def tl(d, x, y, text, font, fill, sp=0):
    """텍스트 왼쪽 정렬"""
    for ln in text.split("\n"):
        bb = d.textbbox((0,0), ln, font=font)
        d.text((x, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def wrap_text(text, max_chars=22):
    lines = []
    for line in text.split("\n"):
        while len(line) > max_chars:
            # 단어 단위로 끊기 시도
            cut = line[:max_chars].rfind(' ')
            if cut < max_chars // 2: cut = max_chars
            lines.append(line[:cut].rstrip())
            line = line[cut:].lstrip()
        lines.append(line)
    return "\n".join(lines)

def text_width(d, text, font):
    bb = d.textbbox((0,0), text, font=font)
    return bb[2] - bb[0]

# ═══════════════════════════════════════════════════════════════
# 오늘의 말씀 파일 읽기
# ═══════════════════════════════════════════════════════════════
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
    sections = {
        "header": "", "ref": "", "title": "", "verse": "",
        "meditation_title": "", "meditation": "",
        "questions": [], "practice": "", "prayer": ""
    }
    ref_match = re.search(r'(창세기|출애굽기|레위기|민수기|신명기|여호수아|사사기|룻기|사무엘상|사무엘하|열왕기상|열왕기하|역대상|역대하|에스라|느헤미야|에스더|욥기|시편|잠언|전도서|아가|이사야|예레미야|예레미야애가|에스겔|다니엘|호세아|요엘|아모스|오바댜|요나|미가|나훔|하박국|스바냐|학개|스가랴|말라기|마태복음|마가복음|누가복음|요한복음|사도행전|로마서|고린도전서|고린도후서|갈라디아서|에베소서|빌립보서|골로새서|데살로니가전서|데살로니가후서|디모데전서|디모데후서|디도서|빌레몬서|히브리서|야고보서|베드로전서|베드로후서|요한일서|요한이서|요한삼서|유다서|요한계시록|삼상|삼하|왕상|왕하|대상|대하|삼)\s*\d+[:\s]*\d+[\-–~]*\d*', content)
    if ref_match:
        sections["ref"] = ref_match.group().strip()
    title_match = re.search(r'\*\*(.+?)\*\*', content)
    if title_match:
        sections["title"] = title_match.group(1).strip().strip('"').strip('"').strip('"')
    verse_lines = []
    for line in content.split("\n"):
        line = line.strip()
        if re.match(r'^[⁰¹²³⁴⁵⁶⁷⁸⁹]+', line) or re.match(r'^\d+[.\s]', line):
            verse_lines.append(line)
    sections["verse"] = "\n".join(verse_lines) if verse_lines else ""
    med_match = re.search(r'\*오늘의 묵상\s*\n"?(.+?)"?\n\n(.+?)(?=\*묵상을 위한 질문|\*오늘의 실천|\*오늘의 기도|$)', content, re.DOTALL)
    if med_match:
        sections["meditation_title"] = med_match.group(1).strip().strip('"').strip('*').strip('"').strip('"')
        sections["meditation"] = med_match.group(2).strip()
    q_match = re.search(r'\*묵상을 위한 질문\s*\n(.+?)(?=\*오늘의 실천|\*오늘의 기도|$)', content, re.DOTALL)
    if q_match:
        for line in q_match.group(1).strip().split("\n"):
            line = line.strip().lstrip('-').strip()
            if line and not line.startswith('※'):
                sections["questions"].append(line)
    pr_match = re.search(r'\*오늘의 실천\s*\n(.+?)(?=\*오늘의 기도|$)', content, re.DOTALL)
    if pr_match:
        sections["practice"] = pr_match.group(1).strip()
    pray_match = re.search(r'\*오늘의 기도\s*\n(.+?)$', content, re.DOTALL)
    if pray_match:
        sections["prayer"] = pray_match.group(1).strip()
    return sections

# ═══════════════════════════════════════════════════════════════
# 2026 트렌디 디자인 시스템
# ═══════════════════════════════════════════════════════════════

# 컬러 팔레트 (뮤트 어스 톤)
class Colors:
    # 메인 배경
    WARM_IVORY = (250, 245, 235)
    SOFT_LINEN = (245, 240, 230)
    SAGE_MIST = (225, 232, 220)
    DUSTY_ROSE_BG = (242, 232, 228)
    DEEP_NIGHT = (28, 25, 35)

    # 텍스트
    CHARCOAL = (40, 38, 35)
    WARM_GRAY = (90, 85, 75)
    SOFT_GRAY = (140, 135, 125)
    MUTED_SAGE = (120, 135, 110)

    # 악센트
    ANTIQUE_GOLD = (185, 155, 95)
    WARM_TERRACOTTA = (195, 140, 100)
    DUSTY_ROSE = (195, 155, 145)
    SAGE_GREEN = (140, 165, 130)
    SLATE_BLUE = (130, 145, 165)

    # 장식
    GOLD_LIGHT = (210, 185, 130)
    GOLD_FAINT = (225, 210, 170)


def create_gradient(w, h, color_top, color_bottom, direction='vertical'):
    """소프트 그라디언트 생성"""
    img = Image.new('RGB', (w, h))
    for y in range(h):
        if direction == 'vertical':
            ratio = y / h
        else:
            ratio = 0.5
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


def create_radial_gradient(w, h, center_color, edge_color, cx=0.5, cy=0.4):
    """원형 그라디언트 (빛이 퍼지는 느낌)"""
    img = Image.new('RGB', (w, h))
    pixels = img.load()
    max_dist = math.sqrt((w * 0.7) ** 2 + (h * 0.7) ** 2)
    center_x, center_y = int(w * cx), int(h * cy)
    for y in range(h):
        for x in range(w):
            dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
            ratio = min(dist / max_dist, 1.0)
            # 부드러운 이징
            ratio = ratio * ratio * (3 - 2 * ratio)
            r = int(center_color[0] + (edge_color[0] - center_color[0]) * ratio)
            g = int(center_color[1] + (edge_color[1] - center_color[1]) * ratio)
            b = int(center_color[2] + (edge_color[2] - center_color[2]) * ratio)
            pixels[x, y] = (r, g, b)
    return img


def add_noise_texture(img, intensity=4):
    """미묘한 페이퍼 텍스처"""
    pixels = img.load()
    w, h = img.size
    random.seed(42)
    for _ in range(w * h // 8):
        x, y = random.randint(0, w-1), random.randint(0, h-1)
        v = random.randint(-intensity, intensity)
        r, g, b = pixels[x, y]
        pixels[x, y] = (max(0,min(255,r+v)), max(0,min(255,g+v)), max(0,min(255,b+v)))
    return img


def draw_arch(d, x, y, width, height, color, line_width=2):
    """아치 프레임 (트렌디 장식)"""
    radius = width // 2
    # 반원 상단
    d.arc([x, y, x + width, y + width], 180, 0, fill=color, width=line_width)
    # 좌우 세로 라인
    d.line([(x, y + radius), (x, y + height)], fill=color, width=line_width)
    d.line([(x + width, y + radius), (x + width, y + height)], fill=color, width=line_width)
    # 하단 라인
    d.line([(x, y + height), (x + width, y + height)], fill=color, width=line_width)


def draw_leaf(d, cx, cy, size, angle, color):
    """미니멀 보태니컬 리프"""
    rad = math.radians(angle)
    # 잎 꼭짓점
    tip_x = cx + math.cos(rad) * size
    tip_y = cy - math.sin(rad) * size
    # 잎 곡선 (단순화 - 타원으로)
    left_x = cx + math.cos(rad + 0.4) * size * 0.5
    left_y = cy - math.sin(rad + 0.4) * size * 0.5
    right_x = cx + math.cos(rad - 0.4) * size * 0.5
    right_y = cy - math.sin(rad - 0.4) * size * 0.5
    d.polygon([(cx, cy), (left_x, left_y), (tip_x, tip_y), (right_x, right_y)], fill=color)
    # 줄기
    d.line([(cx, cy), (tip_x, tip_y)], fill=color, width=1)


def draw_botanical_accent(d, x, y, direction='right', color=None):
    """보태니컬 가지 장식"""
    if color is None:
        color = (*Colors.SAGE_GREEN, 60)
    stem_len = 80
    if direction == 'right':
        d.line([(x, y), (x + stem_len, y - 10)], fill=color, width=1)
        for i, pos in enumerate([0.3, 0.5, 0.7]):
            lx = x + stem_len * pos
            ly = y - 10 * pos
            draw_leaf(d, lx, ly, 12 + i*3, 60 + i*15, color)
    else:
        d.line([(x, y), (x - stem_len, y - 10)], fill=color, width=1)
        for i, pos in enumerate([0.3, 0.5, 0.7]):
            lx = x - stem_len * pos
            ly = y - 10 * pos
            draw_leaf(d, lx, ly, 12 + i*3, 120 - i*15, color)


def draw_minimal_cross(d, cx, cy, size=30, color=None):
    """미니멀 십자가"""
    if color is None:
        color = Colors.ANTIQUE_GOLD
    v_half = size
    h_half = int(size * 0.65)
    d.line([(cx, cy - v_half), (cx, cy + v_half)], fill=color, width=2)
    d.line([(cx - h_half, cy - v_half * 0.2), (cx + h_half, cy - v_half * 0.2)], fill=color, width=2)


def draw_dots_indicator(d, y, current, total, active_color, inactive_color):
    """도트 페이지 인디케이터"""
    dot_size = 6
    gap = 16
    total_w = total * dot_size + (total - 1) * gap
    start_x = (W - total_w) // 2
    for i in range(total):
        x = start_x + i * (dot_size + gap)
        if i + 1 == current:
            d.ellipse([x, y, x + dot_size + 2, y + dot_size + 2], fill=active_color)
        else:
            d.ellipse([x + 1, y + 1, x + dot_size + 1, y + dot_size + 1], fill=inactive_color)


def draw_elegant_divider(d, y, style='gold_line'):
    """세련된 구분선"""
    cx = W // 2
    if style == 'gold_line':
        d.line([(cx - 50, y), (cx + 50, y)], fill=Colors.GOLD_LIGHT, width=1)
        d.ellipse([cx - 3, y - 3, cx + 3, y + 3], fill=Colors.ANTIQUE_GOLD)
    elif style == 'dots':
        for i in range(-2, 3):
            d.ellipse([cx + i*12 - 2, y - 2, cx + i*12 + 2, y + 2], fill=Colors.GOLD_LIGHT)
    elif style == 'diamond':
        d.line([(cx - 40, y), (cx - 8, y)], fill=Colors.GOLD_FAINT, width=1)
        d.polygon([(cx, y-5), (cx+5, y), (cx, y+5), (cx-5, y)], fill=Colors.ANTIQUE_GOLD)
        d.line([(cx + 8, y), (cx + 40, y)], fill=Colors.GOLD_FAINT, width=1)


def create_base_card(card_type, page, total):
    """카드 타입별 베이스 이미지 생성"""
    if card_type == 'prayer':
        # 다크 모드 - 깊은 밤하늘 그라디언트
        img = create_gradient(W, H, (35, 30, 50), (18, 15, 28))
    elif card_type == 'cover':
        # 따뜻한 아이보리 + 빛 느낌
        img = create_radial_gradient(W, H, (255, 250, 240), (240, 232, 218), cx=0.5, cy=0.35)
    elif card_type == 'closing':
        # 세이지 그린 그라디언트
        img = create_radial_gradient(W, H, (238, 242, 232), (220, 228, 212), cx=0.5, cy=0.5)
    elif card_type == 'question':
        # 더스티 로즈 그라디언트
        img = create_radial_gradient(W, H, (248, 240, 236), (238, 225, 218), cx=0.5, cy=0.4)
    elif card_type == 'practice':
        # 워밍 린넨
        img = create_gradient(W, H, (248, 244, 235), (240, 235, 222))
    else:
        # 기본 따뜻한 아이보리
        img = create_gradient(W, H, (252, 248, 240), (245, 240, 230))

    # 페이퍼 텍스처
    img = add_noise_texture(img, intensity=3)

    d = ImageDraw.Draw(img)

    # 상단 얇은 골드 악센트 바
    d.rectangle([0, 0, W, 3], fill=Colors.ANTIQUE_GOLD)

    if card_type != 'prayer':
        # 상단 헤더 영역
        d.text((50, 35), "동산감리교회", font=gf_sans(13), fill=Colors.SOFT_GRAY)
        date_txt = f"{DATE_KR} ({DAY_KR})"
        bb = d.textbbox((0,0), date_txt, font=gf_sans(13))
        d.text((W - (bb[2]-bb[0]) - 50, 35), date_txt, font=gf_sans(13), fill=Colors.SOFT_GRAY)

        # 미니멀 십자가
        draw_minimal_cross(d, W//2, 52, size=18, color=Colors.GOLD_LIGHT)
    else:
        # 다크 모드 헤더
        d.rectangle([0, 0, W, 3], fill=Colors.ANTIQUE_GOLD)
        d.text((50, 35), "동산감리교회", font=gf_sans(13), fill=(100, 95, 85))
        date_txt = f"{DATE_KR} ({DAY_KR})"
        bb = d.textbbox((0,0), date_txt, font=gf_sans(13))
        d.text((W - (bb[2]-bb[0]) - 50, 35), date_txt, font=gf_sans(13), fill=(100, 95, 85))
        draw_minimal_cross(d, W//2, 52, size=18, color=(120, 110, 85))

    # 하단 도트 인디케이터
    if card_type == 'prayer':
        draw_dots_indicator(d, H - 55, page, total, Colors.ANTIQUE_GOLD, (60, 55, 50))
    else:
        draw_dots_indicator(d, H - 55, page, total, Colors.ANTIQUE_GOLD, Colors.GOLD_FAINT)

    return img, d


# ═══════════════════════════════════════════════════════════════
# 카드 타입별 디자인
# ═══════════════════════════════════════════════════════════════

def card_cover(data, page, total):
    """표지 카드 - 아치 프레임 + 미니멀 타이포"""
    img, d = create_base_card('cover', page, total)

    ref = data.get("ref", "")
    title = data.get("title", "")

    # 아치 프레임 (중앙 대형)
    arch_w = 520
    arch_h = 680
    arch_x = (W - arch_w) // 2
    arch_y = 180
    draw_arch(d, arch_x, arch_y, arch_w, arch_h, Colors.GOLD_LIGHT, line_width=2)

    # 아치 안쪽 보태니컬 장식
    draw_botanical_accent(d, arch_x + 30, arch_y + arch_h - 30, 'right', Colors.GOLD_FAINT)
    draw_botanical_accent(d, arch_x + arch_w - 30, arch_y + arch_h - 30, 'left', Colors.GOLD_FAINT)

    # 아치 안 콘텐츠
    y = arch_y + 100
    y = tc(d, y, "오 늘 의  말 씀", gf_sans(15), Colors.SOFT_GRAY, 15)
    y += 25
    draw_elegant_divider(d, y, 'diamond')
    y += 35

    # 성경 구절 레퍼런스
    ref_wrapped = wrap_text(ref, 18)
    y = tc(d, y, ref_wrapped, gf(38, True), Colors.CHARCOAL, 8)
    y += 25

    # 묵상 제목
    title_wrapped = wrap_text(title, 14)
    y = tc(d, y, title_wrapped, gf(26), Colors.WARM_TERRACOTTA, 10)
    y += 30

    draw_elegant_divider(d, y, 'dots')
    y += 30

    # 날짜
    tc(d, y, f"{TODAY.strftime('%Y')}. {DATE_KR} {DAY_KR}요일", gf_sans(15), Colors.SOFT_GRAY)

    # 하단 교회명
    tc(d, H - 100, "@garden___church", gf_sans(12), Colors.GOLD_FAINT)

    return img


def card_verse(data, page, total):
    """말씀 본문 카드 - 엘레건트 인용"""
    img, d = create_base_card('verse', page, total)

    ref = data.get("ref", "")
    text = data.get("text", "")

    # 상단 레퍼런스
    y = 110
    y = tc(d, y, ref, gf_sans(14), Colors.ANTIQUE_GOLD, 12)
    y += 8
    draw_elegant_divider(d, y, 'gold_line')
    y += 30

    # 좌측 세로 골드 라인 (인용 스타일)
    line_x = 85
    d.line([(line_x, y + 10), (line_x, min(y + 850, H - 120))], fill=Colors.GOLD_FAINT, width=2)

    # 큰 여는 따옴표
    d.text((line_x + 15, y - 15), "\u201C", font=gf(60), fill=Colors.GOLD_FAINT)
    y += 45

    # 본문 텍스트
    verse_wrapped = wrap_text(text, 22)
    for ln in verse_wrapped.split("\n")[:18]:
        if not ln.strip():
            y += 12
            continue
        # 절 번호 강조
        num_match = re.match(r'^([⁰¹²³⁴⁵⁶⁷⁸⁹\d]+[.\s]*)', ln)
        if num_match:
            num_text = num_match.group(1)
            rest_text = ln[len(num_text):]
            # 번호는 골드로
            num_w = text_width(d, num_text, gf(20))
            start_x = 110
            d.text((start_x, y), num_text, font=gf(20), fill=Colors.ANTIQUE_GOLD)
            d.text((start_x + num_w + 2, y), rest_text, font=gf(20), fill=Colors.CHARCOAL)
        else:
            d.text((110, y), ln, font=gf(20), fill=Colors.CHARCOAL)
        y += 38

    # 닫는 따옴표
    y += 5
    d.text((W - 130, y), "\u201D", font=gf(60), fill=Colors.GOLD_FAINT)

    return img


def card_meditation(data, page, total):
    """묵상 카드 - 깊이있는 레이아웃"""
    img, d = create_base_card('meditation', page, total)

    title = data.get("title", "")
    body = data.get("body", "")

    y = 120

    if title:
        # 섹션 라벨
        y = tc(d, y, "묵  상", gf_sans(13), Colors.MUTED_SAGE, 12)
        y += 10
        draw_elegant_divider(d, y, 'diamond')
        y += 28

        # 묵상 제목
        title_wrapped = wrap_text(title, 16)
        y = tc(d, y, title_wrapped, gf(30, True), Colors.CHARCOAL, 8)
        y += 25
    else:
        y = 130

    # 본문
    body_wrapped = wrap_text(body, 24)
    margin_x = 90

    for ln in body_wrapped.split("\n")[:22]:
        if not ln.strip():
            y += 14
            continue
        d.text((margin_x, y), ln, font=gf(19), fill=Colors.WARM_GRAY)
        y += 36

    return img


def card_question(data, page, total):
    """질문 카드 - 더스티 로즈 배경"""
    img, d = create_base_card('question', page, total)

    y = 220

    # 섹션 라벨
    y = tc(d, y, "묵상을 위한 질문", gf_sans(14), Colors.DUSTY_ROSE, 15)
    y += 10
    draw_elegant_divider(d, y, 'dots')
    y += 40

    questions = data.get("questions", [])
    for i, q in enumerate(questions[:3]):
        # 질문 번호 원형 배지
        badge_x = 110
        d.ellipse([badge_x - 16, y - 2, badge_x + 16, y + 30],
                  outline=Colors.DUSTY_ROSE, width=2)
        d.text((badge_x - 5, y + 2), str(i + 1), font=gf_sans(16), fill=Colors.DUSTY_ROSE)

        # 질문 텍스트
        q_wrapped = wrap_text(q, 22)
        qy = y + 2
        for ln in q_wrapped.split("\n"):
            d.text((badge_x + 35, qy), ln, font=gf(21), fill=Colors.CHARCOAL)
            qy += 36

        y = qy + 30

    # 하단 장식
    draw_botanical_accent(d, W - 100, H - 140, 'left', Colors.GOLD_FAINT)

    return img


def card_practice(data, page, total):
    """실천 카드 - 따뜻한 린넨 배경"""
    img, d = create_base_card('practice', page, total)

    text = data.get("text", "")

    y = 250

    # 섹션 라벨
    y = tc(d, y, "오늘의 실천", gf_sans(14), Colors.SAGE_GREEN, 15)
    y += 10
    draw_elegant_divider(d, y, 'diamond')
    y += 40

    # 실천 아이콘 (체크 원)
    cx = W // 2
    d.ellipse([cx - 28, y - 2, cx + 28, y + 54], outline=Colors.SAGE_GREEN, width=2)
    d.text((cx - 8, y + 8), "✓", font=gf_sans(24, True), fill=Colors.SAGE_GREEN)
    y += 75

    # 실천 텍스트
    prac_wrapped = wrap_text(text, 22)
    for ln in prac_wrapped.split("\n")[:12]:
        if not ln.strip():
            y += 12
            continue
        y = tc(d, y, ln, gf(21), Colors.CHARCOAL, 12)

    # 양쪽 보태니컬
    draw_botanical_accent(d, 60, H - 160, 'right', Colors.GOLD_FAINT)
    draw_botanical_accent(d, W - 60, H - 160, 'left', Colors.GOLD_FAINT)

    return img


def card_prayer(data, page, total):
    """기도 카드 - 다크 모드 깊은 밤하늘"""
    img, d = create_base_card('prayer', page, total)

    text = data.get("text", "")

    # 별 장식 (미니멀)
    random.seed(777)
    for _ in range(15):
        sx = random.randint(50, W - 50)
        sy = random.randint(80, H - 100)
        sz = random.randint(1, 2)
        alpha = random.randint(40, 90)
        d.ellipse([sx, sy, sx + sz, sy + sz], fill=(200, 195, 170))

    y = 200

    # 기도 라벨
    y = tc(d, y, "오늘의 기도", gf_sans(14), Colors.ANTIQUE_GOLD, 15)
    y += 10
    d.line([(W//2 - 40, y), (W//2 + 40, y)], fill=(120, 110, 85), width=1)
    y += 35

    # 기도 텍스트
    prayer_wrapped = wrap_text(text, 22)
    for ln in prayer_wrapped.split("\n")[:20]:
        if not ln.strip():
            y += 12
            continue
        y = tc(d, y, ln, gf(20), (225, 218, 200), 12)

    # 아멘
    y += 20
    tc(d, y, "아멘.", gf(22, True), Colors.ANTIQUE_GOLD)

    return img


def card_closing(data, page, total):
    """마무리 카드 - 세이지 그린 + 브랜딩"""
    img, d = create_base_card('closing', page, total)

    verse = data.get("verse", "")
    ref = data.get("ref", "")

    # 아치 프레임 (작은 사이즈)
    arch_w = 400
    arch_h = 500
    arch_x = (W - arch_w) // 2
    arch_y = 220
    draw_arch(d, arch_x, arch_y, arch_w, arch_h, Colors.GOLD_LIGHT, line_width=1)

    y = arch_y + 80

    # 구절
    verse_wrapped = wrap_text(verse, 16)
    y = tc(d, y, verse_wrapped, gf(26, True), Colors.CHARCOAL, 10)
    y += 25

    draw_elegant_divider(d, y, 'diamond')
    y += 25

    # 레퍼런스
    y = tc(d, y, ref, gf_sans(16), Colors.ANTIQUE_GOLD, 12)

    # 교회명 + SNS
    y = arch_y + arch_h - 60
    tc(d, y, "동산감리교회", gf_sans(18, True), Colors.CHARCOAL)
    tc(d, y + 30, "@garden___church", gf_sans(13), Colors.SOFT_GRAY)

    # 보태니컬 장식
    draw_botanical_accent(d, arch_x + 10, arch_y + arch_h - 10, 'right', Colors.GOLD_FAINT)
    draw_botanical_accent(d, arch_x + arch_w - 10, arch_y + arch_h - 10, 'left', Colors.GOLD_FAINT)

    # 하단
    tc(d, H - 90, "오늘도 말씀 안에서 은혜로운 하루 되세요", gf(16), Colors.SOFT_GRAY)

    return img


def make_card(card_type, data, page, total):
    """카드 타입별 생성 라우터"""
    if card_type == "cover":
        return card_cover(data, page, total)
    elif card_type == "verse":
        return card_verse(data, page, total)
    elif card_type == "meditation":
        return card_meditation(data, page, total)
    elif card_type == "question":
        return card_question(data, page, total)
    elif card_type == "practice":
        return card_practice(data, page, total)
    elif card_type == "prayer":
        return card_prayer(data, page, total)
    elif card_type == "closing":
        return card_closing(data, page, total)
    else:
        return card_cover(data, page, total)


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 50)
    print(f"  Bible Card Premium - {DATE_KR} ({DAY_KR})")
    print("=" * 50)

    # 1. 오늘의 말씀 읽기
    print("\n[1/4] Loading today's word...")
    content = load_today_word()
    if not content:
        print("  No file found for today. Using AI generation.")
        API_KEY = ""
        env_path = os.path.join(HOME, "lighthouse-media", ".env")
        if os.path.exists(env_path):
            for line in open(env_path, encoding='utf-8'):
                if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

        # 스케줄에서 오늘 정보 가져오기
        schedule_path = os.path.join(HOME, "lighthouse-media", "config", "bible-schedule.json")
        today_ref = ""
        today_title = ""
        if os.path.exists(schedule_path):
            schedule = json.load(open(schedule_path, encoding='utf-8'))
            for entry in schedule:
                if entry['date'] == DATE_STR:
                    today_ref = entry['ref']
                    today_title = entry['title']
                    break

        prompt = f"""당신은 동산감리교회의 목회자이자, 말씀 앞에서 함께 멈추는 동행자입니다.
오늘({DATE_STR} {DAY_KR}요일) 인스타그램 @garden___church 말씀 카드용 묵상을 작성합니다.

본문: {today_ref if today_ref else '사무엘하'}
제목: {today_title if today_title else ''}

═══ 작성 원칙 (반드시 지킬 것) ═══

【1. 장르 감지 → 문체 조절】
본문의 장르를 먼저 판별하고, 그에 맞는 묵상 스타일을 사용하세요:
- 내러티브(사무엘, 열왕기, 사사기 등): "이 장면을 상상해보세요..." → 인물의 표정과 숨결을 그리고 → 그 인물의 감정이 오늘 내 감정과 어떻게 겹치는지 보여주세요.
- 시가(시편, 아가 등): 시의 리듬을 살리고 → 그 감정의 울림을 현대의 언어로 재현하고 → 오늘 우리 삶에서 같은 울림이 어디서 들리는지 연결하세요.
- 지혜(잠언, 전도서 등): 날카로운 진실 하나를 꺼내고 → 왜 그것이 마음을 찌르는지 설명하고 → 오늘 어떻게 살아낼 수 있는지 보여주세요.
- 예언(이사야, 예레미야 등): 하나님의 음성이 들리는 듯한 무게감으로 → 그 말씀이 당시 백성에게 어떤 의미였는지 → 지금 이 시대에 같은 말씀이 우리에게 무엇을 요구하는지 풀어주세요.

【2. 감정 중심 — 분석이 아니라 체험】
본문에서 하나의 핵심 감정을 찾으세요 (외로움, 두려움, 감사, 분노, 희망, 수치심, 그리움, 경외...).
그 감정이 묵상 전체를 관통하게 하세요. 학자가 설명하듯 쓰지 말고, 그 감정을 겪고 있는 사람처럼 쓰세요.
"나도 이 말씀 앞에서 멈춰야 했습니다" — 이 에너지를 유지하세요.

【3. "멈춤의 순간" — 스크롤을 멈추게 하는 한 줄】
묵상 본문 안에 반드시 한 줄, 읽는 사람이 자기 이야기인 줄 알고 멈추는 문장을 넣으세요.
예시: "혹시 지금, 아무도 안 봐도 최선을 다하고 있나요?"
예시: "그 사람 앞에서는 괜찮은 척하면서, 혼자일 때 무너지고 있지 않나요?"
예시: "새벽에 혼자 깨어서, 아무에게도 말 못 한 그 기도..."
이 문장은 보편적이되 너무나 구체적으로 느껴져야 합니다.

【4. 현대적 적용 — 구체적 상황】
추상적인 "오늘 실천할 것" 대신, 사람들이 실제로 겪는 순간을 넣으세요:
"회사에서 무시당했을 때", "아이가 말을 안 들을 때", "새벽에 혼자 깨어 있을 때",
"카톡 답장이 안 올 때", "부모님이 늙어가는 것이 보일 때", "통장 잔고를 확인한 후"
이런 순간에 이 말씀이 어떻게 닿는지 보여주세요.

【5. 나눔 유도 — DM 공유를 부르는 마무리】
캡션 마지막에 이 말이 필요한 누군가를 떠올리게 하는 한 줄을 넣으세요:
예시: "이 말이 필요한 사람이 떠오르시나요? 보내주세요."

【6. 동적 해시태그】
고정 해시태그 대신, 오늘 본문의 키워드 + 핵심 감정 + 삶의 상황에서 자연스럽게 뽑아주세요.
한국어 10개 + 영어 5개, 총 15개. 예: #외로움속의기도 #WhenYouFeelAlone #사무엘하18장

═══ 출력 형식 (정확히 따를 것) ═══

📖 {today_ref}
**"묵상 제목 — 마음을 건드리는 한 줄 인용구 형태"**

*오늘의 묵상
"묵상 소제목 (본문의 핵심 감정이나 장면을 담은 짧은 문구)"

(묵상 본문 2-3문단. 위의 장르별 스타일을 따르되:
- 첫 문단: 성경 속 장면/감정을 생생하게 그려주세요. 독자가 그 자리에 서 있는 것처럼.
- 둘째 문단: 그 장면에서 발견한 진실, 혹은 인물이 마주한 하나님. "멈춤의 순간" 한 줄을 여기에 자연스럽게 넣으세요.
- 셋째 문단: 오늘 우리 삶의 구체적 순간과 연결. 추상적 교훈이 아니라, 누군가의 오늘 하루에 닿는 말.
각 문단 2-3문장. 설교하지 말고 함께 걷는 톤으로.)

*묵상을 위한 질문
- 질문 1 (본문 속 인물/상황에서 출발해 → 내 삶을 비추는 질문)
- 질문 2 (오늘의 핵심 감정과 연결된, 솔직한 자기 성찰 질문)
- 질문 3 (구체적 삶의 상황에서 이 말씀을 어떻게 살 것인가)

*오늘의 실천
(구체적인 하루 실천 2-3문장. "~하세요"가 아니라 "오늘 ___할 때, ___해보는 건 어떨까요?" 같은 제안형으로. 실제 삶의 한 장면을 콕 집어서.)

*오늘의 기도
(공식적인 "하나님 감사합니다" 기도가 아니라, 오늘 묵상의 감정을 그대로 안고 드리는 진짜 기도.
두려웠다면 두려운 채로, 감사했다면 눈물 나는 감사로, 분노했다면 솔직한 분노를 안고.
"주님, 솔직히..." 이런 시작도 괜찮습니다. 형식이 아니라 진심.
2-4줄. 아멘으로 끝.)

동산감리교회
@garden___church

(이 말이 필요한 사람이 떠오르시나요? 보내주세요.)

(본문 키워드 + 핵심 감정 + 삶의 상황 기반 동적 해시태그 15개, 한국어 10 + 영어 5)

[필수 준수]
- 전체 분량: 인스타그램 캡션에 적합한 길이 (너무 길지 않게)
- 묵상 본문은 성경 원문 나열이 아닌, 핵심 메시지 중심으로 풀어쓰기
- 설교조가 아닌 동행자의 톤: "나도 이 말씀 앞에서 같이 서 있습니다"
- 이모지는 📖, ✦, 🙏만 사용 (과도한 이모지 금지)
- 새번역 성경 기준
- *오늘의 묵상, *묵상을 위한 질문, *오늘의 실천, *오늘의 기도 — 이 섹션 마커는 정확히 이대로 유지
- 제목은 반드시 **"제목"** 형식으로 감싸기"""

        r = requests.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
        }, json={"model": "claude-sonnet-4-6", "max_tokens": 3000, "messages": [{"role":"user","content":prompt}]})
        if r.status_code != 200:
            print(f"  [ERROR] Anthropic API {r.status_code}: {r.text[:500]}")
            raise Exception(f"Anthropic API error {r.status_code}")
        content = r.json()["content"][0]["text"]

        # 파일 저장
        save_dir = os.path.join(HOME, "Documents", "오늘의말씀")
        os.makedirs(save_dir, exist_ok=True)
        with open(os.path.join(save_dir, f"{DATE_STR}.txt"), 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Saved to Documents/오늘의말씀/{DATE_STR}.txt")

    sections = parse_word(content)
    print(f"  {sections['ref']} - {sections['meditation_title']}")

    # 2. 프리미엄 카드 8장 생성
    print("\n[2/4] Creating 8 premium design cards...")
    verse_text = sections['verse'] if sections['verse'] else content[content.find('⁷'):content.find('*오늘의 묵상')][:500]
    med_text = sections['meditation']

    # 카드 구성 최적화
    cards = []
    cards.append(("cover", {"ref": sections['ref'], "title": sections['meditation_title']}))

    # 말씀 카드 (긴 텍스트는 2장)
    if len(verse_text) > 350:
        mid = verse_text[:350].rfind('\n')
        if mid < 100: mid = 350
        cards.append(("verse", {"ref": sections['ref'], "text": verse_text[:mid]}))
        cards.append(("verse", {"ref": sections['ref'], "text": verse_text[mid:]}))
    else:
        cards.append(("verse", {"ref": sections['ref'], "text": verse_text}))
        # 빈 자리는 묵상으로 채움
        cards.append(("meditation", {"title": sections['meditation_title'], "body": med_text[:400]}))

    # 묵상 카드 (긴 텍스트는 2장)
    if len(verse_text) > 350:
        cards.append(("meditation", {"title": sections['meditation_title'], "body": med_text[:400]}))

    if len(med_text) > 400:
        cards.append(("meditation", {"title": "", "body": med_text[400:800]}))
    else:
        cards.append(("question", {"questions": sections['questions']}))

    # 나머지 카드
    remaining_types = []
    existing_types = [c[0] for c in cards]
    if 'question' not in existing_types:
        remaining_types.append(("question", {"questions": sections['questions']}))
    remaining_types.append(("practice", {"text": sections['practice']}))
    remaining_types.append(("prayer", {"text": sections['prayer']}))
    remaining_types.append(("closing", {"verse": sections['ref'], "ref": "동산감리교회"}))

    cards.extend(remaining_types)
    cards = cards[:8]  # 최대 8장

    # 8장이 안 되면 closing 추가
    while len(cards) < 8:
        cards.append(("closing", {"verse": sections['ref'], "ref": "동산감리교회"}))

    OUT = os.path.join(HOME, "lighthouse-media", "output", "bible-cards")
    os.makedirs(OUT, exist_ok=True)
    FRAMES = os.path.join(OUT, "frames")

    for i, (ctype, cdata) in enumerate(cards):
        try:
            img = make_card(ctype, cdata, i+1, 8)
            path = os.path.join(OUT, f"card_{i+1}.jpg")
            img.save(path, "JPEG", quality=96)
            print(f"  {i+1}/8 [{ctype}]: OK")
        except Exception as e:
            print(f"  {i+1}/8 [{ctype}]: ERROR({e})")
        time.sleep(0.2)

    # 3. 음악 포함 영상 생성
    print("\n[3/4] Creating video with BGM...")
    vpath = os.path.join(OUT, f"bible_{DATE_STR}.mp4")
    try:
        os.makedirs(FRAMES, exist_ok=True)
        fnum = 0
        for i, (ctype, cdata) in enumerate(cards):
            img = make_card(ctype, cdata, i+1, 8)
            dur = 6 if ctype in ['cover','closing'] else 8
            for f in range(dur * FPS):
                img.save(os.path.join(FRAMES, f"frame_{fnum:05d}.png"))
                fnum += 1

        bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
        bgm = os.path.join(BGM_DIR, random.choice(bgm_files))
        print(f"  BGM: {os.path.basename(bgm)}")
        total_dur = sum(6 if c[0] in ['cover','closing'] else 8 for c in cards)

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
            print("  Video FAIL (ffmpeg)")
    except Exception as e:
        print(f"  Video ERROR: {e}")
        shutil.rmtree(FRAMES, ignore_errors=True)

    # SNS 게시는 post-today-card.py에서 처리 (중복 방지)
    print(f"\n[4/4] Cards saved locally (SNS posting handled by post-today-card.py)")
    print(f"  Cards: {OUT}/card_1~8.jpg")
    if os.path.exists(vpath):
        print(f"  Video: {os.path.basename(vpath)}")

    print(f"\n{'='*50}")
    print(f"  Done! Cards generated (no SNS posting)")
    print(f"{'='*50}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {type(e).__name__}: {e}")
        print("  Script crashed but will not block next steps.")
        import traceback; traceback.print_exc()
