# -*- coding: utf-8 -*-
"""원장(jsonl) — 추가만 한다(지우지 않음)."""
import datetime as dt
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(ROOT, "data", "ledger")


def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def append(name, record, ledger_dir=None):
    d = ledger_dir or LEDGER_DIR
    os.makedirs(d, exist_ok=True)
    rec = {"ts": now_iso(), **record}
    with open(os.path.join(d, f"{name}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read(name, ledger_dir=None):
    p = os.path.join(ledger_dir or LEDGER_DIR, f"{name}.jsonl")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
