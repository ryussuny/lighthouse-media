# -*- coding: utf-8 -*-
"""T-03 수용 기준: AC-2(지표원 2개 이상 원값·시각·점수·1~5위 원장 기록) + 지표 0개 정상 종료."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C, ledger, trends as T  # noqa: E402

GT_XML = """<?xml version="1.0"?><rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
<item><title>기초연금 인상</title><ht:approx_traffic>2000+</ht:approx_traffic><pubDate>x</pubDate></item>
<item><title>혜리</title><ht:approx_traffic>500+</ht:approx_traffic><ht:news_item><ht:news_item_title>드라마 출연</ht:news_item_title></ht:news_item></item>
<item><title>에너지 대책</title><ht:approx_traffic>200+</ht:approx_traffic><ht:news_item><ht:news_item_title>에너지바우처 신청 시작</ht:news_item_title></ht:news_item></item>
<item><title>급등 종목 정부지원금</title><ht:approx_traffic>1000+</ht:approx_traffic></item>
</channel></rss>""".encode("utf-8")
VIDEOS = [{"title": "생활꿀팁 모음 10가지", "views": 1_200_000, "cat": "26"},
          {"title": "국민연금 개편 핵심 정리", "views": 300_000, "cat": "25"}]


class TestTrends(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.acc = C.load_account("test")
        self.banned = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
        self.alerts = []

    def tearDown(self):
        self.tmp.cleanup()

    def fx(self, gt=True, yt=True, ig=True):
        def g(day):
            if not gt:
                raise IOError("down")
            return T.parse_google_trends(GT_XML), "gt.xml"

        def y(day, cats):
            if not yt:
                raise IOError("down")
            return VIDEOS, ["yt.json"]

        def i(today):
            return ({"정부지원금": 1185, "생활꿀팁": 1592} if ig else {}), ("ig.json" if ig else None)
        return {"google_trends": g, "youtube": y, "ig": i}

    def run_(self, **kw):
        return T.run(self.acc, self.banned, fetchers=self.fx(**{k: v for k, v in kw.items() if k in ("gt", "yt", "ig")}),
                     today=dt.date(2026, 11, 12), ledger_dir=self.tmp.name, exclude_kws=kw.get("exclude", ()),
                     notify=lambda *a: self.alerts.append(a))

    def test_ac2_ledger(self):
        rec = self.run_()
        self.assertEqual(rec["status"], "ok")
        self.assertGreaterEqual(len({s["name"] for s in rec["sources"]}), 2)
        for s in rec["sources"]:
            self.assertIn("fetched_at", s)
            self.assertIn("raw_path", s)
        self.assertEqual(len(rec["top5"]), 5)
        self.assertEqual([t["rank"] for t in rec["top5"]], [1, 2, 3, 4, 5])
        self.assertTrue(all("parts" in s and s["formula_ver"] == 1 for s in rec["scores"]))
        self.assertEqual(len(ledger.read("trend_ledger", self.tmp.name)), 1)

    def test_view_weight_dominates(self):
        top = self.run_()["top5"][0]["kw"]
        self.assertEqual(top, "생활꿀팁")  # 유튜브 조회 + 인스타 반응이 가장 큼

    def test_scope_filter(self):
        c = {x["kw"]: x for x in self.run_()["candidates"]}
        self.assertFalse(c["혜리"]["in_scope"])
        self.assertTrue(c["기초연금 인상"]["in_scope"])
        self.assertTrue(c["에너지 대책"]["in_scope"])  # 뉴스 제목에 seed(에너지바우처)
        self.assertIn("금칙", c["급등 종목 정부지원금"]["reason"])

    def test_no_indicator(self):
        rec = self.run_(gt=False, yt=False, ig=False)
        self.assertEqual(rec["status"], "no_indicator")
        self.assertEqual(rec["top5"], [])
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.alerts[0][0], "error")

    def test_cross_account_dedup(self):
        rec = self.run_(exclude=("생활꿀팁",))
        self.assertNotIn("생활꿀팁", [t["kw"] for t in rec["top5"]])

    # ---- 2026-11-12 리뷰 반영 시험 ----
    def custom(self, gt_items=(), videos=(), ig=None, **kw):
        fx = {"google_trends": lambda day: (list(gt_items), "gt.xml"),
              "youtube": lambda day, cats: (list(videos), ["yt.json"]),
              "ig": lambda today: (ig or {}, "ig.json" if ig else None)}
        return T.run(self.acc, self.banned, fetchers=fx, today=dt.date(2026, 11, 12), ledger_dir=self.tmp.name,
                     notify=lambda *a: self.alerts.append(a), **kw)

    def test_major1_empty_google_success_is_not_a_source(self):
        rec = self.custom()  # 세 수집기 모두 호출 성공이지만 0건
        self.assertEqual(rec["status"], "no_indicator")
        self.assertEqual(rec["top5"], [])
        self.assertEqual(len(self.alerts), 1)

    def test_major1_seed_without_evidence_excluded_no_evidence_status(self):
        rec = self.custom(videos=[{"title": "전혀 무관한 영상", "views": 500, "cat": "26"}])
        self.assertEqual(rec["status"], "no_evidence")
        self.assertEqual(rec["top5"], [])
        self.assertTrue(all(s["evidence"] is False for s in rec["scores"]))
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.alerts[0][0], "warn")

    def test_major1_only_evidence_candidates_in_top5(self):
        rec = self.custom(videos=[{"title": "국민연금 개편 핵심 정리", "views": 300000, "cat": "25"}])
        self.assertEqual(rec["status"], "ok_single_indicator")
        self.assertEqual([t["kw"] for t in rec["top5"]], ["국민연금"])
        self.assertEqual(self.alerts, [])

    def test_gate_stop_and_paused_stop_run_immediately(self):
        stop = os.path.join(self.tmp.name, "STOP")
        open(stop, "w").close()
        called = []
        fx = {"google_trends": lambda d: called.append(1) or ([], None)}
        rec = T.run(self.acc, self.banned, fetchers=fx, ledger_dir=self.tmp.name, stop_file=stop)
        self.assertEqual(rec["status"], "gated")
        self.assertEqual(called, [])
        self.assertEqual(ledger.read("trend_ledger", self.tmp.name), [])
        paused = dict(self.acc, paused=True)
        self.assertEqual(T.run(paused, self.banned, fetchers=fx, ledger_dir=self.tmp.name,
                               stop_file=os.path.join(self.tmp.name, "none"))["status"], "gated")

    def test_gate_false_skips_check(self):
        rec = self.custom(gate=False, videos=[{"title": "생활꿀팁 10가지", "views": 1000, "cat": "26"}])
        self.assertIn(rec["status"], ("ok", "ok_single_indicator"))

    def test_mask_secrets(self):
        e = "HTTPSConnectionPool: /v3/videos?part=x&key=AIzaSECRET123&alt=json and ?access_token=EAAB123abc)"
        m = T.mask_secrets(e)
        self.assertNotIn("AIzaSECRET123", m)
        self.assertNotIn("EAAB123abc", m)
        self.assertIn("key=***", m)
        self.assertIn("access_token=***", m)

    def test_error_strings_masked_in_ledger(self):
        def boom(day, cats):
            raise IOError("GET https://x/y?key=TOPSECRET failed")
        rec = T.run(self.acc, self.banned, fetchers={"google_trends": lambda d: ([], None), "youtube": boom,
                                                     "ig": lambda t: ({}, None)},
                    today=dt.date(2026, 11, 12), ledger_dir=self.tmp.name, notify=lambda *a: self.alerts.append(a))
        self.assertNotIn("TOPSECRET", json.dumps(rec, ensure_ascii=False))
        self.assertNotIn("TOPSECRET", json.dumps(self.alerts, ensure_ascii=False))

    def test_strip_paging(self):
        j = {"data": [1], "paging": {"next": "https://g?access_token=x"}}
        self.assertEqual(T.strip_paging(j), {"data": [1]})

    def test_empty_keyword_not_in_scope_or_candidates(self):
        self.assertFalse(T.in_scope("", [], ["정부지원금"])[0])
        self.assertFalse(T.in_scope("  ", ["정부지원금 신청"], ["정부지원금"])[0])
        items = [{"kw": "", "traffic": 500, "pubDate": "x", "news_titles": []},
                 {"kw": "   ", "traffic": 500, "pubDate": "x", "news_titles": []}]
        rec = self.custom(gt_items=items, videos=[{"title": "생활꿀팁 모음", "views": 5000, "cat": "26"}])
        self.assertFalse([c for c in rec["candidates"] if not c["kw"].strip()])

    def test_blank_banned_word_does_not_ban_everything(self):
        self.assertIsNone(T.is_banned("정부지원금", {"x": ["  ", ""]}))
        self.assertEqual(T.is_banned("수익 보장 안내", {"x": ["  ", "수익보장"]}), "x")

    def test_yt_token_path_from_config(self):
        self.assertTrue(C.YT_OAUTH_TOKEN_PATH.endswith("token_lighthouse.json"))
        import inspect
        self.assertNotIn("OneDrive", inspect.getsource(T._yt_headers_params))


if __name__ == "__main__":
    unittest.main()
