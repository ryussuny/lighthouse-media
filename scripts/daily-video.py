"""매일 고퀄리티 숏츠 영상 1편 → YouTube + Instagram + Facebook 동시 업로드"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

HOME = os.path.expanduser("~")
TODAY = datetime.now().strftime("%Y-%m-%d")
OUT = os.path.join(HOME, "lighthouse-media", "output", TODAY)
os.makedirs(OUT, exist_ok=True)

API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
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

def main():
    print("=" * 60)
    print(f"  LIGHTHOUSE MEDIA - Daily Video")
    print(f"  {TODAY}")
    print("=" * 60)

    # 1. 스크립트
    print("\n[1/4] Script...")
    raw = claude(
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

    start = raw.find("{"); end = raw.rfind("}")+1
    script = json.loads(raw[start:end])
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

    # 4. Upload
    print("\n[4/4] Uploading...")

    # YouTube
    print("  YouTube...")
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    ytp = os.path.join(HOME, "OneDrive", "\ubc14\ud0d5 \ud654\uba74", "lighthouse_media", "token_lighthouse.json")
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
        'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
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

if __name__ == "__main__":
    main()
