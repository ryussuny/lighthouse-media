"""사무엘하 1장부터 전체 포스터 일괄 생성 + 인스타/페이스북 게시"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, math, random, time, base64, requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
TOKEN = tokens.get('church_page', tokens['instagram'])
IG_ID = tokens.get('church_ig_id', '')
PAGE_ID = tokens.get('church_page_id', '')
IMGUR_ID = "546c25a59c58ad7"

W, H = 1080, 1350
WEEKDAYS = ['월','화','수','목','금','토','일']

# 폰트
def font(size, bold=True):
    p = 'C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf'
    return ImageFont.truetype(p, size)

def font_serif(size):
    for p in ['C:/Windows/Fonts/NanumMyeongjoBold.ttf', 'C:/Windows/Fonts/batang.ttc']:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: continue
    return font(size)

# 타이틀 줄 분리
def split_title(title):
    """타이틀을 2~3줄로 분리, 마지막 줄은 골드"""
    # 긴 대시 처리
    title = title.replace(' — ', '\n').replace('—', '\n')

    words = title.split()
    if len(words) <= 2:
        return [(title, False)]

    lines = []
    if len(title) <= 10:
        lines = [(title, True)]
    elif len(title) <= 16:
        mid = len(words) // 2
        lines = [(' '.join(words[:mid]), False), (' '.join(words[mid:]), True)]
    else:
        # 3줄로 분리
        total = len(words)
        if total <= 3:
            for i, w in enumerate(words):
                lines.append((w, i == total - 1))
        elif total <= 5:
            lines = [
                (' '.join(words[:2]), False),
                (' '.join(words[2:-1]), False),
                (words[-1], True),
            ]
        else:
            third = total // 3
            lines = [
                (' '.join(words[:third]), False),
                (' '.join(words[third:third*2]), False),
                (' '.join(words[third*2:]), True),
            ]

    # 빈 줄 제거
    lines = [(l, g) for l, g in lines if l.strip()]
    # 마지막 줄은 반드시 골드
    if lines:
        lines[-1] = (lines[-1][0], True)
    return lines

# 키 메시지
KEY_MESSAGES = {
    "삼하 1:1-10": "내 손에 든 것이\n하나님의 것인가, 내 것인가.",
    "삼하 1:11-16": "하나님과 같은 마음으로\n슬퍼할 줄 아는 것이 믿음입니다.",
    "삼하 1:17-27": "슬픔을 노래로 바꾸는 것,\n그것이 신앙의 힘입니다.",
    "삼하 2:1-7": "결정하기 전에\n하나님께 먼저 묻는 것이 지혜입니다.",
    "삼하 2:8-17": "전쟁의 시작보다 중요한 것은\n하나님의 뜻입니다.",
    "삼하 2:18-32": "싸우는 것보다\n멈추는 것이 더 큰 용기입니다.",
    "삼하 3:1-21": "하나님의 저울은\n우리의 것과 다릅니다.",
    "삼하 3:22-39": "의로움과 정의 사이에서\n하나님의 마음을 구합니다.",
    "삼하 4:1-12": "하나님의 이름으로 포장한\n인간의 욕심을 경계합니다.",
    "삼하 5:1-5": "기다림 끝에\n하나님이 열어주시는 문이 있습니다.",
    "삼하 5:6-16": "하나님이 택하신 곳에\n하나님의 역사가 시작됩니다.",
    "삼하 5:17-25": "어제의 방법이 아닌\n오늘의 하나님을 구해야 합니다.",
    "삼하 6:1-11": "하나님의 거룩함 앞에서는\n선한 의도만으로는 충분하지 않습니다.",
}

# 챕터 번호 추출
def get_chapter(ref):
    import re
    m = re.search(r'(\d+):', ref)
    return int(m.group(1)) if m else 1

def create_poster(entry, idx, total_entries):
    """포스터 생성"""
    ref = entry['ref']
    title = entry['title']
    date_str = entry['date']
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    day_kr = WEEKDAYS[dt.weekday()]
    date_kr = dt.strftime('%m/%d')
    chapter = get_chapter(ref)
    series_num = str(idx + 1).zfill(2)

    # 배경 - 시드를 바꿔서 매번 약간 다른 느낌
    random.seed(hash(ref))
    img = Image.new('RGB', (W, H))
    pixels = img.load()

    # 약간씩 다른 색조
    hue_shift = random.randint(-5, 5)
    for y in range(H):
        for x in range(W):
            ratio_y = y / H
            ratio_x = x / W
            mix = ratio_y * 0.7 + ratio_x * 0.3
            r = int(25 + hue_shift + (15 - 25) * mix)
            g = int(28 + (13 - 28) * mix)
            b = int(48 - hue_shift + (30 - 48) * mix)

            light_cx = W * (0.65 + random.random() * 0.1)
            light_cy = H * (0.12 + random.random() * 0.05)
            dist = math.sqrt((x - light_cx)**2 + (y - light_cy)**2)
            light = max(0, 1 - dist / 500) * 0.22
            r = min(255, int(r + light * 55))
            g = min(255, int(g + light * 50))
            b = min(255, int(b + light * 65))
            pixels[x, y] = (max(0,r), max(0,g), max(0,b))

    d = ImageDraw.Draw(img)

    # 십자가 (우측 상단)
    cross_cx = int(W * (0.68 + random.random() * 0.1))
    cross_cy = int(H * (0.12 + random.random() * 0.05))
    for dy in range(-110, 111):
        alpha = max(0, 1 - abs(dy)/110) * 0.1
        c = int(180 * alpha)
        d.point((cross_cx, cross_cy + dy), fill=(90+c, 90+c, 120+c))
    for dx in range(-65, 66):
        alpha = max(0, 1 - abs(dx)/65) * 0.1
        c = int(180 * alpha)
        d.point((cross_cx + dx, cross_cy - 25), fill=(90+c, 90+c, 120+c))

    # 별
    for _ in range(35):
        sx, sy = random.randint(40, W-40), random.randint(25, H-180)
        sz = random.choice([1,1,1,2])
        br = random.randint(110, 210)
        d.ellipse([sx,sy,sx+sz,sy+sz], fill=(br,br,br+15))

    WHITE = (255, 255, 255)
    GOLD = (218, 175, 70)
    LIGHT_GRAY = (180, 180, 190)
    DIM_GRAY = (130, 130, 140)

    # 시리즈 라벨
    d.text((70, 80), f'사무엘하  ·  SERMON SERIES {series_num}', font=font(20), fill=GOLD)
    d.text((70, 120), f'사무엘하 {chapter}장', font=font(22, False), fill=LIGHT_GRAY)

    # 메인 타이틀
    title_lines = split_title(title)
    title_y = 240

    # 폰트 사이즈 결정 (긴 제목은 작게)
    max_line_len = max(len(l) for l, _ in title_lines) if title_lines else 10
    if max_line_len <= 6:
        fsize = 100
    elif max_line_len <= 9:
        fsize = 90
    elif max_line_len <= 12:
        fsize = 80
    else:
        fsize = 68

    for text, is_gold in title_lines:
        color = GOLD if is_gold else WHITE
        f = font(fsize)
        d.text((70, title_y), text, font=f, fill=color)
        bb = d.textbbox((0,0), text, font=f)
        title_y += bb[3] - bb[1] + 12

    # 골드 라인
    title_y += 10
    d.rectangle([70, title_y, 300, title_y + 4], fill=GOLD)
    title_y += 30

    # BIBLE TEXT
    d.text((70, title_y), 'BIBLE TEXT', font=font(16), fill=DIM_GRAY)
    title_y += 28

    # ref를 풀네임으로
    ref_full = ref.replace('삼하', '사무엘하')
    d.text((70, title_y), ref_full, font=font(30), fill=WHITE)
    title_y += 45
    d.text((70, title_y), f'{dt.strftime("%Y")} · {date_kr}  {day_kr}요일  매일 묵상', font=font(16, False), fill=DIM_GRAY)

    # KEY MESSAGE 박스
    key_msg = KEY_MESSAGES.get(ref, f'"{title}"')
    box_x = 500
    box_y = title_y - 75
    box_w = W - 70
    box_h = title_y + 45
    d.rectangle([box_x, box_y, box_w, box_h], outline=GOLD, width=1)

    msg_lines = key_msg.split('\n')
    msg_y = box_y + 15
    for ml in msg_lines:
        d.text((box_x + 25, msg_y), f'"{ml}"' if msg_lines.index(ml) == 0 else ml, font=font_serif(17), fill=WHITE)
        msg_y += 30
    d.text((box_x + 25, msg_y + 8), '— KEY MESSAGE', font=font(12), fill=DIM_GRAY)

    # 교회 브랜딩
    d.text((70, H - 140), '동산감리교회', font=font(18), fill=LIGHT_GRAY)
    d.text((70, H - 112), '@garden___church', font=font(14, False), fill=DIM_GRAY)

    # 하단 골드
    d.rectangle([0, H - 18, W, H], fill=GOLD)

    return img


def create_caption(entry, idx):
    ref = entry['ref']
    title = entry['title']
    dt = datetime.strptime(entry['date'], '%Y-%m-%d')
    day_kr = WEEKDAYS[dt.weekday()]
    date_kr = dt.strftime('%m/%d')
    ref_full = ref.replace('삼하', '사무엘하')
    key_msg = KEY_MESSAGES.get(ref, title).replace('\n', ' ')
    chapter = get_chapter(ref)

    caption = f"""📖 {ref_full}
"{title}"

{key_msg}

사무엘하를 하루 한 장씩 읽으며,
다윗의 이야기 속에서 하나님의 마음을 만납니다.

✦ 오늘의 질문
"이 말씀이 오늘 나의 삶에서 어떤 의미가 있는가?"

✦ 오늘의 실천
오늘 하루 이 말씀을 마음에 품고,
한 가지 구체적인 순종의 행동을 실천합니다.

🙏 오늘의 기도
"하나님, 오늘 이 말씀대로 살아가게 하소서. 아멘."

동산감리교회
@garden___church

#오늘의말씀 #사무엘하 #사무엘하{chapter}장 #성경말씀 #묵상
#기도 #교회 #말씀카드 #동산감리교회 #매일묵상
#성경 #은혜 #거룩 #순종 #예배 #기독교 #하나님
#BibleVerse #DailyDevotional #ChurchLife"""
    return caption


def main():
    schedule = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "bible-schedule.json"), encoding='utf-8'))
    entries = [e for e in schedule if e['date'] <= '2026-05-05']

    OUT = os.path.join(HOME, "lighthouse-media", "output", "bible-cards", "posters")
    os.makedirs(OUT, exist_ok=True)

    print(f"총 {len(entries)}개 포스터 생성 + 게시")
    print("=" * 60)

    for idx, entry in enumerate(entries):
        ref = entry['ref']
        title = entry['title']
        print(f"\n[{idx+1}/{len(entries)}] {ref} - {title}")

        # 1. 포스터 생성
        img = create_poster(entry, idx, len(entries))
        path = os.path.join(OUT, f"poster_{entry['date']}.jpg")
        img.save(path, "JPEG", quality=96)
        print(f"  이미지 생성 OK")

        # 2. Imgur 업로드
        with open(path, 'rb') as f:
            enc = base64.b64encode(f.read()).decode()
        ir = requests.post('https://api.imgur.com/3/image',
            headers={'Authorization': f'Client-ID {IMGUR_ID}'},
            data={'image': enc, 'type': 'base64'})
        img_url = ir.json().get('data',{}).get('link')
        if not img_url:
            print(f"  Imgur FAIL: {ir.json()}")
            time.sleep(5)
            continue
        print(f"  Imgur OK: {img_url}")

        # 3. 캡션
        caption = create_caption(entry, idx)

        # 4. 인스타 게시
        if IG_ID:
            r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media',
                data={'image_url': img_url, 'caption': caption, 'access_token': TOKEN})
            if 'id' in r.json():
                time.sleep(8)
                r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
                    data={'creation_id': r.json()['id'], 'access_token': TOKEN})
                print(f"  IG: {'OK' if 'id' in r2.json() else r2.json()}")
            else:
                print(f"  IG Create FAIL: {r.json()}")

        # 5. 페이스북 게시
        if PAGE_ID:
            fb = requests.post(f'https://graph.facebook.com/v21.0/{PAGE_ID}/photos',
                data={'url': img_url, 'message': caption, 'access_token': TOKEN})
            print(f"  FB: {'OK' if 'id' in fb.json() else fb.json()}")

        # 레이트 리밋 방지
        if idx < len(entries) - 1:
            print(f"  대기 30초...")
            time.sleep(30)

    print(f"\n{'='*60}")
    print(f"완료! 총 {len(entries)}개 포스터 게시 완료")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
