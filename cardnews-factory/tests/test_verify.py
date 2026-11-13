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
             " 2위를 기록.</body></html>")
        body = "65세부터 신청, 3월 31일까지 접수, 1인당 월 34만원씩, 2위를 기록"
        r = self.run_(self.draft(body), self.two(b))
        self.assertTrue(r["pass"], r["G2"])

    def test_numbers_in_unit_boundary(self):
        self.assertEqual(V.numbers_in("2위원회"), ["2"])
        self.assertEqual(V.numbers_in("2위를"), ["2위"])
        self.assertEqual(V.numbers_in("1인분"), ["1"])

    def test_numbers_in(self):
        self.assertEqual(V.numbers_in("2026년 11월 12일, 1,000,000원, 3.5%"),
                         ["2026년", "11월", "12일", "1,000,000원", "3.5%"])

    # ---- 리뷰8: 한 글자 조사(이·가·로·의·도)는 뒤가 비한글일 때만 ----
    def test_single_char_particle_needs_nonhangul_after(self):
        self.assertEqual(V.numbers_in("1인가구 지원"), ["1"])        # 단위 없는 수로 떨어져 G2 가 보류시킴
        self.assertEqual(V.numbers_in("2차로변 공사"), ["2"])
        self.assertEqual(V.numbers_in("9종가는 오른다"), ["9"])
        self.assertEqual(V.numbers_in("3분의 1 지급"), ["3", "1"])
        self.assertEqual(V.numbers_in("2차로 이동"), ["2차"])           # 뒤가 공백이면 조사 '로'

    def test_single_char_particle_positive_kept(self):
        self.assertEqual(V.numbers_in("1인당 지원"), ["1인"])
        self.assertEqual(V.numbers_in("65세부터 신청"), ["65세"])
        self.assertEqual(V.numbers_in("2위를 기록"), ["2위"])
        self.assertEqual(V.numbers_in("2위가 되었다"), ["2위"])
        self.assertEqual(V.numbers_in("3명의 신청"), ["3명"])
        self.assertEqual(V.numbers_in("3명도 신청"), ["3명"])

    def test_g2_holds_on_one_in_household_word(self):
        b = "<html><body>보건복지부: 기준연금액 월 34만원. 1인가구 지원.</body></html>"
        r = self.run_(self.draft("1인가구 월 34만원 지원"), self.two(b))
        self.assertFalse(r["pass"])

    # ---- T-SRC2/3: 선언만 한 출처는 기관 수에서 뺀다(본문·구별력 있는 숫자만) ----
    NOCOMMON = (frozenset(), 999, 5)          # 빈도 계산 없이(실제 캐시를 읽지 않음)
    COMMON = (frozenset({"10%", "65세", "5%"}), 999, 5)

    def two_org(self, other_html):
        return [self.src("m.html", "<html><body>보건복지부: 대상 약 136만 명, 본인부담 약 75만 원, 지급 99만원.</body></html>",
                         "https://www.mohw.go.kr/x", "보건복지부"),
                self.src("o.html", other_html, "https://www.mois.go.kr/1", "행정안전부")]

    def run_c(self, draft, srcs, common=None):
        return V.run(draft, srcs, ledger_dir=self.d, domains=DOMAINS, require_contribution=True, common=common or self.NOCOMMON)

    def dr(self, body, title="안내", caption="", tags=None):
        d = {"account_id": "test", "kw": "기초연금", "cards": [{"title": title, "body": body}] + [{"title": "안내", "body": "확인"}] * 4}
        if caption:
            d["caption"] = caption
        if tags:
            d["hashtags"] = tags
        return d

    COMMON_OTHER = "<html><body>행정안전부 안내: 2026년 11월 1일 시행, 10%, 5%, 65세 이상, 2026.11.01.</body></html>"

    def test_declared_but_unused_org_not_counted(self):
        r = self.run_c(self.dr("대상 약 136만 명"), self.two_org(self.COMMON_OTHER))
        self.assertFalse(r["G1"][0])
        self.assertIn("선언했지만 내용에 쓰이지 않은 기관: 행정안전부", r["G1"][1])

    def test_two_orgs_each_with_distinctive_numbers_passes(self):
        other = "<html><body>행정안전부: 청사 이용 인원 75만 원 규모 예산.</body></html>"
        r = self.run_c(self.dr("대상 약 136만 명, 예산 약 75만 원"), self.two_org(other))
        self.assertTrue(r["G1"][0], r["G1"])

    def test_same_distinctive_number_in_both_counts_both(self):
        other = "<html><body>행정안전부 안내: 대상 약 136만 명.</body></html>"
        r = self.run_c(self.dr("대상 약 136만 명"), self.two_org(other))
        self.assertTrue(r["G1"][0], r["G1"])

    def test_unitless_long_number_does_not_buy_an_org(self):
        # 복지부 단위 숫자 1개 + 타 기관은 무단위 긴 번호(기사 ID 꼴)만 — 번호를 본문에 넣어도 그 기관은 기여가 아니다
        other = "<html><body>행정안전부 게시물 번호 148975407, 조회 148975407.</body></html>"
        r = self.run_c(self.dr("대상 약 136만 명, 번호 148975407"), self.two_org(other))
        self.assertFalse(r["G1"][0])
        self.assertIn("선언했지만 내용에 쓰이지 않은 기관: 행정안전부", r["G1"][1])
        self.assertEqual(V.contribution_tokens(self.dr("대상 약 136만 명, 번호 148975407")), {"136만명"})

    def test_is_distinctive_number_is_the_shared_rule(self):
        self.assertTrue(V.is_distinctive_number("136만명"))
        self.assertFalse(V.is_distinctive_number("148975407"))               # 단위 없음
        self.assertFalse(V.is_distinctive_number("2026년"))                  # 날짜성
        self.assertFalse(V.is_distinctive_number("136만명", {"136만명"}))      # 흔한 토큰
        self.assertFalse(V.is_distinctive_number("7명"))                     # 짧은 숫자
        self.assertTrue(V.is_distinctive_number("7명", allow_short=True))

    def test_contribution_not_required_by_default(self):
        r = V.run(self.dr("대상 약 136만 명"), self.two_org(self.COMMON_OTHER), ledger_dir=self.d, domains=DOMAINS)
        self.assertTrue(r["G1"][0])

    # VERDICT14 의 9변형: 날짜·흔한 숫자를 본문/제목/캡션/해시태그에 끼워도 쓰지 않은 기관은 기여가 아니다
    def test_variants_common_and_date_tokens_do_not_buy_an_org(self):
        base = "대상 약 136만 명"
        variants = []
        for t in ("2026년", "11월", "1일", "2026년 11월 1일", "10%", "65세"):      # 본문 6종
            variants.append(self.dr(f"{base}, {t}"))
        variants.append(self.dr(base, caption=f"{base}\n2026년 11월 1일 10% 65세"))          # 캡션만
        variants.append(self.dr(base, title="2026년 11월 1일 10% 65세"))                       # 제목만
        variants.append(self.dr(base, tags=["#2026년", "#10%", "#65세"]))                      # 해시태그만
        self.assertEqual(len(variants), 9)
        for d in variants:
            r = self.run_c(d, self.two_org(self.COMMON_OTHER), common=self.COMMON)
            self.assertFalse(r["G1"][0], (d["cards"][0], d.get("caption")))

    def test_distinctive_number_only_in_title_or_caption_does_not_count(self):
        other = "<html><body>행정안전부: 청사 이용 인원 75만 원 규모 예산.</body></html>"
        for d in (self.dr("대상 약 136만 명", title="예산 75만 원"), self.dr("대상 약 136만 명", caption="예산 75만 원")):
            r = self.run_c(d, self.two_org(other))
            self.assertFalse(r["G1"][0])

    def test_document_frequency_boundary(self):
        import tempfile as tf
        with tf.TemporaryDirectory() as t:
            idx = os.path.join(t, "index.jsonl")
            lines = []
            n_docs = 100
            for k in range(n_docs):
                path = os.path.join(t, f"d{k}.html")
                # 'A5건' 은 정확히 5개 문서(상한 5 = 포함 허용), 'B6건' 은 6개(상한 초과 = 흔함)
                body = "".join(["문서 A5건 " if k < 5 else "", "문서 B6건 " if k < 6 else "", f"고유 {1000 + k}건"])
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"<html><body>{body}</body></html>")
                lines.append('{"saved_path": %s}' % __import__("json").dumps(path))
            with open(idx, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            common, n, lim, *_ = V.common_tokens(idx)
            self.assertEqual((n, lim), (100, 5))                 # max(5, ceil(100*2%)=2) = 5
            self.assertNotIn("5건", common)
            self.assertIn("6건", common)

    def test_small_cache_also_excludes_short_numbers(self):
        d = self.dr("대상 7명, 약 136만 명")
        self.assertEqual(V.contribution_tokens(d, frozenset(), 10), {"136만명"})        # 저장본 10건: 짧은 숫자 제외
        self.assertEqual(V.contribution_tokens(d, frozenset(), 999), {"7명", "136만명"})

    def test_date_like_tokens_excluded(self):
        for t in ("2026.11.04", "11.4", "2026년", "12월", "1일", "9시", "30분"):
            self.assertTrue(V.is_date_token(t), t)
        self.assertFalse(V.is_date_token("136만명"))
        self.assertFalse(V.is_date_token("7%"))

    def test_g1_failure_keeps_g2_diagnosis(self):
        r = self.run_c(self.dr("대상 약 999만 명"), self.two_org(self.COMMON_OTHER))
        self.assertFalse(r["pass"])
        self.assertIn("진단용 숫자 대조", r["G2"][1])
        self.assertIn("원문에서 못 찾은 값: 999만명", r["G2"][1])

    # ---- T-SRC4: common_tokens 경로 해석·fail-closed ----
    def _mk_cache(self, root, n_rel, n_abs, token_docs=None):
        """인덱스 줄: 상대 'files/…' n_rel 줄 + 절대경로 n_abs 줄 + saved_path 없는 줄 1개. 모든 문서에 '65세' 가 있다."""
        import json as _j
        os.makedirs(os.path.join(root, "files"), exist_ok=True)
        lines = []
        for k in range(n_rel + n_abs):
            path = os.path.join(root, "files", f"d{k}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"<html><body>대상 65세 이상, 고유 {2000 + k}건</body></html>")
            sp = f"files/d{k}.html" if k < n_rel else path
            lines.append(_j.dumps({"url": f"https://www.korea.kr/{k}", "saved_path": sp}))
        lines.append(_j.dumps({"url": "https://www.korea.kr/neg", "negative": True}))   # saved_path 없는 줄
        idx = os.path.join(root, "index.jsonl")
        with open(idx, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return idx

    def test_common_tokens_resolves_relative_and_absolute_paths(self):
        root = os.path.join(self.d, "cache1")
        idx = self._mk_cache(root, 30, 30)
        common, n, lim, *_ = V.common_tokens(idx)
        self.assertEqual(n, 60)                       # 상대 30 + 절대 30 = 전체 줄(saved_path 없는 줄 제외)
        self.assertIn("65세", common)                 # 60개 문서 모두에 있음 → 흔함
        self.assertEqual(lim, 5)

    def test_common_tokens_same_result_from_other_cwd(self):
        root = os.path.join(self.d, "cache2")
        idx = self._mk_cache(root, 40, 20)
        a = V.common_tokens(idx)
        V._DF_CACHE.clear()
        old = os.getcwd()
        other = os.path.join(self.d, "elsewhere")
        os.makedirs(other, exist_ok=True)
        os.chdir(other)
        try:
            b = V.common_tokens(idx)
            c = V.common_tokens(os.path.relpath(idx, other))   # 상대 인덱스 경로도 같은 결과
        finally:
            os.chdir(old)
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertEqual(a[1], 60)

    def test_common_tokens_missing_or_unreadable_index_is_zero_docs(self):
        self.assertEqual(V.common_tokens(os.path.join(self.d, "nope.jsonl"))[1], 0)
        empty = os.path.join(self.d, "empty.jsonl")
        open(empty, "w").close()
        self.assertEqual(V.common_tokens(empty)[1], 0)
        junk = os.path.join(self.d, "junk.jsonl")
        with open(junk, "w", encoding="utf-8") as f:
            f.write("not json\n{\"saved_path\": \"files/missing.html\"}\n")
        self.assertEqual(V.common_tokens(junk)[1], 0)

    def test_fail_closed_when_no_frequency_basis(self):
        r = self.run_c(self.dr("대상 약 136만 명"), self.two_org("<html><body>행정안전부: 대상 약 136만 명.</body></html>"),
                       common=(frozenset(), 0, 5))
        self.assertFalse(r["G1"][0])
        self.assertIn("기여 판정 불가", r["G1"][1])

    # ---- T-SRC5: 상한 1% · 부분 읽기 실패 ----
    def _mk_n_docs(self, root, n, tokens_in):
        """n 개 문서. tokens_in = {문장: 들어갈 문서 수}. 인덱스는 상대경로."""
        import json as _j
        os.makedirs(os.path.join(root, "files"), exist_ok=True)
        lines = []
        for k in range(n):
            extra = " ".join(t for t, c in tokens_in.items() if k < c)
            with open(os.path.join(root, "files", f"d{k}.html"), "w", encoding="utf-8") as f:
                f.write(f"<html><body>고유 {5000 + k}건 {extra}</body></html>")
            lines.append(_j.dumps({"url": f"https://www.korea.kr/{k}", "saved_path": f"files/d{k}.html"}))
        idx = os.path.join(root, "index.jsonl")
        with open(idx, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return idx

    def test_df_ratio_is_one_percent_boundary(self):
        # 600건 → 상한 max(5, ceil(6.0)=6) = 6. 'X6건'(6건)은 허용, 'Y7건'(7건)은 흔함. (2% 였다면 상한 12 라 Y7건 도 구별 숫자로 통과)
        idx = self._mk_n_docs(os.path.join(self.d, "c600"), 600, {"X6건": 6, "Y7건": 7})
        common, n, lim, total, unread = V.common_tokens(idx)
        self.assertEqual((n, lim, total, unread), (600, 6, 600, 0))
        self.assertNotIn("6건", common)
        self.assertIn("7건", common)

    def test_df_65se_style_common_number_does_not_buy_org_at_one_percent(self):
        idx = self._mk_n_docs(os.path.join(self.d, "c535"), 535, {"65세": 10})   # 실제 캐시와 같은 규모·빈도(535건, df=10)
        common = V.common_tokens(idx)
        self.assertIn("65세", common[0])
        other = "<html><body>행정안전부: 대상 65세 이상.</body></html>"
        r = self.run_c(self.dr("대상 약 136만 명, 65세 이상"), self.two_org(other), common=common)
        self.assertFalse(r["G1"][0])

    def _partial_cache(self, name, total, missing):
        idx = self._mk_n_docs(os.path.join(self.d, name), total, {})
        root = os.path.dirname(idx)
        for k in range(missing):
            os.remove(os.path.join(root, "files", f"d{k}.html"))
        return idx

    def test_partial_read_failure_over_5_percent_fails_closed(self):
        idx = self._partial_cache("p94", 100, 6)          # 6% 읽기 실패
        common = V.common_tokens(idx)
        self.assertEqual((common[1], common[3], common[4]), (94, 100, 6))
        r = self.run_c(self.dr("대상 약 136만 명"), self.two_org("<html><body>행정안전부: 대상 약 136만 명.</body></html>"), common=common)
        self.assertFalse(r["G1"][0])
        self.assertIn("기여 판정 불가", r["G1"][1])
        self.assertIn("6/100", r["G1"][1])

    def test_partial_read_failure_within_5_percent_proceeds_with_note(self):
        idx = self._partial_cache("p96", 100, 4)          # 4% 읽기 실패
        common = V.common_tokens(idx)
        r = self.run_c(self.dr("대상 약 136만 명"), self.two_org("<html><body>행정안전부: 대상 약 136만 명.</body></html>"), common=common)
        self.assertTrue(r["G1"][0], r["G1"])
        self.assertIn("읽기 실패 4건", r["G1"][1])


if __name__ == "__main__":
    unittest.main()
