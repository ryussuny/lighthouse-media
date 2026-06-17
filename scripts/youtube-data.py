"""YouTube 채널 데이터를 JSON으로 출력"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
token_path = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")

t = json.load(open(token_path))
creds = Credentials.from_authorized_user_info(t)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_path, 'w') as f:
        f.write(creds.to_json())

yt = build('youtube', 'v3', credentials=creds)

# 채널 통계
ch = yt.channels().list(part='snippet,statistics', mine=True).execute()
item = ch['items'][0]
stats = item['statistics']

# 최근 영상
vids = yt.search().list(part='snippet', channelId=item['id'], order='date', maxResults=5, type='video').execute()
recent = []
for v in vids.get('items', []):
    vid_id = v['id']['videoId']
    # 조회수 가져오기
    vstat = yt.videos().list(part='statistics', id=vid_id).execute()
    views = vstat['items'][0]['statistics'].get('viewCount', 0) if vstat['items'] else 0
    recent.append({
        'title': v['snippet']['title'],
        'date': v['snippet']['publishedAt'][:10],
        'videoId': vid_id,
        'views': int(views),
    })

result = {
    'subscribers': int(stats.get('subscriberCount', 0)),
    'views': int(stats.get('viewCount', 0)),
    'videos': int(stats.get('videoCount', 0)),
    'title': item['snippet']['title'],
    'recentVideos': recent,
}

print(json.dumps(result, ensure_ascii=False))
