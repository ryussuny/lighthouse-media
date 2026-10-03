"""매일 인스타 릴스 1편 자동 생성 + 업로드
- AI(Claude)가 매일 새로운 콘텐츠 생성
- 배경음악 포함 시네마틱 영상 (1080x1920, 30~40초)
- Instagram Reels + Facebook 자동 게시
- API 실패 시 비상용 폴백 풀 사용
- Usage:
    python daily-ig-reels.py              # 자동 주제 선택
    python daily-ig-reels.py comfort      # 특정 카테고리
    python daily-ig-reels.py --dry-run    # 영상만 만들고 업로드하지 않음(점검용)

2026-09-28 릴스 중심 전환:
- 최근 30개 훅을 기억해 같은 주제 반복 방지(config/reels-history.json)
- AI 실패 시 예비 릴스는 같은 것을 30일에 1번까지만(반복 게시 = 노출 억제)
- 첫 장면(훅)은 페이드 없이 첫 프레임부터 보이게, 3초로 단축
- 캡션은 한국어 중심, 해시태그 5개 이내
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, requests, time, base64, subprocess, shutil, random, hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 2026-09-29 worker-2: fal.ai 비주얼(옵션 --visual=ai) — 미설치/미설정이어도 기존 절차형 배경으로 안전 동작
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from lib import fal_visuals as fv
    FAL_VISUALS_AVAILABLE = True
except ImportError as e:
    FAL_VISUALS_AVAILABLE = False
    _FAL_IMPORT_ERR = str(e)

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════
HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
CONFIG_DIR = os.path.join(REPO_DIR, "config")
BGM_DIR = os.path.join(REPO_DIR, "assets", "bgm")
OUT_DIR = os.path.join(REPO_DIR, "output", "reels")
os.makedirs(OUT_DIR, exist_ok=True)

# API Key
API_KEY = ""
for line in open(os.path.join(REPO_DIR, ".env"), encoding='utf-8'):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(CONFIG_DIR, "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

W, H = 1080, 1920
FPS = 24  # 2026-09-29 worker-2: 2→24 (요청 "24~30fps 부드러운 렌더" — 정적배경 캐싱으로 비용 상쇄)
KEN_BURNS_ZOOM_END = 1.15  # AI 배경 장면: 재생 중 1.0→1.15로 천천히 확대(느린 줌)

# ═══════════════════════════════════════════════════════════════
# 폰트
# ═══════════════════════════════════════════════════════════════
def gf(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size):
    for p in ["C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0, 0), ln, font=font)
        d.text(((W - (bb[2] - bb[0])) / 2, y), ln, font=font, fill=fill)
        y += bb[3] - bb[1] + sp
    return y


def wrap_to_width(d, text, font, max_width):
    """공백 기준 그리디 줄바꿈 — 기존 \n은 그대로 유지하고, 폭을 넘는 줄만 공백에서 쪼갠다.
    2026-10-03 worker-2: 실측 프레임 캡처에서 closing 문장(자수 제한 없음)이 화면 밖으로
    잘려나가는 걸 발견(프롬프트가 title/sub는 10~20자로 제한하지만 closing은 제한이 없어
    길어질 수 있음) — 훅 장면에만 있던 단일-분할 로직을 전체 장면에 적용 가능한 범용
    여러줄 랩으로 일반화."""
    out_lines = []
    for line in text.split("\n"):
        if d.textbbox((0, 0), line, font=font)[2] <= max_width or " " not in line:
            out_lines.append(line)
            continue
        words = line.split(" ")
        cur = words[0]
        for w in words[1:]:
            trial = cur + " " + w
            if d.textbbox((0, 0), trial, font=font)[2] <= max_width:
                cur = trial
            else:
                out_lines.append(cur)
                cur = w
        out_lines.append(cur)
    return "\n".join(out_lines)


def tc_boxed(img, d, y, text, font, fill, sp=0, box_alpha=150, pad_x=36, pad_y=18, radius=22, fade=1.0):
    """반투명 박스 + 그림자를 배경으로 깔고 텍스트를 그린다(사진 배경 위 가독성용).
    2026-09-29 worker-2: 브리프 "굵은 한글서체+반투명박스/그림자 자막" 요구 반영.
    fade: 호출부의 장면 진입/퇴장 페이드(0~1) — 박스 알파도 텍스트와 함께 페이드시켜야
    전환 구간에서 "텍스트는 흐린데 박스는 진한" 유령글씨 현상이 안 생긴다(실측 프리뷰
    프레임에서 발견해 수정 — 2026-09-29)."""
    lines = text.split("\n")
    if not lines or not any(lines) or fade <= 0.03:
        return y
    box_alpha = int(box_alpha * fade)
    widths, heights = [], []
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font)
        widths.append(bb[2] - bb[0])
        heights.append(bb[3] - bb[1])
    block_w = max(widths) if widths else 0
    block_h = sum(heights) + sp * (len(lines) - 1)

    box_x0 = max(0, (W - block_w) / 2 - pad_x)
    box_x1 = min(W, (W + block_w) / 2 + pad_x)
    box_y0 = y - pad_y
    box_y1 = y + block_h + pad_y

    # 성능: 프레임 전체(1080x1920) 대신 박스가 실제로 걸치는 영역만 합성(24fps 렌더에서
    # 프레임당 비용을 크게 줄임 — 2026-09-29 worker-2, 초기 구현은 풀프레임 합성이라 느렸음)
    margin = 12
    rx0 = max(0, int(box_x0 - margin))
    ry0 = max(0, int(box_y0 - margin))
    rx1 = min(W, int(box_x1 + margin))
    ry1 = min(H, int(box_y1 + margin + 6))
    if rx1 <= rx0 or ry1 <= ry0:
        return tc(d, y, text, font, fill, sp)

    region = img.crop((rx0, ry0, rx1, ry1)).convert("RGBA")
    overlay = Image.new("RGBA", region.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    bx0, by0 = box_x0 - rx0, box_y0 - ry0
    bx1, by1 = box_x1 - rx0, box_y1 - ry0
    # 그림자(약간 아래로 오프셋, 더 낮은 알파) + 본 박스
    od.rounded_rectangle([bx0, by0 + 6, bx1, by1 + 6], radius=radius, fill=(0, 0, 0, min(255, box_alpha // 2)))
    od.rounded_rectangle([bx0, by0, bx1, by1], radius=radius, fill=(0, 0, 0, box_alpha))
    region.alpha_composite(overlay)
    img.paste(region.convert("RGB"), (rx0, ry0))

    return tc(d, y, text, font, fill, sp)


_BG_CACHE = {}


def get_cached_gradient(style, name):
    """스타일별 정적 그라디언트(+night 별자리)를 1회만 그리고 재사용 — FPS 24 렌더 성능 확보용.
    2026-09-29 worker-2: FPS 2→24 상향에 따른 캐싱(픽셀 결과는 기존과 동일, night 별자리도
    기존 코드처럼 고정 seed라 프레임마다 동일했으므로 캐싱해도 시각적 차이 없음)."""
    key = (style, name if style == "night" else None)
    cached = _BG_CACHE.get(key)
    if cached is not None:
        return cached.copy()

    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    if style == "dawn":
        for row in range(H):
            p = row / H
            d.line([(0, row), (W, row)], fill=(int(10 + p * 40), int(15 + p * 30), int(35 + p * 45)))
    elif style == "night":
        for row in range(H):
            p = row / H
            d.line([(0, row), (W, row)], fill=(int(5 + p * 3), int(5 + p * 5), int(15 + p * 10)))
        seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        for _ in range(80):
            x, y2 = random.randint(0, W), random.randint(0, H // 2)
            br = random.randint(150, 255)
            d.ellipse([x - 1, y2 - 1, x + 1, y2 + 1], fill=(br, br, br))
    elif style == "golden":
        for row in range(H):
            p = row / H
            d.line([(0, row), (W, row)], fill=(int(25 + p * 30), int(15 + p * 18), int(5 + p * 8)))
    elif style == "rain":
        for row in range(H):
            p = row / H
            d.line([(0, row), (W, row)], fill=(int(8 + p * 4), int(10 + p * 6), int(18 + p * 10)))
    else:
        for row in range(H):
            p = row / H
            d.line([(0, row), (W, row)], fill=(int(8 + p * 6), int(10 + p * 8), int(20 + p * 12)))

    _BG_CACHE[key] = img.copy()
    return img


_KB_SRC_CACHE = {}


def get_ken_burns_frame(bg_path, fp):
    """AI 생성 정지이미지를 1회만 로드해 캐시하고, fp(0..1 장면진행)에 따라 1.0→KEN_BURNS_ZOOM_END
    로 서서히 확대하며 중앙 크롭 → (W,H) 리사이즈해 반환(Ken Burns, 전부 로컬/무료).
    2026-09-29 worker-2: 브리프 "느린 줌(Ken Burns)" 요구 반영."""
    src = _KB_SRC_CACHE.get(bg_path)
    if src is None:
        src = Image.open(bg_path).convert("RGB")
        # 커버 리사이즈: 목표 비율(W:H)을 항상 채우도록 확대(짧은 변 기준)
        target_ratio = W / H
        sw, sh = src.size
        src_ratio = sw / sh
        if src_ratio > target_ratio:
            new_h = H
            new_w = int(H * src_ratio)
        else:
            new_w = W
            new_h = int(W / src_ratio)
        src = src.resize((max(new_w, W), max(new_h, H)), Image.LANCZOS)
        _KB_SRC_CACHE[bg_path] = src

    sw, sh = src.size
    zoom = 1.0 + (KEN_BURNS_ZOOM_END - 1.0) * fp
    crop_w = W / zoom
    crop_h = H / zoom
    cx, cy = sw / 2, sh / 2
    box = (cx - crop_w / 2, cy - crop_h / 2, cx + crop_w / 2, cy + crop_h / 2)
    return src.crop(box).resize((W, H), Image.LANCZOS)


# ═══════════════════════════════════════════════════════════════
# Claude API 호출 (3회 재시도)
# ═══════════════════════════════════════════════════════════════
def clean_surrogates(text):
    return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')

def call_claude(prompt, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", headers={
                "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
            }, json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=60)
            data = r.json()
            if "content" in data:
                return clean_surrogates(data["content"][0]["text"])
            err_msg = data.get("error", {}).get("message", str(data))
            print(f"  API error (attempt {attempt+1}/{retries}): {err_msg}")
        except Exception as e:
            print(f"  API exception (attempt {attempt+1}/{retries}): {e}")
        if attempt < retries - 1:
            time.sleep(10 * (attempt + 1))
    return None


# ═══════════════════════════════════════════════════════════════
# 오늘의 카테고리 결정 (요일 기반)
# ═══════════════════════════════════════════════════════════════
DAY_THEME_MAP = {
    0: "motivation",   # Monday
    1: "healing",      # Tuesday
    2: "growth",       # Wednesday
    3: "comfort",      # Thursday (relationships/comfort)
    4: "healing",      # Friday (rest/healing)
    5: "growth",       # Saturday (reflection/growth)
    6: "comfort",      # Sunday (reflection/comfort)
}

VALID_CATEGORIES = {"comfort", "motivation", "growth", "healing"}

HISTORY_FILE = os.path.join(CONFIG_DIR, "reels-history.json")


def load_history():
    try:
        return json.load(open(HISTORY_FILE, encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {"hooks": [], "fallback_used": {}}


def save_history(h):
    h["hooks"] = h.get("hooks", [])[-30:]
    json.dump(h, open(HISTORY_FILE, "w", encoding='utf-8'), ensure_ascii=False, indent=1)

ACCENT_COLORS = [
    (29, 158, 117),   # teal
    (52, 152, 219),   # blue
    (186, 117, 23),   # gold
    (155, 89, 182),   # purple
    (231, 76, 60),    # red
]

STYLES = ["dawn", "night", "golden", "rain"]


def get_today_category(override=None):
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    if override and override in VALID_CATEGORIES:
        return override, date_str
    weekday = today.weekday()
    return DAY_THEME_MAP[weekday], date_str


# ═══════════════════════════════════════════════════════════════
# AI 릴스 콘텐츠 생성
# ═══════════════════════════════════════════════════════════════
def generate_reel_with_ai(category, date_str, recent_hooks=()):
    """Claude API로 릴스 콘텐츠 생성"""
    day_hash = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
    avoid = "\n".join(f"- {h}" for h in list(recent_hooks)[-30:]) or "- (없음)"

    prompt = f"""당신은 Lighthouse Media의 인스타그램 릴스 크리에이티브 디렉터입니다.
매일 25-45세 직장인/부모/사업가의 마음을 움직이는 30초 릴스를 만듭니다.

오늘 날짜: {date_str}
오늘의 카테고리: {category}
시드 번호: {day_hash} (콘텐츠 다양성을 위해 참고 — 어제와 완전히 다른 주제/톤/관점으로)

=== 최근에 이미 쓴 훅 (이 주제·표현과 겹치지 말 것) ===
{avoid}

=== 브랜드 톤 ===
- 목회자+동행자 — 따뜻하게, 옆에서 걸어가는 느낌
- 기독교적 가치관이 자연스럽게 녹아있되 종교적 용어는 사용하지 않음
- 보편적으로 공감할 수 있는 메시지
- 과장/선동/클릭베이트 절대 금지
- "이 사람 내 마음을 아는구나" 느낌

=== 릴스 구조 원칙 ===
1. hook: 첫 1.7초 — 질문이나 반전으로 스크롤을 멈추게 (15자 이내)
2. scenes: 기승전결(起承轉結) — setup → development → twist → conclusion (5~7개)
3. closing: "보내고 싶은 한 줄" — 누군가가 스크린샷 찍거나 DM으로 보낼 만한 문장

=== 카테고리별 방향 ===
- comfort: 하루 끝에 안아주는 말, 괜찮다는 위로, 지친 마음 돌봄
- motivation: 포기하지 않을 이유, 작은 시작의 힘, 내일의 나를 위한 오늘
- growth: 습관/독서/마인드셋/시간관리, 구체적 실천법 포함
- healing: 자연/고요/감정 돌봄, 쉼의 가치, 내면의 평화

=== 반드시 지킬 것 ===
- hook은 반드시 질문("~하고 있나요?") 또는 반전("~는 거짓말입니다") 형태
- scenes의 text는 10자 이내 (화면에 크게 보여야 함)
- scenes의 sub는 20자 이내 (부연설명)
- 5~7개 장면 (총 27~33초 분량)
- closing은 감성적이고 여운이 남는 한 줄
- caption_kr은 공감형 에세이 (300-500자), 마지막에 반드시 "이 말이 필요한 사람에게 보내주세요" 포함
- caption_kr 첫 줄은 피드에서 잘리지 않는 25자 이내 공감 문장(훅을 반복하지 말고 확장)
- caption_en은 따뜻하고 시적인 영어 1문장
- hashtags는 한국어 위주 5개 이내(대형 태그 1개 + 틈새 태그 4개, 예: #직장인위로 #번아웃회복)

JSON으로 출력:
{{"category": "{category}",
 "hook": "첫 1.7초 훅 (15자 이내, 질문 또는 반전)",
 "scenes": [
   {{"text": "핵심 메시지 (10자 이내)", "sub": "부연 (20자 이내)"}},
   {{"text": "핵심 메시지 (10자 이내)", "sub": "부연 (20자 이내)"}},
   {{"text": "핵심 메시지 (10자 이내)", "sub": "부연 (20자 이내)"}},
   {{"text": "핵심 메시지 (10자 이내)", "sub": "부연 (20자 이내)"}},
   {{"text": "핵심 메시지 (10자 이내)", "sub": "부연 (20자 이내)"}}
 ],
 "closing": "여운이 남는 마지막 한 줄",
 "caption_kr": "한국어 캡션 공감형 에세이 300-500자",
 "caption_en": "English caption warm poetic 2-3 sentences",
 "hashtags": "#위로 #힐링 #healing #selfcare ..."
}}

오직 JSON만 출력하세요. 다른 텍스트 없이."""

    raw = call_claude(prompt)
    if not raw:
        return None

    # JSON 파싱
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return None

    try:
        content = json.loads(raw[start:end])
    except json.JSONDecodeError:
        # 흔한 JSON 오류 수정
        raw_json = raw[start:end]
        raw_json = re.sub(r'(?<!\\)\n(?=.*?")', '\\n', raw_json)
        try:
            content = json.loads(raw_json)
        except json.JSONDecodeError:
            print("  JSON parse failed, retrying with Claude...")
            fix_raw = call_claude(
                f"아래 JSON에 문법 오류가 있어. 수정해서 올바른 JSON만 출력해줘.\n"
                f"```json\n{raw[start:end]}\n```"
            )
            if not fix_raw:
                return None
            fs = fix_raw.find("{")
            fe = fix_raw.rfind("}") + 1
            try:
                content = json.loads(fix_raw[fs:fe])
            except json.JSONDecodeError:
                print("  JSON fix also failed")
                return None

    # 필수 필드 검증
    if "scenes" not in content or not content["scenes"]:
        print("  AI output missing scenes")
        return None

    return content


def ai_to_reel(ai_content, date_str):
    """AI 생성 콘텐츠를 기존 scene 포맷(make_frames 호환)으로 변환"""
    day_hash = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
    scenes_raw = ai_content.get("scenes", [])
    n = len(scenes_raw)
    if n == 0:
        return None, None

    # hook을 첫 번째 장면으로 추가 (있으면)
    hook = ai_content.get("hook", "")
    closing = ai_content.get("closing", "")

    # 전체 장면 구성: hook(있으면) + scenes + closing
    all_scenes_raw = []
    if hook:
        all_scenes_raw.append({"text": hook, "sub": ""})
    all_scenes_raw.extend(scenes_raw)
    if closing:
        all_scenes_raw.append({"text": closing, "sub": "@lighthouse_media77"})

    n_total = len(all_scenes_raw)
    scenes = []
    style_cycle = STYLES.copy()
    random.seed(day_hash)
    random.shuffle(style_cycle)

    # 2026-09-29 worker-2: 총 길이를 장면 수와 무관하게 ~TARGET_TOTAL_DUR초로 정규화
    # (master 지시 — 벤치마크 권장 25~35초, 기존엔 장면수*7초로 커져 43~57초까지 초과했음).
    # 훅·클로징 길이는 고정(가독성 확보), 중간 장면은 남는 시간을 균등분배 — 장면 텍스트/개수는
    # 그대로 두고 "재생 속도"만 조정하므로 콘텐츠 손실 없음(품질 트레이드오프 없는 변경).
    TARGET_TOTAL_DUR = 30
    hook_dur = 2.5 if hook else 5
    closing_dur = 4
    n_middle = max(n_total - 2, 1)
    middle_dur = max(2.8, (TARGET_TOTAL_DUR - hook_dur - closing_dur) / n_middle)

    for i, s in enumerate(all_scenes_raw):
        if i == 0:
            dur = hook_dur
        elif i == n_total - 1:
            dur = closing_dur
        else:
            dur = middle_dur

        accent = ACCENT_COLORS[(day_hash + i) % len(ACCENT_COLORS)]
        style = style_cycle[i % len(style_cycle)]

        scene = {
            "dur": dur,
            "style": style,
            "accent": accent,
            "title": s.get("text", ""),
            "body": s.get("sub", ""),
            "quote_en": "",
            "source": "",
        }
        scenes.append(scene)

    # 캡션 조립
    caption = ai_content.get("caption_kr", "")
    caption_en = ai_content.get("caption_en", "")
    hashtags = ai_content.get("hashtags", "")
    if caption_en:
        caption += f"\n\n{caption_en}"
    if hashtags:
        caption += f"\n\n{hashtags}"

    return scenes, caption


# ═══════════════════════════════════════════════════════════════
# 비상용 폴백 풀 (API 실패 시 사용, 베스트 5개)
# ═══════════════════════════════════════════════════════════════
EMERGENCY_POOL = [
    {
        "scenes": [
            {"dur": 8, "style": "night", "accent": (29, 158, 117),
             "quote_en": "\"You are allowed to be\nboth a masterpiece\nand a work in progress.\"",
             "title": "당신은 이미\n충분히 아름답고\n동시에 성장 중입니다", "source": "- Sophia Bush"},
            {"dur": 7, "style": "rain", "accent": (52, 152, 219),
             "quote_en": "", "title": "오늘 힘들었다면\n그건 약한 게 아니라\n살아있다는 증거입니다",
             "body": "당신의 하루를\n응원합니다"},
            {"dur": 7, "style": "golden", "accent": (186, 117, 23),
             "quote_en": "\"Be gentle with yourself.\nYou're doing the best you can.\"",
             "title": "자신에게\n조금 더\n부드러워지세요", "source": ""},
            {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "", "title": "내일은 오늘보다\n조금 더 괜찮은\n하루가 될 겁니다",
             "body": "@lighthouse_media77"},
        ],
        "cap": "오늘 힘들었다면, 이 영상은 당신을 위한 것입니다.\n\n\"You are allowed to be both a masterpiece and a work in progress.\"\n\n자신에게 조금 더 부드러워지세요.\n내일은 조금 더 괜찮을 겁니다.\n\n이 말이 필요한 사람에게 보내주세요.\n\n#위로 #힐링 #오늘도수고했어 #직장인공감 #마음관리 #selfcare #motivation #healing",
    },
    {
        "scenes": [
            {"dur": 8, "style": "golden", "accent": (186, 117, 23),
             "quote_en": "\"Fall seven times,\nstand up eight.\"",
             "title": "일곱 번 넘어지면\n여덟 번\n일어나면 됩니다", "source": "- 일본 속담"},
            {"dur": 7, "style": "dawn", "accent": (231, 76, 60),
             "quote_en": "", "title": "진짜 강함은\n못한다고 생각한 것을\n해냈을 때 옵니다",
             "body": ""},
            {"dur": 7, "style": "night", "accent": (29, 158, 117),
             "quote_en": "", "title": "실패는 끝이 아닙니다\n다시 시작할\n용기만 있다면",
             "body": ""},
            {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
             "quote_en": "", "title": "당신은 생각보다\n강한 사람입니다",
             "body": "@lighthouse_media77"},
        ],
        "cap": "넘어져도 괜찮습니다.\n\n\"Fall seven times, stand up eight.\"\n\n진짜 강함은 못한다고 생각한 것을 해냈을 때 옵니다.\n당신은 생각보다 강한 사람입니다.\n\n이 말이 필요한 사람에게 보내주세요.\n\n#동기부여 #명언 #도전 #성장 #motivation #strength #nevergiveup #resilience",
    },
    {
        "scenes": [
            {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "\"Small daily improvements\nare the key to staggering\nlong-term results.\"",
             "title": "매일의 작은 개선이\n놀라운 결과를\n만들어냅니다", "source": ""},
            {"dur": 7, "style": "golden", "accent": (186, 117, 23),
             "quote_en": "", "title": "습관이 바뀌면\n인생이 바뀝니다",
             "body": "아침 5분의 루틴이\n하루 전체를 바꿉니다"},
            {"dur": 7, "style": "night", "accent": (52, 152, 219),
             "quote_en": "\"We are what we\nrepeatedly do.\nExcellence is not an act\nbut a habit.\"",
             "title": "탁월함은\n행동이 아니라\n습관입니다", "source": "- Aristotle"},
            {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "", "title": "오늘부터\n작게 시작하세요",
             "body": "@lighthouse_media77"},
        ],
        "cap": "매일 1%씩 성장하세요.\n\n습관이 바뀌면 인생이 바뀝니다.\n아침 5분의 루틴이 하루 전체를 바꿉니다.\n\n이 말이 필요한 사람에게 보내주세요.\n\n#자기계발 #습관 #성장 #dailyhabits #growth #selfdevelopment",
    },
    {
        "scenes": [
            {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "\"In every walk with nature,\none receives far more\nthan he seeks.\"",
             "title": "자연 속을 걸을 때\n우리는 구하는 것보다\n훨씬 더 많은 것을\n받습니다", "source": "- John Muir"},
            {"dur": 7, "style": "rain", "accent": (52, 152, 219),
             "quote_en": "", "title": "바람 소리를\n들어보세요",
             "body": "자연은 최고의\n치유자입니다"},
            {"dur": 7, "style": "golden", "accent": (186, 117, 23),
             "quote_en": "", "title": "하루 10분\n하늘을 올려다보는\n것만으로도\n마음이 가벼워집니다",
             "body": ""},
            {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "", "title": "오늘 잠깐\n바깥 공기를\n마셔보세요",
             "body": "@lighthouse_media77"},
        ],
        "cap": "자연이 주는 위로.\n\n바람 소리를 들어보세요. 하늘을 올려다보세요.\n하루 10분이면 마음이 가벼워집니다.\n\n이 말이 필요한 사람에게 보내주세요.\n\n#힐링 #자연 #마음관리 #산책 #치유 #nature #healing #mindfulness #peace",
    },
    {
        "scenes": [
            {"dur": 8, "style": "night", "accent": (186, 117, 23),
             "quote_en": "\"The happiness of your life\ndepends upon the quality\nof your thoughts.\"",
             "title": "당신 인생의 행복은\n당신 생각의 질에\n달려 있습니다", "source": "- Marcus Aurelius"},
            {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
             "quote_en": "", "title": "생각이 바뀌면\n말이 바뀌고\n말이 바뀌면\n인생이 바뀝니다",
             "body": ""},
            {"dur": 7, "style": "golden", "accent": (231, 76, 60),
             "quote_en": "", "title": "당신은 자신의\n마음을 다스릴 수\n있습니다",
             "body": ""},
            {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
             "quote_en": "", "title": "오늘 어떤 생각을\n선택하시겠습니까",
             "body": "@lighthouse_media77"},
        ],
        "cap": "생각이 운명을 만듭니다.\n\n생각이 바뀌면 말이 바뀌고, 말이 바뀌면 인생이 바뀝니다.\n오늘 어떤 생각을 선택하시겠습니까?\n\n이 말이 필요한 사람에게 보내주세요.\n\n#마음가짐 #스토아철학 #명언 #마인드셋 #mindset #stoicism #thoughts",
    },
]


def pick_emergency_reel(date_str, history):
    """비상 폴백: 최근 30일 안에 쓰지 않은 예비 릴스만 선택. 모두 썼으면 None(게시 건너뜀).
    같은 영상을 반복 게시하면 인스타가 계정 노출을 줄이므로, 안 올리는 편이 낫다."""
    used = history.setdefault("fallback_used", {})
    today = datetime.strptime(date_str, "%Y-%m-%d")
    seed = int(hashlib.md5(date_str.encode()).hexdigest()[:8], 16)
    for k in range(len(EMERGENCY_POOL)):
        idx = (seed + k) % len(EMERGENCY_POOL)
        last = used.get(str(idx))
        if not last or (today - datetime.strptime(last, "%Y-%m-%d")).days >= 30:
            used[str(idx)] = date_str
            return EMERGENCY_POOL[idx]
    return None


# ═══════════════════════════════════════════════════════════════
# 프레임 생성
# ═══════════════════════════════════════════════════════════════
def make_frames(scenes, name, bg_images=None):
    """bg_images: {scene_index: 파일경로} — fal.ai로 생성된 장면별 배경(있는 장면만 Ken Burns
    적용, 없는 장면은 기존 절차형 그라디언트 — 전부-아니면-전무는 상위 호출부 정책, 여기선
    장면 단위로 안전하게 혼용 가능하게 둔다)."""
    bg_images = bg_images or {}
    frames_dir = os.path.join(OUT_DIR, f"frames_{name}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    fnum = 0
    total_dur = sum(s.get("dur", 8) for s in scenes)

    for si, sc in enumerate(scenes):
        dur = sc.get("dur", 8)
        style = sc.get("style", "dark")
        accent = sc.get("accent", (29, 158, 117))
        elapsed = sum(scenes[j].get("dur", 8) for j in range(si))
        bg_path = bg_images.get(si)

        n_frames_scene = max(1, round(dur * FPS))
        for f in range(n_frames_scene):
            fp = f / max(n_frames_scene, 1)
            tp = (elapsed + dur * fp) / total_dur
            # 첫 장면은 첫 프레임부터 완전히 보이게(검은 화면으로 시작하면 1초 안에 넘겨짐)
            fade = 1.0 if si == 0 else min(1.0, fp * 4)
            if fp > 0.8:
                fade = max(0, (1 - fp) * 5)

            # 배경 — AI 사진(Ken Burns) 또는 캐시된 절차형 그라디언트
            if bg_path:
                img = get_ken_burns_frame(bg_path, fp)
                # 사진 위 텍스트 가독성을 위한 은은한 어둡게(전체 25%) — 로컬 합성, 비용 없음
                dim = Image.new("RGB", (W, H), (0, 0, 0))
                img = Image.blend(img, dim, 0.25)
            else:
                img = get_cached_gradient(style, name)
            d = ImageDraw.Draw(img)

            # 시네마틱 바
            d.rectangle([0, 0, W, 70], fill=(0, 0, 0))
            d.rectangle([0, H - 70, W, H], fill=(0, 0, 0))

            bc = tuple(int(c * fade) for c in accent)
            d.rectangle([0, 70, W, 73], fill=bc)

            # 브랜드
            d.text((60, 85), "LIGHTHOUSE MEDIA", font=gf(18), fill=tuple(int(c * fade * 0.5) for c in accent))

            # 영어 명언
            qe = sc.get("quote_en", "")
            if qe:
                tc(d, 320, qe, gf_en(26), tuple(int(140 * fade) for _ in range(3)), 6)

            # 구분선
            lw = int(100 * min(1, fp * 3))
            if lw > 0:
                d.rectangle([W // 2 - lw, 490, W // 2 + lw, 492], fill=bc)

            # 한글 제목 — 굵은서체 + 반투명 박스/그림자(가독성, 사진배경일 때 특히 중요)
            title = sc.get("title", "")
            if si == 0 and not qe:
                # 훅 장면: 크게, 화면 중앙에 — 피드에서 스크롤을 멈추게 하는 첫 1초
                hf = gf(84, True)
                title = wrap_to_width(d, title, hf, W - 120)
                tc_boxed(img, d, 820, title, hf, (255, 255, 255), 28, fade=fade)
            else:
                mf = gf(52, True)
                title = wrap_to_width(d, title, mf, W - 140)
                tc_boxed(img, d, 540, title, mf, tuple(int(255 * fade) for _ in range(3)), 20, fade=fade)

            # 부제
            body = sc.get("body", "")
            if body:
                tc(d, 880, body, gf(26, False), tuple(int(160 * fade) for _ in range(3)), 10)

            # 출처
            src = sc.get("source", "")
            if src:
                tc(d, H - 220, src, gf(20, False), tuple(int(c * fade * 0.5) for c in accent))

            # 하단 장식
            d.rectangle([W // 2 - 25, H - 140, W // 2 + 25, H - 137], fill=bc)
            tc(d, H - 120, "@lighthouse_media77", gf(14, False), tuple(int(50 * fade) for _ in range(3)))

            # 진행바
            d.rectangle([0, H - 70, int(W * tp), H - 67], fill=bc)

            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    return frames_dir, total_dur, fnum


# ═══════════════════════════════════════════════════════════════
# 영상 인코딩
# ═══════════════════════════════════════════════════════════════
def encode_video(frames_dir, total_dur, bgm_file, output_name):
    vpath = os.path.join(OUT_DIR, f"{output_name}.mp4")
    bgm_path = os.path.join(BGM_DIR, bgm_file)

    cmd = [FFMPEG, "-y",
           "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
           "-i", bgm_path,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k",
           "-filter_complex", f"[1:a]afade=t=in:d=1,afade=t=out:st={max(1, total_dur - 2)}:d=2,volume=0.3[a]",
           "-map", "0:v", "-map", "[a]",
           "-vf", f"scale={W}:{H},fps=30",
           "-t", str(total_dur), "-shortest",
           vpath]

    subprocess.run(cmd, capture_output=True, timeout=120)
    shutil.rmtree(frames_dir, ignore_errors=True)

    return vpath if os.path.exists(vpath) else None


# ═══════════════════════════════════════════════════════════════
# 업로드 (Instagram Reels + Facebook)
# ═══════════════════════════════════════════════════════════════
def upload_ig_reels(vpath, caption):
    # Imgur에 영상 업로드
    with open(vpath, 'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/upload',
                       headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                       data={'video': enc, 'type': 'base64'}, timeout=120)
    vid_url = ir.json().get('data', {}).get('link')
    if not vid_url:
        print("    Imgur upload failed")
        return None

    print(f"    Imgur OK: {vid_url}")

    # 릴스 컨테이너 생성
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
        'video_url': vid_url,
        'media_type': 'REELS',
        'caption': caption,
        'access_token': IG_TOKEN,
    }, timeout=30)
    d = r.json()
    if 'id' not in d:
        print(f"    IG container failed: {d}")
        return None

    container_id = d['id']
    print(f"    IG container: {container_id}")

    # 처리 대기
    for attempt in range(18):  # 최대 3분
        time.sleep(10)
        check = requests.get(
            f'https://graph.facebook.com/v21.0/{container_id}?fields=status_code&access_token={IG_TOKEN}',
            timeout=10)
        status = check.json().get('status_code', '')
        if status == 'FINISHED':
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
                               data={'creation_id': container_id, 'access_token': IG_TOKEN}, timeout=30)
            return r2.json().get('id')
        elif status == 'ERROR':
            print(f"    IG processing error")
            return None
        print(f"    Processing... ({(attempt + 1) * 10}s)")
    return None


def upload_fb_video(vpath, description):
    with open(vpath, 'rb') as f:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/videos',
                          files={'source': (os.path.basename(vpath), f, 'video/mp4')},
                          data={'description': description[:500], 'access_token': FB_TOKEN}, timeout=120)
    return r.json()


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    # --visual=ai 명시적 opt-in만 fal.ai 사용. 플래그 없는 기본 호출(스케줄러 .bat 포함)은
    # 지금까지와 완전히 동일한 절차형 배경 — 성공기준 "실제 게시·스케줄러 변경 없음" 보장.
    visual_arg = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--visual=")), "procedural")
    out_subdir_arg = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--outsubdir=")), None)
    category_arg = args[0] if args else None
    history = load_history()

    print("=" * 60)
    print("  DAILY INSTAGRAM REELS (AI-Generated)" + ("  [DRY-RUN: 업로드 안 함]" if dry_run else "")
          + (f"  [visual={visual_arg}]" if visual_arg != "procedural" else ""))
    print("=" * 60)

    cat, today = get_today_category(category_arg)
    name = f"daily-{today}-{cat}" + ("-dryrun" if dry_run else "")

    print(f"\n  Date: {today}")
    print(f"  Category: {cat}")

    # AI 콘텐츠 생성
    print("\n  [1/4] AI content generation...")
    ai_content = generate_reel_with_ai(cat, today, history.get("hooks", []))

    scenes = None
    caption = None
    source = "AI"

    if ai_content:
        scenes, caption = ai_to_reel(ai_content, today)
        if scenes:
            print(f"  AI generated: {len(scenes)} scenes")
            hook = ai_content.get("hook", "N/A")
            closing = ai_content.get("closing", "N/A")
            print(f"  Hook: {hook}")
            print(f"  Closing: {closing}")

    # 폴백
    if not scenes:
        fallback = pick_emergency_reel(today, history)
        if not fallback:
            print("  AI 생성 실패 + 최근 30일 안에 예비 릴스를 모두 사용 — 반복 게시 방지 위해 오늘은 건너뜀")
            return
        print("  AI generation failed — using emergency fallback (30일 1회 제한)")
        source = "FALLBACK"
        scenes = fallback["scenes"]
        caption = fallback["cap"]

    # BGM 선택 — 카테고리 분위기에 맞춰 후보군을 좁힌 뒤 랜덤 선택
    # 2026-09-29 worker-2: 1단계 품질기준표(00-benchmark-and-rubric.md) 항목5②
    # "현재는 완전 랜덤이라 카테고리-곡 매칭이 없음, 개선 후보" 반영. 매칭 후보가 비면(파일명
    # 변경 등) 기존처럼 전체 폴에서 랜덤 — 안전 폴백.
    bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
    CATEGORY_BGM = {
        "comfort": ["calm-piano", "soft-acoustic", "emotional", "ambient-dream"],
        "motivation": ["motivational", "upbeat-energy", "cinematic-hope"],
        "growth": ["morning-coffee", "cinematic-hope", "upbeat-energy"],
        "healing": ["healing", "night-rain", "sunset-waves", "lofi-chill", "ambient-dream"],
    }
    matched = [f for f in bgm_files if any(k in f for k in CATEGORY_BGM.get(cat, []))]
    bgm = random.choice(matched or bgm_files)
    print(f"  BGM: {bgm}" + ("" if matched else "  (카테고리 매칭 후보 없음 — 전체 폴에서 선택)"))
    print(f"  Source: {source}")

    # AI 비주얼(opt-in) — cost-preview-confirm 게이트를 lib/fal_visuals.py가 수행.
    # 실패/예산초과/키없음이면 (None, 사유)로 안전 폴백 — 절차형 그라디언트로 계속 진행.
    bg_images = {}
    if visual_arg == "ai":
        print("\n  [1.5/4] AI 배경 이미지 생성(fal.ai)...")
        if not FAL_VISUALS_AVAILABLE:
            print(f"  AI 비주얼 모듈 로드 실패({_FAL_IMPORT_ERR}) — 절차형 배경으로 진행")
        else:
            images_dir = os.path.join(OUT_DIR, f"images_{name}")
            # 중복과금 방지: 같은 날짜·카테고리로 이미 과금받은 이미지가 있고 장면수가 정확히
            # 일치하면 재사용(2026-10-03 master 지시 — 메모리부족 중단 재시도 시 이미 생성된
            # motivation 8장을 재사용하도록). 장면수가 다르면(AI 콘텐츠가 매번 달라질 수 있음)
            # 안전하게 재호출한다.
            existing = sorted(
                os.path.join(images_dir, f) for f in os.listdir(images_dir)
                if f.startswith("scene_") and f.endswith(".png")
            ) if os.path.isdir(images_dir) else []
            if len(existing) == len(scenes) and all(os.path.getsize(p) > 0 for p in existing):
                paths, err = existing, None
                print(f"  기존 AI 배경 {len(existing)}장 재사용(중복과금 방지) — {images_dir}")
            else:
                paths, err = fv.generate_all_scene_images(scenes, cat, images_dir, name)
            if paths:
                bg_images = {i: p for i, p in enumerate(paths)}
                print(f"  AI 배경 {len(paths)}장 준비 완료 — Ken Burns 적용 예정")
            else:
                print(f"  AI 배경 생성 생략({err}) — 절차형 배경으로 폴백")

    # 프레임 생성
    print("\n  [2/4] Generating frames...")
    frames_dir, total_dur, fnum = make_frames(scenes, name, bg_images=bg_images)
    print(f"  {fnum} frames ({total_dur}s)")

    # 영상 인코딩
    print("\n  [3/4] Encoding video...")
    vpath = encode_video(frames_dir, total_dur, bgm, name)
    if not vpath:
        print("  ENCODE FAILED!")
        return
    sz = os.path.getsize(vpath) / (1024 * 1024)
    print(f"  Video: {vpath} ({sz:.1f}MB)")

    if out_subdir_arg:
        dest_dir = os.path.join(OUT_DIR, out_subdir_arg)
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(vpath))
        shutil.copy2(vpath, dest_path)
        print(f"  샘플 사본: {dest_path}")

    if dry_run:
        print("\n  [4/4] DRY-RUN — 업로드 생략")
        print(f"  캡션 미리보기:\n{caption}")
        return

    # 게시 전에 기록(같은 주제 반복 방지 · 예비 릴스 사용일)
    if ai_content and source == "AI" and ai_content.get("hook"):
        history.setdefault("hooks", []).append(ai_content["hook"])
    save_history(history)

    # Facebook 업로드
    print("\n  [4/4] Uploading to SNS...")
    print("  Uploading to Facebook...")
    fb = upload_fb_video(vpath, caption)
    print(f"  FB: {'OK (' + str(fb.get('id', '')) + ')' if 'id' in fb else fb}")
    time.sleep(3)

    # Instagram Reels 업로드
    print("  Uploading to Instagram Reels...")
    ig = upload_ig_reels(vpath, caption)
    print(f"  IG Reels: {'OK (' + str(ig) + ')' if ig else 'Failed or processing'}")

    print(f"\n{'=' * 60}")
    print(f"  DAILY REELS DONE! (source: {source})")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
