"""
Lighthouse Media — 매일 밤 9시 자동 콘텐츠 생성 + 업로드
인스타그램 + 페이스북 + 유튜브 숏츠 동시 게시
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, base64, subprocess, shutil
from datetime import datetime
from pathlib import Path

# === 경로 설정 ===
HOME = os.path.expanduser("~")
PROJECT = os.path.join(HOME, "lighthouse-media")
COWORK = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media")
OUTPUT = os.path.join(PROJECT, "output", datetime.now().strftime("%Y-%m-%d"))
FRAMES_DIR = os.path.join(OUTPUT, "frames")
LOG_DIR = os.path.join(PROJECT, "logs")
os.makedirs(OUTPUT, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ffmpeg 경로
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

# === API 설정 ===
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_KEY:
    env_path = os.path.join(PROJECT, ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("ANTHROPIC_API_KEY="):
                ANTHROPIC_KEY = line.strip().split("=", 1)[1]

IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_CLIENT_ID = "546c25a59c58ad7"

# 토큰 파일에서 읽기
TOKEN_FILE = os.path.join(PROJECT, "config", "tokens.json")
YT_TOKEN_FILE = os.path.join(COWORK, "token_lighthouse.json")
YT_SECRET_FILE = os.path.join(COWORK, "client_secret.json")

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        return json.load(open(TOKEN_FILE))
    return {}

def save_tokens(tokens):
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    json.dump(tokens, open(TOKEN_FILE, 'w'), indent=2)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

# === 1. Claude로 오늘의 콘텐츠 생성 ===
def generate_content():
    import requests as req
    log("콘텐츠 생성 시작 (Claude API)...")

    today = datetime.now().strftime("%Y년 %m월 %d일 %A")

    # 다양한 글로벌 주제 풀 (매일 다른 주제)
    import hashlib
    themes = [
        "self-worth & identity", "rest & recovery", "courage & fear",
        "forgiveness & letting go", "loneliness & connection", "failure & resilience",
        "gratitude & perspective", "boundaries & self-respect", "patience & growth",
        "comparison & authenticity", "grief & healing", "purpose & meaning",
        "relationships & trust", "change & adaptation", "hope & perseverance",
        "anger & peace", "perfectionism & grace", "leadership & humility",
        "creativity & expression", "kindness & compassion", "silence & reflection",
        "regret & redemption", "joy & contentment", "vulnerability & strength",
        "aging & wisdom", "money & true wealth", "dreams & action",
        "parenting & legacy", "friendship & loyalty", "simplicity & focus"
    ]
    day_index = int(hashlib.md5(today.encode()).hexdigest()[:8], 16) % len(themes)
    today_theme = themes[day_index]

    prompt = f"""You are the Content Director for Lighthouse Media (CEO: Sunhee Ryu).
Today: {today}
Today's theme: {today_theme}

TARGET: Global audience (25-45), professionals dealing with life challenges
TONE: Warm, intelligent, practical. No exaggeration, no clickbait, no religious language.
IDENTITY: Christian values expressed through universal wisdom (never preachy).
LANGUAGE: Bilingual — English primary, Korean translation included.

Create today's content set:

[Instagram Card Format]
✦ [Theme]
"English quote — powerful, memorable, 2-3 lines max"

(English body: 3 short paragraphs.
- Para 1: Empathy — acknowledge the universal human struggle
- Para 2: Insight — offer a fresh perspective or reframe
- Para 3: Action — one concrete thing to do today
Each paragraph 2-3 sentences.)

Korean translation (2-3 sentences, natural Korean, not word-for-word)

✦ Today's Wisdom / 오늘의 한마디
"One powerful bilingual sentence"

✦ Today's Practice / 오늘의 실천
Specific, doable action in both languages

Lighthouse Media
@lighthouse_media77

JSON output:
{{
  "title_en": "Card title English (2 lines, max 8 words each)",
  "title_kr": "카드 제목 한국어 (2줄, 각 10자 이내)",
  "topic": "{today_theme}",
  "hook_quote_en": "English quote (powerful, 1-2 sentences)",
  "hook_quote_kr": "한국어 번역",
  "body_empathy": "English empathy paragraph (2-3 sentences)",
  "body_insight": "English insight paragraph (2-3 sentences)",
  "body_action": "English action paragraph (2-3 sentences)",
  "body_kr": "한국어 요약 (3-4문장, 자연스러운 한국어)",
  "one_liner_en": "Today's wisdom English",
  "one_liner_kr": "오늘의 한마디 한국어",
  "daily_practice_en": "Today's practice English (2 sentences)",
  "daily_practice_kr": "오늘의 실천 한국어 (2문장)",
  "hashtags_kr": "#힐링 #자기계발 #위로 #공감 #멘탈케어 #마음관리 #성장 #동기부여 #일상 #하루",
  "hashtags_en": "#selfcare #motivation #healing #mentalhealth #growth #mindset #lighthouse #wisdom #inspiration #dailypractice",
  "scenes": [{{"time": "0-10", "title_en": "Scene title", "narration_en": "English narration", "narration_kr": "한국어 나레이션"}}, ...],
  "fb_post": "Facebook post — English + Korean, 200 words max, empathetic"
}}"""

    resp = req.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }, json={
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}]
    })

    text = resp.json()["content"][0]["text"]

    # JSON 추출
    start = text.find("{")
    end = text.rfind("}") + 1
    content = json.loads(text[start:end])

    # 저장
    with open(os.path.join(OUTPUT, "content.json"), 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    log(f"콘텐츠 생성 완료: {content['title'].split(chr(10))[0]}")
    return content

# === 2. 인스타/FB용 이미지 생성 ===
def create_image(title, subtitle, color=(29,158,117)):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1080
    DARK = (16, 18, 32)

    def get_font(size, bold=False):
        p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
        if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 5], fill=color)
    draw.ellipse([W-250, -80, W+80, 250], fill=(22, 24, 44))
    draw.ellipse([-100, H-200, 200, H+50], fill=(22, 24, 44))

    sm = get_font(24)
    draw.text((60, 50), "LIGHTHOUSE MEDIA", font=sm, fill=color)

    big = get_font(52, True)
    y = 350
    for line in title.split("\n"):
        bb = draw.textbbox((0,0), line, font=big)
        draw.text(((W-(bb[2]-bb[0]))/2, y), line, font=big, fill=(255,255,255))
        y += bb[3]-bb[1] + 20

    med = get_font(28)
    y = 600
    for line in subtitle.split("\n"):
        bb = draw.textbbox((0,0), line, font=med)
        draw.text(((W-(bb[2]-bb[0]))/2, y), line, font=med, fill=(180,180,195))
        y += bb[3]-bb[1] + 12

    draw.rectangle([W//2-50, H-80, W//2+50, H-76], fill=color)

    path = os.path.join(OUTPUT, "post_image.jpg")
    img.save(path, "JPEG", quality=95)
    log("이미지 생성 완료")
    return path

# === 3. 유튜브 숏츠 영상 생성 ===
def create_shorts_video(scenes):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1920
    FPS = 1  # 초당 1프레임 (빠른 생성)
    DARK = (16, 18, 32)
    MAIN = (29, 158, 117)

    def get_font(size, bold=False):
        p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
        if os.path.exists(p): return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    os.makedirs(FRAMES_DIR, exist_ok=True)
    frame_num = 0

    for scene in scenes:
        time_range = scene.get("time", "0-10")
        parts = time_range.replace("s", "").split("-")
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 else start + 10
        duration = end - start

        for sec in range(duration):
            img = Image.new("RGB", (W, H), DARK)
            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, W, 4], fill=MAIN)
            draw.ellipse([W-300, 200, W+100, 600], fill=(22, 24, 44))

            sm = get_font(28)
            draw.text((60, 100), "LIGHTHOUSE MEDIA", font=sm, fill=MAIN)

            title_font = get_font(56, True)
            title = scene.get("title", "")
            y = 600
            for line in title.split("\n"):
                bb = draw.textbbox((0,0), line, font=title_font)
                draw.text(((W-(bb[2]-bb[0]))/2, y), line, font=title_font, fill=(255,255,255))
                y += bb[3]-bb[1] + 20

            narr = scene.get("narration", "")
            sub_font = get_font(30)
            y = 1000
            for line in narr.split("\n")[:4]:
                if len(line) > 20:
                    # 줄 나누기
                    mid = len(line) // 2
                    for half in [line[:mid], line[mid:]]:
                        bb = draw.textbbox((0,0), half, font=sub_font)
                        draw.text(((W-(bb[2]-bb[0]))/2, y), half, font=sub_font, fill=(180,180,195))
                        y += bb[3]-bb[1] + 10
                else:
                    bb = draw.textbbox((0,0), line, font=sub_font)
                    draw.text(((W-(bb[2]-bb[0]))/2, y), line, font=sub_font, fill=(180,180,195))
                    y += bb[3]-bb[1] + 10

            draw.rectangle([W//2-50, H-180, W//2+50, H-176], fill=MAIN)
            tiny = get_font(22)
            txt = "@lighthouse_media77"
            bb = draw.textbbox((0,0), txt, font=tiny)
            draw.text(((W-(bb[2]-bb[0]))/2, H-140), txt, font=tiny, fill=(100,100,120))

            path = os.path.join(FRAMES_DIR, f"frame_{frame_num:05d}.png")
            img.save(path)
            frame_num += 1

    log(f"프레임 {frame_num}개 생성")

    # ffmpeg 합성 (음성 없이, 배경 음악도 없이 무음 영상)
    video_path = os.path.join(OUTPUT, "shorts.mp4")
    cmd = [
        FFMPEG, "-y",
        "-framerate", "1",
        "-i", os.path.join(FRAMES_DIR, "frame_%05d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "25",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={W}:{H},fps=30",
        video_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)

    shutil.rmtree(FRAMES_DIR, ignore_errors=True)

    if os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024*1024)
        log(f"숏츠 영상 생성: {size_mb:.1f}MB")
        return video_path
    return None

# === 4. Imgur 업로드 ===
def upload_imgur(path):
    import requests as req
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    r = req.post('https://api.imgur.com/3/image',
                 headers={'Authorization': f'Client-ID {IMGUR_CLIENT_ID}'},
                 data={'image': data, 'type': 'base64'})
    d = r.json()
    if d.get('success'):
        return d['data']['link']
    return None

# === 5. 인스타그램 게시 ===
def post_instagram(img_url, caption, token):
    import requests as req
    r = req.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
        'image_url': img_url, 'caption': caption, 'access_token': token
    })
    d = r.json()
    if 'id' not in d:
        log(f"IG 컨테이너 실패: {d}")
        return None
    time.sleep(5)
    r2 = req.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={
        'creation_id': d['id'], 'access_token': token
    })
    return r2.json().get('id')

# === 6. 페이스북 게시 ===
def post_facebook(message, img_url, page_token):
    import requests as req
    data = {'message': message, 'access_token': page_token}
    if img_url:
        data['url'] = img_url
        r = req.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data=data)
    else:
        r = req.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/feed', data=data)
    return r.json()

# === 7. 유튜브 업로드 ===
def upload_youtube(video_path, title, description, tags):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    token = json.load(open(YT_TOKEN_FILE))
    creds = Credentials.from_authorized_user_info(token)
    yt = build('youtube', 'v3', credentials=creds)

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22',
            'defaultLanguage': 'ko',
        },
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
    }

    media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
    request = yt.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response['id']

    # 재생목록 추가
    try:
        yt.playlistItems().insert(part='snippet', body={
            'snippet': {
                'playlistId': 'PLqShegXvrK3wiKvpIfJth9m5Fs7j8Qmgm',
                'resourceId': {'kind': 'youtube#video', 'videoId': video_id}
            }
        }).execute()
    except: pass

    return video_id

# === 메인 실행 ===
def main():
    log("=" * 50)
    log("  LIGHTHOUSE MEDIA — 자동 게시 시작")
    log("=" * 50)

    tokens = load_tokens()
    ig_token = tokens.get("instagram")
    fb_page_token = tokens.get("facebook_page")

    # 1. 콘텐츠 생성
    try:
        content = generate_content()
    except Exception as e:
        log(f"콘텐츠 생성 실패: {e}")
        return

    # 2. 이미지 생성 + Imgur 업로드
    colors = [(29,158,117), (186,117,23)]
    color = colors[datetime.now().day % 2]
    img_path = create_image(content["title"], content["subtitle"], color)

    img_url = upload_imgur(img_path)
    if img_url:
        log(f"Imgur 업로드: {img_url}")
    else:
        log("Imgur 업로드 실패")

    # 인스타 캡션 조립
    ig_caption = (
        f"\ud83d\udca1 {content.get('topic', '')}\n"
        f"\"{content.get('hook_quote', '')}\"\n\n"
        f"{content.get('body_empathy', '')}\n\n"
        f"{content.get('body_insight', '')}\n\n"
        f"{content.get('body_action', '')}\n\n"
        f"\u2726 \uc624\ub298\uc758 \ud55c\ub9c8\ub514\n"
        f"\"{content.get('one_liner', '')}\"\n\n"
        f"\u2726 \uc624\ub298\uc758 \uc2e4\ucc9c\n"
        f"{content.get('daily_practice', '')}\n\n"
        f"Lighthouse Media\n"
        f"@lighthouse_media\n\n"
        f"{content.get('hashtags_kr', '')}\n"
        f"{content.get('hashtags_en', '')}"
    )

    # 페이스북 메시지 조립
    fb_message = (
        f"\ud83d\udca1 {content.get('topic', '')}\n"
        f"\"{content.get('hook_quote', '')}\"\n\n"
        f"{content.get('body_empathy', '')}\n\n"
        f"{content.get('body_insight', '')}\n\n"
        f"\u2726 \uc624\ub298\uc758 \ud55c\ub9c8\ub514\n"
        f"\"{content.get('one_liner', '')}\"\n\n"
        f"Lighthouse Media | @lighthouse_media"
    )

    # 3. 인스타그램 — 하루 1개 고품질 게시 (daily-premium-post.py에서 처리)
    log("인스타 건너뜀 (하루 1개 정책 → daily-premium-post.py에서 게시)")

    # 4. 페이스북
    if fb_page_token and img_url:
        try:
            fb = post_facebook(fb_message, img_url, fb_page_token)
            log(f"페이스북 게시: {fb}")
        except Exception as e:
            log(f"페이스북 오류: {e}")
    else:
        log("페이스북 건너뜀 (토큰 없음)")

    # 5. 유튜브 숏츠
    try:
        scenes = content.get("scenes", [])
        if scenes:
            video_path = create_shorts_video(scenes)
            if video_path:
                title_line = content["title"].split("\n")[0]
                vid = upload_youtube(
                    video_path,
                    f"{title_line} #shorts #힐링 #직장인",
                    f"""\ud83d\udca1 {content.get('topic', '')}
"{content.get('hook_quote', '')}"

{content.get('body_empathy', '')}

{content.get('body_insight', '')}

\u2726 {content.get('one_liner', '')}

\u2014
\ub958\uc120\ud76c | Lighthouse Media
@lighthouse_media

{content.get('hashtags_kr', '')}
{content.get('hashtags_en', '')}""",
                    ['\ubc88\uc544\uc6c3\ud68c\ubcf5','\uc790\uae30\uacc4\ubc1c','\uc9c1\uc7a5\uc778\ud790\ub9c1','\ub9c8\uc74c\uad00\ub9ac','\uc22b\uce20','\ud790\ub9c1','shorts','SelfCare','Motivation']
                )
                log(f"유튜브 업로드 완료: https://youtube.com/shorts/{vid}")
        else:
            log("유튜브 건너뜀 (장면 없음)")
    except Exception as e:
        log(f"유튜브 오류: {e}")

    log("=" * 50)
    log("  자동 게시 완료!")
    log("=" * 50)

if __name__ == "__main__":
    main()
