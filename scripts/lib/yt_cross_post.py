"""인스타 릴스 → 유튜브 쇼츠 교차 게시 (공개 업로드)
- 조건: 세로(높이>너비) + 60초 이하일 때만 올린다. 아니면 사유를 출력하고 건너뛴다.
- 제목: 훅 문장 40자 이내 + " #shorts" / 설명: 캡션 본문 + 해시태그 3~5개(#shorts 포함)
- 중복 방지: data/uploaded-videos.json (영상 경로 문자열 목록 — 기존 형식 그대로) 에 있는 경로는 다시 올리지 않는다.
- 호출하는 쪽(daily-ig-reels.py)이 try/except 로 감싼다 — 여기서 예외가 나도 인스타 게시는 영향이 없어야 한다.
- 토큰은 daily-video.py 와 같은 token_lighthouse.json (값은 출력하지 않는다)
- 단독 실행: py scripts/lib/yt_cross_post.py <mp4> [--hook "훅"] [--caption-file 파일] [--dry-run]
"""
import sys
import os, json, re, subprocess

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
UPLOADED = os.path.join(REPO, "data", "uploaded-videos.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "03_사업_마케팅", "lighthouse_media", "token_lighthouse.json")
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
MAX_HOOK = 40
MAX_SECONDS = 60
DEFAULT_TAGS = ["#위로", "#힐링"]


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


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


def already_uploaded(vpath):
    try:
        done = json.load(open(UPLOADED, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return _norm(vpath) in {_norm(p) for p in done if isinstance(p, str)}


def mark_uploaded(vpath):
    try:
        done = json.load(open(UPLOADED, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        done = []
    done.append(os.path.abspath(vpath))
    os.makedirs(os.path.dirname(UPLOADED), exist_ok=True)
    json.dump(done, open(UPLOADED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def build_title(hook):
    hook = re.sub(r"\s+", " ", (hook or "").strip().strip('"“”'))
    if len(hook) > MAX_HOOK:
        cut = hook[:MAX_HOOK]
        sp = cut.rfind(" ")
        hook = (cut[:sp] if sp >= 15 else cut).rstrip(" ,.")
    return f"{hook} #shorts"


def split_caption(caption):
    """캡션 → (해시태그 없는 본문, 해시태그 목록)"""
    tags = re.findall(r"#[^\s#]+", caption or "")
    body = re.sub(r"#[^\s#]+", "", caption or "")
    body = re.sub(r"[ \t]+\n", "\n", body)
    return re.sub(r"\n{3,}", "\n\n", body).strip(), tags


def build_description(caption):
    body, tags = split_caption(caption)
    uniq = []
    for t in tags:
        if t.lower() != "#shorts" and t not in uniq:
            uniq.append(t)
    for t in DEFAULT_TAGS:           # 3개 미만이면 기본 태그로 채운다
        if len(uniq) < 2 and t not in uniq:
            uniq.append(t)
    uniq = uniq[:4] + ["#shorts"]    # 4개 + #shorts = 최대 5개(최소 3개)
    return f"{body}\n\n—\n류선희 | Lighthouse Media\n\n{' '.join(uniq)}", uniq


def _youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def cross_post(vpath, hook, caption, dry_run=False, privacy="public"):
    """유튜브 쇼츠로 올린다. 올렸으면 영상 id, 건너뛰거나 dry-run 이면 None."""
    print("  [YouTube 쇼츠 교차 게시]" + ("  (dry-run: 업로드 안 함)" if dry_run else ""))
    if not hook:
        hook = next((ln.strip() for ln in (caption or "").splitlines() if ln.strip() and not ln.strip().startswith("#")), "")
    why = skip_reason(vpath)
    if why:
        print(f"    건너뜀: {why}")
        return None
    if already_uploaded(vpath):
        print("    건너뜀: 이미 유튜브에 올린 영상(data/uploaded-videos.json)")
        return None
    title = build_title(hook)
    desc, tags = build_description(caption)
    print(f"    제목: {title}")
    print(f"    해시태그: {' '.join(tags)}")
    print(f"    설명 미리보기:\n{desc[:600]}")
    if dry_run:
        return None
    from googleapiclient.http import MediaFileUpload
    yt = _youtube()
    body = {"snippet": {"title": title, "description": desc, "tags": [t.lstrip("#") for t in tags],
                        "categoryId": "22", "defaultLanguage": "ko"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(vpath, mimetype="video/mp4", resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    mark_uploaded(vpath)
    print(f"    https://youtube.com/shorts/{resp['id']}  (공개 범위: {privacy})")
    return resp["id"]


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
