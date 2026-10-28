"""Graph API 토큰이 stdout/stderr(→ logs/*.log)에 평문으로 남지 않게 막는다.

requests 예외 메시지·traceback 에는 요청 URL(?access_token=...)이 그대로 들어간다.
install() 은 sys.stdout/sys.stderr 를 줄 단위 마스킹 래퍼로 바꿔, 어떤 경로(print·logging·
uncaught traceback)로 나가든 토큰 값을 '***' 로 가린다. 요청 자체는 건드리지 않는다.
"""
import atexit
import re
import sys

_KEYS = r"(?:access_token|fb_exchange_token|client_secret|refresh_token)"

_PATTERNS = [
    # URL/쿼리스트링: access_token=값 (& 공백 따옴표 괄호 전까지)
    (re.compile(r"(" + _KEYS + r"=)[^&\s'\"\)\]>]+"), r"\1***"),
    # dict/JSON 표기: 'access_token': '값'  "access_token":"값"
    (re.compile(r"(['\"]" + _KEYS + r"['\"]\s*:\s*['\"])[^'\"]+(['\"])"), r"\1***\2"),
    # 접두사로 식별되는 맨 토큰(Meta 장기 토큰 EAA…, Instagram IGA…/IGQ…)
    (re.compile(r"\b(?:EAA|IGA|IGQ)[A-Za-z0-9_\-]{40,}"), "***"),
    # Google OAuth: 접속 토큰 ya29.…, 갱신 토큰 1//0…  (접두사만 남긴다. 'ya29' 단어·'1//2 비율' 은 길이·'0' 조건으로 제외,
    # ya29. 는 고유 접두사라 앞 문자와 무관하게 가린다. '/' 뒤 1//0 토큰도 가린다)
    (re.compile(r"(ya29\.)[A-Za-z0-9_\-]{20,}"), r"\1***"),
    (re.compile(r"(?<![A-Za-z0-9_.\-])(1//)(?=0)[A-Za-z0-9_\-]{20,}"), r"\1***"),
]


def redact(text):
    for pat, rep in _PATTERNS:
        text = pat.sub(rep, text)
    return text


class _RedactStream:
    """줄 단위로 모아 마스킹한 뒤 원래 스트림에 쓴다(토큰이 write 경계에서 쪼개지는 것 방지)."""

    def __init__(self, stream):
        self._stream = stream
        self._buf = ""

    def write(self, s):
        if not isinstance(s, str):
            return self._stream.write(s)
        self._buf += s
        cut = self._buf.rfind("\n")
        if cut >= 0:
            head, self._buf = self._buf[:cut + 1], self._buf[cut + 1:]
            self._stream.write(redact(head))
        return len(s)

    def flush(self):
        if self._buf:
            self._stream.write(redact(self._buf))
            self._buf = ""
        self._stream.flush()

    def __getattr__(self, name):
        return getattr(self._stream, name)


def install():
    """stdout/stderr 를 마스킹 래퍼로 교체(중복 호출 무해). reconfigure(encoding) 뒤에 부른다."""
    for name in ("stdout", "stderr"):
        cur = getattr(sys, name)
        if not isinstance(cur, _RedactStream):
            setattr(sys, name, _RedactStream(cur))
    atexit.register(lambda: (sys.stdout.flush(), sys.stderr.flush()))
