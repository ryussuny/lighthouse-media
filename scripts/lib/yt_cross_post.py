"""인스타 릴스 → 유튜브 쇼츠 교차 게시
- 조건: 세로(높이>너비) + 60초 이하 + 훅이 비어 있지 않고 + 단정·의료·과장 표현이 없을 때만 올린다.
  (인스타 게시는 이 모듈과 무관하게 그대로 — 여기서는 유튜브만 건너뛴다)
- 제목: 훅 40자 이내 + " #shorts" / 설명: 훅 + 짧은 고정 문구 + 해시태그 3~5개(#shorts 포함). 캡션 전문은 올리지 않는다.
- 스위치: 환경변수 LM_YT_XPOST = off | unlisted | public (기본 public). off 이거나 알 수 없는 값이면 건너뜀.
- 중복 방지: data/uploaded-videos.json (영상 경로 문자열 목록). 읽을 수 없으면(손상 등) 덮어쓰지 않고 유튜브를 건너뛴다.
- 호출하는 쪽(daily-ig-reels.py)이 try/except 로 감싼다 — 여기서 예외가 나도 인스타 게시는 영향이 없어야 한다.
- 토큰은 daily-video.py 와 같은 token_lighthouse.json (값은 출력하지 않는다)
- 단독 실행: py scripts/lib/yt_cross_post.py <mp4> --hook "훅" [--caption-file 파일] [--dry-run]
"""
import sys
import os, json, re, subprocess, socket

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
UPLOADED = os.path.join(REPO, "data", "uploaded-videos.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
MAX_HOOK = 40
MAX_SECONDS = 60
HTTP_TIMEOUT = 120   # 초 — 네트워크 정체로 프로세스가 매달리지 않게
DEFAULT_TAGS = ["#위로", "#힐링", "#공감"]
FIXED_LINE = "오늘 하루도 수고한 당신에게."
CHANNEL_LINE = "류선희 | Lighthouse Media"
# 단정·의료·과장 표현 — 하나라도 있으면 유튜브만 건너뛴다(공백을 뺀 소문자 문자열에서 부분일치).
RISKY_TERMS = [
    "완치", "치료", "낫는다", "낫습니다", "낫게", "반드시낫", "확실히낫", "병이낫", "기적", "100%", "100퍼",
    "무조건", "진단", "처방", "약끊", "약을끊", "우울증이사라", "우울증사라", "우울증이없어", "효과보장", "보장",
    "cure", "miracle", "guarantee", "diagnos", "100%",
]
PRIVACY_BY_SWITCH = {"public": "public", "unlisted": "unlisted"}


def switch():
    """(privacy 또는 None, 설명). None 이면 건너뜀."""
    v = os.environ.get("LM_YT_XPOST", "public").strip().lower()
    if v in PRIVACY_BY_SWITCH:
        return PRIVACY_BY_SWITCH[v], f"LM_YT_XPOST={v}"
    return None, f"LM_YT_XPOST={v or '(빈 값)'} → 끔(off 또는 알 수 없는 값)"


def risky_hits(*texts):
    squashed = re.sub(r"\s+", "", " ".join(t for t in texts if t)).lower()
    return sorted({t for t in RISKY_TERMS if t in squashed})


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def atomic_write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_uploaded():
    """업로드 기록 목록. 파일이 없으면 [] , 읽을 수 없거나 형식이 틀리면 예외(덮어쓰지 않기 위해)."""
    if not os.path.exists(UPLOADED):
        return []
    data = json.load(open(UPLOADED, encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("uploaded-videos.json 이 목록이 아님")
    return data


def probe(vpath):
    """(너비, 높이, 길이초) — ffmpeg -i 의 stderr 에서 읽는다. 읽지 못하면 ValueError."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", vpath], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    m_d = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr)
    m_s = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", r.stderr)
    if not (m_d and m_s):
        raise ValueError("영상 길이·크기를 읽지 못함")
    secs = int(m_d.group(1)) * 3600 + int(m_d.group(2)) * 60 + float(m_d.group(3))
    return int(m_s.group(1)), int(m_s.group(2)), secs


def skip_reason(vpath):
    """올리면 안 되는 사유(문자열) 또는 None."""
    if not os.path.isfile(vpath) or os.path.getsize(vpath) == 0:
        return "영상 파일이 없거나 비어 있음"
    try:
        w, h, secs = probe(vpath)
    except ValueError as e:
        return str(e)
    if h <= w:
        return f"세로 영상이 아님({w}x{h})"
    if secs > MAX_SECONDS:
        return f"{MAX_SECONDS}초 초과({secs:.1f}초)"
    return None


def clean_hook(hook):
    return re.sub(r"\s+", " ", (hook or "").strip().strip('"“”')).strip()


def build_title(hook):
    hook = clean_hook(hook)
    if len(hook) > MAX_HOOK:
        cut = hook[:MAX_HOOK]
        sp = cut.rfind(" ")
        hook = (cut[:sp] if sp >= 15 else cut).rstrip(" ,.")
    return f"{hook} #shorts"


def caption_tags(caption):
    """캡션 맨 끝 해시태그 줄(해시태그만 있는 줄)에서만 태그를 뽑는다 — 본문 속 '#1' 같은 것은 승격하지 않는다."""
    lines = [ln.strip() for ln in (caption or "").splitlines() if ln.strip()]
    if not lines:
        return []
    last = lines[-1]
    if re.sub(r"#[^\s#]+", "", last).strip():
        return []
    return re.findall(r"#[^\s#]+", last)


def build_description(hook, caption):
    """설명 = 훅 + 고정 문구 + 해시태그(3~5개, #shorts 포함). 해시태그 목록도 함께 돌려준다."""
    tags = []
    for t in caption_tags(caption) + DEFAULT_TAGS:
        if t.lower() == "#shorts" or re.fullmatch(r"#\d+", t) or t in tags:
            continue
        tags.append(t)
    tags = tags[:4] + ["#shorts"]
    return f"{clean_hook(hook)}\n\n{FIXED_LINE}\n{CHANNEL_LINE}\n\n{' '.join(tags)}", tags


def _youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        tmp = TOKEN + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        os.replace(tmp, TOKEN)
    return build("youtube", "v3", credentials=creds)


def cross_post(vpath, hook, caption, dry_run=False):
    """유튜브 쇼츠로 올린다. 올렸으면 영상 id, 건너뛰거나 dry-run 이면 None."""
    print("  [YouTube 쇼츠 교차 게시]" + ("  (dry-run: 업로드 안 함)" if dry_run else ""))
    privacy, sw = switch()
    if privacy is None:
        print(f"    건너뜀: {sw}")
        return None
    hook = clean_hook(hook)
    if not hook:
        print("    건너뜀: 훅이 비어 있음(검증된 훅이 없으면 올리지 않는다)")
        return None
    hits = risky_hits(hook, caption)
    if hits:
        print(f"    건너뜀: 단정·의료·과장 표현 감지 {hits} (인스타는 그대로 게시됨)")
        return None
    why = skip_reason(vpath)
    if why:
        print(f"    건너뜀: {why}")
        return None
    try:
        done = load_uploaded()
    except Exception as e:
        print(f"    건너뜀: 업로드 기록을 읽을 수 없어 중복 여부를 확인 못 함({type(e).__name__}) — 기록 파일은 건드리지 않음")
        return None
    if _norm(vpath) in {_norm(p) for p in done if isinstance(p, str)}:
        print("    건너뜀: 이미 유튜브에 올린 영상(data/uploaded-videos.json)")
        return None
    title = build_title(hook)
    desc, tags = build_description(hook, caption)
    print(f"    제목: {title}")
    print(f"    해시태그: {' '.join(tags)}   공개 범위: {privacy} ({sw})")
    print(f"    설명 미리보기:\n{desc}")
    if dry_run:
        return None
    from googleapiclient.http import MediaFileUpload
    old_to = socket.getdefaulttimeout()
    socket.setdefaulttimeout(HTTP_TIMEOUT)
    try:
        yt = _youtube()
        body = {"snippet": {"title": title, "description": desc, "tags": [t.lstrip("#") for t in tags],
                            "categoryId": "22", "defaultLanguage": "ko"},
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
        req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(vpath, mimetype="video/mp4", resumable=True))
        resp = None
        while resp is None:
            _, resp = req.next_chunk()
    finally:
        socket.setdefaulttimeout(old_to)
    vid = resp["id"]
    print(f"    https://youtube.com/shorts/{vid}  (공개 범위: {privacy})")
    try:   # 업로드 직후 바로 기록 — 기록이 실패해도 업로드 사실은 알린다
        atomic_write_json(UPLOADED, done + [os.path.abspath(vpath)])
    except Exception as e:
        print(f"    ⚠ 업로드는 됐으나 기록 실패({type(e).__name__}) — 같은 영상 재실행 시 중복될 수 있음")
    return vid


if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--hook", default="")
    ap.add_argument("--caption-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cap = open(a.caption_file, encoding="utf-8").read() if a.caption_file else ""
    cross_post(a.video, a.hook, cap, dry_run=a.dry_run)
