"""바이럴 콘텐츠 10개 제작 + 인스타/페이스북 게시"""
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

def make_card(title_lines, body_lines, color, style="dark", badge=""):
    if style == "warm":
        bg = (250, 248, 243)
        text_color = (42, 42, 42)
        sub_color = (120, 120, 120)
    else:
        bg = (10, 12, 24)
        text_color = (255, 255, 255)
        sub_color = (170, 175, 190)

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    if style == "dark":
        for row in range(H):
            d.line([(0,row),(W,row)], fill=(10+int(row/H*6), 12+int(row/H*8), 24+int(row/H*10)))
        d.ellipse([W-200,-60,W+60,200], fill=(16,18,34))
    elif style == "warm":
        d.ellipse([W-150,-50,W+50,150], fill=(245,240,230))
        d.ellipse([-80,H-150,120,H+30], fill=(245,240,230))

    d.rectangle([0,0,W,4], fill=color)
    brand_c = color if style == "dark" else (150,150,150)
    d.text((60,55), "LIGHTHOUSE MEDIA", font=gf(18), fill=brand_c)

    if badge:
        bw = len(badge)*12+24
        d.rounded_rectangle([W-bw-50,50,W-50,80], radius=12, fill=color)
        d.text((W-bw-38,55), badge, font=gf(16,True), fill=(255,255,255) if style=="dark" else (255,255,255))

    y = 280
    for ln in title_lines:
        bb = d.textbbox((0,0), ln, font=gf(52,True))
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(52,True), fill=text_color)
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
            txt = ln[1:].strip()
            if style == "dark":
                d.rounded_rectangle([100,y,W-100,y+65], radius=12, fill=(40,44,65))
            else:
                d.rounded_rectangle([100,y,W-100,y+65], radius=12, fill=(235,232,225))
            d.text((140,y+16), txt, font=gf(24,True), fill=text_color)
            y += 82; continue
        if ln.startswith("#"):
            # 숫자 강조
            bb = d.textbbox((0,0), ln[1:], font=gf(80,True))
            d.text(((W-(bb[2]-bb[0]))/2, y), ln[1:], font=gf(80,True), fill=color)
            y += bb[3]-bb[1] + 20; continue
        bb = d.textbbox((0,0), ln, font=gf(24))
        d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(24), fill=sub_color)
        y += bb[3]-bb[1] + 14

    d.rectangle([W//2-30,H-90,W//2+30,H-87], fill=color)
    bb = d.textbbox((0,0), "@lighthouse_media77", font=gf(16))
    footer_c = (70,72,90) if style=="dark" else (180,180,180)
    d.text(((W-(bb[2]-bb[0]))/2, H-70), "@lighthouse_media77", font=gf(16), fill=footer_c)
    return img

def upload_post(img, caption):
    path = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", "viral.jpg")
    img.save(path, "JPEG", quality=95)
    with open(path,'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':enc,'type':'base64'})
    url = ir.json().get('data',{}).get('link')
    if not url: return False, False
    time.sleep(3)

    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url':url,'caption':caption,'access_token':IG_TOKEN})
    ig = False
    if 'id' in r.json():
        time.sleep(5)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id':r.json()['id'],'access_token':IG_TOKEN})
        ig = 'id' in r2.json()

    fb = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url':url,'message':caption[:500],'access_token':FB_TOKEN})
    return ig, 'id' in fb.json()

print("=" * 60)
print("  VIRAL CONTENT FACTORY")
print("=" * 60)

viral_posts = [
    # 1. 공감 폭발형
    {
        "t": ["월요일만 되면", "토할 것 같은", "사람 손"],
        "b": ["", "#87%", "", "한국 직장인이", "월요병을 겪고 있습니다", "", "당신만 그런 게 아닙니다", "", "*공감되면 손 이모지 댓글!", "*친구 태그해주세요"],
        "c": (231,76,60), "s": "dark", "bg": "REAL TALK",
        "cap": "월요일만 되면 토할 것 같은 사람 손\n\n한국 직장인 87%가 월요병을 겪고 있습니다.\n당신만 그런 게 아닙니다.\n\n공감되면 손 이모지 댓글로!\n이런 친구 있으면 태그해주세요.\n\n#월요병 #직장인공감 #번아웃 #직장인일상 #공감 #월요일 #직장인 #힐링 #위로 #마음관리 #자기계발 #직장인공감글 #현실 #퇴근하고싶다 #라이트하우스미디어"
    },
    # 2. 위로형 (따뜻한 배경)
    {
        "t": ["오늘도", "버텨낸 너에게"],
        "b": ["", "잘했어", "", "아무도 몰라도", "네가 얼마나 애쓰고 있는지", "나는 알아", "", "오늘 하루", "정말 수고했어", "", "*이 글이 필요한 친구에게", "*보내주세요"],
        "c": (29,158,117), "s": "warm", "bg": "",
        "cap": "오늘도 버텨낸 너에게.\n\n잘했어.\n\n아무도 몰라도\n네가 얼마나 애쓰고 있는지\n나는 알아.\n\n오늘 하루 정말 수고했어.\n\n이 글이 필요한 친구에게 보내주세요.\n\n#위로 #오늘도수고했어 #힐링 #공감 #직장인 #마음관리 #응원 #하루끝 #수고했어 #위로한마디 #번아웃 #자기계발 #마음챙김 #당신은소중합니다 #라이트하우스미디어"
    },
    # 3. 체크리스트 (저장 유도)
    {
        "t": ["저장 필수", "번아웃 직전", "신호 7가지"],
        "b": ["", "> 1. 사소한 일에 짜증", "> 2. 의욕이 사라짐", "> 3. 잠을 자도 피곤", "> 4. 집중이 안 됨", "> 5. 혼자 있고 싶음", "> 6. 몸이 자주 아픔", "> 7. 웃음이 줄어듦", "", "*4개 이상? 위험 신호입니다", "*프로필에서 무료 전자책 받으세요"],
        "c": (155,89,182), "s": "dark", "bg": "SAVE THIS",
        "cap": "번아웃 직전 신호 7가지\n나중에 필요합니다. 저장해두세요.\n\n1. 사소한 일에 짜증\n2. 의욕이 사라짐\n3. 잠을 자도 피곤\n4. 집중이 안 됨\n5. 혼자 있고 싶음\n6. 몸이 자주 아픔\n7. 웃음이 줄어듦\n\n4개 이상이면 위험 신호.\n프로필 링크에서 무료 전자책 받으세요.\n\n#번아웃자가진단 #번아웃신호 #직장인건강 #멘탈케어 #자기계발 #마음관리 #스트레스 #힐링 #직장인공감 #건강 #번아웃극복 #자기관리 #워라밸 #저장해둬 #라이트하우스미디어"
    },
    # 4. 분노/통쾌형
    {
        "t": ["상사가 절대", "말하지 않는", "진실"],
        "b": ["", "야근은 능력이 아니라", "시스템의 실패입니다", "", "당신이 느린 게 아니라", "일이 너무 많은 겁니다", "", "*이게 팩트입니다", "", "공감되면 공유해주세요", "더 많은 사람이 알아야 합니다"],
        "c": (231,76,60), "s": "dark", "bg": "TRUTH",
        "cap": "상사가 절대 말하지 않는 진실.\n\n야근은 능력이 아니라 시스템의 실패입니다.\n당신이 느린 게 아니라 일이 너무 많은 겁니다.\n\n이게 팩트입니다.\n\n공감되면 공유해주세요.\n더 많은 사람이 알아야 합니다.\n\n#직장인현실 #야근 #직장인공감 #번아웃 #노동 #워라밸 #직장 #퇴근 #직장인일상 #공감글 #현실 #야근반대 #자기계발 #마음관리 #라이트하우스미디어"
    },
    # 5. 실용 팁 (저장)
    {
        "t": ["퇴근 후 30분", "이것만 하면", "내일이 달라집니다"],
        "b": ["", "> 10분: 스마트폰 내려놓기", "> 10분: 동네 한 바퀴 산책", "> 5분: 감사한 것 3개 적기", "> 5분: 내일 할 일 1개 정하기", "", "*이 30분이", "*8시간 수면보다 효과적입니다", "", "저장하고 오늘부터 실천!"],
        "c": (52,152,219), "s": "dark", "bg": "30MIN",
        "cap": "퇴근 후 30분, 이것만 하면 내일이 달라집니다.\n\n10분: 스마트폰 내려놓기\n10분: 동네 산책\n5분: 감사한 것 3개\n5분: 내일 할 일 1개\n\n이 30분이 8시간 수면보다 효과적입니다.\n저장하고 오늘부터!\n\n#퇴근후루틴 #직장인팁 #자기계발 #마음관리 #힐링 #습관 #루틴 #저녁루틴 #워라밸 #직장인루틴 #에너지관리 #생산성 #직장인 #자기관리 #라이트하우스미디어"
    },
    # 6. 선택형 (댓글 유도)
    {
        "t": ["당신의 번아웃", "레벨은?"],
        "b": ["", "> Lv.1 좀 피곤한 정도", "> Lv.2 의욕이 없다", "> Lv.3 출근이 두렵다", "> Lv.4 모든 게 귀찮다", "> Lv.5 아무 감정이 없다", "", "댓글로 레벨 남겨주세요", "같은 레벨끼리 위로해요", "", "*Lv.3 이상이면", "*프로필에서 전자책 받으세요"],
        "c": (186,117,23), "s": "dark", "bg": "LEVEL?",
        "cap": "당신의 번아웃 레벨은?\n\nLv.1 좀 피곤한 정도\nLv.2 의욕이 없다\nLv.3 출근이 두렵다\nLv.4 모든 게 귀찮다\nLv.5 아무 감정이 없다\n\n댓글로 레벨 남겨주세요.\n같은 레벨끼리 위로해요.\n\nLv.3 이상이면 프로필에서 무료 전자책!\n\n#번아웃레벨 #번아웃 #직장인공감 #멘탈 #자기계발 #마음관리 #힐링 #스트레스 #직장인 #공감 #투표 #워라밸 #직장인일상 #번아웃극복 #라이트하우스미디어"
    },
    # 7. 위로 시리즈
    {
        "t": ["괜찮지 않아도", "괜찮습니다"],
        "b": ["", "울고 싶으면 우세요", "쉬고 싶으면 쉬세요", "도망치고 싶으면 도망치세요", "", "그게 약한 게 아닙니다", "그게 살아있다는 증거입니다", "", "*오늘 하루도", "*충분히 잘 버텼습니다"],
        "c": (29,158,117), "s": "warm", "bg": "",
        "cap": "괜찮지 않아도 괜찮습니다.\n\n울고 싶으면 우세요.\n쉬고 싶으면 쉬세요.\n도망치고 싶으면 도망치세요.\n\n그게 약한 게 아닙니다.\n그게 살아있다는 증거입니다.\n\n이 글이 필요한 사람에게 보내주세요.\n\n#괜찮아 #위로 #힐링 #마음관리 #직장인공감 #공감 #응원 #오늘도수고했어 #번아웃 #자기계발 #마음챙김 #위로한마디 #눈물 #힘내 #라이트하우스미디어"
    },
    # 8. 숫자 충격
    {
        "t": ["한국 직장인", "평균 수면 시간"],
        "b": ["", "#5.9시간", "", "권장 수면: 7-9시간", "", "부족한 1.1시간이", "당신의 건강과 행복을", "매일 갉아먹고 있습니다", "", "*오늘부터 30분만", "*일찍 자보세요"],
        "c": (231,76,60), "s": "dark", "bg": "FACT",
        "cap": "한국 직장인 평균 수면 시간: 5.9시간\n\n권장 수면: 7-9시간\n\n부족한 1.1시간이 당신의 건강과 행복을 매일 갉아먹고 있습니다.\n\n오늘부터 30분만 일찍 자보세요.\n\n#수면부족 #직장인건강 #수면 #번아웃 #건강 #자기계발 #마음관리 #힐링 #직장인 #워라밸 #숙면 #피로 #건강관리 #직장인일상 #라이트하우스미디어"
    },
    # 9. Before/After
    {
        "t": ["아침 루틴 전 vs 후", "같은 사람 맞아?"],
        "b": ["", "*BEFORE:", "알람 5번 끄기", "출근길 좀비", "오전 내내 멍", "", "*AFTER (3주 후):", "눈 뜨자마자 물 한 잔", "출근길에 팟캐스트", "오전에 업무 70% 완료", "", "비밀은 프로필 링크에서"],
        "c": (52,152,219), "s": "dark", "bg": "B vs A",
        "cap": "아침 루틴 전 vs 후\n같은 사람 맞아?\n\nBEFORE:\n알람 5번 끄기 / 출근길 좀비 / 오전 내내 멍\n\nAFTER (3주 후):\n물 한 잔 / 팟캐스트 / 오전에 업무 70% 완료\n\n비밀은 프로필 링크에서.\n\n#비포에프터 #아침루틴 #자기계발 #모닝루틴 #직장인 #습관 #변화 #성장 #힐링 #마음관리 #직장인루틴 #미라클모닝 #워라밸 #에너지관리 #라이트하우스미디어"
    },
    # 10. 무료 나눔
    {
        "t": ["무료 전자책", "나눔합니다"],
        "b": ["", "번아웃에서 벗어나는 법", "감정 관리 5가지 기술", "아침 루틴 가이드", "퇴근 후 회복 플랜", "에너지 충전법", "", "*총 18권 무료", "", "> 프로필 링크 클릭!", "> 바로 다운로드 가능!", "", "저장하고 나중에 받아가세요"],
        "c": (29,158,117), "s": "dark", "bg": "FREE x18",
        "cap": "무료 전자책 18권 나눔합니다.\n\n번아웃에서 벗어나는 법\n감정 관리 5가지 기술\n아침 루틴 가이드\n퇴근 후 회복 플랜\n에너지 충전법\n... 외 13권\n\n프로필 링크에서 바로 다운로드!\n저장하고 나중에 받아가세요.\n\n#무료전자책 #전자책나눔 #자기계발 #번아웃 #마음관리 #힐링 #직장인 #무료 #나눔 #전자책 #자기관리 #직장인공감 #워라밸 #습관 #라이트하우스미디어"
    },
]

for i, post in enumerate(viral_posts):
    print(f"\n[{i+1}/10] {post['t'][0]} {post['t'][1] if len(post['t'])>1 else ''}")
    img = make_card(post["t"], post["b"], post["c"], post["s"], post["bg"])
    ig, fb = upload_post(img, post["cap"])
    print(f"  IG:{'OK' if ig else 'X (limit)'} FB:{'OK' if fb else 'X'}")
    time.sleep(4)

print(f"\n{'='*60}")
print("  VIRAL CONTENT DONE!")
print(f"{'='*60}")
