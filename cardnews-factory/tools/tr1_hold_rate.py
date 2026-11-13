# -*- coding: utf-8 -*-
"""T-TR1 트렌드 보류율 실측 — 오프라인(source_cache 저장본 기준). 외부 요청·API 호출 없음, 캐시 읽기만.
입력: data/raw_tr1/gtrends_kr_20261113.xml (구글 트렌드 KR RSS 1회 수신본). 출력: data/raw_tr1/result_20261113.json"""
import datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C, research as R, trends  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = dt.date(2026, 11, 13)
# 오너 지시의 G3 대상(연예·사건사고·정치·의료 단정)을 키워드/뉴스제목 어휘로 거칠게 분류하는 '휴리스틱'(AI 분류기 아님).
TOPIC = {
    "사건사고": ["사고", "살인", "사망", "추락", "화재", "폭행", "체포", "구속", "검사", "누명", "피해자", "실종"],
    "연예": ["배우", "가수", "아이돌", "열애", "결혼설", "이혼", "드라마", "예능", "콘서트"],
    "정치": ["대통령", "국회", "탄핵", "여당", "야당", "선거", "의원", "정권"],
    "의료단정": ["완치", "치료됩니다", "특효", "암이 낫", "효과 보장"],
}
banned = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
raw = open(os.path.join(ROOT, "data", "raw_tr1", "gtrends_kr_20261113.xml"), "rb").read()
items = trends.parse_google_trends(raw)
cache = R.SourceCache()
domains = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
rows = []
for it in items:
    kw, text = it["kw"], it["kw"] + " " + " ".join(it["news_titles"])
    it = {**it, "news_titles": [n.replace("삼성화재", "") for n in it["news_titles"]]}  # 기업명 '삼성화재배'(바둑)는 화재 아님
    row = {"kw": kw, "traffic": it["traffic"], "news": it["news_titles"][:1]}
    cat = trends.is_banned(text, banned)
    # 오분류 방지(실측 1차에서 '삼성화재배'·정책 기사 속 '국회' 언급이 잡힘): 어휘가 키워드 자체에 있거나 뉴스 제목 2건 이상에 있을 때만
    topic = next((k for k, ws in TOPIC.items()
                  if any(w in kw or sum(w in n for n in it["news_titles"]) >= 2 for w in ws)), None)
    if cat or topic:
        row.update(bucket="G3", g3=cat and f"키워드목록:{cat}" or f"휴리스틱:{topic}")
    else:
        cands = cache.match(kw, TODAY)
        keep, drop = R.screen(cands, TODAY, domains)
        reps = R.group_releases(keep)
        orgs = sorted({R._norm(c.get("org") or R.org_of(c["url"])) and (c.get("org") or R.org_of(c["url"])) for c in reps if R.org_is_known(c)})
        row.update(cache_matches=len(cands), kept=len(keep), dropped=[d["reason"] for d in drop][:3], orgs=orgs,
                   bucket="PASS" if len(orgs) >= 2 else "G1_HOLD")
    rows.append(row)
res = {"today": TODAY.isoformat(), "source": "data/raw_tr1/gtrends_kr_20261113.xml", "cache": cache.summary(TODAY), "rows": rows,
       "n": len(rows), **{b: sum(1 for r in rows if r["bucket"] == b) for b in ("G3", "G1_HOLD", "PASS")}}
json.dump(res, open(os.path.join(ROOT, "data", "raw_tr1", "result_20261113.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rows:
    print(r["bucket"], r["kw"], r.get("g3") or (r["cache_matches"], r["kept"], r["orgs"], r["dropped"]))
print({k: res[k] for k in ("n", "G3", "G1_HOLD", "PASS", "cache")})
