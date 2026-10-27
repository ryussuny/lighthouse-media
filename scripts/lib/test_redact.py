"""redact.py 시험 — py -m unittest scripts/lib/test_redact.py (가짜 값만 사용)"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redact import redact  # noqa: E402

A40 = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0"


class Existing(unittest.TestCase):
    def test_query_access_token(self):
        self.assertEqual(redact("GET /me?access_token=" + A40 + "&x=1"), "GET /me?access_token=***&x=1")

    def test_query_other_keys(self):
        for k in ("fb_exchange_token", "client_secret", "refresh_token"):
            self.assertEqual(redact(k + "=abc123 ok"), k + "=*** ok")

    def test_json_double_quote(self):
        self.assertEqual(redact('{"access_token": "' + A40 + '"}'), '{"access_token": "***"}')

    def test_dict_single_quote(self):
        self.assertEqual(redact("{'refresh_token':'secretvalue'}"), "{'refresh_token':'***'}")

    def test_meta_prefixes(self):
        for p in ("EAA", "IGA", "IGQ"):
            self.assertEqual(redact("tok " + p + A40 + " end"), "tok *** end")

    def test_plain_text_unchanged(self):
        self.assertEqual(redact("업로드 완료 3가지 EAA 짧음"), "업로드 완료 3가지 EAA 짧음")


class Google(unittest.TestCase):
    ACCESS = "ya29.a0AfH6SMBx_fake-Token0123456789abcdefGHIJ"
    REFRESH = "1//0gFakeRefreshToken_0123456789-abcdefXYZ"

    def test_access_token(self):
        self.assertEqual(redact("Bearer " + self.ACCESS), "Bearer ya29.***")

    def test_refresh_token(self):
        self.assertEqual(redact("refresh " + self.REFRESH + " done"), "refresh 1//*** done")

    def test_mixed_line_only_tokens_masked(self):
        t = "비율 1//2 와 ya29 단어, 토큰 " + self.ACCESS + " / " + self.REFRESH + " 끝"
        self.assertEqual(redact(t), "비율 1//2 와 ya29 단어, 토큰 ya29.*** / 1//*** 끝")

    def test_negative_plain(self):
        for t in ("1//2 비율", "ya29", "ya29.short", "1//short", "비율은 1//2 입니다", "see ya29 docs"):
            self.assertEqual(redact(t), t)

    def test_no_match_inside_path_or_word(self):
        for t in ("http://x/1//" + "a" * 30, "xya29." + "b" * 30):
            self.assertEqual(redact(t), t)

    def test_after_slash_access(self):
        self.assertEqual(redact("https://x/" + self.ACCESS), "https://x/ya29.***")

    def test_after_slash_refresh(self):
        self.assertEqual(redact("...?t=/" + self.REFRESH + "&a=1"), "...?t=/1//***&a=1")
        self.assertEqual(redact("https://x/" + self.REFRESH), "https://x/1//***")

    def test_refresh_must_start_1_slash_slash_0(self):
        for t in ("a 1//2 비율", "a 1//" + "b" * 30, "https://x/1//" + "9" * 30, "1//" + "z" * 25):
            self.assertEqual(redact(t), t)

    def test_json_form_still_masked(self):
        self.assertEqual(redact('{"refresh_token": "' + self.REFRESH + '"}'), '{"refresh_token": "***"}')


if __name__ == "__main__":
    unittest.main()
