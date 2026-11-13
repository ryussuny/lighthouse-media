# -*- coding: utf-8 -*-
"""T-05 verify — G1(공식 출처 2곳) · G2(수치 글자 대조) 기계 검사. AI 판단 없음.

입력
  draft   : {"account_id", "kw", "cards":[{"title","body",...}], "caption"?, "hashtags"?}
  sources : source_ledger 레코드 목록 [{url, org, org_known?, sha256, saved_path, ...}]

G1  공식 도메인 안 + 저장본 sha256 이 원장 값과 같음 + 서로 다른 '확인된' 기관(org) 2곳 이상.
    org_known 이 False 이거나 org 가 호스트명(점 포함)이면 기관 수에 넣지 않는다(2026-11-12 리뷰).
G2  검사 대상 = 카드의 모든 문자열 필드 + 해시태그 + 캡션. 캡션 면제는 코드가 만드는 줄과 **정확히 같은 꼴**뿐
    ('기준일: YYYY-MM-DD', draft.sources 로 만든 '출처: 기관 URL', 'AI로 제작'). 접두어만 같은 줄은 검사한다.
    ① 숫자 표현(숫자 + 단위, 복합 금액 '1억 2천만원'은 한 토큰, 날짜 포함)을 카드와 원문 양쪽에서 **같은 규칙**으로
       잘라 **토큰 단위로 일치**해야 한다(공백 무시). 부분 문자열 일치가 아니므로 더 긴 수의 앞·뒤 일부는 실패
       ('100만원'↔'2,100만원', '3억'↔'3억5천만원', '5천만원'↔'1억5천만원' 모두 실패).
    ② 단위 없는 1~2자리 숫자는 무엇을 세는지 기계로 확인할 수 없어 실패(사람 검토).
    ③ 한글 수사('오십만원'·'세 가지')·어림수('수십만', '몇백')가 보이면 실패 — 아라비아 숫자로만 쓰게 한다.
    ④ 두 출처 값 비교: 숫자 바로 앞 한글 낱말 1~2개(라벨, 공백 무시·2글자 이상)와 단위가 같은 표현이 출처에
       있는데 값이 다르면 '값 불일치'로 실패(예: 카드 '월 34만원', 출처 B '월 33만원').
    한계: 라벨이 다르게 쓰인 불일치는 못 잡는다 → values_single_source 로 한 출처에서만 확인된 값을 남긴다.
결과는 check_ledger 에 gate 별 한 줄(T-06 guard 와 같은 원장).
"""
import hashlib
import os
import re

from . import config as C
from . import ledger
from .research import html_to_text

MIN_ORGS = 2
NUM = r"\d(?:[\d,]*\d)?(?:\.\d+)?"
UNITS = (r"(?:만\s*원|억\s*원|천\s*원|만\s*명|만\s*가구|만\s*건|억\s*명|원|%|퍼센트|세|살|개월|년|월|일|시간|시|분|명|"
         r"가구|회차|회|배|건|곳|개소|개국|개|주년|주|가지|번|층|차|대|장|점|등급|단계|종류|종|인|편|권|위|만|억|천)?")
PRE = r"(?<!\d)(?<!\d[,.])"   # 앞이 숫자 또는 '숫자,' '숫자.' 이면 더 긴 수의 일부. 문장 끝 '다.' 뒤는 허용
# 복합 금액·수('1억 2천만원'·'34만 9천700원'·'5천만원')는 한 토큰으로 읽는다 — 앞부분만 떼어 대조하면 값이 줄어든다
AMOUNT = NUM + r"(?:\s*[억천만](?:\s*" + NUM + r")?)*"
# 단위 뒤 경계(리뷰7): 한글 단위 바로 뒤에 한글이 붙으면 다른 낱말('2위원회'·'1인분'·'5권역')이라 단위로 치지 않는다.
# 조사·어미·기간말만 예외. 경계가 안 맞으면 단위 없는 수로 떨어져 보류 쪽(보수적)으로 간다.
# 한 글자 예외 이·가·로·의·도 는 그 뒤가 비한글일 때만('1인가구'·'2차로변'·'9종가는' 은 다른 낱말), 의 는 뒤에 숫자가 오면('3분의 1') 분수라 제외(리뷰8)
PARTICLE = (r"(?:이(?![가-힣])|가(?![가-힣])|은|는|을|를|의(?![가-힣])(?!\s*\d)|에|와|과|도(?![가-힣])|로(?![가-힣])|으로|부터|까지|씩|째|당|간|만|보다|처럼|짜리|입니다|였|이었"
            r"|이상|이하|미만|초과|이내|가량|정도|안팎|내외|께|말|초|중순|초순|하순|상순)")
BOUND = r"(?:(?<![가-힣])|(?![가-힣])|(?=" + PARTICLE + r"))"
NUM_RE = re.compile(PRE + AMOUNT + r"\s*" + UNITS + BOUND)
LABEL_RE = r"((?:[가-힣]{1,8}\s+)?[가-힣]{1,8})\s*$"   # 숫자 바로 앞 한글 낱말 1~2개
# 한글 수사: 십·백·천·만·억 이 들어간 수 + 단위 / 고유어 수 + 세는 말(‘한’은 '한 번 더' 같은 관용이 많아 뺀다)
KO_NUM_RE = re.compile(
    r"(?:[일이삼사오육칠팔구]?[십백천만억][일이삼사오육칠팔구십백천만억]*\s*(?:원|명|세|살|개월|년|가구|퍼센트|배|곳|건|가지))"
    r"|(?:(?<![가-힣])(?:두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s+(?:가지|번|개|명|곳|살|달|해|단계|배))"
    r"|(?:(?<![가-힣])(?:스무|서른|마흔|쉰|예순|일흔|여든|아흔|열\s*(?:한|두|세|네|다섯|여섯|일곱|여덟|아홉))"
    r"\s*(?:살|가지|번|개|명|곳|해|달|단계))"
    r"|(?:[일이삼사오육칠팔구]?십\s*대)"
    r"|(?:수[십백천만억]+|몇\s*[십백천만억]+)")
PORTAL_ORGS = {"정책브리핑", "대한민국정책브리핑", "korea.kr", "정부24", "gov.kr",
               "KTV", "KTV국민방송", "국민방송"}   # 포털·방송(2차 전달 매체) 이름은 기관이 아님(리뷰7)
# 캡션에서 검사를 면제하는 줄 = 코드가 만드는 줄과 정확히 같은 꼴뿐(접두어만 같으면 검사)
CAPTION_MACHINE = [re.compile(r"^기준일:\s*\d{4}-\d{2}-\d{2}$"), re.compile(r"^AI로 제작$")]


def _ns(s):
    return "".join(s.split())


def numbers_in(text):
    """숫자 표현 목록(공백 제거, 등장 순서·중복 제거)."""
    out = []
    for m in NUM_RE.finditer(text or ""):
        t = _ns(m.group(0))
        if t and t not in out:
            out.append(t)
    return out


def _split_num_unit(tok):
    m = re.match(r"(" + NUM + r")(.*)$", tok)
    return (m.group(1), m.group(2)) if m else (tok, "")


def _found(tok, text):
    """경계 있는 일치. 원문은 공백을 지운 글이라 '3월 31일'이 '3월31일'이 된다 —
    그래서 뒤쪽 경계(뒤에 숫자·쉼표 금지)는 tok 이 숫자 또는 만·억·천(수가 이어질 수 있는 자리)으로 끝날 때만 본다
    — '3억'은 '3억5천만원' 안에서 찾은 것으로 치지 않는다. 원·명·월 같은 닫는 단위로 끝나면 단위가 경계.
    앞쪽: 숫자, '숫자,' '숫자.' 뒤면 더 긴 수의 일부('2,100만원'의 '100만원')라 불일치."""
    post = r"(?![\d,])" if (tok[-1].isdigit() or tok[-1] in "만억천") else ""
    return re.search(PRE + re.escape(tok) + post, text) is not None


def load_source_text(rec):
    with open(rec["saved_path"], "rb") as f:
        raw = f.read()
    return raw, _ns(html_to_text(raw))


def _org_counts(s):
    org = (s.get("org") or "").strip()
    if not org or s.get("org_known") is False or "." in org or _ns(org) in PORTAL_ORGS:
        return None
    return org


def counts_as_agency(s, domains=None):
    """이 출처가 G1 '서로 다른 확인된 기관' 수에 들어가면 기관명, 아니면 None. 공식 도메인 안 + org_known + 호스트명 아님 + 포털·방송(PORTAL_ORGS) 아님.
    check_g1 과 research(기관 수 세기)가 이 판정 하나를 같이 쓴다(T-04h2 — 중복 구현 금지)."""
    domains = domains or C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
    if not C.is_official_url(s.get("url", ""), domains):
        return None
    return _org_counts(s)


def check_g1(sources, domains):
    bad, orgs, ok_src, unknown = [], set(), [], 0
    for s in sources:
        if not C.is_official_url(s.get("url", ""), domains):
            bad.append(f"비공식 도메인: {s.get('url')}")
            continue
        if not os.path.exists(s.get("saved_path", "")):
            bad.append(f"원문 저장본 없음: {s.get('saved_path')}")
            continue
        with open(s["saved_path"], "rb") as f:
            if hashlib.sha256(f.read()).hexdigest() != s.get("sha256"):
                bad.append(f"sha256 불일치(저장 후 바뀜): {s['saved_path']}")
                continue
        ok_src.append(s)
        org = _org_counts(s)
        if org:
            orgs.add(org)
        else:
            unknown += 1
    ok = len(orgs) >= MIN_ORGS
    reason = f"확인된 공식 기관 {len(orgs)}곳({', '.join(sorted(orgs))})" + ("" if ok else f" — 최소 {MIN_ORGS}곳 필요")
    if unknown:
        reason += f"; 기관 미상 출처 {unknown}건은 기관 수에서 뺌"
    if bad:
        reason += "; " + "; ".join(bad)
    return ok, reason, ok_src


def g2_texts(draft):
    """G2 검사 대상 글 조각 목록 [(어디, 글)]."""
    out = []
    def walk(where, v):  # 리스트·dict 필드 안의 글도 검사
        if isinstance(v, str):
            out.append((where, v))
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                walk(f"{where}.{k2}", v2)
        elif isinstance(v, (list, tuple)):
            for j, v2 in enumerate(v):
                walk(f"{where}[{j}]", v2)

    for i, card in enumerate(draft.get("cards", []), 1):
        for k, v in card.items():
            if k not in ("image_path", "bg_path", "bg_origin", "font"):
                walk(f"card{i}.{k}", v)
    for h in draft.get("hashtags", []) or []:
        out.append(("hashtag", str(h)))
    src_lines = {f"출처: {x.get('org', '')} {x.get('url', '')}".strip() for x in draft.get("sources", []) or []}
    for line in (draft.get("caption") or "").splitlines():
        s = line.strip()
        if not s or s in src_lines or any(r.match(s) for r in CAPTION_MACHINE):
            continue
        if s.startswith("#"):  # 해시태그 줄은 태그 단위로 검사(숫자 든 태그도 대조)
            out += [("hashtag", t) for t in s.split()]
        else:
            out.append(("caption", s))
    for k, v in draft.items():  # 그 밖의 최상위 글 필드도(내부 식별용 키 제외)
        if k not in ("cards", "hashtags", "caption", "sources", "account_id", "kw"):
            walk(k, v)
    return out


def source_tokens(raw):
    """원문을 카드와 **같은 규칙**으로 잘라 만든 숫자 토큰 집합(공백 제거). 대조는 토큰 단위 일치 —
    부분 문자열이 아니므로 '5천만원'은 원문 '1억5천만원'(한 토큰)에서 찾은 것으로 치지 않는다."""
    return set(numbers_in(html_to_text(raw)))


def check_g2(draft, sources):
    texts, toks = {}, {}
    for s in sources:
        raw, stripped = load_source_text(s)
        texts[s["url"]], toks[s["url"]] = stripped, source_tokens(raw)
    missing, conflicts, single, found_in, unitless, ko = [], [], [], {}, [], []
    for where, ctext in g2_texts(draft):
        for m in KO_NUM_RE.finditer(NUM_RE.sub(" ", ctext)):  # '34만원'의 '만원'을 한글 수사로 오인하지 않게
            ko.append(f"{where}:'{m.group(0)}'")
        for m, tok, num, unit in _num_items(ctext):
            if not unit and len(num.replace(",", "")) <= 2:
                unitless.append(f"{where}:'{tok}'")
                continue
            hits = [u for u, ts in toks.items() if tok in ts]
            found_in[tok] = hits
            if not hits:
                missing.append(tok)
                continue
            if len(hits) == 1 and len(texts) > 1:
                single.append(tok)
            lab = re.search(LABEL_RE, ctext[:m.start()])
            if not lab or not unit:
                continue
            label = _ns(lab.group(1))
            if len(label) < 2:  # '월'·'약' 같은 한 글자 라벨은 너무 흔해 불일치 판정에 쓰지 않는다
                continue
            pat = re.compile(re.escape(label) + r"(?<![\d,.])(" + NUM + r")" + re.escape(unit))
            for u, t in texts.items():
                for other in pat.findall(t):
                    if other != num:
                        conflicts.append(f"'{label} {tok}' ↔ 출처 {u} '{label}{other}{unit}'")
    missing, conflicts = list(dict.fromkeys(missing)), list(dict.fromkeys(conflicts))
    unitless, ko = list(dict.fromkeys(unitless)), list(dict.fromkeys(ko))
    ok = not (missing or conflicts or unitless or ko)
    parts = []
    if missing:
        parts.append("원문에서 못 찾은 값: " + ", ".join(missing))
    if conflicts:
        parts.append("값 불일치: " + "; ".join(conflicts))
    if unitless:
        parts.append("단위 없는 짧은 숫자(무엇을 세는지 확인 불가): " + ", ".join(unitless))
    if ko:
        parts.append("한글 수사·어림수(아라비아 숫자로 써야 대조 가능): " + ", ".join(ko))
    reason = "; ".join(parts) or f"숫자 표현 {len(found_in)}개 모두 원문에서 확인"
    return ok, reason, {"found_in": found_in, "values_single_source": list(dict.fromkeys(single))}


DATE_UNITS = {"년", "월", "일", "시", "분"}   # 날짜·시각 단위(분기·상반기·하반기·요일은 숫자+단위 토큰으로 안 잡히거나 위 단위로 환원)
DATE_LIKE = re.compile(r"^\d{1,4}[.\-/]\d{1,2}(?:[.\-/]\d{1,2})?\.?$")   # 2026.11.04 · 11.4. 꼴
DF_RATIO = 0.02        # 문서 빈도 상한 = max(DF_MIN, 저장본 수 × 2%). 실측(저장본 322건): 5%=14건·1인=9건·10%=19건은 흔함, 7%=3건·136만명·75만원·53만원=2건은 구별력 있음
DF_MIN = 5
CACHE_INDEX = os.path.join(C.ROOT, "data", "source_cache", "index.jsonl")   # 시험이 바꿔 끼울 수 있게 모듈 상수
DF_SMALL_CACHE = 50    # 저장본이 이보다 적으면 빈도를 믿을 수 없다 → 짧은 숫자(두 자리 이하, 소수점 없음)도 흔한 토큰으로 본다
_DF_CACHE = {}


def _num_items(ctext):
    """글 한 조각의 숫자 표현 (match, 토큰(공백 제거), 숫자부, 단위부). G2·기여 판정이 같은 추출을 쓴다."""
    for m in NUM_RE.finditer(ctext or ""):
        tok = _ns(m.group(0))
        if tok:
            num, unit = _split_num_unit(tok)
            yield m, tok, num, unit


def is_date_token(tok):
    num, unit = _split_num_unit(tok)
    return bool(DATE_LIKE.match(tok)) or unit in DATE_UNITS or (not unit and bool(DATE_LIKE.match(num)))


def _short_numeric(tok):
    num, _unit = _split_num_unit(tok)
    return len(num.replace(",", "")) <= 2 and "." not in num


def common_tokens(index_path=None):
    """source_cache 인덱스 전체 저장본의 숫자 토큰 문서 빈도 → (흔한 토큰 집합, 저장본 수, 상한). 상한 초과 토큰이 '흔한' 것.
    프로세스당 1회 계산(인덱스 크기·mtime 이 같으면 캐시). 읽을 수 없는 저장본은 건너뜀."""
    import json
    from collections import Counter
    from .research import resolve_saved_path   # 호출 시점 import(순환 방지)
    index_path = os.path.abspath(index_path or CACHE_INDEX)
    base = os.path.dirname(index_path)
    try:
        st = os.stat(index_path)
        key = (index_path, st.st_size, st.st_mtime)
    except OSError:
        return frozenset(), 0, DF_MIN   # 인덱스 없음 → n=0 → 기여 판정 불가(fail-closed)
    if key in _DF_CACHE:
        return _DF_CACHE[key]
    df, n, seen = Counter(), 0, set()
    try:
        fh = open(index_path, encoding="utf-8")
    except OSError:
        return frozenset(), 0, DF_MIN
    with fh as f:
        for line in f:
            try:
                rec = json.loads(line)
                sp = resolve_saved_path(rec, base)["saved_path"]   # 상대('files/…')는 인덱스 디렉터리 기준, 절대는 그대로
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            if sp in seen or not os.path.exists(sp):
                continue
            seen.add(sp)
            try:
                with open(sp, "rb") as g:
                    toks = source_tokens(g.read())
            except OSError:
                continue
            n += 1
            df.update(toks)
    limit = max(DF_MIN, int(-(-n * DF_RATIO // 1)))   # ceil(n*2%)
    res = (frozenset(t for t, c in df.items() if c > limit), n, limit)
    _DF_CACHE.clear()
    _DF_CACHE[key] = res
    return res


def contribution_tokens(draft, common=frozenset(), n_docs=10 ** 6):
    """기여 판정에 쓰는 초안 숫자 토큰: 카드 본문(cards[].body)에서만, 날짜성 제외, 흔한 토큰(common) 제외,
    저장본이 적으면(n_docs < DF_SMALL_CACHE) 짧은 숫자도 제외. 단위 없는 짧은 숫자는 원래 G2 대조 대상이 아니라 제외."""
    out = set()
    for card in draft.get("cards", []) or []:
        body = card.get("body") if isinstance(card, dict) else None
        if not isinstance(body, str):
            continue
        for _m, tok, num, unit in _num_items(body):
            if not unit and len(num.replace(",", "")) <= 2:
                continue
            if is_date_token(tok) or tok in common:
                continue
            if n_docs < DF_SMALL_CACHE and _short_numeric(tok):
                continue
            out.add(tok)
    return out


def contribution_g1(draft, ok_src, g1_why, common=frozenset(), n_docs=10 ** 6):
    """선언한 출처의 기관은, 그 기관 저장본에 구별력 있는 본문 숫자 토큰이 1개 이상 실제로 있어야 기관 수에 든다
    (source_tokens·numbers_in 재사용). 같은 숫자가 두 기관 원문에 다 있으면 둘 다 기여(교차 확인). 반환 (ok, 사유)."""
    if n_docs <= 0:   # fail-closed: 빈도 기준(source_cache)을 못 읽으면 '흔한 숫자' 를 가릴 수 없다
        return False, (g1_why + "; 기여 판정 불가 — source_cache 인덱스를 읽지 못했거나 해석된 저장본 0건(흔한 숫자 기준 없음) — 보류")
    toks = contribution_tokens(draft, common, n_docs)
    declared, contributing = set(), set()
    for s in ok_src:
        org = _org_counts(s)
        if not org:
            continue
        declared.add(org)
        if toks & source_tokens(load_source_text(s)[0]):
            contributing.add(org)
    unused = sorted(declared - contributing)
    ok = len(contributing) >= MIN_ORGS
    reason = g1_why
    if unused:
        reason += f"; 선언했지만 내용에 쓰이지 않은 기관: {', '.join(unused)}(기관 수에서 뺌)"
    if not ok:
        reason += (f"; 내용에 쓰인 기관 {len(contributing)}곳 — 최소 {MIN_ORGS}곳 필요"
                   f"(카드 본문의 구별력 있는 숫자 {len(toks)}개: 날짜성·흔한 숫자는 제외)")
    return ok, reason


def run(draft, sources, ledger_dir=None, domains=None, require_contribution=False, common=None):
    """require_contribution=True(draft 모드: used_sources 는 선언): 숫자를 실제로 쓴 기관만 G1 기관 수에 센다."""
    domains = domains or C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
    base = {"account_id": draft.get("account_id"), "kw": draft.get("kw")}
    g1_ok, g1_why, ok_src = check_g1(sources, domains)
    if g1_ok and require_contribution:
        cset, n_docs, _lim = common if common is not None else common_tokens()
        g1_ok, g1_why = contribution_g1(draft, ok_src, g1_why, cset, n_docs)
    ledger.append("check_ledger", {**base, "gate": "G1", "pass": g1_ok, "reason": g1_why}, ledger_dir)
    if not g1_ok:
        g2_msg = "G1 실패로 대조 생략"
        if ok_src:   # 진단용 대조(통과 판정에는 영향 없음): 어떤 숫자가 원문에 없는지 같이 남긴다
            try:
                _ok2, why2, _d = check_g2(draft, ok_src)
                g2_msg = f"G1 실패 — 진단용 숫자 대조(판정 아님): {why2}"
            except Exception as e:  # noqa: BLE001
                g2_msg = f"G1 실패 — 진단용 대조 오류: {e!r}"[:200]
        ledger.append("check_ledger", {**base, "gate": "G2", "pass": False, "reason": g2_msg}, ledger_dir)
        return {"pass": False, "G1": (g1_ok, g1_why), "G2": (False, g2_msg), "detail": {}}
    g2_ok, g2_why, detail = check_g2(draft, ok_src)
    ledger.append("check_ledger", {**base, "gate": "G2", "pass": g2_ok, "reason": g2_why,
                                   "values_single_source": detail["values_single_source"]}, ledger_dir)
    return {"pass": g1_ok and g2_ok, "G1": (g1_ok, g1_why), "G2": (g2_ok, g2_why), "detail": detail}
