"""
클로드 연결 진단기 — "Claude 연결 안 됨" 문제를 한 방에 찍어준다.

실행:  python scripts/check-claude.py
출력:  .env 위치 / 키 존재 여부 / 키 형태 / 실제 API 응답(상태코드) / 원인별 처방
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import os, json

import urllib.request
import urllib.error

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_DIR, ".env")
MODEL = "claude-sonnet-4-6"

def line(c="─"): print(c * 56)

def load_key():
    """.env에서 ANTHROPIC_API_KEY를 관대하게 읽는다.
    - '=' 양옆 공백 허용
    - 따옴표 제거
    - export 접두사 허용
    반환: (key, 진단메모 리스트)
    """
    notes = []
    if not os.path.exists(ENV_PATH):
        notes.append(f".env 파일이 없습니다 → {ENV_PATH}")
        return "", notes
    raw = ""
    for ln in open(ENV_PATH, encoding="utf-8"):
        s = ln.strip()
        if s.startswith("export "):
            s = s[len("export "):]
        if not s or s.startswith("#"):
            continue
        if s.split("=", 1)[0].strip() == "ANTHROPIC_API_KEY":
            raw = s.split("=", 1)[1].strip().strip('"').strip("'").strip()
            # 기존 스크립트의 엄격한 파서가 잡아내지 못하는 케이스 경고
            if ln.startswith("ANTHROPIC_API_KEY =") or " =" in ln.split("=")[0]:
                notes.append("'=' 양옆에 공백이 있습니다. 기존 스크립트 파서는 이 줄을 "
                             "인식하지 못합니다. 'ANTHROPIC_API_KEY=...' 처럼 붙여 쓰세요.")
            if ('"' in ln) or ("'" in ln):
                notes.append("키를 따옴표로 감쌌습니다. 기존 스크립트는 따옴표째 키로 읽어 "
                             "401이 납니다. 따옴표를 제거하세요.")
            break
    if not raw:
        notes.append(".env는 있으나 ANTHROPIC_API_KEY 값을 못 찾았습니다.")
    return raw, notes

def test_call(key):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "ping"}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return None, f"NETWORK: {e.reason}"
    except Exception as e:
        return None, f"ERROR: {e}"

def main():
    line("═")
    print("  클로드 연결 진단기")
    line("═")

    print(f"\n[1] 저장소 경로: {REPO_DIR}")
    print(f"[2] .env 경로  : {ENV_PATH}")
    print(f"    존재 여부  : {'있음 ✅' if os.path.exists(ENV_PATH) else '없음 ❌'}")

    key, notes = load_key()
    print("\n[3] API 키 상태")
    if key:
        masked = key[:7] + "…" + key[-4:] if len(key) > 12 else "(너무 짧음)"
        print(f"    키 발견    : {masked}  (길이 {len(key)})")
        if not key.startswith("sk-ant-"):
            print("    ⚠️  키가 'sk-ant-' 로 시작하지 않습니다. 잘못된 값일 수 있습니다.")
    else:
        print("    키 발견    : 없음 ❌")
    for n in notes:
        print(f"    ⚠️  {n}")

    if not key:
        line()
        print("\n진단: API 키를 못 읽었습니다 → 이게 '연결 안 됨'의 원인입니다.")
        print("처방:")
        print(f"  1) {ENV_PATH} 파일을 만들고 아래 한 줄을 넣으세요(따옴표/공백 없이):")
        print("     ANTHROPIC_API_KEY=sk-ant-...")
        print("  2) 키는 https://console.anthropic.com/settings/keys 에서 발급")
        line("═")
        return

    print(f"\n[4] 실제 API 호출 테스트 (model={MODEL}) ...")
    status, text = test_call(key)
    print(f"    상태코드   : {status}")

    line()
    if status == 200:
        print("\n진단: 연결 정상 ✅  Claude API가 응답합니다.")
        print("→ '연결 안 됨'이 계속된다면 모델명/네트워크/방화벽이 아니라")
        print("  실행하는 스크립트 쪽 로직(파일 경로, 토큰 등)을 확인하세요.")
    elif status == 401:
        print("\n진단: 401 인증 실패 → API 키가 틀렸거나 만료/폐기됨.")
        print("처방: 콘솔에서 키를 재발급해 .env에 다시 넣으세요.")
        print(f"  서버 응답: {text[:300]}")
    elif status == 400 and "credit" in text.lower():
        print("\n진단: 잔액 부족(credit balance too low).")
        print("처방: console.anthropic.com 의 Billing에서 크레딧을 충전하세요.")
    elif status == 404:
        print(f"\n진단: 404 모델 없음 → '{MODEL}' 모델명이 유효하지 않을 수 있습니다.")
        print("처방: 스크립트의 모델명을 현재 유효한 ID로 교체하세요.")
        print(f"  서버 응답: {text[:300]}")
    elif status == 429:
        print("\n진단: 429 요청 한도 초과(rate limit). 잠시 후 재시도하세요.")
    elif status is None:
        print(f"\n진단: 네트워크 단계에서 실패 → 인터넷/방화벽/프록시 문제.")
        print(f"  상세: {text[:300]}")
        print("처방: api.anthropic.com 으로의 HTTPS 아웃바운드가 막혔는지 확인하세요.")
    else:
        print(f"\n진단: 예상치 못한 응답 {status}")
        print(f"  서버 응답: {text[:300]}")
    line("═")

if __name__ == "__main__":
    main()
