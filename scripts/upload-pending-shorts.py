"""대기 중인 숏츠 영상을 YouTube에 업로드 (할당량 회복 후 실행)"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, glob, time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

HOME = os.path.expanduser("~")
SHORTS_DIR = os.path.join(HOME, "lighthouse-media", "output")

ytp = os.path.join(HOME, "OneDrive", "\ubc14\ud0d5 \ud654\uba74", "lighthouse_media", "token_lighthouse.json")
ytk = json.load(open(ytp))
creds = Credentials.from_authorized_user_info(ytk)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(ytp, 'w') as f: f.write(creds.to_json())

yt = build('youtube', 'v3', credentials=creds)

# 모든 날짜 폴더에서 mp4 파일 찾기
videos = sorted(glob.glob(os.path.join(SHORTS_DIR, "**", "shorts", "*.mp4"), recursive=True))

titles = {
    "stress-3sec": "3초 만에 스트레스 날리는 법 #shorts",
    "morning-2min": "아침 2분이면 하루가 달라집니다 #shorts",
    "burnout-signal": "번아웃 5가지 신호 3개 이상이면 위험 #shorts",
    "comfort-words": "오늘 하루 수고한 당신에게 #shorts #힐링",
    "energy-secret": "직장인 에너지 충전 비밀 3가지 #shorts",
    "daily-shorts": "오늘의 힐링 숏츠 #shorts #직장인",
}

uploaded_file = os.path.join(HOME, "lighthouse-media", "data", "uploaded-videos.json")
uploaded = json.load(open(uploaded_file, encoding='utf-8')) if os.path.exists(uploaded_file) else []

print(f"Found {len(videos)} videos, {len(uploaded)} already uploaded")

count = 0
for vpath in videos:
    if vpath in uploaded: continue
    name = os.path.splitext(os.path.basename(vpath))[0]
    title = titles.get(name, f"{name} #shorts #힐링 #직장인")

    print(f"  Uploading: {name}...")
    try:
        body = {
            'snippet': {'title': title, 'description': f'{title}\n\nLighthouse Media\n#번아웃회복 #자기계발 #직장인힐링 #마음관리',
                        'tags': ['shorts','번아웃','자기계발','직장인','힐링','마음관리'], 'categoryId': '22', 'defaultLanguage': 'ko'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        }
        media = MediaFileUpload(vpath, mimetype='video/mp4', resumable=True)
        req = yt.videos().insert(part='snippet,status', body=body, media_body=media)
        resp = None
        while resp is None: _, resp = req.next_chunk()
        vid = resp['id']
        print(f"    OK! https://youtube.com/shorts/{vid}")
        uploaded.append(vpath)
        count += 1

        try:
            yt.playlistItems().insert(part='snippet', body={
                'snippet': {'playlistId': 'PLqShegXvrK3wiKvpIfJth9m5Fs7j8Qmgm',
                            'resourceId': {'kind': 'youtube#video', 'videoId': vid}}
            }).execute()
        except: pass
        time.sleep(3)
    except Exception as e:
        print(f"    FAIL: {e}")
        break  # 할당량 초과면 중단

os.makedirs(os.path.dirname(uploaded_file), exist_ok=True)
with open(uploaded_file, 'w', encoding='utf-8') as f:
    json.dump(uploaded, f)

print(f"\nUploaded {count} new videos")
