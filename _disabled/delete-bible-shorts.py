"""말씀 쇼츠 45개 YouTube 삭제"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
TOKEN_PATH = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")

BIBLE_IDS = [
    "JyOHSS7_wiQ","8gagLk6s17c","l-3gUiWMviU","SGrvvY1xSL0","ogBOpJ0Fvtg",
    "1byXJhd18YM","spO7TaZ7TWA","6H0R4nDXDVk","U0tOI430YRY","SCj1unLzLAg",
    "cviAv5WMet8","VCHvlkW2JQk","-1efNVcNiYI","y64HzWlA2tI","4CPhT-xc9RQ",
    "cA9y50qRUUU","Sq2sZ8hYU1w","J5uhtU-_m0I","6Nfa-ZtZaEM","kqxwhr-DTUk",
    "CzqH5daHhtU","g9GzOaG0ozA","nQAgvHb6omE","rUlxD4Gw_eg","41_jsoQQG-I",
    "wybVIYj-o24","rPdUJhqrcBM","hEun8EdLS1w","WGaLfQqr9Yc","lt5am-sirqA",
    "ZFWbZUJQnHc","j4v9R7P6x8Y","QWlD1EjSzn4","3UK-C8aZftI","9XtafHwP-q4",
    "IoqPaXIu9Vg","w7LrbjtC5go","XM4PFAibGu4","TlqWfpGQHBQ","5cfObTs6IC0",
    "5ZCzsMiN9FM","T6ZJk6eH7ww","mCaVWXW0efE","J5_WmjBWuvc","7FW0hTP1-8w",
]

# 인증
creds = Credentials.from_authorized_user_info(json.load(open(TOKEN_PATH)))
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_PATH, 'w') as f: f.write(creds.to_json())

yt = build('youtube', 'v3', credentials=creds)

ok, fail = 0, 0
for i, vid in enumerate(BIBLE_IDS, 1):
    try:
        yt.videos().delete(id=vid).execute()
        print(f"  [{i}/{len(BIBLE_IDS)}] 삭제 완료: {vid}")
        ok += 1
    except Exception as e:
        print(f"  [{i}/{len(BIBLE_IDS)}] 실패 ({vid}): {str(e)[:60]}")
        fail += 1

print(f"\n완료: 삭제 {ok}개 / 실패 {fail}개")
