"""7세트 x 8장 Instagram 캐러셀 카드뉴스 → Instagram + Facebook 자동 게시"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens["instagram"]
FB_TOKEN = tokens["facebook_page"]
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
OUT = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", "7sets")
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1350
DARK = (10, 12, 24)

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(draw, y, text, font, fill, sp=0):
    bb = draw.textbbox((0,0), text, font=font)
    draw.text(((W-(bb[2]-bb[0]))/2, y), text, font=font, fill=fill)
    return y + bb[3]-bb[1] + sp

def make_slide(lines, color, badge="", num="", page=""):
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
    tc(d, H-70, "@lighthouse_media77", gf(16), (70,72,90))
    if page:
        d.text((W-80,H-70), page, font=gf(14), fill=(50,52,68))
    return img

# ── 7 Sets Definition ──

ALL_SETS = [
    # SET 1
    {
        "title": "지치지 않고 오래 달리는 법",
        "color": (29,158,117),
        "caption": "지치지 않고 오래 달리는 법\n\n번아웃은 게으름이 아닙니다.\n에너지를 관리하는 방법을 알면\n지치지 않고 오래 달릴 수 있습니다.\n\n충전 루틴 4단계:\n1. 신체 에너지 충전\n2. 감정 에너지 회복\n3. 정신 에너지 정리\n4. 영적 에너지 연결\n\n80% 효율 법칙으로 지속 가능하게!\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#번아웃극복 #에너지관리 #자기관리 #회복탄력성 #직장인힐링 #충전루틴 #지속가능성 #마음관리 #멘탈관리 #워라밸 #습관형성 #자기계발 #힐링 #건강한삶 #라이트하우스미디어",
        "fb_msg": "지치지 않고 오래 달리는 법\n\n번아웃은 게으름이 아닙니다.\n에너지를 관리하는 법을 배워보세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","지치지 않고"),("big","오래 달리는 법"),("line",""),("sub","번아웃 없이 꾸준히 성장하는 비결"),("sub","에너지 관리의 모든 것"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","번아웃은"),("title","게으름이 아닙니다"),("line",""),("body","열심히 하는 사람일수록"),("body","더 쉽게 번아웃됩니다"),("space",""),("accent","문제는 노력이 아니라 방향입니다"),("space",""),("body","에너지를 관리하지 않으면"),("body","어떤 노력도 오래 가지 못합니다")]),
            (""  , "02", "3/8", [("title","에너지 3가지 유형"),("line",""),("accent","1. 신체 에너지"),("body","수면, 운동, 영양의 기본기"),("space",""),("accent","2. 감정 에너지"),("body","관계, 감사, 긍정의 힘"),("space",""),("accent","3. 정신 에너지"),("body","집중, 몰입, 창의력의 원천")]),
            (""  , "03", "4/8", [("title","충전 루틴 4단계"),("line",""),("card","1 | 아침 10분 명상과 호흡"),("card","2 | 점심 후 15분 산책"),("card","3 | 저녁 감사 일기 3줄"),("card","4 | 취침 전 디지털 오프"),("space",""),("sub","매일 반복하면 에너지가 쌓입니다")]),
            (""  , "04", "5/8", [("title","80% 효율 법칙"),("line",""),("body","100%로 달리면"),("body","3개월을 못 갑니다"),("space",""),("accent","80%로 꾸준히 하면"),("accent","3년을 갈 수 있습니다"),("space",""),("body","완벽보다 지속이 중요합니다"),("body","여유 20%가 회복의 시간입니다")]),
            (""  , "05", "6/8", [("title","회복 탄력성 키우기"),("line",""),("accent","마인드셋 전환"),("body","실패는 데이터입니다"),("space",""),("accent","회복 루틴 만들기"),("body","나만의 충전소를 정해두세요"),("space",""),("accent","사회적 지지"),("body","함께 하면 더 빨리 회복됩니다")]),
            (""  , "06", "7/8", [("title","7일 체크리스트"),("line",""),("body","Day 1: 나의 에너지 레벨 체크"),("body","Day 2: 아침 루틴 1개 시작"),("body","Day 3: 에너지 드레인 파악"),("body","Day 4: 충전 활동 1개 추가"),("body","Day 5: 80% 법칙 적용"),("body","Day 6: 회복 루틴 설계"),("body","Day 7: 주간 에너지 리뷰"),("space",""),("accent","무료 전자책에 상세 가이드 포함")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 2
    {
        "title": "감정에 휘둘리지 않는 기술",
        "color": (52,152,219),
        "caption": "감정에 휘둘리지 않는 기술\n\n감정은 적이 아니라 신호입니다.\n감정을 이해하고 다루는 법을 알면\n더 이상 휘둘리지 않습니다.\n\n감정 인식 3단계:\n1. 알아차리기\n2. 이름 붙이기\n3. 수용하기\n\n7일 감정 일기로 시작해보세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#감정관리 #마음챙김 #분노조절 #불안극복 #자기이해 #감정일기 #멘탈케어 #심리학 #자기계발 #힐링 #마음건강 #스트레스관리 #감정인식 #자기돌봄 #라이트하우스미디어",
        "fb_msg": "감정에 휘둘리지 않는 기술\n\n감정은 적이 아니라 신호입니다.\n감정을 다루는 법을 배워보세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","감정에 휘둘리지"),("big","않는 기술"),("line",""),("sub","감정을 다스리는 실전 가이드"),("sub","더 이상 감정의 노예가 되지 마세요"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","감정은"),("title","신호입니다"),("line",""),("body","감정은 적이 아닙니다"),("body","우리 몸이 보내는 메시지입니다"),("space",""),("accent","화가 나면 경계가 침범된 것"),("accent","불안하면 준비가 필요한 것"),("space",""),("body","감정의 언어를 이해하면"),("body","인생이 달라집니다")]),
            (""  , "02", "3/8", [("title","감정 인식 3단계"),("line",""),("accent","Step 1. 알아차리기"),("body","지금 내 몸에서 무슨 일이 일어나는가"),("space",""),("accent","Step 2. 이름 붙이기"),("body","이 감정의 정확한 이름은 무엇인가"),("space",""),("accent","Step 3. 수용하기"),("body","이 감정을 있는 그대로 받아들이기")]),
            (""  , "03", "4/8", [("title","분노 관리법"),("line",""),("card","1 | 6초 룰: 반응 전 6초 멈추기"),("card","2 | 깊은 호흡 3회로 진정하기"),("card","3 | 나-전달법으로 표현하기"),("card","4 | 분노 일기로 패턴 파악"),("space",""),("sub","분노는 관리할 수 있습니다")]),
            (""  , "04", "5/8", [("title","불안 다루기"),("line",""),("body","불안의 90%는"),("body","일어나지 않는 일입니다"),("space",""),("accent","5-4-3-2-1 기법"),("body","5가지 보이는 것, 4가지 만지는 것"),("body","3가지 들리는 것, 2가지 냄새"),("body","1가지 맛으로 현재에 집중"),("space",""),("accent","지금 이 순간에 머무르세요")]),
            (""  , "05", "6/8", [("title","슬픔 수용하기"),("line",""),("body","슬픔을 피하면"),("body","더 오래 머무릅니다"),("space",""),("accent","울어도 괜찮습니다"),("body","슬픔은 치유의 과정입니다"),("space",""),("accent","나에게 친절하세요"),("body","힘든 시간도 지나갑니다"),("body","천천히, 자기 속도대로")]),
            (""  , "06", "7/8", [("title","7일 감정 일기"),("line",""),("body","Day 1: 오늘 느낀 감정 3가지 적기"),("body","Day 2: 감정의 강도 1~10 표시"),("body","Day 3: 감정의 원인 탐색"),("body","Day 4: 몸의 반응 관찰"),("body","Day 5: 대처법 기록"),("body","Day 6: 감정 패턴 발견"),("body","Day 7: 나만의 감정 사전 만들기"),("space",""),("accent","꾸준히 쓰면 감정 근육이 생깁니다")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 3
    {
        "title": "작은 변화가 큰 차이를 만든다",
        "color": (155,89,182),
        "caption": "작은 변화가 큰 차이를 만든다\n\n매일 1%만 나아지면\n1년 후 37배가 됩니다.\n\n작은 습관 4개:\n1. 2분 명상\n2. 감사 1줄\n3. 물 한 잔\n4. 10분 독서\n\n21일 챌린지로 인생을 바꿔보세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#습관형성 #작은변화 #1퍼센트법칙 #자기계발 #21일챌린지 #습관의힘 #성장마인드 #매일성장 #루틴만들기 #자기관리 #동기부여 #목표달성 #꾸준함 #변화 #라이트하우스미디어",
        "fb_msg": "작은 변화가 큰 차이를 만든다\n\n매일 1%만 나아지면 1년 후 37배!\n작은 습관의 놀라운 힘을 경험하세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","작은 변화가"),("big","큰 차이를 만든다"),("line",""),("sub","매일 1%의 성장이 만드는 기적"),("sub","습관의 과학으로 증명된 방법"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","1% 법칙의 힘"),("line",""),("body","매일 1%만 나아지면"),("body","1년 후 37배가 됩니다"),("space",""),("accent","1.01의 365제곱 = 37.78"),("space",""),("body","반대로 매일 1% 퇴보하면"),("body","1년 후 0.03이 됩니다"),("space",""),("accent","작은 차이가 엄청난 결과를 만듭니다")]),
            (""  , "02", "3/8", [("title","습관의 과학"),("line",""),("accent","습관 루프 3단계"),("space",""),("body","1. 신호 → 행동을 시작하는 트리거"),("space",""),("body","2. 루틴 → 반복되는 행동 패턴"),("space",""),("body","3. 보상 → 행동을 강화하는 결과"),("space",""),("accent","이 구조를 알면 습관을 설계할 수 있습니다")]),
            (""  , "03", "4/8", [("title","작은 습관 4개"),("line",""),("card","1 | 아침 2분 명상으로 시작"),("card","2 | 감사한 것 1줄 적기"),("card","3 | 일어나서 물 한 잔"),("card","4 | 자기 전 10분 독서"),("space",""),("sub","작게 시작하면 실패할 수 없습니다")]),
            (""  , "04", "5/8", [("title","트리거 설정법"),("line",""),("body","기존 습관에 새 습관을 연결하세요"),("space",""),("accent","양치 후 → 2분 명상"),("accent","식사 후 → 감사 1줄"),("accent","기상 직후 → 물 한 잔"),("accent","잠자리 → 10분 독서"),("space",""),("body","트리거가 있으면"),("body","의지력이 필요 없습니다")]),
            (""  , "05", "6/8", [("title","실패해도 괜찮다"),("line",""),("body","완벽하지 않아도 됩니다"),("body","하루 빠져도 괜찮습니다"),("space",""),("accent","2번 연속 빠지지만 않으면 됩니다"),("space",""),("body","넘어져도 다시 일어나면"),("body","그것이 진짜 습관입니다"),("space",""),("accent","자신에게 관대해지세요")]),
            (""  , "06", "7/8", [("title","21일 챌린지"),("line",""),("body","Week 1: 습관 1개만 시작"),("body","Week 2: 습관 2개로 확장"),("body","Week 3: 전체 루틴 완성"),("space",""),("accent","21일이면 뇌가 바뀝니다"),("space",""),("body","66일이면 자동화됩니다"),("body","365일이면 인생이 바뀝니다"),("space",""),("accent","오늘 시작하세요")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 4
    {
        "title": "퇴근 후 진짜 쉬는 법",
        "color": (186,117,23),
        "caption": "퇴근 후 진짜 쉬는 법\n\n소파에 누워 핸드폰 보는 건\n진짜 휴식이 아닙니다.\n\n저녁 루틴 5단계:\n1. 샤워로 전환\n2. 30분 산책\n3. 디지털 오프\n4. 취미 활동\n5. 감사 일기\n\n능동적 휴식이 진짜 회복입니다.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#퇴근후 #진짜휴식 #디지털디톡스 #저녁루틴 #수면관리 #워라밸 #직장인 #힐링타임 #능동적휴식 #회복 #자기돌봄 #건강한저녁 #주말계획 #리커버리 #라이트하우스미디어",
        "fb_msg": "퇴근 후 진짜 쉬는 법\n\n소파에서 핸드폰 보는 건 진짜 휴식이 아닙니다.\n능동적 휴식법을 알아보세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","퇴근 후"),("big","진짜 쉬는 법"),("line",""),("sub","소파에 누워 핸드폰 보는 건"),("sub","진짜 휴식이 아닙니다"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","수동적 vs 능동적 휴식"),("line",""),("accent","수동적 휴식"),("body","TV, SNS, 유튜브 시청"),("body","→ 뇌는 계속 일합니다"),("space",""),("accent","능동적 휴식"),("body","산책, 명상, 취미 활동"),("body","→ 뇌가 진짜 쉽니다"),("space",""),("accent","같은 시간, 다른 회복력")]),
            (""  , "02", "3/8", [("title","디지털 디톡스 효과"),("line",""),("body","하루 1시간 디지털 디톡스만으로"),("space",""),("accent","수면의 질 40% 향상"),("accent","불안감 30% 감소"),("accent","집중력 25% 증가"),("space",""),("body","핸드폰을 내려놓는 순간"),("body","진짜 휴식이 시작됩니다")]),
            (""  , "03", "4/8", [("title","저녁 루틴 5단계"),("line",""),("card","1 | 귀가 후 샤워로 모드 전환"),("card","2 | 30분 동네 산책"),("card","3 | 저녁 8시 디지털 오프"),("card","4 | 좋아하는 취미 활동"),("card","5 | 감사 일기 3줄 쓰기"),("space",""),("sub","순서대로 따라해보세요")]),
            (""  , "04", "5/8", [("title","수면의 질 높이기"),("line",""),("accent","취침 2시간 전"),("body","카페인, 밝은 빛 차단"),("space",""),("accent","취침 1시간 전"),("body","핸드폰 내려놓기"),("space",""),("accent","취침 직전"),("body","감사 일기 + 내일 계획"),("space",""),("body","잘 자야 잘 삽니다")]),
            (""  , "05", "6/8", [("title","주말 리커버리"),("line",""),("body","주말은 평일의 연장이 아닙니다"),("space",""),("accent","토요일: 능동적 회복"),("body","운동, 자연, 사람 만나기"),("space",""),("accent","일요일: 준비의 시간"),("body","다음 주 계획, 충전, 정리"),("space",""),("accent","주말을 디자인하세요")]),
            (""  , "06", "7/8", [("title","7일 플랜"),("line",""),("body","Day 1: 퇴근 후 30분 산책"),("body","Day 2: 저녁 8시 핸드폰 OFF"),("body","Day 3: 취미 활동 30분"),("body","Day 4: 감사 일기 시작"),("body","Day 5: 전체 저녁 루틴 실행"),("body","Day 6: 수면 루틴 추가"),("body","Day 7: 주간 리뷰 & 조정"),("space",""),("accent","일주일이면 몸이 기억합니다")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 5
    {
        "title": "새벽 5시의 작은 기적",
        "color": (231,76,60),
        "caption": "새벽 5시의 작은 기적\n\n성공한 사람들의 공통점:\n남들보다 먼저 하루를 시작합니다.\n\n30분 미라클 모닝:\n1. 5분 명상\n2. 10분 운동\n3. 10분 독서\n4. 5분 계획\n\n7일 챌린지로 새벽의 기적을 경험하세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#미라클모닝 #새벽기상 #아침루틴 #자기계발 #5시기상 #모닝루틴 #성공습관 #일찍일어나기 #아침명상 #독서습관 #운동습관 #챌린지 #성장 #동기부여 #라이트하우스미디어",
        "fb_msg": "새벽 5시의 작은 기적\n\n남들보다 먼저 하루를 시작하면\n인생이 달라집니다.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","새벽 5시의"),("big","작은 기적"),("line",""),("sub","남들보다 먼저 시작하는 하루"),("sub","미라클 모닝의 과학적 비밀"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","왜 새벽인가"),("line",""),("body","새벽은 세상이 조용한 시간"),("body","방해 없이 온전히 나에게 집중"),("space",""),("accent","새벽 1시간 = 낮 3시간"),("space",""),("body","CEO의 90%가 새벽에 일어납니다"),("body","우연이 아닙니다"),("space",""),("accent","새벽이 인생을 바꿉니다")]),
            (""  , "02", "3/8", [("title","미라클 모닝 과학"),("line",""),("accent","코르티솔 각성 반응"),("body","기상 후 30분이 뇌 활성화 최고점"),("space",""),("accent","의지력 배터리"),("body","아침에 가장 충만, 저녁에 고갈"),("space",""),("accent","전두엽 활성화"),("body","아침 루틴이 하루 집중력을 결정")]),
            (""  , "03", "4/8", [("title","30분 루틴"),("line",""),("card","1 | 5분 명상 (호흡에 집중)"),("card","2 | 10분 가벼운 운동"),("card","3 | 10분 독서 (자기계발서)"),("card","4 | 5분 오늘의 계획 세우기"),("space",""),("sub","30분이면 충분합니다")]),
            (""  , "04", "5/8", [("title","일찍 일어나는 법"),("line",""),("accent","전날 밤이 핵심입니다"),("space",""),("body","1. 알람을 침대에서 멀리 두기"),("space",""),("body","2. 10시 30분 취침 목표"),("space",""),("body","3. 일어나면 바로 불 켜기"),("space",""),("body","4. 첫 주는 30분만 앞당기기"),("space",""),("accent","천천히, 하지만 꾸준히")]),
            (""  , "05", "6/8", [("title","꾸준히 하는 비결"),("line",""),("body","동기부여는 시작하게 하지만"),("body","습관이 계속하게 합니다"),("space",""),("accent","비결 1: 완벽 포기"),("body","5분이라도 OK"),("space",""),("accent","비결 2: 보상 설정"),("body","좋아하는 커피로 자신에게 상 주기"),("space",""),("accent","비결 3: 기록하기")]),
            (""  , "06", "7/8", [("title","7일 챌린지"),("line",""),("body","Day 1: 평소보다 30분 일찍 기상"),("body","Day 2: 5분 명상만 해보기"),("body","Day 3: 명상 + 운동 추가"),("body","Day 4: 전체 30분 루틴 시도"),("body","Day 5: 루틴 반복"),("body","Day 6: 변화 느끼기"),("body","Day 7: 다음 주 계획"),("space",""),("accent","7일이면 몸이 기억합니다")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 6
    {
        "title": "감정의 온도를 조절하는 법",
        "color": (52,152,219),
        "caption": "감정의 온도를 조절하는 법\n\n감정에도 온도가 있습니다.\n너무 뜨거우면 폭발하고\n너무 차가우면 무감각해집니다.\n\n쿨다운 기술:\n1. 5초 심호흡\n2. 찬물로 손 씻기\n3. 자리 이동하기\n4. 감정 이름 말하기\n\n적정 온도를 유지하는 법을 배우세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#감정온도 #감정조절 #마음관리 #분노조절 #스트레스해소 #감정관리법 #마음챙김 #심리학 #관계개선 #자기이해 #멘탈관리 #감정코칭 #힐링 #자기돌봄 #라이트하우스미디어",
        "fb_msg": "감정의 온도를 조절하는 법\n\n감정에도 적정 온도가 있습니다.\n너무 뜨겁지도, 차갑지도 않게 유지하는 법.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","감정의 온도를"),("big","조절하는 법"),("line",""),("sub","뜨겁지도 차갑지도 않은"),("sub","적정 온도를 찾아가는 여정"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","감정 온도계란"),("line",""),("body","감정에도 온도가 있습니다"),("space",""),("accent","0도: 무감각, 무기력"),("body","감정을 차단한 상태"),("space",""),("accent","50도: 적정 온도"),("body","차분하지만 활력 있는 상태"),("space",""),("accent","100도: 폭발 직전"),("body","분노, 공포, 극심한 불안")]),
            (""  , "02", "3/8", [("title","과열 신호 5가지"),("line",""),("accent","1. 심장이 빨리 뛴다"),("accent","2. 목소리가 커진다"),("accent","3. 손이 떨린다"),("accent","4. 생각이 멈춘다"),("accent","5. 후회할 말이 나온다"),("space",""),("body","이 신호를 알아차리면"),("body","폭발을 막을 수 있습니다")]),
            (""  , "03", "4/8", [("title","쿨다운 기술"),("line",""),("card","1 | 5초 깊은 심호흡"),("card","2 | 찬물로 손 씻기"),("card","3 | 그 자리를 잠시 떠나기"),("card","4 | 감정의 이름을 말하기"),("space",""),("sub","6초만 참으면 감정의 파도가 지나갑니다")]),
            (""  , "04", "5/8", [("title","적정 온도 유지법"),("line",""),("body","매일 감정 체크인을 하세요"),("space",""),("accent","아침: 오늘 내 감정 온도는?"),("body","숫자로 표현하면 객관적이 됩니다"),("space",""),("accent","저녁: 오늘 가장 뜨거웠던 순간은?"),("body","패턴을 발견하면 예방할 수 있습니다"),("space",""),("accent","감정은 관리할 수 있습니다")]),
            (""  , "05", "6/8", [("title","관계에서의 온도"),("line",""),("body","나의 감정 온도가 높으면"),("body","상대방도 뜨거워집니다"),("space",""),("accent","대화 전 온도 체크"),("body","50도 이하일 때만 대화하세요"),("space",""),("accent","상대의 온도도 존중"),("body","뜨거운 사람에게는 시간을 주세요"),("space",""),("body","관계의 비결은 온도 관리입니다")]),
            (""  , "06", "7/8", [("title","실천 가이드"),("line",""),("body","Day 1: 감정 온도 기록 시작"),("body","Day 2: 과열 신호 파악"),("body","Day 3: 쿨다운 기술 연습"),("body","Day 4: 아침 체크인 습관화"),("body","Day 5: 관계에서 온도 관찰"),("body","Day 6: 적정 온도 유지 연습"),("body","Day 7: 한 주 감정 온도 리뷰"),("space",""),("accent","7일이면 감정의 주인이 됩니다")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
    # SET 7
    {
        "title": "에너지 뱅크 채우는 법",
        "color": (29,158,117),
        "caption": "에너지 뱅크 채우는 법\n\n에너지에는 4가지 종류가 있습니다.\n신체, 감정, 정신, 영적 에너지.\n\n충전법 4가지:\n1. 수면 7시간 확보\n2. 감사 일기 3줄\n3. 집중 타임 블록\n4. 의미 있는 일 연결\n\n30일 트래커로 에너지를 설계하세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media\n\n#에너지관리 #에너지충전 #자기관리 #시간관리 #직장인 #건강한삶 #습관 #루틴 #자기계발 #동기부여 #워라밸 #생산성 #에너지설계 #주간계획 #라이트하우스미디어",
        "fb_msg": "에너지 뱅크 채우는 법\n\n에너지에는 4가지 종류가 있습니다.\n전략적으로 충전하는 법을 배우세요.\n\n프로필 링크에서 무료 전자책 다운로드\n\n류선희 | Lighthouse Media",
        "slides": [
            (""  , "", "1/8", [("space",""),("space",""),("big","에너지 뱅크"),("big","채우는 법"),("line",""),("sub","고갈되지 않는 에너지 관리"),("sub","전략적 충전의 모든 것"),("space",""),("sub","무료 가이드 | 류선희")]),
            (""  , "01", "2/8", [("title","에너지 4가지 종류"),("line",""),("accent","1. 신체 에너지"),("body","수면, 운동, 영양"),("space",""),("accent","2. 감정 에너지"),("body","관계, 감사, 기쁨"),("space",""),("accent","3. 정신 에너지"),("body","집중, 학습, 창의"),("space",""),("accent","4. 영적 에너지"),("body","의미, 목적, 가치")]),
            (""  , "02", "3/8", [("title","에너지 드레인 요인"),("line",""),("accent","신체: 수면 부족, 운동 부족"),("space",""),("accent","감정: 부정적 관계, 비교"),("space",""),("accent","정신: 멀티태스킹, 정보 과부하"),("space",""),("accent","영적: 의미 없는 반복, 방향 상실"),("space",""),("body","어디서 새는지 알면"),("body","막을 수 있습니다")]),
            (""  , "03", "4/8", [("title","충전법 4가지"),("line",""),("card","1 | 수면 7시간 확보하기"),("card","2 | 감사 일기 3줄 쓰기"),("card","3 | 집중 타임 블록 만들기"),("card","4 | 의미 있는 일에 연결하기"),("space",""),("sub","4가지를 채우면 에너지가 넘칩니다")]),
            (""  , "04", "5/8", [("title","시간대별 관리"),("line",""),("accent","오전 9~12시: 골든 타임"),("body","가장 중요한 일을 이 시간에"),("space",""),("accent","오후 1~3시: 리차지 타임"),("body","가벼운 업무 + 짧은 휴식"),("space",""),("accent","오후 4~6시: 마무리 타임"),("body","정리, 내일 준비"),("space",""),("body","에너지에 맞춰 일하세요")]),
            (""  , "05", "6/8", [("title","주간 에너지 설계"),("line",""),("accent","월요일: 에너지 세팅"),("body","주간 목표 설정, 루틴 점검"),("space",""),("accent","수요일: 중간 점검"),("body","에너지 레벨 체크, 조정"),("space",""),("accent","금요일: 리뷰 & 충전"),("body","한 주 정리, 주말 계획"),("space",""),("accent","설계하면 흔들리지 않습니다")]),
            (""  , "06", "7/8", [("title","30일 트래커"),("line",""),("body","Week 1: 에너지 관찰 & 기록"),("body","Week 2: 드레인 요인 제거"),("body","Week 3: 충전 루틴 확립"),("body","Week 4: 시간대별 최적화"),("space",""),("accent","30일이면 에너지 시스템이 완성됩니다"),("space",""),("body","무료 전자책에 트래커 포함"),("body","지금 시작하세요")]),
            (""  , "", "8/8", [("space",""),("space",""),("title","무료 가이드"),("title","받는 방법"),("line",""),("cta_btn","3단계만 하면 됩니다"),("space",""),("body","1. @lighthouse_media77 팔로우"),("space",""),("body","2. 이 게시물에 좋아요"),("space",""),("body","3. DM으로 '전자책' 보내기"),("space",""),("accent","즉시 전송해드립니다!")]),
        ]
    },
]

# ── Main Execution ──

print("=" * 60)
print("  7 Sets x 8 Slides Card News → Instagram + Facebook")
print("=" * 60)

START_SET = int(os.environ.get("START_SET", "0"))  # 0-indexed, set env var to skip done sets
for si, s in enumerate(ALL_SETS):
    if si < START_SET:
        print(f"\n  Skipping SET {si+1}/7 (already done)")
        continue
    color = s["color"]
    title = s["title"]
    print(f"\n{'─'*60}")
    print(f"  SET {si+1}/7: {title}")
    print(f"{'─'*60}")

    set_dir = os.path.join(OUT, f"set{si+1}")
    os.makedirs(set_dir, exist_ok=True)

    img_urls = []
    for idx, (badge, num, page, lines) in enumerate(s["slides"]):
        img = make_slide(lines, color, badge, num, page)
        path = os.path.join(set_dir, f"slide_{idx+1:02d}.jpg")
        img.save(path, "JPEG", quality=95)

        with open(path, 'rb') as f:
            d = base64.b64encode(f.read()).decode()
        url = None
        for attempt in range(3):
            try:
                r = requests.post('https://api.imgur.com/3/image',
                                  headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                                  data={'image': d, 'type': 'base64'})
                url = r.json().get('data',{}).get('link')
                if url:
                    break
                print(f"    Slide {idx+1}/8: Retry {attempt+1} (no link)")
            except Exception as e:
                print(f"    Slide {idx+1}/8: Retry {attempt+1} ({e})")
            time.sleep(5)
        if url:
            img_urls.append(url)
        print(f"    Slide {idx+1}/8: {'OK' if url else 'FAIL'} {url or ''}")
        time.sleep(2)

    # ── Instagram Carousel ──
    print(f"\n    Posting IG carousel for SET {si+1}...")
    ig_ids = []
    for url in img_urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media',
                          data={'image_url': url, 'is_carousel_item': 'true', 'access_token': IG_TOKEN})
        d = r.json()
        if 'id' in d:
            ig_ids.append(d['id'])
        time.sleep(2)

    caption = s["caption"]

    if len(ig_ids) >= 2:
        time.sleep(8)
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media',
                          data={'media_type': 'CAROUSEL', 'children': ','.join(ig_ids),
                                'caption': caption, 'access_token': IG_TOKEN})
        c = r.json()
        if 'id' in c:
            time.sleep(8)
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
                               data={'creation_id': c['id'], 'access_token': IG_TOKEN})
            print(f"    IG: OK {r2.json().get('id','')}")
        else:
            print(f"    IG: {c}")
    else:
        print(f"    IG: Not enough slides ({len(ig_ids)})")

    # ── Facebook Photo ──
    if img_urls:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos',
                          data={'url': img_urls[0], 'message': s["fb_msg"], 'access_token': FB_TOKEN})
        print(f"    FB: {'OK' if 'id' in r.json() else r.json()}")

    print(f"    SET {si+1} complete!")

    if si < len(ALL_SETS) - 1:
        print(f"    Waiting 5s before next set...")
        time.sleep(5)

print(f"\n{'='*60}")
print("  All 7 sets posted! Check @lighthouse_media77")
print(f"{'='*60}")
