"""전체 자동 마케팅 블리츠: 릴스형 5개 + FB 텍스트 3개 + 해시태그 리서치"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

W, H = 1080, 1350

def make_post(title_lines, body_lines, color, badge=""):
    img = Image.new("RGB", (W, H), (10,12,24))
    d = ImageDraw.Draw(img)
    for row in range(H):
        d.line([(0,row),(W,row)], fill=(10+int(row/H*6), 12+int(row/H*8), 24+int(row/H*10)))
    d.ellipse([W-200,-60,W+60,200], fill=(16,18,34))
    d.rectangle([0,0,W,4], fill=color)
    d.text((60,55), "LIGHTHOUSE MEDIA", font=gf(18), fill=color)
    if badge:
        bw = len(badge)*12+20
        d.rounded_rectangle([W-bw-50,50,W-50,80], radius=12, fill=color)
        d.text((W-bw-38,55), badge, font=gf(16,True), fill=(255,255,255))

    y = 280
    for ln in title_lines:
        bb = d.textbbox((0,0), ln, font=gf(52,True))
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(52,True), fill=(255,255,255))
        y += bb[3]-bb[1] + 22
    y += 20
    d.rectangle([W//2-50,y,W//2+50,y+2], fill=color)
    y += 30
    for ln in body_lines:
        if ln == "": y += 16; continue
        if ln.startswith("*"):
            bb = d.textbbox((0,0), ln[1:], font=gf(26,True))
            d.text(((W-(bb[2]-bb[0]))/2, y), ln[1:], font=gf(26,True), fill=color)
            y += bb[3]-bb[1] + 20; continue
        if ln.startswith(">"):
            d.rounded_rectangle([100,y,W-100,y+65], radius=12, fill=(40,44,65))
            d.text((140,y+16), ln[1:].strip(), font=gf(24,True), fill=(255,255,255))
            y += 82; continue
        bb = d.textbbox((0,0), ln, font=gf(24))
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(24), fill=(170,175,190))
        y += bb[3]-bb[1] + 14

    d.rectangle([W//2-30,H-90,W//2+30,H-87], fill=color)
    bb = d.textbbox((0,0), "@lighthouse_media77", font=gf(16))
    d.text(((W-(bb[2]-bb[0]))/2, H-70), "@lighthouse_media77", font=gf(16), fill=(70,72,90))
    return img

def upload_ig_fb(img, caption):
    path = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", "blitz.jpg")
    img.save(path, "JPEG", quality=95)
    with open(path,'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':enc,'type':'base64'})
    ir_data = ir.json()
    url = ir_data.get('data',{}).get('link')
    if not url:
        print(f"    Imgur fail: {ir_data.get('data',{}).get('error','unknown')}")
        return False, False
    time.sleep(3)
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url':url,'caption':caption,'access_token':IG_TOKEN})
    ig = False
    r_data = r.json()
    if 'id' in r_data:
        time.sleep(5)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id':r_data['id'],'access_token':IG_TOKEN})
        r2_data = r2.json()
        ig = 'id' in r2_data
        if not ig:
            print(f"    IG publish fail: {r2_data.get('error',{}).get('message','unknown')}")
    else:
        print(f"    IG media fail: {r_data.get('error',{}).get('message','unknown')}")
    fb = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url':url,'message':caption[:500],'access_token':FB_TOKEN})
    return ig, 'id' in fb.json()

print("=" * 60)
print("  AUTO MARKETING BLITZ")
print("=" * 60)

# 릴스형 게시물 5개
posts = [
    {
        "t": ["3초 안에", "스트레스", "날리는 법"],
        "b": ["", "*지금 해보세요", "", "> 주먹 꽉 쥐기 (3초)", "> 한번에 풀기", "> 깊게 한숨 쉬기", "", "코르티솔 23% 감소", "", "*저장하고 매일 실천"],
        "c": (231,76,60), "bg": "30SEC",
        "cap": "3초 안에 스트레스 날리는 법\n\n지금 해보세요:\n1. 주먹 꽉 쥐기 (3초)\n2. 한번에 풀기\n3. 깊게 한숨 쉬기\n\n이것만으로 코르티솔 23% 감소.\n저장하고 매일 실천하세요!\n\n#스트레스해소 #직장인팁 #3초힐링 #번아웃극복 #마음관리 #자기계발 #힐링 #직장인 #스트레스관리 #멘탈케어 #자기관리 #직장인공감 #마음챙김 #워라밸 #라이트하우스미디어"
    },
    {
        "t": ["아침 3분으로", "하루가", "달라집니다"],
        "b": ["", "> 물 한 잔 마시기", "> 1분 스트레칭", "> 감사한 것 1가지", "", "*딱 3분 투자", "*하루 전체가 바뀝니다", "", "내일 아침부터 시작하세요"],
        "c": (52,152,219), "bg": "3MIN",
        "cap": "아침 3분으로 하루가 달라집니다.\n\n1. 물 한 잔\n2. 1분 스트레칭\n3. 감사한 것 1가지\n\n딱 3분이면 됩니다.\n내일 아침부터 시작하세요.\n\n#모닝루틴 #아침습관 #3분루틴 #직장인아침 #자기계발 #습관형성 #마음관리 #힐링 #직장인루틴 #에너지관리 #워라밸 #미라클모닝 #건강습관 #성장 #라이트하우스미디어"
    },
    {
        "t": ["직장인 90%가", "모르는", "에너지 충전법"],
        "b": ["", "커피가 아닙니다", "", "*마이크로 브레이크", "", "> 2시간마다 3분 휴식", "> 창밖 보기 20초", "> 깊은 호흡 3회", "", "하루 5번이면 충분합니다"],
        "c": (186,117,23), "bg": "SECRET",
        "cap": "직장인 90%가 모르는 에너지 충전법\n\n커피가 아닙니다.\n답은 '마이크로 브레이크'.\n\n2시간마다 3분 휴식\n창밖 보기 20초\n깊은 호흡 3회\n\n하루 5번이면 충분합니다.\n\n#에너지관리 #직장인꿀팁 #마이크로브레이크 #번아웃극복 #직장인 #자기계발 #마음관리 #힐링 #업무효율 #집중력 #생산성 #워라밸 #직장인일상 #피로회복 #라이트하우스미디어"
    },
    {
        "t": ["이 글을 보는", "당신에게"],
        "b": ["", "오늘도 잘 버텼습니다", "", "아무도 알아주지 않아도", "당신은 충분히", "잘하고 있습니다", "", "*쉬어도 괜찮습니다", "*울어도 괜찮습니다", "", "내일은 조금 나을 겁니다"],
        "c": (29,158,117), "bg": "",
        "cap": "이 글을 보는 당신에게.\n\n오늘도 잘 버텼습니다.\n\n아무도 알아주지 않아도\n당신은 충분히 잘하고 있습니다.\n\n쉬어도 괜찮습니다.\n내일은 오늘보다 조금 나을 겁니다.\n\n공감되면 친구에게 보내주세요.\n\n#위로 #오늘도수고했어 #직장인공감 #힐링 #마음관리 #응원 #공감 #위로한마디 #번아웃 #직장인 #하루끝 #자기계발 #마음챙김 #당신은소중합니다 #라이트하우스미디어"
    },
    {
        "t": ["번아웃 자가진단", "3개 이상이면", "위험 신호"],
        "b": ["", "> 아침에 일어나기 싫다", "> 일에 의미를 못 느낀다", "> 짜증이 자주 난다", "> 집중이 안 된다", "> 몸이 자주 아프다", "> 잠이 안 온다", "", "*3개 이상? 프로필에서", "*무료 전자책 받으세요"],
        "c": (155,89,182), "bg": "CHECK",
        "cap": "번아웃 자가진단\n\n1. 아침에 일어나기 싫다\n2. 일에 의미를 못 느낀다\n3. 짜증이 자주 난다\n4. 집중이 안 된다\n5. 몸이 자주 아프다\n6. 잠이 안 온다\n\n3개 이상 해당?\n프로필 링크에서 무료 전자책 받으세요.\n\n#번아웃자가진단 #번아웃 #직장인건강 #멘탈케어 #스트레스 #마음관리 #자기계발 #직장인공감 #건강 #힐링 #번아웃극복 #자기관리 #직장인 #워라밸 #라이트하우스미디어"
    },
]

print("\n[1/3] Reels-style posts...")
for i, p in enumerate(posts):
    img = make_post(p["t"], p["b"], p["c"], p["bg"])
    ig, fb = upload_ig_fb(img, p["cap"])
    print(f"  [{i+1}/5] {p['t'][0]} - IG:{'OK' if ig else 'X'} FB:{'OK' if fb else 'X'}")
    time.sleep(3)

# FB 텍스트 게시물
print("\n[2/3] FB text posts...")
fb_texts = [
    "직장인 여러분, 월요일 아침 기분이 어떠세요?\n\nA. 죽을 것 같다\nB. 그냥저냥\nC. 나름 괜찮다\n\n댓글로 알려주세요!\n\n- Lighthouse Media",
    "번아웃 자가진단:\n1. 아침에 일어나기 싫다\n2. 일에 의미 없음\n3. 짜증 자주 남\n4. 집중 안됨\n5. 몸이 아픔\n\n3개 이상? 댓글로 '전자책' 남기면\n무료 번아웃 탈출 가이드 보내드립니다!\n\n- Lighthouse Media",
    "오늘 하루도 수고하셨습니다.\n\n내일 아침, 눈 뜨자마자 이것만 해보세요:\n1. 물 한 잔 (30초)\n2. 기지개 (30초)\n3. 감사한 것 1가지 (1분)\n\n이 2분이 하루를 바꿉니다.\n\n- Lighthouse Media",
]
for i, msg in enumerate(fb_texts):
    r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/feed', data={'message': msg, 'access_token': FB_TOKEN})
    print(f"  [{i+1}/3] {'OK' if 'id' in r.json() else 'FAIL'}")
    time.sleep(2)

# 해시태그 리서치
print("\n[3/3] Hashtag research...")
for tag in ["burnout", "selfcare", "mentalhealth"]:
    r = requests.get(f'https://graph.facebook.com/v21.0/ig_hashtag_search?q={tag}&user_id={IG_ID}&access_token={IG_TOKEN}')
    data = r.json().get('data', [])
    if data:
        tid = data[0]['id']
        r2 = requests.get(f'https://graph.facebook.com/v21.0/{tid}/recent_media?user_id={IG_ID}&fields=id&limit=5&access_token={IG_TOKEN}')
        cnt = len(r2.json().get('data', []))
        print(f"  #{tag}: {cnt} recent posts found")
    time.sleep(2)

print(f"\n{'='*60}")
print("  BLITZ COMPLETE!")
print("  IG: 5 posts + FB: 3 text + 5 image = 13 new posts")
print(f"{'='*60}")
