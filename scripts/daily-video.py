"""매일 고퀄리티 숏츠 영상 1편 → YouTube + Instagram + Facebook 동시 업로드"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT = os.path.join(HOME, "lighthouse-media", "output", TODAY)
os.makedirs(OUT, exist_ok=True)

API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env"), encoding="utf-8"):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens.get("instagram","")
FB_TOKEN = tokens.get("facebook_page","")
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"

def claude(prompt, max_t=4096):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": max_t, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

def gf(size, bold=False):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def draw_centered(draw, y, text, font, fill, W, spacing=10):
    for line in text.split("\n"):
        bb = draw.textbbox((0,0), line, font=font)
        draw.text(((W-(bb[2]-bb[0]))/2, y), line, font=font, fill=fill)
        y += bb[3]-bb[1] + spacing
    return y

def main(dry_run=False, privacy="unlisted"):
    print("=" * 60)
    print(f"  LIGHTHOUSE MEDIA - Daily Video")
    print(f"  {TODAY}")
    print("=" * 60)

    # 1. 스크립트
    print("\n[1/4] Script...")
    _prompt = (
        "너는 Lighthouse Media(류선희) 숏츠 스크립트 작가다.\n"
        "타겟: 지친 20-40대 직장인. 톤: 따뜻하고 지적이며 실용적.\n"
        "종교 콘텐츠 아님 — 세속적 자기계발/동기부여/힐링.\n"
        "과장/선동 금지. 이모지: 💡, ✦만 사용.\n\n"
        "인스타 카드 형식:\n"
        "💡 [주제]\n\"핵심 메시지\"\n공감→위로→실천 흐름\n✦ 오늘의 한마디\n✦ 오늘의 실천\n\n"
        "JSON: {\"title\":\"제목30자이내\","
        "\"topic\":\"주제 키워드\","
        "\"hook_quote\":\"핵심 인용구\","
        "\"scenes\":[{\"duration\":8,\"title\":\"2줄제목\",\"narration\":\"3문장\",\"emotion\":\"공감/위로/희망/실천\"},...6-8장면 총60초],"
        "\"description\":\"설명200자\","
        "\"tags\":[15개],"
        "\"one_liner\":\"오늘의 한마디\","
        "\"daily_practice\":\"오늘의 실천 2문장\","
        "\"body_empathy\":\"공감 문단 2-3문장\","
        "\"body_insight\":\"위로 문단 2-3문장\","
        "\"body_action\":\"실천 문단 2-3문장\","
        "\"hashtags_kr\":\"#힐링 #자기계발 #번아웃 #직장인 #마음관리 #위로 #공감 #멘탈케어 #일상 #하루\","
        "\"hashtags_en\":\"#LighthouseMedia #SelfCare #Motivation #Healing #Mindfulness\","
        "\"ig_caption\":\"인스타캡션 (카드형식)\","
        "\"fb_post\":\"페이스북200자\"}\n\n"
        "첫3초: 충격통계/질문. 감정곡선: 공감->위로->희망->실천. 마지막: CTA."
    )

    # 모델이 가끔 문법이 깨진 JSON을 돌려준다(2026-10-08 실패 원인) — 최대 3회 재시도
    for attempt in range(1, 4):
        raw = claude(_prompt)
        start = raw.find("{"); end = raw.rfind("}")+1
        try:
            script = json.loads(raw[start:end])
            break
        except json.JSONDecodeError as e:
            print(f"  JSON 파싱 실패({attempt}/3): {e}")
            if attempt == 3:
                raise
    print(f"  Title: {script['title']}")

    # 2. 프레임
    print("\n[2/4] Frames...")
    W, H = 1080, 1920
    FPS = 2
    FRAMES = os.path.join(OUT, "frames")
    os.makedirs(FRAMES, exist_ok=True)
    DARK = (12, 14, 28)
    MAIN = (29, 158, 117)
    em_colors = {"공감":(100,120,180),"위로":(29,158,117),"희망":(186,117,23),"실천":(52,152,219)}

    fnum = 0
    for si, sc in enumerate(script['scenes']):
        dur = sc.get('duration', 8)
        emotion = sc.get('emotion', '위로')
        ec = em_colors.get(emotion, MAIN)
        title = sc.get('title', '')
        narr = sc.get('narration', '')

        for f in range(dur * FPS):
            prog = f / (dur * FPS)
            fade = min(1.0, f / max(FPS * 0.5, 1))
            if f > (dur * FPS) - FPS * 0.3:
                fade = max(0, ((dur * FPS) - f) / max(FPS * 0.3, 1))

            img = Image.new("RGB", (W, H), DARK)
            d = ImageDraw.Draw(img)

            # Background
            off = int(prog * 40)
            d.ellipse([W-300+off, 100-off, W+100+off, 500-off], fill=(18,20,38))
            d.ellipse([-150-off, H-400+off, 250-off, H-100+off], fill=(18,20,38))

            bc = tuple(int(c*fade) for c in ec)
            d.rectangle([0,0,W,4], fill=bc)

            # Scene num (big transparent)
            nc = tuple(int(c*fade*0.08) for c in ec)
            d.text((W-250, 150), str(si+1), font=gf(200, True), fill=nc)

            # Brand
            d.text((60, 80), "LIGHTHOUSE MEDIA", font=gf(22), fill=tuple(int(c*fade) for c in MAIN))

            # Emotion badge
            d.rounded_rectangle([60,130,60+len(emotion)*22+20,165], radius=10, fill=bc)
            d.text((72,135), emotion, font=gf(18,True), fill=tuple(int(255*fade) for _ in range(3)))

            # Title
            tc = tuple(int(255*fade) for _ in range(3))
            y = 550
            for ln in title.split("\n"):
                bb = d.textbbox((0,0), ln, font=gf(56,True))
                d.text(((W-(bb[2]-bb[0]))/2, y), ln, font=gf(56,True), fill=tc)
                y += bb[3]-bb[1]+20

            # Divider
            lw = int(160 * min(1, prog*2))
            if lw > 0: d.rectangle([W//2-lw, 800, W//2+lw, 803], fill=bc)

            # Narration
            nf = max(0, min(1, (prog-0.2)*2))
            nc2 = tuple(int(190*nf*fade) for _ in range(3))
            ny = 860
            for ln in narr.split("\n")[:4]:
                while len(ln) > 22:
                    part = ln[:22]
                    bb = d.textbbox((0,0), part, font=gf(28))
                    d.text(((W-(bb[2]-bb[0]))/2, ny), part, font=gf(28), fill=nc2)
                    ny += bb[3]-bb[1]+8
                    ln = ln[22:]
                if ln.strip():
                    bb = d.textbbox((0,0), ln, font=gf(28))
                    d.text(((W-(bb[2]-bb[0]))/2, ny), ln, font=gf(28), fill=nc2)
                    ny += bb[3]-bb[1]+8

            # Footer
            d.rectangle([W//2-40, H-140, W//2+40, H-136], fill=bc)
            fc = tuple(int(80*fade) for _ in range(3))
            txt = "@lighthouse_media77"
            bb = d.textbbox((0,0), txt, font=gf(18))
            d.text(((W-(bb[2]-bb[0]))/2, H-110), txt, font=gf(18), fill=fc)

            img.save(os.path.join(FRAMES, f"frame_{fnum:05d}.png"))
            fnum += 1

        print(f"  Scene {si+1}/{len(script['scenes'])}: {title.split(chr(10))[0] if chr(10) in title else title[:15]} ({dur}s)")

    total_dur = sum(s.get('duration',8) for s in script['scenes'])
    print(f"  {fnum} frames ({total_dur}s)")

    # 3. ffmpeg
    print("\n[3/4] Encoding...")
    vpath = os.path.join(OUT, "daily-shorts.mp4")
    subprocess.run([FFMPEG, "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "frame_%05d.png"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-vf", f"scale={W}:{H},fps=30", "-t", str(total_dur), vpath],
                   capture_output=True, timeout=120)
    shutil.rmtree(FRAMES, ignore_errors=True)

    if not os.path.exists(vpath):
        print("  FAIL!"); return
    print(f"  OK! {os.path.getsize(vpath)/(1024*1024):.1f}MB")

    if dry_run:  # --dry-run: 기존 방식 비교 샘플 — 인코딩까지만, 어디에도 올리지 않는다
        os.makedirs(QUALITY_DIR, exist_ok=True)
        keep = os.path.join(QUALITY_DIR, "legacy-sample.mp4")
        shutil.copy(vpath, keep)
        print(f"  DRY-RUN — 업로드 생략(유튜브·인스타·페이스북). 비교 샘플: {keep}")
        return

    # 4. Upload
    print("\n[4/4] Uploading...")

    # YouTube
    print("  YouTube...")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    ytp = os.path.join(HOME, "OneDrive", "\ubc14\ud0d5 \ud654\uba74", "03_\uc0ac\uc5c5_\ub9c8\ucf00\ud305", "lighthouse_media", "token_lighthouse.json")
    ytk = json.load(open(ytp))
    creds = Credentials.from_authorized_user_info(ytk)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(ytp, 'w') as f: f.write(creds.to_json())

    yt = build('youtube', 'v3', credentials=creds)
    yt_desc = (
        f"\ud83d\udca1 {script.get('topic', '')}\n"
        f"\"{script.get('hook_quote', '')}\"\n\n"
        f"{script.get('body_empathy', '')}\n\n"
        f"{script.get('body_insight', '')}\n\n"
        f"\u2726 {script.get('one_liner', '')}\n\n"
        f"\u2014\n"
        f"\ub958\uc120\ud76c | Lighthouse Media\n"
        f"@lighthouse_media\n\n"
        f"{script.get('hashtags_kr', '')}\n"
        f"{script.get('hashtags_en', '')}"
    )
    body = {
        'snippet': {
            'title': script['title'] + ' #shorts',
            'description': yt_desc,
            'tags': script.get('tags', ['\ubc88\uc544\uc6c3','\uc790\uae30\uacc4\ubc1c','\ud790\ub9c1','shorts']),
            'categoryId': '22', 'defaultLanguage': 'ko',
        },
        'status': {'privacyStatus': privacy, 'selfDeclaredMadeForKids': False}
    }
    media = MediaFileUpload(vpath, mimetype='video/mp4', resumable=True)
    req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
    resp = None
    while resp is None: _, resp = req.next_chunk()
    vid_id = resp['id']
    print(f"    https://youtube.com/shorts/{vid_id}")

    try:
        yt.playlistItems().insert(part='snippet', body={
            'snippet': {'playlistId': 'PLqShegXvrK3wiKvpIfJth9m5Fs7j8Qmgm',
                        'resourceId': {'kind': 'youtube#video', 'videoId': vid_id}}
        }).execute()
    except: pass

    # Thumbnail for IG/FB
    thumb = Image.new("RGB", (1080, 1350), DARK)
    td = ImageDraw.Draw(thumb)
    td.rectangle([0,0,1080,5], fill=MAIN)
    td.text((60,60), "LIGHTHOUSE MEDIA", font=gf(24), fill=MAIN)
    td.rounded_rectangle([60,110,200,145], radius=10, fill=MAIN)
    td.text((78,115), "NEW", font=gf(20,True), fill=(255,255,255))
    ttl = script['title'].replace('#shorts','').strip()
    draw_centered(td, 400, ttl, gf(48, True), (255,255,255), 1080, 20)
    td.rectangle([490,1350-100,590,1350-96], fill=MAIN)
    tpath = os.path.join(OUT, "thumb.jpg")
    thumb.save(tpath, "JPEG", quality=95)

    with open(tpath, 'rb') as f:
        idata = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/image', headers={'Authorization': f'Client-ID {IMGUR_ID}'}, data={'image': idata, 'type': 'base64'})
    turl = ir.json().get('data',{}).get('link')

    # Instagram
    print("  Instagram...")
    if turl and IG_TOKEN:
        cap = (
            f"\ud83d\udca1 {script.get('topic', '')}\n"
            f"\"{script.get('hook_quote', script['title'])}\"\n\n"
            f"{script.get('body_empathy', '')}\n\n"
            f"{script.get('body_insight', '')}\n\n"
            f"{script.get('body_action', '')}\n\n"
            f"\u2726 \uc624\ub298\uc758 \ud55c\ub9c8\ub514\n"
            f"\"{script.get('one_liner', '')}\"\n\n"
            f"\u2726 \uc624\ub298\uc758 \uc2e4\ucc9c\n"
            f"{script.get('daily_practice', '')}\n\n"
            f"Lighthouse Media\n"
            f"@lighthouse_media\n\n"
            f"{script.get('hashtags_kr', '')}\n"
            f"{script.get('hashtags_en', '')}"
        )
        r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={'image_url': turl, 'caption': cap, 'access_token': IG_TOKEN})
        d = r.json()
        if 'id' in d:
            time.sleep(5)
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish', data={'creation_id': d['id'], 'access_token': IG_TOKEN})
            print(f"    OK! {r2.json().get('id','')}")
        else:
            print(f"    {d}")

    # Facebook
    print("  Facebook...")
    if turl and FB_TOKEN:
        fm = (
            f"\ud83d\udca1 {script.get('topic', '')}\n"
            f"\"{script.get('hook_quote', script['title'])}\"\n\n"
            f"{script.get('body_empathy', '')}\n\n"
            f"{script.get('body_insight', '')}\n\n"
            f"\u2726 {script.get('one_liner', '')}\n\n"
            f"YouTube: https://youtube.com/shorts/{vid_id}\n"
            f"Lighthouse Media | @lighthouse_media"
        )
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/photos', data={'url': turl, 'message': fm, 'access_token': FB_TOKEN})
        d = r.json()
        print(f"    {'OK!' if 'id' in d else d}")

    print(f"\n{'='*60}")
    print(f"  Video uploaded to 3 channels!")
    print(f"  YT: https://youtube.com/shorts/{vid_id}")
    print(f"{'='*60}")

# ════════════════════════════════════════════════════════════════════════════
# 품질 모드 (--quality) — 오너 지시 2026-10-15 "조회수 높은 영상 수준"  (worker-3, forge 착용)
#   한국어 TTS 나레이션 + AI 배경(Ken Burns) + 나레이션 타이밍 자막 + 제목 공식 + 해시태그 3~6개
#   - 기본은 dry-run: --upload 를 명시하지 않으면 어디에도 올리지 않는다(루브릭 C2).
#   - 인스타·페이스북 썸네일 게시는 하지 않는다(이미지 도달 ≈ 0 — 제거 '제안', 적용은 JARVIS·오너 승인 후).
#   - 편당 비용(Claude 대본·TTS·이미지, 재시도 포함) US$0.30 초과면 호출·업로드하지 않는다(루브릭 C1, master 결정 2026-10-15). 단가 출처는 lib/fal_tts.py·lib/fal_visuals.py 주석.
#   - 실패는 fail-closed: 어떤 단계든 실패하면 업로드하지 않고 사유를 failures.log 에 남긴다(폴백 없음). 공개 범위 기본 unlisted(--privacy).
#   - 스케줄러가 부르는 기존 방식(플래그 없음)은 그대로 둔다 — 새 방식은 오너 승인 뒤 daily-video.bat 에 --quality --upload 를 넣을 때 켜진다.
# ════════════════════════════════════════════════════════════════════════════
QUALITY_DIR = os.path.join(HOME, "lighthouse-media", "output", "youtube", "quality")
PER_VIDEO_BUDGET_USD = 0.30                  # 편당 상한(US$) — TTS+이미지(재생성 포함)+Claude 대본(재시도 포함) 합계. master 결정 2026-10-15
TL_LEAD, TL_GAP, TL_TAIL = 0.10, 0.22, 1.2   # 첫 음성 시작·문장 사이 휴지·끝 여운(초)
SYLLABLES_MIN, SYLLABLES_MAX = 175, 290       # 루브릭 S1 (≈ 33~55초; 하한 150은 29초대 영상을 만들어 TTS 뒤에 길이 가드에 걸렸다 — R3에서 175로 올림)
LEN_MIN, LEN_MAX = 30.0, 55.0                 # 루브릭 L1
CATEGORY_BGM = {"comfort": "trend-comfort", "motivation": "trend-motivation", "growth": "trend-growth", "healing": "trend-healing"}
RELIGION_WORDS = ["하나님", "하느님", "주님", "예수", "그리스도", "부처", "스님", "불교", "교회", "성경", "찬송", "아멘", "신앙", "은혜", "천국", "축복", "믿음", "구원", "영혼"]
RELIGION_RE = re.compile(r"(?<![가-힣])기도|(?<![가-힣])신(?:의|께|이)(?![가-힣])")
UNSOURCED_RE = re.compile(r"\d\s*%|퍼센트|연구|조사|통계|박사|교수|논문|실험|전문가|과학자")
NAMED_PERSON_RE = re.compile(r"쇼펜하우어|니체|법륜|법정|공자|괴테|아인슈타인|스티브 잡스|워런 버핏|말했다|말씀하셨")
# 주제 순환: --topic 을 안 주면 날짜로 하나를 고른다(매일 같은 주제로 올리지 않게). 최근 올린 제목은 대본 프롬프트에 넣어 겹치지 않게 한다.
TOPICS = [
    "퇴근 후에도 머릿속이 꺼지지 않는 직장인", "거절하지 못해서 늘 지치는 사람", "남과 비교하다 하루가 무너지는 날", "아침에 일어나기 힘든 사람의 작은 시작",
    "열심히 했는데 인정받지 못한 날", "쉬어도 쉰 것 같지 않을 때", "혼자 있는 시간이 필요한 사람", "실수한 뒤 계속 자책하는 사람",
    "일요일 밤마다 불안해지는 사람", "관계에서 먼저 지치는 사람", "완벽하지 않아도 괜찮다고 말해 주는 법", "번아웃이 와도 일상을 놓지 않는 법",
    "하루를 마무리하는 작은 습관", "나를 돌보는 일이 어색한 사람",
    # 자가점검형 — 채널 최고 조회 '번아웃 5가지 신호 3개 이상이면 위험'(1025회) 형식. 2026-10-20 --script-only 5건 전부 통과
    "번아웃 직전 5가지 신호, 3개 이상이면 쉬어야 할 때", "쉬어야 할 때를 알려주는 4가지 신호", "마음이 지쳤다는 걸 알려주는 5가지 행동",
    "나도 모르게 무리하고 있다는 4가지 신호", "번아웃이 오기 전 몸이 보내는 5가지 신호",
]
HISTORY_PATH = os.path.join(QUALITY_DIR, "history.json")


def pick_topic(today=None):
    today = today or datetime.now()
    return TOPICS[today.toordinal() % len(TOPICS)]


def recent_titles(n=14):
    try:
        return json.load(open(HISTORY_PATH, encoding="utf-8"))[-n:]
    except (OSError, json.JSONDecodeError):
        return []


IMAGE_STYLE_SUFFIX = (", soft painterly illustration, bright well-exposed scene with warm natural daylight or warm lamp light (not dark, not night), calm, vertical composition, "
                      "no text, no letters, no readable writing on any paper, book, screen or sign, no logo, no emblem, no signature, no stamp, no watermark, "
                      "no rope, no cord, no cable, no hanging string, no noose, no visible human faces (people only from behind or far away), "
                      "clean empty floor or soft shadow along the bottom edge")
IMAGE_RETRY_SUFFIX = ", very bright sunny daylight, light pastel colors, high key lighting"
IMAGE_FALLBACK_PROMPTS = [  # 3번째 시도: 안전·밝은 야외·창가 장면 — 천장 등·끈·책·서류가 들어갈 틈이 없는 소재(R3: 실내 정물 프롬프트에서 올가미 모양 전등줄·가짜 글자가 계속 나왔다)
    "a quiet sunny park path with trees and soft light, seen from far away",
    "a bright sunlit windowsill with a green potted plant and a plain white mug, soft daylight",
    "a wide blue sky with soft white clouds above green treetops",
]
OPEN_Q = "'\"‘“"     # 자막 카드 분할 시 '여는 따옴표'로 보는 글자
CLOSE_Q = "'\"’”"
IMG_MIN_MEAN, IMG_MIN_STD = 40.0, 15.0      # 축소 회색조 평균·표준편차 기준 — 검은 장면(평균 0)·거의 단색을 거른다
IMG_MAX_ATTEMPTS = 3
VIDEO_MIN_SECOND_MEAN = 30.0                # 완성본 초당 샘플 평균 밝기(0~255)가 이보다 낮으면 업로드하지 않는다
SETTINGS = ["출근길 버스 안", "점심시간 혼자 먹는 식당 구석", "회의가 끝난 빈 회의실", "야근 뒤 편의점 앞", "주말 오전 거실 소파", "퇴근길 엘리베이터 안",
            "이직 면접 전날 저녁 책상 앞", "카페에서 메신저 알림을 보는 순간", "비 오는 날 정류장 우산 아래", "점심 뒤 사무실 자리", "퇴근 후 현관 신발장 앞", "아침 출근 준비하며 창밖을 보는 순간"]
SCIENCE_RE = re.compile(r"뇌|호르몬|신경(?!\s*(?:쓰|써))|세로토닌|코르티솔|도파민|심리학|심리적으로|과학적|의학|진단|증상|우울증|불안장애|면역|생리")
ASSERT_RE = re.compile(r"사실은|사실 .{0,10}(?:거예요|거에요|이에요|입니다)|항상|절대|반드시|누구나|모든 사람|무조건|뿐이에요|뿐입니다|(?:두려운|무서운|겁나는|외로운|불안한|무거운)\s*거(?:예요|에요)")
BAD_IMAGE_WORDS = re.compile(r"\b(bed|bedroom|sheets?|pillow|blanket|night|midnight|dark|dim|naked|bath|bathroom|shower|body|hospital|"
                             r"rope|ropes|cord|cords|noose|cable|cables|string|strings|hanging|text|letters?|writing|written|words?|signs?|poster|newspaper|magazine|label|papers?|documents?|folders?|books?|notebooks?|journals?|diary|screens?|laptops?|monitors?|pens?)\b", re.I)
CLAUDE_PRICE_PER_MTOK = (3.0, 15.0)  # (입력, 출력) US$/백만 토큰 — claude-sonnet-4-6 단가를 이 저장소에서 확인하지 못해 Sonnet 계열 공시가로 가정한 값 [미확인]


def hash_str(t):
    import hashlib
    return int(hashlib.md5(t.encode("utf-8")).hexdigest()[:8], 16)


def _syllables(text):
    return len(re.findall(r"[가-힣]", text))


CLAUDE_SPENT = {"input_tokens": 0, "output_tokens": 0, "calls": 0}   # 이 프로세스의 모든 Claude 호출(JSON 파싱 실패·검사 탈락 재시도 포함) 누적 토큰 — 비용 게이트·실패 로그용


def claude_json(prompt, tries=3, max_t=3500):
    """Claude 호출 → (JSON 객체, usage). 형식이 깨지면 최대 tries회 재시도. 실패하면 예외."""
    last = None
    for attempt in range(1, tries + 1):
        r = requests.post("https://api.anthropic.com/v1/messages", headers={
            "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
        }, json={"model": "claude-sonnet-4-6", "max_tokens": max_t, "messages": [{"role": "user", "content": prompt}]}, timeout=120)
        j = r.json()
        _u = j.get("usage") or {}
        CLAUDE_SPENT["calls"] += 1
        CLAUDE_SPENT["input_tokens"] += _u.get("input_tokens", 0) or 0
        CLAUDE_SPENT["output_tokens"] += _u.get("output_tokens", 0) or 0
        if "content" not in j:
            last = f"API 응답 이상: {str(j)[:200]}"
            print(f"  Claude 호출 실패({attempt}/{tries}): {last}")
            continue
        raw = j["content"][0]["text"]
        a, b = raw.find("{"), raw.rfind("}") + 1
        try:
            return json.loads(raw[a:b]), j.get("usage", {})
        except json.JSONDecodeError as e:
            last = f"JSON 파싱 실패: {e}"
            print(f"  {last} ({attempt}/{tries})")
    raise RuntimeError(last or "Claude 호출 실패")


def quality_prompt(topic, feedback="", recent=(), setting=""):
    return (
        "너는 Lighthouse Media(류선희) 유튜브 쇼츠 대본 작가다. 목표: 조회수가 높은 한국 '인생 조언·위로' 쇼츠 수준의 나레이션 대본.\n"
        f"오늘 주제: {topic}\n"
        "타겟: 지친 20~40대 직장인(공감하는 말투). 톤: 따뜻하고 지적이며 실용적. 존댓말(~해요/~입니다) 한 가지로 통일.\n"
        "브랜드 원칙: 종교 색 없이 보편적인 자기돌봄 조언. 하나님·기도·부처·스님·교회·신앙 같은 말 금지.\n"
        "근거 원칙: 통계·퍼센트·'연구에 따르면'·박사/교수/전문가·실존 인물의 말 인용·'~하면 낫는다/성공한다' 같은 보장 표현은 쓰지 마라(출처 없는 단정 금지). "
        "과학·의학·심리학 단정도 금지: 뇌·호르몬·신경·세로토닌·코르티솔·도파민·심리학·심리적으로·과학적·의학·진단·증상·우울증·불안장애·면역·생리 같은 말로 원인이나 몸의 작용을 설명하지 말고, 사람의 경험과 가능성('~일 수 있어요', '~해 보세요')으로만 말한다. "
        "위 낱말은 대본·제목·설명·태그 어디에도 쓰지 마라('신경 쓰다'도 '마음에 두다'로, '증상'은 '모습'으로 바꾼다). "
        "다음 낱말도 대본·제목·설명·태그에 쓰지 마라: 퍼센트·%·연구·조사·통계·박사·교수·논문·실험·전문가·과학자. "
        "속마음을 단정하지 마라('사실은', '항상', '절대', '반드시', '누구나', '모든 사람', '무조건', '~뿐이에요', '~뿐입니다', '두려운/무서운/겁나는/외로운/불안한/무거운 거예요' 금지).\n\n"
        "구성(감정곡선): ① 첫 문장 = 제목의 약속을 그대로 말하는 훅(공백 포함 25자 이내를 목표로 써라 — 30자를 넘으면 탈락한다. 제목이 길면 앞부분만 말하고, 인사·자기소개 금지) ② 공감 ③ 구체적 상황 1곳(시간·장소·행동이 있는 장면 문장 1개 — 배경은 '" + (setting or "일상의 한 장면") + "'로 한다. '일요일 밤'은 이미 많이 써서 쓰지 마라) "
        "④ 관점 전환(위로) ⑤ 오늘 할 수 있는 실천 1개(한 가지 행동, 동사로 끝나게) ⑥ 짧은 마무리 한 줄.\n"
        "제목 공식 중 하나를 골라라: A) 대상+특징/행동 수('…한 사람들의 3가지 특징') B) 궁금증·숨김('…가 끝까지 숨기는 것') C) 세대·대상 호명('30대에게 꼭 전하고 싶은 말') D) 숫자 약속('…하면 달라지는 하루 습관 3가지'). "
        "제목은 15~30자, 과장·허위 약속 금지. 제목에 숫자가 있으면(예: 3가지) 본론에서 정확히 그만큼의 항목을 '첫째, … 둘째, … 셋째, …'로 말한다. "
        "첫 문장은 제목 문구를 거의 그대로 말하고, title_lines는 제목을 줄여 둘로 나눈 것이다(제목에 없는 말 금지).\n\n"
        "분량: 문장 8~14개, 문장당 공백 포함 35자 이내를 목표로 써라(40자를 넘으면 탈락한다; 첫 문장은 25자 이내가 목표, 30자 초과 탈락). 쓴 뒤 문장마다 글자 수를 세어 확인한다. 전체 한글 음절은 175~290개(약 33~55초 나레이션). 소리 내어 읽기 편한 짧은 문장. 숫자는 '3가지'처럼 말로 읽히게 쓴다.\n"
        "장면: 5~7장면. 각 장면에 문장 2개 안팎을 묶는다(sentences[].scene = 장면 번호 0부터, 순서대로 같거나 커진다). "
        "각 장면의 image_prompt는 영어로, 사람 얼굴 없는 구체적이고 **밝은 낮** 장면(창가, 길, 책상, 공원, 카페 등) 한 문장. 밤·어둠·침대·침실·이불·욕실·병원·신체 장면은 쓰지 마라(어둡거나 이미지 안전필터가 빈 이미지를 낼 수 있다). 밧줄·끈·줄·케이블·매달린 물건(rope, cord, noose, cable, string)과 글자가 보이는 물건(text, letters, sign, poster, magazine, newspaper, paper, document, folder, book, notebook, journal, laptop, screen, pen)도 image_prompt에 쓰지 마라(자해를 연상시키거나 이미지에 알아볼 수 없는 가짜 글자가 그려진다). 창가·햇빛·식물·머그컵·의자·길·나무·하늘처럼 글자가 들어갈 수 없는 소재로 그린다.\n\n"
        "JSON만 출력(설명 금지):\n"
        "{\"title\":\"15~30자 제목\",\"title_lines\":[\"화면 위 제목 1줄(14자 이하)\",\"2줄(14자 이하)\"],\"formula\":\"A|B|C|D\","
        "\"category\":\"comfort|motivation|growth|healing\","
        "\"sentences\":[{\"text\":\"나레이션 한 문장\",\"scene\":0},...],"
        "\"situation_idx\":구체적 상황 문장의 인덱스(0부터),"
        "\"scenes\":[{\"image_prompt\":\"English one-sentence scene\"},...],"
        "\"description_hook\":\"설명 첫 줄(훅 한 줄)\",\"description_body\":\"설명 본문 2~3줄\","
        "\"hashtags\":[\"#해시태그\",...3~5개, #shorts 제외],\"tags\":[\"검색 키워드\",...8~12개]}\n"
        + (f"\n최근에 올린 제목(같은 제목·같은 훅 금지): {' / '.join(recent)}\n" if recent else "")
        + (f"\n지난 시도의 문제 — 아래 항목만 정확히 고치고, 통과한 부분(제목·구성·다른 문장)은 되도록 그대로 유지해라:\n{feedback}\n" if feedback else "")
    )


def validate_script(s):
    """루브릭 H2·S1~S4·N1·N2·G1 자동 검사. 문제 목록(빈 목록 = 통과)."""
    p = []
    try:
        sents = [x["text"].strip() for x in s["sentences"]]
        scene_ids = [int(x["scene"]) for x in s["sentences"]]
        title = s["title"].strip()
        n_scenes = len(s["scenes"])
    except Exception as e:
        return [f"필드 누락/형식 오류: {e}"]
    syl = sum(_syllables(t) for t in sents)
    if syl < SYLLABLES_MIN: p.append(f"한글 음절 {syl}개 — {SYLLABLES_MIN}~{SYLLABLES_MAX}이어야 한다 → 최소 {SYLLABLES_MIN - syl}음절(문장 1~2개 분량) 늘려라(공감·상황 장면 문장을 더하는 식으로)")
    elif syl > SYLLABLES_MAX: p.append(f"한글 음절 {syl}개 — {SYLLABLES_MIN}~{SYLLABLES_MAX}이어야 한다 → 최소 {syl - SYLLABLES_MAX}음절(문장 1~2개 분량) 줄여라(겹치는 위로 문장을 빼는 식으로)")
    if not (8 <= len(sents) <= 14): p.append(f"문장 {len(sents)}개 — 8~14개")
    for i, t in enumerate(sents):
        if i == 0 and len(t) > 30:
            p.append(f"첫 문장({len(t)}자) \"{t}\" → 30자 이하로 줄여라(제목 문구를 거의 그대로 말하되 군더더기를 뺀다)")
        elif i > 0 and len(t) > 40:
            p.append(f"{i + 1}번째 문장({len(t)}자) \"{t}\" → 40자 이하 두 문장으로 나눠라(쉼표나 '~고/~서/~지만' 뒤에서 끊는다)")
    if not (15 <= len(title) <= 30): p.append(f"제목 {len(title)}자 — 15~30자")
    tl = s.get("title_lines") or []
    if not (1 <= len(tl) <= 2) or any(len(x) > 14 for x in tl):
        p.append(f"title_lines는 1~2줄, 줄당 14자 이하여야 한다 → 현재 {[(x, len(x)) for x in tl]} — 제목 '{title}'을 14자 이하 두 줄로 나눠라")
    if not (5 <= n_scenes <= 7): p.append(f"장면 {n_scenes}개 — 5~7개")
    if scene_ids != sorted(scene_ids) or (scene_ids and (scene_ids[0] != 0 or scene_ids[-1] != n_scenes - 1 or set(scene_ids) != set(range(n_scenes)))):
        p.append("sentences[].scene이 0..장면수-1을 순서대로 모두 덮지 않는다")
    v = s.get("situation_idx")
    if not isinstance(v, int) or not (0 <= v < len(sents)): p.append("situation_idx(구체적 상황 문장의 번호, 0부터)가 없거나 범위 밖이다")
    pi = s.get("practice_idx")   # 실천 문장은 모델이 고르지 않고 코드가 assign_practice_idx()로 지정한다(R4)
    if not isinstance(pi, int) or not (0 <= pi < len(sents)):
        p.append("'~해 보세요'로 끝나는 실천 문장이 하나도 없다 → 오늘 할 수 있는 행동 하나를 '~해 보세요.'로 끝나는 한 문장으로 써라(예: '창문을 열고 숨을 세 번 쉬어 보세요.')")
    elif v == pi:
        p.append("구체 상황 문장과 실천 문장이 같다 — 서로 다른 문장이어야 한다")
    blob = " ".join(sents + [title, s.get("description_hook", ""), s.get("description_body", ""), " ".join(s.get("tags", [])), " ".join(x.get("image_prompt", "") for x in s["scenes"])])
    for w in RELIGION_WORDS:
        if w in blob: p.append(f"종교 용어 '{w.strip()}'")
    m = RELIGION_RE.search(blob)
    if m: p.append(f"종교 용어 '{m.group(0)}'")
    spoken = " ".join(sents + [title])
    # 안전 검사(정규식·대상 텍스트는 R3와 같다 — R4는 '어디에서 걸렸는지'를 메시지에 더했을 뿐 완화하지 않았다)
    named = [(f"{i + 1}번째 문장", t) for i, t in enumerate(sents)] + [("제목", title)]
    for rx, what, fix in ((UNSOURCED_RE, "근거 없는 단정 가능 표현", "통계·연구·전문가 같은 출처 주장을 빼고 경험 표현으로"),
                          (NAMED_PERSON_RE, "실존 인물·인용 표현", "인물 인용을 빼고"),
                          (SCIENCE_RE, "과학·의학·심리학 단정 표현", "원인·생리 작용을 말하지 말고 경험 표현('~일 수 있어요')으로"),
                          (ASSERT_RE, "단정 표현", "'~일 수 있어요'·'~해 보세요'로 완화")):
        for where, txt in named:
            m = rx.search(txt)
            if m:
                p.append(f"{where} \"{txt}\"에 {what} '{m.group(0)}' → {fix} 고쳐라")
    meta_fields = (("description_hook", s.get("description_hook", "")), ("description_body", s.get("description_body", "")),
                   ("tags", " ".join(s.get("tags", []))), ("hashtags", " ".join(s.get("hashtags", []))))
    for rx, what in ((UNSOURCED_RE, "근거 없는 단정 가능 표현"), (NAMED_PERSON_RE, "실존 인물·인용 표현"), (SCIENCE_RE, "과학·의학·심리학 단정 표현"), (ASSERT_RE, "단정 표현")):
        for fname, txt in meta_fields:   # 제목은 위 검사에 이미 들어 있고, 설명·태그·해시태그에도 같은 검사를 건다(R3)
            m = rx.search(txt)
            if m:
                p.append(f"{fname}에 {what} '{m.group(0)}' → 이 표현을 빼고 일상어로 다시 써라(현재: \"{txt[:60]}\")")
    for k, sc in enumerate(s["scenes"]):
        mb = BAD_IMAGE_WORDS.search(sc.get("image_prompt", ""))
        if mb: p.append(f"{k + 1}번째 장면 image_prompt에 '{mb.group(0)}' → 이 단어를 빼고 창가·햇빛·식물·머그컵·의자·길·나무·하늘 같은 소재로 다시 써라(현재: \"{sc.get('image_prompt', '')[:90]}\")")
    # 제목의 약속을 지키는가(루브릭 H2): 숫자 약속이면 그만큼 항목을 말하고, 첫 문장·화면 제목은 제목과 같은 말이어야 한다
    m = re.search(r"(\d+|두|세|네|다섯)\s*(?:가지|개)", title)
    if m:
        n_promise = {"두": 2, "세": 3, "네": 4, "다섯": 5}.get(m.group(1)) or int(m.group(1))
        if 2 <= n_promise <= 5:
            all_ords = ["첫째", "둘째", "셋째", "넷째", "다섯째", "여섯째"]
            ords = all_ords[:n_promise]
            miss = [o for o in ords if o not in spoken]
            extra = [o for o in all_ords[n_promise:] if o in spoken]
            pos = [spoken.find(o) for o in ords if o in spoken]
            dup = [o for o in ords if spoken.count(o) > 1]
            if miss: p.append(f"제목이 {n_promise}가지를 약속하는데 대본에 {miss}가 없다(항목마다 '첫째, 둘째…'로 말해라)")
            if extra: p.append(f"제목이 {n_promise}가지를 약속하는데 대본에 {extra}까지 나온다(약속한 개수와 본문 항목 수가 같아야 한다)")
            if dup: p.append(f"항목 표시 {dup}가 두 번 이상 나온다")
            if pos != sorted(pos): p.append("첫째·둘째… 순서가 뒤바뀌었다")

    def _bigrams(t):
        t = re.sub(r"[^가-힣]", "", t)
        return {t[i:i + 2] for i in range(len(t) - 1)}
    if sents and len(_bigrams(title) & _bigrams(sents[0])) < 3: p.append("첫 문장이 제목의 약속과 같은 말이 아니다(제목 문구를 거의 그대로 말해라)")
    tlb = _bigrams("".join(tl))
    if tlb and len(tlb & _bigrams(title)) < 0.6 * len(tlb): p.append("title_lines가 제목의 문구와 다르다(제목을 둘로 나눈 것이어야 한다)")
    tags = s.get("hashtags") or []
    if not (3 <= len(tags) <= 5) or any(not t.startswith("#") or " " in t for t in tags) or any(t.lower() == "#shorts" for t in tags):
        p.append("hashtags는 '#'로 시작하는 3~5개(#shorts 제외 — 코드가 붙인다)")
    if len(s.get("tags", [])) < 5: p.append("tags 5개 이상")
    return p


CONNECTIVE_ENDS = ("고", "며", "면서", "지만", "는데", "은데", "인데", "서", "니까", "다가", "거나", "으면", "라면")
NOT_CONNECTIVE_ENDS = ("에서", "에게서", "로서", "께서", "부터서")     # 조사 '~에서' 등은 절 경계가 아니다
FIRST_MAX, SENT_MAX, SPLIT_MIN_PART = 30, 40, 8
MAX_SENTENCES = 14


def _quotes_balanced(t):
    return sum(t.count(c) for c in "'\"") % 2 == 0


def _split_candidates(text):
    """한 문장을 공백 경계에서 둘로 나누는 후보 [(왼쪽, 오른쪽, 종류)]. 종류: comma(쉼표 뒤) / conn(연결어미 뒤). 따옴표 안·너무 짧은 조각은 제외."""
    words = text.split(" ")
    out = []
    for k in range(len(words) - 1):
        w = words[k]
        if w.endswith(","): kind = "comma"
        elif w.endswith(CONNECTIVE_ENDS) and not w.endswith(NOT_CONNECTIVE_ENDS): kind = "conn"
        else: continue
        left = " ".join(words[:k + 1]).rstrip(",").strip()
        right = " ".join(words[k + 1:]).strip()
        if len(left) < SPLIT_MIN_PART or len(right) < SPLIT_MIN_PART: continue
        if not (_quotes_balanced(left) and _quotes_balanced(right)): continue
        out.append((left, right, kind))
    return out


def _best_split(text, limit, prefer_long_left):
    cands = _split_candidates(text)
    ok_left = [c for c in cands if len(c[0]) <= limit]
    if not ok_left: return None
    commas = [c for c in ok_left if c[2] == "comma"]
    if commas: ok_left = commas      # 쉼표가 자연스러운 끊는 자리라 있으면 연결어미보다 먼저 쓴다
    both = [c for c in ok_left if len(c[1]) <= limit]
    if both and not prefer_long_left:
        return min(both, key=lambda c: max(len(c[0]), len(c[1])) - (3 if c[2] == "comma" else 0))
    return max(ok_left, key=lambda c: len(c[0]) + (3 if c[2] == "comma" else 0))


def autofix_style(s):
    """문체 기준(문장 길이 40자·첫 문장 30자)만 결정론으로 교정한다 — 쉼표·연결어미 뒤에서 문장을 둘로 나눈다(낱말·의미는 그대로, 따옴표 안은 안 끊음).
    안전 기준(과학·단정·종교·이미지 소재)은 건드리지 않는다. 장면 번호는 나뉜 두 조각이 같이 물려받고 situation_idx 는 밀린 만큼 보정한다.
    반환: (같은 객체, 교정 기록 목록). 나눌 곳이 없거나 문장이 14개를 넘게 되면 그 문장은 그대로 두어 검사기가 사유를 되먹임한다."""
    fixes = []
    try:
        sents = s["sentences"]
        for x in sents: x["text"] = x["text"].strip()
    except Exception:
        return s, fixes
    i = 0
    while i < len(sents):
        limit = FIRST_MAX if i == 0 else SENT_MAX
        t = sents[i]["text"]
        if len(t) > limit and len(sents) < MAX_SENTENCES:
            c = _best_split(t, limit, prefer_long_left=(i == 0))
            if c:
                left, right, kind = c
                sc = sents[i].get("scene", 0)
                sents[i]["text"] = left
                sents.insert(i + 1, {"text": right, "scene": sc})
                si = s.get("situation_idx")
                if isinstance(si, int) and si > i: s["situation_idx"] = si + 1
                fixes.append(f"{i + 1}번째 문장({len(t)}자)을 {kind} 뒤에서 {len(left)}자+{len(right)}자로 분할")
                continue   # 오른쪽 조각이 아직 길면 다음 반복에서 다시 본다
        i += 1
    return s, fixes


PRACTICE_END_RE = re.compile(r"(?:보세요|하세요|봐요|써 보|적어 보|해요)[.!]?$")


def assign_practice_idx(s):
    """실천 문장 지정(R4): 모델이 고르지 않고 코드가 찾는다 — '~해 보세요'(보세요)로 끝나는 마지막 문장, 없으면 '~하세요', 없으면 기존 느슨한 어미.
    하나도 없으면 practice_idx 를 None 으로 둬서 검사기가 그것만 되먹임하게 한다."""
    sents = [x["text"].strip() for x in s.get("sentences", [])]
    for pat in (r"보세요[.!]?$", r"하세요[.!]?$"):
        hits = [i for i, t in enumerate(sents) if re.search(pat, t)]
        if hits:
            s["practice_idx"] = hits[-1]; return s
    hits = [i for i, t in enumerate(sents) if PRACTICE_END_RE.search(t)]
    s["practice_idx"] = hits[-1] if hits else None
    return s


def generate_script(topic, setting="", max_attempts=5, trace=None):
    """대본을 만들고 검사한다. 매 시도: Claude → 문체 자동 교정(autofix_style) → 실천 문장 지정 → 검사(validate_script).
    탈락하면 구체적 사유(몇 번째 문장 몇 자·무엇을 바꿀지)를 다음 프롬프트에 되먹임한다. trace 목록을 주면 시도마다 {attempt, fixes, problems} 를 기록한다.
    반환: (대본, 누적 usage {input_tokens, output_tokens, attempts})."""
    feedback = ""
    recent = recent_titles()
    total = {"input_tokens": 0, "output_tokens": 0, "attempts": 0}
    for attempt in range(1, max_attempts + 1):
        print(f"  대본 생성 {attempt}/{max_attempts} ...")
        s, usage = claude_json(quality_prompt(topic, feedback, recent, setting))
        total["attempts"] += 1
        total["input_tokens"] += usage.get("input_tokens", 0) or 0
        total["output_tokens"] += usage.get("output_tokens", 0) or 0
        s, fixes = autofix_style(s)
        s = assign_practice_idx(s)
        if fixes: print("    자동 교정: " + " / ".join(fixes))
        probs = validate_script(s)
        if trace is not None: trace.append({"attempt": attempt, "fixes": fixes, "problems": probs})
        if not probs:
            return s, total
        feedback = "\n".join(f"  {k + 1}) {x}" for k, x in enumerate(probs))
        print(f"    검사 미통과: {' / '.join(probs)}")
    raise RuntimeError(f"대본이 {max_attempts}회 모두 기준을 통과하지 못했다: " + " / ".join(probs))


def claude_cost_usd(tokens):
    return round((tokens["input_tokens"] * CLAUDE_PRICE_PER_MTOK[0] + tokens["output_tokens"] * CLAUDE_PRICE_PER_MTOK[1]) / 1e6, 4)


def image_stats(path):
    """생성 이미지 검사(M1): 16x28 회색조 평균·표준편차. 파일이 깨지면 (0,0)."""
    try:
        from PIL import Image
        im = Image.open(path).convert("L").resize((32, 56))
        px = list(im.getdata())
        m = sum(px) / len(px)
        sd = (sum((v - m) ** 2 for v in px) / len(px)) ** 0.5
        return round(m, 1), round(sd, 1)
    except Exception:
        return 0.0, 0.0


def image_ok(path):
    m, sd = image_stats(path)
    return (m >= IMG_MIN_MEAN and sd >= IMG_MIN_STD), m, sd


VISION_CALL_RESERVE_USD = 0.012   # 이미지 1장 비전 검사 호출 1회의 예약 비용(실측 토큰은 CLAUDE_SPENT 에 합산된다 — 이 값은 호출 전 게이트용 상한 추정)
VISION_PROMPT = (
    "이 이미지는 지친 직장인을 위로하는 쇼츠의 배경 그림이다. 아래를 엄격히 판정해 JSON만 출력하라(설명 금지).\n"
    "{\"rope_or_noose\": 밧줄·끈·줄·사슬·체인·케이블·전선·매달린 고리·올가미·목을 맨다고 읽힐 수 있는 모양이 하나라도 보이면 true(식물 줄기·창틀·커튼 끈처럼 분명히 무해한 것만 false),"
    "\"text_or_logo\": 간판·포스터·책 표지·서류·라벨·상표·서명·워터마크에 글자나 글자처럼 보이는 무늬(알아볼 수 없게 뭉개진 것 포함)가 눈에 띄게 보이면 true,"
    "\"face\": 또렷한 사람 얼굴이 보이면 true,"
    "\"unsafe_other\": 자해·폭력·무기·피·병원 도구·어둡고 섬뜩한 분위기 중 하나라도 있으면 true,"
    "\"note\": 근거 한 줄}"
)


def image_vision_problems(path):
    """생성 이미지를 Claude 비전으로 검사(올가미·밧줄·가짜 글자·얼굴·위험 요소). 반환: 문제 목록(빈 목록 = 통과).
    호출·파싱이 실패하면 통과로 보지 않는다(fail-closed). 렌더에서 잘려 나가는 아래 12%는 빼고 본다. 토큰은 CLAUDE_SPENT 에 합산."""
    import base64, io, sys as _sys
    _sys.path.insert(0, os.path.join(HOME, "lighthouse-media", "scripts", "lib"))
    import shorts_render as R
    try:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        im = im.crop((0, 0, w, int(h * (1 - R.BOTTOM_CROP)))).resize((512, int(512 * h * (1 - R.BOTTOM_CROP) / w)))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": "claude-sonnet-4-6", "max_tokens": 300, "messages": [{"role": "user", "content": [
                              {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}, {"type": "text", "text": VISION_PROMPT}]}]}, timeout=90)
        j = r.json()
        u = j.get("usage") or {}
        CLAUDE_SPENT["calls"] += 1
        CLAUDE_SPENT["input_tokens"] += u.get("input_tokens", 0) or 0
        CLAUDE_SPENT["output_tokens"] += u.get("output_tokens", 0) or 0
        raw = j["content"][0]["text"]
        v = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except Exception as e:
        return [f"비전 검사 실패({type(e).__name__}: {str(e)[:120]}) — 검사하지 못했으므로 통과로 보지 않는다"]
    probs = []
    if v.get("rope_or_noose"): probs.append("밧줄·끈·올가미 형상")
    if v.get("text_or_logo"): probs.append("글자·로고·서명 형상")
    if v.get("face"): probs.append("또렷한 얼굴")
    if v.get("unsafe_other"): probs.append("위험·섬뜩한 요소")
    if probs: probs.append("근거: " + str(v.get("note", ""))[:100])
    return probs


def video_dark_problems(path, ffmpeg):
    """완성본 관문(M1): ffmpeg blackdetect + 초당 샘플 평균 밝기. 문제 목록(빈 목록 = 통과)."""
    probs = []
    r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-an", "-vf", "blackdetect=d=0.5:pic_th=0.90:pix_th=0.15", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0: probs.append(f"blackdetect 실행 실패(ffmpeg 종료 코드 {r.returncode}) — 검사하지 못했으므로 통과로 보지 않는다")
    segs = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    if segs: probs.append(f"blackdetect 검은 구간 {segs}")
    r = subprocess.run([ffmpeg, "-v", "error", "-i", path, "-an", "-vf", "fps=1,scale=16:28,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    fr = 16 * 28
    data = r.stdout
    if r.returncode != 0 or len(data) < fr: probs.append("초당 밝기 샘플을 얻지 못했다(ffmpeg 실패) — 통과로 보지 않는다")
    dark = []
    for k in range(len(data) // fr):
        chunk = data[k * fr:(k + 1) * fr]
        if sum(chunk) / fr < VIDEO_MIN_SECOND_MEAN: dark.append(k)
    if dark: probs.append(f"초당 평균 밝기 {VIDEO_MIN_SECOND_MEAN:.0f} 미만인 초 {dark}")
    return probs


def _ffprobe_bin():
    return FFMPEG.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG.endswith("ffmpeg.exe") else "ffprobe"


def video_spec_problems(path):
    """업로드 전 규격 관문: h264 1080x1920 + aac + 길이 LEN_MIN~LEN_MAX. ffprobe 실패도 문제로 본다(fail-closed)."""
    try:
        r = subprocess.run([_ffprobe_bin(), "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration", "-of", "json", path],
                           capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if r.returncode != 0: return [f"ffprobe 실행 실패(종료 코드 {r.returncode})"]
        j = json.loads(r.stdout)
    except Exception as e:
        return [f"ffprobe 실행 실패: {e}"]
    probs = []
    st = j.get("streams", [])
    v = [x for x in st if x.get("codec_type") == "video"]
    a = [x for x in st if x.get("codec_type") == "audio"]
    if not v or v[0].get("codec_name") != "h264" or (v[0].get("width"), v[0].get("height")) != (1080, 1920):
        probs.append(f"영상 스트림이 h264 1080x1920이 아니다: {v[:1]}")
    if not a or a[0].get("codec_name") != "aac": probs.append(f"오디오 스트림이 aac가 아니다: {a[:1]}")
    try:
        dur = float(j["format"]["duration"])
        if not (LEN_MIN <= dur <= LEN_MAX): probs.append(f"길이 {dur:.1f}s — {LEN_MIN:.0f}~{LEN_MAX:.0f}초 밖")
    except Exception:
        probs.append("길이를 읽지 못했다")
    return probs


def cost_gate(claude_usd, tts_usd, image_usd, budget=None):
    """편당 비용 게이트: Claude 대본(재시도 포함) + TTS + 이미지(재생성 포함) 합계가 상한을 넘으면 (False, 합계). 상한 이하면 (True, 합계)."""
    budget = PER_VIDEO_BUDGET_USD if budget is None else budget
    total = round(claude_usd + tts_usd + image_usd, 5)
    return total <= budget, total


def _log_failure(name, code, reason):
    """fail-closed 기록 — 업로드하지 않은 이유를 failures.log 에 남긴다(폴백 없음: 그날은 건너뛴다)."""
    msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {name} exit={code} 업로드 안 함: {reason}"
    print("  [fail-closed] " + msg)
    try:
        os.makedirs(QUALITY_DIR, exist_ok=True)
        with open(os.path.join(QUALITY_DIR, "failures.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass
    return code


def finalize_and_upload(final, script, tl, name, dry, privacy, spent_usd, ffmpeg=None, upload_fn=None):
    """6단계: 완성본 관문(blackdetect·밝기·규격)과 비용 합계를 모두 통과해야만 업로드 함수를 부른다. 반환: 종료 코드.
    관문이 하나라도 실패하거나 검사 자체가 실패하면 upload_fn 은 호출되지 않는다(fail-closed)."""
    ffmpeg = ffmpeg or FFMPEG
    upload_fn = upload_fn or upload_youtube_quality
    print("\n[6/6] Upload...")
    try:
        gate = video_dark_problems(final, ffmpeg) + video_spec_problems(final)
    except Exception as e:
        gate = [f"완성본 관문 실행 예외: {e}"]
    print(f"  [완성본 관문] blackdetect·초당 밝기·규격: {'통과' if not gate else '실패 — ' + '; '.join(gate)}")
    if gate: return _log_failure(name, 4, "완성본 관문 실패 — " + "; ".join(gate))
    if spent_usd > PER_VIDEO_BUDGET_USD: return _log_failure(name, 2, f"실제 누적 비용 ${spent_usd:.4f} > 상한 ${PER_VIDEO_BUDGET_USD:.2f}")
    if dry:
        print("  DRY-RUN — 업로드 생략(유튜브·인스타·페이스북 모두). 올리려면 --quality --upload (오너 승인 후)")
        return 0
    try:
        upload_fn(final, script, tl, privacy)
    except Exception as e:
        return _log_failure(name, 6, f"업로드 호출 예외: {e}")
    try:  # 올린 제목 기록(다음 대본이 겹치지 않게) — 업로드한 때만
        h = recent_titles(200) + [script["title"]]
        json.dump(h, open(HISTORY_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except OSError:
        pass
    print("  (인스타·페이스북 썸네일 게시는 품질 모드에서 하지 않는다)")
    return 0


def split_cards(text, max_lines=2, max_chars=16):
    """자막 카드 나누기 — shorts_render.split_sentence 와 같은 규칙에 '따옴표 안에서는 카드를 끊지 않는다'를 더했다(R3: "'지금은" 처럼 인용이 카드 사이에서 잘리던 문제).
    반환: [(카드 텍스트(줄바꿈 포함), 글자수)]."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(HOME, "lighthouse-media", "scripts", "lib"))
    import shorts_render as R
    lines = R.wrap_chars(text, max_chars)
    if len(lines) <= max_lines:
        return [("\n".join(lines), sum(len(x) for x in lines))]
    n_cards = -(-len(lines) // max_lines)
    words = text.split()
    total = sum(len(w) for w in words) or 1
    groups, cur, acc = [], [], 0
    quote_open, quote_start = False, 0
    for w in words:
        for ch in w:
            if ch in OPEN_Q and not quote_open:
                quote_open, quote_start = True, len(cur)
            elif ch in CLOSE_Q and quote_open:
                quote_open = False
        cur.append(w)
        acc += len(w)
        if len(groups) < n_cards - 1 and acc >= total * (len(groups) + 1) / n_cards:
            if quote_open:
                if quote_start > 0:        # 따옴표가 열린 낱말 앞에서 끊는다
                    groups.append(cur[:quote_start])
                    cur, quote_start = cur[quote_start:], 0
                continue                   # 앞에 낱말이 없으면 따옴표가 닫힐 때까지 미룬다
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    cards = []
    for g in groups:
        ls = R.wrap_chars(" ".join(g), max_chars)
        cards.append(("\n".join(ls), sum(len(x) for x in ls)))
    return cards


def speech_bounds(path, ffmpeg):
    """TTS mp3 앞뒤 무음을 잰다 → (음성 시작 오프셋, 음성 끝 오프셋) 초. 자막·타임라인을 실제 음성 시각에 맞추는 데 쓴다."""
    import array
    r = subprocess.run([ffmpeg, "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True)
    a = array.array("h")
    a.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    win = 160  # 10ms
    rms = []
    for k in range(0, len(a) - win, win):
        seg = a[k:k + win]
        rms.append((sum(v * v for v in seg) / win) ** 0.5)
    if not rms: return 0.0, len(a) / 16000.0
    thr = max(rms) * 0.06
    idx = [k for k, v in enumerate(rms) if v > thr]
    if not idx: return 0.0, len(a) / 16000.0
    return max(0.0, idx[0] * 0.01 - 0.02), min(len(a) / 16000.0, (idx[-1] + 1) * 0.01 + 0.04)


def _ffprobe_duration(path):
    ffp = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG.endswith("ffmpeg.exe") else "ffprobe"
    r = subprocess.run([ffp, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())


def build_timeline(script, chunks):
    """TTS 청크의 실제 길이로 문장·장면·자막 구간(초)을 만든다. chunks[i]['dur'] = 그 문장의 음성 길이."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(HOME, "lighthouse-media", "scripts", "lib"))
    import shorts_render as R
    t = TL_LEAD
    sents = []
    for i, (sd, ch) in enumerate(zip(script["sentences"], chunks)):
        sp = ch["off1"] - ch["off0"]   # 앞뒤 무음을 뺀 실제 음성 길이
        sents.append({"i": i, "text": sd["text"].strip(), "scene": int(sd["scene"]), "start": round(t, 3), "end": round(t + sp, 3), "audio": ch["path"],
                      "off0": round(ch["off0"], 3), "off1": round(ch["off1"], 3)})
        t += sp + TL_GAP
    total = round(sents[-1]["end"] + TL_TAIL, 3)
    # 자막 카드: 한 문장 안에서 글자 수 비례로 시간 배분(문장이 길어도 음성 구간 밖으로 안 나간다)
    subs = []
    for s in sents:
        cards = split_cards(s["text"])
        wsum = sum(c[1] for c in cards) or 1
        cur = s["start"]
        for k, (txt, wn) in enumerate(cards):
            end = s["end"] if k == len(cards) - 1 else cur + (s["end"] - s["start"]) * wn / wsum
            subs.append({"start": round(cur, 3), "end": round(end, 3), "text": txt, "sentence": s["i"]})
            cur = end
    # 마지막 문장의 자막은 끝 여운 동안 유지
    subs[-1]["end"] = total - 0.3
    scenes = []
    n_sc = len(script["scenes"])
    for si in range(n_sc):
        mine = [s for s in sents if s["scene"] == si]
        start = 0.0 if si == 0 else scenes[-1]["end"]
        end = total if si == n_sc - 1 else mine[-1]["end"] + TL_GAP / 2
        scenes.append({"index": si, "start": round(start, 3), "end": round(end, 3)})
    return {"sentences": sents, "subs": subs, "scenes": scenes, "total": total}


def mux_audio(silent, tl, bgm_path, out_path, ffmpeg):
    """나레이션(문장별 mp3를 시작 시각에 배치) + 배경음악(나레이션 아래로 덕킹) → 통합 라우드니스 정규화 → 영상에 입힘."""
    sents, total = tl["sentences"], tl["total"]
    cmd = [ffmpeg, "-y", "-i", silent]
    for s in sents:
        cmd += ["-i", s["audio"]]
    cmd += ["-stream_loop", "-1", "-i", bgm_path]
    n = len(sents)
    parts = []
    for i, s in enumerate(sents):
        ms = int(round(s["start"] * 1000))
        parts.append(f"[{i + 1}:a]aresample=44100,atrim=start={s['off0']:.3f}:end={s['off1']:.3f},asetpts=PTS-STARTPTS,adelay={ms}|{ms}[n{i}]")
    parts.append("".join(f"[n{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total:.3f},asplit=2[nar][narsc]")
    parts.append(f"[{n + 1}:a]aresample=44100,volume=0.30,afade=t=out:st={total - 1.5:.2f}:d=1.5[bg]")
    parts.append("[bg][narsc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=400[duck]")
    parts.append(f"[nar][duck]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError("오디오 합성 실패: " + r.stderr[-500:])
    return out_path


def upload_youtube_quality(vpath, script, tl, privacy="unlisted"):
    """품질 모드 유튜브 업로드(--upload 명시 때만 호출). 인스타·페이스북은 올리지 않는다."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    ytp = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
    creds = Credentials.from_authorized_user_info(json.load(open(ytp, encoding="utf-8")))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(ytp, "w", encoding="utf-8") as f: f.write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    tags_line = " ".join(script["hashtags"] + ["#shorts"])
    desc = f"{script['description_hook']}\n\n{script['description_body']}\n\n—\n류선희 | Lighthouse Media\n\n{tags_line}"
    body = {"snippet": {"title": script["title"] + " #shorts", "description": desc, "tags": script["tags"], "categoryId": "22", "defaultLanguage": "ko"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(vpath, mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    print(f"    https://youtube.com/shorts/{resp['id']}  (공개 범위: {privacy})")
    return resp["id"]


def quality_main(args):
    import sys as _sys, random as _random
    _sys.path.insert(0, os.path.join(HOME, "lighthouse-media", "scripts", "lib"))
    import fal_tts as T, fal_visuals as fv, shorts_render as R
    if args.upload and args.dry_run:
        print("--upload 와 --dry-run 을 함께 줄 수 없다(모순). 하나만 지정한다."); return 2
    dry = not args.upload
    name = args.name = args.name or f"quality-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    work = os.path.join(QUALITY_DIR, "work", name)
    os.makedirs(work, exist_ok=True)
    print("=" * 60)
    print(f"  LIGHTHOUSE MEDIA - Daily Video (QUALITY mode)  {name}")
    print(f"  {'DRY-RUN — 업로드하지 않음' if dry else '!! --upload 지정됨: 유튜브에 업로드한다 !!'}")
    print("=" * 60)

    # 1. 대본
    print("\n[1/6] Script...")
    args.topic = args.topic or pick_topic()
    setting = SETTINGS[abs(hash_str(name + args.topic)) % len(SETTINGS)]
    print(f"  주제: {args.topic} / 구체 상황 배경 힌트: {setting}")
    script, usage = generate_script(args.topic, setting)
    usage = {**usage, **{k: CLAUDE_SPENT[k] for k in ("input_tokens", "output_tokens")}, "api_calls": CLAUDE_SPENT["calls"]}   # 재시도·JSON 재요청까지 전부 합친 값
    claude_usd = claude_cost_usd(usage)
    print(f"  Title: {script['title']}  (공식 {script.get('formula')})  Claude 시도 {usage['attempts']}회, 토큰 in/out = {usage['input_tokens']}/{usage['output_tokens']} ≈ ${claude_usd:.4f} (단가 가정 {CLAUDE_PRICE_PER_MTOK} US$/MTok [미확인])")
    n_img = len(script["scenes"])
    tts_chars = sum(len(s["text"].strip()) for s in script["sentences"])
    est = {"tts": T.estimate_tts_cost(tts_chars), "image": round(n_img * fv.IMAGE_MODEL_COST_USD, 5)}
    ok_cost, est["total"] = cost_gate(claude_usd, est["tts"], est["image"])
    print(f"  [비용미리보기] Claude 대본 ${claude_usd:.4f}(API {usage['api_calls']}회) + TTS {tts_chars}자 ${est['tts']:.4f} + 이미지 {n_img}장 ${est['image']:.4f} = ${est['total']:.4f} (상한 ${PER_VIDEO_BUDGET_USD:.2f})")
    if not ok_cost:
        return _log_failure(name, 2, f"비용 게이트: 예상 ${est['total']:.4f} > 상한 ${PER_VIDEO_BUDGET_USD:.2f} — TTS·이미지를 호출하지 않았다")

    # 2. 나레이션
    print("\n[2/6] Narration (fal TTS)...")
    chunks, err = T.synth_chunks([s["text"].strip() for s in script["sentences"]], os.path.join(work, "tts"), name, PER_VIDEO_BUDGET_USD,
                                 voice=args.voice, speed=args.speed, spent_usd=claude_usd)
    if not chunks:
        return _log_failure(name, 1, f"TTS 실패: {err}")
    for c in chunks:
        c["dur"] = _ffprobe_duration(c["path"])
        c["off0"], c["off1"] = speech_bounds(c["path"], FFMPEG)
    voice_s = sum(c["off1"] - c["off0"] for c in chunks)   # 앞뒤 무음을 뺀 실제 음성 길이(문장 사이 휴지 제외)
    syl = sum(_syllables(s["text"]) for s in script["sentences"])
    span = voice_s + TL_GAP * (len(chunks) - 1)   # 첫 음성 시작~마지막 음성 끝(문장 사이 휴지 포함) = 벤치마크 말 속도와 같은 기준
    print(f"  음성 {voice_s:.1f}s(휴지 제외) / 말 시작~끝 {span:.1f}s, 한글 {syl}음절 → {syl / span:.2f} 음절/초 (벤치마크 기준, 중앙 ≈6; 휴지 제외 {syl / voice_s:.2f})")

    # 3. 타임라인(+길이 검사)
    tl = build_timeline(script, chunks)
    print(f"  타임라인: 총 {tl['total']:.1f}s, 장면 {len(tl['scenes'])}개 {[round(s['end'] - s['start'], 1) for s in tl['scenes']]}, 자막 {len(tl['subs'])}장")
    odd = [round(x["end"] - x["start"], 1) for x in tl["scenes"] if not (3.0 <= x["end"] - x["start"] <= 10.0)]
    if odd: print(f"  [장면 길이 주의] 3~10초 밖의 장면 {odd}s — 루브릭 G1")
    if not (LEN_MIN <= tl["total"] <= LEN_MAX):
        print(f"  [길이 경고] {tl['total']:.1f}s — 루브릭 L1은 {LEN_MIN:.0f}~{LEN_MAX:.0f}초. 이미지 호출 전에 중단한다(--speed 조정 또는 대본 재생성)."); return _log_failure(name, 3, f"길이 {tl['total']:.1f}s가 {LEN_MIN:.0f}~{LEN_MAX:.0f}초 밖")

    # 4. 배경 이미지
    print("\n[3/6] Background images (fal)...")
    img_dir = os.path.join(work, "img"); os.makedirs(img_dir, exist_ok=True)
    key = fv.load_fal_key()
    if not key:
        return _log_failure(name, 1, "FAL_KEY 없음")
    paths, img_calls, img_log = [], 0, []
    for i, sc in enumerate(script["scenes"]):
        base = sc["image_prompt"].strip().rstrip(".")
        variants = [base + IMAGE_STYLE_SUFFIX, base + IMAGE_RETRY_SUFFIX + IMAGE_STYLE_SUFFIX, IMAGE_FALLBACK_PROMPTS[i % len(IMAGE_FALLBACK_PROMPTS)] + IMAGE_STYLE_SUFFIX]
        out, got = None, None
        for att, prompt in enumerate(variants[:IMG_MAX_ATTEMPTS], 1):
            if not cost_gate(claude_cost_usd(CLAUDE_SPENT) + VISION_CALL_RESERVE_USD, est["tts"], (img_calls + 1) * fv.IMAGE_MODEL_COST_USD)[0]:
                return _log_failure(name, 2, f"비용 게이트: 이미지 재시도 {img_calls + 1}번째 호출이면 상한 ${PER_VIDEO_BUDGET_USD:.2f}을 넘는다(Claude·TTS 포함)")
            img_calls += 1
            outp, err = fv.generate_scene_image(prompt, os.path.join(img_dir, f"scene_{i:02d}.png"), key=key)
            if not outp:
                print(f"  장면 {i} 시도 {att}: 생성 실패 {err}"); img_log.append({"scene": i, "attempt": att, "error": str(err)[:120]}); continue
            ok, m, sd = image_ok(outp)
            img_log.append({"scene": i, "attempt": att, "mean": m, "std": sd, "ok": ok})
            print(f"  장면 {i} 시도 {att}: 평균 {m} 표준편차 {sd} → {'OK' if ok else '불량(검거나 단색) — 다시 만든다'}")
            if not ok: continue
            vp = image_vision_problems(outp)
            img_log[-1]["vision"] = vp
            print(f"    비전 검사: {'통과' if not vp else '불량 — ' + ' / '.join(vp) + ' — 다시 만든다'}")
            if not vp:
                out = outp; break
        if not out:
            return _log_failure(name, 1, f"장면 {i}: {IMG_MAX_ATTEMPTS}번 모두 빈/검은 이미지·비전 검사 탈락(올가미·가짜 글자 등)이거나 생성 실패")
        paths.append(out)
    est["image"] = round(img_calls * fv.IMAGE_MODEL_COST_USD, 5)
    claude_usd = claude_cost_usd(CLAUDE_SPENT)   # 대본 + 이미지 비전 검사까지 실측 토큰으로 다시 계산
    usage = {**usage, "input_tokens": CLAUDE_SPENT["input_tokens"], "output_tokens": CLAUDE_SPENT["output_tokens"], "api_calls": CLAUDE_SPENT["calls"]}
    est["total"] = cost_gate(claude_usd, est["tts"], est["image"])[1]
    print(f"  이미지 호출 {img_calls}회(장면 {n_img}장 + 재생성 {img_calls - n_img}회) = ${est['image']:.4f}")
    fv.log_run_cost("quality_image_batch", fv.IMAGE_MODEL, img_calls, est["image"], reel_name=name)
    for sc, pth in zip(tl["scenes"], paths): sc["image"] = pth

    # 5. 렌더
    print("\n[4/6] Render frames...")
    silent = os.path.join(work, "silent.mp4")
    R.render_video(tl["scenes"], script["title_lines"], tl["subs"], tl["total"], silent, ffmpeg=FFMPEG)

    print("\n[5/6] Mix audio...")
    cat = script.get("category", "comfort")
    bgm_dir = os.path.join(HOME, "lighthouse-media", "assets", "bgm")
    pool = sorted(f for f in os.listdir(bgm_dir) if f.endswith(".mp3") and CATEGORY_BGM.get(cat, "trend-comfort") in f) or sorted(f for f in os.listdir(bgm_dir) if f.endswith(".mp3"))
    bgm = _random.Random(name).choice(pool)
    print(f"  BGM: {bgm} (카테고리 {cat})")
    final = os.path.join(QUALITY_DIR, name + ".mp4")
    mux_audio(silent, tl, os.path.join(bgm_dir, bgm), final, FFMPEG)
    print(f"  OK {final}  {os.path.getsize(final) / 1048576:.1f}MB")
    report = {"name": name, "topic": args.topic, "script": script, "timeline": {k: v for k, v in tl.items() if k != "sentences"},
              "sentences": [{k: v for k, v in s.items() if k != "audio"} for s in tl["sentences"]],
              "voice": {"model": T.TTS_MODEL, "voice": args.voice or T.DEFAULT_VOICE, "speed": args.speed if args.speed is not None else T.DEFAULT_SPEED,
                        "voice_sec": round(voice_s, 2), "span_sec": round(span, 2), "syllables": syl, "syll_per_s": round(syl / span, 2), "syll_per_s_excl_gaps": round(syl / voice_s, 2)},
              "cost_usd": {**est, "image_calls": img_calls, "claude_tokens": usage, "claude_usd_est": claude_usd, "claude_price_assumed_per_mtok": CLAUDE_PRICE_PER_MTOK,
                           "total_incl_claude": est["total"], "budget_usd": PER_VIDEO_BUDGET_USD, "pricing": T.TTS_PRICING_SOURCE},
              "setting_hint": setting, "image_checks": img_log, "bgm": bgm, "dry_run": dry, "privacy": args.privacy}
    code = finalize_and_upload(final, script, tl, name, dry, args.privacy, est["total"])
    report["gate_exit_code"] = code
    json.dump(report, open(os.path.join(QUALITY_DIR, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return code


def script_only_main(args):
    """--script-only: 대본만 생성·검사한다(fal·이미지·TTS·업로드 없음). 주제별 통과 여부·시도 횟수·탈락 사유·Claude 비용을 표로 남긴다.
    --topics-n 개의 주제를 TOPICS 에서 고르고(--topic 을 주면 그 하나), --attempts 안에 통과하면 합격. 누적 Claude 비용이 --cost-cap 을 넘을 것 같으면 남은 주제는 건너뛴다."""
    n = 1 if args.topic else args.topics_n
    topics = [args.topic] if args.topic else [TOPICS[(k * 3) % len(TOPICS)] for k in range(n)]
    rows = []
    t0 = dict(CLAUDE_SPENT)
    for k, topic in enumerate(topics):
        spent_before = claude_cost_usd(CLAUDE_SPENT)
        if spent_before + 0.04 > args.cost_cap:
            rows.append({"topic": topic, "passed": None, "note": f"비용 상한 ${args.cost_cap:.2f} 때문에 건너뜀"}); continue
        setting = SETTINGS[abs(hash_str(f"script-only-{k}" + topic)) % len(SETTINGS)]
        print(f"\n=== [{k + 1}/{len(topics)}] {topic}  (배경 힌트: {setting}) ===")
        trace = []
        row = {"topic": topic, "setting": setting, "trace": trace}
        try:
            script, usage = generate_script(topic, setting, max_attempts=args.attempts, trace=trace)
            row.update({"passed": True, "attempts": usage["attempts"], "title": script["title"]})
        except RuntimeError as e:
            row.update({"passed": False, "attempts": len(trace), "error": str(e)[:300]})
        row["claude_usd"] = round(claude_cost_usd(CLAUDE_SPENT) - spent_before, 4)
        rows.append(row)
    total_usd = claude_cost_usd({k: CLAUDE_SPENT[k] - t0[k] for k in ("input_tokens", "output_tokens")})
    ran = [r for r in rows if r.get("passed") is not None]
    ok = [r for r in ran if r["passed"]]
    print("\n" + "=" * 70)
    print(f"  --script-only 결과: {len(ok)}/{len(ran)} 통과 (한도 {args.attempts}회 이내)  Claude ${total_usd:.4f} [단가 가정 {CLAUDE_PRICE_PER_MTOK}]")
    for r in rows:
        if r.get("passed") is None: print(f"  - {r['topic']}: {r['note']}"); continue
        first = r["trace"][0]["problems"] if r["trace"] else []
        print(f"  - {'PASS' if r['passed'] else 'FAIL'} {r['attempts']}회 ${r['claude_usd']:.4f} {r['topic']} | 1회차 사유: {len(first)}건")
    os.makedirs(QUALITY_DIR, exist_ok=True)
    out = os.path.join(QUALITY_DIR, f"script-only-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    json.dump({"attempts_limit": args.attempts, "cost_cap": args.cost_cap, "claude_usd": total_usd, "passed": len(ok), "ran": len(ran), "rows": rows}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  기록: {out}")
    return 0 if len(ok) == len(ran) and ran else 1


def run_quality(args):
    """fail-closed 최상위: 어떤 예외든 업로드 없이 사유를 남기고 비영 종료 코드를 돌려준다(폴백 없음 — 그날은 건너뛴다)."""
    name = args.name or "quality-unnamed"
    try:
        return quality_main(args)
    except BaseException as e:   # noqa: B036 — KeyboardInterrupt 포함, 어떤 중단이든 업로드로 이어지지 않는다
        cs = CLAUDE_SPENT
        return _log_failure(name, 5, f"{type(e).__name__}: {str(e)[:300]} (Claude 호출 {cs['calls']}회, 토큰 in/out {cs['input_tokens']}/{cs['output_tokens']} ≈ ${claude_cost_usd(cs):.4f})")


def parse_args(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Lighthouse Media daily video")
    ap.add_argument("--quality", action="store_true", help="새 방식(한국어 나레이션·AI 배경·동기 자막). 기본 dry-run")
    ap.add_argument("--upload", action="store_true", help="--quality 에서만: 실제로 유튜브에 올린다(명시하지 않으면 올리지 않음)")
    ap.add_argument("--dry-run", action="store_true", help="업로드하지 않는다(기존 방식에서는 인코딩까지만)")
    ap.add_argument("--topic", default=None, help="없으면 날짜로 TOPICS에서 순환 선택")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--speed", type=float, default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--script-only", action="store_true", help="대본만 생성·검사(이미지·TTS·업로드 없음)해서 통과율을 잰다")
    ap.add_argument("--topics-n", type=int, default=5, help="--script-only 에서 시험할 주제 수(--topic 을 주면 그 하나)")
    ap.add_argument("--attempts", type=int, default=5, help="--script-only 에서 주제당 최대 시도 횟수(합격 기준)")
    ap.add_argument("--cost-cap", type=float, default=0.60, help="--script-only 누적 Claude 비용 상한(US$)")
    ap.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted", help="유튜브 공개 범위(기본 unlisted=일부공개). 기존 방식·--quality 업로드 둘 다에 적용")
    return ap.parse_args(argv)


if __name__ == "__main__":
    _a = parse_args()
    if _a.script_only:
        sys.exit(script_only_main(_a))
    if _a.quality:
        if _a.upload and _a.dry_run:
            print("--upload 와 --dry-run 을 함께 줄 수 없다(모순). 하나만 지정한다."); sys.exit(2)
        sys.exit(run_quality(_a))
    if _a.upload and _a.dry_run:
        print("--upload 와 --dry-run 을 함께 줄 수 없다(모순)."); sys.exit(2)
    if _a.upload:
        print("--upload 는 --quality 와 함께만 쓴다(기존 방식은 플래그 없이 올린다)."); sys.exit(2)
    main(dry_run=_a.dry_run, privacy=_a.privacy)
