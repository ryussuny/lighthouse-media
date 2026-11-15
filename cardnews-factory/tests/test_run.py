# -*- coding: utf-8 -*-
"""T-09 시험: 가짜 fetcher·생성기·분류기로 끝까지 통과 1건 / 관문별 보류 / 중간 STOP / evidence=none 보류 / cost_ledger 줄 / HTML.
네트워크·Anthropic·Higgsfield·인스타 호출 0."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cardnews import config as C, ledger, report, run as R  # noqa: E402

BANNED = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
TODAY = dt.date(2026, 11, 12)
NOW = dt.datetime(2026, 11, 12, 20, 0, 0)
DOC_A = "<html><body><p>기초연금은 만 65세 이상 어르신에게 지급한다. 생활꿀팁 정부지원금 건강보험 국민연금 안내.</p></body></html>".encode("utf-8")
DOC_B = "<html><body><p>보건복지부 보도자료입니다. 기초연금 신청은 가까운 주민센터를 방문해서 하면 된다. 기초연금 대상은 만 65세 이상이며 소득과 재산 기준을 따로 본다. 서류는 신분증과 통장 사본이다.</p></body></html>".encode("utf-8")
VIDEOS = [{"title": "기초연금 핵심 정리", "views": 900000, "cat": "26"}, {"title": "생활꿀팁 모음", "views": 400000, "cat": "26"}]


def _rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


NAMES = "가나다라마"


def gen_ok(prompt):
    return json.dumps({"cards": [{"title": f"제목{NAMES[i]}", "body": "기초연금은 만 65세 이상이 대상입니다" if i == 1 else f"본문{NAMES[i]}"} for i in range(5)],
                       "caption_body": "기초연금 안내입니다.", "hashtags": ["기초연금", "생활정보"]}, ensure_ascii=False)


def gen_wrong_number(prompt):
    return json.dumps({"cards": [{"title": f"제목{NAMES[i]}", "body": "월 99만원 지급, 만 65세 이상" if i == 1 else f"본문{NAMES[i]}"} for i in range(5)],
                       "caption_body": "안내", "hashtags": ["기초연금"]}, ensure_ascii=False)


USED_DEFAULT = ("https://www.korea.kr/news/a", "https://www.mohw.go.kr/b")   # fx() 기본 두 출처
from cardnews import verify as _V  # noqa: E402
_REAL_COMMON = _V.common_tokens   # setUp 이 가짜로 막기 전의 실제 함수(가짜 없는 시험용)
ok_classify = lambda t: (True, "none", "정상")  # noqa: E731
bad_classify = lambda t: (False, "adult", "가짜 분류기: 위반")  # noqa: E731


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.tmp.name
        self.d = {k: os.path.join(t, k) for k in ("ledger", "out", "hold", "sources", "drafts")}
        self.stop = os.path.join(t, "STOP")
        self.alerts = []
        self.acc = C.load_account("test")
        pc = mock.patch("cardnews.verify.common_tokens", return_value=(frozenset(), 999, 5))   # 실제 source_cache 를 읽지 않음
        pc.start()
        self.addCleanup(pc.stop)
        # 원장 ts 를 실제 시계가 아닌 시험 고정 NOW 로 — 안 그러면 TODAY+2일을 넘긴 날부터 G5 시험이 날짜 때문에 깨진다
        pn = mock.patch("cardnews.ledger.now_iso", return_value=NOW.isoformat(timespec="seconds"))
        pn.start()
        self.addCleanup(pn.stop)

    def discover(self, docs=None):
        docs = docs if docs is not None else [("https://www.korea.kr/news/a", "행정안전부", DOC_A), ("https://www.mohw.go.kr/b", "보건복지부", DOC_B)]
        return lambda kw: [{"url": u, "org": o, "published": "2026-11-10", "org_known": True, "content": c, "title": f"{o} {kw} 안내"} for u, o, c in docs]

    def fx(self, docs=None, discover=None):
        return {"trends": {"google_trends": lambda day: ([], None), "youtube": lambda day, cats: (VIDEOS, ["yt.json"]),
                           "ig": lambda today: ({}, None)},
                "research": {"discover": discover or self.discover(docs)}}

    def go(self, acc=None, generate=gen_ok, classify=ok_classify, fetchers=None, **kw):
        return R.run(acc or self.acc, BANNED, today=TODAY, now=NOW, fetchers=fetchers or self.fx(), generate=generate,
                     classify=classify, notify=lambda *a: self.alerts.append(a), ledger_dir=self.d["ledger"],
                     out_root=kw.pop("out_root", self.d["out"]), hold_root=self.d["hold"], sources_dir=self.d["sources"],
                     stop_file=self.stop, bg_manifest=kw.pop("bg_manifest", []), **kw)

    def holds(self):
        p = os.path.join(self.d["hold"], TODAY.isoformat())
        return sorted(os.listdir(p)) if os.path.isdir(p) else []

    def out_account_dir(self):
        return os.path.join(self.d["out"], TODAY.isoformat(), "test")

    # ---- 통과 ----
    def test_full_pass(self):
        r = self.go()
        self.assertEqual(r["status"], "ok", r["reason"])
        out = r["out_dir"]
        self.assertEqual(out, self.out_account_dir())
        for i in range(1, 6):
            self.assertTrue(os.path.exists(os.path.join(out, f"card_{i}.png")))
        cap = _rd(os.path.join(out, "캡션.txt"))
        self.assertTrue(cap.strip().endswith("AI로 제작"))
        self.assertIn("출처: ", cap)
        m = json.loads(_rd(os.path.join(out, "manifest.json")))
        self.assertFalse(m["posted"])
        self.assertEqual([g["gate"] for g in m["gates"][:2]], ["G1", "G2"])
        self.assertTrue(all(g["pass"] for g in m["gates"]))
        self.assertTrue(os.path.exists(os.path.join(out, "design_manifest.json")))
        self.assertEqual(m["design"]["cards"][0]["image_path"], os.path.join(out, "card_1.png"))
        self.assertEqual(self.holds(), [])
        self.assertEqual(self.alerts, [])
        self.assertFalse(os.path.exists(os.path.join(self.d["out"], TODAY.isoformat(), ".stage_test")))
        rows = ledger.read("check_ledger", self.d["ledger"])
        self.assertEqual([x for x in rows if x["gate"] == "ALL"][-1]["pass"], True)
        self.assertTrue(r["html"] and os.path.exists(r["html"]))

    def test_cost_ledger_line(self):
        r = self.go()
        rows = ledger.read("cost_ledger", self.d["ledger"])
        self.assertEqual(len(rows), 1)
        c = rows[0]
        self.assertEqual(c["higgsfield"]["calls"], 0)
        self.assertEqual(c["higgsfield"]["credits"], 0)
        self.assertEqual(c["anthropic"]["calls"], 2)   # compose 1 + guard 분류 1
        self.assertEqual((c["account_id"], c["status"]), ("test", "ok"))
        self.assertIn("input_tokens", c["anthropic"])
        self.assertEqual(r["cost"], {k: c[k] for k in ("anthropic", "higgsfield", "attempts")})
        self.assertEqual(len(ledger.read("run_ledger", self.d["ledger"])), 1)

    def test_real_background_library_used(self):
        r = self.go(bg_manifest=None)  # None → data/backgrounds/manifest.json (Higgsfield 재사용)
        self.assertEqual(r["status"], "ok", r["reason"])
        m = json.loads(_rd(os.path.join(r["out_dir"], "manifest.json")))
        self.assertTrue(all(c["bg_origin"] == "higgsfield" and c["job_id"] for c in m["design"]["cards"]))

    # ---- 관문별 보류 ----
    def test_verify_g2_wrong_number_held(self):
        r = self.go(generate=gen_wrong_number)
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"))
        self.assertIn("99만원", r["reason"])
        self.assertEqual(len(self.holds()), 1)
        self.assertTrue(os.path.exists(os.path.join(r["hold_path"], "draft.json")))
        self.assertFalse(os.path.exists(self.out_account_dir()))
        self.assertEqual(len(self.alerts), 1)

    def test_verify_g1_single_org_held_by_research(self):
        r = self.go(fetchers=self.fx(docs=[("https://www.korea.kr/news/a", "행정안전부", DOC_A)]))
        self.assertEqual((r["status"], r["stage"]), ("held", "research"))
        self.assertFalse(os.path.exists(self.out_account_dir()))
        self.assertEqual(len(self.alerts), 1)  # research 가 1회

    def test_guard_g3_held_one_alert(self):
        r = self.go(classify=bad_classify)
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("G3", r["reason"])
        self.assertEqual(len(self.holds()), 1)
        self.assertFalse(os.path.exists(self.out_account_dir()))
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(ledger.read("cost_ledger", self.d["ledger"])[0]["status"], "held")

    def test_guard_g3_keyword_held(self):
        gen = lambda p: gen_ok(p).replace("기초연금 안내입니다.", "수익 보장 안내")  # noqa: E731
        r = self.go(generate=gen)
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))

    def test_g5_duplicate_second_run_held(self):
        self.assertEqual(self.go()["status"], "ok")
        self.alerts.clear()
        r = self.go()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("G5", r["reason"])

    def test_g5_not_poisoned_by_failed_design(self):
        r = self.go(bg_manifest=[{"file": "x.png", "origin": "external"}])
        self.assertEqual((r["status"], r["stage"]), ("held", "design"))
        self.alerts.clear()
        self.assertEqual(self.go()["status"], "ok")  # 같은 키워드 재시도가 G5 에 막히지 않는다

    def test_design_failure_held(self):
        r = self.go(bg_manifest=[{"file": "x.png", "origin": "external"}])
        self.assertEqual((r["status"], r["stage"]), ("held", "design"))
        self.assertFalse(os.path.exists(self.out_account_dir()))
        self.assertEqual(len(self.alerts), 1)

    def test_compose_error_held(self):
        r = self.go(generate=lambda p: "그냥 글")
        self.assertEqual((r["status"], r["stage"]), ("held", "compose"))
        self.assertEqual(len(self.alerts), 1)

    def test_evidence_none_held(self):
        fake = {"status": "ok", "kw": "기초연금", "source_urls": [], "evidence": "none", "reason": "x"}
        with mock.patch("cardnews.research.run", return_value=fake):
            r = self.go()
        self.assertEqual((r["status"], r["stage"]), ("held", "research"))
        self.assertIn("evidence=none", r["reason"])
        self.assertEqual(len(self.alerts), 1)
        self.assertFalse(os.path.exists(self.out_account_dir()))

    def test_no_candidates(self):
        fx = {"trends": {"google_trends": lambda d: ([], None), "youtube": lambda d, c: ([], []), "ig": lambda t: ({}, None)},
              "research": {"discover": self.discover()}}
        r = self.go(fetchers=fx)
        self.assertEqual((r["status"], r["stage"]), ("no_candidates", "trends"))

    # ---- STOP·paused ----
    def test_stop_in_middle(self):
        def discover(kw):
            open(self.stop, "w").close()      # research 도중 STOP 생김
            return self.discover()(kw)
        r = self.go(fetchers=self.fx(discover=discover))
        self.assertEqual((r["status"], r["stage"]), ("stopped", "compose"))
        self.assertIn("STOP", r["reason"])
        self.assertEqual(ledger.read("cost_ledger", self.d["ledger"])[0]["anthropic"]["calls"], 0)  # compose 호출 전에 멈춤
        self.assertEqual(self.holds(), [])
        self.assertFalse(os.path.exists(self.out_account_dir()))

    def test_paused_stops_at_start(self):
        r = self.go(acc=dict(self.acc, paused=True))
        self.assertEqual((r["status"], r["stage"]), ("stopped", "trends"))
        self.assertEqual(ledger.read("trend_ledger", self.d["ledger"]), [])

    def test_stop_before_design(self):
        def classify(t):
            open(self.stop, "w").close()
            return True, "none", "ok"
        r = self.go(classify=classify)
        self.assertEqual((r["status"], r["stage"]), ("stopped", "design"))
        self.assertFalse(os.path.exists(self.out_account_dir()))

    # ---- HTML ----
    def test_html_report(self):
        self.go(generate=gen_wrong_number)       # 보류 1건
        self.go()                                  # 결과 1건
        html_path = os.path.join(self.d["out"], TODAY.isoformat(), "index.html")
        h = _rd(html_path)
        self.assertIn("기초연금", h)
        self.assertIn("<img", h)
        self.assertIn("보류함", h)
        self.assertIn("99만원", h)                 # 보류 사유
        self.assertIn("https://www.mohw.go.kr/b", h)  # 출처 링크
        self.assertIn("G2", h)
        self.assertNotIn("<script", h)
        self.assertNotIn("cdn", h.lower())
        self.assertEqual(report.build(TODAY.isoformat(), self.d["out"], self.d["hold"], self.d["ledger"]), html_path)

    def test_exception_becomes_error_status(self):
        with mock.patch("cardnews.trends.run", side_effect=RuntimeError("boom ?key=SECRET1")):
            r = self.go()
        self.assertEqual(r["status"], "error")
        self.assertNotIn("SECRET1", r["reason"])
        self.assertEqual(self.alerts[-1][0], "error")

    # ---- --rehearsal ----
    def _evidence_none(self):
        from cardnews import research
        real = research.run

        def wrapped(*a, **k):
            r = dict(real(*a, **k))
            r["evidence"] = "none"
            return r
        return mock.patch("cardnews.research.run", side_effect=wrapped)

    def test_rehearsal_skips_only_evidence_rule(self):
        with self._evidence_none():
            held = self.go()                        # 일반 실행: evidence=none 이면 보류
        self.assertEqual((held["status"], held["stage"]), ("held", "research"))
        self.alerts.clear()
        with self._evidence_none():
            r = self.go(rehearsal=True, out_root=os.path.join(self.tmp.name, "rehearsal"))
        self.assertEqual(r["status"], "ok", r["reason"])
        out = r["out_dir"]
        self.assertIn("rehearsal", out)
        self.assertTrue(_rd(os.path.join(out, "캡션.txt")).startswith("[리허설 — 게시 불가]"))
        mtxt = _rd(os.path.join(out, "manifest.json"))
        m = json.loads(mtxt)
        self.assertTrue(m["rehearsal"] and m["evidence_rule_skipped"] and not m["posted"])
        self.assertEqual(list(m)[0], "rehearsal_notice")
        self.assertEqual(m["rehearsal_notice"], "리허설 — 게시 불가")
        h = _rd(r["html"])
        self.assertIn("리허설 — 게시 불가", h)
        self.assertLess(h.index("리허설 — 게시 불가"), h.index("카드뉴스 공장"))
        cost = ledger.read("cost_ledger", self.d["ledger"])
        self.assertTrue(cost[-1]["rehearsal"] is True)
        self.assertFalse(cost[0]["rehearsal"])
        self.assertEqual([x for x in ledger.read("check_ledger", self.d["ledger"]) if x["gate"] == "ALL"], [])
        self.assertEqual(self.alerts, [])

    def test_rehearsal_does_not_relax_other_gates(self):
        with self._evidence_none():
            r = self.go(rehearsal=True, out_root=os.path.join(self.tmp.name, "rehearsal"), classify=bad_classify)
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        with self._evidence_none():
            r = self.go(rehearsal=True, out_root=os.path.join(self.tmp.name, "rehearsal"), generate=gen_wrong_number)
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"))

    def test_rehearsal_default_dir_and_no_g5_poison(self):
        self.assertTrue(R.REHEARSAL_DIR.replace("\\", "/").endswith("data/rehearsal"))
        with self._evidence_none():
            self.go(rehearsal=True, out_root=os.path.join(self.tmp.name, "rehearsal"))
        self.alerts.clear()
        self.assertEqual(self.go()["status"], "ok")   # 리허설이 같은 키워드의 실제 실행을 G5 로 막지 않는다

    def test_sources_come_from_research_sources_for_run(self):
        calls = []
        from cardnews import research
        real = research.sources_for_run

        def spy(rrec, ledger_dir=None):
            calls.append(rrec.get("run_id"))
            return real(rrec, ledger_dir)
        with mock.patch("cardnews.research.sources_for_run", side_effect=spy):
            r = self.go()
        self.assertEqual(r["status"], "ok", r["reason"])
        self.assertEqual(len(calls), 1)

    def test_caption_source_lines_use_portal_label_for_unknown_org(self):
        doc_c = ("<html><body><p>정책브리핑 재게시 기사입니다. 기초연금 안내를 쉽게 풀어 설명합니다. 기초연금 수급 연령은 만 65세 이상입니다. "
                 "자세한 내용은 담당 부처 누리집을 참고하세요.</p></body></html>").encode("utf-8")
        docs = [("https://www.korea.kr/briefing/a", "korea.kr", doc_c, False), ("https://www.korea.kr/news/x", "행정안전부", DOC_A, True),
                ("https://www.mohw.go.kr/b", "보건복지부", DOC_B, True)]
        disc = lambda kw: [{"url": u, "org": o, "org_known": k, "published": "2026-11-10",  # noqa: E731
                            "content": c, "title": f"{o} {kw} 안내"} for u, o, c, k in docs]
        r = self.go(fetchers=self.fx(discover=disc))
        self.assertEqual(r["status"], "ok", r["reason"])        # 기관 미상(포털)은 표기만 바뀌고 G1·G2 는 그대로 통과
        cap = _rd(os.path.join(r["out_dir"], "캡션.txt"))
        lines = [ln for ln in cap.splitlines() if ln.startswith("출처:")]
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[-1].startswith("출처: 정책브리핑(korea.kr) https://www.korea.kr/briefing/a"), lines)
        self.assertNotIn("출처: korea.kr", cap)
        self.assertTrue(all(g["pass"] for g in json.loads(_rd(os.path.join(r["out_dir"], "manifest.json")))["gates"]))

    # ---- G2 보류 시 1회 재작성 ----
    def test_g2_fail_then_rewrite_succeeds(self):
        prompts = []

        def gen(prompt):
            prompts.append(prompt)
            return gen_wrong_number(prompt) if len(prompts) == 1 else gen_ok(prompt)
        r = self.go(generate=gen)
        self.assertEqual(r["status"], "ok", r["reason"])
        self.assertEqual(len(prompts), 2)
        self.assertNotIn("검증(G2)에서 보류", prompts[0])
        self.assertIn("검증(G2)에서 보류", prompts[1])                 # verify 사유가 피드백으로 들어감
        self.assertIn("99만원", prompts[1])
        self.assertIn("원문 숫자만 단위와 함께 쓰라", prompts[1])
        self.assertEqual(r["cost"]["attempts"], 2)
        c = ledger.read("cost_ledger", self.d["ledger"])[0]
        self.assertEqual(c["attempts"], 2)
        self.assertEqual(c["anthropic"]["calls"], 3)                   # compose 2 + guard 분류 1
        names = [g["gate"] for g in r["gates"]]
        self.assertIn("G2(1차 — 재작성됨)", names)
        self.assertEqual(self.alerts, [])                              # 재작성 성공이면 알림 없음
        self.assertTrue(all(g["pass"] for g in r["gates"] if "재작성됨" not in g["gate"]))

    def test_g2_fails_twice_held_after_one_rewrite(self):
        n = []

        def gen(prompt):
            n.append(1)
            return gen_wrong_number(prompt)
        r = self.go(generate=gen)
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"))
        self.assertEqual(len(n), 2)                                    # 최초 1 + 재작성 1, 그 이상 없음
        self.assertIn("재작성 후에도 실패", r["reason"])
        self.assertEqual(r["cost"]["attempts"], 2)
        self.assertEqual(len(self.alerts), 1)
        self.assertFalse(os.path.exists(self.out_account_dir()))

    def test_g3_fail_is_not_rewritten(self):
        n = []

        def gen(prompt):
            n.append(1)
            return gen_ok(prompt)
        r = self.go(generate=gen, classify=bad_classify)
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertEqual(len(n), 1)                                    # 금칙은 재작성(우회 시도) 없음
        self.assertEqual(r["cost"]["attempts"], 1)

    def test_g1_fail_is_not_rewritten(self):
        n = []

        def gen(prompt):
            n.append(1)
            return gen_ok(prompt)
        with mock.patch("cardnews.verify.run", return_value={"pass": False, "G1": (False, "공식 기관 1곳"), "G2": (False, "G1 실패로 대조 생략"), "detail": {}}):
            r = self.go(generate=gen)
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"))
        self.assertEqual(len(n), 1)
        self.assertNotIn("재작성 후에도", r["reason"])

    def test_cost_ledger_attempts_single_run(self):
        self.go()
        self.assertEqual(ledger.read("cost_ledger", self.d["ledger"])[0]["attempts"], 1)

    # ---- R7b: 다시 쓰기 전 1차 초안 감사 기록 ----
    def _audit_dirs(self, root):
        p = os.path.join(root, "_attempts", TODAY.isoformat())
        return [os.path.join(p, n) for n in sorted(os.listdir(p))] if os.path.isdir(p) else []

    def test_rewrite_leaves_attempt1_audit_record(self):
        n = []

        def gen(prompt):
            n.append(1)
            return gen_wrong_number(prompt) if len(n) == 1 else gen_ok(prompt)
        r = self.go(generate=gen)
        self.assertEqual(r["status"], "ok", r["reason"])
        dirs = self._audit_dirs(self.d["hold"])
        self.assertEqual(len(dirs), 1)
        a = json.load(open(os.path.join(dirs[0], "draft_attempt1.json"), encoding="utf-8"))
        self.assertEqual((a["attempt"], a["gate"]), (1, "G2"))
        self.assertTrue(a["reason"])
        self.assertEqual(len(a["draft"]["cards"]), 5)
        self.assertIn("99만원", json.dumps(a["draft"], ensure_ascii=False))
        rows = [x for x in ledger.read("run_ledger", self.d["ledger"]) if x.get("attempt") == 1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gate"], "G2")
        self.assertEqual(rows[0]["reason"], " ".join(a["reason"].split("\n"))[:300])
        self.assertEqual(self.holds(), [])                       # 보류함 목록에는 섞이지 않음
        self.assertTrue(all(g["pass"] for g in r["gates"] if "재작성됨" not in g["gate"]))  # 재작성본은 전 관문 재검사

    def test_no_audit_record_when_first_attempt_passes(self):
        self.go()
        self.assertEqual(self._audit_dirs(self.d["hold"]), [])
        self.assertEqual([x for x in ledger.read("run_ledger", self.d["ledger"]) if x.get("attempt") == 1], [])

    def test_audit_record_kept_when_rewrite_also_fails(self):
        r = self.go(generate=gen_wrong_number)
        self.assertEqual(r["status"], "held")
        self.assertEqual(len(self._audit_dirs(self.d["hold"])), 1)
        self.assertEqual(len(self.holds()), 1)

    def test_rehearsal_audit_goes_to_rehearsal_folder(self):
        n = []

        def gen(prompt):
            n.append(1)
            return gen_wrong_number(prompt) if len(n) == 1 else gen_ok(prompt)
        r = self.go(generate=gen, rehearsal=True)
        self.assertEqual(r["status"], "ok", r["reason"])
        self.assertEqual(len(self._audit_dirs(self.d["out"])), 1)
        self.assertEqual(self._audit_dirs(self.d["hold"]), [])

    # ---- T-SW1: 좌석 작성 방식 ----
    def _write(self, name, obj_or_text, raw=False):
        """raw=False 이면 초안 JSON 에 빠진 kw·author_surface 기본값을 채운다(검사 통과용). raw=True 는 있는 그대로."""
        p = os.path.join(self.d["drafts"], TODAY.isoformat(), name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not raw and name.endswith(".json") and ".g3." not in name:
            obj = json.loads(obj_or_text) if isinstance(obj_or_text, str) else dict(obj_or_text)
            obj.setdefault("kw", "기초연금")
            obj.setdefault("author_surface", "worker-1")
            obj.setdefault("used_sources", list(USED_DEFAULT))
            obj_or_text = obj
        with open(p, "w", encoding="utf-8") as f:
            f.write(obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text, ensure_ascii=False))
        return p

    def _sha(self, p):
        from cardnews import guard
        return guard.file_sha256(p)

    def _seat(self, acc=None, **kw):
        return R.run(acc or self.acc, BANNED, today=TODAY, now=NOW, fetchers=kw.pop("fetchers", None) or self.fx(), notify=lambda *a: self.alerts.append(a),
                     ledger_dir=self.d["ledger"], out_root=self.d["out"], hold_root=self.d["hold"], sources_dir=self.d["sources"],
                     stop_file=self.stop, bg_manifest=[], drafts_dir=self.d["drafts"], **kw)

    def _verdict(self, draft_path, **over):
        v = {"ok": True, "category": "none", "reviewer_surface": "reviewer-gemini", "draft_sha256": self._sha(draft_path)}
        v.update(over)
        return self._write("test.g3.json", v)

    def test_metered_off_by_default_compose_and_classify(self):
        from cardnews import compose, guard
        env = {k: v for k, v in os.environ.items() if k != "CARDNEWS_ALLOW_METERED_API"}
        env["ANTHROPIC_API_KEY"] = "x"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch("requests.post") as post:
            with self.assertRaises(compose.ComposeError):
                compose.default_generate("p")
            ok, cat, why = guard.default_classify("글")
            self.assertFalse(ok)
            self.assertEqual(cat, "classifier_error")
            post.assert_not_called()

    def test_draft_file_passes_with_reviewer_verdict(self):
        p = self._write("test.json", gen_ok(""))
        self._verdict(p)
        r = self._seat()
        self.assertEqual(r["status"], "ok", r["reason"])
        self.assertEqual(r["cost"]["anthropic"]["calls"], 0)
        g3 = [g for g in r["gates"] if g["gate"] == "G3"][0]
        self.assertTrue(g3["pass"])
        self.assertIn("분류 통과", g3["reason"])

    def test_missing_draft_is_skipped_with_one_alert(self):
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("skipped", "draft"))
        self.assertEqual(len(self.alerts), 1)
        self.assertEqual(self.holds(), [])
        self.assertFalse(os.path.exists(self.out_account_dir()))

    def test_explicit_draft_file_path(self):
        p = self._write("other.json", gen_ok(""))
        self._write("other.g3.json", {"ok": True, "category": "none", "reviewer_surface": "r", "draft_sha256": self._sha(p)})
        r = self._seat(draft_file=p)
        self.assertEqual(r["status"], "ok", r["reason"])

    def test_g3_verdict_missing_holds(self):
        self._write("test.json", gen_ok(""))
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("판정 파일 없음", r["reason"])

    def test_g3_verdict_sha_mismatch_holds(self):
        p = self._write("test.json", gen_ok(""))
        self._verdict(p, draft_sha256="0" * 64)
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("draft_sha256", r["reason"])

    def test_g3_verdict_category_not_none_or_not_true_holds(self):
        p = self._write("test.json", gen_ok(""))
        for over in ({"category": "adult", "ok": False}, {"ok": "true"}, {"category": "none", "ok": False}, {"reviewer_surface": ""}):
            self._verdict(p, **over)
            self.assertEqual(self._seat()["status"], "held", over)

    def test_g3_reviewer_same_as_author_holds(self):
        d = json.loads(gen_ok(""))
        d["author_surface"] = "worker-1"
        p = self._write("test.json", d)
        self._verdict(p, reviewer_surface="worker-1")
        r = self._seat()
        self.assertEqual(r["status"], "held")
        self.assertIn("같음", r["reason"])

    def test_keyword_g3_still_runs_first(self):
        d = json.loads(gen_ok(""))
        d["caption_body"] = "무조건 오르는 종목 알려드립니다 리딩방"
        p = self._write("test.json", d)
        self._verdict(p)
        r = self._seat()
        self.assertEqual(r["status"], "held")
        self.assertIn("키워드 금칙", r["reason"])

    def test_g2_fail_without_retry_file_holds_with_hint(self):
        p = self._write("test.json", gen_wrong_number(""))
        self._verdict(p)
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"))
        self.assertIn("test.retry.json", r["reason"])
        self.assertEqual(len(self.alerts), 1)

    def test_g2_fail_then_retry_file_rechecked_once(self):
        self._write("test.json", gen_wrong_number(""))
        rp = self._write("test.retry.json", gen_ok(""))
        self._verdict(rp)            # 판정은 최종(재작성본) 초안 기준
        r = self._seat()
        self.assertEqual(r["status"], "ok", r["reason"])
        self.assertEqual(r["cost"]["attempts"], 2)
        self.assertTrue(any(g["gate"] == "G2(1차 — 재작성됨)" for g in r["gates"]))
        dirs = os.path.join(self.d["hold"], "_attempts", TODAY.isoformat())
        self.assertTrue(os.path.exists(os.path.join(dirs, os.listdir(dirs)[0], "draft_attempt1.json")))

    def test_retry_file_also_failing_holds_no_third_try(self):
        self._write("test.json", gen_wrong_number(""))
        self._write("test.retry.json", gen_wrong_number(""))
        r = self._seat()
        self.assertEqual(r["status"], "held")
        self.assertIn("재작성 후에도 실패", r["reason"])

    def test_verdict_for_first_draft_does_not_cover_retry(self):
        p = self._write("test.json", gen_wrong_number(""))
        self._write("test.retry.json", gen_ok(""))
        self._verdict(p)             # 1차 초안 판정 → 재작성본과 sha 다름
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))

    def test_kw_mismatch_in_draft_holds(self):
        d = json.loads(gen_ok(""))
        d["kw"] = "전혀다른주제"
        p = self._write("test.json", d)
        self._verdict(p)
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "compose"))

    def test_invest_disclaimer_required_in_every_card(self):
        msg = "투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다."
        acc = dict(self.acc, required_disclaimer=msg)
        p = self._write("test.json", gen_ok(""))
        self._verdict(p)
        r = self._seat(acc=acc)
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("필수 고지 문구 없음", r["reason"])
        d = json.loads(gen_ok(""))
        for c in d["cards"]:
            c["body"] += " " + msg
        p = self._write("test.json", d)
        self._verdict(p)
        self.assertEqual(self._seat(acc=acc)["status"], "ok")

    def test_one_card_missing_disclaimer_holds(self):
        from cardnews import guard
        msg = "투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다."
        d = {"cards": [{"title": "t", "body": f"본문 {msg}"} for _ in range(5)], "caption": "x\nAI로 제작", "sources": [], "hashtags": []}
        d["cards"][3]["body"] = "본문만"
        ok, why = guard.g7(d, required_disclaimer=msg)
        self.assertFalse(ok)
        self.assertIn("카드4 필수 고지 문구 없음", why)

    def test_report_marks_audit_rows(self):
        ledger.append("run_ledger", {"date": TODAY.isoformat(), "account_id": "test", "attempt": 1, "gate": "G2", "reason": "x"}, self.d["ledger"])
        os.makedirs(os.path.join(self.d["out"], TODAY.isoformat()), exist_ok=True)
        path = report.build(TODAY.isoformat(), self.d["out"], self.d["hold"], self.d["ledger"])
        html = _rd(path)
        self.assertIn("재작성 1차(G2)", html)
        self.assertNotIn("<td>None</td>", html)

    # ---- T-SW1b: 리뷰9 ----
    def _held_compose(self, r, needle):
        self.assertEqual((r["status"], r["stage"]), ("held", "compose"), r["reason"])
        self.assertIn(needle, r["reason"])

    def test_neg_author_surface_missing_holds(self):
        d = json.loads(gen_ok(""))
        d["kw"] = "기초연금"
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        self._held_compose(self._seat(), "author_surface")

    def test_neg_author_surface_blank_holds(self):
        p = self._write("test.json", dict(json.loads(gen_ok("")), author_surface="  "))
        self._verdict(p)
        self._held_compose(self._seat(), "author_surface")

    def test_neg_kw_missing_holds(self):
        d = json.loads(gen_ok(""))
        d["author_surface"] = "worker-1"
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        self._held_compose(self._seat(), "kw")

    def test_neg_code_fence_holds(self):
        d = dict(json.loads(gen_ok("")), kw="기초연금", author_surface="worker-1")
        p = self._write("test.json", "```json\n" + json.dumps(d, ensure_ascii=False) + "\n```", raw=True)
        self._verdict(p)
        self._held_compose(self._seat(), "순수 JSON")

    def test_neg_reviewer_case_difference_holds(self):
        p = self._write("test.json", dict(json.loads(gen_ok("")), author_surface="Worker-2"))
        self._verdict(p, reviewer_surface="worker-2")
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("같음", r["reason"])

    def test_neg_reviewer_prefix_difference_holds(self):
        p = self._write("test.json", dict(json.loads(gen_ok("")), author_surface="154"))
        self._verdict(p, reviewer_surface="surface:154")
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "guard"))
        self.assertIn("같음", r["reason"])

    def test_norm_surface(self):
        from cardnews import guard
        self.assertEqual(guard.norm_surface(" Surface:154 "), "154")
        self.assertEqual(guard.norm_surface("Worker-2"), "worker-2")
        self.assertEqual(guard.norm_surface(None), "")

    def test_skipped_alert_once_per_day_and_account(self):
        self._seat()
        self._seat()
        self.assertEqual(len(self.alerts), 1)
        rows = [x for x in ledger.read("run_ledger", self.d["ledger"]) if x.get("status") == "skipped"]
        self.assertEqual(len(rows), 2)

    def test_g5_future_tolerance_plus_two_days(self):
        from cardnews import guard
        today = TODAY

        def hit(days_ahead):
            d = {"account_id": "fx", "kw": "기초연금", "cards": [{"title": "가", "body": "나"}] * 5, "caption": "x"}
            led = os.path.join(self.tmp.name, f"led{days_ahead}")
            ledger.append("check_ledger", {"gate": "ALL", "pass": True, "account_id": "fx", "kw": "기초연금", "titles": [], "sent_hashes": [],
                                           "ts": (today + dt.timedelta(days=days_ahead)).isoformat() + "T10:00:00"}, led)
            return not guard.g5(d, led, today)[0]
        self.assertTrue(hit(2))
        self.assertFalse(hit(3))

    # ---- T-SRC1: 실제로 쓴 출처만 ----
    def _held_c(self, r, needle):
        self.assertEqual((r["status"], r["stage"]), ("held", "compose"), r["reason"])
        self.assertIn(needle, r["reason"])

    def _draft_with(self, **over):
        d = dict(json.loads(gen_ok("")), kw="기초연금", author_surface="worker-1")
        d.update(over)
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        return p

    def test_src_used_sources_missing_holds(self):
        d = dict(json.loads(gen_ok("")), kw="기초연금", author_surface="worker-1")
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        self._held_c(self._seat(), "used_sources 없음")

    def test_src_used_sources_empty_or_wrong_type_holds(self):
        for bad in ([], "https://www.mohw.go.kr/b", [""], [1]):
            self._draft_with(used_sources=bad)
            self._held_c(self._seat(), "used_sources")

    def test_src_unknown_url_holds(self):
        self._draft_with(used_sources=["https://www.mohw.go.kr/b", "https://evil.example/x"])
        self._held_c(self._seat(), "이번 실행 출처가 아닌 url")

    def test_src_duplicate_url_holds(self):
        self._draft_with(used_sources=["https://www.mohw.go.kr/b", "https://www.mohw.go.kr/b"])
        self._held_c(self._seat(), "중복")

    def test_src_two_orgs_in_run_but_one_used_holds_g1(self):
        self._draft_with(used_sources=["https://www.mohw.go.kr/b"])
        r = self._seat()
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"), r["reason"])
        self.assertIn("G1", r["reason"])

    def test_src_both_used_passes_and_caption_lists_only_used(self):
        self._draft_with(used_sources=list(USED_DEFAULT))
        r = self._seat()
        self.assertEqual(r["status"], "ok", r["reason"])
        cap = _rd(os.path.join(r["out_dir"], "캡션.txt"))
        lines = [x for x in cap.splitlines() if x.startswith("출처:")]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("mohw.go.kr/b" in x for x in lines) and any("korea.kr/news/a" in x for x in lines))

    def test_src_number_only_in_unused_source_holds_g2(self):
        # 3번째 출처(미사용)에만 '99만원' 이 있고 초안이 그 숫자를 쓰면, 쓰지 않은 출처 덕에 통과하면 안 된다
        extra = "<html><body><p>국민연금공단 안내. 기초연금 월 99만원 지급.</p></body></html>".encode("utf-8")
        docs = [("https://www.korea.kr/news/a", "행정안전부", DOC_A), ("https://www.mohw.go.kr/b", "보건복지부", DOC_B),
                ("https://www.nps.or.kr/c", "국민연금공단", extra)]
        d = json.loads(gen_wrong_number(""))
        d.update(kw="기초연금", author_surface="worker-1", used_sources=list(USED_DEFAULT))
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        r = self._seat(fetchers=self.fx(docs=docs))
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"), r["reason"])
        self.assertIn("G2", r["reason"])

    def test_src_retry_file_same_rule(self):
        self._write("test.json", gen_wrong_number(""))
        rd = dict(json.loads(gen_ok("")), kw="기초연금", author_surface="worker-1")   # used_sources 없음
        rp = self._write("test.retry.json", json.dumps(rd, ensure_ascii=False), raw=True)
        self._verdict(rp)
        self._held_c(self._seat(), "used_sources 없음")

    # ---- T-SRC2 ----
    def test_src2_declared_org_without_numbers_holds_g1(self):
        docs = [("https://www.korea.kr/news/a", "행정안전부", "<html><body><p>행정안전부 안내 기초연금 청사 안내.</p></body></html>".encode("utf-8")),
                ("https://www.mohw.go.kr/b", "보건복지부", DOC_B)]
        self._draft_with(used_sources=["https://www.korea.kr/news/a", "https://www.mohw.go.kr/b"])
        r = self._seat(fetchers=self.fx(docs=docs))
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"), r["reason"])
        self.assertIn("선언했지만 내용에 쓰이지 않은 기관: 행정안전부", r["reason"])

    def test_src2_unknown_url_message_has_closest_candidate(self):
        self._draft_with(used_sources=["https://www.mohw.go.kr/bb"])
        r = self._seat()
        self._held_c(r, "그대로 복사")
        self.assertIn("가장 가까운 후보 'https://www.mohw.go.kr/b'", r["reason"])

    def test_src2_caption_body_missing_or_hashtags_not_list_holds(self):
        self._draft_with(used_sources=list(USED_DEFAULT), caption_body="")
        self._held_c(self._seat(), "caption_body")
        self._draft_with(used_sources=list(USED_DEFAULT), hashtags="기초연금")
        self._held_c(self._seat(), "hashtags")

    # ---- T-SRC4: 가짜 없는 common_tokens(임시 source_cache, 상대경로 인덱스) ----
    def _tmp_cache(self, n=60):
        root = os.path.join(self.tmp.name, "source_cache")
        os.makedirs(os.path.join(root, "files"), exist_ok=True)
        lines = []
        for k in range(n):
            path = os.path.join(root, "files", f"f{k}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"<html><body>일반 안내 만 65세 이상, 임시기준 9876만 원, 고유 {3000 + k}건</body></html>")
            lines.append(json.dumps({"url": f"https://www.korea.kr/f{k}", "saved_path": f"files/f{k}.html"}))   # 상대경로
        idx = os.path.join(root, "index.jsonl")
        with open(idx, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return idx

    def _real_common_run(self, body, idx, docs=None):
        from cardnews import verify as V
        d = dict(json.loads(gen_ok("")), kw="기초연금", author_surface="worker-1", used_sources=list(USED_DEFAULT))
        d["cards"][1]["body"] = body
        p = self._write("test.json", json.dumps(d, ensure_ascii=False), raw=True)
        self._verdict(p)
        V._DF_CACHE.clear()
        with mock.patch("cardnews.verify.common_tokens", _REAL_COMMON), mock.patch.object(V, "CACHE_INDEX", idx):
            return self._seat(fetchers=self.fx(docs=docs) if docs else None)

    def test_src4_real_common_only_common_number_holds_g1(self):
        # '9876만 원' 은 임시 캐시 60건 전부에만 있고 실제 캐시에는 없는 값 → 실제 캐시를 읽었다면 구별 숫자로 통과했을 것(CACHE_INDEX 대체가 실제로 쓰이는지 구별)
        from cardnews import verify as V
        idx = self._tmp_cache()
        a = "<html><body><p>행정안전부 기초연금 안내. 기초연금 임시기준 9876만 원.</p></body></html>".encode("utf-8")
        b = "<html><body><p>보건복지부 보도자료. 기초연금 임시기준 9876만 원입니다.</p></body></html>".encode("utf-8")
        docs = [("https://www.korea.kr/news/a", "행정안전부", a), ("https://www.mohw.go.kr/b", "보건복지부", b)]
        self.assertEqual(_REAL_COMMON(idx)[1], 60)                    # 임시 캐시에서 60건을 읽었다
        self.assertIn("9876만원", _REAL_COMMON(idx)[0])              # 임시 캐시에서만 흔한 토큰
        self.assertNotIn("9876만원", _REAL_COMMON()[0])               # 실제 캐시에서는 흔하지 않음(없음)
        r = self._real_common_run("기초연금 임시기준은 9876만 원입니다", idx, docs=docs)
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"), r["reason"])
        self.assertIn("선언했지만 내용에 쓰이지 않은 기관", r["reason"])

    def test_src4_real_common_distinctive_number_passes(self):
        idx = self._tmp_cache()
        a = "<html><body><p>행정안전부 기초연금 안내. 기초연금 대상 약 136만 명.</p></body></html>".encode("utf-8")
        b = "<html><body><p>보건복지부 보도자료. 기초연금 대상은 약 136만 명입니다. 서류는 신분증이다.</p></body></html>".encode("utf-8")
        docs = [("https://www.korea.kr/news/a", "행정안전부", a), ("https://www.mohw.go.kr/b", "보건복지부", b)]
        r = self._real_common_run("기초연금 대상은 약 136만 명입니다", idx, docs=docs)
        self.assertEqual(r["status"], "ok", r["reason"])

    def test_src4_missing_cache_index_holds_fail_closed(self):
        r = self._real_common_run("기초연금은 만 65세 이상이 대상입니다", os.path.join(self.tmp.name, "no", "index.jsonl"))
        self.assertEqual((r["status"], r["stage"]), ("held", "verify"), r["reason"])
        self.assertIn("기여 판정 불가", r["reason"])


if __name__ == "__main__":
    unittest.main()
