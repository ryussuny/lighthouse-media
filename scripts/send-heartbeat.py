"""JARVIS PC 상태 → 관제탑 하트비트 (30분마다 스케줄러 실행)
수집: 스케줄러 최근 실행 결과, 동산교회 백업 시각, 오늘 콘텐츠 발행 수, 교회 서버 상태
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, subprocess, datetime, glob
import urllib.request

HOME = os.path.expanduser("~")
TOWER = "https://lighthouse-media.onrender.com/api/heartbeat"

TASKS = [
    "LighthouseMedia_MusicUpload", "LighthouseMedia_BibleCard", "LighthouseMedia_DailyReels",
    "LighthouseMedia_Premium", "LighthouseMedia_AutoEngage",
    "DongsanChurch_DailyBackup", "DongsanChurch_BridgeServer", "DongsanChurch_MainServer",
]

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

def church_server():
    try:
        with urllib.request.urlopen("http://localhost:4000/api/server-info", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def today_output():
    today = datetime.date.today().strftime("%Y-%m-%d")
    n = 0
    for pat in ["output/" + today + "/**/*", "output/**/*" + today + "*"]:
        n += len(glob.glob(os.path.join(HOME, "lighthouse-media", pat), recursive=True))
    return n

def main():
    payload = {
        "host": os.environ.get("COMPUTERNAME", "JARVIS-PC"),
        "sent": datetime.datetime.now().isoformat(timespec="seconds"),
        "schedulers": [task_status(t) for t in TASKS],
        "church_backup_last": latest_backup(),
        "church_server_up": church_server(),
        "today_output_files": today_output(),
    }
    req = urllib.request.Request(TOWER, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print("heartbeat sent:", r.status)

if __name__ == "__main__":
    main()
