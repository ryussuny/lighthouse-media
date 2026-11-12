# -*- coding: utf-8 -*-
"""T-03 수용 기준: AC-2(지표원 2개 이상 원값·시각·점수·1~5위 원장 기록) + 지표 0개 정상 종료."""
import datetime as dt
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


if __name__ == "__main__":
    unittest.main()
