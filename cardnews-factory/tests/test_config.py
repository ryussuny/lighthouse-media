# -*- coding: utf-8 -*-
"""T-02 수용 기준: 설정 검증 통과 + STOP·paused 읽기(AC-9). 실행: py -m unittest discover -s tests"""
import copy
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C  # noqa: E402


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.acc = C.load_account("test")

    def test_all_configs_valid(self):
        rep = C.validate_all()
        self.assertEqual({k: v for k, v in rep.items() if v}, {})

    def test_bad_account_rejected(self):
        bad = copy.deepcopy(self.acc)
        bad["daily_post_cap"] = 5
        bad["post_times"] = ["25:00"]
        bad["access_token"] = "x"
        del bad["topic"]
        errs = C.validate_account(bad)
        self.assertTrue(any("topic" in e for e in errs))
        bad["topic"] = "t"
        errs = C.validate_account(bad)
        self.assertTrue(any("daily_post_cap" in e for e in errs))
        self.assertTrue(any("post_times" in e for e in errs))
        self.assertTrue(any("access_token" in e for e in errs))

    def test_real_account_needs_token_ref(self):
        real = dict(self.acc, is_virtual=False, token_ref=None)
        self.assertTrue(any("token_ref" in e for e in C.validate_account(real)))

    def test_run_gate_ok(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(C.run_gate(self.acc, os.path.join(d, "STOP")), (True, "ok"))

    def test_stop_file_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            stop = os.path.join(d, "STOP")
            open(stop, "w").close()
            ok, why = C.run_gate(self.acc, stop)
            self.assertFalse(ok)
            self.assertIn("STOP", why)

    def test_paused_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            ok, why = C.run_gate(dict(self.acc, paused=True), os.path.join(d, "STOP"))
            self.assertFalse(ok)
            self.assertIn("paused", why)

    def test_official_domain(self):
        dom = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
        self.assertTrue(C.is_official_url("https://www.nhis.or.kr/x", dom))
        self.assertTrue(C.is_official_url("https://www.mohw.go.kr/a", dom))
        self.assertFalse(C.is_official_url("https://blog.naver.com/a", dom))
        self.assertFalse(C.is_official_url("https://go.kr.evil.com/a", dom))
        # v2: .or.kr·.ac.kr·.re.kr 접미사는 공식 아님(사설 단체·대학) — 명시 exact 만
        self.assertFalse(C.is_official_url("https://random-assoc.or.kr/a", dom))
        self.assertFalse(C.is_official_url("https://www.some-univ.ac.kr/a", dom))
        self.assertFalse(C.is_official_url("https://lab.re.kr/a", dom))
        self.assertTrue(C.is_official_url("https://www.nps.or.kr/a", dom))

    # ---- 2026-11-12 리뷰 반영: 교회 계열 차단·token_ref 허용 목록·공백 금칙어 ----
    def test_church_accounts_blocked(self):
        cases = {"account_id": "dongsan_church", "topic": "동산교회 말씀 카드뉴스", "token_ref": "token_dongsan",
                 "handle": "garden___church", "brand": {"font": "x", "logo_path": "교회로고.png"}}
        for k, v in cases.items():
            errs = C.validate_account(dict(self.acc, **{k: v}))
            self.assertTrue(any("교회" in e and k in e for e in errs), (k, errs))
        errs = C.validate_account(dict(self.acc, account_id="church", topic="t"))
        self.assertTrue(any("account_id" in e for e in errs))
        self.assertTrue(any("CHURCH" not in e and "교회" in e for e in errs))
        self.assertTrue(any("교회" in e for e in C.validate_account(dict(self.acc, is_virtual=False, token_ref="Token_Dongsan"))))

    def test_token_ref_allowlist(self):
        ok = dict(self.acc, is_virtual=False, token_ref="instagram")
        self.assertEqual(C.validate_account(ok), [])
        bad = dict(self.acc, is_virtual=False, token_ref="some_other_token")
        self.assertTrue(any("허용 목록" in e for e in C.validate_account(bad)))

    def test_normal_account_not_blocked(self):
        self.assertEqual(C.validate_account(self.acc), [])

    def test_blank_banned_word_rejected(self):
        b = {"categories": {k: ["x"] for k in ("medical_claim", "investment_solicit", "political_agitation", "adult", "copyright_suspect")}}
        self.assertEqual(C.validate_banned(b), [])
        b["categories"]["adult"] = ["x", "   "]
        self.assertTrue(any("adult" in e for e in C.validate_banned(b)))

    def test_yt_token_path_configurable(self):
        self.assertTrue(C.YT_OAUTH_TOKEN_PATH)

    def test_new_accounts_valid_and_virtual(self):
        for a in ("travel", "invest", "trend"):
            acc = C.load_account(a)
            self.assertTrue(acc["is_virtual"], a)
            self.assertIsNone(acc["token_ref"], a)
            self.assertEqual(acc["daily_post_cap"], 1, a)
        inv = C.load_account("invest")
        self.assertEqual(inv["required_disclaimer"], "투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다.")
        for w in ("매수 추천", "목표가", "수익률 보장", "텐배거", "코인 추천", "에어드랍", "종목 추천", "리딩"):
            self.assertIn(w, inv["banned_topics_extra"], w)
        self.assertNotIn("required_disclaimer", C.load_account("travel"))

    def test_required_disclaimer_must_be_nonempty_string(self):
        acc = dict(C.load_account("invest"), required_disclaimer=" ")
        self.assertTrue(any("required_disclaimer" in e for e in C.validate_account(acc)))

    def test_metered_flag(self):
        env = {k: v for k, v in os.environ.items() if k != "CARDNEWS_ALLOW_METERED_API"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(C.metered_allowed())
            os.environ["CARDNEWS_ALLOW_METERED_API"] = "1"
            self.assertTrue(C.metered_allowed())

    def test_invest_account_requires_disclaimer(self):
        acc = dict(C.load_account("invest"))
        del acc["required_disclaimer"]
        self.assertTrue(any("required_disclaimer" in e for e in C.validate_account(acc)))
        acc2 = dict(C.load_account("travel"), type="invest")
        self.assertTrue(any("required_disclaimer" in e for e in C.validate_account(acc2)))
        self.assertEqual(C.validate_account(C.load_account("travel")), [])


if __name__ == "__main__":
    unittest.main()
