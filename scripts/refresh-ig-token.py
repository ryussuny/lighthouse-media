"""Instagram/Facebook 장기 토큰 자동 갱신
- 60일 장기 토큰을 만료 전에 갱신
- 만료 7일 전부터 자동 갱신 시도
- 실행: python scripts/refresh-ig-token.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests
from datetime import datetime, timedelta

HOME = os.path.expanduser("~")
TOKENS_PATH = os.path.join(HOME, "lighthouse-media", "config", "tokens.json")

def load_tokens():
    with open(TOKENS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKENS_PATH, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)

def check_expiry(tokens):
    """토큰 만료일 확인"""
    created = datetime.fromisoformat(tokens.get('created', '2026-04-25T00:00:00'))
    expires_days = tokens.get('expires_days', 60)
    expires_at = created + timedelta(days=expires_days)
    days_left = (expires_at - datetime.now()).days
    return expires_at, days_left

def refresh_token(token_key, token_value):
    """Facebook Graph API로 장기 토큰 갱신"""
    url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': '985982700527891',  # Lighthouse Media Auto 앱 ID
        'fb_exchange_token': token_value,
    }
    # 장기 토큰은 client_secret 없이 갱신 가능 (같은 토큰으로 연장)
    r = requests.get(url, params=params, timeout=30)
    data = r.json()

    if 'access_token' in data:
        return data['access_token'], data.get('expires_in', 5184000)

    # 대안: 토큰 자체 갱신 (long-lived → long-lived)
    url2 = f"https://graph.facebook.com/v21.0/me?fields=id&access_token={token_value}"
    r2 = requests.get(url2, timeout=15)
    if 'id' in r2.json():
        print(f"    토큰 유효 확인 (갱신은 앱 시크릿 필요)")
        return None, None

    return None, None

def main():
    tokens = load_tokens()
    expires_at, days_left = check_expiry(tokens)

    print("=" * 50)
    print("  Instagram/Facebook 토큰 상태 확인")
    print("=" * 50)
    print(f"  생성일: {tokens.get('created', '?')}")
    print(f"  만료일: {expires_at.strftime('%Y-%m-%d')}")
    print(f"  남은 일수: {days_left}일")

    if days_left > 7:
        print(f"\n  ✓ 토큰 정상 (만료까지 {days_left}일)")

        # 각 토큰 유효성 검증
        for key, name in [('instagram', 'Lighthouse IG'), ('facebook_page', 'Lighthouse FB'),
                          ('church_page', '동산교회')]:
            token = tokens.get(key, '')
            if token:
                r = requests.get(f"https://graph.facebook.com/v21.0/me?access_token={token}", timeout=10)
                status = "유효" if 'id' in r.json() else "만료/오류"
                print(f"    {name}: {status}")

    elif days_left > 0:
        print(f"\n  ⚠ 곧 만료! ({days_left}일 남음)")
        print("  갱신을 시도합니다...")

        for key in ['instagram', 'facebook_page', 'church_page']:
            old_token = tokens.get(key, '')
            if not old_token: continue
            new_token, expires_in = refresh_token(key, old_token)
            if new_token:
                tokens[key] = new_token
                tokens['expires_days'] = expires_in // 86400
                tokens['created'] = datetime.now().isoformat()
                print(f"    {key}: 갱신 성공! ({expires_in//86400}일)")
            else:
                print(f"    {key}: 자동 갱신 실패 — 수동 갱신 필요")
                print(f"    → 브라우저에서 Facebook 개발자 도구로 새 토큰 발급 필요")

        save_tokens(tokens)
        print(f"\n  tokens.json 업데이트 완료")

    else:
        print(f"\n  ✗ 토큰 만료됨! ({abs(days_left)}일 전)")
        print("  → 수동 갱신 필요: Facebook 개발자 도구에서 새 토큰 발급")

    print(f"\n{'=' * 50}")

if __name__ == '__main__':
    main()
