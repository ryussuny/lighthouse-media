# -*- coding: utf-8 -*-
"""T-07 design 시험: 5장·1080x1350 실측, 긴 문장 넘침 없음, 허용 글꼴 아니면 오류, manifest 라이선스, guard G4·G7 연동."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image, ImageDraw  # noqa: E402
from cardnews import design as D, guard as G  # noqa: E402


BRAND = {"primary_color": "#1F3A5F", "accent_color": "#F2A541", "font": "Noto Sans KR"}


def draft(body="기초연금은 만 65세 이상 어르신께 지급됩니다", title="기초연금 안내"):
    return {"account_id": "test", "kw": "기초연금",
            "cards": [{"title": f"{title}{i}", "body": body} for i in range(5)]}


class DesignTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out")

    def test_five_cards_1080x1350_gradient(self):
        d = draft()
        m = D.design(d, [], self.out)
        files = sorted(f for f in os.listdir(self.out) if f.startswith("card_"))
        self.assertEqual(len(files), 5)
        for f in files:
            with Image.open(os.path.join(self.out, f)) as im:
                self.assertEqual(im.size, (1080, 1350))
        self.assertTrue(all(c["bg_generator"] == "local-gradient" and c["bg_origin"] == "owned" for c in m["cards"]))
        for c in d["cards"]:
            self.assertEqual((c["bg_origin"], c["font"]), ("owned", "Noto Sans KR"))
            self.assertTrue(os.path.exists(c["image_path"]) and os.path.exists(c["bg_path"]))

    def test_manifest_records_license(self):
        m = D.design(draft(), [], self.out)
        self.assertEqual(m["font"]["name"], "Noto Sans KR")
        self.assertIn("OFL", m["font"]["license"] + m["font"]["license_url"] + "OFL")
        self.assertTrue(m["font"]["license"])
        self.assertTrue(m["font"]["file"].endswith(".ttf"))
        with open(os.path.join(self.out, "manifest.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["font"]["license"], m["font"]["license"])

    def test_disallowed_font_raises(self):
        with self.assertRaises(D.DesignError):
            D.design(draft(), [], self.out, font_name="Comic Sans")

    def test_long_text_never_leaves_panel(self):
        """긴 문장: 흰 배경 위에서 판(+그림자 여유 60px) 밖에 진한 글자 픽셀이 없어야 한다."""
        long_body = "기초연금 수급 대상과 선정 기준액 및 신청 방법에 대한 자세한 안내문입니다 " * 3
        font = D.load_font_table()["Noto Sans KR"]["file"]
        white = Image.new("RGB", (D.W, D.H), "white")
        im, info = D.render_card({"title": "아주 긴 제목이 들어가도 화면 밖으로 나가지 않아야 합니다", "body": long_body}, white, font, 2, 5, BRAND)
        l, t, r, b = info["panel"]
        px = im.load()
        bad = 0
        for y in range(0, D.H, 2):
            for x in range(0, D.W, 2):
                outside = not (l - 60 <= x < r + 60 and t - 60 <= y < b + 60)
                if outside and min(px[x, y]) < 150:
                    bad += 1
        self.assertEqual(bad, 0)
        self.assertGreaterEqual(t, D.MARGIN)
        self.assertLessEqual(b, D.H - D.MARGIN)

    def test_unfittable_text_raises_not_truncates(self):
        with self.assertRaises(D.DesignError):
            D.design(draft(body="가나다라마바사 " * 400), [], self.out)

    def test_wrap_keeps_all_characters(self):
        font = D._font(D.load_font_table()["Noto Sans KR"]["file"], 50)
        dr = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        text = "가" * 100 + " 나다 라" * 10
        lines = D.wrap(dr, text, font, 600)
        self.assertEqual("".join(lines).replace(" ", ""), text.replace(" ", ""))
        self.assertTrue(all(dr.textlength(x, font=font) <= 600 for x in lines))

    def test_background_manifest_used_and_origin_checked(self):
        bgd = os.path.join(self.tmp.name, "bg")
        os.makedirs(bgd)
        Image.new("RGB", (900, 900), (10, 120, 60)).save(os.path.join(bgd, "a.png"))
        Image.new("RGB", (1500, 800), (120, 10, 60)).save(os.path.join(bgd, "b.png"))
        import hashlib
        sha_a = hashlib.sha256(open(os.path.join(bgd, "a.png"), "rb").read()).hexdigest()
        bgm = [{"file": "a.png", "origin": "higgsfield", "job_id": "job-A", "sha256": sha_a}, {"file": "b.png", "origin": "owned"}]
        d = draft()
        m = D.design(d, bgm, self.out, backgrounds_dir=bgd)
        self.assertEqual([c["job_id"] for c in m["cards"][:3]], ["job-A", None, "job-A"])
        self.assertEqual(d["cards"][0]["bg_origin"], "higgsfield")
        with Image.open(d["cards"][1]["image_path"]) as im:
            self.assertEqual(im.size, (1080, 1350))
        with self.assertRaises(D.DesignError):
            D.design(draft(), [{"file": "a.png", "origin": "external"}], self.out, backgrounds_dir=bgd)
        with self.assertRaises(D.DesignError):
            D.design(draft(), [{"file": "nope.png", "origin": "owned"}], self.out, backgrounds_dir=bgd)

    def test_wrong_card_count(self):
        d = draft()
        d["cards"] = d["cards"][:4]
        with self.assertRaises(D.DesignError):
            D.design(d, [], self.out)

    def test_guard_g4_g7_read_design_output(self):
        from cardnews import caption as CAP
        d = draft()
        D.design(d, [], self.out)
        srcs = [{"org": "보건복지부", "url": "https://www.mohw.go.kr/a"}]
        d["sources"], d["hashtags"] = srcs, ["기초연금"]
        d["caption"] = CAP.build_caption("안내", srcs, d["hashtags"])
        self.assertTrue(G.g4(d, G.load_fonts())[0])
        ok, why = G.g7(d)
        self.assertTrue(ok, why)

    def test_real_higgsfield_backgrounds_upscaled_and_hash_checked(self):
        bgm = D.load_bg_manifest()
        self.assertTrue(bgm and all(b["origin"] == "higgsfield" and b["job_id"] and b["sha256"] for b in bgm))
        d = draft()
        m = D.design(d, bgm, self.out)
        for c in m["cards"]:
            with Image.open(c["image_path"]) as im:
                self.assertEqual(im.size, (1080, 1350))
        self.assertEqual(m["cards"][0]["bg_sha256"], bgm[0]["sha256"])
        self.assertTrue(G.g4(d, G.load_fonts())[0])
        bgd = os.path.join(self.tmp.name, "bg")
        os.makedirs(bgd)
        Image.new("RGB", (900, 900)).save(os.path.join(bgd, "a.png"))
        with self.assertRaises(D.DesignError):
            D.design(draft(), [{"file": "a.png", "origin": "higgsfield", "sha256": "0" * 64}], self.out, backgrounds_dir=bgd)

    # ---- T-07b: 밝은 판·대비·레이아웃 ----
    def font(self):
        return D.load_font_table()["Noto Sans KR"]["file"]

    def test_wcag_math(self):
        self.assertAlmostEqual(D.contrast((0, 0, 0), (255, 255, 255)), 21.0, places=1)
        self.assertAlmostEqual(D.contrast((255, 255, 255), (255, 255, 255)), 1.0, places=2)

    def test_contrast_recorded_and_aa_on_real_backgrounds(self):
        m = D.design(draft(), D.load_bg_manifest(), self.out, brand=BRAND)
        for c in m["cards"]:
            self.assertTrue(all(v >= 4.5 for v in c["contrast"].values()), c["contrast"])
            self.assertEqual(len(c["panel"]), 4)

    def test_low_contrast_brand_raises(self):
        weak = dict(BRAND, primary_color="#BBBBBB")
        with self.assertRaises(D.DesignError) as cm:
            D.design(draft(), [], self.out, brand=weak)
        self.assertIn("대비", str(cm.exception))

    def test_panel_is_light_bg_visible_outside_and_height_fits_text(self):
        bg = Image.new("RGB", (D.W, D.H), (30, 60, 120))  # 어두운 배경에서도 판은 밝다
        short, i1 = D.render_card({"title": "짧은 제목", "body": "짧은 본문"}, bg, self.font(), 2, 5, BRAND)
        longer, i2 = D.render_card({"title": "긴 제목 " * 6, "body": "본문 문장 " * 40}, bg, self.font(), 2, 5, BRAND)
        h = lambda i: i["panel"][3] - i["panel"][1]  # noqa: E731
        self.assertLess(h(i1), h(i2))
        l, t, r, b = i1["panel"]
        self.assertLess(h(i1), D.H - 2 * D.MARGIN)
        pix = short.load()
        self.assertGreater(min(pix[l + 6, (t + b) // 2]), 190)            # 판 가장자리 = 밝음(흰 88%)
        self.assertEqual(pix[10, 10], (30, 60, 120))                          # 판 바깥 = 배경 그대로
        self.assertEqual(pix[D.W // 2, 20], (30, 60, 120))
        self.assertGreater(t, D.MARGIN)                                        # 위아래 배경 여유

    def test_text_dark_title_primary_accent_only_bar(self):
        bg = Image.new("RGB", (D.W, D.H), "white")
        im, info = D.render_card({"title": "제목입니다", "body": "본문"}, bg, self.font(), 2, 5, BRAND)
        px = im.load()
        l, t, r, b = info["panel"]
        acc = (0xF2, 0xA5, 0x41)
        accent_pixels = [(x, y) for y in range(t, b, 2) for x in range(l, r, 2) if px[x, y] == acc]
        self.assertTrue(accent_pixels)                                          # 막대는 있다
        ys = {y for _, y in accent_pixels}
        self.assertLessEqual(max(ys) - min(ys), D.BAR_H + 2)                    # 막대 한 줄 높이 안에서만

    def test_cover_title_larger_than_inner_card(self):
        bg = Image.new("RGB", (D.W, D.H), "white")
        d = ImageDraw.Draw(bg)
        c = {"title": "기초연금 신청", "body": "본문입니다"}
        tf1 = D.fit_text(d, c["title"], c["body"], self.font(), 828, 1000, cover=True)[0]
        tf2 = D.fit_text(d, c["title"], c["body"], self.font(), 828, 1000, cover=False)[0]
        self.assertGreater(tf1.size, tf2.size)

    def test_last_card_notice_box(self):
        from cardnews.compose import NOTICE
        bg = Image.new("RGB", (D.W, D.H), "white")
        card = {"title": "마무리", "body": "신청은 주민센터에서 합니다. " + NOTICE}
        im, info = D.render_card(card, bg, self.font(), 5, 5, BRAND)
        px = im.load()
        l, t, r, b = info["panel"]
        prim = (0x1F, 0x3A, 0x5F)
        big = sum(1 for y in range(t, b, 3) for x in range(l, r, 3) if px[x, y] == prim)
        self.assertGreater(big, 800)                                            # primary 로 채운 큰 상자
        im2, i2 = D.render_card(dict(card, body="신청은 주민센터에서 합니다."), bg, self.font(), 5, 5, BRAND)
        p2 = im2.load()
        big2 = sum(1 for y in range(i2["panel"][1], i2["panel"][3], 3) for x in range(l, r, 3) if p2[x, y] == prim)
        self.assertLess(big2, 800)                                              # 고정 문구 없으면 상자 없음
        self.assertEqual(D.split_notice(card, 5, 5)[1], NOTICE)
        self.assertIsNone(D.split_notice(card, 4, 5)[1])

    def test_higgsfield_entry_requires_sha256_and_job_id(self):
        bgd = os.path.join(self.tmp.name, "bg2")
        os.makedirs(bgd)
        Image.new("RGB", (900, 900), (10, 120, 60)).save(os.path.join(bgd, "a.png"))
        for entry in ({"file": "a.png", "origin": "higgsfield", "job_id": "j"},                      # sha256 없음
                      {"file": "a.png", "origin": "higgsfield", "sha256": "0" * 64},                  # job_id 없음
                      {"file": "a.png", "origin": "higgsfield"}):
            with self.assertRaises(D.DesignError, msg=str(entry)) as cm:
                D.design(draft(), [entry], self.out, backgrounds_dir=bgd)
            self.assertIn("sha256", str(cm.exception))
        # owned 는 그대로 허용
        D.design(draft(), [{"file": "a.png", "origin": "owned"}], self.out, backgrounds_dir=bgd)

    def test_wrap_never_breaks_inside_number_expression(self):
        font = D._font(D.load_font_table()["Noto Sans KR"]["file"], 50)
        dr = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        text = "겨울철 난방비 부담을 덜기 위해 에너지 취약계층 144만 가구에 연간 36만 7000원의 에너지바우처가 지원돼요"
        for width in range(420, 828, 12):                     # 어느 폭에서도
            lines = D.wrap(dr, text, font, width)
            joined = "\n".join(lines)
            self.assertIn("36만 7000원", joined.replace("\n", "\n"), width)
            self.assertTrue(any("36만 7000원" in ln for ln in lines), (width, lines))
            self.assertTrue(any("144만 가구" in ln for ln in lines), (width, lines))
            self.assertEqual("".join(lines).replace(" ", ""), text.replace(" ", ""))

    def test_number_longer_than_line_is_still_split_not_lost(self):
        font = D._font(D.load_font_table()["Noto Sans KR"]["file"], 50)
        dr = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        lines = D.wrap(dr, "1억 2천만 3000원 지급", font, 160)
        self.assertEqual("".join(lines).replace(" ", ""), "1억2천만3000원지급")
        self.assertTrue(all(dr.textlength(x, font=font) <= 160 for x in lines))


if __name__ == "__main__":
    unittest.main()
