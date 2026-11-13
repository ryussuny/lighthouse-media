# -*- coding: utf-8 -*-
"""T-09 run — 1단계 끝에서 끝: 게시 단계 없음(결과 폴더까지).

흐름(각 단계 앞에서 config.run_gate 재확인 — STOP 파일·paused 이면 다음 단계 전에 멈추고 status="stopped"):
  trends.run → research.run → compose → verify(G1·G2) → guard(G3·G4·G5·G7) → design → G4·G7 재확인(실제 PNG 실측)
  → caption 점검 → data/out/<날짜>/<계정>/ (card_1~5.png · 캡션.txt · manifest.json · design_manifest.json)
어느 관문이든 실패 → data/hold/<날짜>/ 에 사본·사유, 알림 1회, 결과 폴더에는 안 넣음.
research 가 evidence="none" 으로 표시했거나 trends 점수에서 근거(evidence)가 없는 주제는 보류(지표 근거 없는 주제는 내지 않음).
비용: 실행마다 cost_ledger 한 줄(Anthropic 호출 수·토큰, Higgsfield 0 — 배경은 data/backgrounds 라이브러리 재사용).
기록: run_ledger(실행 한 줄) · check_ledger(관문별) · 결과 HTML(report.build).
CLI: py -m cardnews.run --account test   (게시 개념 자체가 없음)

status: ok | held | stopped | no_candidates | error
"""
import datetime as dt
import json
import os
import hashlib
import shutil

from . import caption as CAP, compose, config as C, design, guard, ledger, report, research, trends, verify

ROOT = C.ROOT
OUT_DIR = os.path.join(ROOT, "data", "out")
REHEARSAL_DIR = os.path.join(ROOT, "data", "rehearsal")
REHEARSAL_MARK = "리허설 — 게시 불가"
HOLD_DIR = os.path.join(ROOT, "data", "hold")
DRAFTS_DIR = os.path.join(ROOT, "data", "drafts")


class _Done(Exception):
    def __init__(self, result):
        self.result = result


def _usage_snapshot():
    return dict(compose.USAGE), dict(guard.USAGE)


def run(acc, banned, today=None, now=None, fetchers=None, generate=None, classify=None, notify=None,
        ledger_dir=None, out_root=None, hold_root=None, sources_dir=None, stop_file=None, bg_manifest=None, rehearsal=False,
        draft_file=None, drafts_dir=None):
    """rehearsal=True(compose~design 실경로 시험용): evidence=none 보류 규칙만 건너뛴다(G1~G7 은 그대로 전부 적용).
    결과는 data/rehearsal/<날짜>/ 에, manifest·캡션.txt·HTML 맨 위에 '리허설 — 게시 불가' 표시, cost/run_ledger 에 rehearsal=true.
    G5 용 ALL 행은 남기지 않는다(리허설이 실제 실행을 중복으로 막지 않게).
    좌석 작성 방식(종량 API 꺼짐이 기본): draft_file(또는 기본 data/drafts/<날짜>/<계정>.json) 의 초안을 받아 G1~G7 그대로 돈다.
      파일 없으면 status=skipped + 알림 1회. G3 분류는 <계정>.g3.json(리뷰어 판정), G2 만 실패하면 <계정>.retry.json 으로 1회 재검사.
      generate 를 주입하거나 CARDNEWS_ALLOW_METERED_API=1 이면(draft_file 없을 때) 예전처럼 compose 가 글을 쓴다.
    fetchers: {"trends": {...trends.run fetchers}, "research": {"discover": f(kw)}} (시험용 주입, 없으면 실제 수집)."""
    now = now or dt.datetime.now()
    today = today or now.date()
    day = today.isoformat()
    out_root, hold_root = out_root or (REHEARSAL_DIR if rehearsal else OUT_DIR), hold_root or HOLD_DIR
    if notify is None:
        from . import alert
        notify = alert.send
    fetchers = fetchers or {}
    stop_kw = {"stop_file": stop_file} if stop_file else {}
    c0, g0 = _usage_snapshot()
    inj = {"calls": 0}
    gates, state = [], {"kw": None, "stage": "start", "attempts": 1}

    def count(fn):
        def w(*a, **k):
            inj["calls"] += 1
            return fn(*a, **k)
        return w
    draft_mode = bool(draft_file) or (generate is None and not C.metered_allowed())
    if draft_mode:
        draft_path = draft_file or os.path.join(drafts_dir or DRAFTS_DIR, day, f"{acc['account_id']}.json")
        base = draft_path[:-5] if draft_path.lower().endswith(".json") else draft_path
        g3_path, retry_path = base + ".g3.json", base + ".retry.json"
        state["draft_sha"], state["author"] = None, None
        gen = None
        clf = classify or (lambda text: guard.file_classifier(g3_path, state["draft_sha"], state["author"])(text))
    else:
        gen = count(generate) if generate else compose.default_generate
        clf = count(classify) if classify else guard.default_classify

    def finish(status, stage, reason, hold_path=None, out_dir=None):
        c1, g1 = _usage_snapshot()
        cost = {"anthropic": {"calls": inj["calls"] + (c1["calls"] - c0["calls"]) + (g1["calls"] - g0["calls"]),
                              "input_tokens": (c1["input_tokens"] - c0["input_tokens"]) + (g1["input_tokens"] - g0["input_tokens"]),
                              "output_tokens": (c1["output_tokens"] - c0["output_tokens"]) + (g1["output_tokens"] - g0["output_tokens"])},
                "attempts": state["attempts"],
                "higgsfield": {"calls": 0, "credits": 0, "note": "배경은 data/backgrounds 라이브러리 재사용"}}
        ledger.append("cost_ledger", {"date": day, "account_id": acc["account_id"], "kw": state["kw"], "status": status, "rehearsal": rehearsal, **cost}, ledger_dir)
        ledger.append("run_ledger", {"date": day, "account_id": acc["account_id"], "kw": state["kw"], "status": status,
                                     "stage": stage, "reason": reason, "hold_path": hold_path, "out_dir": out_dir,
                                     "rehearsal": rehearsal}, ledger_dir)
        html_path = None
        try:
            html_path = report.build(day, out_root, hold_root, ledger_dir, rehearsal=rehearsal)
        except Exception as e:  # noqa: BLE001 — 보고서 실패가 실행 결과를 가리지 않게
            reason += f" (보고서 실패: {e!r})"[:120]
        return {"status": status, "stage": stage, "reason": reason, "kw": state["kw"], "hold_path": hold_path,
                "out_dir": out_dir, "html": html_path, "cost": cost, "gates": gates}

    def checkgate(stage):
        state["stage"] = stage
        ok, why = C.run_gate(acc, **stop_kw)
        if not ok:
            raise _Done(finish("stopped", stage, why))

    def hold(stage, draft, results, reason):
        d = draft or {"account_id": acc["account_id"], "kw": state["kw"]}
        path = guard._hold(d, results, hold_root, now)
        notify("warn", f"[{acc['account_id']}] 보류 — {state['kw']}", f"{stage}: {reason}"[:500])
        raise _Done(finish("held", stage, reason, hold_path=path))

    def row(gate, ok, reason, draft):
        gates.append({"gate": gate, "pass": ok, "reason": reason})
        ledger.append("check_ledger", {"gate": gate, "pass": ok, "reason": reason, "account_id": acc["account_id"],
                                       "kw": draft.get("kw") if draft else state["kw"]}, ledger_dir)

    try:
        # 1) trends
        checkgate("trends")
        trec = trends.run(acc, banned, fetchers=fetchers.get("trends"), today=today, ledger_dir=ledger_dir,
                          notify=notify, gate=False)
        if trec.get("status") not in ("ok", "ok_single_indicator"):
            raise _Done(finish("no_candidates", "trends", f"{trec.get('status')}: {trec.get('reason', '')}"))
        # 2) research
        checkgate("research")
        rrec = research.run(acc, today=today, fetchers=fetchers.get("research"), ledger_dir=ledger_dir,
                            sources_dir=sources_dir, notify=notify)
        state["kw"] = rrec.get("kw")
        if rrec.get("status") != "ok":
            raise _Done(finish("held", "research", rrec.get("reason", "research 보류"), hold_path=None))  # research 가 이미 알림 1회
        sc = {s["kw"]: s for s in trec.get("scores", [])}.get(state["kw"])
        if not rehearsal and (rrec.get("evidence") == "none" or (sc is not None and sc.get("evidence") is False)):
            hold("research", None, [("EVIDENCE", False, "지표 근거 없는 주제(evidence=none)")], "지표 근거 없는 주제(evidence=none)")
        sources = research.sources_for_run(rrec, ledger_dir)   # 이번 실행(run_id) 몫만
        # 3~4) compose → verify G1·G2. G2 만 실패하면 verify 사유를 피드백으로 넘겨 같은 출처로 딱 1회 다시 쓴다(전 관문 처음부터).
        #      G1 실패·compose 실패는 재작성 없이 바로 보류. (G3 는 아래 guard — 금칙이라 재작성하지 않는다.)
        feedback = None
        if draft_mode and not os.path.exists(draft_path):
            state["stage"] = "draft"
            why = f"초안 파일 없음: {draft_path} (키워드 {state['kw']!r}, 출처 {len(sources)}건) — 좌석이 쓰면 다시 실행"
            already = any(x.get("date") == day and x.get("account_id") == acc["account_id"] and x.get("status") == "skipped"
                          for x in ledger.read("run_ledger", ledger_dir))
            if not already:   # 같은 날·같은 계정 알림은 1회만
                notify("warn", f"[{acc['account_id']}] 초안 없음 — 오늘 건너뜀", why[:500])
            raise _Done(finish("skipped", "draft", why))
        for attempt in (1, 2):
            state["attempts"] = attempt
            checkgate("compose")
            try:
                if draft_mode:
                    src_path = draft_path if attempt == 1 else retry_path
                    with open(src_path, "rb") as f:
                        raw_bytes = f.read()
                    state["draft_sha"] = hashlib.sha256(raw_bytes).hexdigest()
                    try:
                        raw_text = raw_bytes.decode("utf-8")
                        meta = json.loads(raw_text)   # 순수 JSON 만(코드펜스·머리말 금지 — 검사가 조용히 꺼지는 길을 막는다)
                    except (UnicodeDecodeError, json.JSONDecodeError) as e:
                        raise compose.ComposeError(f"초안이 순수 JSON 이 아님(코드펜스·설명 금지): {e}") from e
                    if not isinstance(meta, dict):
                        raise compose.ComposeError("초안 최상위가 JSON 객체가 아님")
                    state["author"] = meta.get("author_surface")
                    if not guard.norm_surface(state["author"]):
                        raise compose.ComposeError("초안에 author_surface 없음/빈 값")
                    if not str(meta.get("kw") or "").strip():
                        raise compose.ComposeError("초안에 kw 없음/빈 값")
                    if meta["kw"] != state["kw"]:
                        raise compose.ComposeError(f"초안 kw {meta['kw']!r} 가 오늘 주제 {state['kw']!r} 와 다름")
                    draft = compose.compose(state["kw"], sources, account_id=acc["account_id"], generate=lambda p: raw_text,
                                            today=today)
                else:
                    draft = compose.compose(state["kw"], sources, account_id=acc["account_id"], generate=gen, today=today,
                                            feedback=feedback)
            except (compose.ComposeError, OSError) as e:
                hold("compose", None, [("COMPOSE", False, str(e))], f"글 생성 실패({attempt}차): {e}")
            checkgate("verify")
            v = verify.run(draft, sources, ledger_dir)
            if v["pass"]:
                gates.append({"gate": "G1", "pass": v["G1"][0], "reason": v["G1"][1]})
                gates.append({"gate": "G2", "pass": v["G2"][0], "reason": v["G2"][1]})
                break
            if v["G1"][0] and attempt == 1 and (not draft_mode or os.path.exists(retry_path)):   # G2 만 실패 → 재작성 1회
                gates.append({"gate": "G2(1차 — 재작성됨)", "pass": False, "reason": v["G2"][1]})
                # 감사 기록: 다시 쓰기 전에 1차 초안 + 실패 사유를 남긴다(보류함 목록과 섞이지 않게 _attempts/ 아래)
                audit = os.path.join(out_root if rehearsal else hold_root, "_attempts", day,
                                     guard._hold_name(draft, now))
                os.makedirs(audit, exist_ok=True)
                with open(os.path.join(audit, "draft_attempt1.json"), "w", encoding="utf-8") as f:
                    json.dump({"attempt": 1, "gate": "G2", "reason": v["G2"][1], "draft": draft}, f, ensure_ascii=False, indent=1)
                ledger.append("run_ledger", {"date": day, "account_id": acc["account_id"], "kw": state["kw"], "attempt": 1,
                                             "gate": "G2", "reason": str(v["G2"][1]).replace("\n", " ")[:300],
                                             "audit_path": audit, "rehearsal": rehearsal}, ledger_dir)
                feedback = v["G2"][1]
                continue
            gates.append({"gate": "G1", "pass": v["G1"][0], "reason": v["G1"][1]})
            gates.append({"gate": "G2", "pass": v["G2"][0], "reason": v["G2"][1]})
            hold("verify", draft, [("G1", *v["G1"]), ("G2", *v["G2"])],
                 f"G1: {v['G1'][1]} / G2: {v['G2'][1]}" + (" (재작성 후에도 실패)" if attempt == 2 else "")
                 + (f" (재작성 파일 없음: {retry_path} — 좌석이 쓰면 다시 실행)" if draft_mode and attempt == 1 and v["G1"][0] else ""))
        # 5) guard G3·G5·G7(글·캡션) — G4(배경·글꼴)·G7(이미지 실측)은 design 이 채운 뒤 재확인
        checkgate("guard")
        gr = guard.run_guards(draft, acc, banned, classify=clf, alert_send=notify, ledger_dir=ledger_dir, hold_dir=hold_root,
                              today=today, now=now, record_all=False, gates=("G3", "G5", "G7"),
                              required_disclaimer=acc.get("required_disclaimer"))
        for g, ok, why in gr["results"]:
            gates.append({"gate": g, "pass": ok, "reason": why})
        if not gr["pass"]:
            fails = "; ".join(f"{g}: {w}" for g, ok, w in gr["results"] if not ok)
            raise _Done(finish("held", "guard", fails, hold_path=gr["hold_path"]))  # guard 가 이미 보류함 기록·알림 1회
        # 6) design (임시 폴더에서 만들고 전 관문 통과 뒤에만 결과 폴더로)
        checkgate("design")
        stage_dir = os.path.join(out_root, day, f".stage_{acc['account_id']}")
        shutil.rmtree(stage_dir, ignore_errors=True)
        try:
            dm = design.design(draft, bg_manifest if bg_manifest is not None else design.load_bg_manifest(), stage_dir,
                               brand=acc.get("brand"))
        except design.DesignError as e:
            hold("design", draft, [("DESIGN", False, str(e))], f"디자인 실패: {e}")
        # 7) G4·G7 재확인(실제 PNG 실측) + 캡션
        checkgate("recheck")
        fonts = guard.load_fonts()
        results = []
        ok4, w4 = guard.g4(draft, fonts)
        ok7, w7 = guard.g7(draft, strict=True, required_disclaimer=acc.get("required_disclaimer"))
        okc = CAP.check_caption(draft)
        results = [("G4(design 후)", ok4, w4), ("G7(design 후)", ok7, w7), ("CAPTION", not okc, "; ".join(okc) or "캡션 통과")]
        for g, ok, why in results:
            row(g, ok, why, draft)
        if not all(ok for _, ok, _ in results):
            bad = "; ".join(f"{g}: {w}" for g, ok, w in results if not ok)
            path = guard._hold(draft, results, hold_root, now)
            shutil.move(stage_dir, os.path.join(path, "cards"))
            notify("warn", f"[{acc['account_id']}] 보류 — {state['kw']}", f"recheck: {bad}"[:500])
            raise _Done(finish("held", "recheck", bad, hold_path=path))
        # 8) 결과 폴더
        checkgate("output")
        final = os.path.join(out_root, day, acc["account_id"])
        if os.path.exists(final):
            os.replace(final, f"{final}_prev_{now.strftime('%H%M%S')}")
        os.replace(stage_dir, final)
        for c in draft["cards"]:
            c["image_path"] = os.path.join(final, os.path.basename(c["image_path"]))
            if os.path.dirname(c["bg_path"]) == stage_dir:
                c["bg_path"] = os.path.join(final, os.path.basename(c["bg_path"]))
        for c in dm["cards"]:
            c["image_path"] = os.path.join(final, os.path.basename(c["image_path"]))
            if os.path.dirname(c["bg_file"]) == stage_dir:
                c["bg_file"] = os.path.join(final, os.path.basename(c["bg_file"]))
        os.replace(os.path.join(final, "manifest.json"), os.path.join(final, "design_manifest.json"))
        with open(os.path.join(final, "design_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(dm, f, ensure_ascii=False, indent=1)
        with open(os.path.join(final, "캡션.txt"), "w", encoding="utf-8") as f:
            f.write((f"[{REHEARSAL_MARK}]\n\n" if rehearsal else "") + draft["caption"] + "\n")
        if not rehearsal:
            ledger.append("check_ledger", {"gate": "ALL", "pass": True, "reason": "전 관문 통과", "account_id": acc["account_id"],
                                           "kw": state["kw"], "titles": [c["title"] for c in draft["cards"]], "sent_hashes": guard.sentence_hashes(draft),
                                           "hold_path": None}, ledger_dir)
        manifest = {"account_id": acc["account_id"], "kw": state["kw"], "date": day, "created": ledger.now_iso(),
                    "sources": draft["sources"], "gates": gates, "design": dm, "hashtags": draft["hashtags"],
                    "cards": [{"title": c["title"], "body": c["body"]} for c in draft["cards"]], "posted": False}
        if rehearsal:
            manifest = {"rehearsal_notice": REHEARSAL_MARK, "rehearsal": True, **manifest, "evidence_rule_skipped": True}
        with open(os.path.join(final, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        res = finish("ok", "output", f"전 관문 통과 — 결과 폴더 {final}", out_dir=final)
        manifest["cost"] = res["cost"]
        with open(os.path.join(final, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        res["html"] = report.build(day, out_root, hold_root, ledger_dir, rehearsal=rehearsal)
        return res
    except _Done as d:
        return d.result
    except Exception as e:  # noqa: BLE001
        try:
            notify("error", f"[{acc['account_id']}] 실행 오류({state['stage']})", repr(e)[:400])
        except Exception:  # noqa: BLE001
            pass
        return finish("error", state["stage"], trends.mask_secrets(repr(e))[:300])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="카드뉴스 공장 1단계(게시 없음)")
    ap.add_argument("--account", default="test")
    ap.add_argument("--draft-file", nargs="?", const="", default=None,
                    help="좌석이 쓴 초안 JSON 경로(값 없이 쓰면 data/drafts/<날짜>/<계정>.json). 종량 API 꺼짐이 기본이라 이 방식이 기본 동작")
    ap.add_argument("--rehearsal", action="store_true", help="evidence=none 보류만 건너뛰고 data/rehearsal/ 에 '리허설 — 게시 불가' 로 출력")
    a = ap.parse_args(argv)
    acc = C.load_account(a.account)
    ok, why = C.run_gate(acc)
    if not ok:
        print("중단:", why)
        return 0
    banned = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
    r = run(acc, banned, rehearsal=a.rehearsal, draft_file=a.draft_file or None)
    print(json.dumps({k: r[k] for k in ("status", "stage", "reason", "kw", "hold_path", "out_dir", "html", "cost")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
