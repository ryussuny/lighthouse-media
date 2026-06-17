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

# 다양한 깊이 있는 주제 풀 (매일 다른 주제)
import hashlib
deep_themes = [
    "번아웃 뒤에 남는 것 — 소진이 가르쳐주는 진짜 우선순위",
    "불안은 나쁜 감정이 아니다 — 불안과 친구 되는 법",
    "완벽주의의 진짜 이름은 두려움이다",
    "혼자인 시간의 힘 — 고독과 외로움의 차이",
    "비교가 멈추는 순간 — 나만의 타임라인으로 사는 법",
    "실패 후 일어서는 데 필요한 건 용기가 아니라 친절",
    "경계를 세우는 것은 이기적이 아니라 건강한 것이다",
    "감사는 감정이 아니라 연습이다 — 뇌가 바뀌는 감사의 과학",
    "말하지 못한 감정이 몸에 저장될 때",
    "작은 습관이 인생을 바꾸는 과학적 이유",
    "용서는 상대를 위한 것이 아니라 나를 자유롭게 하는 것",
    "관계에서 상처받는 패턴을 알아차리는 법",
    "꿈을 미루는 진짜 이유와 오늘 시작하는 한 걸음",
    "분노 뒤에 숨은 진짜 감정 찾기",
    "나이 듦이 가르쳐주는 것들 — 시간의 지혜",
    "돈보다 중요한 진짜 부 — 시간과 관계의 경제학",
    "리더십은 직함이 아니라 영향력이다",
    "창의성은 재능이 아니라 용기의 문제",
    "디지털 시대의 진짜 연결 — 깊은 대화의 기술",
    "슬픔을 충분히 슬퍼하는 것의 치유력",
    "성장통이 필요한 이유 — 불편함이 성장의 신호",
    "인생 후반전을 위한 마인드셋 리셋",
    "매일 같은 일상이 지루할 때 — 일상의 재발견",
    "자기 자신에게 하는 말이 인생을 결정한다",
    "느린 것이 빠른 것이다 — 조급함을 내려놓는 지혜",
    "취약함을 보여주는 용기가 진짜 강함이다",
    "목적 없는 바쁨에서 벗어나는 법",
    "사랑은 감정이 아니라 매일의 선택이다",
    "과거의 나와 화해하는 법",
    "지금 이 순간이 전부라는 것의 깊은 의미",
]
day_hash = int(hashlib.md5(DATE_STR.encode()).hexdigest()[:8], 16)
today_theme = deep_themes[day_hash % len(deep_themes)]

content_raw = claude(
    f"당신은 Lighthouse Media의 수석 콘텐츠 디렉터입니다.\n"
    f"오늘 날짜: {DATE_STR}\n"
    f"오늘의 깊이 있는 주제: {today_theme}\n\n"
    "=== 콘텐츠 철학 ===\n"
    "Lighthouse Media는 하루에 단 1개의 게시물만 올립니다.\n"
    "그래서 이 1개가 오늘 하루를 살아가는 사람들의 마음에 진짜 닿아야 합니다.\n"
    "피상적인 동기부여가 아닌, 삶의 깊은 곳을 건드리는 글을 씁니다.\n\n"
    "=== 타겟 ===\n"
    "25-45세 직장인, 부모, 사업가 — 바쁜 일상 속에서 잠깐 멈추고 생각하고 싶은 사람들\n\n"
    "=== 톤 ===\n"
    "- 따뜻하지만 지적인 깊이가 있는 글 (에세이 수준)\n"
    "- 과장/선동/클릭베이트 절대 금지\n"
    "- 종교적 표현 없이 보편적 지혜로 (기독교 가치관은 녹아있되 드러나지 않게)\n"
    "- 읽는 사람이 '이건 나 얘기다'라고 느끼게\n"
    "- 구체적인 심리학/신경과학/철학 근거를 자연스럽게 녹여서\n\n"
    "=== 글쓰기 원칙 ===\n"
    "1. 첫 문장에서 공감을 잡아라 (구체적 상황 묘사)\n"
    "2. 문제의 본질을 짚어라 (표면이 아닌 뿌리)\n"
    "3. 새로운 관점을 제시하라 (아, 이렇게도 볼 수 있구나)\n"
    "4. 실천 가능한 한 가지를 남겨라 (오늘 당장 할 수 있는 것)\n\n"
    "JSON으로 출력:\n"
    '{"topic": "주제 카테고리 (번아웃/감정/습관/에너지/관계/성장/자아/회복 중 택1)",\n'
    ' "hook": "첫 장면 — 공감가는 상황 묘사 한 문장 (15자 이내)",\n'
    ' "hook_quote": "핵심 인용구 — 에세이의 한 줄 요약 (깊이 있게)",\n'
    ' "scenes": [\n'
    '   {"text": "장면 핵심 (10자 이내)", "sub": "부연 설명 (20자 이내, 깊이 있게)"},\n'
    '   ... (6~8장면 — 기승전결 구조로)\n'
    ' ],\n'
    ' "closing": "마무리 — 여운이 남는 한 문장",\n'
    ' "one_liner": "오늘의 한마디 — 기억에 새겨질 한 줄",\n'
    ' "daily_practice": "오늘의 실천 — 구체적이고 즉시 실행 가능한 2문장",\n'
    ' "body_empathy": "공감 문단 — 구체적 상황을 그림처럼 묘사 (3-4문장, 읽는 사람이 고개를 끄덕이게)",\n'
    ' "body_insight": "인사이트 문단 — 심리학/철학/신경과학 근거를 자연스럽게 녹인 새로운 관점 (3-4문장)",\n'
    ' "body_action": "실천 문단 — 오늘 당장 할 수 있는 구체적 행동과 그 효과 (3-4문장)",\n'
    ' "body_depth": "깊이 문단 — 이 주제에 대한 한 층 더 깊은 통찰, 역설이나 반전이 있으면 좋음 (2-3문장)",\n'
    ' "hashtags_kr": "#힐링 #자기계발 #번아웃 #직장인 #마음관리 #위로 #공감 #멘탈케어 #일상 #하루 #에세이 #깊은생각",\n'
    ' "hashtags_en": "#LighthouseMedia #SelfCare #Motivation #Healing #Mindfulness #DeepThoughts #InnerPeace",\n'
    ' "caption": "인스타 캡션 — 에세이 형식으로 작성 (hook_quote → body_empathy → body_insight → body_depth → body_action → one_liner → daily_practice 순서로 자연스럽게)"}\n\n'
    "규칙:\n"
    "- 한 장면에 텍스트 최대 10자 (크게 보이도록)\n"
    "- 피상적 위로 금지 — 진짜 깊이 있는 메시지\n"
    "- 과장/선동 금지\n"
    "- 구체적이고 실제 삶에 와닿는 내용\n"
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
if not content['scenes']:
    content['scenes'] = [{"text": content['hook'], "sub": content.get('one_liner','')}]

print(f"  Topic: {content['topic']}")
print(f"  Hook: {content['hook']}")

# 콘텐츠 JSON 저장 (확인용)
with open(os.path.join(OUT, "content.json"), 'w', encoding='utf-8') as f:
    json.dump(content, f, ensure_ascii=False, indent=2)

# === 릴스 영상 제작 ===
print("\n[2/4] Creating premium video...")

scenes_data = []
# 오프닝
scenes_data.append({"dur": 6, "bg": pal['bg'], "items": [
    {"y": 700, "text": content['hook'], "font": ft(48), "color": pal['text']},
]})

# 본문 장면들
for sc in content['scenes']:
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
ctr(td, 450, content['hook'], ft(48), pal['text'], 20)
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
            f"\"{content.get('hook_quote', content['hook'])}\"\n\n"
            f"{content.get('body_empathy', '')}\n\n"
            f"{content.get('body_insight', '')}\n\n"
            f"{content.get('body_depth', '')}\n\n"
            f"{content.get('body_action', '')}\n\n"
            f"\u2726 \uc624\ub298\uc758 \ud55c\ub9c8\ub514\n"
            f"\"{content.get('one_liner', content['closing'])}\"\n\n"
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
    f"\"{content.get('hook_quote', content['hook'])}\"\n\n"
    f"{content.get('body_empathy', '')}\n\n"
    f"{content.get('body_insight', '')}\n\n"
    f"{content.get('body_depth', '')}\n\n"
    f"{content.get('body_action', '')}\n\n"
    f"\u2726 {content.get('one_liner', content['closing'])}\n\n"
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
print(f"  {content['hook']}")
print(f"  Palette: {pal['name']}")
print(f"{'='*50}")
