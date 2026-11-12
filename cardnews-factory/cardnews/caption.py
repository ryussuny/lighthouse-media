# -*- coding: utf-8 -*-
"""T-08 caption — 출처 줄·"AI로 제작"·해시태그 상한·길이 상한·과장/낚시 표현 점검(AC-7).

draft 입력 약속(compose 가 아직 없어 이 모양으로 가정):
  draft = {"account_id", "kw",
           "cards": [{"title","body","bg_path","bg_origin":"higgsfield|owned|external","font"}] * 5,
           "caption", "hashtags": [...], "sources": [{"url","org"}]}
캡션 형식(build_caption): 본문 / 빈 줄 / "출처: 기관명 URL" 줄들 / 해시태그 줄 / 마지막 줄 "AI로 제작".
"""
import re

AI_LABEL = "AI로 제작"
MAX_CAPTION = 2200  # 인스타그램 캡션 상한(티켓 지정)
# PRD_v2 에 해시태그 상한 값이 없어 10 으로 둠(master 보고 대상). 인스타 자체 상한은 30.
MAX_HASHTAGS = 10
HYPE_WORDS = ["충격", "경악", "무조건", "100%", "100％", "대박", "절대", "필독", "난리", "역대급",
              "꼭 보세요", "안 보면 손해", "지금 당장", "미쳤", "소름", "폭로", "단독 공개", "비밀"]


def _norm(s):
    return "".join(s.split()).lower()


PORTAL_LABELS = {"korea.kr": "정책브리핑(korea.kr)"}


def display_sources(records):
    """source_ledger 레코드 → 캡션·draft 용 [{url, org}]. 기관 미상(org_known=false 이거나 org 가 호스트명)은
    포털명 '정책브리핑(korea.kr)'(또는 '기관 미확인(호스트)')으로 표기하고, 확인된 기관 출처 뒤에 둔다(원래 순서 유지).
    표기는 draft['sources'] 와 캡션 줄이 같은 문자열이라 verify 의 캡션 면제(출처 줄 정확 일치)와 맞는다."""
    from urllib.parse import urlparse
    from .research import org_is_known
    known, unknown = [], []
    for r in records:
        if org_is_known(r):
            known.append({"url": r["url"], "org": r["org"]})
            continue
        host = (urlparse(r["url"]).hostname or "").lower()
        host = host[4:] if host.startswith("www.") else host
        base = ".".join(host.split(".")[-2:]) if host else ""
        unknown.append({"url": r["url"], "org": PORTAL_LABELS.get(base) or f"기관 미확인({host})"})
    return known + unknown


def source_lines(sources):
    return [f"출처: {s['org']} {s['url']}" for s in sources]


def build_caption(body, sources, hashtags):
    tags = " ".join(h if h.startswith("#") else "#" + h for h in hashtags)
    parts = [body.strip(), "\n".join(source_lines(sources))]
    if tags:
        parts.append(tags)
    parts.append(AI_LABEL)
    return "\n\n".join(p for p in parts if p)


def find_hype(text):
    n = _norm(text)
    return [w for w in HYPE_WORDS if _norm(w) in n]


def check_caption(draft, max_hashtags=MAX_HASHTAGS, max_len=MAX_CAPTION):
    """보류 사유 목록(빈 목록=통과)."""
    reasons = []
    cap = draft.get("caption") or ""
    if not cap.strip():
        return ["캡션 비어 있음"]
    if len(cap) > max_len:
        reasons.append(f"캡션 길이 {len(cap)}자 > 상한 {max_len}자")
    if cap.rstrip().splitlines()[-1].strip() != AI_LABEL:
        reasons.append(f"캡션 마지막 줄이 '{AI_LABEL}' 가 아님")
    srcs = draft.get("sources") or []
    if not srcs:
        reasons.append("출처 목록 없음")
    for s in srcs:
        line = f"출처: {s.get('org', '')} {s.get('url', '')}"
        if not s.get("org") or not s.get("url"):
            reasons.append(f"출처 항목에 기관명/URL 누락: {s}")
        elif line not in cap:
            reasons.append(f"캡션에 출처 줄 없음: {line}")
    tags = draft.get("hashtags") or []
    if len(tags) > max_hashtags:
        reasons.append(f"해시태그 {len(tags)}개 > 상한 {max_hashtags}개")
    in_cap = re.findall(r"#\S+", cap)
    if len(in_cap) > max_hashtags:
        reasons.append(f"캡션 속 해시태그 {len(in_cap)}개 > 상한 {max_hashtags}개")
    hype = find_hype(cap + " " + " ".join(f"{c.get('title', '')} {c.get('body', '')}" for c in draft.get("cards", [])))
    if hype:
        reasons.append("과장·낚시 표현: " + ", ".join(hype))
    return reasons
