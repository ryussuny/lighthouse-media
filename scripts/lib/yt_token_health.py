"""유튜브 OAuth 토큰 만료 조기경보 (읽기전용 · API 쿼터 0).

Google 테스트 모드 refresh token 은 발급 후 7일이면 죽는다. 이 모듈은
  1) token_lighthouse.json / token_dongsan.json 을 메모리에서만 refresh 시험하고(파일에 다시 쓰지 않는다),
  2) config/yt-token-reauth.json 사이드카의 재인증 시각으로 남은 일수를 계산해
  3) data/yt-token-health.json 에 결과를 저장한다.

재인증(토큰 새로 발급)을 하면 사이드카의 해당 파일 항목을 그 시각(iso)으로 갱신한다.
단독 실행: py scripts\\lib\\yt_token_health.py
"""
import os, json, datetime

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # lighthouse-media
SIDECAR = os.path.join(ROOT, "config", "yt-token-reauth.json")
OUT = os.path.join(ROOT, "data", "yt-token-health.json")
FILES = ("token_lighthouse.json", "token_dongsan.json")
LIFETIME_DAYS = 7
WARN_DAYS = 2
REFRESH_TIMEOUT = 10


def _sidecar():
    try:
        with open(SIDECAR, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _days_left(iso, now):
    if not iso:
        return None
    try:
        t = datetime.datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.astimezone()
        return round(LIFETIME_DAYS - (now - t).total_seconds() / 86400, 2)
    except Exception:
        return None


def _refresh_ok(path):
    """(ok, error) — refresh 만 시험. 토큰 파일은 읽기만 한다."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(path)
        if not creds.refresh_token:
            return False, "refresh_token 없음"
        import requests

        class _Capped(requests.Session):  # google-auth 기본 timeout 120초 → 10초 상한(heartbeat 지연 방지)
            def request(self, *a, **k):
                k["timeout"] = min(k.get("timeout") or REFRESH_TIMEOUT, REFRESH_TIMEOUT)
                return super().request(*a, **k)
        creds.refresh(Request(_Capped()))  # 메모리에서만 갱신, 저장 안 함
        return True, ""
    except Exception as e:
        msg = str(e).replace("\n", " ")
        return False, (type(e).__name__ + ": " + msg)[:120]


def check(save=True):
    now = datetime.datetime.now().astimezone()
    side = _sidecar()
    res = {}
    for name in FILES:
        path = os.path.join(BASE, name)
        if not os.path.exists(path):
            ok, err = False, "파일 없음"
        else:
            ok, err = _refresh_ok(path)
        iso = side.get(name)
        res[name] = {"ok": ok, "error": err, "reauth_at": iso, "days_left": _days_left(iso, now)}
    if save:
        try:
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump({"checked_at": now.isoformat(timespec="seconds"), "tokens": res}, f, ensure_ascii=False, indent=1)
        except Exception:
            pass
    return res


def _line(name, r):
    d = r["days_left"]
    if not r["ok"]:
        flag = "만료/불량"
    elif d is not None and d <= 0:
        flag = "7일 수명 초과(곧 만료 가능)"
    elif d is not None and d <= WARN_DAYS:
        flag = f"경고 {WARN_DAYS}일 이내"
    else:
        flag = "정상"
    left = "?" if d is None else f"{d}일"
    err = f" · {r['error']}" if r["error"] else ""
    return f"{name}: ok={r['ok']} · 남은 {left} · 재인증 {r['reauth_at']} · [{flag}]{err}"


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] yt token health")
    for n, r in check().items():
        print(_line(n, r))
