# -*- coding: utf-8 -*-
"""T-PAIR1 수용 기준 — '두 기관 같은 사안' 묶음 찾기(순수 함수) · research 후보 순서·채택 기준 · --topic · pair 지표 판정. 네트워크 없음."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C, ledger, research as R, run as RUN, trends as T  # noqa: E402

TODAY = dt.date(2026, 11, 13)
COMMON = (frozenset({"10%", "65세"}), 999, 5)     # 흔한 토큰 집합, 읽은 저장본 수(빈도 계산 없이 주입)


def _uniq(key, n=200):
    import hashlib
    h = hashlib.sha256(key.encode()).digest()
    return "".join(chr(0xAC00 + (h[i % 32] * 7 + i * 131) % 2000) for i in range(n))


def doc(host, org, pub, title, txt, org_known=True):
    """캐시 저장본 한 건 모양. 본문 뒤에 서로 다른 무작위 글자를 붙여 '같은 보도자료'로 안 묶이게 한다."""
    url = f"https://www.{host}/{_uniq(title + org, 4)}"
    return {"url": url, "org": org, "org_known": org_known, "published": pub, "title": title,
            "content": f"<html><body><p>{txt} {_uniq(url)}</p></body></html>".encode("utf-8")}


def fsc(pub="2026-11-10", title="신용융자 담보비율 완화 조치", txt="담보비율 140% 유지, 신용융자 잔액 4,321억원"):
    return doc("fsc.go.kr", "금융위원회", pub, title, txt)


def mofe(pub="2026-11-10", title="증권사 신용융자 한시 면제 시행", txt="신용융자 담보비율 의무 면제 대상 5,678억원"):
    return doc("mofe.go.kr", "재정경제부", pub, title, txt)


def find(docs, **kw):
    return R.find_pairs(docs, TODAY, common=kw.pop("common", COMMON), **kw)


class TestFindPairs(unittest.TestCase):
    def test_two_agencies_same_matter_is_a_pair(self):
        b = find([fsc(), mofe()])
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["kw"], "신용융자")
        self.assertEqual(b[0]["orgs"], ["금융위원회", "재정경제부"])
        self.assertTrue(all(d["distinct"] for d in b[0]["docs"]))

    def test_same_agency_repost_only_is_not_a_pair(self):
        a = fsc()
        b = fsc(title="신용융자 담보비율 완화 조치 보도참고")
        b = {**b, "url": "https://www.korea.kr/repost", "org": "금융위원회"}   # 원문 + korea.kr 재게시: 기관은 같다
        self.assertEqual(find([a, b]), [])

    def test_date_gap_boundary_3_days_ok_4_days_not(self):
        self.assertEqual(len(find([fsc("2026-11-08"), mofe("2026-11-11")])), 1)    # 차이 3일 — 묶음
        self.assertEqual(find([fsc("2026-11-07"), mofe("2026-11-11")]), [])        # 차이 4일 — 아님

    def test_window_7_days(self):
        self.assertEqual(len(find([fsc("2026-11-06"), mofe("2026-11-06")])), 1)    # 오늘-7일 — 포함
        self.assertEqual(find([fsc("2026-11-05"), mofe("2026-11-05")]), [])        # 8일 전 — 최근 7일 밖
        self.assertEqual(find([fsc("2026-11-14"), mofe("2026-11-14")]), [])        # 미래 날짜는 안 침

    def test_no_shared_title_keyword_is_not_a_pair(self):
        self.assertEqual(find([fsc(), mofe(title="청년 일자리 확대 방안 발표")]), [])

    def test_single_short_word_overlap_is_not_a_pair(self):
        self.assertEqual(find([fsc(title="증시 점검 회의"), mofe(title="증시 개장 행사")]), [])        # '증시' 2글자 하나만 겹침

    def test_generic_official_word_does_not_make_a_pair(self):
        self.assertEqual(find([fsc(title="국민 지원 확대 방안"), mofe(title="국민 지원 확대 계획")]), [])  # 공문어뿐

    def test_agency_without_distinctive_number_excluded(self):
        self.assertEqual(find([fsc(), mofe(txt="신용융자 담보비율 의무 면제 대상 확대")]), [])        # 재경부 쪽 숫자 없음
        self.assertEqual(len(find([fsc(), mofe(), doc("moel.go.kr", "고용노동부", "2026-11-10", "신용융자 관련 노동 동향", "신용융자 종사자 숫자 없음")])), 1)
        # 세 번째 기관은 숫자가 없어 빠지고 두 기관 묶음만 남는다

    def test_date_and_common_numbers_are_not_distinctive(self):
        only_dates = "2026년 11월 10일 시행, 2026.11.10 발표, 10%, 65세 이상"
        self.assertEqual(find([fsc(txt=only_dates), mofe()]), [])
        self.assertEqual(find([fsc(txt="신용융자 10% 65세"), mofe()]), [])                         # 흔한 토큰(주입)

    def test_short_numbers_and_unitless_ids_are_not_distinctive(self):
        self.assertEqual(find([fsc(txt="신용융자 7명, 3건 150 148975484"), mofe()]), [])           # 짧은 숫자·단위 없는 번호(기사 ID)

    def test_unknown_org_does_not_count(self):
        b = doc("korea.kr", "korea.kr", "2026-11-10", "신용융자 담보비율 안내", "신용융자 4,321억원", org_known=False)
        self.assertEqual(find([fsc(), b]), [])

    def test_different_agencies_same_release_is_not_a_pair(self):
        a = fsc()
        b = {**mofe(title=a["title"]), "content": a["content"]}   # 제목·본문이 같음 → group_releases 가 1건으로 합친다
        self.assertEqual(find([a, b]), [])

    def test_common_title_word_excluded_by_title_frequency(self):
        filler = [doc("moel.go.kr", "고용노동부", "2026-11-10", f"플랫폼 개편 소식 {i}", f"플랫폼 {1000 + i}건") for i in range(10)]
        a = doc("fsc.go.kr", "금융위원회", "2026-11-10", "플랫폼 개편 점검", "플랫폼 4,321억원")
        b = doc("mofe.go.kr", "재정경제부", "2026-11-10", "플랫폼 개편 발표문", "플랫폼 5,678억원")
        self.assertEqual(find(filler + [a, b]), [])       # '플랫폼'·'개편' 이 제목 12건에 흔함 → 핵심어 아님
        self.assertEqual(len(find([a, b])), 1)            # 문서가 둘뿐이면 흔하지 않아 묶음

    def test_fail_closed_without_frequency_basis(self):
        self.assertEqual(find([fsc(), mofe()], common=(frozenset(), 0, 5)), [])

    def test_ordering_more_agencies_then_newer(self):
        third = doc("moel.go.kr", "고용노동부", "2026-11-10", "신용융자 이용 노동자 대출", "신용융자 이용 노동자 9,876명")
        x = find([fsc(), mofe(), third])
        self.assertEqual(len(x[0]["orgs"]), 3)


class PairRunBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ld = os.path.join(self.tmp.name, "ledger")
        self.sd = os.path.join(self.tmp.name, "sources")
        self.acc = C.load_account("test")
        self.alerts = []

    def tearDown(self):
        self.tmp.cleanup()

    def seed_trend(self, top, in_scope=True):
        ledger.append("trend_ledger", {
            "date": TODAY.isoformat(), "account_id": "test", "status": "ok",
            "candidates": [{"kw": k, "origin": "seed", "in_scope": in_scope} for k in top],
            "scores": [{"kw": k, "value": 0.9, "parts": {"yt_matches": 1, "gt_traffic": 0, "ig_like_median": None}} for k in top],
            "top5": [{"rank": i + 1, "kw": k, "score": 1} for i, k in enumerate(top[:5])]}, self.ld)

    def texts(self, kw, org_a="보건복지부", org_b="국민연금공단", head=True):
        pad = "" if head else "가나다라 " * 120   # 본문 첫 300자 밖으로
        return [{"url": "https://www.korea.kr/news/a", "org": org_a, "published": "2026-11-10", "title": f"{_uniq(kw + 'a', 10)}",
                 "content": f"<html><body><p>{pad}{kw} 안내 {_uniq(kw + 'a')}</p></body></html>".encode("utf-8")},
                {"url": "https://www.mohw.go.kr/b", "org": org_b, "published": "2026-11-10", "title": f"{_uniq(kw + 'b', 10)}",
                 "content": f"<html><body><p>{pad}{kw} 안내 {_uniq(kw + 'b')}</p></body></html>".encode("utf-8")}]

    def disc(self, table, bundles=None):
        tried = []

        def d(kw):
            tried.append(kw)
            return table.get(kw, [])
        d.tried = tried
        if bundles is not None:
            d.pairs = lambda today=None: bundles
        return d

    def go(self, d, acc=None, **kw):
        fetchers = {"discover": d, **kw.pop("fetchers", {})}
        if kw.get("topic") is not None:
            kw.setdefault("rehearsal", True)   # --topic 은 리허설 표지와 같이만 허용(R.run 도 거부)
        return R.run(acc or self.acc, today=TODAY, fetchers=fetchers, ledger_dir=self.ld, sources_dir=self.sd,
                     notify=lambda *a: self.alerts.append(a), **kw)

    def tries(self):
        return [r for r in ledger.read("research_ledger", self.ld) if r["type"] == "try"]

    @staticmethod
    def bundle(kw, titles=None, orgs=("기후에너지환경부", "보건복지부")):
        titles = titles or [f"{kw} 안내 가"] * 2
        return {"kw": kw, "kws": [kw], "orgs": list(orgs), "latest": "2026-11-10",
                "docs": [{"url": f"https://www.korea.kr/{i}", "org": o, "published": "2026-11-10", "title": t, "distinct": ["1,234억원"]}
                         for i, (o, t) in enumerate(zip(orgs, titles))]}


class TestResearchTopicalRule(PairRunBase):
    """채택 기준(더 엄격): kw 가 제목·본문 첫 단락에 실제로 나오는 기관이 2곳 이상."""

    def test_kw_only_in_one_agency_head_is_not_adopted_and_goes_next(self):
        self.seed_trend(["건강보험", "기초연금"])
        mohw = self.texts("건강보험")[0]                                       # 보건복지부: 본문 첫 단락에 건강보험
        nts = {**self.texts("건강보험", head=False)[1], "org": "국세청"}       # 국세청: 본문 첫 단락 밖에서만 건강보험(스침)
        d = self.disc({"건강보험": [mohw, nts], "기초연금": self.texts("기초연금")})
        r = self.go(d)
        self.assertEqual((r["status"], r["kw"]), ("ok", "기초연금"))
        t = self.tries()
        self.assertFalse(t[0]["adopted"])
        self.assertIn("kw 가 제목·본문 첫 단락에 나오는 기관 1곳(보건복지부)", t[0]["reason"])
        self.assertIn("채택 안 함", t[0]["reason"])
        self.assertTrue(t[1]["adopted"])

    def test_kw_in_title_counts_even_if_body_head_does_not(self):
        self.seed_trend(["건강보험"])
        a, b = self.texts("건강보험", head=False)
        a["title"], b["title"] = "건강보험 개편 안내", "건강보험 보도"
        r = self.go(self.disc({"건강보험": [a, b]}))
        self.assertEqual((r["status"], r["kw"]), ("ok", "건강보험"))

    def test_all_trend_candidates_topically_thin_is_hold(self):
        self.seed_trend(["건강보험"])
        a, b = self.texts("건강보험", head=False)
        r = self.go(self.disc({"건강보험": [a, b]}))
        self.assertEqual(r["status"], "hold")


class TestResearchPairCandidates(PairRunBase):
    def test_trend_first_pairs_only_after_all_trend_fail(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"기초연금": self.texts("기초연금"), "에너지바우처": self.texts("에너지바우처")}, [self.bundle("에너지바우처")])
        r = self.go(d)
        self.assertEqual((r["kw"], d.tried), ("기초연금", ["기초연금"]))            # 트렌드가 되면 pair 는 시도 안 함

    def test_pair_tried_when_trend_candidates_all_fail(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"에너지바우처": self.texts("에너지바우처")}, [self.bundle("에너지바우처")])
        r = self.go(d, fetchers={"evidence": lambda kw: True})
        self.assertEqual((r["status"], r["kw"], r["evidence"]), ("ok", "에너지바우처", "indicator"))
        self.assertEqual(d.tried, ["기초연금", "에너지바우처"])
        t = self.tries()
        self.assertEqual((t[-1]["src"], t[-1]["adopted"]), ("pair", True))
        self.assertIn("두 기관 같은 사안 묶음", r["reason"])

    def test_pair_without_indicator_is_evidence_none(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"에너지바우처": self.texts("에너지바우처")}, [self.bundle("에너지바우처")])
        r = self.go(d, fetchers={"evidence": lambda kw: False})
        self.assertEqual((r["status"], r["evidence"]), ("ok", "none"))
        self.assertIn("evidence=none", r["reason"])

    def test_pair_out_of_scope_not_tried_but_recorded(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"메가프로젝트": self.texts("메가프로젝트")}, [self.bundle("메가프로젝트")])
        r = self.go(d)
        self.assertEqual(r["status"], "hold")
        self.assertNotIn("메가프로젝트", d.tried)
        self.assertTrue(any(t["src"] == "pair" and "계정 범위 밖" in t["reason"] for t in self.tries()))

    def test_pair_banned_word_in_title_not_tried(self):
        self.seed_trend(["기초연금"])
        b = self.bundle("에너지바우처", titles=["에너지바우처 지급 안내", "리딩방 단속 에너지바우처"])
        d = self.disc({"에너지바우처": self.texts("에너지바우처")}, [b])
        r = self.go(d)
        self.assertEqual(r["status"], "hold")
        self.assertNotIn("에너지바우처", d.tried)
        self.assertTrue(any("금칙 분류 investment_solicit" in t["reason"] for t in self.tries()))

    def test_pair_account_banned_extra_applies(self):
        self.seed_trend(["기초연금"])
        acc = {**self.acc, "banned_topics_extra": ["에너지바우처"]}
        d = self.disc({"에너지바우처": self.texts("에너지바우처")}, [self.bundle("에너지바우처")])
        r = self.go(d, acc=acc)
        self.assertEqual(r["status"], "hold")
        self.assertNotIn("에너지바우처", d.tried)

    def test_pair_still_needs_two_agencies_with_kw_in_title_or_head(self):
        self.seed_trend(["기초연금"])
        a, b = self.texts("에너지바우처", head=False)    # 캐시 매칭은 되지만 첫 단락 밖
        d = self.disc({"에너지바우처": [a, b]}, [self.bundle("에너지바우처")])
        r = self.go(d)
        self.assertEqual(r["status"], "hold")

    def test_discover_without_pairs_attribute_means_no_pair_candidates(self):
        self.seed_trend(["기초연금"])
        d = self.disc({})
        self.assertEqual(self.go(d)["status"], "hold")


class TestTopicOption(PairRunBase):
    def test_topic_runs_only_matching_pair_bundles(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"에너지바우처": self.texts("에너지바우처"), "기초연금": self.texts("기초연금")},
                      [self.bundle("에너지바우처")])
        r = self.go(d, topic="에너지바우처")
        self.assertEqual((r["status"], r["kw"]), ("ok", "에너지바우처"))
        self.assertEqual(d.tried, ["에너지바우처"])                    # 트렌드 순위(기초연금)는 안 돈다

    def test_topic_with_no_matching_bundle_is_hold(self):
        self.seed_trend(["기초연금"])
        d = self.disc({"기초연금": self.texts("기초연금")}, [self.bundle("에너지바우처")])
        r = self.go(d, topic="CBAM")
        self.assertEqual(r["status"], "hold")
        self.assertIn("일치하는 두 기관 묶음이 없음", r["reason"])
        self.assertEqual(d.tried, [])

    def test_topic_out_of_scope_bundle_is_hold_not_forced(self):
        d = self.disc({"메가프로젝트": self.texts("메가프로젝트")}, [self.bundle("메가프로젝트")])
        r = self.go(d, topic="메가프로젝트")
        self.assertEqual(r["status"], "hold")
        self.assertEqual(d.tried, [])

    def test_topic_without_rehearsal_is_error_in_run_and_cli(self):
        with self.assertRaises(ValueError):
            RUN.run(self.acc, {}, topic="에너지바우처", rehearsal=False, ledger_dir=self.ld)
        with self.assertRaises(SystemExit) as cm:
            RUN.main(["--account", "test", "--topic", "에너지바우처"])
        self.assertEqual(cm.exception.code, 2)


    def test_research_run_topic_without_rehearsal_is_value_error(self):
        d = self.disc({}, [self.bundle("에너지바우처")])
        with self.assertRaises(ValueError) as cm:
            self.go(d, topic="에너지바우처", rehearsal=False)
        self.assertIn("--topic 은 --rehearsal 과 같이만 쓸 수 있다", str(cm.exception))
        self.assertEqual(d.tried, [])


class TestPairKeywordDedupe(PairRunBase):
    def test_pair_kw_same_as_trend_candidate_by_norm_is_tried_once(self):
        self.seed_trend(["에너지 바우처"])        # 트렌드 후보(공백 포함) = 묶음 kw '에너지바우처' 와 _norm 이 같다
        d = self.disc({"에너지 바우처": [], "에너지바우처": []}, [self.bundle("에너지바우처")])
        self.go(d)
        self.assertEqual(len(d.tried), 1, d.tried)


class TestIndicatorEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = os.path.join(self.tmp.name, TODAY.isoformat())
        os.makedirs(d)
        with open(os.path.join(d, "120000_yt_mostPopular_KR_cat0.json"), "w", encoding="utf-8") as f:
            json.dump({"items": [{"snippet": {"title": "오늘의 에너지 바우처 신청법"}, "statistics": {"viewCount": "10"}}]}, f)
        self.none = lambda today: ({}, None)

    def tearDown(self):
        self.tmp.cleanup()

    def ev(self, kw, ig=None):
        return T.indicator_evidence(kw, TODAY, raw_dir=self.tmp.name, ig_loader=ig or self.none)

    def test_youtube_title_match_is_evidence(self):
        self.assertTrue(self.ev("에너지바우처")[0])

    def test_no_indicator_is_none(self):
        ok, parts = self.ev("신용융자")
        self.assertFalse(ok)
        self.assertEqual((parts["yt_matches"], parts["gt_traffic"], parts["ig_like_median"]), (0, 0, None))

    def test_whole_word_requires_word_boundary(self):
        def ev(kw):
            return T.indicator_evidence(kw, TODAY, raw_dir=self.tmp.name, ig_loader=self.none, whole_word=True)[0]
        self.assertFalse(ev("에너지바우처"))   # 제목은 '에너지 바우처'(띄어쓰기) — 정규화 부분 일치는 되지만 완전한 단어가 아님
        self.assertTrue(ev("바우처"))          # 앞뒤가 공백·문장 끝
        self.assertFalse(ev("바우"))           # 단어 일부
        self.assertTrue(ev("에너지"))          # 단독 단어
        self.assertFalse(ev("신청"))           # '신청법' 의 앞부분 — 뒤가 한글이면 완전한 단어가 아님
        self.assertTrue(T.indicator_evidence("신청", TODAY, raw_dir=self.tmp.name, ig_loader=self.none)[0])   # 트렌드 경로(기본)는 부분 일치 그대로

        self.assertTrue(self.ev("신용융자", ig=lambda t: ({"신용융자": 12}, "x"))[0])

    def test_loader_failure_means_no_evidence(self):
        def boom(t):
            raise RuntimeError("x")
        self.assertFalse(self.ev("신용융자", ig=boom)[0])

    def test_no_raw_dir_means_no_evidence(self):
        self.assertFalse(T.indicator_evidence("신용융자", TODAY, raw_dir=os.path.join(self.tmp.name, "nope"), ig_loader=self.none)[0])


if __name__ == "__main__":
    unittest.main()
