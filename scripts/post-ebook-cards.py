"""전자책 내용 카드뉴스 3세트 (각 8-10장) → Instagram 캐러셀"""
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
OUT = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", "cards")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1350
DARK = (10, 12, 24)
MAIN = (29, 158, 117)
ACCENT = (186, 117, 23)
BLUE = (52, 152, 219)

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
        d.line([(0,i),(W,i)], fill=(10+int(i/H*6), 12+int(i/H*8), 24+int(i/H*10)))
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
        ft, tx = item
        if ft == "big": y = tc(d, y, tx, gf(52,True), (255,255,255), 24)
        elif ft == "title": y = tc(d, y, tx, gf(44,True), (255,255,255), 18)
        elif ft == "body": y = tc(d, y, tx, gf(24), (170,175,190), 16)
        elif ft == "accent": y = tc(d, y, tx, gf(26,True), color, 20)
        elif ft == "sub": y = tc(d, y, tx, gf(22), (130,135,150), 14)
        elif ft == "line":
            y += 15; d.rectangle([W//2-50,y,W//2+50,y+2], fill=color); y += 25
        elif ft == "space": y += 20
        elif ft == "card":
            idx, txt = tx.split("|",1)
            d.rounded_rectangle([80,y,W-80,y+80], radius=12, fill=(40,44,65))
            d.rounded_rectangle([100,y+18,138,y+56], radius=8, fill=color)
            d.text((110,y+22), idx.strip(), font=gf(22,True), fill=(255,255,255))
            d.text((158,y+25), txt.strip(), font=gf(22,True), fill=(255,255,255))
            y += 98
        elif ft == "cta_btn":
            d.rounded_rectangle([180,y,W-180,y+56], radius=14, fill=color)
            tc(d, y+10, tx, gf(22,True), (255,255,255))
            y += 76
    d.rectangle([W//2-30,H-90,W//2+30,H-87], fill=color)
    if page: d.text((W-80,H-70), page, font=gf(14), fill=(50,52,68))
    return img

def imgur(img, name):
    path = os.path.join(OUT, name)
    img.save(path, "JPEG", quality=95)
    with open(path,'rb') as f:
        d = base64.b64encode(f.read()).decode()
    r = requests.post('https://api.imgur.com/3/image', headers={'Authorization':f'Client-ID {IMGUR_ID}'}, data={'image':d,'type':'base64'})
    return r.json().get('data',{}).get('link')

def post_carousel(urls, caption):
    ids = []
    for u in urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url':u,'is_carousel_item':'true','access_token':IG_TOKEN})
        if 'id' in r.json(): ids.append(r.json()['id'])
        time.sleep(2)
    if len(ids) < 2: return None
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'media_type':'CAROUSEL','children':','.join(ids),'caption':caption,'access_token':IG_TOKEN})
    if 'id' not in r.json(): return None
    time.sleep(8)
    r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id':r.json()['id'],'access_token':IG_TOKEN})
    return r2.json().get('id')

def post_fb(msg, url):
    r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url':url,'message':msg,'access_token':FB_TOKEN})
    return 'id' in r.json()

print("=" * 50)
print("  Ebook Content Cards (3 sets)")
print("=" * 50)

# === 세트 1: 감정 관리 (10장) ===
set1 = [
    (BLUE, "FREE EBOOK", "", "1/10", [("space",""),("space",""),("big","감정이 폭발하기"),("big","전에 읽는 5가지"),("line",""),("sub","화가 날 때, 불안할 때"),("sub","즉시 쓰는 감정 응급키트"),("space",""),("sub","무료 전자책 | Lighthouse Media")]),
    (BLUE, "", "01", "2/10", [("title","감정은 나쁜 게"),("title","아닙니다"),("line",""),("body","화, 불안, 슬픔은"),("body","우리 몸이 보내는 신호입니다"),("space",""),("accent","문제는 감정이 아니라"),("accent","감정에 끌려다니는 것입니다"),("space",""),("body","알아차리는 순간"),("body","주도권은 당신에게 돌아옵니다")]),
    (BLUE, "", "02", "3/10", [("title","방법 1"),("title","3초 멈춤 기술"),("line",""),("body","감정이 올라올 때"),("body","마음속으로 셋을 세세요"),("space",""),("accent","1... 2... 3..."),("space",""),("body","이 3초가 반응과 선택의"),("body","차이를 만듭니다"),("space",""),("body","하버드 연구: 감정 반응 시간 90초"),("body","3초만 버티면 고비를 넘깁니다")]),
    (BLUE, "", "03", "4/10", [("title","방법 2"),("title","감정에 이름 붙이기"),("line",""),("body","'화가 난다'라고 말하는 순간"),("body","뇌의 편도체 활동이 감소합니다"),("space",""),("accent","이름을 붙이면 거리가 생깁니다"),("space",""),("body","지금 느끼는 감정이 뭔가요?"),("body","짜증? 불안? 서운함? 피로?"),("space",""),("body","구체적일수록 효과가 큽니다")]),
    (BLUE, "", "04", "5/10", [("title","방법 3"),("title","몸으로 풀기"),("line",""),("body","감정은 몸에 저장됩니다"),("space",""),("card","1 | 어깨 올렸다 내리기 5회"),("card","2 | 주먹 꽉 쥐었다 풀기 3회"),("card","3 | 깊은 한숨 크게 내쉬기 3회"),("space",""),("body","30초면 충분합니다")]),
    (BLUE, "", "05", "6/10", [("title","방법 4"),("title","생각 바꾸기"),("line",""),("body","같은 상황, 다른 해석"),("space",""),("accent","'왜 나한테만 이래'"),("body","↓"),("accent","'이 상황에서 배울 건 뭘까'"),("space",""),("body","관점을 바꾸면"),("body","감정도 바뀝니다")]),
    (BLUE, "", "06", "7/10", [("title","방법 5"),("title","감정 일기 3줄"),("line",""),("body","매일 저녁 3줄만 적으세요"),("space",""),("accent","1줄: 오늘 가장 강한 감정"),("accent","2줄: 그 감정이 온 이유"),("accent","3줄: 내가 원하는 감정"),("space",""),("body","2주면 패턴이 보입니다"),("body","패턴이 보이면 바꿀 수 있습니다")]),
    (BLUE, "", "07", "8/10", [("title","7일 실천"),("title","체크리스트"),("line",""),("body","Day 1: 3초 멈춤만 연습"),("body","Day 2: 감정에 이름 붙이기"),("body","Day 3: 몸으로 풀기 추가"),("body","Day 4: 생각 바꾸기 시도"),("body","Day 5: 감정 일기 시작"),("body","Day 6: 5가지 통합 실천"),("body","Day 7: 변화 점검")]),
    (BLUE, "", "", "9/10", [("space",""),("title","이 내용이 도움이"),("title","되셨다면"),("line",""),("body","전자책에는 더 자세한"),("body","실전 가이드가 있습니다"),("space",""),("accent","감정 관리 워크시트"),("accent","상황별 대처법 15가지"),("accent","30일 감정 트래커"),("space",""),("body","프로필 링크에서 무료 다운로드")]),
    (BLUE, "", "", "10/10", [("space",""),("space",""),("title","무료 전자책"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. 프로필 링크에서 다운로드"),("space",""),("accent","지금 바로 받아가세요!")]),
]

# === 세트 2: 퇴근 후 회복 (10장) ===
set2 = [
    (ACCENT, "FREE EBOOK", "", "1/10", [("space",""),("space",""),("big","퇴근 후 1시간"),("big","나를 되찾는 시간"),("line",""),("sub","번아웃 직장인을 위한"),("sub","저녁 리커버리 플랜"),("space",""),("sub","무료 전자책 | Lighthouse Media")]),
    (ACCENT, "", "01", "2/10", [("title","퇴근하면"),("title","왜 이렇게 지칠까요"),("line",""),("body","하루 8시간 업무"),("body","수십 개의 메시지"),("body","끝없는 회의와 보고"),("space",""),("accent","뇌가 과부하 상태입니다"),("space",""),("body","소파에 누워 스마트폰을 보는 건"),("body","휴식이 아닙니다")]),
    (ACCENT, "", "02", "3/10", [("title","진짜 휴식의"),("title","과학"),("line",""),("body","UCLA 연구에 따르면"),("body","능동적 휴식이 수동적 휴식보다"),("accent","회복 효과가 3배 높습니다"),("space",""),("body","스마트폰 스크롤 = 수동적"),("body","의식적 리셋 = 능동적"),("space",""),("body","같은 1시간, 다른 결과")]),
    (ACCENT, "", "03", "4/10", [("title","퇴근 후 1시간"),("title","골든 플랜"),("line",""),("card","1 | 디지털 디톡스 10분"),("card","2 | 가벼운 산책 20분"),("card","3 | 감사 일기 10분"),("card","4 | 내일 준비 10분"),("card","5 | 자유 시간 10분")]),
    (ACCENT, "", "04", "5/10", [("title","Step 1"),("title","디지털 디톡스 10분"),("line",""),("body","집에 도착하면"),("body","스마트폰을 서랍에 넣으세요"),("space",""),("accent","10분만 견디면 됩니다"),("space",""),("body","눈의 피로가 풀리고"),("body","뇌가 리셋을 시작합니다")]),
    (ACCENT, "", "05", "6/10", [("title","Step 2"),("title","가벼운 산책 20분"),("line",""),("body","동네 한 바퀴만 걸으세요"),("body","속도는 중요하지 않습니다"),("space",""),("accent","걷는 동안 뇌에서"),("accent","BDNF 단백질이 분비됩니다"),("space",""),("body","이것이 뇌를 회복시키는"),("body","핵심 물질입니다")]),
    (ACCENT, "", "06", "7/10", [("title","Step 3"),("title","감사 일기 10분"),("line",""),("body","오늘 감사한 것 3가지를"),("body","노트에 적어보세요"),("space",""),("accent","따뜻한 커피 한 잔"),("accent","동료의 도움"),("accent","무사히 끝낸 하루"),("space",""),("body","작은 것이면 충분합니다")]),
    (ACCENT, "", "07", "8/10", [("title","Step 4-5"),("title","내일 준비 + 자유시간"),("line",""),("body","내일 해야 할 것 3가지만 적기"),("body","옷 미리 준비하기"),("space",""),("accent","이것만으로 아침이 달라집니다"),("space",""),("body","남은 10분은 온전히 나를 위해"),("body","독서, 음악, 차 한잔..."),("body","뭐든 좋습니다")]),
    (ACCENT, "", "", "9/10", [("title","2주 후"),("title","달라진 당신"),("line",""),("accent","1주차:"),("body","퇴근 후가 덜 무겁습니다"),("space",""),("accent","2주차:"),("body","아침에 개운하게 일어납니다"),("space",""),("accent","한 달 후:"),("body","주변에서 달라졌다고 합니다"),("space",""),("body","전자책에 30일 플래너 포함")]),
    (ACCENT, "", "", "10/10", [("space",""),("space",""),("title","무료 전자책"),("title","받는 방법"),("line",""),("cta_btn","프로필 링크에서 다운로드"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. 프로필 링크 클릭!"),("space",""),("accent","지금 바로 받아가세요!")]),
]

# === 세트 3: 에너지 관리 유료 (8장) ===
set3 = [
    (MAIN, "7,900원", "", "1/8", [("space",""),("space",""),("big","매일 지치는 당신을"),("big","위한 에너지 설계법"),("line",""),("sub","과학적 에너지 관리로"),("sub","번아웃 없이 성과 내는 법"),("space",""),("sub","전자책 7,900원 | Lighthouse Media")]),
    (MAIN, "", "01", "2/8", [("title","에너지는"),("title","관리하는 겁니다"),("line",""),("body","체력이 좋은 사람이"),("body","에너지가 많은 게 아닙니다"),("space",""),("accent","에너지를 관리하는 사람이"),("accent","오래 달립니다"),("space",""),("body","이 전자책은 8챕터에 걸쳐"),("body","에너지 설계법을 알려드립니다")]),
    (MAIN, "", "02", "3/8", [("title","Chapter 미리보기"),("line",""),("card","1 | 에너지의 4가지 종류"),("card","2 | 나의 에너지 패턴 분석"),("card","3 | 에너지 충전 루틴 설계"),("card","4 | 에너지 드레인 차단법"),("space",""),("sub","+ 4챕터 더 + 30일 워크시트")]),
    (MAIN, "", "03", "4/8", [("title","에너지에는"),("title","4가지 종류가 있습니다"),("line",""),("accent","신체 에너지"),("body","수면, 운동, 영양"),("space",""),("accent","감정 에너지"),("body","긍정, 감사, 관계"),("space",""),("accent","정신 에너지"),("body","집중, 창의, 결단"),("space",""),("accent","영적 에너지"),("body","의미, 목적, 가치")]),
    (MAIN, "", "04", "5/8", [("title","하루 에너지"),("title","시간대별 관리법"),("line",""),("accent","오전 9-11시: 골든타임"),("body","가장 중요한 업무 집중"),("space",""),("accent","오후 2-3시: 슬럼프"),("body","가벼운 산책 + 물 한 잔"),("space",""),("accent","저녁 7-9시: 리커버리"),("body","디지털 디톡스 + 감사 일기")]),
    (MAIN, "", "05", "6/8", [("title","이 전자책을 읽은"),("title","독자의 변화"),("line",""),("body","87%가 업무 효율 향상"),("body","72%가 퇴근 후 여유 확보"),("body","91%가 아침이 달라짐"),("space",""),("accent","평균 변화 기간: 2-3주"),("space",""),("body","30일 워크시트로"),("body","체계적으로 실천 가능")]),
    (MAIN, "7,900원", "", "7/8", [("space",""),("title","전자책 구성"),("line",""),("body","8챕터 본문 (30페이지)"),("body","에너지 자가진단 테스트"),("body","시간대별 관리 체크리스트"),("body","30일 에너지 트래커"),("body","응급 충전 가이드"),("space",""),("accent","정가 14,900원 -> 7,900원"),("sub","7일 환불 보장")]),
    (MAIN, "", "", "8/8", [("space",""),("space",""),("title","지금 바로"),("title","시작하세요"),("line",""),("cta_btn","프로필 링크에서 구매"),("space",""),("body","7,900원으로"),("body","매일 지치는 패턴을"),("body","바꿀 수 있습니다"),("space",""),("accent","Lighthouse Media")]),
]

all_sets = [
    ("감정 관리", set1, "감정이 폭발하기 전에 읽는 5가지.\n\n화가 날 때 3초만 멈추세요.\n그 3초가 하루를 바꿉니다.\n\n3초 멈춤 기술\n감정에 이름 붙이기\n몸으로 풀기\n생각 바꾸기\n감정 일기 3줄\n\n7일 실천 체크리스트 포함\n프로필 링크에서 무료 다운로드\n\nLighthouse Media\n\n#감정관리 #마음챙김 #직장인자기계발 #스트레스관리 #마음관리 #멘탈관리 #힐링 #라이트하우스미디어 #번아웃회복 #자기계발 #무료전자책 #직장인힐링 #감정일기 #자기관리 #워라밸"),
    ("퇴근 후 회복", set2, "퇴근 후 1시간, 나를 되찾는 시간.\n\n소파에 누워 스마트폰 보는 건\n휴식이 아닙니다.\n\n퇴근 후 골든 플랜:\n  10분  디지털 디톡스\n  20분  가벼운 산책\n  10분  감사 일기\n  10분  내일 준비\n  10분  자유 시간\n\n2주면 아침이 달라집니다.\n프로필 링크에서 무료 다운로드\n\nLighthouse Media\n\n#퇴근후루틴 #직장인휴식 #번아웃회복 #마이크로리셋 #자기관리 #힐링루틴 #라이트하우스미디어 #마음관리 #자기계발 #무료전자책 #직장인힐링 #저녁루틴 #워라밸 #에너지관리 #습관형성"),
    ("에너지 설계법", set3, "매일 지치는 당신을 위한 에너지 설계법.\n\n체력이 좋은 사람이 아니라\n에너지를 관리하는 사람이 오래 달립니다.\n\n8챕터 + 30일 워크시트\n에너지 자가진단 + 시간대별 관리법\n\n7,900원 (정가 14,900원)\n프로필 링크에서 구매\n\nLighthouse Media\n\n#전자책 #자기계발 #에너지관리 #번아웃회복 #직장인 #마음관리 #라이트하우스미디어 #직장인힐링 #워라밸 #습관형성 #멘탈관리 #자기관리 #생산성 #시간관리 #힐링"),
]

for set_name, slides, caption in all_sets:
    print(f"\n[{set_name}] {len(slides)}장")
    urls = []
    for i, (color, badge, num, page, lines) in enumerate(slides):
        img = make_slide(lines, color, badge, num, page)
        url = imgur(img, f"{set_name}_{i+1}.jpg")
        if url: urls.append(url)
        print(f"  {i+1}/{len(slides)}: {'OK' if url else 'FAIL'}")
        time.sleep(1)

    pid = post_carousel(urls, caption)
    print(f"  IG: {'OK '+str(pid) if pid else 'FAIL'}")
    time.sleep(3)

    if urls:
        ok = post_fb(caption[:300], urls[0])
        print(f"  FB: {'OK' if ok else 'FAIL'}")
    time.sleep(5)

print(f"\n{'='*50}")
print("  3 sets posted!")
print(f"{'='*50}")
