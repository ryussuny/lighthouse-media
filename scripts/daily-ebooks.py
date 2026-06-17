"""매일 전자책 생산: 무료 3권 + 유료 1권 → 깔끔한 HTML + SNS 내용 포함 게시 + 자동 발송"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, markdown
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# === CONFIG ===
HOME = os.path.expanduser("~")
TODAY = datetime.now().strftime("%Y-%m-%d")
EBOOK_DIR = os.path.join(HOME, "lighthouse-media", "dashboard", "public", "ebooks", TODAY)
os.makedirs(EBOOK_DIR, exist_ok=True)

API_KEY = ""
env_path = os.path.join(HOME, "lighthouse-media", ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding='utf-8'):
        if line.startswith("ANTHROPIC_API_KEY="):
            API_KEY = line.strip().split("=", 1)[1]

tokens_path = os.path.join(HOME, "lighthouse-media", "config", "tokens.json")
tokens = json.load(open(tokens_path, encoding='utf-8')) if os.path.exists(tokens_path) else {}
IG_TOKEN = tokens.get("instagram", "")
FB_TOKEN = tokens.get("facebook_page", "")
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

def claude(prompt, max_t=4096):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": max_t, "messages": [{"role": "user", "content": prompt}]})
    return r.json()["content"][0]["text"]

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def make_cover(title, subtitle, price, filename, color=(29, 158, 117)):
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), (16, 18, 32))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 6], fill=color)
    draw.ellipse([W-250, -80, W+80, 250], fill=(22, 26, 48))
    draw.ellipse([-100, H-250, 200, H+50], fill=(22, 26, 48))
    draw.text((60, 60), "LIGHTHOUSE MEDIA", font=gf(24), fill=color)
    badge_text = "FREE" if price == 0 else f"{price:,}won"
    badge_color = color if price == 0 else (186, 117, 23)
    draw.rounded_rectangle([60, 110, 60 + len(badge_text) * 12 + 30, 145], radius=10, fill=badge_color)
    draw.text((78, 115), badge_text, font=gf(20, True), fill=(255, 255, 255))
    y = 400
    for line in title.split("\n"):
        bb = draw.textbbox((0, 0), line, font=gf(52, True))
        draw.text(((W - (bb[2] - bb[0])) / 2, y), line, font=gf(52, True), fill=(255, 255, 255))
        y += bb[3] - bb[1] + 20
    y += 40
    for line in subtitle.split("\n"):
        bb = draw.textbbox((0, 0), line, font=gf(28))
        draw.text(((W - (bb[2] - bb[0])) / 2, y), line, font=gf(28), fill=(180, 180, 195))
        y += bb[3] - bb[1] + 12
    draw.text((W // 2 - 30, H - 120), "류선희", font=gf(26), fill=(120, 120, 140))
    draw.rectangle([W // 2 - 50, H - 60, W // 2 + 50, H - 56], fill=color)
    path = os.path.join(EBOOK_DIR, filename)
    img.save(path, "JPEG", quality=95)
    return path

def make_html(title, subtitle, md_content, price, slug):
    """마크다운을 깔끔한 HTML 전자책으로 변환"""
    is_free = price == 0
    accent = "#1D9E75" if is_free else "#BA7517"
    badge = "FREE EBOOK" if is_free else f"{price:,}원"
    badge_bg = accent
    bg_grad = "135deg,#1a1a2e,#16213e" if is_free else "135deg,#1a1a2e,#0f3460"

    # 마크다운 → HTML 변환
    body_html = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc'])

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title.replace(chr(10), ' ')} - Lighthouse Media</title>
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
  font-family: 'Pretendard', -apple-system, sans-serif;
  background: #FAF8F3;
  color: #333;
  line-height: 2.0;
  font-size: 16px;
  max-width: 680px;
  margin: 0 auto;
  padding: 40px 28px 80px;
  word-break: keep-all;
}}

/* 커버 */
.cover {{
  background: linear-gradient({bg_grad});
  color: #fff;
  padding: 70px 40px;
  border-radius: 20px;
  text-align: center;
  margin-bottom: 50px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.2);
}}
.cover h1 {{ font-size: 30px; line-height: 1.4; margin-bottom: 14px; font-weight: 800; }}
.cover .sub {{ color: {accent}; font-size: 17px; line-height: 1.6; }}
.cover .author {{ color: #888; margin-top: 24px; font-size: 14px; }}
.badge {{
  display: inline-block;
  background: {badge_bg};
  color: #fff;
  padding: 5px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 20px;
}}

/* 본문 타이포그래피 */
h1 {{
  font-size: 26px;
  font-weight: 800;
  color: #1a1a2e;
  margin: 48px 0 20px;
  line-height: 1.4;
}}
h2 {{
  font-size: 22px;
  font-weight: 700;
  color: {accent};
  margin: 44px 0 18px;
  padding: 14px 0 14px 16px;
  border-left: 4px solid {accent};
  background: rgba(29,158,117,0.03);
  border-radius: 0 8px 8px 0;
  line-height: 1.4;
}}
h3 {{
  font-size: 18px;
  font-weight: 700;
  color: #2a2a2a;
  margin: 32px 0 14px;
  line-height: 1.5;
}}
p {{
  margin-bottom: 18px;
  font-size: 16px;
  line-height: 2.0;
  color: #444;
  letter-spacing: -0.2px;
}}
strong {{ color: #1a1a2e; font-weight: 700; }}
em {{ color: {accent}; font-style: normal; font-weight: 600; }}

/* 리스트 */
ul, ol {{
  margin: 14px 0 20px 24px;
  line-height: 2.0;
}}
li {{
  margin-bottom: 10px;
  padding-left: 4px;
  color: #444;
}}
li strong {{ color: #2a2a2a; }}

/* 구분선 */
hr {{
  border: none;
  height: 1px;
  background: linear-gradient(90deg, transparent, #ddd, transparent);
  margin: 36px 0;
}}

/* 인용 */
blockquote {{
  border-left: 3px solid {accent};
  background: rgba(29,158,117,0.04);
  padding: 16px 20px;
  margin: 20px 0;
  border-radius: 0 10px 10px 0;
  font-size: 15px;
  color: #555;
  line-height: 1.9;
}}

/* 테이블 */
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 14px;
}}
th {{
  background: {accent};
  color: #fff;
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
}}
td {{
  padding: 10px 14px;
  border-bottom: 1px solid #eee;
}}
tr:nth-child(even) td {{ background: #f9f9f6; }}

/* 코드 블록 (체크리스트 등) */
code {{
  background: #f0ede6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
  color: {accent};
}}
pre {{
  background: #1a1a2e;
  color: #e0e0e0;
  padding: 20px;
  border-radius: 12px;
  overflow-x: auto;
  margin: 20px 0;
  line-height: 1.7;
  font-size: 14px;
}}

/* PDF 저장 버튼 */
.toolbar {{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(250,248,243,0.95);
  padding: 10px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  z-index: 100;
  backdrop-filter: blur(8px);
}}
.toolbar .brand {{ font-size: 13px; color: #999; font-weight: 600; }}
.toolbar .btn {{
  background: {accent};
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
}}
.toolbar .btn:hover {{ opacity: 0.9; }}

/* CTA (무료 전자책 하단) */
.cta-box {{
  background: linear-gradient(135deg, rgba(29,158,117,0.08), rgba(186,117,23,0.06));
  border: 1px solid rgba(29,158,117,0.2);
  border-radius: 14px;
  padding: 30px;
  margin-top: 40px;
  text-align: center;
}}
.cta-box h3 {{ color: #1a1a2e; margin-bottom: 8px; }}
.cta-box p {{ font-size: 14px; color: #888; margin-bottom: 16px; }}
.cta-box a {{
  display: inline-block;
  background: {accent};
  color: #fff;
  padding: 12px 28px;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 700;
}}

/* 푸터 */
.footer {{
  text-align: center;
  margin-top: 50px;
  padding-top: 30px;
  border-top: 1px solid #eee;
  font-size: 13px;
  color: #aaa;
  line-height: 1.8;
}}

/* 인쇄 */
@media print {{
  .toolbar, .cta-box {{ display: none; }}
  body {{ max-width: 100%; padding: 20px; font-size: 14px; }}
  h2 {{ page-break-before: always; }}
  p, li {{ orphans: 3; widows: 3; }}
}}

/* 모바일 */
@media (max-width: 600px) {{
  body {{ padding: 20px 16px 60px; font-size: 15px; }}
  .cover {{ padding: 50px 24px; }}
  .cover h1 {{ font-size: 24px; }}
  h2 {{ font-size: 19px; }}
}}
</style>
</head>
<body>

<div class="toolbar">
  <span class="brand">Lighthouse Media</span>
  <button class="btn" onclick="window.print()">PDF로 저장</button>
</div>

<div style="height:50px"></div>

<div class="cover">
  <span class="badge">{badge}</span>
  <h1>{title.replace(chr(10), '<br>')}</h1>
  <p class="sub">{subtitle.replace(chr(10), ' | ')}</p>
  <div class="author">류선희 | Lighthouse Media</div>
</div>

{body_html}

{"<div class='cta-box'><h3>더 깊은 내용이 궁금하다면</h3><p>유료 전자책에서 실전 가이드를 만나보세요</p><a href=\"/shop.html\">전자책 보러가기</a></div>" if is_free else ""}

<div class="footer">
  <strong>Lighthouse Media</strong><br>
  류선희 | 실제로 삶이 나아지는 콘텐츠<br>
  <a href="/free.html" style="color:{accent};text-decoration:none;">무료 PDF 더 받기</a>
</div>

</body>
</html>"""

    path = os.path.join(EBOOK_DIR, f"{'free' if is_free else 'paid'}-{slug}.html")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path

def upload_imgur(path, retries=3):
    with open(path, 'rb') as f:
        d = base64.b64encode(f.read()).decode()
    for attempt in range(retries):
        try:
            r = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': d, 'type': 'base64'}, timeout=30)
            url = r.json().get('data', {}).get('link')
            if url: return url
            print(f"    Imgur attempt {attempt+1}: {r.json().get('data',{}).get('error','unknown')}")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"    Imgur attempt {attempt+1}: {e}")
        time.sleep(5 * (attempt + 1))
    return None

def post_ig(img_url, caption, retries=2):
    if not IG_TOKEN: return None
    for attempt in range(retries):
        try:
            r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url': img_url, 'caption': caption, 'access_token': IG_TOKEN}, timeout=30)
            d = r.json()
            if 'id' not in d:
                err_code = d.get('error',{}).get('code', 0)
                err_msg = d.get('error',{}).get('message','unknown')
                print(f"    IG container fail: {err_msg}")
                if err_code == 4:  # rate limit
                    wait = 120 * (attempt + 1)
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return None
            time.sleep(8)
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id': d['id'], 'access_token': IG_TOKEN}, timeout=30)
            return r2.json().get('id')
        except Exception as e:
            print(f"    IG error: {e}")
    return None

def post_fb(msg, img_url):
    if not FB_TOKEN: return {}
    data = {'message': msg, 'access_token': FB_TOKEN}
    if img_url:
        data['url'] = img_url
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data=data)
    else:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/feed', data=data)
    return r.json()

# === MAIN ===
def main():
    print("=" * 60)
    print(f"  LIGHTHOUSE MEDIA - Ebook Factory + Auto Delivery")
    print(f"  {TODAY} | Free x3 + Paid x1 (7,900won)")
    print("=" * 60)

    # 1. 주제 생성
    print("\n[1] Generating topics...")
    topics_raw = claude(f"""오늘: {TODAY}
타겟: 20-40대 한국 직장인, 번아웃/자기계발/마음관리
브랜드: Lighthouse Media (대표: 류선희)

오늘의 전자책 4권 주제를 JSON으로 만들어줘:
{{"free": [
  {{"title": "2줄제목\\n각10자이내", "subtitle": "2줄부제\\n각15자이내", "slug": "english-slug", "summary": "인스타/페이스북에 올릴 핵심 내용 요약 3줄 (각 줄 공감가는 문장)"}},
  ... (3개)
], "paid": {{
  "title": "2줄제목", "subtitle": "2줄부제", "slug": "english-slug", "price": 7900, "summary": "핵심 내용 요약 5줄"
}}}}

주제 방향:
- 무료1: 아침/시작 관련
- 무료2: 감정/마음 관련
- 무료3: 저녁/회복 관련
- 유료: 종합 에너지/생산성 관련

한국어로 작성. 실용적이고 따뜻한 톤.""")

    start = topics_raw.find("{")
    end = topics_raw.rfind("}") + 1
    topics = json.loads(topics_raw[start:end])

    all_books = []

    # 2. 무료 3권
    for i, t in enumerate(topics["free"]):
        title = t['title']
        subtitle = t.get('subtitle', t.get('sub', ''))
        slug = t['slug']
        summary = t.get('summary', '')
        print(f"\n[FREE {i+1}/3] {title.split(chr(10))[0] if chr(10) in title else title[:20]}")

        content = claude(f"""전자책을 한국어로 작성해줘.

제목: {title}
부제: {subtitle}
저자: 류선희 (Lighthouse Media)
분량: 7페이지 (약 3,500자)
타겟: 매일 지치는 20-40대 직장인

구조:
- 5챕터 (각 챕터 600자)
- 각 챕터에 구체적 실천법 포함
- 마지막에 7일 실천 체크리스트
- 마크다운 형식

톤: 따뜻하고 지적이며 실용적
금지: 과장, 선동, "인생이 바뀝니다"

중요: 깔끔한 마크다운으로 작성. ## 으로 챕터 구분.""", max_t=3500)

        html_path = make_html(title, subtitle, content, 0, slug)
        cover = make_cover(title, subtitle, 0, f"cover-free-{slug}.jpg")
        all_books.append({"type": "free", "title": title, "slug": slug, "cover": cover, "html": html_path, "summary": summary, "subtitle": subtitle})
        print(f"  Done!")
        time.sleep(2)

    # 3. 유료 1권
    pt = topics["paid"]
    title = pt['title']
    subtitle = pt.get('subtitle', pt.get('sub', ''))
    slug = pt['slug']
    summary = pt.get('summary', '')
    price = pt.get('price', 7900)
    print(f"\n[PAID] {title.split(chr(10))[0] if chr(10) in title else title[:20]} - {price:,}won")

    content = claude(f"""유료 전자책을 한국어로 작성해줘.

제목: {title}
부제: {subtitle}
저자: 류선희 (Lighthouse Media)
가격: {price:,}원
분량: 30페이지 (약 15,000자)
타겟: 매일 지치는 20-40대 직장인

구조:
- 8챕터 (각 1,800자)
- 각 챕터에 연구/사례 인용
- 구체적 실천 방법 포함
- 마지막 챕터: 30일 실천 워크시트 (체크리스트+질문)
- 마크다운 형식

톤: 따뜻하고 지적이며 실용적. 권위있는 전문가.
금지: 과장, 선동

중요: 깔끔한 마크다운. ## 으로 챕터 구분.""", max_t=4096)

    html_path = make_html(title, subtitle, content, price, slug)
    cover = make_cover(title, subtitle, price, f"cover-paid-{slug}.jpg", (186, 117, 23))
    all_books.append({"type": "paid", "title": title, "slug": slug, "cover": cover, "html": html_path, "price": price, "summary": summary, "subtitle": subtitle})
    print(f"  Done!")

    # 4. SNS 게시 (내용 포함)
    print(f"\n{'=' * 60}")
    print(f"  Posting to SNS with content preview...")
    print(f"{'=' * 60}")

    base_url = "https://construction-appointments-recall-axis.trycloudflare.com"

    for book in all_books:
        title_flat = book['title'].replace('\n', ' ')
        is_free = book['type'] == 'free'
        summary = book.get('summary', '')

        img_url = upload_imgur(book['cover'])
        if not img_url:
            print(f"  {title_flat[:20]}: Imgur fail")
            continue
        time.sleep(2)

        # 인스타 캡션 (내용 포함)
        ebook_url = f"/ebooks/{TODAY}/{'free' if is_free else 'paid'}-{book['slug']}.html"
        price_line = "무료 전자책" if is_free else f"전자책 {book.get('price', 7900):,}원"

        ig_caption = f"""{title_flat}

{summary}

{price_line}
링크인바이오에서 바로 읽을 수 있습니다.

류선희 | Lighthouse Media
"실제로 삶이 나아지는 콘텐츠"

#전자책 #무료전자책 #자기계발 #직장인 #번아웃회복 #마음관리 #힐링 #라이트하우스미디어 #습관형성 #에너지관리 #워라밸 #직장인힐링 #멘탈관리 #자기관리 #감정관리"""

        ig = post_ig(img_url, ig_caption)
        print(f"  [{book['type'].upper()}] {title_flat[:25]} - IG:{'OK' if ig else 'SKIP'}", end="")
        time.sleep(30)  # 인스타 rate limit 방지: 게시 간격 30초

        # 페이스북 (내용 포함)
        fb_msg = f"""[{price_line}] {title_flat}

{summary}

지금 바로 읽어보세요.
류선희 | Lighthouse Media"""

        fb = post_fb(fb_msg, img_url)
        print(f" FB:{'OK' if 'id' in fb or 'post_id' in fb else 'SKIP'}")
        time.sleep(3)

    # 5. 인덱스 저장
    idx = {
        "date": TODAY,
        "books": [{
            "type": b["type"],
            "title": b["title"],
            "subtitle": b.get("subtitle", ""),
            "slug": b["slug"],
            "price": b.get("price", 0),
            "url": f"/ebooks/{TODAY}/{'free' if b['type'] == 'free' else 'paid'}-{b['slug']}.html",
        } for b in all_books]
    }
    with open(os.path.join(EBOOK_DIR, "index.json"), 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

    # 6. 리드에게 자동 발송 (이메일 목록에 새 전자책 알림)
    leads_path = os.path.join(HOME, "lighthouse-media", "data", "leads.json")
    if os.path.exists(leads_path):
        leads = json.load(open(leads_path, encoding='utf-8'))
        print(f"\n  Leads DB: {len(leads)}명 등록됨")
        # TODO: 이메일 발송 시스템 연동 시 여기서 자동 발송

    print(f"\n{'=' * 60}")
    print(f"  {len(all_books)} ebooks created + posted!")
    for b in all_books:
        p = f" ({b.get('price', 0):,}won)" if b.get('price') else " (FREE)"
        print(f"    {b['title'].replace(chr(10), ' ')}{p}")
    print(f"  Location: /ebooks/{TODAY}/")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
