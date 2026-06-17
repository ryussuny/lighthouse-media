"""세련된 전자책 홍보 카드뉴스 8장 → Instagram 캐러셀 + Facebook"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens.get("instagram","")
FB_TOKEN = tokens.get("facebook_page","")
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
OUT = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", "premium")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1350
DARK = (10, 12, 24)
MAIN = (29, 158, 117)
ACCENT = (186, 117, 23)

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(draw, y, text, font, fill, sp=0):
    bb = draw.textbbox((0,0), text, font=font)
    draw.text(((W-(bb[2]-bb[0]))/2, y), text, font=font, fill=fill)
    return y + bb[3]-bb[1] + sp

def make_slide(lines, color=MAIN, badge="", num="", page=""):
    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    for i in range(H):
        r = int(10 + (i/H)*6); g = int(12 + (i/H)*8); b = int(24 + (i/H)*10)
        d.line([(0,i),(W,i)], fill=(r,g,b))
    d.ellipse([W-200,-60,W+60,200], fill=(16,18,34))
    d.ellipse([-80,H-200,140,H+20], fill=(16,18,34))
    d.rectangle([0,0,W,3], fill=color)
    d.text((60,55), "LIGHTHOUSE MEDIA", font=gf(18), fill=color)
    if badge:
        bw = len(badge)*11+24
        d.rounded_rectangle([W-bw-50,50,W-50,80], radius=12, fill=color)
        d.text((W-bw-38,55), badge, font=gf(16,True), fill=(255,255,255))
    if num:
        d.text((60,140), num, font=gf(120,True), fill=(color[0]//10,color[1]//10,color[2]//10))
    y = 280
    for item in lines:
        ftype, text = item
        if ftype == "big":
            y = tc(d, y, text, gf(52,True), (255,255,255), 24)
        elif ftype == "title":
            y = tc(d, y, text, gf(44,True), (255,255,255), 18)
        elif ftype == "body":
            y = tc(d, y, text, gf(24), (170,175,190), 16)
        elif ftype == "accent":
            y = tc(d, y, text, gf(26,True), color, 20)
        elif ftype == "sub":
            y = tc(d, y, text, gf(22), (130,135,150), 14)
        elif ftype == "line":
            y += 15
            d.rectangle([W//2-50,y,W//2+50,y+2], fill=color)
            y += 25
        elif ftype == "space":
            y += 20
        elif ftype == "card":
            idx, txt = text.split("|",1)
            d.rounded_rectangle([80,y,W-80,y+80], radius=12, fill=(40,44,65))
            d.rounded_rectangle([100,y+18,138,y+56], radius=8, fill=color)
            d.text((110,y+22), idx.strip(), font=gf(22,True), fill=(255,255,255))
            d.text((158,y+25), txt.strip(), font=gf(22,True), fill=(255,255,255))
            y += 98
        elif ftype == "cta_btn":
            d.rounded_rectangle([180,y,W-180,y+56], radius=14, fill=color)
            tc(d, y+10, text, gf(22,True), (255,255,255))
            y += 76
    d.rectangle([W//2-30,H-90,W//2+30,H-87], fill=color)
    if page:
        d.text((W-80,H-70), page, font=gf(14), fill=(50,52,68))
    return img

print("=" * 50)
print("  Premium Cards")
print("=" * 50)

slides_data = [
    # 1. 표지
    (MAIN, "FREE EBOOK", "", "1/8", [
        ("space",""), ("space",""),
        ("big", "하루 7분이면"),
        ("big", "번아웃 탈출"),
        ("big", "가능합니다"),
        ("line",""),
        ("sub", "직장인 74%가 겪는 만성 피로"),
        ("sub", "과학적으로 검증된 회복 루틴"),
        ("space",""),
        ("sub", "무료 전자책 | Lighthouse Media"),
    ]),
    # 2. 문제
    (MAIN, "", "01", "2/8", [
        ("title", "직장인 74%가"),
        ("title", "만성 피로를 겪습니다"),
        ("line",""),
        ("body", "매일 아침 알람이 울리면"),
        ("body", "한숨부터 나옵니다"),
        ("space",""),
        ("accent", "당신만 그런 게 아닙니다"),
        ("space",""),
        ("body", "현대인의 뇌는 하루 평균"),
        ("body", "35,000번의 결정을 내립니다"),
        ("space",""),
        ("body", "지치는 건 당연합니다"),
    ]),
    # 3. 해결
    (MAIN, "", "02", "3/8", [
        ("title", "하지만 7분이면"),
        ("title", "달라집니다"),
        ("line",""),
        ("body", "스탠퍼드 대학 연구 결과:"),
        ("space",""),
        ("accent", "3분 호흡 = 코르티솔 23% 감소"),
        ("accent", "2분 감사 = 옥시토신 분비 증가"),
        ("accent", "2분 목표 = 도파민 활성화"),
        ("space",""),
        ("body", "매일 7분 투자로"),
        ("body", "뇌의 기본 설정이 바뀝니다"),
    ]),
    # 4. 루틴
    (MAIN, "", "03", "4/8", [
        ("title", "아침 7분 루틴"),
        ("line",""),
        ("card", "1 | 깊은 호흡 2분 (4-7-8 호흡법)"),
        ("card", "2 | 감사한 것 3가지 적기 (2분)"),
        ("card", "3 | 오늘의 목표 1개 설정 (2분)"),
        ("card", "4 | 몸 깨우기 스트레칭 (1분)"),
        ("space",""),
        ("sub", "총 7분 | 장소 무관 | 도구 불필요"),
    ]),
    # 5. 변화
    (MAIN, "", "04", "5/8", [
        ("title", "2주면 변화가"),
        ("title", "시작됩니다"),
        ("line",""),
        ("accent", "1주차:"),
        ("body", "아침이 조금 덜 힘들어집니다"),
        ("space",""),
        ("accent", "2주차:"),
        ("body", "습관이 자리잡기 시작합니다"),
        ("space",""),
        ("accent", "4주차:"),
        ("body", "주변에서 달라졌다고 합니다"),
        ("space",""),
        ("accent", "시작이 반입니다"),
    ]),
    # 6. 체크리스트
    (MAIN, "", "05", "6/8", [
        ("title", "7일 실천 체크리스트"),
        ("line",""),
        ("body", "Day 1:  호흡만 해보기"),
        ("body", "Day 2:  호흡 + 감사"),
        ("body", "Day 3:  전체 루틴 1회"),
        ("body", "Day 4:  2회 반복"),
        ("body", "Day 5:  자동으로!"),
        ("body", "Day 6:  변화 느끼기"),
        ("body", "Day 7:  습관 완성"),
        ("space",""),
        ("accent", "무료 전자책에 상세 가이드 포함"),
    ]),
    # 7. 유료
    (ACCENT, "7,900원", "", "7/8", [
        ("space",""),
        ("title", "더 깊은 회복이"),
        ("title", "필요하다면"),
        ("line",""),
        ("accent", "유료 전자책 안내"),
        ("space",""),
        ("body", "번아웃에서 벗어나는 힘"),
        ("body", "8챕터 + 30일 워크시트"),
        ("space",""),
        ("body", "에너지 설계법"),
        ("body", "감정 관리 기술"),
        ("body", "지속가능한 루틴 구축"),
    ]),
    # 8. CTA
    (MAIN, "", "", "8/8", [
        ("space",""), ("space",""),
        ("title", "무료 전자책"),
        ("title", "받는 방법"),
        ("line",""),
        ("cta_btn", "3단계만 하면 됩니다"),
        ("space",""),
        ("body", "1. @lighthouse_media77 팔로우"),
        ("space",""),
        ("body", "2. 이 게시물에 좋아요"),
        ("space",""),
        ("body", "3. DM으로 '전자책' 보내기"),
        ("space",""),
        ("accent", "즉시 전송해드립니다!"),
    ]),
]

img_urls = []
for i, (color, badge, num, page, lines) in enumerate(slides_data):
    img = make_slide(lines, color, badge, num, page)
    path = os.path.join(OUT, f"p_{i+1:02d}.jpg")
    img.save(path, "JPEG", quality=95)

    with open(path, 'rb') as f:
        d = base64.b64encode(f.read()).decode()
    r = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': d, 'type': 'base64'})
    url = r.json().get('data',{}).get('link')
    if url: img_urls.append(url)
    print(f"  Slide {i+1}/8: {'OK' if url else 'FAIL'}")
    time.sleep(1)

# Post carousel
print(f"\n  Posting carousel...")
ids = []
for url in img_urls:
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url': url, 'is_carousel_item': 'true', 'access_token': IG_TOKEN})
    d = r.json()
    if 'id' in d: ids.append(d['id'])
    time.sleep(2)

caption = "하루 7분이면 번아웃 탈출 가능합니다.\n\n직장인 74%가 만성 피로를 겪고 있습니다.\n하지만 매일 7분만 투자하면 달라집니다.\n\n아침 7분 루틴:\n  2분  깊은 호흡\n  2분  감사 일기\n  2분  목표 설정\n  1분  스트레칭\n\n2주면 변화가 시작됩니다.\n\n무료 전자책 받기:\n1. @lighthouse_media77 팔로우\n2. 이 게시물 좋아요\n3. DM으로 '전자책'\n\nLighthouse Media\n\n#번아웃회복 #자기계발 #직장인힐링 #마음관리 #아침루틴 #7분루틴 #무료전자책 #라이트하우스미디어 #직장인루틴 #에너지관리 #워라밸 #습관형성 #멘탈관리 #힐링 #자기관리"

if len(ids) >= 2:
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'media_type': 'CAROUSEL', 'children': ','.join(ids), 'caption': caption, 'access_token': IG_TOKEN})
    c = r.json()
    if 'id' in c:
        time.sleep(8)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id': c['id'], 'access_token': IG_TOKEN})
        print(f"  IG: OK {r2.json().get('id','')}")
    else:
        print(f"  IG: {c}")

# FB
if img_urls:
    fm = "하루 7분이면 번아웃 탈출 가능합니다.\n\n2주면 변화가 시작됩니다.\n무료 전자책도 준비되어 있습니다.\n\nLighthouse Media"
    r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url': img_urls[0], 'message': fm, 'access_token': FB_TOKEN})
    print(f"  FB: {'OK' if 'id' in r.json() else r.json()}")

print(f"\n{'='*50}")
print("  Done! Check @lighthouse_media77")
print(f"{'='*50}")
