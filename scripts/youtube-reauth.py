"""YouTube 토큰 재인증 스크립트
브라우저가 열리면 Google 계정으로 로그인 → 권한 허용하면 자동 완료됩니다."""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os

HOME = os.path.expanduser("~")
TOKEN_PATH = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")

# 기존 토큰에서 client 정보 읽기
old = json.load(open(TOKEN_PATH, encoding='utf-8'))
CLIENT_ID = old['client_id']
CLIENT_SECRET = old['client_secret']
SCOPES = old['scopes']

print("=" * 50)
print("  YouTube 토큰 재인증")
print("=" * 50)
print(f"  토큰 파일: {TOKEN_PATH}")
print(f"  Client ID: {CLIENT_ID[:20]}...")
print(f"  Scopes: {len(SCOPES)}개")
print()

from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth2 flow 실행 (브라우저 자동 열림)
flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    scopes=SCOPES,
)

print("  브라우저가 열립니다. Google 계정으로 로그인해주세요...")
print()

creds = flow.run_local_server(port=8090, prompt='consent')

# 새 토큰 저장
token_data = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": list(creds.scopes),
    "universe_domain": "googleapis.com",
    "account": "",
    "expiry": creds.expiry.isoformat() + "Z" if creds.expiry else "",
}

with open(TOKEN_PATH, 'w', encoding='utf-8') as f:
    json.dump(token_data, f, indent=2)

print("=" * 50)
print("  ✓ 토큰 재인증 완료!")
print(f"  ✓ 저장: {TOKEN_PATH}")
print(f"  ✓ 만료: {token_data['expiry']}")
print("=" * 50)
