"""JARVIS PC 상태 → 관제탑 하트비트 (30분마다 스케줄러 실행)
수집: 스케줄러 최근 실행 결과, 동산교회 백업 시각, 오늘 콘텐츠 발행 수, 교회 서버 상태
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, subprocess, datetime, glob
import urllib.request

HOME = os.path.expanduser("~")
TOWER = "https://lighthouse-media.onrender.com/api/heartbeat"

TASKS = [
    "LighthouseMedia_MusicUpload", "LighthouseMedia_BibleCard", "LighthouseMedia_DailyReels",
    "LighthouseMedia_Premium", "LighthouseMedia_AutoEngage",
    "DongsanChurch_DailyBackup",
]  # 서버형(Bridge/Main)은 작업코드 대신 실제 포트로 확인

def task_status(name):
    """PowerShell Get-ScheduledTaskInfo — 로케일 무관, 신뢰 가능"""
    try:
        ps = (f"Get-ScheduledTask -TaskName '{name}' | Get-ScheduledTaskInfo | "
              f"Select-Object LastRunTime,LastTaskResult | ConvertTo-Json")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0 or not out.stdout.strip():
            return {"name": name, "ok": False, "note": "작업 없음"}
        d = json.loads(out.stdout)
        code = int(d.get("LastTaskResult", -1))
        # 0=성공, 267009=실행중, 267011=아직 미실행, 267014=중지됨(수동)
        ok = code in (0, 267009, 267011)
        lr = d.get("LastRunTime") or ""
        if isinstance(lr, str) and lr.startswith("/Date("):
            ms = int(lr[6:-2]); lr = datetime.datetime.fromtimestamp(ms/1000).strftime("%m/%d %H:%M")
        return {"name": name, "ok": ok, "last": str(lr), "code": str(code)}
    except Exception as e:
        return {"name": name, "ok": False, "note": str(e)[:40]}

def latest_backup():
    try:
        d = os.path.join(HOME, "dongsan_backup", "daily")
        items = sorted(glob.glob(os.path.join(d, "*")), key=os.path.getmtime, reverse=True)
        if not items: return None
        return datetime.datetime.fromtimestamp(os.path.getmtime(items[0])).strftime("%m/%d %H:%M")
    except Exception:
        return None

def port_up(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return True
    except urllib.error.HTTPError:
        return True  # 응답 자체가 오면 살아있는 것 (404 포함)
    except Exception:
        return False

def church_server():
    return port_up("http://localhost:4000/api/server-info")

def bridge_server():
    return port_up("http://localhost:5555/")

def today_output():
    today = datetime.date.today().strftime("%Y-%m-%d")
    n = 0
    for pat in ["output/" + today + "/**/*", "output/**/*" + today + "*"]:
        n += len(glob.glob(os.path.join(HOME, "lighthouse-media", pat), recursive=True))
    return n

# ===== cys 플릿/이슈/스케줄 (jarvis-ui cys-bridge.js에서 이식, 2026-08-12) =====
# 원본은 Render 원격 대시보드에서 직접 `cys` CLI·로컬 로그를 조회했으나 Render엔 이 PC 파일이
# 안 보인다 — 그래서 이 PC(로컬)에서 이미 30분마다 도는 하트비트 페이로드에 실어 보내는 방식으로
# 전환했다. 원본의 역할별 heartbeat 로그 파싱(ctx%)은 이식하지 않았다 — round/*_heartbeat.log가
# 메인 pack엔 아예 없고 dept-2에도 7/30 이후 정지된 죽은 데이터라 빈 화면만 만들 것이었음.
CYS_PACK_DIR = os.path.join(HOME, ".cys", "pack")

def cys_fleet():
    """cys status --json + cys list 결합 — 지금 떠있는 노드 스냅샷(role/agent/상태/pid)."""
    try:
        status_out = subprocess.run(["cys", "status", "--json"], capture_output=True, text=True, timeout=10)
        list_out = subprocess.run(["cys", "list"], capture_output=True, text=True, timeout=10)
        if status_out.returncode != 0 or not status_out.stdout.strip():
            return []
        status = json.loads(status_out.stdout)
        pid_by_surface = {}
        for line in list_out.stdout.splitlines():
            cols = line.split("\t")
            if len(cols) >= 3:
                m = re.search(r"pid=(\d+)", cols[2])
                pid_by_surface[cols[0].strip()] = int(m.group(1)) if m else None
        nodes = []
        for s in status.get("surfaces", []):
            nodes.append({
                "role": s.get("role"),
                "surface_ref": s.get("surface_ref"),
                "agent": s.get("agent"),
                "agent_alive": s.get("agent_alive"),
                "idle_secs": s.get("idle_secs"),
                "queue_depth": s.get("queue_depth"),
                "pid": pid_by_surface.get(s.get("surface_ref")),
            })
        return nodes
    except Exception:
        return []

def cys_defects():
    """SESSION_STATE.md의 ★ 표시 항목(알려진 이슈·미해결 게이트) 최근 10개, 최신 먼저."""
    try:
        path = os.path.join(CYS_PACK_DIR, "round", "SESSION_STATE.md")
        if not os.path.exists(path):
            return []
        items = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = re.sub(r"^[-*→]\s*", "", re.sub(r"^#{1,6}\s*", "", line.strip()))
                if stripped.startswith("★") and line.strip():
                    items.append(line.strip())
        return items[-10:][::-1]
    except Exception:
        return []

def cys_schedule():
    """cys 내부 schedule.json 잡 목록(phoenix 스냅샷·fleet digest 등, Windows 작업스케줄러와 별개)."""
    try:
        path = os.path.join(CYS_PACK_DIR, "schedule.json")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return [{"id": j.get("id"), "every_minutes": j.get("every_minutes")} for j in data.get("jobs", [])]
    except Exception:
        return []

def main():
    payload = {
        "host": os.environ.get("COMPUTERNAME", "JARVIS-PC"),
        "sent": datetime.datetime.now().isoformat(timespec="seconds"),
        "schedulers": [task_status(t) for t in TASKS],
        "church_backup_last": latest_backup(),
        "church_server_up": church_server(),
        "bridge_up": bridge_server(),
        "today_output_files": today_output(),
        "cys_fleet": cys_fleet(),
        "cys_defects": cys_defects(),
        "cys_schedule": cys_schedule(),
    }
    req = urllib.request.Request(TOWER, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print("heartbeat sent:", r.status)

if __name__ == "__main__":
    main()
