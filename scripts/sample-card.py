"""샘플 카드 2장: 표지 + 질문"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, re, random, math
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

W, H = 1080, 1350
OUT = os.path.join(HOME, "lighthouse-media", "output", "bible-final")
os.makedirs(OUT, exist_ok=True)

def ai(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 300, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

def ft(sz):
    for p in ['C:/Windows/Fonts/HANBatangB.ttf','C:/Windows/Fonts/malgunbd.ttf']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def ft_s(sz):
    return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', sz) if os.path.exists('C:/Windows/Fonts/malgun.ttf') else ImageFont.load_default()

def ct(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        if not ln.strip(): y += sp+5; continue
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

print("=== Making Sample Cards ===")

# AI 질문 생성
print("AI question...")
raw = ai("삼하 3:22-39 본문. 다윗이 아브넬의 죽음에 울었고, 요압이 아브넬을 죽였다. 이 본문으로 깊은 묵상 질문 1개만. 2~3줄, 줄당 12자 이하. 텍스트만 출력. JSON 아닌 순수 텍스트로.")
question = raw.strip().strip('"').strip("'")
# 줄당 12자 넘으면 자르기
lines = []
for ln in question.split("\n"):
    while len(ln) > 12:
        lines.append(ln[:12])
        ln = ln[12:]
    if ln.strip(): lines.append(ln.strip())
question = "\n".join(lines[:3])
print(f"  {question}")

# === 카드 1: 표지 ===
print("Card 1: Cover...")
img1 = Image.new('RGB', (W, H), (0, 0, 0))
d1 = ImageDraw.Draw(img1)

# 새벽 하늘 그라디언트
for row in range(H):
    p = row / H
    if p < 0.5:
        r = int(25 + p * 120)
        g = int(20 + p * 90)
        b = int(50 + p * 60)
    else:
        r = int(85 - (p - 0.5) * 60)
        g = int(65 - (p - 0.5) * 50)
        b = int(80 - (p - 0.5) * 80)
    d1.line([(0, row), (W, row)], fill=(r, g, b))

# 수평선 빛
cy = int(H * 0.45)
for i in range(80):
    r = 50 + i * 8
    d1.ellipse([W // 2 - r, cy - r // 3, W // 2 + r, cy + r // 3],
               fill=(255, 220, 160, int(20 * (1 - i / 80))))

# 산
random.seed(777)
peaks = [(0, int(H*0.58))]
x = 0
while x < W + 50:
    x += random.randint(100, 180)
    peaks.append((x, int(H * 0.55 + random.randint(-70, 30))))
for i in range(len(peaks) - 1):
    x1, y1 = peaks[i]
    x2, y2 = peaks[i + 1]
    for xx in range(int(x1), min(int(x2), W)):
        t = (xx - x1) / max(x2 - x1, 1)
        yy = y1 + t * (y2 - y1)
        d1.line([(xx, int(yy)), (xx, H)], fill=(12, 10, 18))

# 별
for _ in range(25):
    sx = random.randint(60, W - 60)
    sy = random.randint(60, int(H * 0.3))
    d1.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(210, 205, 190))

# 텍스처
for _ in range(1500):
    x, y = random.randint(0, W - 1), random.randint(0, H - 1)
    px = img1.getpixel((x, y))
    v = random.randint(-2, 2)
    img1.putpixel((x, y), tuple(max(0, min(255, c + v)) for c in px))

# 프레임
d1.rectangle([40, 40, W - 40, H - 40], outline=(180, 160, 120, 50), width=1)

# 십자가
cx = W // 2
d1.rectangle([cx - 1, 75, cx + 1, 108], fill=(200, 180, 140))
d1.rectangle([cx - 11, 88, cx + 11, 90], fill=(200, 180, 140))

# 날짜
ct(d1, 140, "04/30  목요일", ft_s(16), (175, 165, 145))

# 점
for off in [-15, -5, 0, 5, 15]:
    d1.ellipse([cx + off - 2, 190, cx + off + 2, 194], fill=(175, 155, 115))

# 본문 (크게)
ct(d1, 380, "사무엘하", ft_s(24), (195, 185, 165), 12)
ct(d1, 430, "3:22-39", ft(64), (235, 225, 205), 10)

# 구분선
d1.rectangle([cx - 45, 545, cx + 45, 546], fill=(175, 155, 115))

# 제목 (크게)
ct(d1, 590, "다윗이 울었다", ft(44), (225, 215, 195), 22)
ct(d1, 660, "요압이 죽였다", ft(44), (225, 215, 195))

# 하단
d1.rectangle([cx - 18, H - 82, cx + 18, H - 80], fill=(110, 100, 78))
ct(d1, H - 68, "동산감리교회", ft_s(13), (135, 125, 105))

img1.save(os.path.join(OUT, "sample_cover.jpg"), "JPEG", quality=95)
print("  OK!")

# === 카드 2: 질문 ===
print("Card 2: Question...")
img2 = Image.new('RGB', (W, H), (248, 245, 237))
d2 = ImageDraw.Draw(img2)

# 따뜻한 크림 그라디언트 + 빛
for row in range(H):
    p = row / H
    r = int(250 - p * 8 + math.sin(p * 3.14) * 4)
    g = int(246 - p * 10 + math.sin(p * 3.14) * 3)
    b = int(236 - p * 14)
    d2.line([(0, row), (W, row)], fill=(r, g, b))

# 부드러운 빛
for i in range(40):
    r = 100 + i * 7
    d2.ellipse([W - 180 - r, -60 - r // 2, W - 180 + r, -60 + r // 2],
               fill=(255, 250, 240, int(5 * (1 - i / 40))))

# 텍스처
random.seed(999)
for _ in range(2500):
    x, y = random.randint(0, W - 1), random.randint(0, H - 1)
    px = img2.getpixel((x, y))
    v = random.randint(-3, 3)
    img2.putpixel((x, y), tuple(max(0, min(255, c + v)) for c in px))

# 프레임
d2.rectangle([40, 40, W - 40, H - 40], outline=(210, 200, 180), width=1)
for ccx, ccy in [(40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)]:
    d2.line([(ccx - 8, ccy), (ccx + 8, ccy)], fill=(210, 200, 180))
    d2.line([(ccx, ccy - 8), (ccx, ccy + 8)], fill=(210, 200, 180))

# 구절
ct(d2, 200, "삼하 3:22-39", ft_s(16), (180, 165, 140))

# 점
for off in [-15, -5, 0, 5, 15]:
    d2.ellipse([cx + off - 2, 250, cx + off + 2, 254], fill=(200, 185, 155))

# 질문 (크게! 46pt)
y = 430
for ln in question.split("\n"):
    if not ln.strip():
        y += 20
        continue
    bb = d2.textbbox((0, 0), ln, font=ft(46))
    # 그림자
    d2.text(((W - (bb[2] - bb[0])) / 2 + 1, y + 1), ln, font=ft(46), fill=(238, 235, 225))
    d2.text(((W - (bb[2] - bb[0])) / 2, y), ln, font=ft(46), fill=(48, 38, 28))
    y += bb[3] - bb[1] + 28

# 하단
d2.rectangle([cx - 18, H - 82, cx + 18, H - 80], fill=(200, 185, 155))
ct(d2, H - 68, "동산감리교회", ft_s(13), (165, 155, 135))

img2.save(os.path.join(OUT, "sample_question.jpg"), "JPEG", quality=95)
print("  OK!")

print("\n=== Done! ===")
print(f"  {OUT}/sample_cover.jpg")
print(f"  {OUT}/sample_question.jpg")
print("  파일 탐색기에서 확인해주세요.")
