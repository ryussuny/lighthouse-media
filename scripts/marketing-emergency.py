"""마케팅 긴급 투입: 참여 유도 게시물 5개 + 성장 전략"""
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

def claude(prompt, max_t=4096):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": max_t, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def tc(draw, y, text, font, fill, W=1080, sp=0):
    bb = draw.textbbox((0,0), text, font=font)
    draw.text(((W-(bb[2]-bb[0]))/2, y), text, font=font, fill=fill)
    return y + bb[3]-bb[1] + sp

W, H = 1080, 1350
DARK = (10, 12, 24)

print("=" * 60)
print("  MARKETING EMERGENCY")
print("=" * 60)

# 1. 분석
print("\n[1/3] 100만 채널 비교 분석...")
analysis = claude("너는 인스타그램 성장 전문가다. 우리 채널(@lighthouse_media77): 팔로워4명, 게시물36개, 좋아요평균1개, 댓글0. 주제: 번아웃/자기계발/마음관리. 타겟: 20-40대 한국 직장인.\n\n100만 채널과 비교해서:\n1. 치명적 문제 TOP5\n2. 100만 채널 초기 전략 TOP10\n3. 즉시 실행 액션 20개\n4. 해시태그 50개(대형15+중형20+소형15)\n5. 참여율 올리는 방법 10가지\n6. 릴스 바이럴 공식\n7. 7일 100명 로드맵\n\n솔직하게. 숫자 기반으로.")

os.makedirs(os.path.join(HOME, "lighthouse-media", "output"), exist_ok=True)
with open(os.path.join(HOME, "lighthouse-media", "output", "marketing-emergency.md"), 'w', encoding='utf-8') as f:
    f.write(analysis)
print("  완료!")

# 2. 참여 유도 게시물 5개
print("\n[2/3] 참여 유도 게시물 5개 제작+게시...")

posts = [
    {"color": (231,76,60), "badge": "VOTE", "title": "월요일 아침\n당신의 기분은?",
     "lines": ["", "A. 죽을 것 같다", "B. 그냥저냥 버틴다", "C. 나름 괜찮다", "D. 월요일이 좋다", "", "댓글로 알파벳 남겨주세요!", "가장 많은 답변의 해결법", "전자책을 만들어 드립니다"],
     "cap": "월요일 아침, 당신의 기분은?\n\nA. 죽을 것 같다\nB. 그냥저냥 버틴다\nC. 나름 괜찮다\nD. 월요일이 좋다\n\n댓글로 알파벳 하나만!\n가장 많은 답변의 해결법 전자책 만들어 드릴게요.\n\n#월요병 #직장인공감 #번아웃 #직장인일상 #자기계발 #마음관리 #힐링 #직장인루틴 #워라밸 #직장인공감글 #투표 #번아웃극복 #자기관리 #직장인 #라이트하우스미디어"},

    {"color": (52,152,219), "badge": "Q&A", "title": "지금 가장\n듣고 싶은 말은?",
     "lines": ["", "1. 수고했어, 오늘도", "2. 넌 충분히 잘하고 있어", "3. 쉬어도 괜찮아", "4. 네 마음을 알아", "", "댓글로 번호 남겨주세요", "매일 그 말을 보내드릴게요"],
     "cap": "지금 가장 듣고 싶은 말은?\n\n1. 수고했어, 오늘도\n2. 넌 충분히 잘하고 있어\n3. 쉬어도 괜찮아\n4. 네 마음을 알아\n\n댓글로 번호 하나만 남겨주세요.\n\n#위로 #힐링 #직장인공감 #마음관리 #자기계발 #오늘도수고했어 #번아웃 #응원 #직장인 #마음챙김 #공감 #위로해줘 #하루끝 #자기관리 #라이트하우스미디어"},

    {"color": (29,158,117), "badge": "SAVE", "title": "저장 필수\n감정 응급키트",
     "lines": ["", "1. 화날 때: 3초 멈추기", "2. 불안할 때: 4-7-8 호흡", "3. 지칠 때: 2분 스트레칭", "4. 슬플 때: 감정에 이름 붙이기", "5. 무기력할 때: 딱 1개만 하기", "", "저장해두고 필요할 때 꺼내보세요"],
     "cap": "직장인 감정 응급키트 5가지\n나중에 꼭 필요할 때가 옵니다.\n\n1. 화날 때: 3초 멈추기\n2. 불안할 때: 4-7-8 호흡\n3. 지칠 때: 2분 스트레칭\n4. 슬플 때: 감정에 이름 붙이기\n5. 무기력할 때: 딱 1개만 하기\n\n저장 + 친구 태그!\n\n#감정관리 #직장인팁 #자기계발 #마음관리 #스트레스관리 #힐링 #직장인공감 #번아웃극복 #자기관리 #저장해둬 #직장인필수 #마음챙김 #워라밸 #꿀정보 #라이트하우스미디어"},

    {"color": (186,117,23), "badge": "TAG", "title": "이런 친구에게\n보내주세요",
     "lines": ["", "매일 야근하는 친구", "최근에 힘들어 보이는 친구", "항상 괜찮다고 하는 친구", "월요일마다 죽겠다는 친구", "쉬는 법을 모르는 친구", "", "태그하면 무료 전자책 선물!"],
     "cap": "이런 친구가 있다면 태그해주세요.\n\n매일 야근하는 친구\n힘들어 보이는 친구\n항상 괜찮다고 하는 친구\n월요일마다 죽겠다는 친구\n\n태그하면 무료 전자책을 보내드려요!\n작은 위로가 큰 힘이 됩니다.\n\n#친구태그 #위로 #직장인공감 #힐링 #마음관리 #자기계발 #번아웃 #무료전자책 #선물 #직장인 #공감 #응원 #함께 #우정 #라이트하우스미디어"},

    {"color": (155,89,182), "badge": "SHARE", "title": "퇴근하고\n가장 먼저\n하는 일은?",
     "lines": ["", "A. 소파에 눕는다", "B. 스마트폰을 본다", "C. 밥을 먹는다", "D. 운동을 한다", "E. 아무것도 못한다", "", "댓글로 솔직하게!", "공감되면 친구에게 공유!"],
     "cap": "퇴근하고 가장 먼저 하는 일은?\n\nA. 소파에 눕는다\nB. 스마트폰을 본다\nC. 밥을 먹는다\nD. 운동을 한다\nE. 아무것도 못한다\n\n댓글로 솔직하게!\n공감되면 친구에게 공유!\n\n#퇴근후 #직장인일상 #직장인공감 #번아웃 #자기계발 #마음관리 #힐링 #워라밸 #퇴근 #공감 #솔직 #직장인루틴 #자기관리 #일상 #라이트하우스미디어"},
]

for i, post in enumerate(posts):
    color = post['color']
    print(f"  [{i+1}/5] {post['title'].split(chr(10))[0]}")

    img = Image.new("RGB", (W, H), DARK)
    d = ImageDraw.Draw(img)
    for row in range(H):
        d.line([(0,row),(W,row)], fill=(10+int(row/H*6), 12+int(row/H*8), 24+int(row/H*10)))
    d.ellipse([W-200,-60,W+60,200], fill=(16,18,34))
    d.rectangle([0,0,W,4], fill=color)
    d.text((60,55), "LIGHTHOUSE MEDIA", font=gf(18), fill=color)
    bw = len(post['badge'])*12+20
    d.rounded_rectangle([W-bw-50,50,W-50,80], radius=12, fill=color)
    d.text((W-bw-38,55), post['badge'], font=gf(16,True), fill=(255,255,255))

    y = 250
    for ln in post['title'].split("\n"):
        y = tc(d, y, ln, gf(52,True), (255,255,255), W, 22)
    y += 20
    d.rectangle([W//2-50,y,W//2+50,y+2], fill=color)
    y += 30

    for ln in post['lines']:
        if ln == '':
            y += 16; continue
        if len(ln) > 1 and (ln[0].isalpha() and ln[1] == '.') or (ln[0].isdigit() and ln[1] == '.'):
            d.rounded_rectangle([100,y,W-100,y+65], radius=12, fill=(40,44,65))
            d.text((140,y+16), ln, font=gf(26,True), fill=(255,255,255))
            y += 82
        else:
            y = tc(d, y, ln, gf(24), (170,175,190), W, 14)

    d.rectangle([W//2-30,H-90,W//2+30,H-87], fill=color)
    tc(d, H-70, "@lighthouse_media77", gf(16), (70,72,90), W)

    path = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "insta-images", f"engage_{i+1}.jpg")
    img.save(path, "JPEG", quality=95)
    with open(path, 'rb') as f:
        idata = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': idata, 'type': 'base64'})
    img_url = ir.json().get('data',{}).get('link')
    time.sleep(3)

    if img_url:
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url': img_url, 'caption': post['cap'], 'access_token': IG_TOKEN})
        rd = r.json()
        if 'id' in rd:
            time.sleep(5)
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id': rd['id'], 'access_token': IG_TOKEN})
            print(f"    IG: OK")
        else:
            print(f"    IG: {rd}")

        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url': img_url, 'message': post['cap'][:300], 'access_token': FB_TOKEN})
        print(f"    FB: {'OK' if 'id' in r.json() else 'FAIL'}")
    time.sleep(3)

# 3. 전략 문서
print("\n[3/3] 성장 전략 문서...")
strategy = claude("인스타 @lighthouse_media77 (팔로워4명)이 7일 안에 100명 달성하려면:\n1. 매일 해야 할 참여 루틴 (시간대별)\n2. 팔로우해야 할 한국 자기계발 계정 20개 (실제 계정명)\n3. 사용할 해시태그 30개 (대형10+중형10+소형10)\n4. 스토리 활용법 5가지\n5. 릴스 1000뷰 넘기는 법\n구체적으로.")

with open(os.path.join(HOME, "lighthouse-media", "output", "growth-7day-plan.md"), 'w', encoding='utf-8') as f:
    f.write(strategy)
print("  저장 완료!")

print(f"\n{'='*60}")
print("  MARKETING DONE!")
print("  - 참여 유도 게시물 5개 (투표/질문/저장/태그/공유)")
print("  - 100만 채널 비교 분석 리포트")
print("  - 7일 100명 성장 전략")
print(f"{'='*60}")
