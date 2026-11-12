# -*- coding: utf-8 -*-
"""T-03 trends — 후보 수집 → 주제 경계 필터 → 점수 → 1~5위 → trend_ledger.

결정론: AI가 순위를 정하지 않는다. 산식은 FORMULA 에 고정하고 원장에 계산값을 남긴다.
지표원(읽기 전용):
  - google_trends : 구글 트렌드 KR RSS (키 불필요)
  - youtube       : mostPopular KR, 계정 카테고리 + 전체(0). API 키(YT_API_KEY) 또는 OAuth 토큰(메모리 갱신만)
  - ig_hashtag    : 최근 7일 안의 해시태그 실측 요약 파일(있을 때만; 주간 30개 한도 때문에 매일 새로 부르지 않음)
지표를 하나도 못 받으면 후보 없이 종료하고 사유를 기록한다(AC-2).
"""
import datetime as dt
import glob
import json
import math
import os
import xml.etree.ElementTree as ET

import re

import requests

from . import config as C
from . import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
UA = {"User-Agent": "Mozilla/5.0 (cardnews-factory)"}
GT_URL = "https://trends.google.com/trending/rss?geo=KR"
GT_NS = "{https://trends.google.com/trending/rss}"
YT_BASE = "https://www.googleapis.com/youtube/v3"
FORMULA = {
    "ver": 1,
    "text": "score = 0.6*view + 0.25*rising + 0.15*fit; "
            "view = 0.7*min(1,log10(1+yt_views)/7) + 0.3*min(1,log10(1+ig_like_median)/5) (ig 없으면 yt만); "
            "rising = min(1,log10(gt_traffic)/4) (트렌드 RSS에 있을 때) 아니면 0; fit = 1(seed) / 0.7(경계 통과 트렌드어)",
}
_SECRET_Q = re.compile(r"(?i)([?&](?:key|access_token|token|refresh_token|client_secret|api_key)=)[^&\s'\")]+")


def mask_secrets(s):
    """예외·로그 문자열 속 URL 쿼리의 키·토큰 값을 가린다(원장·알림 본문에 비밀이 실리는 경로 차단)."""
    return _SECRET_Q.sub(r"\g<1>***", str(s))


def strip_paging(obj):
    """Graph API 응답의 paging(next URL 에 access_token 이 실림)을 저장 전에 제거."""
    if isinstance(obj, dict):
        obj.pop("paging", None)
    return obj


W_VIEW, W_RISING, W_FIT = 0.6, 0.25, 0.15


# ---------- 수집 ----------
def _raw_path(day, name):
    d = os.path.join(RAW_DIR, day)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{dt.datetime.now().strftime('%H%M%S')}_{name}")


def fetch_google_trends(day):
    r = requests.get(GT_URL, headers=UA, timeout=20)
    r.raise_for_status()
    p = _raw_path(day, "gtrends_trending_rss.xml")
    with open(p, "wb") as f:
        f.write(r.content)
    return parse_google_trends(r.content), p


def parse_google_trends(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.findall("./channel/item"):
        traffic = (it.findtext(GT_NS + "approx_traffic") or "0").replace("+", "").replace(",", "")
        out.append({
            "kw": (it.findtext("title") or "").strip(),
            "traffic": int(traffic) if traffic.isdigit() else 0,
            "pubDate": it.findtext("pubDate"),
            "news_titles": [n.findtext(GT_NS + "news_item_title") or "" for n in it.findall(GT_NS + "news_item")],
        })
    return out


def _yt_headers_params():
    key = os.environ.get("YT_API_KEY")
    if key:
        return {}, {"key": key}
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    creds = Credentials.from_authorized_user_file(C.YT_OAUTH_TOKEN_PATH)
    if not creds.valid:
        creds.refresh(Request())  # 메모리만, 파일에 쓰지 않음
    return {"Authorization": f"Bearer {creds.token}"}, {}


def fetch_youtube(day, categories):
    h, extra = _yt_headers_params()
    videos, paths = [], []
    for cid in ["0"] + [c for c in categories if c != "0"]:
        params = {"part": "snippet,statistics", "chart": "mostPopular", "regionCode": "KR", "maxResults": 50, **extra}
        if cid != "0":
            params["videoCategoryId"] = cid
        r = requests.get(f"{YT_BASE}/videos", params=params, headers=h, timeout=20)
        p = _raw_path(day, f"yt_mostPopular_KR_cat{cid}.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(r.text)
        paths.append(p)
        if r.ok:
            videos += parse_youtube(r.json(), cid)
    return videos, paths


def parse_youtube(j, cid):
    return [{"title": i["snippet"]["title"], "views": int(i.get("statistics", {}).get("viewCount", 0) or 0), "cat": cid}
            for i in j.get("items", [])]


def load_ig_hashtags(today, max_age_days=7):
    """가장 최근 해시태그 요약(7일 이내). {태그: like_median}"""
    best = None
    for p in glob.glob(os.path.join(RAW_DIR, "*", "*_ig_hashtag_summary.json")):
        day = os.path.basename(os.path.dirname(p))
        try:
            age = (today - dt.date.fromisoformat(day)).days
        except ValueError:
            continue
        if 0 <= age <= max_age_days and (best is None or p > best):
            best = p
    if not best:
        return {}, None
    with open(best, encoding="utf-8") as f:
        s = json.load(f)
    return {k: v.get("like_median") for k, v in s.get("tags", {}).items() if v.get("like_median") is not None}, best


# ---------- 경계·점수 ----------
def _norm(s):
    return "".join(s.split()).lower()


def in_scope(kw, news_titles, seeds):
    """규칙 경계: 트렌드어 자체나 그 뉴스 제목에 seed 키워드가 들어 있으면 통과. 이유를 돌려준다."""
    n = _norm(kw)
    if not n:
        return False, "빈 키워드"
    for s in seeds:
        ns = _norm(s)
        if ns and (ns in n or n in ns):
            return True, f"seed '{s}' 와 키워드 겹침"
    for t in news_titles:
        nt = _norm(t)
        for s in seeds:
            if _norm(s) and _norm(s) in nt:
                return True, f"뉴스 제목에 seed '{s}' 포함"
    return False, "계정 seed 키워드와 무관"


def is_banned(kw, banned):
    n = _norm(kw)
    for cat, words in banned.items():
        for w in words:
            nw = _norm(w)
            if nw and nw in n:
                return cat
    return None


def score_candidates(cands, videos, ig_likes):
    out = []
    for c in cands:
        nk = _norm(c["kw"])
        yt_views = sum(v["views"] for v in videos if nk and nk in _norm(v["title"]))
        yt_n = sum(1 for v in videos if nk and nk in _norm(v["title"]))
        ig = ig_likes.get(c["kw"])
        yt_part = min(1.0, math.log10(1 + yt_views) / 7)
        if ig is not None:
            view = 0.7 * yt_part + 0.3 * min(1.0, math.log10(1 + ig) / 5)
        else:
            view = yt_part
        rising = min(1.0, math.log10(c["traffic"]) / 4) if c.get("traffic", 0) > 1 else 0.0
        fit = 1.0 if c["origin"] == "seed" else 0.7
        s = W_VIEW * view + W_RISING * rising + W_FIT * fit
        out.append({"kw": c["kw"], "value": round(s, 4), "formula_ver": FORMULA["ver"],
                    "parts": {"yt_views": yt_views, "yt_matches": yt_n, "ig_like_median": ig,
                              "gt_traffic": c.get("traffic", 0), "view": round(view, 4),
                              "rising": round(rising, 4), "fit": fit}})
    out.sort(key=lambda x: (-x["value"], x["kw"]))
    return out


# ---------- 실행 ----------
def run(acc, banned, fetchers=None, today=None, ledger_dir=None, exclude_kws=(), notify=None, gate=True, stop_file=None):
    """fetchers: 시험용 주입 {'google_trends': f(day)->(items,path), 'youtube': f(day,cats)->(videos,paths), 'ig': f(date)->(dict,path)}

    gate(기본 True): STOP 파일·paused 이면 아무것도 수집·기록하지 않고 {"status": "gated"} 로 바로 중단(AC-9).
    ※ T-09 오케스트레이터는 이 한 번에 의존하지 말고 단계마다(수집·research·design·게시 직전) config.run_gate 를 재확인한다.
    지표 성공 = 받은 개수 n>0. 근거 지표 0 인 seed 는 top5 에서 뺀다(없으면 status="no_evidence" + 알림).
    """
    if gate:
        ok, why = C.run_gate(acc, **({"stop_file": stop_file} if stop_file else {}))
        if not ok:
            return {"status": "gated", "reason": why, "account_id": acc.get("account_id"), "top5": []}
    today = today or dt.date.today()
    day = today.isoformat()
    f = {"google_trends": fetch_google_trends, "youtube": fetch_youtube, "ig": load_ig_hashtags, **(fetchers or {})}
    sources, gt_items, videos, ig_likes, errors = [], [], [], {}, []

    try:
        gt_items, p = f["google_trends"](day)
        if gt_items:
            sources.append({"name": "google_trends", "fetched_at": ledger.now_iso(), "raw_path": p, "n": len(gt_items)})
        else:
            errors.append("google_trends: 0건")
    except Exception as e:  # noqa: BLE001
        errors.append(mask_secrets(f"google_trends: {e!r}")[:200])
    try:
        videos, ps = f["youtube"](day, [str(c) for c in acc["trend_categories"].get("youtube", [])])
        if videos:
            sources.append({"name": "youtube", "fetched_at": ledger.now_iso(), "raw_path": ps, "n": len(videos)})
        else:
            errors.append("youtube: 0건")
    except Exception as e:  # noqa: BLE001
        errors.append(mask_secrets(f"youtube: {e!r}")[:200])
    try:
        ig_likes, p = f["ig"](today)
        if ig_likes:
            sources.append({"name": "ig_hashtag", "fetched_at": ledger.now_iso(), "raw_path": p, "n": len(ig_likes)})
    except Exception as e:  # noqa: BLE001
        errors.append(mask_secrets(f"ig: {e!r}")[:200])

    base = {"date": day, "account_id": acc["account_id"], "sources": sources, "errors": errors, "formula": FORMULA}
    if not sources:
        rec = ledger.append("trend_ledger", {**base, "status": "no_indicator", "candidates": [], "scores": [], "top5": [],
                                             "reason": "지표를 하나도 받지 못함 — 그날 게시 후보 없음(주제 지어내지 않음)"}, ledger_dir)
        if notify:
            notify("error", f"[{acc['account_id']}] 지표 0개 — 오늘 카드뉴스 없음", "; ".join(errors))
        return rec

    seeds = acc["seed_keywords"]
    cands, seen = [], set()
    for s in seeds:
        if not _norm(s):
            continue
        cands.append({"kw": s, "origin": "seed", "in_scope": True, "reason": "계정 seed 키워드", "traffic": 0})
        seen.add(_norm(s))
    for it in gt_items:
        if not _norm(it["kw"]):
            continue  # 빈 제목 항목은 후보로 만들지 않음
        ok, why = in_scope(it["kw"], it["news_titles"], seeds)
        if _norm(it["kw"]) in seen:  # seed 와 같으면 트래픽만 붙인다
            for c in cands:
                if _norm(c["kw"]) == _norm(it["kw"]):
                    c["traffic"] = it["traffic"]
            continue
        cands.append({"kw": it["kw"], "origin": "google_trends", "in_scope": ok, "reason": why, "traffic": it["traffic"]})
        seen.add(_norm(it["kw"]))
    all_banned = {**banned}
    if acc.get("banned_topics_extra"):
        all_banned["account_extra"] = acc["banned_topics_extra"]
    for c in cands:
        cat = is_banned(c["kw"], all_banned)
        if cat:
            c["in_scope"], c["reason"] = False, f"금칙 분류 {cat}"
        if _norm(c["kw"]) in {_norm(x) for x in exclude_kws}:
            c["in_scope"], c["reason"] = False, "다른 계정이 오늘 이미 고른 키워드(중복 방지)"
    scores = score_candidates([c for c in cands if c["in_scope"]], videos, ig_likes)
    for s in scores:
        pt = s["parts"]
        s["evidence"] = bool(pt["yt_matches"] or pt["gt_traffic"] or pt["ig_like_median"] is not None)
    evid = [s for s in scores if s["evidence"]]
    top5 = [{"rank": i + 1, "kw": s["kw"], "score": s["value"]} for i, s in enumerate(evid[:5])]
    if not top5:
        rec = ledger.append("trend_ledger", {**base, "status": "no_evidence", "candidates": cands, "scores": scores, "top5": [],
                                             "reason": "근거 지표(유튜브 일치·트렌드 검색량·IG 반응)가 있는 후보가 0 — seed 만으로 순위를 만들지 않음"}, ledger_dir)
        if notify:
            notify("warn", f"[{acc['account_id']}] 근거 지표 있는 후보 0 — 오늘 카드뉴스 없음", "; ".join(errors))
        return rec
    status = "ok" if len({s["name"] for s in sources}) >= 2 else "ok_single_indicator"
    return ledger.append("trend_ledger", {**base, "status": status, "candidates": cands, "scores": scores, "top5": top5}, ledger_dir)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ROOT)
    from cardnews import config as C
    acc = C.load_account(sys.argv[1] if len(sys.argv) > 1 else "test")
    ok, why = C.run_gate(acc)
    if not ok:
        print("중단:", why)
        sys.exit(0)
    banned = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
    from cardnews import alert
    rec = run(acc, banned, notify=alert.send)
    print(json.dumps({k: rec[k] for k in ("status", "top5", "errors")}, ensure_ascii=False, indent=1))
    print("sources:", [s["name"] for s in rec["sources"]])
