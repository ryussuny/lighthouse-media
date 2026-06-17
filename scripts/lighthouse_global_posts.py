"""
Lighthouse Media — 글로벌 프리미엄 콘텐츠 생성 + Instagram 게시
기독교 정체성 유지, 종교적 색깔은 드러내지 않음
영어+한국어 병기, 전 세계인 공감 가능한 위로와 도전
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, math, random, time, base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
tokens = json.load(open(os.path.join(REPO, "config", "tokens.json"), encoding='utf-8'))
LH_TOKEN = tokens['facebook_page']
LH_IG_ID = '17841425580883266'
LH_PAGE_ID = '1097948196731052'
IMGUR_ID = "546c25a59c58ad7"
OUTPUT = os.path.join(REPO, "output", "global-cards")
os.makedirs(OUTPUT, exist_ok=True)

W, H = 1080, 1350

# ═══════════════════════════════════════════════════════
# 10가지 글로벌 콘텐츠 (다양한 주제)
# ═══════════════════════════════════════════════════════
POSTS = [
    {
        "theme": "self-worth",
        "quote_en": "You were never meant\nto earn your worth.\nIt was given to you.",
        "quote_kr": "당신의 가치는\n증명하는 것이 아니라\n이미 주어진 것입니다.",
        "body": "We spend years trying to prove we're enough — to parents, bosses, even ourselves. But what if worth isn't something you earn? What if it was placed inside you before you ever achieved a single thing?",
        "body_kr": "우리는 충분하다는 것을 증명하려고 수년을 보냅니다. 하지만 당신의 가치가 성취 이전에 이미 존재하는 것이라면요?",
        "hashtags": "#selfworth #youareenough #mentalhealth #healing #motivation #selflove #innerpeace #identity #worthit #lighthouse",
        "colors": [(45, 38, 65), (25, 20, 42)],  # deep purple
        "accent": (200, 170, 255),
    },
    {
        "theme": "rest",
        "quote_en": "Rest is not\na reward for\nfinishing.\nIt's fuel for\nbeginning.",
        "quote_kr": "쉼은 끝낸 자의 보상이 아니라\n시작하는 자의 연료입니다.",
        "body": "Hustle culture taught us that rest is weakness. But the most creative minds in history knew: restoration isn't laziness — it's strategy. You can't pour from an empty cup.",
        "body_kr": "쉬는 것은 약함이 아닙니다. 빈 컵으로는 아무것도 줄 수 없습니다.",
        "hashtags": "#rest #burnoutrecovery #selfcare #mentalhealth #productivity #wellness #balance #mindfulness #restoration #lighthouse",
        "colors": [(20, 45, 45), (10, 25, 28)],  # deep teal
        "accent": (130, 220, 200),
    },
    {
        "theme": "courage",
        "quote_en": "Courage is not\nthe absence of fear.\nIt's one more step\nwhile shaking.",
        "quote_kr": "용기란 두려움이 없는 것이 아니라\n떨리는 중에도 한 발 더 내딛는 것입니다.",
        "body": "Every brave person you admire was terrified before they acted. The difference? They moved anyway. Your next breakthrough is hiding behind the thing you're most afraid of.",
        "body_kr": "당신이 존경하는 모든 용감한 사람도 행동 전에는 두려웠습니다. 차이는 하나, 그래도 움직였다는 것.",
        "hashtags": "#courage #bravery #fear #growth #mindset #motivation #inspiration #strength #keepgoing #lighthouse",
        "colors": [(50, 30, 20), (28, 15, 10)],  # warm dark brown
        "accent": (240, 180, 100),
    },
    {
        "theme": "forgiveness",
        "quote_en": "Forgiveness\nis not saying\n'it was okay.'\nIt's saying\n'I won't carry\nthis anymore.'",
        "quote_kr": "용서는 '괜찮았어'가 아니라\n'더 이상 이것을 짊어지지 않겠어'\n라는 선언입니다.",
        "body": "Holding onto resentment is like drinking poison and waiting for the other person to get sick. Letting go isn't about them — it's about freeing yourself.",
        "body_kr": "분노를 붙잡고 있는 것은 독을 마시면서 상대가 아프기를 기다리는 것과 같습니다.",
        "hashtags": "#forgiveness #lettinggo #healing #peace #freedom #mentalhealth #growth #innerpeace #emotional #lighthouse",
        "colors": [(40, 35, 55), (20, 18, 35)],  # muted indigo
        "accent": (180, 160, 220),
    },
    {
        "theme": "loneliness",
        "quote_en": "Feeling alone\nin a crowded room\nis a signal,\nnot a sentence.",
        "quote_kr": "사람들 속에서 외로움을 느끼는 것은\n판결이 아니라 신호입니다.",
        "body": "Loneliness isn't about the number of people around you. It's about the depth of connection. One real conversation can heal what a thousand surface-level interactions cannot.",
        "body_kr": "외로움은 주변 사람의 수가 아니라 연결의 깊이에 관한 것입니다. 진심 어린 대화 하나가 천 번의 피상적 만남보다 낫습니다.",
        "hashtags": "#loneliness #connection #belonging #mentalhealth #community #realfriends #vulnerability #human #together #lighthouse",
        "colors": [(25, 30, 50), (12, 15, 30)],  # midnight blue
        "accent": (140, 170, 230),
    },
    {
        "theme": "failure",
        "quote_en": "Failure is not\nthe opposite\nof success.\nIt's part of\nthe journey.",
        "quote_kr": "실패는 성공의 반대가 아니라\n여정의 일부입니다.",
        "body": "Edison failed 10,000 times. J.K. Rowling was rejected 12 times. Every 'no' brought them closer to 'yes.' Your failure isn't a dead end — it's a detour leading somewhere better.",
        "body_kr": "에디슨은 만 번 실패했고, 롤링은 12번 거절당했습니다. 당신의 실패는 막다른 길이 아니라 더 나은 곳으로 가는 우회로입니다.",
        "hashtags": "#failure #success #resilience #growth #nevergiveup #motivation #entrepreneur #mindset #comeback #lighthouse",
        "colors": [(45, 25, 25), (25, 12, 12)],  # deep red-brown
        "accent": (230, 140, 120),
    },
    {
        "theme": "gratitude",
        "quote_en": "Gratitude\ndoesn't change\nyour situation.\nIt changes\nyour eyes.",
        "quote_kr": "감사는 상황을 바꾸지 않습니다.\n당신의 시선을 바꿉니다.",
        "body": "Neuroscience confirms: gratitude literally rewires your brain. Just 3 things you're thankful for each day can shift your entire perspective. It's not about ignoring pain — it's about seeing what's also true.",
        "body_kr": "뇌과학이 증명합니다 — 매일 감사 3가지만 적어도 뇌가 변합니다. 고통을 무시하는 것이 아니라, 동시에 존재하는 좋은 것을 보는 것입니다.",
        "hashtags": "#gratitude #thankful #mindfulness #positivity #mentalhealth #perspective #growth #neuroscience #happiness #lighthouse",
        "colors": [(35, 40, 20), (18, 22, 10)],  # dark olive
        "accent": (200, 210, 130),
    },
    {
        "theme": "boundaries",
        "quote_en": "'No' is a\ncomplete sentence.\nYou don't owe\nanyone an\nexplanation.",
        "quote_kr": "'아니요'는 완전한 문장입니다.\n누구에게도 설명할 의무가 없습니다.",
        "body": "Setting boundaries isn't selfish — it's self-respect. The people who get upset when you set limits are the ones who benefited the most from you having none.",
        "body_kr": "경계를 세우는 것은 이기적인 것이 아니라 자기 존중입니다. 당신의 한계 설정에 화내는 사람이 바로 그 한계가 없어서 이득을 봤던 사람입니다.",
        "hashtags": "#boundaries #selfrespect #mentalhealth #toxicrelationships #healing #growth #selfcare #no #healthyrelationships #lighthouse",
        "colors": [(50, 35, 35), (28, 18, 18)],  # warm charcoal
        "accent": (220, 160, 160),
    },
    {
        "theme": "patience",
        "quote_en": "A seed doesn't\nbecome a tree\novernight.\nYour growth\nis happening\neven when you\ncan't see it.",
        "quote_kr": "씨앗이 하룻밤에 나무가 되지 않습니다.\n보이지 않아도 당신은 자라고 있습니다.",
        "body": "In a world of instant results, patience feels like punishment. But the deepest roots grow in the darkest soil. Trust the process — even when progress is invisible.",
        "body_kr": "즉각적 결과의 시대에 인내는 벌처럼 느껴집니다. 하지만 가장 깊은 뿌리는 가장 어두운 흙에서 자랍니다.",
        "hashtags": "#patience #growth #trust #process #motivation #mindset #seedtotree #invisible #faith #lighthouse",
        "colors": [(30, 38, 30), (15, 20, 15)],  # forest dark
        "accent": (150, 200, 140),
    },
    {
        "theme": "comparison",
        "quote_en": "Stop comparing\nyour chapter 1\nto someone else's\nchapter 20.",
        "quote_kr": "당신의 1장을\n누군가의 20장과\n비교하지 마세요.",
        "body": "Social media shows highlight reels, not behind-the-scenes. That person you envy? They cried in their car last Tuesday. Everyone is fighting battles you can't see. Run your own race.",
        "body_kr": "SNS는 하이라이트만 보여줍니다. 당신이 부러워하는 그 사람도 지난 화요일 차에서 울었을 수 있습니다. 자기만의 레이스를 뛰세요.",
        "hashtags": "#comparison #beyourself #socialmedia #authenticity #journey #growth #selflove #ownpath #unique #lighthouse",
        "colors": [(40, 30, 45), (22, 15, 28)],  # dark plum
        "accent": (210, 170, 220),
    },
]

# ═══════════════════════════════════════════════════════
# 프리미엄 디자인
# ═══════════════════════════════════════════════════════
def get_font(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_en_font(size, bold=True):
    paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return get_font(size, bold)

def text_w(d, text, f):
    bb = d.textbbox((0,0), text, font=f)
    return bb[2]-bb[0]

def text_h(d, text, f):
    bb = d.textbbox((0,0), text, font=f)
    return bb[3]-bb[1]

def create_premium_card(post, index):
    """프리미엄 글로벌 카드 생성"""
    color_top, color_bot = post['colors']
    accent = post['accent']

    # 배경 그라디언트 + 빛 효과
    img = Image.new('RGB', (W, H))
    px = img.load()
    random.seed(index * 17)

    for y in range(H):
        ratio = y / H
        r = int(color_top[0] + (color_bot[0]-color_top[0]) * ratio)
        g = int(color_top[1] + (color_bot[1]-color_top[1]) * ratio)
        b = int(color_top[2] + (color_bot[2]-color_top[2]) * ratio)
        for x in range(W):
            px[x, y] = (r, g, b)

    # 빛 효과 (우상단)
    cx, cy = int(W*0.8), int(H*0.15)
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x-cx)**2 + (y-cy)**2)
            if dist < 500:
                intensity = (1-dist/500)**3 * 0.3
                r2,g2,b2 = px[x,y]
                px[x,y] = (min(255,r2+int(accent[0]*intensity)),
                           min(255,g2+int(accent[1]*intensity)),
                           min(255,b2+int(accent[2]*intensity)))

    # 미세 노이즈
    for _ in range(W*H//10):
        sx, sy = random.randint(0,W-1), random.randint(0,H-1)
        v = random.randint(-3,3)
        r3,g3,b3 = px[sx,sy]
        px[sx,sy] = (max(0,min(255,r3+v)), max(0,min(255,g3+v)), max(0,min(255,b3+v)))

    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    d = ImageDraw.Draw(img)

    # 상단 악센트 라인
    d.rectangle([0, 0, W, 4], fill=accent)

    # 브랜드 상단
    d.text((60, 35), "LIGHTHOUSE MEDIA", font=get_en_font(14, True), fill=(*accent, 180))
    theme_text = post['theme'].upper()
    tw = text_w(d, theme_text, get_en_font(14, True))
    d.text((W-60-tw, 35), theme_text, font=get_en_font(14, True), fill=(150,150,160))

    # 구분선
    d.line([(60, 65), (W-60, 65)], fill=(*accent[:3],), width=1)

    # 영문 대형 인용구
    y = 110
    f_quote = get_en_font(52, True)
    for line in post['quote_en'].split('\n'):
        # 텍스트 그림자
        d.text((62, y+2), line, font=f_quote, fill=(0,0,0))
        d.text((60, y), line, font=f_quote, fill=(255,255,255))
        _, lh = text_h(d, line, f_quote), 0
        bb = d.textbbox((0,0), line, font=f_quote)
        y += bb[3]-bb[1] + 12

    # 한국어 번역
    y += 25
    d.line([(60, y), (120, y)], fill=accent, width=2)
    y += 18
    f_kr = get_font(22, False)
    for line in post['quote_kr'].split('\n'):
        d.text((60, y), line, font=f_kr, fill=(*accent,))
        bb = d.textbbox((0,0), line, font=f_kr)
        y += bb[3]-bb[1] + 8

    # 본문 영어
    y += 35
    d.line([(60, y), (W-60, y)], fill=(80,80,90), width=1)
    y += 25
    f_body = get_en_font(20, False)
    body = post['body']
    # 줄바꿈 (45자)
    words = body.split(' ')
    lines = []
    current = ''
    for w in words:
        if len(current + ' ' + w) > 45:
            lines.append(current.strip())
            current = w
        else:
            current += ' ' + w
    if current: lines.append(current.strip())

    for line in lines[:6]:
        d.text((60, y), line, font=f_body, fill=(190, 190, 200))
        y += 30

    # 한국어 본문
    y += 15
    f_kr_body = get_font(18, False)
    kr_body = post['body_kr']
    kr_remaining = kr_body
    kr_lines = 0
    while kr_remaining and kr_lines < 3:
        if len(kr_remaining) <= 35:
            d.text((60, y), kr_remaining, font=f_kr_body, fill=(140,140,155))
            y += 28; break
        cut = kr_remaining[:35].rfind(' ')
        if cut < 8: cut = 35
        d.text((60, y), kr_remaining[:cut], font=f_kr_body, fill=(140,140,155))
        y += 28; kr_remaining = kr_remaining[cut:].lstrip(); kr_lines += 1

    # 하단 악센트 라인
    d.rectangle([0, H-4, W, H], fill=accent)

    # 하단 브랜드
    d.text((60, H-75), "Lighthouse Media", font=get_en_font(16, True), fill=(180,180,190))
    d.text((60, H-50), "@lighthouse_media77", font=get_en_font(13, False), fill=(120,120,130))

    # 우하단 로고 텍스트
    logo = "✦"
    lw = text_w(d, logo, get_font(28, True))
    d.text((W-60-lw, H-70), logo, font=get_font(28, True), fill=accent)

    return img

def build_caption(post):
    """글로벌 캡션"""
    quote_clean = post['quote_en'].replace('\n', ' ')
    caption = f"✦ {quote_clean}\n\n"
    caption += f"{post['body']}\n\n"
    caption += f"—\n\n"
    caption += f"{post['quote_kr'].replace(chr(10), ' ')}\n\n"
    caption += f"{post['body_kr']}\n\n"
    caption += f"—\n"
    caption += f"Lighthouse Media | @lighthouse_media77\n"
    caption += f"Follow for daily wisdom & healing\n\n"
    caption += post['hashtags']
    return caption

# ═══════════════════════════════════════════════════════
# 업로드 & 게시
# ═══════════════════════════════════════════════════════
def upload_imgur(path):
    for attempt in range(3):
        try:
            with open(path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                data={'image': enc, 'type': 'base64'}, timeout=30)
            url = r.json().get('data',{}).get('link')
            if url: return url
        except Exception as e:
            print(f"    Imgur attempt {attempt+1}: {e}")
        time.sleep(5)
    return None

def post_ig(image_url, caption):
    try:
        r = requests.post(f'https://graph.facebook.com/v21.0/{LH_IG_ID}/media',
            data={'image_url': image_url, 'caption': caption, 'access_token': LH_TOKEN}, timeout=30)
        cid = r.json().get('id')
        if not cid: print(f"    IG container fail: {r.json()}"); return None
        time.sleep(8)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{LH_IG_ID}/media_publish',
            data={'creation_id': cid, 'access_token': LH_TOKEN}, timeout=30)
        result = r2.json()
        if 'id' in result: print(f"    IG OK"); return result['id']
        print(f"    IG fail: {result}"); return None
    except Exception as e:
        print(f"    IG error: {e}"); return None

def post_fb(image_url, caption):
    try:
        r = requests.post(f'https://graph.facebook.com/v21.0/{LH_PAGE_ID}/photos',
            data={'url': image_url, 'message': caption[:500], 'access_token': LH_TOKEN}, timeout=30)
        data = r.json()
        if 'id' in data: print(f"    FB OK"); return data['id']
        print(f"    FB fail: {data}"); return None
    except Exception as e:
        print(f"    FB error: {e}"); return None

# ═══════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  Lighthouse Media — Global Premium Content")
    print("  10 posts | EN+KR | Diverse themes")
    print("=" * 55)

    for i, post in enumerate(POSTS):
        print(f"\n  [{i+1}/10] {post['theme'].upper()}")

        # 카드 생성
        card = create_premium_card(post, i)
        path = os.path.join(OUTPUT, f"global_{i+1:02d}_{post['theme']}.jpg")
        card.save(path, "JPEG", quality=95)
        print(f"    Card saved")

        # 캡션
        caption = build_caption(post)

        # 업로드 + 게시
        url = upload_imgur(path)
        if not url:
            print(f"    SKIP: Imgur failed"); continue

        post_ig(url, caption)
        time.sleep(3)
        post_fb(url, caption)
        time.sleep(8)  # rate limit 방지

        print(f"    Done: {post['theme']}")

    print(f"\n{'=' * 55}")
    print("  Complete! 10 global posts published.")
    print(f"{'=' * 55}")

if __name__ == '__main__':
    main()
