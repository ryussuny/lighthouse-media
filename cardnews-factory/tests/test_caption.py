# -*- coding: utf-8 -*-
"""T-08 수용 기준: AC-7 — 캡션에 출처 줄·"AI로 제작"·해시태그 상한 준수 + 과장·낚시 표현 보류."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import caption as CAP  # noqa: E402

SRC = [{"org": "보건복지부", "url": "https://www.mohw.go.kr/a"}, {"org": "국민연금공단", "url": "https://www.nps.or.kr/b"}]


def draft(**kw):
    cards = [{"title": f"제목{i}", "body": f"본문{i}"} for i in range(5)]
    d = {"cards": cards, "sources": SRC, "hashtags": ["기초연금", "생활정보"]}
    d["caption"] = CAP.build_caption("기초연금 신청 방법 안내", SRC, d["hashtags"])
    d.update(kw)
    return d


class CaptionTest(unittest.TestCase):
    def test_build_passes_ac7(self):
        d = draft()
        self.assertEqual(CAP.check_caption(d), [])
        lines = d["caption"].splitlines()
        self.assertEqual(lines[-1], "AI로 제작")
        self.assertIn("출처: 보건복지부 https://www.mohw.go.kr/a", d["caption"])
        self.assertIn("출처: 국민연금공단 https://www.nps.or.kr/b", d["caption"])

    def test_missing_ai_label(self):
        d = draft(caption="본문\n\n" + "\n".join(CAP.source_lines(SRC)) + "\n\n#a")
        self.assertTrue(any("AI로 제작" in r for r in CAP.check_caption(d)))

    def test_ai_label_not_last(self):
        d = draft(caption=draft()["caption"] + "\n더보기")
        self.assertTrue(any("AI로 제작" in r for r in CAP.check_caption(d)))

    def test_missing_source_line(self):
        d = draft(caption="본문\n\n#a\n\nAI로 제작")
        self.assertTrue(any("출처 줄 없음" in r for r in CAP.check_caption(d)))

    def test_no_sources(self):
        self.assertTrue(any("출처 목록 없음" in r for r in CAP.check_caption(draft(sources=[]))))

    def test_hashtag_cap(self):
        tags = [f"태그{i}" for i in range(CAP.MAX_HASHTAGS + 1)]
        d = draft(hashtags=tags)
        d["caption"] = CAP.build_caption("본문", SRC, tags)
        rs = CAP.check_caption(d)
        self.assertTrue(any("해시태그" in r for r in rs))
        tags = tags[:CAP.MAX_HASHTAGS]
        d = draft(hashtags=tags)
        d["caption"] = CAP.build_caption("본문", SRC, tags)
        self.assertEqual(CAP.check_caption(d), [])

    def test_length_cap(self):
        d = draft()
        d["caption"] = CAP.build_caption("가" * 2200, SRC, ["a"])
        self.assertTrue(any("길이" in r for r in CAP.check_caption(d)))

    def test_exactly_2200_ok(self):
        d = draft()
        base = len(CAP.build_caption("", SRC, d["hashtags"]))
        d["caption"] = CAP.build_caption("가" * (2200 - base - 2), SRC, d["hashtags"])
        self.assertLessEqual(len(d["caption"]), 2200)
        self.assertEqual(CAP.check_caption(d), [])

    def test_hype_words(self):
        for w in ("충격", "무조건", "100%"):
            d = draft()
            d["caption"] = CAP.build_caption(f"이것은 {w} 놓치지 마세요", SRC, d["hashtags"])
            self.assertTrue(any("과장" in r and w in r for r in CAP.check_caption(d)), w)

    def test_hype_in_card_text(self):
        d = draft()
        d["cards"][2]["title"] = "충 격 공개"
        self.assertTrue(any("과장" in r for r in CAP.check_caption(d)))

    def test_empty_caption(self):
        self.assertEqual(CAP.check_caption(draft(caption="")), ["캡션 비어 있음"])

    def test_display_sources_portal_label_and_order(self):
        recs = [{"url": "https://www.korea.kr/briefing/a", "org": "korea.kr", "org_known": False},
                {"url": "https://www.korea.kr/news/b", "org": "보건복지부", "org_known": True},
                {"url": "https://www.example.go.kr/c", "org": "example.go.kr"},            # org_known 없음 + 호스트명
                {"url": "https://www.moel.go.kr/d", "org": "고용노동부"}]                   # org_known 없음 + 기관명
        out = CAP.display_sources(recs)
        self.assertEqual([x["org"] for x in out],
                         ["보건복지부", "고용노동부", "정책브리핑(korea.kr)", "기관 미확인(example.go.kr)"])
        self.assertEqual(out[0]["url"], "https://www.korea.kr/news/b")          # 확인된 기관이 먼저

    def test_display_sources_matches_caption_lines_for_verify_exemption(self):
        from cardnews import verify
        recs = [{"url": "https://www.korea.kr/briefing/a", "org": "korea.kr", "org_known": False},
                {"url": "https://www.korea.kr/news/b", "org": "보건복지부", "org_known": True}]
        srcs = CAP.display_sources(recs)
        d = {"cards": [{"title": "t", "body": "b"}] * 5, "hashtags": [], "sources": srcs,
             "caption": CAP.build_caption("안내 문장입니다", srcs, [])}
        self.assertEqual(CAP.check_caption(d), [])
        lines = [t for w, t in verify.text_fields(d)] if hasattr(verify, "text_fields") else []
        for line in CAP.source_lines(srcs):
            self.assertNotIn(line, lines)                 # 출처 줄은 G2 검사 대상에서 면제(정확 일치)


if __name__ == "__main__":
    unittest.main()
