# -*- coding: utf-8 -*-
"""T-04/T-04b 수용 기준. 네트워크 없음(가짜 discover·가짜 fetcher)."""
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C, ledger, research as R  # noqa: E402

TODAY = dt.date(2026, 11, 12)


def page(txt):
    return f"<html><head><title>t</title><script>x=1</script></head><body><p>{txt}</p></body></html>".encode("utf-8")


def _uniq(url, n):
    """URL 마다 서로 다른(재게시로 안 묶이는) 한글 무작위 문자열 — 제목·본문 유사도 판정 시험을 방해하지 않게."""
    import hashlib
    h = hashlib.sha256(url.encode()).digest()
    return "".join(chr(0xAC00 + (h[i % 32] * 7 + i * 131) % 2000) for i in range(n))


def cand(url, org, pub="2026-11-10", txt="기초연금 안내", title=None):
    return {"url": url, "org": org, "published": pub, "content": page(txt + " " + _uniq(url, 200)),
            "title": title if title is not None else _uniq(url + "t", 12)}


A = cand("https://www.korea.kr/news/a", "보건복지부")
B = cand("https://www.mohw.go.kr/b", "국민연금공단")


def kr_article(body, org="보건복지부", pub="2026-11-11T18:27:00+09:00", sidebar="", prev_next=""):
    """정책브리핑 기사 모양 — 사이드바(본문 밖)·view_title~view_opt 본문·이전/다음 기사 목록."""
    return (f'<html><head><title>{_uniq(body + org, 10)}</title></head><body><div class="side">{sidebar}</div>'
            f'<script>{{"datePublished": "{pub}", "author": {{"@type": "Organization", "name": "{org}" }}}}</script>'
            f'<div class="view_title"><h1>제목</h1><div class="view_cont">{body}</div>'
            f'<div>이전다음기사 영역 {prev_next}</div></div><div class="view_opt">x</div></body></html>').encode("utf-8")


class TestResearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ld = os.path.join(self.tmp.name, "ledger")
        self.sd = os.path.join(self.tmp.name, "sources")
        self.acc = C.load_account("test")
        self.alerts = []
        self.top = ["생활꿀팁", "기초연금", "국민연금", "건강보험", "연말정산"]
        self.seed_trend()

    def seed_trend(self, extra=(), top=None, out_of_scope=(), no_evidence=()):
        """top5 는 self.top 의 앞 5개. extra: top5 밖 in_scope 후보(점수 낮은 순서대로). out_of_scope: 금칙·범위 밖 후보."""
        top = self.top if top is None else top
        allkw = list(top) + list(extra)
        cands = [{"kw": k, "origin": "seed", "in_scope": True} for k in allkw]
        cands += [{"kw": k, "origin": "google_trends", "in_scope": False, "reason": "금칙"} for k in out_of_scope]
        scores = [{"kw": k, "value": round(0.9 - i * 0.01, 4),
                   "parts": {"yt_matches": 0 if k in no_evidence else 1, "gt_traffic": 0, "ig_like_median": None}}
                  for i, k in enumerate(allkw)]
        ledger.append("trend_ledger", {"date": TODAY.isoformat(), "account_id": "test", "status": "ok", "candidates": cands,
                                       "scores": scores,
                                       "top5": [{"rank": i + 1, "kw": k, "score": 1 - i / 10} for i, k in enumerate(top[:5])]},
                      self.ld)

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, disc):
        f = disc if callable(disc) else (lambda kw: disc)
        return R.run(self.acc, today=TODAY, fetchers={"discover": f}, ledger_dir=self.ld,
                     sources_dir=self.sd, notify=lambda *a: self.alerts.append(a))

    def tries(self):
        return [r for r in ledger.read("research_ledger", self.ld) if r["type"] == "try"]

    # --- G1 기본 ---
    def test_two_orgs_ok_sha(self):
        r = self.go([A, B])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["kw"], "생활꿀팁")
        led = ledger.read("source_ledger", self.ld)
        self.assertEqual(len(led), 2)
        for rec, c in zip(led, (A, B)):
            self.assertEqual(rec["sha256"], hashlib.sha256(c["content"]).hexdigest())
            with open(rec["saved_path"], "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), rec["sha256"])
            self.assertTrue(rec["org"] and rec["fetched_at"] and rec["url"] and rec["published"])
        self.assertEqual(self.alerts, [])

    def test_same_org_two_articles_is_hold(self):
        r = self.go([A, cand("https://www.korea.kr/news/a2", "보건복지부")])
        self.assertEqual(r["status"], "hold")
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(ledger.read("source_ledger", self.ld), [])  # hold 키워드는 저장하지 않음

    def test_same_org_extra_article_saved_counts_once(self):
        r = self.go([A, cand("https://www.korea.kr/news/a2", "보건복지부"), B])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["n_sources"], 3)
        self.assertEqual(r["orgs"], ["국민연금공단", "보건복지부"])

    def test_unknown_org_not_counted(self):
        x = cand("https://www.korea.kr/news/x", None)                       # org 없음 → 호스트로 대체 = 미상
        y = cand("https://www.mohw.go.kr/y", "mohw.go.kr")                  # org 가 호스트명 그대로 = 미상
        z = cand("https://www.korea.kr/news/z", "보건복지부")                # 확인된 기관 1곳
        self.assertFalse(R.org_is_known(x))
        self.assertFalse(R.org_is_known(y))
        self.assertTrue(R.org_is_known(z))
        r = self.go([x, y, z])
        self.assertEqual(r["status"], "hold")  # 확인된 기관이 1곳뿐
        self.assertIn("확인된 서로 다른 기관 1곳", self.tries()[0]["reason"])
        self.assertIn("기관 미상 2건 제외", self.tries()[0]["reason"])

    def test_unknown_org_saved_but_flagged_when_ok(self):
        x = cand("https://www.korea.kr/news/x", None)
        r = self.go([A, B, x])
        self.assertEqual(r["status"], "ok")
        self.assertEqual((r["n_sources"], r["orgs"]), (3, ["국민연금공단", "보건복지부"]))  # 미상은 기관 목록에서 제외
        led = ledger.read("source_ledger", self.ld)
        self.assertEqual([x["org_known"] for x in led], [True, True, False])

    def test_org_known_explicit_flag_wins(self):
        self.assertTrue(R.org_is_known({"url": "https://www.korea.kr/a", "org": "korea.kr", "org_known": True}))
        self.assertFalse(R.org_is_known({"url": "https://www.korea.kr/a", "org": "보건복지부", "org_known": False}))

    def test_unofficial_dropped(self):
        r = self.go([cand("https://blog.naver.com/x", "네이버"), A,
                     cand("https://evil-korea.kr.example.com/z", "가짜")])
        self.assertEqual(r["status"], "hold")
        dropped = self.tries()[0]["dropped"]
        self.assertEqual({d["reason"] for d in dropped}, {"비공식 도메인"})
        self.assertEqual(len(dropped), 2)

    # --- 날짜 ---
    def test_31_days_old_dropped(self):
        old = (TODAY - dt.timedelta(days=31)).isoformat()
        r = self.go([A, cand("https://www.mohw.go.kr/b", "국민연금공단", pub=old)])
        self.assertEqual(r["status"], "hold")
        self.assertIn("31일", self.tries()[0]["dropped"][0]["reason"])

    def test_30_days_old_kept(self):
        d = (TODAY - dt.timedelta(days=30)).isoformat()
        self.assertEqual(self.go([A, cand("https://www.mohw.go.kr/b", "국민연금공단", pub=d)])["status"], "ok")

    def test_no_date_dropped(self):
        r = self.go([A, cand("https://www.mohw.go.kr/b", "국민연금공단", pub=None)])
        self.assertEqual(r["status"], "hold")
        self.assertEqual(self.tries()[0]["dropped"][0]["reason"], "게시일 읽지 못함")

    def test_parse_date_formats(self):
        self.assertEqual(R.parse_date("2026-11-11T18:27:00+09:00"), dt.date(2026, 11, 11))
        self.assertEqual(R.parse_date("2026.11.11"), dt.date(2026, 11, 11))
        self.assertEqual(R.parse_date("Thu, 12 Nov 2026 07:07:00 GMT"), dt.date(2026, 11, 12))
        self.assertIsNone(R.parse_date("어제"))
        self.assertIsNone(R.parse_date(""))

    # --- top5 순회 ---
    def test_top1_fails_top2_adopted(self):
        r = self.go(lambda kw: [A, B] if kw == "기초연금" else [A])
        self.assertEqual((r["status"], r["kw"]), ("ok", "기초연금"))
        t = self.tries()
        self.assertEqual([(x["kw"], x["adopted"]) for x in t], [("생활꿀팁", False), ("기초연금", True)])
        self.assertEqual({s["kw"] for s in ledger.read("source_ledger", self.ld)}, {"기초연금"})
        self.assertEqual(self.alerts, [])

    def test_all_five_fail_one_alert(self):
        calls = []

        def disc(kw):
            calls.append(kw)
            return []
        r = self.go(disc)
        self.assertEqual(r["status"], "hold")
        self.assertEqual(calls, self.top)
        self.assertEqual(len(self.tries()), 5)
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.alerts[0][0], "warn")
        self.assertEqual(ledger.read("source_ledger", self.ld), [])

    def test_discover_error_continues_to_next(self):
        def disc(kw):
            if kw == "생활꿀팁":
                raise IOError("down")
            return [A, B]
        r = self.go(disc)
        self.assertEqual((r["status"], r["kw"]), ("ok", "기초연금"))
        self.assertIn("출처 검색 실패", self.tries()[0]["reason"])

    def test_no_trend_record_hold(self):
        r = R.run(self.acc, today=dt.date(2026, 1, 1), fetchers={"discover": lambda kw: []}, ledger_dir=self.ld,
                  sources_dir=self.sd, notify=lambda *a: self.alerts.append(a))
        self.assertEqual(r["status"], "hold")
        self.assertIsNone(r["kw"])
        self.assertEqual(len(self.alerts), 1)

    def test_duplicate_url_counted_once(self):
        r = self.go([A, dict(A), B])
        self.assertEqual(r["n_sources"], 2)

    # --- T-04d: 후보 넓히기 ---
    def fresh(self):
        shutil_rm = __import__("shutil").rmtree
        shutil_rm(self.ld, ignore_errors=True)
        shutil_rm(self.sd, ignore_errors=True)
        self.alerts.clear()

    def test_top5_all_fail_sixth_adopted(self):
        self.fresh()
        self.seed_trend(extra=["에너지바우처", "육아휴직"])
        tried = []

        def disc(kw):
            tried.append(kw)
            return [A, B] if kw == "에너지바우처" else []
        r = self.go(disc)
        self.assertEqual((r["status"], r["kw"]), ("ok", "에너지바우처"))
        self.assertEqual(tried, self.top + ["에너지바우처"])  # 7번째 후보는 시도하지 않음
        t = self.tries()
        self.assertEqual(len(t), 6)
        self.assertEqual((t[5]["src"], t[5]["adopted"], t[5]["rank"]), ("in_scope", True, 6))
        self.assertEqual(self.alerts, [])

    def test_max_15_tries(self):
        self.fresh()
        extra = [f"후보{i}" for i in range(20)]
        self.seed_trend(extra=extra)
        tried = []

        def disc(kw):
            tried.append(kw)
            return []
        r = self.go(disc)
        self.assertEqual(r["status"], "hold")
        self.assertEqual(len(tried), R.MAX_TRIES)
        self.assertEqual(R.MAX_TRIES, 15)
        self.assertEqual(len(self.tries()), 15)
        self.assertEqual(len(self.alerts), 1)

    def test_out_of_scope_and_dupes_skipped(self):
        self.fresh()
        self.seed_trend(extra=["기초연금", "연말 정산"], out_of_scope=["도박"], top=["연말정산", "기초연금"])
        tried = []
        self.go(lambda kw: tried.append(kw) or [])
        self.assertEqual(tried, ["연말정산", "기초연금"])  # '연말 정산'(공백만 다름)·중복·범위 밖(도박) 제외

    def test_evidence_none_marked(self):
        self.fresh()
        self.seed_trend(top=["지표있음"], extra=["근거없는시드"], no_evidence=["근거없는시드"])
        r = self.go(lambda kw: [A, B] if kw == "근거없는시드" else [])
        self.assertEqual((r["status"], r["kw"], r["evidence"]), ("ok", "근거없는시드", "none"))
        self.assertIn("evidence=none(지표 근거 없음, 공식 출처만 있음)", r["reason"])
        self.assertEqual([x["evidence"] for x in self.tries()], ["indicator", "none"])

    def test_evidence_indicator_marked(self):
        r = self.go([A, B])
        self.assertEqual(r["evidence"], "indicator")
        self.assertNotIn("evidence=none", r["reason"])

    def test_trends_evidence_field_preferred(self):
        self.assertTrue(R._has_evidence({"evidence": True, "parts": {}}))
        self.assertFalse(R._has_evidence({"evidence": False, "parts": {"yt_matches": 3}}))
        self.assertTrue(R._has_evidence({"parts": {"yt_matches": 0, "gt_traffic": 0, "ig_like_median": 0}}))  # IG 0 도 '있음'
        self.assertFalse(R._has_evidence({"parts": {"yt_matches": 0, "gt_traffic": 0, "ig_like_median": None}}))

    def test_no_in_scope_hold(self):
        self.fresh()
        self.seed_trend(top=[], out_of_scope=["도박"])
        r = self.go([A, B])
        self.assertEqual(r["status"], "hold")
        self.assertIsNone(r["kw"])

    def test_request_count_unchanged_when_keywords_grow(self):
        """키워드가 1개든 15개든 기관 사이트로 나가는 요청 수는 같다(provider 캐시)."""
        sm = (b'<urlset><url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=2</loc></url></urlset>')
        rss = ("<rss><channel><item><title>가</title><link>https://www.mohw.go.kr/b</link><description>나</description>"
               "<pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item></channel></rss>").encode("utf-8")
        lst = b'<a href="enewsView.do?news_seq=7" title="t">x</a>'
        view = ('<div class="b_info"><dl><dt>등록일</dt><dd>2026-11-10</dd></dl><div class="b_content">본문</div></div>'
                '<div class="synap_view"></div>').encode("utf-8")

        def count_for(n_kw):
            self.fresh()
            self.seed_trend(top=[f"없는말{i}" for i in range(min(5, n_kw))], extra=[f"없는말{i}" for i in range(5, n_kw)])
            urls = []

            class Fake:
                def get(self, url):
                    urls.append(url)
                    if url.endswith("sitemap_policy.xml"):
                        return sm, url
                    if url.endswith("sitemap_briefing.xml"):
                        return b"<urlset></urlset>", url
                    if url == R.MOHW_RSS:
                        return rss, url
                    if url == R.MOEL_LIST:
                        return lst, url
                    return (view if "enewsView" in url else page("정책 기사")), url
            r = R.run(self.acc, today=TODAY, fetchers={"discover": R.default_discover(Fake(), cache=R.SourceCache(os.path.join(self.tmp.name, f'cache{n_kw}')), today=TODAY)}, ledger_dir=self.ld,
                      sources_dir=self.sd, notify=lambda *a: None)
            self.assertEqual(r["status"], "hold")
            self.assertEqual(len(r["tried"]), n_kw)
            return len(urls)
        n1, n15 = count_for(1), count_for(15)
        self.assertGreater(n1, 0)
        self.assertEqual(n1, n15)

    # --- T-04e: 관련도 ---
    def test_relevance_stricter_rules(self):
        f = "가" * 400
        kw = "기초연금"
        self.assertEqual(R.relevance(kw, "기초연금 인상", page(f)), (True, "제목에 포함"))
        ok, why = R.relevance(kw, "무관", page("기초연금 안내 " + f + kw))
        self.assertTrue(ok)
        self.assertIn("본문 첫 300자 포함+본문 2회", why)
        self.assertEqual(R.relevance(kw, "무관", page("기초연금 안내 " + f)), (False, "본문 1회 언급·관련도 낮음"))
        self.assertEqual(R.relevance(kw, "무관", page(f + kw + f + kw + f + kw)), (True, "본문에 3회"))
        ok, why = R.relevance(kw, "무관", page(f + kw + f + kw))
        self.assertFalse(ok)
        self.assertIn("본문 2회지만 첫 문단 밖", why)
        self.assertEqual(R.relevance(kw, "무관", page(f + kw + f)), (False, "본문 1회 언급·관련도 낮음"))
        self.assertEqual(R.relevance(kw, "무관", page(f))[1], "본문에 없음·관련도 낮음")

    def test_relevance_ignores_nav_footer_popular(self):
        kw = "기초연금"
        html_ = ('<nav>기초연금 기초연금 기초연금</nav><footer>기초연금</footer>'
                 '<div class="popular_keyword">기초연금 기초연금</div><ul class="rank_list"><li>기초연금</li></ul>'
                 '<div class="b_content">' + "가" * 400 + "기초연금" + "가" * 400 + '</div>')
        self.assertEqual(R.relevance(kw, "무관", html_.encode("utf-8")), (False, "본문 1회 언급·관련도 낮음"))
        nomark = '<nav>기초연금 기초연금 기초연금</nav><div class="popular_keyword">기초연금</div><p>본문</p>'
        self.assertEqual(R.relevance(kw, "무관", nomark.encode("utf-8"))[0], False)
        self.assertNotIn("기초연금", R.strip_chrome(nomark))

    def test_relevance_uses_body_block_not_chrome(self):
        # 본문 표지(view_cont) 앞의 제목 영역·버튼 문구는 '첫 300자'에 세지 않는다
        art = ('<div class="view_title">' + "메뉴 " * 200 + '기초연금 </div><div class="view_cont">' + "가" * 400 + "기초연금" + '</div>').encode("utf-8")
        self.assertEqual(R.relevance("기초연금", "무관", art), (False, "본문 1회 언급·관련도 낮음"))

    def test_relevance_drop_recorded_in_run(self):
        low = dict(cand("https://www.korea.kr/news/low", "행정안전부"), relevance=(False, "본문 1회 언급·관련도 낮음"))
        r = self.go([A, low])
        self.assertEqual(r["status"], "hold")  # A 한 곳만 남음
        d = self.tries()[0]["dropped"]
        self.assertEqual(d, [{"url": "https://www.korea.kr/news/low", "reason": "본문 1회 언급·관련도 낮음"}])

    def test_providers_attach_relevance(self):
        sm = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=5</loc></url></urlset>'
        once = kr_article("가" * 400 + "기초연금" + "가" * 400)
        twice = kr_article("기초연금 " + "가" * 400 + "기초연금")

        class Fake:
            def __init__(self, art):
                self.art = art

            def get(self, url):
                return (sm if url.endswith("policy.xml") else b"<urlset></urlset>" if url.endswith("briefing.xml") else self.art), url
        a = R.KoreaKrProvider(Fake(once))("기초연금")[0]
        b = R.KoreaKrProvider(Fake(twice))("기초연금")[0]
        self.assertEqual(a["relevance"], (False, "본문 1회 언급·관련도 낮음"))
        self.assertTrue(b["relevance"][0])
        self.assertTrue(a["org_known"] and a["org"] == "보건복지부")
        res = R.screen([a, b], TODAY, C.load_json(os.path.join(C.CONFIG, "official_domains.json")))
        self.assertEqual(len(res[1]), 1 + 0)  # a 는 관련도로 탈락(b 는 같은 URL 이라 중복 처리) — 사유가 남는다
        self.assertEqual(res[1][0]["reason"], "본문 1회 언급·관련도 낮음")

    def test_mohw_and_moel_providers_relevance_and_known(self):
        rss = ("<rss><channel><item><title>기초연금 개편</title><link>https://www.mohw.go.kr/a</link>"
               "<description>내용</description><pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item>"
               "<item><title>다른 제목</title><link>https://www.mohw.go.kr/b</link>"
               "<description>한 줄 안내. " + "가" * 400 + " 기초연금 언급</description>"
               "<pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item></channel></rss>").encode("utf-8")

        class Fake:
            def get(self, url):
                return rss, url
        res = {x["url"][-1]: x for x in R.MohwRssProvider(Fake())("기초연금")}
        self.assertEqual(res["a"]["relevance"], (True, "제목에 포함"))
        self.assertEqual(res["b"]["relevance"], (False, "본문 1회 언급·관련도 낮음"))
        self.assertTrue(res["a"]["org_known"])

    # --- FIX_T04-08 ---
    def test_same_release_grouped_as_one(self):
        base = "겨울철 144만 가구에 에너지바우처 지급 위기가구 40만 명 발굴 " * 8
        a = dict(cand("https://www.korea.kr/news/a", "보건복지부"), title="겨울철 144만 가구에 에너지바우처 지급")
        a["content"] = page(base)
        b = dict(cand("https://www.mohw.go.kr/b", "국민연금공단"), title="겨울철 144만 가구에 에너지바우처 지급…")
        b["content"] = page(base + "추가")
        self.assertTrue(R.same_release(a, b))
        r = self.go([a, b])
        self.assertEqual(r["status"], "hold")  # 재게시 → 1곳으로 합산 → 2곳 못 채움
        self.assertIn("재게시 1건 합산", self.tries()[0]["reason"])

    def test_body_similarity_without_title_similarity(self):
        t = "정부는 오늘 겨울철 취약계층 난방비를 지원한다고 밝혔다 " * 10
        a = dict(cand("https://www.korea.kr/news/a", "보건복지부"), title="가나다라마바사")
        a["content"] = page(t)
        b = dict(cand("https://www.mohw.go.kr/b", "국민연금공단"), title="전혀 다른 제목 아자차카타")
        b["content"] = page(t)
        self.assertTrue(R.same_release(a, b))
        self.assertFalse(R.same_release(cand("https://www.korea.kr/news/x", "a"), cand("https://www.mohw.go.kr/y", "b")))

    def test_different_releases_still_ok_and_dup_of_recorded(self):
        dup = dict(A, url="https://www.korea.kr/news/a-repost")
        r = self.go([A, dup, B])
        self.assertEqual(r["status"], "ok")
        led = ledger.read("source_ledger", self.ld)
        self.assertEqual(sorted(x["dup_of"] is not None for x in led), [False, False, True])
        self.assertEqual(r["orgs"], ["국민연금공단", "보건복지부"])
        self.assertTrue(all("org_known" in x for x in led))

    def test_org_with_dot_is_unknown(self):
        self.assertFalse(R.org_is_known({"url": "https://www.korea.kr/a", "org": "www.example.go.kr"}))
        self.assertFalse(R.org_is_known({"url": "https://www.korea.kr/a", "org": "korea.kr"}))
        self.assertTrue(R.org_is_known({"url": "https://www.korea.kr/a", "org": "보건복지부"}))

    def test_run_gate_stop_file_and_paused(self):
        stop = os.path.join(self.tmp.name, "STOP")
        open(stop, "w").close()
        called = []
        r = R.run(self.acc, today=TODAY, fetchers={"discover": lambda kw: called.append(kw) or [A, B]}, ledger_dir=self.ld,
                  sources_dir=self.sd, notify=lambda *a: None, stop_file=stop)
        self.assertEqual(r["status"], "gated")
        self.assertEqual(called, [])
        self.assertEqual(ledger.read("research_ledger", self.ld), [])
        os.remove(stop)
        paused = dict(self.acc, paused=True)
        kw = dict(today=TODAY, fetchers={"discover": lambda k: [A, B]}, ledger_dir=self.ld, sources_dir=self.sd, stop_file=stop)
        self.assertEqual(R.run(paused, **kw)["status"], "gated")
        self.assertEqual(R.run(self.acc, **kw)["status"], "ok")
        self.assertEqual(R.run(paused, gate=False, **kw)["status"], "ok")

    def test_providers_use_only_official_domains_list(self):
        d = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
        for u in R.SITEMAPS + [R.MOHW_RSS, R.MOEL_LIST, R.MOEL_VIEW + "1"]:
            self.assertTrue(C.is_official_url(u, d), u)
        self.assertNotIn(".or.kr", d["suffixes"])
        self.assertNotIn("@", R.UA)
        self.assertNotIn("Mozilla", R.UA)

    # --- PoliteFetcher ---
    def fetcher_env(self, routes):
        calls = []

        class Resp:
            def __init__(s, st, body, hd):
                s.status_code, s.headers = st, hd or {}
                s.content = body if isinstance(body, bytes) else body.encode("utf-8")
                s.text = s.content.decode("utf-8")
                s.ok = st < 400

            def raise_for_status(s):
                if s.status_code >= 400:
                    raise IOError(s.status_code)

        def fake_get(url, headers=None, timeout=0, allow_redirects=True):
            calls.append((url, (headers or {}).get("User-Agent"), allow_redirects))
            st, body, hd = routes.get(url, (404, "", None))
            return Resp(st, body, hd)
        slept = []
        f = R.PoliteFetcher(sleep=lambda x: slept.append(x), domains=C.load_json(os.path.join(C.CONFIG, "official_domains.json")))
        return f, calls, slept, fake_get

    ALLOW = (200, "User-agent: *\nAllow: /", None)

    def test_fetcher_counts_robots_and_ua(self):
        routes = {"https://www.korea.kr/robots.txt": self.ALLOW,
                  "https://www.korea.kr/a": (200, "A", None), "https://www.korea.kr/b": (200, "B", None)}
        f, calls, slept, fake = self.fetcher_env(routes)
        with mock.patch("requests.get", fake):
            f.get("https://www.korea.kr/a")
            f.get("https://www.korea.kr/b")
        self.assertEqual(f.count["korea.kr"], 3)  # robots 1 + 페이지 2
        self.assertEqual(len(slept), 2)  # 첫 요청(robots)은 대기 없음, 이후 요청(페이지 2건)은 간격 대기 — robots 도 같은 시계를 쓴다
        self.assertTrue(all(ua == R.UA and "@" not in ua for _, ua, _ in calls))
        self.assertTrue(all(ar is False for _, _, ar in calls))  # 리다이렉트를 자동으로 따라가지 않음

    def test_fetcher_host_cap_includes_robots(self):
        routes = {"https://www.korea.kr/robots.txt": self.ALLOW}
        routes.update({f"https://www.korea.kr/p{i}": (200, "x", None) for i in range(5)})
        f, calls, slept, fake = self.fetcher_env(routes)
        f.max_pages = 3  # robots 1 + 2건
        with mock.patch("requests.get", fake):
            f.get("https://www.korea.kr/p0")
            f.get("https://www.korea.kr/p1")
            with self.assertRaises(RuntimeError):
                f.get("https://www.korea.kr/p2")

    def test_fetcher_redirect_final_url_rechecked(self):
        base = {"https://www.korea.kr/robots.txt": self.ALLOW,
                "https://www.mohw.go.kr/robots.txt": (200, "User-agent: *\nDisallow: /secret", None)}
        f, calls, slept, fake = self.fetcher_env(dict(base, **{"https://www.korea.kr/x": (302, "", {"Location": "https://evil.example.com/y"})}))
        with mock.patch("requests.get", fake), self.assertRaises(PermissionError):
            f.get("https://www.korea.kr/x")
        self.assertNotIn("https://evil.example.com/y", [c[0] for c in calls])
        f, calls, slept, fake = self.fetcher_env(dict(base, **{"https://www.korea.kr/x": (302, "", {"Location": "https://www.mohw.go.kr/secret/z"})}))
        with mock.patch("requests.get", fake), self.assertRaises(PermissionError):
            f.get("https://www.korea.kr/x")
        self.assertIn("https://www.mohw.go.kr/robots.txt", [c[0] for c in calls])
        f, calls, slept, fake = self.fetcher_env(dict(base, **{"https://www.korea.kr/x": (301, "", {"Location": "https://www.mohw.go.kr/ok"}),
                                                              "https://www.mohw.go.kr/ok": (200, "본문", None)}))
        with mock.patch("requests.get", fake):
            body, final = f.get("https://www.korea.kr/x")
        self.assertEqual((body, final), ("본문".encode("utf-8"), "https://www.mohw.go.kr/ok"))
        self.assertGreaterEqual(f.count["mohw.go.kr"], 2)

    def test_fetcher_refuses_unofficial_and_robots_disallow(self):
        f, calls, slept, fake = self.fetcher_env({"https://www.korea.kr/robots.txt": (200, "User-agent: *\nDisallow: /no", None)})
        with mock.patch("requests.get", fake):
            with self.assertRaises(PermissionError):
                f.get("https://blog.naver.com/x")
            with self.assertRaises(PermissionError):
                f.get("https://www.korea.kr/no/page")
        self.assertNotIn("https://blog.naver.com/x", [c[0] for c in calls])

    def test_robots_unreadable_means_blocked(self):
        f, calls, slept, fake = self.fetcher_env({})
        with mock.patch("requests.get", fake), self.assertRaises(PermissionError):
            f.get("https://www.korea.kr/a")

    # --- T-04f: 출처 누적 캐시 ---
    CACHE_SM = (b'<urlset>'
                b'<url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=1</loc></url>'
                b'<url><lastmod>2026-11-10</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=2</loc></url>'
                b'</urlset>')

    def cache_env(self, articles, mohw_items=(), moel=None):
        """가짜 fetcher: 요청 URL 기록. articles{url: html bytes}. 날짜별로 articles 를 바꿔 끼울 수 있게 dict 를 공유."""
        urls = []
        sm_rows = articles.get("_sm")

        class Fake:
            count = {}

            def get(self, url):
                urls.append(url)
                if url.endswith("sitemap_policy.xml"):
                    return articles["_sm"], url
                if url.endswith("sitemap_briefing.xml"):
                    return b"<urlset></urlset>", url
                if url == R.MOHW_RSS:
                    return articles.get("_rss", b"<rss><channel></channel></rss>"), url
                if url == R.MOEL_LIST:
                    return b"", url
                return articles[url], url
        return Fake(), urls

    def kr(self, newsid, body, org="보건복지부", pub="2026-11-11T10:00:00+09:00"):
        return f"https://www.korea.kr/news/policyNewsView.do?newsId={newsid}", kr_article(body, org=org, pub=pub)

    def disc(self, fake, day, cache_dir):
        return R.default_discover(fake, cache=R.SourceCache(cache_dir), today=day)

    def test_second_day_does_not_rerequest_first_day_urls(self):
        cdir = os.path.join(self.tmp.name, "c")
        u1, a1 = self.kr(1, "기초연금 안내 " * 3, "보건복지부")
        u2, a2 = self.kr(2, "다른 소식", "행정안전부", "2026-11-10T10:00:00+09:00")
        arts = {"_sm": self.CACHE_SM, u1: a1, u2: a2}
        fake, urls = self.cache_env(arts)
        d1 = self.disc(fake, dt.date(2026, 11, 12), cdir)
        d1("아무거나")
        first = [u for u in urls if "View.do" in u]
        self.assertEqual(sorted(first), sorted([u1, u2]))
        # 둘째 날: 새 기사 3 추가, 1·2 는 이미 캐시에 있음
        u3, a3 = self.kr(3, "새 소식", "국토교통부", "2026-11-12T08:00:00+09:00")
        arts["_sm"] = (b'<urlset><url><lastmod>2026-11-12</lastmod><loc>' + u3.encode() + b'</loc></url>'
                       b'<url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url>'
                       b'<url><lastmod>2026-11-10</lastmod><loc>' + u2.encode() + b'</loc></url></urlset>')
        arts[u3] = a3
        urls.clear()
        d2 = self.disc(fake, dt.date(2026, 11, 13), cdir)  # 새 SourceCache 인스턴스 = 프로그램 재시작과 같음
        d2("아무거나")
        self.assertEqual([u for u in urls if "View.do" in u], [u3])  # 새 URL 만 요청
        self.assertEqual(d2.summary()["known_skipped"] >= 2, True)

    def test_unparsable_page_not_rerequested(self):
        cdir = os.path.join(self.tmp.name, "c")
        u1 = "https://www.korea.kr/news/policyNewsView.do?newsId=1"
        fake, urls = self.cache_env({"_sm": self.CACHE_SM, u1: "<html>구조 모름</html>".encode("utf-8"),
                                     "https://www.korea.kr/news/policyNewsView.do?newsId=2": b"<html>x</html>"})
        self.disc(fake, TODAY, cdir)("x")
        urls.clear()
        self.disc(fake, TODAY, cdir)("x")
        self.assertEqual([u for u in urls if "View.do" in u], [])  # 읽을 수 없던 URL 도 다시 받지 않음

    def test_31_day_old_cached_article_not_matched_and_not_deleted(self):
        cdir = os.path.join(self.tmp.name, "c")
        old_pub = (TODAY - dt.timedelta(days=31)).isoformat() + "T10:00:00+09:00"
        u1, a1 = self.kr(1, "기초연금 안내 기초연금", "보건복지부", old_pub)
        u2, a2 = self.kr(2, "기초연금 소식 기초연금", "행정안전부", "2026-11-10T10:00:00+09:00")
        sm = (b'<urlset><url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url>'
              b'<url><lastmod>2026-11-11</lastmod><loc>' + u2.encode() + b'</loc></url></urlset>')
        fake, urls = self.cache_env({"_sm": sm, u1: a1, u2: a2})
        d = self.disc(fake, TODAY, cdir)
        got = d("기초연금")
        self.assertEqual([c["url"] for c in got], [u2])  # 31일 지난 u1 은 매칭 제외
        self.assertTrue(d.cache.has(u1))  # 지우지 않고 인덱스·저장본에 남아 있음
        self.assertTrue(os.path.exists(d.cache.entries[u1]["saved_path"]))
        # 30일째면 포함
        d30 = R.SourceCache(cdir)
        self.assertEqual(len(d30.match("기초연금", TODAY - dt.timedelta(days=0))), 1)
        self.assertEqual(len(d30.match("기초연금", dt.date(2026, 10, 12) + dt.timedelta(days=30))), 2)  # u1 게시 10-12 → 30일째 포함

    def test_yesterday_plus_today_two_orgs_ok_and_ledger_points_to_cache(self):
        cdir = os.path.join(self.tmp.name, "c")
        u1, a1 = self.kr(1, "기초연금 안내 " + "가" * 50 + " 기초연금", "보건복지부", "2026-11-11T10:00:00+09:00")
        sm1 = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url></urlset>'
        fake, urls = self.cache_env({"_sm": sm1, u1: a1})
        yday = dt.date(2026, 11, 12)
        self.top = ["기초연금"]
        self.fresh()
        self.seed_trend(top=["기초연금"])
        kw = dict(ledger_dir=self.ld, sources_dir=self.sd, notify=lambda *a: self.alerts.append(a), cache_dir=cdir)
        # 어제 실행: 기관 1곳만 → hold. 캐시에는 쌓임
        d1 = R.default_discover(fake, cache=R.SourceCache(cdir), today=yday)
        r1 = R.run(self.acc, today=yday, fetchers={"discover": d1}, **{k: v for k, v in kw.items() if k != "cache_dir"})
        self.assertEqual(r1["status"], "hold")
        # 오늘: 다른 기관 기사 1건이 새로 올라옴 → 캐시의 어제 기사 + 오늘 기사 = 두 기관 → ok
        u2, a2 = self.kr(2, "기초연금 개편 " + "나" * 50 + " 기초연금", "행정안전부", "2026-11-13T08:00:00+09:00")
        sm2 = (b'<urlset><url><lastmod>2026-11-13</lastmod><loc>' + u2.encode() + b'</loc></url>'
               b'<url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url></urlset>')
        fake2, urls2 = self.cache_env({"_sm": sm2, u1: a1, u2: a2})
        today = dt.date(2026, 11, 13)
        ledger.append("trend_ledger", {"date": today.isoformat(), "account_id": "test", "status": "ok",
                                       "candidates": [{"kw": "기초연금", "in_scope": True}],
                                       "scores": [{"kw": "기초연금", "value": 0.9, "parts": {"yt_matches": 1}}],
                                       "top5": [{"rank": 1, "kw": "기초연금", "score": 0.9}]}, self.ld)
        d2 = R.default_discover(fake2, cache=R.SourceCache(cdir), today=today)
        r2 = R.run(self.acc, today=today, fetchers={"discover": d2}, ledger_dir=self.ld, sources_dir=self.sd,
                   notify=lambda *a: None)
        self.assertEqual(r2["status"], "ok")
        self.assertEqual(r2["orgs"], ["보건복지부", "행정안전부"])
        self.assertEqual([u for u in urls2 if "View.do" in u], [u2])  # 어제 기사는 다시 요청하지 않음
        led = ledger.read("source_ledger", self.ld)
        cache = R.SourceCache(cdir)
        for rec in led:  # source_ledger 는 캐시 저장본 경로·sha256 을 그대로
            self.assertEqual(rec["saved_path"], cache.entries[rec["url"]]["saved_path"])
            self.assertEqual(rec["sha256"], cache.entries[rec["url"]]["sha256"])
            self.assertTrue(rec["saved_path"].startswith(cdir))
        self.assertEqual(r2["cache"]["in_window"], 2)

    def test_tampered_cache_file_fails_verify_and_is_excluded_from_matching(self):
        from cardnews import verify
        cdir = os.path.join(self.tmp.name, "c")
        u1, a1 = self.kr(1, "기초연금 지급액 인상 안내 " + _uniq("a", 120) + " 기초연금 " * 3, "보건복지부")
        u2, a2 = self.kr(2, "기초연금 신청 절차 개편 " + _uniq("b", 120) + " 기초연금 " * 3, "행정안전부", "2026-11-10T10:00:00+09:00")
        sm = (b'<urlset><url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url>'
              b'<url><lastmod>2026-11-10</lastmod><loc>' + u2.encode() + b'</loc></url></urlset>')
        fake, urls = self.cache_env({"_sm": sm, u1: a1, u2: a2})
        self.top = ["기초연금"]
        self.fresh()
        self.seed_trend(top=["기초연금"])
        d = R.default_discover(fake, cache=R.SourceCache(cdir), today=TODAY)
        r = R.run(self.acc, today=TODAY, fetchers={"discover": d}, ledger_dir=self.ld, sources_dir=self.sd,
                  notify=lambda *a: None)
        self.assertEqual(r["status"], "ok")
        led = ledger.read("source_ledger", self.ld)
        dom = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
        self.assertTrue(verify.check_g1(led, dom)[0])  # 변조 전엔 통과
        with open(led[0]["saved_path"], "ab") as f:
            f.write("<p>변조</p>".encode("utf-8"))
        ok, reason, _ = verify.check_g1(led, dom)
        self.assertFalse(ok)
        self.assertIn("sha256 불일치", reason)
        # 변조된 캐시 항목은 이후 매칭에서도 빠지고 기록된다
        c2 = R.SourceCache(cdir)
        got = c2.match("기초연금", TODAY)
        self.assertEqual(len(got), 1)
        self.assertEqual(c2.summary(TODAY)["tampered"] if c2.tampered_urls else len(c2.tampered_urls), 1)

    def test_cache_dir_default_is_data_source_cache(self):
        self.assertTrue(R.CACHE_DIR.replace("\\", "/").endswith("data/source_cache"))

    # --- T-04g: 금융위·산업통상부 + 총 상한 ---
    FSC_LIST_HTML = ('<a href="/no010101/88133?srchCtgry=&curPage=" title="x">가상자산사업자 보안 강화. 금일 등록된 게시글</a>'
                     '<a href="/no010101/88133?srchCtgry=">dup</a>'
                     '<a href="/no010101/88125?srchCtgry="><span>금융회사 지배구조 개선</span></a>').encode("utf-8")

    @staticmethod
    def fsc_view(body, day="2026-11-12", subject="가상자산사업자 보안 강화"):
        return ('<html><div class="board-view-wrap"><div class="header"><div class="subject">' + subject +
                '</div><div class="day"><span>' + day + '</span><span>조회수 : 1</span></div></div>'
                '<div class="cont"><script>var x=1;</script>' + body + '</div>이전글 다른 글 제목</div></html>').encode("utf-8")

    MOTIR_LIST_HTML = ('<a href="/kor/article/ATCL3f49a5a8c/172401/view?mno=&pageIndex=1"> 팀코리아 점검회의 개최 </a>'
                       '<a href="/kor/article/ATCL3f49a5a8c/172400/view?mno=&pageIndex=1">충청권 착공식</a>'
                       '<a href="/kor/article/ATCL3f49a5a8c/172401/view">dup</a>').encode("utf-8")

    @staticmethod
    def motir_view(body, day="2026-11-12"):
        return ('<html><h3 class="cont-tit">보도·참고자료</h3><ul><li><em>등록일</em><span>' + day + '</span></li></ul>'
                '<div>' + body + '</div>이전글 어떤 글</html>').encode("utf-8")

    def test_fsc_parsers(self):
        self.assertEqual(R.parse_fsc_list(self.FSC_LIST_HTML),
                         [(R.FSC_VIEW + "88133", "가상자산사업자 보안 강화"), (R.FSC_VIEW + "88125", "금융회사 지배구조 개선")])
        e = R.parse_fsc_view(self.fsc_view("본문 내용 가상자산 100억원"), R.FSC_VIEW + "88133")
        self.assertEqual((e["org"], e["org_known"], e["published"], e["title"]), ("금융위원회", True, "2026-11-12", "가상자산사업자 보안 강화"))
        text = R.body_text(e["content"])
        self.assertIn("본문 내용 가상자산 100억원", text)
        self.assertNotIn("다른 글 제목", text)  # 이전글 이후(내비)는 저장본에 없음
        self.assertNotIn("var x", text)
        self.assertIsNone(R.parse_fsc_view("<html>구조 모름</html>".encode("utf-8"), R.FSC_VIEW + "1"))
        self.assertIsNone(R.parse_fsc_view(self.fsc_view("x", day="날짜 없음"), R.FSC_VIEW + "1")["published"])

    def test_motir_parsers(self):
        self.assertEqual(R.parse_motir_list(self.MOTIR_LIST_HTML),
                         [(R.MOTIR_VIEW + "172401/view", "팀코리아 점검회의 개최"), (R.MOTIR_VIEW + "172400/view", "충청권 착공식")])
        e = R.parse_motir_view(self.motir_view("원전 2027년 4월 건설허가"), R.MOTIR_VIEW + "172401/view", "제목")
        self.assertEqual((e["org"], e["org_known"], e["published"]), ("산업통상부", True, "2026-11-12"))
        self.assertIn("원전 2027년 4월 건설허가", R.body_text(e["content"]))
        self.assertNotIn("어떤 글", R.body_text(e["content"]))
        self.assertIsNone(R.parse_motir_view(b"<html>x</html>", "u", "t"))

    def agency_fetcher(self, routes):
        class Fake:
            count = {}
            urls = []

            def get(s, url):
                s.urls.append(url)
                return routes[url], url
        return Fake()

    def test_fsc_and_motir_providers_refresh_into_cache_new_urls_only(self):
        routes = {R.FSC_LIST: self.FSC_LIST_HTML, R.FSC_VIEW + "88133": self.fsc_view("가상자산 본문 " * 5),
                  R.FSC_VIEW + "88125": self.fsc_view("지배구조 본문 " * 5, subject="금융회사 지배구조 개선"),
                  R.MOTIR_LIST: self.MOTIR_LIST_HTML,
                  R.MOTIR_VIEW + "172401/view": self.motir_view("점검회의 본문 " * 5),
                  R.MOTIR_VIEW + "172400/view": self.motir_view("착공식 본문 " * 5, day="2026-11-11")}
        cache = R.SourceCache(os.path.join(self.tmp.name, "c"))
        f = self.agency_fetcher(routes)
        for P in (R.FscProvider, R.MotirProvider):
            P(f).refresh(cache, TODAY)
        self.assertEqual(len([e for e in cache.entries.values() if e.get("saved_path")]), 4)
        orgs = sorted({e["org"] for e in cache.entries.values()})
        self.assertEqual(orgs, ["금융위원회", "산업통상부"])
        for e in cache.entries.values():  # 저장본 sha256 일치
            self.assertEqual(hashlib.sha256(open(e["saved_path"], "rb").read()).hexdigest(), e["sha256"])
        got = cache.match("점검회의", TODAY)
        self.assertEqual([(g["org"], g["published"]) for g in got], [("산업통상부", "2026-11-12")])
        # 둘째 실행: 목록만 다시 받고 상세는 재요청 없음
        f.urls.clear()
        for P in (R.FscProvider, R.MotirProvider):
            P(f).refresh(cache, TODAY)
        self.assertEqual(sorted(f.urls), sorted([R.FSC_LIST, R.MOTIR_LIST]))

    def test_new_providers_legacy_call_and_relevance(self):
        routes = {R.FSC_LIST: self.FSC_LIST_HTML, R.FSC_VIEW + "88133": self.fsc_view("가상자산 " * 5), R.FSC_VIEW + "88125": self.fsc_view("다른 내용", subject="금융회사 지배구조 개선")}
        res = R.FscProvider(self.agency_fetcher(routes))("가상자산")
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0]["relevance"][0])
        self.assertEqual(res[0]["org"], "금융위원회")

    def test_robots_block_skips_agency_without_detail_requests(self):
        routes = {"https://www.fsc.go.kr/robots.txt": (200, "User-agent: *\nDisallow: /no010101", None),
                  "https://www.motir.go.kr/robots.txt": (200, "User-agent: *\nDisallow: /kor/article", None)}
        f, calls, slept, fake = self.fetcher_env(routes)
        cache = R.SourceCache(os.path.join(self.tmp.name, "c"))
        with mock.patch("requests.get", fake):
            R.FscProvider(f).refresh(cache, TODAY)
            R.MotirProvider(f).refresh(cache, TODAY)
        self.assertEqual(cache.entries, {})
        fetched = [c[0] for c in calls]
        self.assertFalse(any(u.startswith((R.FSC_LIST, R.MOTIR_LIST)) for u in fetched))  # 목록도 요청하지 않음
        self.assertEqual(sorted(fetched), ["https://www.fsc.go.kr/robots.txt", "https://www.motir.go.kr/robots.txt"])

    def test_total_cap_and_host_shares(self):
        self.assertLessEqual(sum(R.HOST_CAPS.values()), R.TOTAL_MAX_PAGES)
        self.assertEqual(R.TOTAL_MAX_PAGES, 200)
        routes = {"https://www.korea.kr/robots.txt": self.ALLOW, "https://www.mohw.go.kr/robots.txt": self.ALLOW}
        for h in ("www.fsc.go.kr", "www.motir.go.kr", "www.moel.go.kr"):
            routes[f"https://{h}/robots.txt"] = self.ALLOW
        f, calls, slept, fake = self.fetcher_env(routes)
        f.max_total = 5
        f.host_caps = {}
        f.max_pages = 40
        routes.update({f"https://www.korea.kr/p{i}": (200, "x", None) for i in range(10)})
        with mock.patch("requests.get", fake):
            n = 0
            with self.assertRaises(RuntimeError) as cm:
                for i in range(10):
                    f.get(f"https://www.korea.kr/p{i}")
                    n += 1
        self.assertIn("총 상한", str(cm.exception))
        self.assertEqual(f.total, 5)  # robots 1 + 페이지 4
        self.assertEqual(n, 4)

    def test_full_default_discover_stays_within_caps(self):
        """모든 provider 가 최대로 쓰려 해도(큰 사이트맵·목록) 실행당 200·호스트별 몫을 넘지 않는다."""
        art = kr_article("정책 본문 " * 20)
        sm = ("<urlset>" + "".join(f'<url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId={i}</loc></url>'
                                   for i in range(100)) + "</urlset>").encode("utf-8")
        smb = ("<urlset>" + "".join(f'<url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/briefing/policyBriefingView.do?newsId={i}</loc></url>'
                                    for i in range(100)) + "</urlset>").encode("utf-8")
        rss = ("<rss><channel>" + "".join(
            f"<item><title>t{i}</title><link>https://www.mohw.go.kr/b{i}</link><description>d{i}</description><pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item>"
            for i in range(30)) + "</channel></rss>").encode("utf-8")
        moel_list = "".join(f'<a href="enewsView.do?news_seq={i}" title="t">x</a>' for i in range(100, 140)).encode("utf-8")
        moel_view = ('<div class="b_info"><dl><dt>등록일</dt><dd>2026-11-10</dd></dl><div class="b_content">본문</div></div>'
                     '<div class="synap_view"></div>').encode("utf-8")
        fsc_list = "".join(f'<a href="/no010101/{i}">t{i}</a>' for i in range(900, 940)).encode("utf-8")
        motir_list = "".join(f'<a href="/kor/article/ATCL3f49a5a8c/{i}/view">t{i}</a>' for i in range(100, 140)).encode("utf-8")

        class Resp:
            def __init__(s, body):
                s.status_code, s.headers, s.content, s.ok = 200, {}, body, True
                s.text = body.decode("utf-8", "replace")

            def raise_for_status(s):
                pass

        def fake_get(url, headers=None, timeout=0, allow_redirects=True):
            if url.endswith("/robots.txt"):
                return Resp(b"User-agent: *\nAllow: /")
            if url.endswith("sitemap_policy.xml"):
                return Resp(sm)
            if url.endswith("sitemap_briefing.xml"):
                return Resp(smb)
            if "korea.kr" in url:
                return Resp(art)
            if url == R.MOHW_RSS:
                return Resp(rss)
            if url == R.MOEL_LIST:
                return Resp(moel_list)
            if "moel.go.kr" in url:
                return Resp(moel_view)
            if url == R.FSC_LIST:
                return Resp(fsc_list)
            if "fsc.go.kr" in url:
                return Resp(self.fsc_view("본문 " * 10))
            if url == R.MOTIR_LIST:
                return Resp(motir_list)
            if url == R.NTS_LIST:
                return Resp(self.nts_list(range(500, 540)))
            if "nts.go.kr" in url:
                return Resp(self.nts_view("본문 " * 100))
            if url == R.BOK_LIST:
                return Resp(self.bok_list([("보도자료", n, f"t{n}") for n in range(600, 640)]).encode("utf-8"))
            if "bok.or.kr" in url:
                return Resp(self.bok_view("본문 " * 100))
            if url == R.NPS_LIST:
                return Resp(self.nps_list([f"P{n}" for n in range(40)]))
            if "nps.or.kr" in url:
                return Resp(self.nps_view("본문 " * 100))
            return Resp(self.motir_view("본문 " * 10))
        f = R.PoliteFetcher(sleep=lambda x: None)
        with mock.patch("requests.get", fake_get):
            d = R.default_discover(f, cache=R.SourceCache(os.path.join(self.tmp.name, "c")), today=TODAY)
            d("본문")
        self.assertLessEqual(f.total, R.TOTAL_MAX_PAGES)
        for host, n in f.count.items():
            self.assertLessEqual(n, R.HOST_CAPS.get(host, R.MAX_PAGES), host)
        self.assertEqual(sorted(f.count), ["bok.or.kr", "fsc.go.kr", "korea.kr", "moel.go.kr", "mohw.go.kr", "motir.go.kr",
                                          "nps.or.kr", "nts.go.kr"])
        self.assertEqual(d.summary()["requests_total"], f.total)

    # --- T-04h: 국세청·한국은행·국민연금공단 + robots 표준 해석 ---
    @staticmethod
    def nts_list(ids):
        return "".join(f'<tr><td><a href="javascript:;" data-id="{i}" title="국세청 제목 {i}"  class="nttInfoBtn">제목 {i}</a></td>'
                       f'<td data-table="date">2026.11.12.</td></tr>' for i in ids).encode("utf-8")

    @staticmethod
    def nts_view(body, day="2026.11.12.", subject="기준시가 사전열람"):
        return (f'<form><div class="bbs_ViewA"><h3> {subject}</h3><ul class="bbsV_data"><li><strong> 담당부서</strong> 과</li>'
                f'<li><strong> 작성일자</strong> {day}</li></ul><div class="bbsV_cont"><div>{body}</div></div>'
                '<div class="bbsV_atchmnfl">첨부파일 없음</div></div></form>').encode("utf-8")

    @staticmethod
    def bok_list(rows):
        return "<ul>" + "".join(
            f'<li class="bbsRowCls"><span class="i"><span class="t1">\n {kind}\n </span></span>'
            f'<span class="dataInfo"><span class="date"><span class="sr-only">등록일</span>2026.11.13</span></span>'
            f'<div class="set"><a href="/portal/bbs/B0000501/view.do?nttId={n}&amp;menuNo=201264" class="title">\n <!-- x -->\n {t}\n </a></div></li>'
            for kind, n, t in rows) + "</ul>"

    @staticmethod
    def bok_view(body, day="2026.11.13", subject="물가지수"):
        return (f'<div class="bd-view"><h2 class="subject">{subject}</h2><dl><dt class="sr-only">등록일</dt><dd class="date">{day}</dd></dl>'
                f'<div class="dbdata"><p>{body}</p></div></div></form><div class="btnSet"></div>').encode("utf-8")

    @staticmethod
    def nps_list(ids):
        return "".join(f'<li><p class="title"><a href="/pnsgdnc/nscvrgdata/getOHAE0002M1.do?menuId=MN24000898&pstId={i}&hmpgCd=01&sortSe=FR"> [보도자료] 연금 {i} </a></p></li>'
                       for i in ids).encode("utf-8")

    @staticmethod
    def nps_view(body, day=" 2026/11/12 ", subject="[보도자료] 해외수급자"):
        return (f'<div class="data-view"><table><tr><th scope="row">제목</th><td colspan="5" class="view-title">{subject}</td></tr>'
                f'<tr><th scope="row">등록일</th><td>{day}</td></tr></table><div class="data-view-contents">'
                f'<div class="view-contents-wrap"><p>{body}</p></div></div><ul><li>이전글</li></ul></div>').encode("utf-8")

    def test_nts_list_and_view_parse(self):
        lst = R.parse_nts_list(self.nts_list([1356055, 1355828, 1356055]))
        self.assertEqual([u for u, _ in lst], [R.NTS_VIEW + "1356055", R.NTS_VIEW + "1355828"])  # 중복 제거·순서 유지
        self.assertEqual(lst[0][1], "국세청 제목 1356055")
        e = R.parse_nts_view(self.nts_view("양도소득세 안내 " * 30), lst[0][0], lst[0][1])
        self.assertEqual((e["org"], e["published"], e["org_known"]), ("국세청", "2026-11-12", True))
        self.assertEqual(R.SourceCache.saved_date(e["content"]), dt.date(2026, 11, 12))  # 저장본 안 '게시일:' 에서 다시 읽힘
        self.assertNotIn("class=", R.body_text(e["content"]))
        self.assertNotIn("첨부파일", R.body_text(e["content"]))
        self.assertIsNone(R.parse_nts_view(self.nts_view("짧음"), "u", "t"))   # 본문 너무 짧음
        self.assertIsNone(R.parse_nts_view(b"<html>x</html>", "u", "t"))

    def test_bok_list_only_press_release_and_view(self):
        html_ = self.bok_list([("주간보도계획", 1, "주간"), ("보도자료", 2, "수출입물가지수"), ("공개시장운영 공지", 3, "RP"),
                               ("보도자료", 4, "금융안정 상황")])
        lst = R.parse_bok_list(html_)
        self.assertEqual([t for _, t in lst], ["수출입물가지수", "금융안정 상황"])
        self.assertTrue(lst[0][0].startswith("https://www.bok.or.kr/portal/bbs/B0000501/view.do?nttId=2&menuNo=201264"))  # &amp; 해제
        e = R.parse_bok_view(self.bok_view("물가 본문 " * 60), lst[0][0], lst[0][1])
        self.assertEqual((e["org"], e["published"], e["title"]), ("한국은행", "2026-11-13", "물가지수"))
        self.assertEqual(R.SourceCache.saved_date(e["content"]), dt.date(2026, 11, 13))
        self.assertIsNone(R.parse_bok_view(self.bok_view("※ 자세한 내용은 &lt;붙임&gt; 문서를 참조하시기 바랍니다."), "u", "t"))  # 첨부뿐

    def test_nps_list_and_view_parse(self):
        lst = R.parse_nps_list(self.nps_list(["ZZ1236", "ZZ1233", "ZZ1236"]))
        self.assertEqual([u for u, _ in lst], [R.NPS_VIEW + "ZZ1236", R.NPS_VIEW + "ZZ1233"])
        self.assertEqual(lst[0][1], "[보도자료] 연금 ZZ1236")
        e = R.parse_nps_view(self.nps_view("국민연금 본문 " * 40), lst[0][0], lst[0][1])
        self.assertEqual((e["org"], e["published"]), ("국민연금공단", "2026-11-12"))   # 2026/11/12 형식
        self.assertNotIn("이전글", R.body_text(e["content"]))
        self.assertNotIn("class=", R.body_text(e["content"]))

    def test_new_providers_refresh_cache_new_urls_only_and_negative_for_empty_body(self):
        bok_rows = self.bok_list([("보도자료", 2, "물가"), ("보도자료", 4, "첨부뿐")])
        bl = R.parse_bok_list(bok_rows)
        routes = {R.NTS_LIST: self.nts_list([11, 12]), R.NTS_VIEW + "11": self.nts_view("세금 본문 " * 40, subject="세금 A"),
                  R.NTS_VIEW + "12": self.nts_view("세금 본문 " * 40, day="2026.10.01.", subject="세금 B"),
                  R.BOK_LIST: bok_rows.encode("utf-8"), bl[0][0]: self.bok_view("물가 본문 " * 60), bl[1][0]: self.bok_view("붙임 참조"),
                  R.NPS_LIST: self.nps_list(["P1"]), R.NPS_VIEW + "P1": self.nps_view("연금 본문 " * 60)}
        cache = R.SourceCache(os.path.join(self.tmp.name, "c"))
        f = self.agency_fetcher(routes)
        for P in (R.NtsProvider, R.BokProvider, R.NpsProvider):
            P(f).refresh(cache, TODAY)
        pos = [e for e in cache.entries.values() if e.get("saved_path")]
        self.assertEqual(sorted(e["org"] for e in pos), ["국민연금공단", "국세청", "국세청", "한국은행"])
        neg = [e for e in cache.entries.values() if e.get("skip_reason")]
        self.assertEqual([e["url"] for e in neg], [bl[1][0]])
        # 30일 창은 저장본 날짜 기준(2026-10-01 은 TODAY 기준 밖)
        self.assertEqual(sorted(e["title"] for e in cache.within(TODAY) if e["org"] == "국세청"), ["세금 A"])
        # 둘째 실행: 목록만 다시 받고 상세 재요청 없음(음성 기록 포함)
        f.urls.clear()
        for P in (R.NtsProvider, R.BokProvider, R.NpsProvider):
            P(f).refresh(cache, TODAY)
        self.assertEqual(sorted(f.urls), sorted([R.NTS_LIST, R.BOK_LIST, R.NPS_LIST]))

    def test_new_providers_robots_block_skips_without_list_requests(self):
        routes = {"https://www.nts.go.kr/robots.txt": (200, "User-agent: *\nDisallow: /nts", None),
                  "https://www.bok.or.kr/robots.txt": (200, "User-agent: *\nDisallow: /\nAllow: /imer/", None),
                  "https://www.nps.or.kr/robots.txt": (200, "User-agent: *\nDisallow: /pnsgdnc/", None)}
        f, calls, slept, fake = self.fetcher_env(routes)
        cache = R.SourceCache(os.path.join(self.tmp.name, "c"))
        with mock.patch("requests.get", fake):
            for P in (R.NtsProvider, R.BokProvider, R.NpsProvider):
                P(f).refresh(cache, TODAY)
        self.assertEqual(cache.entries, {})
        self.assertEqual(sorted(c[0] for c in calls), sorted(routes))  # robots.txt 만 요청, 목록·상세 0

    def test_robots_rfc9309_longest_match_bok_style(self):
        r = R._RobotRules()
        r.parse(["User-agent : *", "Disallow: /", "Allow: /portal/", "Allow: /imer/"])   # 한국은행 실제 형태
        T = R.ROBOTS_TOKEN
        self.assertTrue(r.can_fetch(T, "https://www.bok.or.kr/portal/singl/newsData/listCont.do?menuNo=201263"))
        self.assertFalse(r.can_fetch(T, "https://www.bok.or.kr/kor/x.do"))
        self.assertFalse(r.can_fetch(T, "https://www.bok.or.kr/"))
        r.parse(["User-agent: *", "Disallow: /search/", "Disallow: /a/b.do?m=1*", "Disallow: /x$"])
        self.assertTrue(r.can_fetch(T, "https://h/ok"))
        self.assertFalse(r.can_fetch(T, "https://h/search/q"))
        self.assertFalse(r.can_fetch(T, "https://h/a/b.do?m=123"))
        self.assertTrue(r.can_fetch(T, "https://h/a/b.do?m=2"))
        self.assertFalse(r.can_fetch(T, "https://h/x"))
        self.assertTrue(r.can_fetch(T, "https://h/xy"))
        r.parse(["User-agent: *", "Disallow: /", "User-agent: cardnews-factory", "Allow: /ok"])  # 우리 토큰 그룹이 * 보다 우선
        self.assertTrue(r.can_fetch(T, "https://h/ok/1"))
        r.parse(["User-agent: *", "Disallow:"])   # 빈 Disallow = 전부 허용
        self.assertTrue(r.can_fetch(T, "https://h/anything"))
        r.parse(["User-agent: *", "Allow: /a", "Disallow: /a"])  # 같은 길이면 Allow
        self.assertTrue(r.can_fetch(T, "https://h/a"))

    def test_new_collector_urls_official_and_caps(self):
        d = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
        for u in (R.NTS_LIST, R.NTS_VIEW + "1", R.BOK_LIST, R.NPS_LIST, R.NPS_VIEW + "x"):
            self.assertTrue(C.is_official_url(u, d), u)
        for h in ("nts.go.kr", "bok.or.kr", "nps.or.kr"):
            self.assertLessEqual(R.HOST_CAPS[h], 15)
        self.assertLessEqual(sum(R.HOST_CAPS.values()), R.TOTAL_MAX_PAGES)

    # --- T-04h2: 기관 수 판정을 verify G1 과 공유 · robots 그룹 병합 ---
    def test_h2_portal_org_not_counted_moves_to_next_keyword(self):
        mohw = cand("https://www.mohw.go.kr/h2a", "보건복지부")
        ktv = cand("https://www.korea.kr/h2b", "KTV")
        nts = cand("https://www.nts.go.kr/h2c", "국세청")
        r = self.go(lambda kw: [mohw, ktv] if kw == "생활꿀팁" else ([mohw, nts] if kw == "기초연금" else []))
        self.assertEqual((r["status"], r["kw"]), ("ok", "기초연금"))   # 복지부+KTV 는 1기관 → 다음 후보
        self.assertEqual(r["orgs"], ["국세청", "보건복지부"])
        first = self.tries()[0]
        self.assertFalse(first["adopted"])
        self.assertIn("1곳", first["reason"])

    def test_h2_research_and_verify_count_same_agencies(self):
        from cardnews import verify
        d = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
        pairs = [("보건복지부", "KTV"), ("보건복지부", "KTV 국민방송"), ("보건복지부", "국민방송"), ("보건복지부", "정책브리핑"),
                 ("보건복지부", "대한민국정책브리핑"), ("보건복지부", "정부24"), ("보건복지부", "국세청"),
                 ("보건복지부", "한국정책방송원"), ("보건복지부", "보건복지부"), ("보건복지부", "www.korea.kr"), ("보건복지부", "")]
        for i, (o1, o2) in enumerate(pairs):
            self.fresh()
            c1 = cand(f"https://www.mohw.go.kr/h2x{i}", o1)
            c2 = cand(f"https://www.nts.go.kr/h2y{i}", o2)
            r = self.go([c1, c2])
            srcs = ledger.read("source_ledger", self.ld)
            ok_g1, _, _ = verify.check_g1(srcs, d)
            self.assertEqual(r["status"] == "ok", ok_g1, (o1, o2))   # 같은 입력 → 같은 기관 수 판정
            if srcs:
                self.assertEqual(len({verify.counts_as_agency(x, d) for x in srcs} - {None}),
                                 len(r["orgs"]), (o1, o2))

    def test_h2_robots_duplicate_group_merged(self):
        r = R._RobotRules()
        r.parse(["User-agent: *", "Disallow: /a/", "", "User-agent: *", "Disallow: /b/", "",
                 "User-agent: cardnews-factory", "Disallow: /c/", "User-agent: cardnews-factory", "Disallow: /d/"])
        T = R.ROBOTS_TOKEN
        self.assertFalse(r.can_fetch(T, "https://h/c/1"))
        self.assertFalse(r.can_fetch(T, "https://h/d/1"))   # 같은 에이전트 그룹 둘이 병합
        self.assertTrue(r.can_fetch(T, "https://h/a/1"))    # 우리 토큰 그룹이 있으면 * 는 안 씀
        r.parse(["User-agent: *", "Disallow: /a/", "", "User-agent: *", "Disallow: /b/"])
        self.assertFalse(r.can_fetch(T, "https://h/a/1"))
        self.assertFalse(r.can_fetch(T, "https://h/b/1"))   # * 그룹 둘 병합
        self.assertTrue(r.can_fetch(T, "https://h/ok"))

    # --- 후속: run_id · 산업부 공유버튼 ---
    def test_run_id_in_return_ledgers_and_sources_for_run(self):
        r1 = self.go([A, B])
        r2 = self.go([A, B])  # 같은 키워드 재실행 → source_ledger 에 같은 줄이 또 쌓인다
        self.assertTrue(r1["run_id"].startswith("research-") and r2["run_id"].startswith("research-"))
        self.assertNotEqual(r1["run_id"], r2["run_id"])
        led = ledger.read("source_ledger", self.ld)
        self.assertEqual(len(led), 4)  # 2+2 줄
        self.assertEqual({x["run_id"] for x in led}, {r1["run_id"], r2["run_id"]})
        for rec in self.tries():
            self.assertIn(rec["run_id"], (r1["run_id"], r2["run_id"]))
        mine = R.sources_for_run(r2, self.ld)
        self.assertEqual(len(mine), 2)
        self.assertTrue(all(x["run_id"] == r2["run_id"] for x in mine))
        self.assertEqual(R.sources_for_run({"run_id": None}, self.ld), [])  # run_id 없으면 아무것도 안 돌려줌

    def test_sources_for_run_dedupes_url_sha(self):
        rid = "research-x"
        for _ in range(2):  # 같은 run_id 안에서 같은 줄이 두 번 쓰였다고 가정
            ledger.append("source_ledger", {"url": "u", "sha256": "s", "run_id": rid, "kw": "k"}, self.ld)
        ledger.append("source_ledger", {"url": "u", "sha256": "s", "run_id": "other", "kw": "k"}, self.ld)
        self.assertEqual(len(R.sources_for_run({"run_id": rid}, self.ld)), 1)

    def test_gated_has_no_run_id_and_explicit_run_id_kept(self):
        stop = os.path.join(self.tmp.name, "STOP")
        open(stop, "w").close()
        r = R.run(self.acc, today=TODAY, fetchers={"discover": lambda kw: []}, ledger_dir=self.ld, sources_dir=self.sd, stop_file=stop)
        self.assertEqual(r["status"], "gated")
        os.remove(stop)
        r = R.run(self.acc, today=TODAY, fetchers={"discover": lambda kw: [A, B]}, ledger_dir=self.ld, sources_dir=self.sd,
                  stop_file=stop, run_id="research-fixed")
        self.assertEqual(r["run_id"], "research-fixed")
        self.assertEqual({x["run_id"] for x in ledger.read("source_ledger", self.ld)}, {"research-fixed"})

    MOTIR_REAL_LIKE = (
        '<html><h3 class="cont-tit"><i>보도·참고자료</i></h3>'
        '<!-- page share --><div class="page-share"><div class="page-share-sns"><button type="button" class="share-btn-sns"><i>페이지 공유</i></button>'
        '<div class="share-list"><a href="x" class="sns-facebook"><i>페이스북</i></a><a class="sns-twitter"><i>X</i></a>'
        '<a class="share-btn-close">sns 공유닫기</a></div></div><div><button type="button" class="share-btn-print"><i>프린트</i></button></div></div>'
        '<!-- //page share --></div><!-- //컨텐츠 Header --><!-- 컨텐츠 본문 영역 --><!-- 본문 시작 -->'
        '<link type="text/css" rel="stylesheet" href="/a.css"><form action="/k"><input type="hidden" name="mno" value=""/></form>'
        '<ul><li><em>담당자</em><span>이수정</span></li><li><em>등록일</em><span>2026-11-12</span></li></ul>'
        '<div>원전 2027년 4월 건설허가 신청 계획을 점검했다. 기업간 공유하고 지원한다.</div>이전글 다른 글</html>').encode("utf-8")

    def test_motir_share_button_text_removed_from_body_and_head(self):
        e = R.parse_motir_view(self.MOTIR_REAL_LIKE, R.MOTIR_VIEW + "1/view", "제목")
        text = R.body_text(e["content"])
        for junk in ("페이지 공유", "프린트", "페이스북", "sns 공유닫기", "본문 시작", "class=", "page-share"):
            self.assertNotIn(junk, text, junk)
        self.assertIn("기업간 공유하고 지원한다", text)  # 본문 속 '공유' 는 그대로
        self.assertTrue(text.startswith("담당자"))  # 첫 300자는 본문 정보부터 시작
        self.assertEqual(e["published"], "2026-11-12")
        self.assertNotIn("다른 글", text)

    def test_body_text_has_no_tag_fragment_prefix(self):
        t = R.body_text('<div class="b_content">본문 시작 글</div>'.encode("utf-8"))
        self.assertEqual(t, "본문 시작 글")
        self.assertEqual(R.body_text('<div class="view_cont" id="a">내용</div>'.encode("utf-8")), "내용")

    # --- T-R7a: 호스트 예외 격리 · 캐시 무결성 ---
    @staticmethod
    def _r7_lines(path):
        with open(path, encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]

    def _r7_setup(self, kw="기초연금"):
        self.top = [kw]
        self.fresh()
        self.seed_trend(top=[kw])
        return dict(ledger_dir=self.ld, sources_dir=self.sd, notify=lambda *a: None)

    def test_r7_one_host_exception_others_continue(self):
        cdir = os.path.join(self.tmp.name, "c")
        u1, a1 = self.kr(1, "기초연금 안내 " + "가" * 50 + " 기초연금", "보건복지부")
        sm = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>' + u1.encode() + b'</loc></url></urlset>'
        fake, _ = self.cache_env({"_sm": sm, u1: a1})
        kw = self._r7_setup()
        with mock.patch.object(R.MohwRssProvider, "refresh", side_effect=ValueError("boom")):
            d = R.default_discover(fake, cache=R.SourceCache(cdir), today=TODAY)
            r = R.run(self.acc, today=TODAY, fetchers={"discover": d}, **kw)
        self.assertNotEqual(r["status"], "error")  # korea.kr 쪽은 계속 돌았다(기관 1곳이라 hold)
        self.assertEqual(r["status"], "hold")
        self.assertEqual(r["cache"]["entries"], 1)
        self.assertIn("MohwRssProvider", r["cache"]["host_errors"])
        hosts = [x for x in ledger.read("research_ledger", self.ld) if x.get("type") == "host_error"]
        self.assertEqual([h["host"] for h in hosts], ["MohwRssProvider"])
        self.assertIn("boom", hosts[0]["reason"])

    def test_r7_all_hosts_fail_status_error(self):
        cdir = os.path.join(self.tmp.name, "c")
        fake, _ = self.cache_env({"_sm": b"<urlset></urlset>"})
        kw = self._r7_setup()
        names = ("KoreaKrProvider", "MohwRssProvider", "MoelProvider", "FscProvider", "MotirProvider",
                 "NtsProvider", "BokProvider", "NpsProvider")
        patches = [mock.patch.object(getattr(R, n), "refresh", side_effect=RuntimeError(n)) for n in names]
        for pt in patches:
            pt.start()
        try:
            d = R.default_discover(fake, cache=R.SourceCache(cdir), today=TODAY)
            r = R.run(self.acc, today=TODAY, fetchers={"discover": d}, **kw)
        finally:
            for pt in patches:
                pt.stop()
        self.assertEqual(r["status"], "error")
        self.assertIn("모든 수집처 실패", r["reason"])
        hosts = [x for x in ledger.read("research_ledger", self.ld) if x.get("type") == "host_error"]
        self.assertEqual(len(hosts), 8)

    def test_r7_index_published_forged_uses_saved_date(self):
        cdir = os.path.join(self.tmp.name, "c")
        u1, a1 = self.kr(1, "기초연금 안내 " + "가" * 50, "보건복지부", "2026-09-01T10:00:00+09:00")  # 실제로는 오래된 글
        fake, _ = self.cache_env({"_sm": b"<urlset></urlset>"})
        c = R.SourceCache(cdir)
        e = R.KoreaKrProvider(fake).parse_page(a1, u1)
        c.add(e)
        # index 의 published 를 최근 날짜로 위조(저장본은 그대로)
        lines = self._r7_lines(c.index)
        lines[-1]["published"] = "2026-11-11"
        with open(c.index, "w", encoding="utf-8") as f:
            for x in lines:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        c2 = R.SourceCache(cdir)
        self.assertEqual(c2.within(TODAY), [])  # 저장본 날짜(09-01)는 30일 밖
        self.assertEqual(c2.match("기초연금", TODAY), [])
        # 반대: index 가 오래된 날짜로 적혀 있어도 저장본이 최근이면 저장본 날짜 사용
        u2, a2 = self.kr(2, "기초연금 개편 " + "나" * 50, "보건복지부", "2026-11-10T10:00:00+09:00")
        c2.add(R.KoreaKrProvider(fake).parse_page(a2, u2))
        lines = self._r7_lines(c2.index)
        lines[-1]["published"] = "2026-01-01"
        with open(c2.index, "w", encoding="utf-8") as f:
            for x in lines:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        got = R.SourceCache(cdir).within(TODAY)
        self.assertEqual([x["url"] for x in got], [u2])
        self.assertEqual(got[0]["published"], "2026-11-10")

    def test_r7_undatable_saved_file_excluded_from_window(self):
        cdir = os.path.join(self.tmp.name, "c")
        c = R.SourceCache(cdir)
        c.add({"url": "https://www.korea.kr/news/policyNewsView.do?newsId=9", "org": "보건복지부", "org_known": True,
               "published": "2026-11-11", "title": "t", "content": "<html><body>날짜 없는 본문 기초연금</body></html>".encode()})
        self.assertEqual(R.SourceCache(cdir).within(TODAY), [])

    def test_r7_saved_path_relative_roundtrip_and_legacy_absolute(self):
        cdir = os.path.join(self.tmp.name, "c")
        c = R.SourceCache(cdir)
        content = "<html><body><p>게시일: 2026-11-11</p>기초연금 본문</body></html>".encode()
        rec = c.add({"url": "https://www.korea.kr/news/policyNewsView.do?newsId=5", "org": "보건복지부", "org_known": True,
                     "published": "2026-11-11", "title": "t", "content": content})
        raw_line = self._r7_lines(c.index)[-1]
        self.assertFalse(os.path.isabs(raw_line["saved_path"]))
        self.assertTrue(raw_line["saved_path"].startswith("files/"))
        self.assertTrue(os.path.isabs(rec["saved_path"]) and os.path.exists(rec["saved_path"]))
        c2 = R.SourceCache(cdir)
        e = c2.entries["https://www.korea.kr/news/policyNewsView.do?newsId=5"]
        self.assertEqual(os.path.normcase(e["saved_path"]), os.path.normcase(rec["saved_path"]))
        self.assertEqual(len(c2.match("기초연금", TODAY)), 1)
        # 옛 절대경로 줄도 읽힌다
        legacy = {**raw_line, "url": "https://www.korea.kr/news/policyNewsView.do?newsId=6", "saved_path": rec["saved_path"]}
        with open(c.index, "a", encoding="utf-8") as f:
            f.write(json.dumps(legacy, ensure_ascii=False) + "\n")
        c3 = R.SourceCache(cdir)
        self.assertEqual(c3.entries[legacy["url"]]["saved_path"], rec["saved_path"])
        self.assertEqual(len(c3.within(TODAY)), 2)

    # --- provider ---
    def test_sitemap_parse_and_korea_kr_provider(self):
        sm = (b'<urlset><url><lastmod>2026-11-10</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=1</loc></url>'
              b'<url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=2</loc></url></urlset>')
        self.assertEqual([u for _, u in R.parse_sitemap(sm)][0][-1], "2")  # 최신순
        art = kr_article("기초연금 인상", org="보건복지부", pub="2026-11-11T18:27:00+09:00")
        self.assertEqual(R.korea_kr_meta(art), ("보건복지부", "2026-11-11T18:27:00+09:00"))

        class Fake:
            def get(self, url):
                if url.endswith("policy.xml"):
                    return sm, url
                if url.endswith("briefing.xml"):
                    raise IOError("x")
                return (art if url.endswith("=2") else kr_article("무관한 글")), url
        res = R.KoreaKrProvider(Fake())("기초연금")
        self.assertEqual([x["url"][-1] for x in res], ["2"])
        self.assertEqual(res[0]["org"], "보건복지부")
        self.assertEqual(R.parse_date(res[0]["published"]), dt.date(2026, 11, 11))

    def test_korea_kr_sidebar_and_prev_next_do_not_match(self):
        """T-04d 실측 오탐 회귀: 사이드바 '주요 뉴스'·이전/다음 기사 제목에 키워드가 있어도 본문에 없으면 매칭 안 함."""
        sm = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=5</loc></url></urlset>'
        art = kr_article("무관한 본문", sidebar="주요 뉴스 겨울철 에너지바우처 지급", prev_next="이전기사 에너지바우처 안내 다음기사")

        class Fake:
            def get(self, url):
                return (sm if url.endswith("policy.xml") else b"<urlset></urlset>" if url.endswith("briefing.xml") else art), url
        p = R.KoreaKrProvider(Fake())
        self.assertEqual(p("에너지바우처"), [])
        self.assertEqual(len(p("무관한 본문")), 1)
        # 저장본(content)에도 사이드바·이전/다음 기사 문구가 들어가지 않는다 → T-05 숫자 대조가 오염되지 않음
        saved = p("무관한 본문")[0]["content"].decode("utf-8")
        self.assertNotIn("주요 뉴스", saved)
        self.assertNotIn("이전기사", saved)

    def test_korea_kr_page_without_article_block_is_skipped(self):
        sm = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/news/policyNewsView.do?newsId=5</loc></url></urlset>'

        class Fake:
            def get(self, url):
                return (sm if url.endswith("policy.xml") else b"<urlset></urlset>" if url.endswith("briefing.xml")
                        else "<html>기초연금 전체 페이지</html>".encode("utf-8")), url
        self.assertEqual(R.KoreaKrProvider(Fake())("기초연금"), [])  # 구조를 못 읽으면 전체로 대신하지 않음

    def test_korea_kr_briefing_org_is_host_not_person_and_lastmod_not_used(self):
        sm = b'<urlset><url><lastmod>2026-11-11</lastmod><loc>https://www.korea.kr/briefing/policyBriefingView.do?newsId=9</loc></url></urlset>'

        def prov(art):
            class Fake:
                def get(self, url):
                    return (sm if url.endswith("briefing.xml") else b"<urlset></urlset>" if url.endswith("policy.xml") else art), url
            return R.KoreaKrProvider(Fake())("기초연금")
        res = prov(kr_article("기초연금 기초연금", org="김근성 상임위원", pub=""))
        self.assertEqual((res[0]["org"], res[0]["org_known"], res[0]["published"]), ("korea.kr", False, None))
        keep, drop = R.screen(res, TODAY, C.load_json(os.path.join(C.CONFIG, "official_domains.json")))
        self.assertEqual(keep, [])
        self.assertIn("lastmod", drop[0]["reason"])
        res = prov(kr_article("2026.11.09 김근성 상임위원 기초연금 기초연금", org="김근성 상임위원", pub=""))
        self.assertEqual(res[0]["published"], "2026-11-09")

    def test_mohw_rss_provider(self):
        rss = ("<rss><channel><item><title><![CDATA[기초연금 개편]]></title><link>https://www.mohw.go.kr/board.es?x=1</link>"
               "<description><![CDATA[기초연금 월 지급액 안내]]></description><pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item>"
               "<item><title>무관</title><link>https://www.mohw.go.kr/board.es?x=2</link><description>다른 내용</description>"
               "<pubDate>Thu, 12 Nov 2026 07:07:00 GMT</pubDate></item></channel></rss>").encode("utf-8")

        class Fake:
            n = 0

            def get(self, url):
                Fake.n += 1
                return rss, url
        p = R.MohwRssProvider(Fake())
        res = p("기초연금")
        self.assertEqual(len(res), 1)
        self.assertEqual((res[0]["org"], res[0]["url"]), ("보건복지부", "https://www.mohw.go.kr/board.es?x=1"))
        p("연말정산")
        self.assertEqual(Fake.n, 1)  # 키워드가 바뀌어도 RSS 는 한 번만 받음
        self.assertIn("기초연금 월 지급액", res[0]["content"].decode("utf-8"))

    def test_moel_provider_parse_and_single_load(self):
        lst = ('<a href="enewsView.do?news_seq=7" class="e" title="기초연금 현황">x</a>'
               '<a href="enewsView.do?news_seq=9" class="e" title="무관 공고">y</a>'
               '<a href="enewsView.do?news_seq=9" title="무관 공고">dup</a>').encode("utf-8")

        def view(seq, body):
            return (f'<div class="b_info"><dl><dt>제목</dt><dd>t{seq}</dd></dl><dl><dt>등록일</dt><dd>2026-11-10&nbsp;</dd></dl>'
                    f'<div class="b_content">{body}</div></div><div class="synap_view">nav 국민연금</div>').encode("utf-8")

        class Fake:
            urls = []

            def get(self, url):
                Fake.urls.append(url)
                if url == R.MOEL_LIST:
                    return lst, url
                return (view(7, "기초연금 월 지급 안내") if url.endswith("=7") else view(9, "다른 내용")), url
        self.assertEqual([x[0] for x in R.parse_moel_list(lst)], ["9", "7"])  # 번호 큰 순·중복 제거
        self.assertEqual(R.parse_moel_view(view(7, "본문"))[0], "2026-11-10")
        p = R.MoelProvider(Fake())
        res = p("기초연금")
        self.assertEqual(len(res), 1)
        self.assertEqual((res[0]["org"], res[0]["published"], res[0]["url"]),
                         ("고용노동부", "2026-11-10", R.MOEL_VIEW + "7"))
        self.assertEqual(p("국민연금"), [])  # synap_view(본문 밖) 문구는 매칭되지 않음
        self.assertEqual(len(Fake.urls), 3)  # 목록1 + 상세2, 키워드 바뀌어도 재요청 없음
        self.assertEqual(R.screen(res, TODAY, C.load_json(os.path.join(C.CONFIG, "official_domains.json")))[1], [])

    def test_korea_kr_budget_fills_host_cap(self):
        n = R.KoreaKrProvider(None).per
        total = 1 + len(R.SITEMAPS) + n * len(R.SITEMAPS)  # robots.txt 1 + 사이트맵 + 기사
        self.assertLessEqual(total, R.MAX_PAGES)
        self.assertGreaterEqual(total, R.MAX_PAGES - len(R.SITEMAPS))


if __name__ == "__main__":
    unittest.main()
