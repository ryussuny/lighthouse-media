"""Lighthouse Media — 하루 1개 프리미엄 콘텐츠 (음악 포함 릴스)
매일 저녁 7시, 신중하고 깊이 있는 콘텐츠 1개만."""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env"), encoding='utf-8'):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"
BGM_DIR = os.path.join(HOME, "lighthouse-media", "assets", "bgm")

TODAY = datetime.now()
DATE_STR = TODAY.strftime("%Y-%m-%d")
DAY_NUM = TODAY.timetuple().tm_yday  # 연중 몇번째 날 (음악/주제 순환용)
OUT = os.path.join(HOME, "lighthouse-media", "output", DATE_STR, "premium")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1920  # 릴스 세로
FPS = 2

# === 폰트 ===
def ft(s):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, s)
            except: pass
    return ImageFont.load_default()

def ft_l(s):
    for p in ['C:/Windows/Fonts/HANBatang.ttf','C:/Windows/Fonts/malgun.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, s)
            except: pass
    return ImageFont.load_default()

def ft_s(s):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', s) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

def ft_sb(s):
    return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', s) if os.path.exists('C:/Windows/Fonts/malgunbd.ttf') else ImageFont.load_default()

# === 색상 팔레트 (요일별 순환) ===
palettes = [
    {"bg":(248,245,237), "accent":(180,150,80), "text":(55,45,35), "sub":(100,80,60), "dark_bg":(28,25,32), "name":"ivory-gold"},
    {"bg":(240,245,240), "accent":(90,130,90), "text":(40,55,40), "sub":(80,110,80), "dark_bg":(22,30,25), "name":"sage"},
    {"bg":(245,240,235), "accent":(160,120,80), "text":(60,45,35), "sub":(130,100,70), "dark_bg":(30,25,20), "name":"warm-brown"},
    {"bg":(238,242,248), "accent":(100,120,160), "text":(35,45,65), "sub":(70,90,130), "dark_bg":(20,25,35), "name":"blue-gray"},
    {"bg":(248,243,238), "accent":(150,100,80), "text":(55,40,35), "sub":(120,85,65), "dark_bg":(30,22,18), "name":"terracotta"},
]

pal = palettes[DAY_NUM % len(palettes)]

def ctr(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp + 5; continue
        # 줄바꿈 (최대 14자)
        while len(ln) > 14:
            part = ln[:14]
            bb = d.textbbox((0,0), part, font=font)
            d.text(((W-(bb[2]-bb[0]))/2, y), part, font=font, fill=fill)
            y += bb[3]-bb[1] + 8
            ln = ln[14:]
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def grain(img, intensity=3):
    d = ImageDraw.Draw(img)
    w, h = img.size
    random.seed(DAY_NUM)
    for _ in range(3000):
        x, y = random.randint(0,w-1), random.randint(0,h-1)
        px = img.getpixel((x,y))
        v = random.randint(-intensity, intensity)
        img.putpixel((x,y), tuple(max(0,min(255,c+v)) for c in px))

def dots(d, y, color):
    cx = W//2
    for off in [-20,-7,0,7,20]:
        d.ellipse([cx+off-2, y, cx+off+2, y+4], fill=color)

def cross(d, y, color):
    cx = W//2
    d.rectangle([cx-1, y, cx+1, y+35], fill=color)
    d.rectangle([cx-13, y+15, cx+13, y+17], fill=color)

def clean_surrogates(text):
    """surrogate 문자 제거 (API 응답에서 간헐적 발생)"""
    return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')

def claude(prompt, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", headers={
                "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
            }, json={"model": "claude-sonnet-4-6", "max_tokens": 2000, "messages": [{"role":"user","content":prompt}]}, timeout=60)
            data = r.json()
            if "content" in data:
                return clean_surrogates(data["content"][0]["text"])
            err_msg = data.get("error", {}).get("message", str(data))
            print(f"  API error (attempt {attempt+1}/{retries}): {err_msg}")
        except Exception as e:
            print(f"  API exception (attempt {attempt+1}/{retries}): {e}")
        if attempt < retries - 1:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("Claude API failed after all retries")

# === 오늘의 콘텐츠 생성 ===
print("=" * 50)
print(f" Lighthouse Media Premium ({DATE_STR})")
print(f"  Palette: {pal['name']}")
print("=" * 50)

print("\n[1/4] AI content generation (deep quality mode)...")

# 다양한 깊이 있는 주제 풀 (매일 다른 주제) — 7개 카테고리, 100+개
import hashlib

deep_themes = [
    # ── 감정 (Emotions) ──
    "분노 뒤에 숨은 슬픔 — 화를 내는 진짜 이유를 알 때",
    "불안과의 동거 — 없애려 하지 말고 함께 걷는 법",
    "기쁨을 허락하는 법 — 행복해도 괜찮다는 허락",
    "눈물의 언어 — 울음이 말해주는 것들",
    "무감각이라는 신호 — 아무것도 느끼지 못할 때",
    "질투가 가르쳐주는 것 — 내가 진짜 원하는 것의 지도",
    "수치심과 죄책감의 차이 — 나를 공격하는 감정 다루기",
    "외로움의 정체 — 사람 사이에서 느끼는 고독",
    "감정을 이름 붙이는 순간 — 감정 문해력이라는 힘",
    "완벽주의의 진짜 이름은 두려움이다",
    "말하지 못한 감정이 몸에 저장될 때",
    "두려움과 설렘은 같은 심장 박동이다",
    "후회라는 감정의 쓸모 — 과거가 보내는 편지",
    "괜찮지 않아도 괜찮다 — 솔직함이 주는 해방",
    "감정의 파도를 타는 법 — 90초의 과학",

    # ── 관계 (Relationships) ──
    "말하지 못한 사과 — 입 안에서 삼킨 말들의 무게",
    "거리두기의 지혜 — 사랑하면서 떨어져 있는 기술",
    "사랑의 다른 언어 — 같은 말이 다르게 들릴 때",
    "관계에서 상처받는 패턴을 알아차리는 법",
    "경계를 세우는 것은 이기적이 아니라 건강한 것이다",
    "부모와 화해하는 법 — 완벽하지 않은 사랑 이해하기",
    "좋은 대화의 조건 — 듣는 것이 말하는 것보다 어렵다",
    "이별 후에 남는 것 — 관계가 가르쳐준 나",
    "사랑은 감정이 아니라 매일의 선택이다",
    "디지털 시대의 진짜 연결 — 깊은 대화의 기술",
    "혼자 밥 먹는 용기 — 관계의 질과 양 사이에서",
    "갈등이 관계를 키운다 — 싸우는 법을 아는 사이",
    "떠나야 할 관계를 알아보는 법 — 사랑과 집착 사이",
    "친구가 줄어드는 나이 — 관계의 편집이 필요한 시기",
    "말투가 관계를 결정한다 — 한 마디의 온도",

    # ── 성장 (Growth) ──
    "실패의 선물 — 넘어져야 보이는 풍경",
    "느린 성장의 힘 — 대나무는 5년을 땅속에서 보낸다",
    "40대의 재발견 — 인생 후반전을 위한 마인드셋 리셋",
    "비교가 멈추는 순간 — 나만의 타임라인으로 사는 법",
    "성장통이 필요한 이유 — 불편함이 성장의 신호",
    "꿈을 미루는 진짜 이유와 오늘 시작하는 한 걸음",
    "리더십은 직함이 아니라 영향력이다",
    "창의성은 재능이 아니라 용기의 문제",
    "작은 습관이 인생을 바꾸는 과학적 이유",
    "30대의 정체기 — 멈춤이 후퇴가 아닌 이유",
    "배움에 나이가 없다는 말의 진짜 의미",
    "완성이 아니라 방향이다 — 매일 1%의 변화",
    "자기 자신에게 하는 말이 인생을 결정한다",
    "포기의 기술 — 버려야 할 것을 아는 지혜",
    "나의 한계가 나의 시작점이다 — 약점을 전략으로",

    # ── 회복 (Healing) ──
    "트라우마 이후의 일상 — 회복은 직선이 아니다",
    "슬픔의 단계들 — 충분히 슬퍼하는 것의 치유력",
    "자기 용서 — 가장 어려운 종류의 용서",
    "번아웃 뒤에 남는 것 — 소진이 가르쳐주는 진짜 우선순위",
    "과거의 나와 화해하는 법 — 그때의 나도 최선이었다",
    "용서는 상대를 위한 것이 아니라 나를 자유롭게 하는 것",
    "상처가 지혜가 되는 순간 — 킨츠기라는 철학",
    "회복탄력성은 타고나는 것이 아니라 연습하는 것이다",
    "멈춰도 괜찮다 — 쉼이 게으름이 아닌 이유",
    "다시 시작하는 법 — 리셋 버튼은 언제나 있다",
    "불면의 밤이 말하는 것 — 마음이 보내는 SOS",
    "내면의 비평가 잠재우기 — 나를 향한 잔소리 멈추기",
    "취약함을 보여주는 용기가 진짜 강함이다",
    "완벽하지 않은 하루도 의미 있다 — 불완전함의 미학",
    "지친 마음에 보내는 편지 — 잘하고 있다는 증거들",

    # ── 일상 (Daily Life) ──
    "출퇴근길의 명상 — 지하철 30분이 달라지는 법",
    "밥 한 끼의 의미 — 누군가와 나누는 식탁의 힘",
    "계절이 가르쳐주는 것 — 자연의 리듬으로 사는 지혜",
    "매일 같은 일상이 지루할 때 — 일상의 재발견",
    "돈보다 중요한 진짜 부 — 시간과 관계의 경제학",
    "목적 없는 바쁨에서 벗어나는 법",
    "아침 루틴의 과학 — 하루를 결정하는 첫 30분",
    "잠드기 전 5분 — 하루를 마무리하는 의식의 힘",
    "정리의 심리학 — 공간을 비우면 마음이 열린다",
    "산책의 철학 — 걸을 때 뇌에서 일어나는 일",
    "혼자인 시간의 힘 — 고독과 외로움의 차이",
    "스마트폰을 내려놓는 순간 — 디지털 디톡스의 효과",
    "책 한 권의 무게 — 독서가 뇌를 바꾸는 과학",
    "요리라는 명상 — 손을 쓸 때 마음이 고요해진다",
    "느리게 걷는 연습 — 속도를 줄이면 보이는 것들",

    # ── 영성 (Spirituality — subtle) ──
    "침묵의 힘 — 말하지 않아도 전해지는 것들",
    "감사의 과학 — 뇌가 바뀌는 감사의 신경과학",
    "용서가 자유인 이유 — 붙잡고 있던 것을 놓을 때",
    "지금 이 순간이 전부라는 것의 깊은 의미",
    "느린 것이 빠른 것이다 — 조급함을 내려놓는 지혜",
    "나이 듦이 가르쳐주는 것들 — 시간의 지혜",
    "고통 속에서 의미를 찾는 법 — 빅터 프랭클의 통찰",
    "겸손이 자신감이 되는 역설 — 아는 만큼 작아지는 것",
    "기다림의 기술 — 인내가 만드는 깊이",
    "비움의 역설 — 가진 것을 놓을 때 얻는 것",
    "감사 일기를 21일 쓰면 벌어지는 일",
    "자연 앞에서 겸손해지는 순간 — 경이의 감정",
    "섬김이 리더십이 되는 순간 — 낮은 곳의 힘",
    "고요함 속에서 듣는 법 — 내면의 목소리",
    "삶의 의미는 찾는 것이 아니라 만드는 것이다",

    # ── 시의성 (Timely / Seasonal) ──
    "월요일 아침 — 한 주를 여는 마음의 온도",
    "비 오는 날의 위로 — 날씨가 감정에 미치는 영향",
    "금요일 저녁의 해방감 — 쉼의 질을 높이는 법",
    "새벽 4시의 고요함 — 세상이 잠든 사이 깨어 있는 것",
    "계절이 바뀌는 길목에서 — 변화를 감지하는 감각",
    "연말이 두려운 사람들에게 — 숫자가 아닌 것으로 한 해를 세는 법",
    "생일 즈음에 — 나이 한 살의 무게와 선물",
    "장마철 우울 — 빛이 줄어들 때 마음을 돌보는 법",
    "여름밤의 불면 — 더위가 아니라 마음이 뜨거운 것",
    "가을이 오면 — 무언가를 놓아주기 좋은 계절",
    "겨울의 느린 시간 — 자연이 쉬는 법을 배우다",
    "명절이 힘든 사람들에게 — 가족이라는 이름의 과제",
    "새해 첫날의 함정 — 결심이 아니라 시스템을 바꿔라",
    "수요일의 무기력 — 한 주의 한가운데서 중심잡기",
    "일요일 저녁의 불안 — 내일을 맞이하는 마음 준비",
]
day_hash = int(hashlib.md5(DATE_STR.encode()).hexdigest()[:8], 16)
today_theme = deep_themes[day_hash % len(deep_themes)]

# 심리학 프레임워크 순환 (매일 다른 렌즈)
frameworks = [
    "ACT(수용전념치료) — 생각과 감정을 통제하려 하지 말고 수용하며 가치 방향으로 행동하는 관점",
    "CBT(인지행동치료) — 생각이 감정을 만든다는 관점. 자동적 사고를 알아차리고 재구성하기",
    "회복탄력성(Resilience) — 역경 후 회복하는 힘. 사회적 지지, 자기효능감, 의미 부여의 세 기둥",
    "브레네 브라운의 취약성(Vulnerability) — 취약함을 보여줄 용기가 진짜 연결과 강함의 시작",
    "마틴 셀리그만의 긍정심리학(PERMA) — 긍정정서, 몰입, 관계, 의미, 성취의 다섯 기둥",
    "빅터 프랭클의 로고테라피(Logotherapy) — 어떤 상황에서든 의미를 찾을 자유가 있다",
    "자기결정이론(Self-Determination) — 자율성, 유능감, 관계성이 내적 동기의 세 축",
    "성장 마인드셋(Growth Mindset) — 능력은 고정이 아니라 노력으로 성장한다는 믿음",
    "마음챙김(MBSR) — 판단 없이 지금 이 순간에 주의를 기울이는 연습",
    "애착이론(Attachment Theory) — 초기 관계 패턴이 평생의 관계 방식을 형성한다",
]
today_framework = frameworks[day_hash % len(frameworks)]

content_raw = claude(
    f"당신은 Lighthouse Media의 수석 콘텐츠 디렉터입니다.\n"
    f"오늘 날짜: {DATE_STR}\n"
    f"오늘의 주제: {today_theme}\n"
    f"오늘의 심리학 렌즈: {today_framework}\n\n"
    "=== 당신의 목소리 ===\n"
    "당신은 목회자이자 동행자입니다. 설교하지 않습니다. 옆에서 함께 걷습니다.\n"
    "따뜻하지만 지적인 깊이가 있고, 독자의 삶에 진짜 닿는 글을 씁니다.\n"
    "기독교 가치관(은혜, 용서, 섬김, 회복)은 DNA처럼 녹아있되 종교 용어는 쓰지 않습니다.\n"
    "누가 읽어도 고개를 끄덕이는 보편적 지혜입니다.\n\n"
    "=== 타겟 ===\n"
    "25-45세 바쁜 직장인, 부모, 사업가 — 삶의 의미를 찾고 싶지만 여유가 없는 사람들\n\n"
    "=== 글쓰기 원칙 (반드시 지켜라) ===\n\n"
    "1. **생생한 첫 장면 (Real-life scenario opening)**\n"
    "   추상적 시작 금지. 구체적 순간으로 시작하라.\n"
    '   나쁜 예: "우리는 모두 지쳐 있습니다"\n'
    '   좋은 예: "퇴근길 지하철에서 창밖을 보다가 갑자기 눈물이 났다면..."\n'
    '   좋은 예: "새벽 2시, 또 눈이 떠졌다. 내일 회의가 걱정되는 게 아니라, 뭐가 걱정인지 모르겠는 게 문제다."\n\n'
    "2. **하나의 연구/근거 (One research finding)**\n"
    "   반드시 1개의 구체적 연구 결과나 심리학 개념을 포함하라.\n"
    f"   오늘의 렌즈({today_framework.split('—')[0].strip()})를 자연스럽게 녹여라.\n"
    '   예: "하버드 성인발달연구 75년의 결론은 단 하나였다 — 좋은 관계가 좋은 삶을 만든다."\n'
    '   예: "신경과학자 질 볼트 테일러에 따르면, 감정의 화학적 수명은 90초다."\n\n'
    "3. **반전 (Perspective twist)**\n"
    "   에세이 중간에 반드시 관점이 뒤집히는 순간이 있어야 한다.\n"
    '   예: "그런데 정말 강한 사람은 눈물을 참는 사람이 아니었다..."\n'
    '   예: "우리가 두려워하는 것은 실패가 아니다. 진짜 두려운 것은..."\n\n'
    "4. **마이크로 액션 (Micro-action)**\n"
    '   "자신을 사랑하세요" 같은 뜬구름 금지. 오늘 당장 할 수 있는 구체적 행동 1개.\n'
    '   예: "오늘 밤 자기 전, 거울을 보고 \'수고했어\' 한 마디만 하세요."\n'
    '   예: "지금 핸드폰을 내려놓고, 3번 깊게 숨을 쉬어보세요. 4초 들이쉬고, 7초 내쉬고."\n\n'
    "5. **공유 트리거 (Shareability hook)**\n"
    "   캡션 끝에 '지금 떠오르는 사람에게 보내주세요'를 자연스럽게 포함하라.\n"
    "   읽는 사람이 '이거 내 친구한테 보내야 해'라고 느끼게 하라.\n\n"
    "=== JSON 출력 형식 ===\n"
    '{"topic": "주제 카테고리 (감정/관계/성장/회복/일상/영성/시의성 중 택1)",\n'
    ' "hook": "첫 장면 — 생생한 상황 묘사 한 문장 (15자 이내, 카드 표시용)",\n'
    ' "hook_quote": "핵심 인용구 — 에세이의 한 줄 요약 (임팩트 있게)",\n'
    ' "scenes": [\n'
    '   {"text": "장면 핵심 (10자 이내)", "sub": "부연 설명 (20자 이내, 깊이 있게)"},\n'
    '   ... (6~8장면 — 기승전결 + 반전 구조)\n'
    ' ],\n'
    ' "closing": "마무리 — 여운이 남는 한 문장",\n'
    ' "one_liner": "오늘의 한마디 — 기억에 새겨질 한 줄",\n'
    ' "daily_practice": "마이크로 액션 — 지금 당장 할 수 있는 구체적 행동 1개 (2문장)",\n'
    ' "body_empathy": "공감 문단 — 구체적 상황의 생생한 묘사로 시작 (3-4문장, 읽는 사람이 \'이건 나 얘기다\' 느끼게)",\n'
    ' "body_insight": "인사이트 문단 — 오늘의 심리학 렌즈 기반 연구/근거 1개를 자연스럽게 녹인 새 관점 (3-4문장)",\n'
    ' "body_action": "실천 문단 — 마이크로 액션과 그 과학적 효과 (3-4문장, 구체적이고 즉시 실행 가능)",\n'
    ' "body_depth": "반전 문단 — 관점이 뒤집히는 순간. \'그런데 정말은...\' (2-3문장, 역설/반전 필수)",\n'
    ' "hashtags_kr": "#힐링 #자기계발 #번아웃 #직장인 #마음관리 #위로 #공감 #멘탈케어 #일상 #하루 #에세이 #깊은생각",\n'
    ' "hashtags_en": "#LighthouseMedia #SelfCare #Motivation #Healing #Mindfulness #DeepThoughts #InnerPeace",\n'
    ' "caption": "인스타 캡션 에세이 (아래 구조 준수, 500-700자)"}\n\n'
    "=== 캡션 구조 (반드시 이 순서) ===\n"
    "1) hook_quote (인용구로 시작)\n"
    "2) body_empathy (공감 — 생생한 장면)\n"
    "3) body_insight (인사이트 — 연구/근거)\n"
    "4) body_depth (반전 — 관점 뒤집기)\n"
    "5) body_action (실천 — 마이크로 액션)\n"
    "6) one_liner (한 줄 정리)\n"
    "7) daily_practice (오늘의 실천)\n"
    "8) '지금 이 글을 읽고 떠오르는 사람이 있다면, 보내주세요.'\n"
    "9) hashtags\n\n"
    "=== 금지 사항 ===\n"
    "- 추상적 위로 금지 (구체적 장면과 행동으로)\n"
    "- 과장/선동/클릭베이트 절대 금지\n"
    "- 종교 용어 금지 (기도, 하나님, 은혜, 축복 등 직접 표현 금지)\n"
    "- 한 장면 텍스트 최대 10자 (영상 카드용)\n"
    "- 캡션은 미니 에세이 수준 (500-700자)"
)

start = content_raw.find("{")
end = content_raw.rfind("}") + 1
try:
    content = json.loads(content_raw[start:end])
except json.JSONDecodeError:
    # JSON 파싱 실패 시 재시도 (Claude에게 수정 요청)
    import re
    raw_json = content_raw[start:end]
    # 흔한 JSON 오류 수정: 줄바꿈이 포함된 문자열 값
    raw_json = re.sub(r'(?<!\\)\n(?=.*?")', '\\n', raw_json)
    try:
        content = json.loads(raw_json)
    except json.JSONDecodeError:
        print("  JSON parse failed, retrying with Claude...")
        fix_raw = claude(
            f"아래 JSON에 문법 오류가 있어. 수정해서 올바른 JSON만 출력해줘.\n"
            f"```json\n{content_raw[start:end]}\n```"
        )
        fs = fix_raw.find("{")
        fe = fix_raw.rfind("}") + 1
        content = json.loads(fix_raw[fs:fe])
# surrogate 문자 제거 (모든 문자열 값)
for k, v in content.items():
    if isinstance(v, str):
        content[k] = clean_surrogates(v)
    elif isinstance(v, list):
        content[k] = [clean_surrogates(x) if isinstance(x, str) else
                       {sk: clean_surrogates(sv) if isinstance(sv, str) else sv for sk, sv in x.items()} if isinstance(x, dict) else x
                       for x in v]
# 필수 키 폴백
defaults = {
    'topic': '성장', 'hook': today_theme.split('—')[0].strip(),
    'hook_quote': today_theme, 'closing': '오늘도 한 걸음.',
    'one_liner': '작은 변화가 큰 차이를 만든다.',
    'daily_practice': '오늘 하루, 잠깐 멈추고 나를 돌아보세요.',
    'body_empathy': '', 'body_insight': '', 'body_action': '', 'body_depth': '',
    'hashtags_kr': '#힐링 #자기계발 #마음관리 #위로',
    'hashtags_en': '#LighthouseMedia #SelfCare #Healing',
    'caption': '', 'scenes': [],
}
for k, v in defaults.items():
    if k not in content or not content[k]:
        content[k] = v
if not content.get('scenes'):
    content['scenes'] = [{"text": content.get('hook', ''), "sub": content.get('one_liner', '')}]

print(f"  Topic: {content.get('topic', '성장')}")
print(f"  Hook: {content.get('hook', today_theme)}")

# 콘텐츠 JSON 저장 (확인용)
with open(os.path.join(OUT, "content.json"), 'w', encoding='utf-8') as f:
    json.dump(content, f, ensure_ascii=False, indent=2)

# === 릴스 영상 제작 ===
print("\n[2/4] Creating premium video...")

scenes_data = []
# 오프닝
scenes_data.append({"dur": 6, "bg": pal['bg'], "items": [
    {"y": 700, "text": content.get('hook', ''), "font": ft(48), "color": pal['text']},
]})

# 본문 장면들
for sc in content.get('scenes', []):
    scenes_data.append({"dur": 7, "bg": pal['bg'], "items": [
        {"y": 650, "text": sc['text'], "font": ft(52), "color": pal['text']},
        {"y": 850, "text": sc.get('sub',''), "font": ft_l(28), "color": pal['sub']},
    ]})

# 마무리
scenes_data.append({"dur": 7, "bg": pal['dark_bg'], "items": [
    {"y": 700, "text": content.get('closing', content.get('one_liner', '')), "font": ft(42), "color": (220,215,205)},
]})

# 클로징
scenes_data.append({"dur": 5, "bg": pal['bg'], "items": [
    {"y": 750, "text": "Lighthouse Media", "font": ft_sb(22), "color": pal['accent']},
    {"y": 800, "text": "@lighthouse_media77", "font": ft_s(16), "color": (170,155,135)},
]})

# 프레임 생성
FRAMES = os.path.join(OUT, "frames")
os.makedirs(FRAMES, exist_ok=True)
fn = 0
total_dur = sum(s['dur'] for s in scenes_data)

for si, scene in enumerate(scenes_data):
    dur = scene['dur']
    bg = scene['bg']
    elapsed = sum(scenes_data[j]['dur'] for j in range(si))

    for f in range(dur * FPS):
        fp = f / max(dur*FPS, 1)
        fade = min(1.0, fp * 3)
        if fp > 0.85: fade = max(0, (1-fp) * 7)

        img = Image.new('RGB', (W, H), bg)
        grain(img, 3)
        d = ImageDraw.Draw(img)

        # 상단 라인
        ac = tuple(int(c*fade) for c in pal['accent'])
        d.rectangle([0, 0, W, 2], fill=ac)

        # 십자가 (미니멀)
        cross(d, 60, ac)

        # 텍스트
        for item in scene['items']:
            text = item['text']
            if not text: continue
            y = item['y']
            color = tuple(int(c*fade) for c in item['color'])
            font = item['font']

            # 슬라이드업 효과
            y_offset = int((1 - min(1, fp * 2.5)) * 20)
            ctr(d, y + y_offset, text, font, color, 20)

        # 하단 진행바
        tp = (elapsed + dur*fp) / total_dur
        bar_w = int(W * tp)
        d.rectangle([0, H-4, bar_w, H], fill=ac)

        # 하단 점
        dots(d, H-60, ac)

        img.save(os.path.join(FRAMES, f"f_{fn:05d}.png"))
        fn += 1

print(f"  {fn} frames ({total_dur}s)")

# BGM 선택 (랜덤)
bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
bgm = os.path.join(BGM_DIR, random.choice(bgm_files))
print(f"  BGM: {os.path.basename(bgm)}")

# ffmpeg 합성
vpath = os.path.join(OUT, f"premium_{DATE_STR}.mp4")
subprocess.run([FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f_%05d.png"),
                "-i", bgm, "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-filter_complex", f"[1:a]afade=t=in:d=2,afade=t=out:st={total_dur-3}:d=3,volume=0.2[a]",
                "-map", "0:v", "-map", "[a]",
                "-vf", f"scale={W}:{H},fps=30", "-t", str(total_dur), "-shortest", vpath],
               capture_output=True, timeout=120)
shutil.rmtree(FRAMES, ignore_errors=True)

if os.path.exists(vpath):
    sz = os.path.getsize(vpath) / (1024*1024)
    print(f"  Video: {sz:.1f}MB")
else:
    print("  Video FAIL")
    sys.exit(1)

# === 인스타 릴스 업로드 ===
print("\n[3/4] Instagram Reels...")

# Imgur에 영상은 안 올라가므로 썸네일로 이미지 게시
# 썸네일 (1080x1350)
thumb = Image.new('RGB', (1080, 1350), pal['bg'])
grain(thumb, 3)
td = ImageDraw.Draw(thumb)
td.rectangle([0,0,1080,2], fill=pal['accent'])
cross(td, 60, pal['accent'])
ctr(td, 450, content.get('hook', ''), ft(48), pal['text'], 20)
dots(td, 650, pal['accent'])
ctr(td, 700, content.get('closing', content.get('one_liner', '')), ft_l(28), pal['sub'], 12)
ctr(td, 1200, "Lighthouse Media", ft_sb(18), pal['accent'])
ctr(td, 1240, "@lighthouse_media77", ft_s(14), (170,155,135))

thumb_path = os.path.join(OUT, "thumb.jpg")
thumb.save(thumb_path, "JPEG", quality=95)

thumb_url = None
for attempt in range(3):
    try:
        with open(thumb_path, 'rb') as f:
            enc = base64.b64encode(f.read()).decode()
        ir = requests.post('https://api.imgur.com/3/image',
            headers={'Authorization': f'Client-ID {IMGUR_ID}'},
            data={'image': enc, 'type': 'base64'}, timeout=60)
        thumb_url = ir.json().get('data',{}).get('link')
        if thumb_url:
            print(f"  Imgur OK: {thumb_url}")
            break
        print(f"  Imgur attempt {attempt+1}: {ir.json().get('data',{}).get('error','unknown')}")
    except Exception as e:
        print(f"  Imgur attempt {attempt+1}: {e}")
    time.sleep(10 * (attempt + 1))

if thumb_url:
    # 에세이 형식의 깊이 있는 캡션 조립
    caption = clean_surrogates(content.get('caption', ''))
    if not caption or len(caption) < 100:
        caption = clean_surrogates(
            f"\"{content.get('hook_quote', content.get('hook', ''))}\"\n\n"
            f"{content.get('body_empathy', '')}\n\n"
            f"{content.get('body_insight', '')}\n\n"
            f"{content.get('body_depth', '')}\n\n"
            f"{content.get('body_action', '')}\n\n"
            f"\u2726 \uc624\ub298\uc758 \ud55c\ub9c8\ub514\n"
            f"\"{content.get('one_liner', content.get('closing', ''))}\"\n\n"
            f"\u2726 \uc624\ub298\uc758 \uc2e4\ucc9c\n"
            f"{content.get('daily_practice', '')}\n\n"
            f"\u2014\nLighthouse Media\n"
            f"@lighthouse_media77\n\n"
            f"{content.get('hashtags_kr', '#\ud790\ub9c1 #\uc790\uae30\uacc4\ubc1c #\ubc88\uc544\uc6c3 #\uc9c1\uc7a5\uc778 #\ub9c8\uc74c\uad00\ub9ac')}\n"
            f"{content.get('hashtags_en', '#LighthouseMedia #SelfCare #Motivation #Healing')}"
        )
    ig_ok = False
    for attempt in range(3):
        try:
            r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
                'image_url': thumb_url, 'caption': caption, 'access_token': IG_TOKEN
            }, timeout=30)
            if 'id' in r.json():
                time.sleep(8)
                r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={
                    'creation_id': r.json()['id'], 'access_token': IG_TOKEN
                }, timeout=30)
                print(f"  IG: {'OK' if 'id' in r2.json() else r2.json()}")
                ig_ok = True
                break
            else:
                err_code = r.json().get('error',{}).get('code', 0)
                err_msg = r.json().get('error',{}).get('message', r.json())
                print(f"  IG attempt {attempt+1}: {err_msg}")
                if err_code == 4:  # rate limit
                    wait = 120 * (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                break
        except Exception as e:
            print(f"  IG error: {e}")
            break
    if not ig_ok:
        print("  IG: SKIP (rate limited)")
else:
    print("  Imgur failed after 3 attempts")

# === 페이스북 ===
print("\n[4/4] Facebook...")

# 페이스북 메시지 조립
fb_desc = clean_surrogates(
    f"\"{content.get('hook_quote', content.get('hook', ''))}\"\n\n"
    f"{content.get('body_empathy', '')}\n\n"
    f"{content.get('body_insight', '')}\n\n"
    f"{content.get('body_depth', '')}\n\n"
    f"{content.get('body_action', '')}\n\n"
    f"\u2726 {content.get('one_liner', content.get('closing', ''))}\n\n"
    f"\u2014\nLighthouse Media | @lighthouse_media77"
)
# 영상 업로드
with open(vpath, 'rb') as f:
    fb = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/videos',
        files={'source': (os.path.basename(vpath), f, 'video/mp4')},
        data={'description': fb_desc[:500], 'access_token': FB_TOKEN})
print(f"  FB Video: {'OK' if 'id' in fb.json() else fb.json()}")

print(f"\n{'='*50}")
print(f"  Premium content posted!")
print(f"  {content.get('hook', '')}")
print(f"  Palette: {pal['name']}")
print(f"{'='*50}")
