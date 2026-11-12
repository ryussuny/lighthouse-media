# -*- coding: utf-8 -*-
"""카드뉴스 공장 → 통합 작업실 알림 통로(workroom_notify.notify).

보류(G 관문 실패)·지표 0개·비용 상한 도달·실행 오류를 보낸다. 알림 통로를 못 찾아도 공장은 멈추지 않는다.
"""
import os
import sys

WORKROOM = os.environ.get("WORKROOM_DIR") or os.path.join(os.path.expanduser("~"), "jarvis-workroom")


def send(level, title, body="", sender=None):
    try:
        if WORKROOM not in sys.path:
            sys.path.insert(0, WORKROOM)
        import workroom_notify
        return workroom_notify.notify(level, title, body, source="cardnews", sender=sender)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"[cardnews.alert] 알림 통로 실패: {e!r}\n")
        return None
