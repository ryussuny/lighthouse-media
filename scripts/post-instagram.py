"""
Lighthouse Media — 인스타그램 자동 게시
카드뉴스 10장 생성 → 서버 업로드 → Instagram Graph API 캐러셀 게시
"""
import os
import sys
import time
import requests

# Windows 콘솔 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont

# === CONFIG ===
import json
_tokens = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "tokens.json"), encoding='utf-8'))
ACCESS_TOKEN = _tokens['instagram']
IG_USER_ID = "17841425580883266"
BASE_URL = os.environ.get("PUBLIC_URL", "https://construction-appointments-recall-axis.trycloudflare.com")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "dashboard", "public", "insta-images")

# 색상
MAIN = (29, 158, 117)       # #1D9E75
ACCENT = (186, 117, 23)     # #BA7517
DARK = (20, 22, 40)         # 다크 네이비
WHITE = (255, 255, 255)
LIGHT = (200, 200, 210)
BG = (250, 248, 243)        # #FAF8F3

W, H = 1080, 1350

def get_font(size, bold=False):
    """시스템 폰트 찾기"""
    font_paths = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf" if bold else "C:/Windows/Fonts/NanumGothic.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw_rounded_rect(draw, xy, fill, radius=20):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)

def draw_centered_text(draw, y, text, font, fill=WHITE, line_spacing=10):
    """여러 줄 텍스트 가운데 정렬"""
    lines = text.split("\n")
    total_h = 0
    line_sizes = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        line_sizes.append((lw, lh))
        total_h += lh + line_spacing

    cy = y
    for i, line in enumerate(lines):
        lw, lh = line_sizes[i]
        draw.text(((W - lw) / 2, cy), line, font=font, fill=fill)
        cy += lh + line_spacing

def make_slide_1():
    """후킹: 월요일이 두려운 당신에게"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # 배경 장식 - 큰 원
    draw.ellipse([W-300, -100, W+100, 300], fill=(25, 30, 55))
    draw.ellipse([-150, H-350, 250, H+50], fill=(25, 30, 55))

    # 상단 바
    draw.rectangle([0, 0, W, 6], fill=MAIN)

    # 브랜드
    small = get_font(28)
    draw.text((80, 80), "LIGHTHOUSE MEDIA", font=small, fill=MAIN)

    # 메인 텍스트
    big = get_font(72, bold=True)
    med = get_font(48, bold=True)

    draw_centered_text(draw, 400, "월요일이\n두려운\n당신에게", big, WHITE, 30)

    # 하단 서브텍스트
    sub = get_font(32)
    draw_centered_text(draw, 900, "87%의 직장인이 경험한 변화의 비밀", sub, LIGHT)

    # 하단 바
    draw.rectangle([W//2-60, H-120, W//2+60, H-116], fill=MAIN)

    # 페이지 번호
    tiny = get_font(24)
    draw.text((W-80, H-60), "1/10", font=tiny, fill=(100, 100, 120))

    return img

def make_slide_2():
    """공감: 이런 적 있으시죠?"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=MAIN)

    title = get_font(52, bold=True)
    draw_centered_text(draw, 80, "이런 적 있으시죠?", title, MAIN)

    items = [
        "일요일 밤,\n내일 생각에 잠이 안 온다",
        "월요일 아침 알람 소리가\n세상에서 가장 싫다",
        "업무 시간 내내\n퇴근 시간만 기다린다",
        "금요일 해방감이\n한 주의 유일한 기쁨이다",
    ]

    body = get_font(34, bold=True)
    num_font = get_font(44, bold=True)

    y = 230
    for i, item in enumerate(items):
        # 카드 배경
        draw_rounded_rect(draw, [80, y, W-80, y+200], (30, 33, 55), 16)
        # 번호
        draw.text((120, y+30), str(i+1), font=num_font, fill=MAIN)
        # 텍스트
        draw.text((200, y+40), item, font=get_font(30), fill=WHITE)
        y += 230

    tiny = get_font(24)
    draw.text((W-80, H-60), "2/10", font=tiny, fill=(100, 100, 120))
    return img

def make_slide_stat():
    """통계: 87%가 변했습니다"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=MAIN)

    title = get_font(48, bold=True)
    draw_centered_text(draw, 100, "실천한 직장인의 변화", title, WHITE)

    # 큰 숫자
    huge = get_font(160, bold=True)
    draw_centered_text(draw, 350, "87%", huge, MAIN)

    sub = get_font(36)
    draw_centered_text(draw, 580, "월요일 부담감이 줄었다", sub, LIGHT)

    # 추가 통계
    stats = [("72%", "업무 효율성 향상"), ("91%", "개인시간 확보 성공")]
    y = 750
    stat_font = get_font(56, bold=True)
    desc_font = get_font(28)
    for val, desc in stats:
        draw_rounded_rect(draw, [120, y, W-120, y+130], (30, 33, 55), 12)
        draw.text((180, y+20), val, font=stat_font, fill=ACCENT)
        draw.text((420, y+45), desc, font=desc_font, fill=LIGHT)
        y += 160

    tiny = get_font(24)
    draw.text((W-80, H-60), "3/10", font=tiny, fill=(100, 100, 120))
    return img

def make_secret_slide(num, title_text, body_text, page):
    """비밀 슬라이드 (4~8)"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=MAIN)

    # 번호 배지
    badge_font = get_font(28, bold=True)
    draw_rounded_rect(draw, [80, 80, 280, 130], MAIN, 25)
    draw.text((110, 85), f"SECRET {num}", font=badge_font, fill=WHITE)

    # 제목
    title = get_font(52, bold=True)
    draw_centered_text(draw, 250, title_text, title, WHITE, 20)

    # 구분선
    draw.rectangle([W//2-100, 480, W//2+100, 483], fill=MAIN)

    # 본문
    body = get_font(32)
    draw_centered_text(draw, 550, body_text, body, LIGHT, 15)

    # 하단 장식
    draw.ellipse([W//2-150, H-250, W//2+150, H-50], outline=MAIN, width=2)

    tiny = get_font(24)
    draw.text((W-80, H-60), f"{page}/10", font=tiny, fill=(100, 100, 120))
    return img

def make_slide_offer():
    """가격/오퍼 슬라이드"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=ACCENT)

    title = get_font(44, bold=True)
    draw_centered_text(draw, 100, "30일 워크시트 포함", title, ACCENT)

    sub = get_font(36)
    draw_centered_text(draw, 200, "읽고 끝이 아닌\n실천하는 전자책", sub, WHITE, 15)

    # 가격 박스
    draw_rounded_rect(draw, [120, 400, W-120, 750], (30, 33, 55), 20)

    old = get_font(36)
    new_price = get_font(80, bold=True)

    # 정가 (취소선 효과)
    draw_centered_text(draw, 430, "정가 24,900원", old, (120, 120, 130))
    draw.line([W//2-120, 455, W//2+120, 455], fill=(120, 120, 130), width=2)

    # 할인가
    draw_centered_text(draw, 520, "14,900원", new_price, MAIN)

    # 할인 배지
    badge = get_font(28, bold=True)
    draw_rounded_rect(draw, [W//2-60, 670, W//2+60, 710], ACCENT, 10)
    draw.text((W//2-45, 675), "40% OFF", font=badge, fill=WHITE)

    # 포함 내용
    items = ["전자책 60페이지 (10챕터)", "실천 워크시트", "7일 환불 보장"]
    item_font = get_font(30)
    y = 830
    for item in items:
        draw.text((180, y), f"  {item}", font=item_font, fill=LIGHT)
        # 체크마크
        draw.text((130, y), "✓", font=item_font, fill=MAIN)
        y += 60

    tiny = get_font(24)
    draw.text((W-80, H-60), "9/10", font=tiny, fill=(100, 100, 120))
    return img

def make_slide_cta():
    """CTA: 링크인바이오"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=MAIN)

    # 로고
    brand = get_font(32, bold=True)
    draw_centered_text(draw, 200, "LIGHTHOUSE MEDIA", brand, MAIN)

    # 메인 CTA
    big = get_font(56, bold=True)
    draw_centered_text(draw, 400, "링크인바이오에서\n다운로드", big, WHITE, 20)

    # 화살표/포인터
    draw_centered_text(draw, 620, "↓", get_font(80), MAIN)

    # CTA 버튼 모양
    draw_rounded_rect(draw, [200, 750, W-200, 840], MAIN, 16)
    btn = get_font(34, bold=True)
    draw_centered_text(draw, 762, "지금 바로 확인하기", btn, WHITE)

    # 저자
    author = get_font(28)
    draw_centered_text(draw, 950, "저자: 류선희", author, LIGHT)
    draw_centered_text(draw, 1000, "@lighthouse_media77", author, (100, 100, 120))

    tiny = get_font(24)
    draw.text((W-85, H-60), "10/10", font=tiny, fill=(100, 100, 120))
    return img

def generate_all_slides():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    slides = [
        make_slide_1(),
        make_slide_2(),
        make_slide_stat(),
        make_secret_slide(1, "관점의 전환", "'해야 하는 일'에서\n'성장의 기회'로\n바라보는 순간\n모든 것이 달라집니다", 4),
        make_secret_slide(2, "에너지 관리", "하루 15분 투자로\n만드는 지속가능한\n에너지 충전 루틴", 5),
        make_secret_slide(3, "80% 효율 법칙", "완벽주의를 내려놓으면\n오히려 만족도가\n올라갑니다", 6),
        make_secret_slide(4, "관계 에너지", "동료가 스트레스가 아닌\n동력이 되는\n소통의 기술", 7),
        make_secret_slide(5, "루틴의 힘", "의지력에 의존하지 않는\n자동화된\n성공 시스템", 8),
        make_slide_offer(),
        make_slide_cta(),
    ]

    paths = []
    for i, slide in enumerate(slides):
        path = os.path.join(OUTPUT_DIR, f"slide_{i+1:02d}.jpg")
        slide.save(path, "JPEG", quality=95)
        paths.append(path)
        print(f"  ✅ 슬라이드 {i+1}/10 저장: {path}")

    return paths

def post_carousel_to_instagram(image_urls, caption):
    """Instagram Graph API로 캐러셀 게시"""
    print(f"\n📸 인스타그램 캐러셀 게시 시작...")
    print(f"   이미지 {len(image_urls)}장")

    # Step 1: 각 이미지를 컨테이너로 등록
    container_ids = []
    for i, url in enumerate(image_urls):
        resp = requests.post(
            f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
            data={
                "image_url": url,
                "is_carousel_item": "true",
                "access_token": ACCESS_TOKEN,
            }
        )
        data = resp.json()
        if "id" in data:
            container_ids.append(data["id"])
            print(f"   ✅ 이미지 {i+1} 등록: {data['id']}")
        else:
            print(f"   ❌ 이미지 {i+1} 실패: {data}")
            return None

    # Step 2: 캐러셀 컨테이너 생성
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(container_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        }
    )
    carousel = resp.json()
    if "id" not in carousel:
        print(f"   ❌ 캐러셀 생성 실패: {carousel}")
        return None

    carousel_id = carousel["id"]
    print(f"   ✅ 캐러셀 생성: {carousel_id}")

    # Step 3: 게시 (publish)
    time.sleep(5)  # 처리 대기
    resp = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_USER_ID}/media_publish",
        data={
            "creation_id": carousel_id,
            "access_token": ACCESS_TOKEN,
        }
    )
    result = resp.json()
    if "id" in result:
        print(f"\n   🎉 게시 완료! 게시물 ID: {result['id']}")
        return result["id"]
    else:
        print(f"   ❌ 게시 실패: {result}")
        return None

def main():
    print("═══════════════════════════════════════════")
    print("  LIGHTHOUSE MEDIA — 인스타그램 자동 게시")
    print("═══════════════════════════════════════════\n")

    # 1. 이미지 생성
    print("▶ 카드뉴스 10장 생성 중...")
    paths = generate_all_slides()

    # 2. 공개 URL 생성
    image_urls = []
    for i in range(10):
        url = f"{BASE_URL}/insta-images/slide_{i+1:02d}.jpg"
        image_urls.append(url)

    print(f"\n▶ 공개 URL 확인: {image_urls[0]}")

    # URL 접근 테스트
    test = requests.head(image_urls[0], timeout=10)
    if test.status_code != 200:
        print(f"   ⚠️ URL 접근 불가 ({test.status_code}). 서버와 터널이 실행 중인지 확인하세요.")
        print(f"   로컬 이미지는 {OUTPUT_DIR}에 저장되었습니다.")
        return

    print(f"   ✅ URL 접근 가능 ({test.status_code})")

    # 3. 캡션
    caption = """월요일이 두려운 당신에게.

매주 일요일 밤, 내일 생각에 잠이 안 오시나요?
87%의 직장인이 이 5가지 비밀로 월요일이 달라졌습니다.

✓ 관점의 전환
✓ 에너지 관리법
✓ 80% 효율 법칙
✓ 관계 에너지
✓ 루틴의 힘

30일 실천 워크시트 포함 전자책
지금 링크인바이오에서 확인하세요.

—
류선희 | Lighthouse Media
"실제로 삶이 나아지는 콘텐츠"

#직장인자기계발 #번아웃회복 #월요병극복 #자기계발책추천 #직장인힐링 #마음관리 #직장인루틴 #에너지관리 #워라밸 #자기계발 #전자책추천 #직장인필독 #마인드셋 #습관형성 #라이트하우스미디어"""

    # 4. 게시
    post_id = post_carousel_to_instagram(image_urls, caption)

    if post_id:
        print(f"\n═══════════════════════════════════════════")
        print(f"  ✅ 인스타그램 게시 완료!")
        print(f"  📱 @lighthouse_media77 에서 확인하세요")
        print(f"═══════════════════════════════════════════")

if __name__ == "__main__":
    main()
