# -*- coding: utf-8 -*-
"""계정 설정 읽기·검증 + 실행 가능 여부(STOP 파일·paused) 판정. 표준 라이브러리만 쓴다."""
import json
import os
import re
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config")
STOP_FILE = os.path.join(ROOT, "STOP")

REQUIRED = {
    "account_id": str, "topic": str, "seed_keywords": list, "trend_categories": dict,
    "daily_post_cap": int, "post_times": list, "paused": bool, "banned_topics_extra": list, "brand": dict,
}
MAX_DAILY_CAP = 2  # PRD_v2 §2: 계정당 하루 1~2건
YT_NO_CHART_KR = {"27"}  # T-01 실측(2026-11-12): 교육 카테고리 mostPopular KR → 404


class ConfigError(ValueError):
    pass


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_account(acc):
    errs = []
    for k, t in REQUIRED.items():
        if k not in acc:
            errs.append(f"필드 없음: {k}")
        elif not isinstance(acc[k], t) or (t is int and isinstance(acc[k], bool)):
            errs.append(f"형식 오류: {k} 는 {t.__name__} 이어야 함")
    if errs:
        return errs
    if not re.fullmatch(r"[a-z0-9_]{2,32}", acc["account_id"]):
        errs.append("account_id 는 영문 소문자·숫자·_ 2~32자")
    if not acc["topic"].strip():
        errs.append("topic 비어 있음")
    if not acc["seed_keywords"] or not all(isinstance(s, str) and s.strip() for s in acc["seed_keywords"]):
        errs.append("seed_keywords 는 비어 있지 않은 문자열 목록")
    if not 1 <= acc["daily_post_cap"] <= MAX_DAILY_CAP:
        errs.append(f"daily_post_cap 은 1~{MAX_DAILY_CAP}")
    for t in acc["post_times"]:
        if not (isinstance(t, str) and re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t)):
            errs.append(f"post_times 형식 오류: {t!r} (HH:MM)")
    if not acc.get("is_virtual") and not acc.get("token_ref"):
        errs.append("실계정은 token_ref 필요(토큰 값은 파일에 쓰지 않음)")
    yt = acc["trend_categories"].get("youtube", [])
    if set(map(str, yt)) & YT_NO_CHART_KR:
        errs.append(f"유튜브 카테고리 {sorted(set(map(str, yt)) & YT_NO_CHART_KR)} 는 한국 인기 목록 없음(T-01 실측 404)")
    for k in ("token", "access_token"):
        if k in acc:
            errs.append(f"토큰 값을 설정 파일에 쓰면 안 됨: {k}")
    return errs


def validate_banned(b):
    errs = []
    cats = b.get("categories")
    need = {"medical_claim", "investment_solicit", "political_agitation", "adult", "copyright_suspect"}
    if not isinstance(cats, dict):
        return ["categories 없음"]
    miss = need - set(cats)
    if miss:
        errs.append(f"금칙 분류 누락: {sorted(miss)}")
    for k, v in cats.items():
        if not (isinstance(v, list) and v and all(isinstance(x, str) and x for x in v)):
            errs.append(f"금칙 분류 {k} 는 비어 있지 않은 문자열 목록")
    return errs


def validate_domains(d):
    errs = []
    if not d.get("suffixes") or not all(s.startswith(".") for s in d["suffixes"]):
        errs.append("suffixes 는 '.' 으로 시작하는 목록")
    if not isinstance(d.get("exact"), list):
        errs.append("exact 목록 없음")
    return errs


def is_official_url(url, domains):
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return bool(host) and (host in domains["exact"] or any(host.endswith(s) for s in domains["suffixes"]))


def load_account(account_id):
    p = os.path.join(CONFIG, "accounts", f"{account_id}.json")
    if not os.path.exists(p):
        raise ConfigError(f"계정 설정 없음: {p}")
    acc = load_json(p)
    errs = validate_account(acc)
    if acc.get("account_id") != account_id:
        errs.append("파일 이름과 account_id 불일치")
    if errs:
        raise ConfigError("; ".join(errs))
    return acc


def run_gate(acc, stop_file=STOP_FILE):
    """AC-9: 실행해도 되는지. (ok, 사유). STOP 파일이 우선."""
    if os.path.exists(stop_file):
        return False, f"STOP 파일 있음: {stop_file}"
    if acc.get("paused"):
        return False, f"계정 일시정지(paused=true): {acc['account_id']}"
    return True, "ok"


def validate_all():
    report = {}
    acc_dir = os.path.join(CONFIG, "accounts")
    for fn in sorted(os.listdir(acc_dir)):
        if fn.endswith(".json"):
            try:
                load_account(fn[:-5])
                report[f"accounts/{fn}"] = []
            except (ConfigError, json.JSONDecodeError) as e:
                report[f"accounts/{fn}"] = [str(e)]
    report["common_banned.json"] = validate_banned(load_json(os.path.join(CONFIG, "common_banned.json")))
    report["official_domains.json"] = validate_domains(load_json(os.path.join(CONFIG, "official_domains.json")))
    return report


if __name__ == "__main__":
    import sys
    rep = validate_all()
    bad = {k: v for k, v in rep.items() if v}
    for k, v in rep.items():
        print(("FAIL " if v else "OK   ") + k + ("" if not v else " — " + "; ".join(v)))
    sys.exit(1 if bad else 0)
