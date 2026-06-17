"""YouTube OAuth 토큰 재인증 (브라우저 로그인 필요)"""
import json, os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

HOME = os.path.expanduser("~")
CLIENT_SECRET = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "client_secret.json")
TOKEN_PATH = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl',
]

print("YouTube OAuth 재인증을 시작합니다...")
print("브라우저가 열리면 Google 계정으로 로그인하세요.\n")

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
creds = flow.run_local_server(port=8080)

with open(TOKEN_PATH, 'w') as f:
    f.write(creds.to_json())

print(f"\n토큰 갱신 완료!")
print(f"저장 위치: {TOKEN_PATH}")
print(f"만료일: {creds.expiry}")
