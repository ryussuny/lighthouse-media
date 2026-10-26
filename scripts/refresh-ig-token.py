"""Instagram/Facebook 장기 토큰 자동 갱신
- 60일 장기 토큰을 만료 전에 갱신
- 만료 7일 전부터 자동 갱신 시도
- 실행: python scripts/refresh-ig-token.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
from lib.redact import install as _redact_install; _redact_install()
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

GRAPH_DEBUG = "https://graph.facebook.com/v21.0/debug_token"
TOKEN_NAMES = [('instagram', 'Lighthouse IG'), ('facebook_page', 'Lighthouse FB'),
               ('church_page', '동산교회')]

def inspect_token(token):
    """Graph debug_token 으로 실제 유효 여부·만료를 읽는다. 토큰 값은 반환·출력하지 않는다.
    반환: {'ok': bool, 'valid': bool, 'expires_at': int|None, 'data_access_expires_at': int|None, 'reason': str}
    ok=False 는 조회 자체 실패(네트워크·응답 이상) — 유효/무효 판단 불가."""
    try:
        r = requests.get(GRAPH_DEBUG, params={'input_token': token, 'access_token': token}, timeout=15)
        body = r.json()
    except Exception as e:
        # 예외 메시지에는 요청 URL(토큰 포함)이 들어갈 수 있어 클래스명만 쓴다
        return {'ok': False, 'reason': f"조회 실패({type(e).__name__})"}
    if not isinstance(body, dict):
        return {'ok': False, 'reason': "조회 실패(응답 형식 이상)"}
    data = body.get('data')
    if not isinstance(data, dict):
        err = body.get('error') if isinstance(body.get('error'), dict) else {}
        msg = str(err.get('message', '응답 없음'))[:80]
        return {'ok': False, 'reason': f"조회 실패(HTTP {r.status_code}: {msg})"}
    out = {'ok': True, 'valid': bool(data.get('is_valid')),
           'expires_at': data.get('expires_at'),
           'data_access_expires_at': data.get('data_access_expires_at'), 'reason': ''}
    if not out['valid']:
        err = data.get('error') if isinstance(data.get('error'), dict) else {}
        out['reason'] = str(err.get('message', '무효 토큰'))[:80]
    return out

def _fmt_ts(ts):
    """epoch 초 → (표시 문자열, 남은 일수|None). 0/없음 = 만료 없음."""
    if not ts:
        return "만료 없음", None
    dt = datetime.fromtimestamp(int(ts))
    return dt.strftime('%Y-%m-%d'), (dt - datetime.now()).days

def main():
    tokens = load_tokens()
    changed = False

    print("=" * 50)
    print("  Instagram/Facebook 토큰 상태 확인 (Graph debug_token 실측)")
    print("=" * 50)
    # tokens.json 의 created+expires_days 는 참고용 — 실제 만료 판단에 쓰지 않는다
    try:
        ref_exp, ref_left = check_expiry(tokens)
        print(f"  (참고: tokens.json 기록 기준 추정 {ref_exp.strftime('%Y-%m-%d')}, 실제 만료와 무관할 수 있음)")
    except Exception:
        pass

    for key, name in TOKEN_NAMES:
        token = tokens.get(key, '')
        if not token:
            print(f"    {name}: 토큰 없음(tokens.json에 값 없음)")
            continue
        info = inspect_token(token)
        if not info['ok']:
            print(f"    {name}: 확인 불가 — {info['reason']}")
            continue
        if not info['valid']:
            print(f"    {name}: 무효 — {info['reason']} → 수동 갱신 필요")
            continue

        exp_txt, days_left = _fmt_ts(info['expires_at'])
        da_txt, da_left = _fmt_ts(info['data_access_expires_at'])
        left_txt = f", 남은 {days_left}일" if days_left is not None else ""
        if da_left is None:
            da_left_txt = ""
        else:
            da_left_txt = f" (남은 {da_left}일)" if da_left >= 0 else f" ({-da_left}일 전 지남)"
        print(f"    {name}: 유효 — 토큰 {'만료 없음' if days_left is None else '만료 ' + exp_txt}{left_txt} / 데이터 접근 만료 {da_txt}{da_left_txt}")

        if days_left is not None and days_left <= 7:
            print(f"      ⚠ 곧 만료 — 갱신 시도")
            try:
                new_token, expires_in = refresh_token(key, token)
            except Exception as e:
                new_token, expires_in = None, None
                print(f"      갱신 호출 실패({type(e).__name__})")
            if new_token:
                tokens[key] = new_token
                tokens['expires_days'] = expires_in // 86400
                tokens['created'] = datetime.now().isoformat()
                changed = True
                print(f"      {key}: 갱신 성공! ({expires_in//86400}일)")
            else:
                print(f"      {key}: 자동 갱신 실패 — 수동 갱신 필요")
                print(f"      → 브라우저에서 Facebook 개발자 도구로 새 토큰 발급 필요")

    if changed:
        save_tokens(tokens)
        print(f"\n  tokens.json 업데이트 완료")

    print(f"\n{'=' * 50}")

if __name__ == '__main__':
    main()
