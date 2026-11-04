"""페이스북 페이지 게시 공통 도구 (2026-11-04 오너 지시: 페이스북 교차게시).

- 페이지 2개: church = 동산감리교회 페이지(tokens.json church_page_id / church_page)
             lighthouse = Lighthouse Media 페이지(1097948196731052 / facebook_page)
- 교회 페이지엔 교회·신앙 콘텐츠만 올린다 — 부르는 쪽이 지킨다(교회 스크립트만 account="church" 를 쓴다).
- 같은 키는 두 번 올리지 않는다: config/fb-posts.json (게시기록). RetryIG 처럼 같은 것을 되풀이해 올리는 일을 막는다.
  게시 요청이 실패해도 자동으로 다시 시도하지 않는다(부르는 쪽 예약 실행이 다음 차례에 한 번 더 부를 뿐).
- 토큰 값은 출력하지 않는다. 실패 메시지는 Graph 오류 문구만 보인다.
"""
import os, json, datetime
import requests

HOME = os.path.expanduser("~")
CONFIG = os.path.join(HOME, "lighthouse-media", "config")
LEDGER = os.path.join(CONFIG, "fb-posts.json")
G = "https://graph.facebook.com/v21.0"
LIGHTHOUSE_PAGE = "1097948196731052"


def _page(account):
    t = json.load(open(os.path.join(CONFIG, "tokens.json"), encoding="utf-8"))
    if account == "church":
        return t["church_page_id"], t["church_page"]
    if account == "lighthouse":
        return LIGHTHOUSE_PAGE, t["facebook_page"]
    raise ValueError(f"알 수 없는 페이지: {account}")


def _ledger():
    try:
        return json.load(open(LEDGER, encoding="utf-8"))
    except FileNotFoundError:
        return {}


def already(key):
    return _ledger().get(key)


def _record(key, account, post_id, link, what):
    L = _ledger()
    L[key] = {"page": account, "post_id": post_id, "link": link, "what": what,
              "at": datetime.datetime.now().isoformat(timespec="seconds")}
    json.dump(L, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _err(r):
    try:
        e = r.json().get("error", {})
        return f"{e.get('code')}/{e.get('error_subcode')} {e.get('message')}"
    except Exception:
        return f"HTTP {r.status_code}"


def _permalink(obj_id, token):
    try:
        return requests.get(f"{G}/{obj_id}", params={"fields": "permalink_url", "access_token": token},
                            timeout=30).json().get("permalink_url", "")
    except Exception:
        return ""


def _guard(account, key, dry, what):
    if not key:
        raise ValueError("게시기록 키가 필요하다")
    prev = already(key)
    if prev:
        print(f"  [페북 {account}] 이미 게시함({prev['at']}) — 건너뜀: {prev.get('link')}")
        return True
    if dry:
        print(f"  [페북 {account}] --dry-run: {what} 게시 안 함 (키 {key})")
        return True
    return False


def post_video(account, path, description, key, dry=False):
    """세로 영상 → 페이지 동영상. 성공 시 링크, 건너뜀/실패 시 None."""
    if _guard(account, key, dry, f"영상 {os.path.basename(path)}"):
        return None
    pid, tok = _page(account)
    with open(path, "rb") as f:
        r = requests.post(f"{G}/{pid}/videos", files={"source": (os.path.basename(path), f, "video/mp4")},
                          data={"description": description[:5000], "access_token": tok}, timeout=900)
    vid = r.json().get("id") if r.ok else None
    if not vid:
        print(f"  [페북 {account}] 영상 게시 실패: {_err(r)}")
        return None
    link = _permalink(vid, tok) or f"https://www.facebook.com/{vid}"
    if link.startswith("/"):
        link = "https://www.facebook.com" + link
    _record(key, account, vid, link, "video")
    print(f"  [페북 {account}] 영상 게시: {link}")
    return link


def post_photos(account, paths, message, key, dry=False):
    """사진 여러 장 → 한 게시물(앨범형). 성공 시 링크."""
    if _guard(account, key, dry, f"사진 {len(paths)}장"):
        return None
    pid, tok = _page(account)
    media = []
    for p in paths:
        with open(p, "rb") as f:
            r = requests.post(f"{G}/{pid}/photos", files={"source": (os.path.basename(p), f, "image/jpeg")},
                              data={"published": "false", "access_token": tok}, timeout=180)
        if not (r.ok and r.json().get("id")):
            print(f"  [페북 {account}] 사진 올리기 실패({os.path.basename(p)}): {_err(r)} — 게시하지 않음")
            return None
        media.append({"media_fbid": r.json()["id"]})
    data = {"message": message, "access_token": tok}
    for i, m in enumerate(media):
        data[f"attached_media[{i}]"] = json.dumps(m)
    r = requests.post(f"{G}/{pid}/feed", data=data, timeout=60)
    post = r.json().get("id") if r.ok else None
    if not post:
        print(f"  [페북 {account}] 게시 실패: {_err(r)}")
        return None
    link = _permalink(post, tok) or f"https://www.facebook.com/{post}"
    _record(key, account, post, link, f"photos x{len(paths)}")
    print(f"  [페북 {account}] 사진 {len(paths)}장 게시: {link}")
    return link


def post_link(account, message, url, key, dry=False):
    """링크 게시(유튜브 주소 등)."""
    if _guard(account, key, dry, f"링크 {url}"):
        return None
    pid, tok = _page(account)
    r = requests.post(f"{G}/{pid}/feed", data={"message": message, "link": url, "access_token": tok}, timeout=60)
    post = r.json().get("id") if r.ok else None
    if not post:
        print(f"  [페북 {account}] 링크 게시 실패: {_err(r)}")
        return None
    link = _permalink(post, tok) or f"https://www.facebook.com/{post}"
    _record(key, account, post, link, "link")
    print(f"  [페북 {account}] 링크 게시: {link}")
    return link
