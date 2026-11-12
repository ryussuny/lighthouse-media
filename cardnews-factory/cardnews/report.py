# -*- coding: utf-8 -*-
"""T-09 report — 그날의 결과·보류함을 한 장 HTML(data/out/<날짜>/index.html)로. 외부 CDN 없음(CSS 인라인).

읽는 것: out/<날짜>/<계정>/manifest.json(결과), hold/<날짜>/*/(draft.json·reason.txt·cards/), run_ledger.jsonl(그날 실행 줄).
이미지는 상대 경로로 링크한다(파일 이동 시 폴더째 옮기면 됨).
"""
import glob
import html
import json
import os

from . import config as C, ledger

OUT_DIR = os.path.join(C.ROOT, "data", "out")
HOLD_DIR = os.path.join(C.ROOT, "data", "hold")
CSS = """body{font-family:'Noto Sans KR','Malgun Gothic',sans-serif;margin:0;background:#f3f5f8;color:#1b2838}
header{background:#1F3A5F;color:#fff;padding:18px 28px}h1{margin:0;font-size:22px}h2{margin:28px 28px 8px;font-size:18px}
.wrap{padding:0 28px 40px}.box{background:#fff;border-radius:14px;padding:18px;margin:12px 0;box-shadow:0 1px 6px rgba(0,0,0,.08)}
.cards{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}.cards img{width:150px;height:187px;object-fit:cover;border-radius:8px;border:1px solid #d8dee8}
pre{white-space:pre-wrap;background:#f6f8fb;padding:10px;border-radius:8px;font-size:13px}table{border-collapse:collapse;font-size:13px}
td,th{border:1px solid #d8dee8;padding:4px 8px;text-align:left;vertical-align:top}.ok{color:#0a7d33;font-weight:700}.no{color:#b3261e;font-weight:700}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;background:#e8eef7}.hold{background:#fdecea}.small{color:#5b6b80;font-size:12px}"""


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _gates_table(gates):
    rows = "".join(f"<tr><td>{_e(g['gate'])}</td><td class='{'ok' if g['pass'] else 'no'}'>{'통과' if g['pass'] else '실패'}</td>"
                   f"<td>{_e(g['reason'])}</td></tr>" for g in gates)
    return f"<table><tr><th>관문</th><th>결과</th><th>사유·증거</th></tr>{rows}</table>"


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def build(day, out_root=None, hold_root=None, ledger_dir=None, rehearsal=False):
    out_root, hold_root = out_root or OUT_DIR, hold_root or HOLD_DIR
    day_dir = os.path.join(out_root, day)
    os.makedirs(day_dir, exist_ok=True)
    banner = ("<div style='background:#b3261e;color:#fff;padding:14px 28px;font-size:20px;font-weight:800'>"
              "리허설 — 게시 불가 (evidence=none 규칙만 건너뛴 시험 출력)</div>") if rehearsal else ""
    parts = [f"{banner}<header><h1>{'[리허설] ' if rehearsal else ''}카드뉴스 공장 — {_e(day)} 결과·보류함</h1><div class='small' style='color:#cfd9ea'>1단계: 게시 없음(결과 폴더까지만)</div></header><div class='wrap'>"]

    parts.append("<h2>결과</h2>")
    n_res = 0
    for mp in sorted(glob.glob(os.path.join(day_dir, "*", "manifest.json"))):
        m = _read_json(mp)
        if not m or "_prev_" in os.path.dirname(mp):
            continue
        n_res += 1
        d = os.path.dirname(mp)
        rel = os.path.basename(d)
        imgs = "".join(f"<img src='{_e(rel)}/{_e(os.path.basename(c['image_path']))}' alt='카드{c['card']}'>" for c in m.get("design", {}).get("cards", []))
        cap = ""
        cp = os.path.join(d, "캡션.txt")
        if os.path.exists(cp):
            with open(cp, encoding="utf-8") as f:
                cap = f.read()
        srcs = "".join(f"<li><a href='{_e(s['url'])}'>{_e(s['org'])}</a> <span class='small'>{_e(s.get('url'))}</span></li>" for s in m.get("sources", []))
        parts.append(f"<div class='box'><b>{_e(m.get('account_id'))}</b> · 키워드 <span class='tag'>{_e(m.get('kw'))}</span>"
                     f"<div class='cards'>{imgs}</div><pre>{_e(cap)}</pre><b>출처</b><ul>{srcs}</ul>"
                     f"<b>관문 결과</b>{_gates_table(m.get('gates', []))}"
                     f"<div class='small'>비용: {_e(json.dumps(m.get('cost', {}), ensure_ascii=False))}</div></div>")
    if not n_res:
        parts.append("<div class='box small'>오늘 결과 폴더에 나온 카드뉴스 없음</div>")

    parts.append("<h2>보류함</h2>")
    n_hold = 0
    for hd in sorted(glob.glob(os.path.join(hold_root, day, "*"))):
        if not os.path.isdir(hd):
            continue
        n_hold += 1
        draft = _read_json(os.path.join(hd, "draft.json")) or {}
        try:
            with open(os.path.join(hd, "reason.txt"), encoding="utf-8") as f:
                reason = f.read()
        except OSError:
            reason = ""
        imgs = ""
        for p in sorted(glob.glob(os.path.join(hd, "cards", "card_*.png"))):
            imgs += f"<img src='{_e(os.path.relpath(p, day_dir).replace(os.sep, '/'))}'>"
        cap = draft.get("caption", "")
        srcs = "".join(f"<li>{_e(s.get('org'))} {_e(s.get('url'))}</li>" for s in draft.get("sources", []) or [])
        parts.append(f"<div class='box hold'><b>{_e(draft.get('account_id'))}</b> · 키워드 <span class='tag'>{_e(draft.get('kw'))}</span>"
                     f"<pre>{_e(reason)}</pre><div class='cards'>{imgs}</div>"
                     + (f"<pre>{_e(cap)}</pre>" if cap else "") + (f"<ul>{srcs}</ul>" if srcs else "")
                     + f"<div class='small'>{_e(os.path.basename(hd))}</div></div>")
    if not n_hold:
        parts.append("<div class='box small'>오늘 보류 없음</div>")

    parts.append("<h2>오늘 실행 기록</h2><div class='box'><table><tr><th>시각</th><th>계정</th><th>상태</th><th>단계</th><th>사유</th></tr>")
    for r in ledger.read("run_ledger", ledger_dir):
        if r.get("date") == day:
            parts.append(f"<tr><td>{_e(r['ts'][11:19])}</td><td>{_e(r.get('account_id'))}</td><td>{_e(r.get('status'))}</td>"
                         f"<td>{_e(r.get('stage'))}</td><td>{_e(r.get('reason'))}</td></tr>")
    parts.append("</table></div></div>")
    path = os.path.join(day_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>{'[리허설 — 게시 불가] ' if rehearsal else ''}카드뉴스 {_e(day)}</title><style>{CSS}</style></head><body>{''.join(parts)}</body></html>")
    return path
