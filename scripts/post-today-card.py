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
import traceback

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
# Claude API 설정
# ═══════════════════════════════════════════════════════════════
def load_api_key():
    """Load Anthropic API key from .env"""
    env_path = os.path.join(REPO_DIR, ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.strip().split("=", 1)[1].strip('"').strip("'")
    return ""

ANTHROPIC_API_KEY = load_api_key()
CLAUDE_MODEL = "claude-sonnet-4-6"

def call_claude(system_prompt, user_prompt, max_tokens=1500):
    """Claude API 호출 (3회 재시도)"""
    if not ANTHROPIC_API_KEY:
        print("  Claude API: No API key found")
        return None

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=60,
            )
            data = r.json()
            if r.status_code == 200 and "content" in data:
                text = data["content"][0]["text"]
                print(f"  Claude API OK (attempt {attempt+1})")
                return text
            print(f"  Claude API attempt {attempt+1} fail: {data.get('error', data)}")
        except Exception as e:
            print(f"  Claude API attempt {attempt+1} error: {e}")
        if attempt < 2:
            time.sleep(3)

    print("  Claude API: All 3 attempts failed, using fallback")
    return None


def generate_ai_caption(date_str, entry, series_num, content):
    """Claude AI로 Instagram 최적화 캡션 생성"""
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

    system_prompt = """당신은 동산감리교회 @garden___church 인스타그램 계정의 캡션 작가입니다.
목회자이자 동행자 — 가르치되 함께 걷는 사람. "나도 이 말씀 앞에서 울었습니다" 에너지.

2026년 인스타그램 알고리즘은 DM 공유("sends")를 좋아요보다 3~5배 높게 평가합니다.
모든 캡션은 "이거 내 친구한테 보내야 해" 충동을 일으켜야 합니다.

캡션은 반드시 아래 구조를 따르세요:

[HOOK — 질문이나 상황 묘사, 첫 줄에서 스크롤을 멈추게]
(빈 줄)
[핵심 메시지 — 묵상의 가장 강력한 한 문단, 2~4문장]
(빈 줄)
[멈춤의 순간 — 읽는 사람이 자기 삶을 돌아보는 한 줄]
(빈 줄)
[오늘의 한 마디 — 기억에 남을 핵심 문장, 따옴표로 감싸기]
(빈 줄)
이 말씀이 필요한 사람이 떠오르시나요? 💌 보내주세요.

절대 지킬 것:
- 설교 톤 금지. 함께 걷는 동행자 톤.
- 구체적 상황 사용 (새벽에 혼자 깨어 있을 때, 카톡 답장이 안 올 때, 회의실에서 무시당했을 때...)
- 감정 중심 — 분석이 아니라 체험
- 캡션 본문(해시태그 제외)은 800자 이내로 간결하게
- 해시태그는 별도로 생성하므로 캡션에 해시태그 넣지 마세요
- 교회명, 계정명도 넣지 마세요 (별도로 추가됩니다)"""

    user_prompt = f"""오늘 날짜: {date_str} ({day_kr}요일)
성경 본문: {ref_full}
묵상 제목: {title}
시리즈: {book_name} 묵상 #{series_num}

아래는 오늘의 전체 묵상 내용입니다. 이 내용을 기반으로 Instagram 최적화 캡션을 작성하세요:

---
{content if content else '(묵상 파일 없음 — 제목과 성경 본문만으로 작성하세요)'}
---

위 구조대로 캡션을 작성하세요. 해시태그/교회명/계정명은 넣지 마세요."""

    result = call_claude(system_prompt, user_prompt, max_tokens=1200)
    return result


def generate_ai_hashtags(date_str, entry, content):
    """Claude AI로 동적 해시태그 생성"""
    ref = entry['ref']
    title = entry['title']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)

    system_prompt = """당신은 인스타그램 해시태그 전략가입니다.
성경 묵상 콘텐츠의 도달률을 극대화하는 해시태그를 생성합니다.

규칙:
- 총 15~20개 해시태그
- 한국어 10~12개 + 영어 5~8개
- 반드시 포함: #오늘의말씀 #동산감리교회 #말씀카드 #묵상
- 성경 본문 키워드 (인물, 장소, 주제)
- 오늘 묵상의 핵심 감정
- 이 본문이 다루는 삶의 상황
- 해시태그만 출력하세요. 설명 없이 한 줄에 모든 해시태그를 나열하세요.
- #을 빠뜨리지 마세요."""

    user_prompt = f"""성경 본문: {ref}
제목: {title}
책: {book_name} {chapter}장

묵상 내용 요약:
{content[:500] if content else title}

해시태그를 생성하세요:"""

    result = call_claude(system_prompt, user_prompt, max_tokens=300)
    if result:
        # 해시태그만 추출 (# 으로 시작하는 단어들)
        tags = re.findall(r'#\S+', result)
        # 필수 태그 확인 및 추가
        required = ['#오늘의말씀', '#동산감리교회', '#말씀카드', '#묵상']
        for req in required:
            if req not in tags:
                tags.insert(0, req)
        # 20개 제한
        tags = tags[:20]
        return ' '.join(tags)
    return None


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

def build_caption_fallback(date_str, entry, series_num, content):
    """폴백 캡션 — AI 실패 시 기존 방식으로 생성"""
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
            if not line:
                body_lines.append('')
            elif line.startswith('📖'):
                continue
            elif line.startswith('@garden') or line.startswith('동산감리교회') or line.startswith('동산교회'):
                continue
            elif line.startswith('#') and all(c in '#_가-힣a-zA-Z0-9 ' for c in line):
                continue
            else:
                body_lines.append(line)
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
        hashtag_start = caption.rfind('#오늘의말씀')
        if hashtag_start > 0:
            tail = caption[hashtag_start:]
            head = caption[:hashtag_start].rstrip()
            max_head = 2200 - len(tail) - 10
            if len(head) > max_head:
                head = head[:max_head].rsplit('\n', 1)[0] + '\n\n'
            caption = head + '\n\n' + tail

    return caption


def build_caption(date_str, entry, series_num, content):
    """Instagram 최적화 캡션 생성 — AI 우선, 실패 시 폴백"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]
    ref = entry['ref']
    book_name = get_series_book(ref)
    chapter = get_chapter(ref)

    ref_map = {'삼하': '사무엘하', '삼상': '사무엘상', '왕상': '열왕기상', '왕하': '열왕기하'}
    ref_full = ref
    for short, full in ref_map.items():
        if ref.startswith(short + ' '):
            ref_full = ref.replace(short, full, 1)
            break

    # ── Step 1: AI 캡션 본문 생성 ──
    ai_body = None
    try:
        print("  Generating AI caption...")
        ai_body = generate_ai_caption(date_str, entry, series_num, content)
    except Exception as e:
        print(f"  AI caption error: {e}")
        traceback.print_exc()

    # ── Step 2: AI 해시태그 생성 ──
    ai_hashtags = None
    try:
        print("  Generating AI hashtags...")
        ai_hashtags = generate_ai_hashtags(date_str, entry, content)
    except Exception as e:
        print(f"  AI hashtag error: {e}")
        traceback.print_exc()

    # ── AI 실패 시 폴백 ──
    if not ai_body:
        print("  Fallback: using raw devotional text caption")
        return build_caption_fallback(date_str, entry, series_num, content)

    # ── Step 3: 캡션 조립 ──
    # 시리즈 헤더
    header = f'📖 {book_name} 묵상 #{series_num} | {ref_full}\n'
    header += f'오늘의 말씀 | {dt.strftime("%m/%d")} ({day_kr})\n\n'

    # AI 본문 (해시태그/교회명이 혼입되었을 경우 제거)
    body = ai_body.strip()
    # AI가 혼입했을 수 있는 해시태그 줄 제거
    body_lines = body.split('\n')
    clean_lines = []
    for line in body_lines:
        stripped = line.strip()
        # 해시태그만으로 구성된 줄 제거
        if stripped and all(word.startswith('#') for word in stripped.split()):
            continue
        clean_lines.append(line)
    body = '\n'.join(clean_lines).strip()

    # 푸터
    footer = '\n\n—\n'
    footer += '동산감리교회 @garden___church\n\n'

    # 해시태그
    if ai_hashtags:
        hashtags = ai_hashtags
    else:
        # 폴백 해시태그
        hashtags = (
            f'#오늘의말씀 #{book_name} #{book_name}{chapter}장 #성경말씀 #묵상 '
            f'#기도 #교회 #말씀카드 #동산감리교회 #매일묵상 '
            f'#성경 #은혜 #다윗 #기독교 #하나님 #예배 '
            f'#BibleVerse #DailyDevotional'
        )

    caption = header + body + footer + hashtags

    # ── 2200자 제한 체크 ──
    if len(caption) > 2200:
        # 해시태그/푸터 보존, 본문 줄임
        fixed_len = len(header) + len(footer) + len(hashtags) + 10
        max_body = 2200 - fixed_len
        if max_body < 200:
            max_body = 200
        if len(body) > max_body:
            body = body[:max_body].rsplit('\n', 1)[0].rstrip() + '...'
        caption = header + body + footer + hashtags

    # 최종 안전장치
    if len(caption) > 2200:
        caption = caption[:2197] + '...'

    print(f"  Caption length: {len(caption)} chars")
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
