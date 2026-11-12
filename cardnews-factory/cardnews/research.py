# -*- coding: utf-8 -*-
"""T-04/T-04b research — trend_ledger 오늘 top5 를 순위대로 → 공식 출처 수집 → 원문 저장·sha256 → source_ledger.

주제·출처를 지어내지 않는다. G1 규칙(PRD_v2 §4 + master 결정):
  - 공식 도메인(config/official_domains.json) 밖 URL 은 버린다.
  - 출처 게시일이 MAX_AGE_DAYS(30)일을 넘거나 날짜를 못 읽으면 버린다(사유 기록).
  - '2곳' = 서로 다른 '확인된' 기관(org) 2곳 이상. 같은 기관 기사 여러 건은 저장하되 1곳으로 센다.
    기관 미상(제공 기관을 못 읽어 호스트명으로 대체한 것, org_known=false)은 저장은 해도 기관 수에 넣지 않는다.
  - 관련도(relevance, 더 엄격한 쪽): 키워드가 ① 기사 제목에 있거나 ② 본문 첫 300자에 있으면서 본문 총 2회 이상이거나
    ③ 본문에 3회 이상일 때만 출처 후보. 그 밖(예: 본문 1회 언급)은 버리고 사유를 research_ledger 에 남긴다.
    본문은 nav·footer·인기검색어 같은 덩어리를 뺀 텍스트로 센다.
  - 같은 보도자료 재게시(제목 유사도 0.8 이상 또는 본문 8자 조각 Jaccard 0.6 이상)는 1곳으로 합산(source_ledger.dup_of).
  - 게시일: JSON-LD datePublished → 기사 상단 표시일. 사이트맵 lastmod(수정일)는 쓰지 않고, 날짜를 못 읽으면 버리며 사유를 남긴다.
  - 요청: 식별 UA(연락처 없음), robots.txt 요청도 간격·호스트 카운터에 포함, 리다이렉트는 매 홉 공식 도메인·robots·상한 재적용.
  - research.run(gate=True): STOP 파일·paused 면 아무것도 하지 않음. 도메인 목록은 config/official_domains.json 하나만 쓴다
    (provider URL 상수도 같은 목록 안이어야 함 — 시험으로 확인).
  - top5 를 순위대로, 그래도 못 채우면 같은 날 trend_ledger 의 in_scope 후보(점수순, 금칙·중복 제외)를 이어서
    최대 MAX_TRIES(15)개까지 시도해 처음으로 G1 을 채우는 키워드를 채택. 시도마다 research_ledger 에 한 줄.
    모두 못 채우면 hold + 알림 1회(키워드마다 알림 없음).
  - 지표 근거가 없는 후보(seed 만 있고 유튜브·트렌드·IG 지표 0)가 채택되면 evidence='none'(지표 근거 없음, 공식 출처만 있음)
    으로 표시한다 — 이런 주제를 보류할지는 T-09 에서 master 가 정한다.
  - provider 는 페이지·RSS 를 한 번만 받으므로 키워드 수가 늘어도 기관 사이트 요청 수는 늘지 않는다.
  - 출처 누적 캐시(data/source_cache/, T-04f): 요청 상한(호스트당 40/실행·1.2초)은 그대로 두고 받은 기사(본문 구간·게시일·
    org·org_known·sha256)를 쌓아 매일 '아직 안 받은 새 URL'만 받는다. 키워드 매칭은 캐시 전체 중 게시 30일 이내 기사에서 한다.
    30일 지난 항목은 매칭에서만 빼고 지우지 않는다. 채택 시 source_ledger 는 캐시 저장본 경로·sha256 을 그대로 가리킨다.

── 검색 방법 조사 결과 (2026-11-12 실측, 키 불필요·로그인 불필요 경로만) ──
 A) 정책브리핑 사이트맵(https://www.korea.kr/sitemapindex.xml — robots.txt 의 Sitemap: 줄로 공시):
    sitemap_policy.xml(정책뉴스 3,423건)·sitemap_briefing.xml(1,979건)에 url + lastmod(제목 없음).
    최신 N건 본문을 받아 키워드가 실제 있는 것만 채택. 매칭·저장은 페이지 전체가 아니라 '본문 구간'(제목~본문, 사이드바·
    이전/다음 기사 목록 제외)만 쓴다 — 전체를 쓰면 사이드바 때문에 거의 모든 페이지가 걸린다(T-04d 실측: 39건 중 36건 오탐).
    기사 JSON-LD 에서 제공 기관(author.name, Organization 일 때)과 datePublished 를 읽는다. 정책브리핑 '브리핑' 글은
    author 가 개인(대변인·국장)이라 기관 미상 → org=호스트명. 날짜는 없으면 사이트맵 lastmod. 한계: 최근 N건만 탐색.
 B) 보건복지부 보도자료 RSS(https://www.mohw.go.kr/rss/board.es?mid=a10503000000&bid=0027):
    https://www.mohw.go.kr/robots.txt 가 /rss 와 이 URL 을 명시 Allow(같은 파일이 /search/ 는 Disallow).
    키 불필요, 최신 30건에 본문 전문·pubDate 포함 → 항목(제목·링크·게시일·본문)을 원문 저장본으로 쓴다.
 B2) 고용노동부 보도자료(https://www.moel.go.kr/news/enews/report/enewsList.do → enewsView.do?news_seq=N):
    https://www.moel.go.kr/robots.txt 는 /portal/·/v2024/ 등만 Disallow, /news/ 는 허용. 키 불필요. 목록에서 최신 N건을 받아
    상세 페이지의 '등록일'(YYYY-MM-DD)과 본문(b_content)을 읽는다. 기관=고용노동부(근로복지공단 등 산하 보도 포함 — 게시 주체는 고용노동부 누리집).
 C) 제외(2026-11-12 실측):
    - 국민연금공단 nps.or.kr: RSS 없음(/rss/rss.do 404). https://www.nps.or.kr/robots.txt 가 /search/ 와
      /pbcpgdnc/ognzprsn/getOHAG0013M0List.do?menuId=MN24001022* 를 Disallow — 보도자료 게시판 위치를 robots 허용 경로에서 확인하지 못함.
    - 국민건강보험공단 nhis.or.kr: https://www.nhis.or.kr/robots.txt 가 'Disallow : /nhis/' — 보도자료 목록
      (/nhis/together/wbhaea01600m01.do)이 이 아래라 불허로 판단, 사용 안 함.
    - 국세청 nts.go.kr: robots 는 Allow: / 이나 RSS 없음(/rss/rss.do 404), 보도자료 목록(/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028)
      은 제목·게시일만 있고 상세(selectNttInfo.do)가 폼 POST 전용(GET 은 217바이트 오류) → 본문 원문을 못 얻어 G2 불가.
    - 복지로 bokjiro.go.kr: /robots.txt 요청에 HTML 응답 — 규칙 확인 불가.
    - 정책브리핑 RSS(서비스 중단 공지 https://www.korea.kr/etc/noticeView.do?newsId=132038885),
    정책브리핑 검색 totalSearch.do(GET 응답에 결과 없음·스크립트 렌더), 정부24(robots 거의 전면 Disallow),
    복지로(robots.txt 확인 불가), 공공데이터포털·법령정보센터 OpenAPI(인증키 필요).
준수: robots.txt 를 호스트별로 읽어 허용 URL 만 요청, 요청 간 1.2초, 실행당 호스트별 MAX_PAGES(40)건 이하, 로그인·우회 없음.
네트워크는 전부 주입 가능: run(..., fetchers={"discover": f(kw)->[{"url","org","published","content"(bytes),"title"}]}).
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

from . import config as C
from . import ledger

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_DIR = os.path.join(ROOT, "data", "sources")
# 브라우저로 위장하지 않는 식별 UA. 개인 연락처(이메일 등)는 넣지 않는다.
UA = "cardnews-factory/1.0 (non-commercial research; robots-compliant)"
ROBOTS_TOKEN = "cardnews-factory"   # robots.txt 의 User-agent 매칭용 제품 토큰
MAX_REDIRECTS = 3
MIN_SOURCES = 2          # 서로 다른 기관 수
MAX_AGE_DAYS = 30
MAX_TRIES = 15           # 한 번 실행에서 시도하는 키워드 상한(top5 + 나머지 in_scope 후보)
MAX_PAGES = 40           # 한 번 실행에서 호스트당 받는 요청 상한(하루 수십 건 이하)
MIN_INTERVAL = 1.2       # 요청 간 최소 간격(초)
SITEMAPS = ["https://www.korea.kr/sitemap_policy.xml", "https://www.korea.kr/sitemap_briefing.xml"]
MOHW_RSS = "https://www.mohw.go.kr/rss/board.es?mid=a10503000000&bid=0027"
MOEL_LIST = "https://www.moel.go.kr/news/enews/report/enewsList.do"
MOEL_VIEW = "https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq="
MOEL_ITEMS = 12          # 고용노동부 보도자료 최신 N건(상세 N+목록 1 = 13요청 < 40)


def _norm(s):
    return "".join(s.split()).lower()


def html_to_text(raw):
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    s = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return html.unescape(s)


def page_title(raw):
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    m = re.search(r'(?is)<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)', s) \
        or re.search(r"(?is)<title[^>]*>(.*?)</title>", s)
    return html.unescape(m.group(1)).strip() if m else ""


def org_of(url):
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


RELEVANCE_HEAD = 300        # 본문 첫 문단 대용: 첫 N자
RELEVANCE_HEAD_MIN = 2      # 첫 문단에 있을 때 필요한 본문 총 횟수
RELEVANCE_BODY_MIN = 3      # 첫 문단에 없어도 통과하는 본문 횟수
_BODY_MARK = re.compile(r'class="[^"]*(?:view_cont|b_content)[^"]*"')
# 메뉴·바닥글·인기검색어 같은 '본문 밖' 덩어리 — 통째로 제거한다(중첩이 깊으면 일부 찌꺼기가 남을 수 있어 보수적으로 둠)
_CHROME_TAGS = re.compile(r"(?is)<(nav|footer|header|aside|form|select|button)\b[^>]*>.*?</\1>")
_CHROME_CLS = re.compile(r'(?is)<(div|ul|ol|section|dl|p|span)\b[^>]*?(?:class|id)="[^"]*'
                         r'(?:popular|keyword|rank|hotissue|hot_|sidebar|gnb|lnb|footer|breadcrumb|sns|share|related|recommend|banner|paging|btn_)'
                         r'[^"]*"[^>]*>.*?</\1>')


def strip_chrome(s):
    """nav·footer·인기검색어·공유/추천/배너 덩어리를 뺀 HTML."""
    s = _CHROME_TAGS.sub(" ", s)
    return _CHROME_CLS.sub(" ", s)


def body_text(content):
    """저장본에서 '본문' 텍스트(공백 정리, nav·footer·인기검색어 제거). 본문 표지(view_cont·b_content)가 있으면 그 뒤, 없으면 전체."""
    s = content.decode("utf-8", "replace") if isinstance(content, (bytes, bytearray)) else content
    m = _BODY_MARK.search(s)
    t = html_to_text(strip_chrome(s[m.start():] if m else s))
    return re.sub(r"\s+", " ", t).strip()


def relevance(kw, title, content):
    """(통과 여부, 사유). 더 엄격한 기준 — 아래 중 하나:
    ① 제목에 있음  ② 본문 첫 300자에 있으면서 본문 총 2회 이상  ③ 본문 3회 이상.
    그 밖(본문 1회 언급 등)은 탈락."""
    n = _norm(kw)
    body = body_text(content)
    cnt = _norm(body).count(n) if n else 0
    in_head = bool(n) and n in _norm(body[:RELEVANCE_HEAD])
    if n and n in _norm(title or ""):
        return True, "제목에 포함"
    if in_head and cnt >= RELEVANCE_HEAD_MIN:
        return True, f"본문 첫 {RELEVANCE_HEAD}자 포함+본문 {cnt}회"
    if cnt >= RELEVANCE_BODY_MIN:
        return True, f"본문에 {cnt}회"
    if cnt == 1:
        return False, "본문 1회 언급·관련도 낮음"
    if cnt == 0:
        return False, "본문에 없음·관련도 낮음"
    return False, f"본문 {cnt}회지만 첫 문단 밖·관련도 낮음"


def _shingles(text, k=8, limit=4000):
    t = _norm(text)[:limit]
    return {t[i:i + k] for i in range(max(0, len(t) - k + 1))}


def same_release(a, b, title_ratio=0.8, body_jaccard=0.6):
    """같은 보도자료 재게시인가(제목이 매우 비슷하거나 본문이 근사 일치). a, b: {title, content}."""
    import difflib
    ta, tb = _norm(a.get("title", "")), _norm(b.get("title", ""))
    if ta and tb and difflib.SequenceMatcher(None, ta, tb).ratio() >= title_ratio:
        return True
    sa, sb = _shingles(body_text(a["content"])), _shingles(body_text(b["content"]))
    return bool(sa and sb) and len(sa & sb) / len(sa | sb) >= body_jaccard


def org_is_known(c):
    """제공 기관이 확인된 것인가. org 가 없거나 호스트명 그대로(대체값)면 미상. 후보가 org_known 을 직접 주면 그걸 따른다."""
    if "org_known" in c:
        return bool(c["org_known"])
    org = c.get("org")
    # 호스트명(점이 있는 도메인 꼴)은 기관명이 아니다 — 호스트 대체값·도메인 문자열은 미상
    return bool(org) and "." not in org and _norm(org) != _norm(org_of(c.get("url", "")))


def parse_date(s):
    """ISO / 2026.11.11 / RFC822 → date. 못 읽으면 None."""
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)
    try:
        if m:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        d = email.utils.parsedate_to_datetime(s)
        return d.date() if d else None
    except (TypeError, ValueError):
        return None


def korea_kr_meta(raw):
    """정책브리핑 기사 JSON-LD 에서 (제공 기관, 게시일 문자열). 기관은 Organization 일 때만, 없으면 None."""
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    org = None
    m = re.search(r'"author"\s*:\s*\{[^{}]*?"@type"\s*:\s*"Organization"[^{}]*?"name"\s*:\s*"([^"]+)"', s)
    if m:
        org = html.unescape(m.group(1)).strip()
    d = re.search(r'"datePublished"\s*:\s*"([^"]*)"', s)
    pub = d.group(1) if d and d.group(1).strip() else None
    if not pub:
        d = re.search(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', s)
        pub = d.group(1) if d else None
    return org, pub


def korea_kr_article(raw):
    """정책브리핑 기사 '본문 구간'(제목~본문, '이전·다음 기사' 목록 앞까지)의 HTML 조각. 구간을 못 찾으면 ''.
    페이지 전체를 보면 사이드바 '주요 뉴스'·이전/다음 기사 제목 때문에 거의 모든 페이지가 키워드에 걸린다(T-04d 실측 오탐 36/39).
    그래서 못 찾으면 전체로 대신하지 않고 비운다(= 매칭 안 함)."""
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    i = s.find('class="view_title"')
    if i < 0:
        return ""
    j = s.find('class="view_opt"', i)
    seg = s[i:(j if j > i else i + 60000)]
    k = seg.find("이전다음기사")
    return strip_chrome(seg[:k] if k > 0 else seg)


def korea_kr_shown_date(seg):
    """기사 상단에 표시되는 게시일(2026.11.11) — 본문 구간 첫 날짜. 없으면 None. (사이트맵 lastmod 는 수정일이라 쓰지 않는다)"""
    m = re.search(r"(?<!\d)(\d{4})\.(\d{2})\.(\d{2})(?!\d)", html_to_text(seg))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


# ---------- 키워드 선택 ----------
def _has_evidence(score):
    """trends 가 붙인 evidence 가 있으면 그대로, 옛 기록이면 parts 로 계산(유튜브·트렌드 트래픽·IG 중 하나라도 있으면 True)."""
    if "evidence" in score:
        return bool(score["evidence"])
    pt = score.get("parts", {})
    return bool(pt.get("yt_matches") or pt.get("gt_traffic") or pt.get("ig_like_median") is not None)


def candidate_keywords(account_id, today, ledger_dir=None, max_tries=MAX_TRIES):
    """오늘 날짜·해당 계정의 가장 최근 trend_ledger 한 줄 → 시도할 키워드 [{kw, src, evidence}], 사유.
    순서: top5(순위순) → 나머지 in_scope 점수순. 금칙·범위 밖(in_scope=False)·중복은 제외, 최대 max_tries."""
    day = today.isoformat()
    recs = [r for r in ledger.read("trend_ledger", ledger_dir)
            if r.get("date") == day and r.get("account_id") == account_id]
    if not recs:
        return [], f"오늘({day}) {account_id} 의 trend_ledger 기록 없음 — 먼저 trends 실행"
    rec = recs[-1]
    scores = {s["kw"]: s for s in rec.get("scores", [])}
    in_scope = {c["kw"] for c in rec.get("candidates", []) if c.get("in_scope")}
    out, seen = [], set()

    def add(kw, src):
        n = _norm(kw)
        if n in seen or kw not in in_scope or len(out) >= max_tries:
            return
        seen.add(n)
        out.append({"kw": kw, "src": src, "evidence": _has_evidence(scores.get(kw, {}))})

    for t in sorted(rec.get("top5", []), key=lambda t: t.get("rank", 99)):
        add(t["kw"], "top5")
    for s in sorted(rec.get("scores", []), key=lambda s: (-s.get("value", 0), s["kw"])):
        add(s["kw"], "in_scope")
    if not out:
        return [], f"trend_ledger status={rec.get('status')} — 시도할 in_scope 후보 없음"
    return out, "ok"


# ---------- 기본 네트워크 ----------
class PoliteFetcher:
    """robots.txt 준수 + 요청 간격 + 호스트당 상한. requests 는 여기서만 import.
    robots.txt 요청도 같은 간격·호스트 카운터에 들어간다. 리다이렉트는 직접 따라가며 매 홉마다
    공식 도메인·robots·호스트 상한을 다시 적용한다(공식 밖으로 나가는 리다이렉트는 거부)."""

    def __init__(self, max_pages=MAX_PAGES, interval=MIN_INTERVAL, sleep=time.sleep, domains=None):
        self.max_pages, self.interval, self.sleep = max_pages, interval, sleep
        self.count, self.last, self.robots = {}, 0.0, {}
        self.domains = domains or C.load_json(os.path.join(C.CONFIG, "official_domains.json"))

    def _tick(self, url):
        """요청 1건을 호스트 카운터·간격에 반영(robots 포함). 상한이면 예외."""
        host = org_of(url)
        if self.count.get(host, 0) >= self.max_pages:
            raise RuntimeError(f"호스트 상한 도달: {host} {self.max_pages}건")
        wait = self.interval - (time.monotonic() - self.last)
        if wait > 0:
            self.sleep(wait)
        self.last = time.monotonic()
        self.count[host] = self.count.get(host, 0) + 1

    def _allowed(self, url):
        import requests
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                self._tick(base + "/robots.txt")
                r = requests.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=15, allow_redirects=False)
                rp.parse(r.text.splitlines() if r.status_code == 200 else ["User-agent: *", "Disallow: /"])
            except Exception:  # noqa: BLE001  robots 를 못 읽으면 막힌 것으로 본다
                rp.parse(["User-agent: *", "Disallow: /"])
            self.robots[base] = rp
        return self.robots[base].can_fetch(ROBOTS_TOKEN, url)

    def get(self, url):
        import requests
        for _ in range(MAX_REDIRECTS + 1):
            if not C.is_official_url(url, self.domains):
                raise PermissionError(f"공식 도메인 밖: {url}")
            if not self._allowed(url):
                raise PermissionError(f"robots.txt 불허: {url}")
            self._tick(url)
            r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=False)
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                url = urljoin(url, r.headers["Location"])
                continue
            r.raise_for_status()
            return r.content, url
        raise RuntimeError("리다이렉트 너무 많음")


def parse_sitemap(xml_bytes):
    """[(lastmod, url)] 최신순. 사이트맵 규격(sitemaps.org) 그대로."""
    s = xml_bytes.decode("utf-8", "replace")
    out = []
    for m in re.finditer(r"(?s)<url>(.*?)</url>", s):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", m.group(1))
        lm = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", m.group(1))
        if loc:
            out.append((lm.group(1) if lm else "", html.unescape(loc.group(1))))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def parse_rss_items(xml_bytes):
    """RSS 2.0 → [{url, title, published, text}]"""
    root = ET.fromstring(xml_bytes)
    out = []
    for it in root.findall("./channel/item"):
        out.append({"url": (it.findtext("link") or "").strip(), "title": (it.findtext("title") or "").strip(),
                    "published": it.findtext("pubDate"), "text": it.findtext("description") or ""})
    return out


# ---------- 출처 누적 캐시 (T-04f) ----------
CACHE_DIR = os.path.join(ROOT, "data", "source_cache")


class SourceCache:
    """받은 기사(본문 구간 저장본)를 누적한다. 요청 상한은 그대로 두고, 매일 '아직 안 받은 새 URL'만 받아 쌓는다.
    - index.jsonl 은 추가만(같은 url 의 마지막 줄이 유효). 저장본은 files/<sha 앞 16자>_<호스트>.html.
    - 저장본 규칙은 원문 저장과 같다: 본문 구간만, sha256 기록. 읽을 때 sha256 을 다시 확인해 다르면 매칭에서 뺀다.
    - 게시 MAX_AGE_DAYS 일이 지난 항목은 매칭에서 빼기만 하고 지우지 않는다(비가역 삭제 금지)."""

    def __init__(self, cache_dir=None):
        self.dir = cache_dir or CACHE_DIR
        self.files = os.path.join(self.dir, "files")
        self.index = os.path.join(self.dir, "index.jsonl")
        self.entries = {}
        self.stats = {"fetched": 0, "known_skipped": 0, "negative": 0}
        self.tampered_urls = set()
        self._texts = None
        if os.path.exists(self.index):
            with open(self.index, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            e = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(e, dict) and e.get("url"):
                            self.entries[e["url"]] = e

    def has(self, url):
        return url in self.entries

    def _append(self, rec):
        os.makedirs(self.dir, exist_ok=True)
        rec = {"cached_at": ledger.now_iso(), **rec}
        with open(self.index, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.entries[rec["url"]] = rec
        self._texts = None
        return rec

    def add(self, entry):
        """entry: {url, org, org_known, published, title, content(bytes), date_note?} → 저장본 + 인덱스 한 줄"""
        content = entry["content"]
        sha = hashlib.sha256(content).hexdigest()
        os.makedirs(self.files, exist_ok=True)
        path = os.path.join(self.files, f"{sha[:16]}_{org_of(entry['url'])}.html")
        if not (os.path.exists(path) and self._sha_of(path) == sha):  # 없거나 바뀌었으면 (다시) 쓴다
            with open(path, "wb") as f:
                f.write(content)
        d = parse_date(entry.get("published"))
        self.stats["fetched"] += 1
        return self._append({"url": entry["url"], "org": entry.get("org"), "org_known": bool(entry.get("org_known")),
                             "published": d.isoformat() if d else None, "title": entry.get("title", ""), "sha256": sha,
                             "saved_path": path, "fetched_at": ledger.now_iso(), "date_note": entry.get("date_note")})

    def add_negative(self, url, reason):
        """읽을 수 없는 URL(본문 구간 없음·리다이렉트 별칭 등) — 내일 다시 요청하지 않도록 기록."""
        self.stats["negative"] += 1
        return self._append({"url": url, "skip_reason": reason})

    @staticmethod
    def _sha_of(path):
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            return None

    def within(self, today, max_age=MAX_AGE_DAYS):
        out = []
        for e in self.entries.values():
            if e.get("skip_reason") or not e.get("saved_path"):
                continue
            d = parse_date(e.get("published"))
            if d is not None and 0 <= (today - d).days <= max_age:
                out.append(e)
        return out

    def read(self, e):
        """저장본 바이트. 파일이 없거나 sha256 이 다르면 None(변조·손상 — 매칭에서 제외하고 기록)."""
        try:
            with open(e["saved_path"], "rb") as f:
                raw = f.read()
        except OSError:
            self.tampered_urls.add(e["url"])
            return None
        if hashlib.sha256(raw).hexdigest() != e.get("sha256"):
            self.tampered_urls.add(e["url"])
            return None
        return raw

    def match(self, kw, today):
        """캐시 전체 중 게시 MAX_AGE_DAYS 일 이내 기사에서 kw 가 본문에 있는 것 → 후보 목록(저장본 경로·sha256 포함)."""
        if self._texts is None or self._texts[0] != today:
            texts = {}
            for e in self.within(today):
                raw = self.read(e)
                if raw is not None:
                    texts[e["url"]] = (e, raw, _norm(html_to_text(raw)))
            self._texts = (today, texts)
        n = _norm(kw)
        out = []
        for e, raw, nt in self._texts[1].values():
            if n and n in nt:
                out.append({"url": e["url"], "org": e.get("org"), "org_known": bool(e.get("org_known")),
                            "published": e.get("published"), "content": raw, "title": e.get("title", ""),
                            "saved_path": e["saved_path"], "sha256": e["sha256"], "from_cache": True,
                            "relevance": relevance(kw, e.get("title", ""), raw)})
        return out

    def summary(self, today):
        pos = [e for e in self.entries.values() if e.get("saved_path") and not e.get("skip_reason")]
        return {"entries": len(pos), "in_window": len(self.within(today)), **self.stats,
                "tampered": len(self.tampered_urls)}


class KoreaKrProvider:
    """정책브리핑 사이트맵 최신 기사. 캐시가 있으면 refresh(cache) 로 새 URL 만 받아 쌓고, 없으면 __call__ 로 메모리 매칭(옛 방식)."""

    def __init__(self, fetcher, per_sitemap=None):
        # 호스트당 MAX_PAGES(40)에 맞춘다: robots 1 + 사이트맵 2 를 뺀 나머지를 사이트맵들에 균등 배분(1+2+18+18=39)
        self.f = fetcher
        self.per = per_sitemap or (MAX_PAGES - 1 - len(SITEMAPS)) // len(SITEMAPS)
        self.pages = None

    def parse_page(self, content, final):
        """기사 페이지 → 캐시/매칭용 항목. 본문 구간을 못 읽으면 None(전체로 대신하지 않음)."""
        org, pub = korea_kr_meta(content)
        if "policyBriefingView" in final:  # 브리핑 글의 author 는 기관이 아니라 대변인·국장 등 개인 → 기관 미상(호스트로)
            org = None
        seg = korea_kr_article(content)
        if not seg:
            return None
        title = page_title(content)
        doc = (f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(final)}</p>"
               f"{seg}</body></html>")
        # 게시일: JSON-LD → 기사 상단 표시일. 사이트맵 lastmod 는 수정일이라 쓰지 않는다(없으면 None + 사유)
        pub = pub or korea_kr_shown_date(seg)
        return {"url": final, "org": org or org_of(final), "org_known": org_is_known({"url": final, "org": org}),
                "published": pub, "content": doc.encode("utf-8"), "title": title,
                "date_note": None if pub else "게시일 없음(사이트맵 lastmod 는 수정일이라 쓰지 않음)"}

    def _rows(self, sm):
        try:
            body, _ = self.f.get(sm)
        except Exception:  # noqa: BLE001
            return []
        return [u for u in parse_sitemap(body) if "View.do" in u[1]]

    def refresh(self, cache, today):
        for sm in SITEMAPS:
            fresh = []
            for lastmod, url in self._rows(sm):
                d = parse_date(lastmod)
                if d is not None and (today - d).days > MAX_AGE_DAYS:  # 수정일이 30일보다 오래됐으면 게시일도 그 이전
                    continue
                if cache.has(url):
                    cache.stats["known_skipped"] += 1
                    continue
                fresh.append(url)
            for url in fresh[:self.per]:  # 최신 순으로 아직 안 받은 것만, 예산 안에서
                try:
                    content, final = self.f.get(url)
                except Exception:  # noqa: BLE001  일시 오류는 기록하지 않아 내일 다시 시도
                    continue
                e = self.parse_page(content, final)
                if e is None:
                    cache.add_negative(url, "본문 구간을 읽지 못함")
                    continue
                cache.add(e)
                if final != url:
                    cache.add_negative(url, f"리다이렉트 → {final}")

    def _load(self):
        self.pages = []
        for sm in SITEMAPS:
            for lastmod, url in self._rows(sm)[:self.per]:
                try:
                    content, final = self.f.get(url)
                except Exception:  # noqa: BLE001
                    continue
                e = self.parse_page(content, final)
                if e:
                    self.pages.append({**e, "_norm": _norm(html_to_text(e["content"]))})

    def __call__(self, kw):
        if self.pages is None:
            self._load()
        return [{**{k: v for k, v in p.items() if k != "_norm"},
                 "relevance": relevance(kw, p["title"], p["content"])} for p in self.pages if _norm(kw) in p["_norm"]]


class MohwRssProvider:
    """보건복지부 보도자료 RSS(robots 명시 Allow). 항목 → 원문 저장본(제목·링크·게시일·본문)."""

    def __init__(self, fetcher):
        self.f, self.items = fetcher, None

    def _fetch_items(self):
        try:
            body, _ = self.f.get(MOHW_RSS)
            return parse_rss_items(body)
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def entry(it):
        doc = (f"<html><head><title>{html.escape(it['title'])}</title></head><body>"
               f"<p>출처: 보건복지부 보도자료 RSS</p><p>링크: {html.escape(it['url'])}</p>"
               f"<p>게시일: {html.escape(str(it['published']))}</p><div class=\"b_content\">{html.escape(it['text'])}</div></body></html>")
        return {"url": it["url"], "org": "보건복지부", "org_known": True, "published": it["published"],
                "content": doc.encode("utf-8"), "title": it["title"]}

    def refresh(self, cache, today):
        for it in self._fetch_items():  # RSS 한 번에 본문까지 오므로 추가 요청 없음 — 새 항목·바뀐 항목만 저장
            e = self.entry(it)
            old = cache.entries.get(e["url"])
            if old and old.get("sha256") == hashlib.sha256(e["content"]).hexdigest():
                cache.stats["known_skipped"] += 1
            else:
                cache.add(e)

    def __call__(self, kw):
        if self.items is None:
            self.items = self._fetch_items()
        out = []
        for it in self.items:
            if _norm(kw) in _norm(it["title"] + it["text"]):
                e = self.entry(it)
                out.append({**e, "relevance": relevance(kw, it["title"], e["content"])})
        return out


def parse_moel_list(raw):
    """고용노동부 보도자료 목록 → [(news_seq, title)] 최신(번호 큰 순)"""
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    seen, out = set(), []
    for m in re.finditer(r'<a\s[^>]*?href="enewsView\.do\?news_seq=(\d+)"[^>]*>', s):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        t = re.search(r'title="([^"]*)"', m.group(0))
        out.append((m.group(1), html.unescape(t.group(1)).strip() if t else ""))
    out.sort(key=lambda x: int(x[0]), reverse=True)
    return out


def parse_moel_view(raw):
    """고용노동부 보도자료 상세 → (등록일 문자열|None, 본문 HTML 조각)"""
    s = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    d = re.search(r"<dt>\s*등록일\s*</dt>\s*<dd>\s*(\d{4}-\d{2}-\d{2})", s)
    i = s.find('class="b_info"')
    if i < 0:
        return (d.group(1) if d else None), ""
    j = s.find("synap_view", i)
    return (d.group(1) if d else None), s[i:(j if j > i else i + 20000)]


class MoelProvider:
    """고용노동부 보도자료. 캐시가 있으면 새 번호만 상세 요청(최대 N건), 없으면 최신 N건 메모리 매칭(옛 방식)."""

    def __init__(self, fetcher, n=MOEL_ITEMS):
        self.f, self.n, self.items = fetcher, n, None

    def _rows(self):
        try:
            body, _ = self.f.get(MOEL_LIST)
            return parse_moel_list(body)
        except Exception:  # noqa: BLE001
            return []

    def _fetch_one(self, seq, title):
        """상세 1건 → (항목 | None=본문 못 읽음 | False=요청 실패)"""
        url = MOEL_VIEW + seq
        try:
            raw, final = self.f.get(url)
        except Exception:  # noqa: BLE001
            return False
        pub, frag = parse_moel_view(raw)
        if not frag:
            return None
        doc = f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(url)}</p>{frag}</body></html>"
        return {"url": url, "org": "고용노동부", "org_known": True, "published": pub,
                "content": doc.encode("utf-8"), "title": title}

    def refresh(self, cache, today):
        fresh = []
        for seq, title in self._rows():
            if cache.has(MOEL_VIEW + seq):
                cache.stats["known_skipped"] += 1
            else:
                fresh.append((seq, title))
        for seq, title in fresh[:self.n]:
            e = self._fetch_one(seq, title)
            if e is False:
                continue
            if e is None:
                cache.add_negative(MOEL_VIEW + seq, "본문 구간을 읽지 못함")
            else:
                cache.add(e)

    def _load(self):
        self.items = []
        for seq, title in self._rows()[:self.n]:
            e = self._fetch_one(seq, title)
            if e:
                self.items.append({**e, "_norm": _norm(html_to_text(e["content"]))})

    def __call__(self, kw):
        if self.items is None:
            self._load()
        return [{**{k: v for k, v in i.items() if k != "_norm"}, "relevance": relevance(kw, i["title"], i["content"])}
                for i in self.items if _norm(kw) in i["_norm"]]


def default_discover(fetcher=None, cache=None, today=None, cache_dir=None):
    """기본 출처 탐색. 첫 호출 때 각 provider 가 '아직 안 받은 새 URL 만' 받아 캐시에 쌓고(요청 상한은 그대로),
    키워드 매칭은 캐시 전체 중 게시 30일 이내 기사에서 한다. discover.summary() 로 캐시 상태를 본다."""
    f = fetcher or PoliteFetcher()
    cache = cache or SourceCache(cache_dir)
    day = today or dt.date.today()
    providers = [KoreaKrProvider(f), MohwRssProvider(f), MoelProvider(f)]
    state = {"refreshed": False}

    def discover(kw):
        if not state["refreshed"]:
            state["refreshed"] = True
            for p in providers:
                p.refresh(cache, day)
        return cache.match(kw, day)

    def summary():
        out = cache.summary(day)
        out["requests"] = dict(getattr(f, "count", {}))
        return out
    discover.summary = summary
    discover.cache = cache
    return discover


def screen(cands, today, domains, max_age=MAX_AGE_DAYS):
    """G1 거름망 → (통과 목록, 버림 사유 목록[{url, reason}]). 통과 항목에 published_date 부여."""
    keep, drop, seen = [], [], set()
    for c in cands:
        url = c.get("url", "")
        if not C.is_official_url(url, domains):
            drop.append({"url": url, "reason": "비공식 도메인"})
        elif url in seen:
            continue
        elif not c.get("content"):
            drop.append({"url": url, "reason": "본문 없음"})
        elif c.get("relevance") and not c["relevance"][0]:
            seen.add(url)
            drop.append({"url": url, "reason": c["relevance"][1]})
        else:
            seen.add(url)
            d = parse_date(c.get("published"))
            if d is None:
                drop.append({"url": url, "reason": c.get("date_note") or "게시일 읽지 못함"})
            elif (today - d).days > max_age:
                drop.append({"url": url, "reason": f"게시일 {d.isoformat()} — {(today - d).days}일 경과(>{max_age}일)"})
            elif (today - d).days < 0:
                drop.append({"url": url, "reason": f"게시일 {d.isoformat()} 이 미래"})
            else:
                keep.append({**c, "published_date": d.isoformat()})
    return keep, drop


def group_releases(keep):
    """같은 보도자료 재게시를 묶어 각 후보에 dup_of(대표 URL, 대표 자신은 None)를 붙인다. 대표 = 기관 확인된 것 우선, 게시일 빠른 순.
    돌려주는 값: 대표 후보 목록(기관 수는 이것만으로 센다)."""
    groups = []
    for c in keep:
        for g in groups:
            if any(same_release(c, m) for m in g):
                g.append(c)
                break
        else:
            groups.append([c])
    reps = []
    for g in groups:
        rep = min(g, key=lambda x: (not org_is_known(x), x["published_date"]))
        for c in g:
            c["dup_of"] = None if c is rep else rep["url"]
        reps.append(rep)
    return reps


def run(acc, today=None, fetchers=None, ledger_dir=None, sources_dir=None, notify=None, min_sources=MIN_SOURCES,
        gate=True, stop_file=None, cache_dir=None):
    """gate=True(기본): STOP 파일·paused 면 아무것도 하지 않고 {'status':'gated'} 를 돌려준다(원장 기록 없음). T-09 도 단계마다 재확인."""
    if gate:
        ok_gate, why_gate = C.run_gate(acc, stop_file) if stop_file else C.run_gate(acc)
        if not ok_gate:
            return {"status": "gated", "reason": why_gate, "account_id": acc.get("account_id"), "kw": None, "n_sources": 0}
    today = today or dt.date.today()
    day = today.isoformat()
    domains = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
    discover = (fetchers or {}).get("discover") or default_discover(today=today, cache_dir=cache_dir)
    out_dir = os.path.join(sources_dir or SOURCES_DIR, day)
    base = {"date": day, "account_id": acc["account_id"]}

    def final(status, reason, kw, saved=(), tried=(), evidence=None):
        rec = ledger.append("research_ledger", {
            **base, "type": "run", "kw": kw, "status": status, "reason": reason, "n_sources": len(saved),
            "orgs": sorted({s["org"] for s in saved if s.get("org_known")}), "source_urls": [s["url"] for s in saved],
            "tried": list(tried), "evidence": evidence,
            "cache": discover.summary() if callable(getattr(discover, "summary", None)) else None}, ledger_dir)
        if status == "hold" and notify:
            notify("warn", f"[{acc['account_id']}] 공식 출처 부족 — 카드뉴스 보류", reason)
        return rec

    cands_kw, why = candidate_keywords(acc["account_id"], today, ledger_dir)
    if not cands_kw:
        return final("hold", why, None)

    tried = []
    for rank, ck in enumerate(cands_kw, 1):
        kw = ck["kw"]
        meta = {"rank": rank, "src": ck["src"], "evidence": "indicator" if ck["evidence"] else "none"}
        try:
            cands = discover(kw) or []
        except Exception as e:  # noqa: BLE001
            ledger.append("research_ledger", {**base, "type": "try", **meta, "kw": kw, "adopted": False,
                                              "reason": f"출처 검색 실패: {e!r}"[:200]}, ledger_dir)
            tried.append(kw)
            continue
        keep, drop = screen(cands, today, domains)
        reps = group_releases(keep)
        orgs = {_norm(c.get("org") or org_of(c["url"])) for c in reps if org_is_known(c)}
        n_unknown = sum(1 for c in keep if not org_is_known(c))
        n_dup = sum(1 for c in keep if c.get("dup_of"))
        ok = len(orgs) >= min_sources
        unk = (f", 기관 미상 {n_unknown}건 제외" if n_unknown else "") + (f", 같은 보도자료 재게시 {n_dup}건 합산" if n_dup else "")
        reason = (f"확인된 서로 다른 기관 {len(orgs)}곳 채움{unk}" if ok
                  else f"확인된 서로 다른 기관 {len(orgs)}곳 (최소 {min_sources}곳 필요){unk}")
        ledger.append("research_ledger", {
            **base, "type": "try", **meta, "kw": kw, "adopted": ok, "reason": reason,
            "candidates": len(cands), "kept": [c["url"] for c in keep], "dropped": drop}, ledger_dir)
        tried.append(kw)
        if not ok:
            continue
        saved = []
        for c in keep:
            content = c["content"]
            sha = hashlib.sha256(content).hexdigest()
            if c.get("saved_path") and c.get("sha256") == sha:  # 캐시 저장본을 그대로 가리킨다(verify 가 sha256 재확인)
                path = c["saved_path"]
            else:
                path = os.path.join(out_dir, f"{sha[:12]}_{org_of(c['url'])}.html")
                os.makedirs(out_dir, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(content)
            saved.append(ledger.append("source_ledger", {
                "url": c["url"], "org": c.get("org") or org_of(c["url"]), "title": c.get("title", ""),
                "published": c["published_date"], "fetched_at": ledger.now_iso(), "sha256": sha,
                "saved_path": path, "kw": kw, "org_known": org_is_known(c), "dup_of": c.get("dup_of")}, ledger_dir))
        note = "" if ck["evidence"] else "; evidence=none(지표 근거 없음, 공식 출처만 있음)"
        return final("ok", f"{reason}; 채택 키워드 {kw!r}(시도 {rank}번째, {ck['src']}), 저장 {len(saved)}건{note}",
                     kw, saved, tried, evidence=meta["evidence"])
    return final("hold", f"시도 {len(cands_kw)}개 키워드 모두 공식 출처(확인된 기관) {min_sources}곳을 못 채움: {', '.join(tried)}",
                 None, (), tried)


if __name__ == "__main__":
    import sys
    acc = C.load_account(sys.argv[1] if len(sys.argv) > 1 else "test")
    ok, why = C.run_gate(acc)
    if not ok:
        print("중단:", why)
        sys.exit(0)
    from . import alert
    r = run(acc, notify=alert.send)
    print(json.dumps({k: r[k] for k in ("status", "reason", "kw", "evidence", "n_sources", "orgs", "source_urls", "tried")},
                     ensure_ascii=False, indent=1))
    for s in ledger.read("source_ledger")[-r["n_sources"]:] if r["n_sources"] else []:
        print(s["kw"], s["org"], s["published"], s["url"])
    print("source_ledger:", os.path.join(ledger.LEDGER_DIR, "source_ledger.jsonl"))
