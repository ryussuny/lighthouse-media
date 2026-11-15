"""post-video-to-ig.py 길이 분기 시험 — 네트워크·실제 영상 없이 mock 만 사용."""
import importlib.util, os, sys, tempfile, unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "scripts", "post-video-to-ig.py")


def load():
    spec = importlib.util.spec_from_file_location("post_video_to_ig", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DurationBranch(unittest.TestCase):
    def run_main(self, dur):
        m = load()
        cap = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        cap.write("캡션")
        cap.close()
        self.addCleanup(os.unlink, cap.name)
        tokens = {"instagram": "T", "church_ig_id": "X", "church_page": "P"}
        with mock.patch.object(sys, "argv", ["x", "v.mp4", "--caption-file", cap.name, "--no-facebook"]), \
             mock.patch.object(m.json, "load", return_value=tokens), \
             mock.patch.object(m, "load_ledger", return_value={}), \
             mock.patch.object(m, "prepare", side_effect=lambda p: p), \
             mock.patch.object(m, "probe", return_value={"format": {"duration": str(dur)}}), \
             mock.patch.object(m, "upload_ig_reels", return_value=None) as imgur, \
             mock.patch.object(m, "upload_ig_reels_resumable", return_value=None) as resum, \
             mock.patch("builtins.open", mock.mock_open(read_data="캡션")):
            rc = m.main()
        return rc, imgur, resum

    def test_short_uses_imgur(self):
        rc, imgur, resum = self.run_main(59.9)
        self.assertEqual((imgur.call_count, resum.call_count), (1, 0))
        self.assertEqual(rc, 1)  # mock 이 None 반환 → 게시 실패 경로(기록 안 씀)

    def test_boundary_60_uses_imgur(self):
        _, imgur, resum = self.run_main(60.0)
        self.assertEqual((imgur.call_count, resum.call_count), (1, 0))

    def test_over_60_uses_resumable(self):
        _, imgur, resum = self.run_main(60.1)
        self.assertEqual((imgur.call_count, resum.call_count), (0, 1))

    def test_65_uses_resumable(self):
        _, imgur, resum = self.run_main(65.0)
        self.assertEqual((imgur.call_count, resum.call_count), (0, 1))


class ResumableFunction(unittest.TestCase):
    def setUp(self):
        self.m = load()
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"x" * 1000)
        f.close()
        self.path = f.name
        self.addCleanup(os.unlink, self.path)

    def resp(self, payload, status=200):
        r = mock.Mock()
        r.json.return_value = payload
        r.content = b"1"
        r.status_code = status
        return r

    def test_success_flow(self):
        with mock.patch.object(self.m.requests, "post", side_effect=[self.resp({"id": "C1"}), self.resp({"success": True})]) as post, \
             mock.patch.object(self.m, "_publish_container", return_value="M1") as pub:
            self.assertEqual(self.m.upload_ig_reels_resumable(self.path, "c", "T"), "M1")
        pub.assert_called_once_with("C1", "T")
        self.assertIn("upload_type", post.call_args_list[0].kwargs["data"])
        self.assertEqual(post.call_args_list[1].kwargs["headers"]["file_size"], "1000")

    def test_session_failure_returns_none(self):
        with mock.patch.object(self.m.requests, "post", return_value=self.resp({"error": "e"})), \
             mock.patch.object(self.m, "_publish_container") as pub:
            self.assertIsNone(self.m.upload_ig_reels_resumable(self.path, "c", "T"))
        pub.assert_not_called()

    def test_upload_failure_returns_none(self):
        with mock.patch.object(self.m.requests, "post", side_effect=[self.resp({"id": "C1"}), self.resp({"success": False}, 400)]), \
             mock.patch.object(self.m, "_publish_container") as pub:
            self.assertIsNone(self.m.upload_ig_reels_resumable(self.path, "c", "T"))
        pub.assert_not_called()


    def nonjson(self, text, status=502):
        r = mock.Mock()
        r.json.side_effect = ValueError("not json")
        r.content = text.encode()
        r.text = text
        r.status_code = status
        return r

    def run_capture(self, responses):
        import contextlib, io
        buf = io.StringIO()
        with mock.patch.object(self.m.requests, "post", side_effect=responses), \
             mock.patch.object(self.m, "_publish_container") as pub, \
             contextlib.redirect_stdout(buf):
            result = self.m.upload_ig_reels_resumable(self.path, "c", "SECRET_TOKEN_XYZ")
        pub.assert_not_called()
        return result, buf.getvalue()

    def test_session_nonjson_returns_none_without_token(self):
        result, out = self.run_capture([self.nonjson("<html>502 Bad Gateway token=SECRET_TOKEN_XYZ</html>")])
        self.assertIsNone(result)
        self.assertIn("502", out)
        self.assertNotIn("SECRET_TOKEN_XYZ", out)

    def test_upload_nonjson_returns_none_without_token(self):
        result, out = self.run_capture([self.resp({"id": "C1"}), self.nonjson("<html>error SECRET_TOKEN_XYZ</html>", 500)])
        self.assertIsNone(result)
        self.assertIn("500", out)
        self.assertNotIn("SECRET_TOKEN_XYZ", out)


if __name__ == "__main__":
    unittest.main()
