"""나레이션용 숫자 읽기 — 사람이 읽듯 고유어 수사로 바꾼다 (2026-10-24 오너 지시).

TTS가 '3가지'를 '삼 가지', '4가지'를 '사 가지'로 읽는 문제를 막는다. 자막·제목은 그대로 두고
TTS에 보내는 글자만 바꾼다(fal_tts.synth_chunk 에서 호출).

  3가지 → 세 가지     4개 → 네 개      20명 → 스무 명     21번 → 스물한 번
  1번째 → 첫 번째     2번째 → 두 번째  3시 → 세 시        5분·3년·10% 처럼 한자어로 읽는 단위는 그대로

'장'(요한복음 3장=삼 장)·'권'(성경 66권=육십육 권)은 한자어로 읽는 경우가 많아 넣지 않는다.
고유어로 읽는 단위만 바꾸고, 1~99만 다룬다(100 이상은 숫자 그대로 두어 TTS 기본 읽기에 맡긴다).
"""
import re

ONES = ["", "한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉"]
TENS = ["", "열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔"]

# 고유어 수사와 함께 읽는 단위(뒤에 조사가 붙어도 된다). '시간'은 '시'보다 먼저 와야 한다.
NATIVE_UNITS = ["가지", "개", "명", "번", "살", "마리", "시간", "시", "사람", "군데", "잔",
                "걸음", "달", "그릇", "켤레", "통", "곳", "줄", "마디", "문장"]


def native(n):
    """1~99 → 관형 고유어 수사(한·두·세·네·스무…). 범위 밖이면 None."""
    if not 1 <= n <= 99:
        return None
    t, o = divmod(n, 10)
    if n == 20:
        return "스무"
    return TENS[t] + ONES[o]


# 단위 바로 뒤에 한글이 오면 조사·어미로 시작할 때만 바꾼다 — '3달러'(삼 달러)·'3개월'(삼 개월)·'2시대'·'7번호' 오변환 방지(리뷰 2026-10-24)
_AFTER_OK = "은는이가을를의에도만씩째쯤까부로으와과요입였뿐밖정중나동안며랑예마"
_UNIT_RE = re.compile(r"(?<![\d.,])(\d{1,2})\s*(" + "|".join(NATIVE_UNITS) + r")(?![가-힣](?<![" + _AFTER_OK + r"]))")


def speakable(text):
    """TTS에 보낼 문장에서 '숫자+고유어 단위'를 사람 읽기로 바꾼다."""
    if not text:
        return text

    def rep(m):
        n, unit = int(m.group(1)), m.group(2)
        if unit == "번" and text[m.end():m.end() + 1] == "째":
            return ("첫" if n == 1 else native(n)) + " 번" if native(n) else m.group(0)
        w = native(n)
        return f"{w} {unit}" if w else m.group(0)

    return _UNIT_RE.sub(rep, text)


if __name__ == "__main__":
    import sys
    for s in sys.argv[1:]:
        print(speakable(s))
