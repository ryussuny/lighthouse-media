# -*- coding: utf-8 -*-
"""T-02 수용 기준: 설정 검증 통과 + STOP·paused 읽기(AC-9). 실행: py -m unittest discover -s tests"""
import copy
import os
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
