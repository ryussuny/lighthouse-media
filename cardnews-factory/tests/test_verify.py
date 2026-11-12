# -*- coding: utf-8 -*-
"""T-05 수용 기준: AC-4(숫자 틀리면 보류) · AC-6(출처 1곳이면 보류) + 값 불일치·sha256 변조."""
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import ledger, verify as V  # noqa: E402

DOMAINS = {"exact": ["korea.kr", "nps.or.kr"], "suffixes": [".go.kr"]}
SRC_A = "<html><body><p>2026년 기초연금 선정기준액은 단독가구 월 228만원이며, 기준연금액은 월 34만원입니다.</p></body></html>"
SRC_B = "<html><body>보건복지부 발표: 기준연금액 월 34만원, 신청은 만 65세부터.</body></html>"


class TestVerify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def src(self, name, html, url, org):
        p = os.path.join(self.d, name)
        b = html.encode("utf-8")
        with open(p, "wb") as f:
            f.write(b)
        return {"url": url, "org": org, "sha256": hashlib.sha256(b).hexdigest(), "saved_path": p}

    def two(self, b_html=SRC_B):
        return [self.src("a.html", SRC_A, "https://www.korea.kr/news/1", "국민연금공단"),
                self.src("b.html", b_html, "https://www.mohw.go.kr/x", "보건복지부")]

    def draft(self, body):
        return {"account_id": "test", "kw": "기초연금",
                "cards": [{"title": "2026년 기초연금", "body": body}] + [{"title": "안내", "body": "신청 전 기관 확인"}] * 4}

    def run_(self, draft, sources):
        return V.run(draft, sources, ledger_dir=self.d, domains=DOMAINS)

    def test_pass(self):
        r = self.run_(self.draft("기준연금액 월 34만원, 만 65세부터 신청"), self.two())
        self.assertTrue(r["pass"], r)
        rows = ledger.read("check_ledger", self.d)
        self.assertEqual([x["gate"] for x in rows], ["G1", "G2"])

    def test_ac4_wrong_number_held(self):
        r = self.run_(self.draft("기준연금액 월 35만원"), self.two())
        self.assertFalse(r["pass"])
        self.assertIn("35만원", r["G2"][1])

    def test_ac6_single_source_held(self):
        r = self.run_(self.draft("기준연금액 월 34만원"), self.two()[:1])
        self.assertFalse(r["pass"])
        self.assertFalse(r["G1"][0])

    def test_same_org_twice_held(self):
        s = self.two()
        s[1]["org"] = "국민연금공단"
        self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0])

    def test_value_conflict_between_sources(self):
        b = "<html><body>보건복지부: 기준연금액 월 33만원, 만 65세부터.</body></html>"
        r = self.run_(self.draft("기준연금액 월 34만원"), self.two(b))
        self.assertFalse(r["pass"])
        self.assertIn("불일치", r["G2"][1])

    def test_tampered_file_rejected(self):
        s = self.two()
        with open(s[0]["saved_path"], "ab") as f:
            f.write(b"x")
        r = self.run_(self.draft("월 34만원"), s)
        self.assertFalse(r["G1"][0])
        self.assertIn("sha256", r["G1"][1])

    def test_unofficial_domain_dropped(self):
        s = self.two()
        s[1]["url"] = "https://blog.example.com/p"
        self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0])

    # ---- 2026-11-12 리뷰 반영(경계·범위·한글 수사·기관 미상) ----
    def test_boundary_no_partial_match(self):
        b = "<html><body>보건복지부: 기준연금액 월 34만원, 총 2,100만원 예산.</body></html>"
        r = self.run_(self.draft("예산은 100만원 규모"), self.two(b))
        self.assertFalse(r["pass"])
        self.assertIn("100만원", r["G2"][1])

    def test_unitless_short_number_fails(self):
        r = self.run_(self.draft("신청 방법은 5 단계로 나뉩니다 5"), self.two())
        self.assertFalse(r["pass"])
        self.assertIn("단위 없는", r["G2"][1])

    def test_unit_gaji_must_match_exactly(self):
        r = self.run_(self.draft("신청 방법 5가지"), self.two())  # 원문에 '5가지' 없음('65세'의 5 는 안 됨)
        self.assertFalse(r["pass"])

    def test_caption_numbers_checked(self):
        d = self.draft("기준연금액 월 34만원")
        d["caption"] = "월 99만원 지급! 신청자 1,234만명\n기준일: 2026-11-12\n출처: 보건복지부 https://www.mohw.go.kr/x\nAI로 제작"
        r = self.run_(d, self.two())
        self.assertFalse(r["pass"])
        self.assertIn("99만원", r["G2"][1])
        self.assertNotIn("2026-11-12", r["G2"][1])  # 코드가 넣는 기준일 줄은 제외

    def test_extra_card_fields_checked(self):
        d = self.draft("기준연금액 월 34만원")
        d["cards"][1] = {"title": "안내", "body": "확인", "footer": "최대 77만원"}
        self.assertFalse(self.run_(d, self.two())["pass"])

    def test_korean_numerals_fail(self):
        for body in ("기준연금액 월 오십만원", "신청 방법 세 가지", "수십만 명이 받습니다"):
            r = self.run_(self.draft(body), self.two())
            self.assertFalse(r["pass"], body)
            self.assertIn("한글 수사", r["G2"][1])

    def test_arabic_man_won_not_flagged_as_korean(self):
        self.assertTrue(self.run_(self.draft("기준연금액 월 34만원"), self.two())["pass"])

    def test_unknown_org_not_counted(self):
        s = self.two()
        s[1]["org_known"] = False
        self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0])
        s = self.two()
        s[1]["org"] = "korea.kr"  # 호스트명 대체 = 기관 미상
        self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0])

    # ---- 재검증3 반영: 정상 숫자는 통과해야(AC-4 정상 경로) ----
    def test_normal_numbers_found(self):
        b = ("<html><body><p>보건복지부 발표.</p><p>2026년 신청은 3월 31일까지이며, 기준연금액 월 34만 9천700원,"
             " 대상 약 700만 명입니다.</p></body></html>")
        d = self.draft("2026년 신청은 3월 31일까지, 월 34만 9천700원")
        d["cards"][2] = {"title": "대상", "body": "약 700만 명"}
        r = self.run_(d, self.two(b))
        self.assertTrue(r["pass"], r["G2"])

    def test_prefix_only_caption_line_is_checked(self):
        d = self.draft("기준연금액 월 34만원")
        d["sources"] = [{"org": "보건복지부", "url": "https://www.mohw.go.kr/x"}]
        d["caption"] = ("출처: 보건복지부 https://www.mohw.go.kr/x\n출처: 가짜 월 99만원\n기준일: 2026-11-12 최대 88만원\n"
                        "기준일: 2026-11-12\nAI로 제작")
        r = self.run_(d, self.two())
        self.assertFalse(r["pass"])
        self.assertIn("99만원", r["G2"][1])
        self.assertIn("88만원", r["G2"][1])

    def test_native_numerals_fail(self):
        for body in ("스무 살 이상", "열두 가지 혜택", "삼십대 청년"):
            self.assertFalse(self.run_(self.draft(body), self.two())["pass"], body)

    def test_portal_name_not_org(self):
        s = self.two()
        s[1]["org"] = "정책브리핑"
        self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0])
        for name in ("KTV", "KTV 국민방송"):
            s = self.two()
            s[1]["org"] = name
            self.assertFalse(self.run_(self.draft("월 34만원"), s)["G1"][0], name)

    # ---- 재검증4 반영: 만·억·천 뒤 숫자 이어짐(값 축소) 차단, 복합 금액 한 토큰 ----
    def test_truncated_amount_fails(self):
        b = "<html><body>보건복지부: 사업비 3억5천만원, 기준연금액 월 36만9천700원, 지원 1억 2천만원.</body></html>"
        for body in ("사업비 3억 규모", "월 36만 지급", "1억 지원"):
            r = self.run_(self.draft(body), self.two(b))
            self.assertFalse(r["pass"], body)

    def test_compound_amounts_pass(self):
        b = "<html><body>보건복지부: 사업비 3억5천만원, 월 34만 9천700원, 지원 1억 2천만원, 5천만원 한도, 2천만 원.</body></html>"
        r = self.run_(self.draft("사업비 3억 5천만원, 월 34만 9천700원, 지원 1억 2천만원, 5천만원 한도, 2천만 원"), self.two(b))
        self.assertTrue(r["pass"], r["G2"])

    def test_nested_fields_checked(self):
        d = self.draft("기준연금액 월 34만원")
        d["cards"][1] = {"title": "안내", "body": "확인", "bullets": ["최대 77만원"], "meta": {"note": "88만원"}}
        r = self.run_(d, self.two())
        self.assertFalse(r["pass"])
        self.assertIn("77만원", r["G2"][1])
        self.assertIn("88만원", r["G2"][1])

    # ---- 재검증5 반영: 앞쪽 축소(억·만·천 앞붙음) 차단 = 토큰 단위 일치 ----
    def test_front_truncation_fails(self):
        b = "<html><body>보건복지부: 사업비 1억5천만원, 월 2억 34만원, 대상 1만2천명.</body></html>"
        for body in ("사업비 5천만원", "월 34만원 지원", "대상 2천명"):
            s = [self.src("a.html", b, "https://www.korea.kr/news/1", "국민연금공단"),
                 self.src("b.html", b.replace("보건복지부", "복지"), "https://www.mohw.go.kr/x", "보건복지부")]
            self.assertFalse(self.run_(self.draft(body), s)["pass"], body)

    def test_top_level_extra_field_checked(self):
        d = self.draft("기준연금액 월 34만원")
        d["subtitle"] = "최대 77만원"
        self.assertFalse(self.run_(d, self.two())["pass"])

    # ---- 리뷰7 반영: 한글 단위 뒤 경계 — 다른 낱말 속 '2위'·'1인' 은 일치가 아님 ----
    def test_unit_inside_other_word_not_matched(self):
        b = ("<html><body>보건복지부: 2위원회 구성, 1인분 제공, 3편성, 5권역, 10개국어, 8종목, 7인승 차량,"
             " 기준연금액 월 34만원.</body></html>")
        for body in ("평가 2위", "1인 지원", "3편 제작", "5권 배포", "10개국 참여", "8종 혜택", "7인 가족"):
            r = self.run_(self.draft(body), self.two(b))
            self.assertFalse(r["pass"], body)

    def test_unit_followed_by_particle_passes(self):
        b = ("<html><body>보건복지부: 만 65세부터 신청, 3월 31일까지 접수, 1인당 월 34만원씩, 2위를 기록,"
             " 1인가구 지원.</body></html>")
        body = "65세부터 신청, 3월 31일까지 접수, 1인당 월 34만원씩, 2위를 기록, 1인가구 지원"
        r = self.run_(self.draft(body), self.two(b))
        self.assertTrue(r["pass"], r["G2"])

    def test_numbers_in_unit_boundary(self):
        self.assertEqual(V.numbers_in("2위원회"), ["2"])
        self.assertEqual(V.numbers_in("2위를"), ["2위"])
        self.assertEqual(V.numbers_in("1인분"), ["1"])

    def test_numbers_in(self):
        self.assertEqual(V.numbers_in("2026년 11월 12일, 1,000,000원, 3.5%"),
                         ["2026년", "11월", "12일", "1,000,000원", "3.5%"])


if __name__ == "__main__":
    unittest.main()
