"""refresh-ig-token.py inspect_token() 단위시험 — requests.get 을 가짜로 바꾼다(실제 Graph 호출 없음).
실행: py scripts/test_refresh_ig_token.py"""
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location("rit", os.path.join(HERE, "refresh-ig-token.py"))
rit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rit)

FAKE = "FAKEtok_UNITTEST_0123"


class _Resp:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def json(self):
        return self._body


class InspectTokenTest(unittest.TestCase):
    def setUp(self):
        self._orig = rit.requests.get

    def tearDown(self):
        rit.requests.get = self._orig

    def _fake(self, resp=None, exc=None):
        def get(*a, **k):
            if exc:
                raise exc
            return resp
        rit.requests.get = get

    def test_code_190_is_invalid_not_unknown(self):
        long_msg = "Error validating access token: Session has expired on Monday. " + "x" * 100
        self._fake(_Resp({"error": {"message": long_msg, "type": "OAuthException", "code": 190}}, 400))
        r = rit.inspect_token(FAKE)
        self.assertTrue(r["ok"])
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], long_msg[:80])

    def test_valid_token(self):
        self._fake(_Resp({"data": {"is_valid": True, "expires_at": 0, "data_access_expires_at": 0}}))
        r = rit.inspect_token(FAKE)
        self.assertTrue(r["ok"])
        self.assertTrue(r["valid"])

    def test_network_exception_is_unknown(self):
        self._fake(exc=rit.requests.exceptions.ConnectionError(f"url ?access_token={FAKE}"))
        r = rit.inspect_token(FAKE)
        self.assertFalse(r["ok"])
        self.assertNotIn(FAKE, r["reason"])

    def test_other_error_code_is_unknown(self):
        self._fake(_Resp({"error": {"message": "(#4) rate limit", "code": 4}}, 400))
        r = rit.inspect_token(FAKE)
        self.assertFalse(r["ok"])
        self.assertIn("HTTP 400", r["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
