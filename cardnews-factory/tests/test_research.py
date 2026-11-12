# -*- coding: utf-8 -*-
"""T-04/T-04b 수용 기준. 네트워크 없음(가짜 discover·가짜 fetcher)."""
import datetime as dt
import hashlib
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
