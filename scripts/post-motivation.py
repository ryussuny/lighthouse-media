"""동기부여 숏츠 썸네일 → 인스타/페이스북 게시"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

W, H = 1080, 1350

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size):
    p = "C:/Windows/Fonts/timesbd.ttf"
    if not os.path.exists(p): p = "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0,0), ln, font=font)
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=font, fill=fill)
        y += bb[3]-bb[1] + sp
    return y

def make_quote_card(quote_en, quote_kr, source, style_color, bg_style):
    img = Image.new("RGB", (W, H), (0,0,0))
    d = ImageDraw.Draw(img)

    if bg_style == "dawn":
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(int(10+p*35), int(15+p*25), int(35+p*40)))
    elif bg_style == "night":
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(int(5+p*3), int(5+p*5), int(15+p*10)))
        import random; random.seed(42)
        for _ in range(60):
            x, y2 = random.randint(0,W), random.randint(0,H//2)
            d.ellipse([x-1,y2-1,x+1,y2+1], fill=(200,200,200))
    elif bg_style == "golden":
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(int(25+p*30), int(15+p*18), int(5+p*8)))
    else:
        for row in range(H):
            p = row / H
            d.line([(0,row),(W,row)], fill=(int(8+p*6), int(10+p*8), int(20+p*12)))

    # 레터박스
    d.rectangle([0,0,W,60], fill=(0,0,0))
    d.rectangle([0,H-60,W,H], fill=(0,0,0))

    # 브랜드
    d.text((60,80), "LIGHTHOUSE MEDIA", font=gf(16), fill=(*style_color, 120))

    # 영어 명언
    if quote_en:
        tc(d, 300, quote_en, gf_en(24), (140,140,150), 6)

    # 구분선
    d.rectangle([W//2-60, 480, W//2+60, 482], fill=style_color)

    # 한글 명언
    tc(d, 530, quote_kr, gf(44, True), (255,255,255), 20)

    # 출처
    if source:
        tc(d, 900, source, gf(22), (*style_color, 180))

    # 하단
    d.rectangle([W//2-30, H-130, W//2+30, H-127], fill=style_color)
    tc(d, H-110, "@lighthouse_media77", gf(14), (60,60,70))

    return img

print("=" * 50)
print("  Motivation Quote Cards → IG + FB")
print("=" * 50)

quotes = [
    {
        "en": "\"The only way to do great work\nis to love what you do.\"",
        "kr": "위대한 일을 하는\n유일한 방법은\n하는 일을 사랑하는 것이다",
        "src": "- Steve Jobs",
        "color": (52,152,219), "bg": "dawn",
        "cap": "위대한 일을 하는 유일한 방법은\n하는 일을 사랑하는 것이다.\n\n\"The only way to do great work\nis to love what you do.\"\n- Steve Jobs\n\n오늘 하는 일에서 작은 즐거움을 찾아보세요.\n\n#명언 #스티브잡스 #동기부여 #자기계발 #도전 #성장 #직장인 #영감 #위로 #힐링 #인생명언 #세계명언 #라이트하우스미디어 #마음관리 #워라밸"
    },
    {
        "en": "\"Fall seven times,\nstand up eight.\"",
        "kr": "일곱 번 넘어져도\n여덟 번째 일어서라",
        "src": "- Japanese Proverb",
        "color": (29,158,117), "bg": "mountain",
        "cap": "일곱 번 넘어져도 여덟 번째 일어서라.\n\n\"Fall seven times, stand up eight.\"\n- Japanese Proverb\n\n포기하고 싶은 순간이\n성장 직전의 순간입니다.\n\n#명언 #도전 #포기하지마 #동기부여 #자기계발 #성장 #직장인 #힐링 #용기 #일본속담 #인생명언 #세계명언 #라이트하우스미디어 #마음관리 #파이팅"
    },
    {
        "en": "\"Stars can't shine\nwithout darkness.\"",
        "kr": "어둠이 없으면\n별은 빛날 수 없습니다",
        "src": "",
        "color": (155,89,182), "bg": "night",
        "cap": "어둠이 없으면 별은 빛날 수 없습니다.\n\n\"Stars can't shine without darkness.\"\n\n지금 힘든 시간을 보내고 있다면\n그건 당신이 빛나기 위한 과정입니다.\n\n이 글이 필요한 사람에게 보내주세요.\n\n#위로 #힐링 #명언 #별 #어둠 #동기부여 #자기계발 #공감 #응원 #마음관리 #인생명언 #세계명언 #라이트하우스미디어 #직장인 #희망"
    },
    {
        "en": "\"This too shall pass.\"",
        "kr": "이것 또한\n지나가리라",
        "src": "- Persian Proverb",
        "color": (186,117,23), "bg": "golden",
        "cap": "이것 또한 지나가리라.\n\n\"This too shall pass.\"\n- Persian Proverb\n\n좋은 것도, 나쁜 것도\n모두 지나갑니다.\n\n지금 이 순간을 견디고 있는\n당신에게 전합니다.\n\n#이것또한지나가리라 #명언 #위로 #힐링 #동기부여 #페르시아속담 #인생 #자기계발 #공감 #마음관리 #인생명언 #세계명언 #라이트하우스미디어 #직장인 #희망"
    },
    {
        "en": "\"Believe you can\nand you're halfway there.\"",
        "kr": "할 수 있다고 믿으면\n이미 반은 온 것입니다",
        "src": "- Theodore Roosevelt",
        "color": (29,158,117), "bg": "dawn",
        "cap": "할 수 있다고 믿으면 이미 반은 온 것입니다.\n\n\"Believe you can and you're halfway there.\"\n- Theodore Roosevelt\n\n오늘도 자신을 믿어주세요.\n\n#명언 #루즈벨트 #동기부여 #자기계발 #도전 #성장 #직장인 #믿음 #자신감 #힐링 #인생명언 #세계명언 #라이트하우스미디어 #마음관리 #파이팅"
    },
]

for i, q in enumerate(quotes):
    print(f"\n[{i+1}/5] {q['kr'].split(chr(10))[0]}")
    img = make_quote_card(q['en'], q['kr'], q['src'], q['color'], q['bg'])

    path = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", f"quote_{i+1}.jpg")
    img.save(path, "JPEG", quality=95)

    with open(path, 'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': enc, 'type': 'base64'})
    url = ir.json().get('data',{}).get('link')
    if not url: print("  Imgur FAIL"); continue
    time.sleep(3)

    # IG
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url': url, 'caption': q['cap'], 'access_token': IG_TOKEN})
    ig = False
    if 'id' in r.json():
        time.sleep(5)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id': r.json()['id'], 'access_token': IG_TOKEN})
        ig = 'id' in r2.json()

    # FB
    fb = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url': url, 'message': q['cap'][:500], 'access_token': FB_TOKEN})

    print(f"  IG:{'OK' if ig else 'X'} FB:{'OK' if 'id' in fb.json() else 'X'}")
    time.sleep(3)

print(f"\n{'='*50}")
print("  Done! 5 cinematic quote cards posted")
print(f"{'='*50}")
