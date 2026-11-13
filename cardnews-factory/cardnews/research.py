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
 B3) 금융위원회 보도자료(https://www.fsc.go.kr/no010101 → /no010101/<번호>): robots.txt 는 User-agent:* Allow:/ , 키 불필요,
    상세에 등록일(YYYY-MM-DD)과 본문 전문. 기관=금융위원회.
 B4) 산업통상부 보도·참고자료(https://www.motir.go.kr/kor/article/ATCL3f49a5a8c → /<번호>/view): robots.txt 는 /kor/search·/search·
    /attach/viewer 만 Disallow. 상세에 등록일과 본문 전문. 옛 주소 motie.go.kr 은 motir.go.kr 로 301(robots.txt 요청이 리다이렉트라
    우리 fetcher 는 옛 주소를 차단으로 본다 → 새 주소만 사용). 기관=산업통상부.
 C2) T-04g 추가 조사에서 제외(2026-11-12 실측):
    - 식품의약품안전처 mfds.go.kr: 보도자료 RSS(/www/rss/brd.do?brdId=ntc0021)는 되지만 항목에 본문이 없고(content:encoded 가 제목과 같음),
      상세(/brd/m_99/view.do?seq=N)도 제목+첨부파일(hwpx·pdf) 링크뿐 → 본문을 못 읽어 G2 불가.
    - 여성가족부 mogef.go.kr: /robots.txt 가 400 → 규칙 확인 불가라 차단으로 봄(RSS 주소 /hg/rss/hg_rss_f001.do 는 있으나 사용 안 함).
    - 국토교통부 molit.go.kr: /robots.txt 가 307 리다이렉트(응답 없음) → 규칙 확인 불가.
    - 행정안전부 mois.go.kr·질병관리청 kdca.go.kr: 첫 화면이 스크립트/메타 리프레시뿐이라 보도자료 목록 주소를 키 없이 찾지 못함
      (robots.txt 자체는 허용 — 목록 URL 확인 시 추가 후보).
    - 재정경제부(구 기획재정부) mofe.go.kr: robots 는 /sch/schMain.do·/id/qustnr.do 만 Disallow 이나 목록이 세션 ID(;jsessionid) 링크·
      스크립트 상세라 안정적으로 파싱하지 못함(추가 후보).
    - 중소벤처기업부 mss.go.kr: robots Allow:/ 이나 목록의 상세 링크를 찾지 못함(첨부 다운로드 링크만 확인) — 추가 후보.
 C) 제외(2026-11-12 실측):
    - (국민연금공단 nps.or.kr: T-04h 에서 추가됨 — D 참조)
    - 국민건강보험공단 nhis.or.kr: https://www.nhis.or.kr/robots.txt 가 'Disallow : /nhis/' — 보도자료 목록
      (/nhis/together/wbhaea01600m01.do)이 이 아래라 불허로 판단, 사용 안 함.
    - (국세청 nts.go.kr: T-04h 에서 추가됨 — D 참조. 옛 판단 '상세 POST 전용' 은 인자 없이 GET 한 결과였고, 인자를 다 주면 GET 으로 읽힌다)
    - 복지로 bokjiro.go.kr: /robots.txt 요청에 HTML 응답 — 규칙 확인 불가.
    - 정책브리핑 RSS(서비스 중단 공지 https://www.korea.kr/etc/noticeView.do?newsId=132038885),
    정책브리핑 검색 totalSearch.do(GET 응답에 결과 없음·스크립트 렌더), 정부24(robots 거의 전면 Disallow),
    복지로(robots.txt 확인 불가), 공공데이터포털·법령정보센터 OpenAPI(인증키 필요).
 알려진 한계(T-04h2, 이번엔 고치지 않음):
    - _RobotRules: 경로의 퍼센트 인코딩(%7E 등)을 정규화하지 않고 비교한다(규칙·URL 인코딩이 다르면 어긋날 수 있음).
    - 음성 캐시('본문 구간을 읽지 못함'·한국은행 '붙임 문서 참조')는 영구 기록이라, 나중에 본문이 채워져도 다시 받지 않는다.
    - _RobotRules: User-agent 부분일치(우리 토큰이 에이전트 줄에 '포함'되면 일치) — 표준의 제품 토큰 비교보다 느슨할 수 있다.
 D) T-04h 추가(2026-11-13 실측, 목록 1회+상세 1~2건):
    - 국세청 nts.go.kr: 목록 /nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028 (HTTP 200, 10건) 의 <a class="nttInfoBtn" data-id=글번호> 가
      자바스크립트 폼 제출이지만 상세 /nts/na/ntt/selectNttInfo.do?bbsId=1028&mi=2201&nttSn=글번호 를 GET 으로 받으면 본문 전문과 작성일자가 읽힌다(200).
    - 한국은행 bok.or.kr: robots.txt 가 'Disallow: /' + 'Allow: /portal/' — 파이썬 robotparser(첫 규칙 우선)는 전부 불허로 읽어서 RFC 9309(가장 긴 경로
      규칙 우선)로 읽는 _RobotRules 로 바꿨다(허용 경로 /portal/ 만 열리고 나머지는 그대로 막힘). 목록 페이지(/portal/singl/newsData/list.do?menuNo=201263)는
      자바스크립트 뼈대라, 페이지 자체가 쓰는 /portal/singl/newsData/listCont.do 조각을 GET(분류가 '보도자료'인 행만). 상세 본문은 '붙임 문서 참조'뿐인
      항목이 많아 본문 200자 미만이면 '본문 구간을 읽지 못함'으로 캐시에 기록(재요청 없음).
    - 국민연금공단 nps.or.kr: robots 는 /search/ 등만 Disallow. 목록 /pnsgdnc/nscvrgdata/getOHAE0002M0List.do?menuId=MN24000898 (200, 10건),
      상세 getOHAE0002M1.do?...&pstId=글번호 에 본문(view-contents-wrap)과 등록일(2026/11/12 형식).
    - 금융감독원 fss.or.kr: /robots.txt 요청에 연결이 끊김(www·비www 모두 2회 ConnectionError) → 규칙 확인 불가라 차단으로 봄. 제외.
    - 문화체육관광부 mcst.go.kr: 목록(/site/s_notice/press/pressList.jsp, robots Allow:/)·상세(pressView.jsp?pSeq=N, 게시일 있음)는 읽히지만 본문이
      Synap 문서뷰어 iframe(/attachFiles/viewer/skin/doc.html, 내용은 자바스크립트가 서버 변환본을 불러옴)이라 서버 응답에 본문 텍스트가 없다 → G2 불가. 제외.
준수(실행당 총 TOTAL_MAX_PAGES=200·호스트별 몫 HOST_CAPS, 근거는 상수 주석): robots.txt 를 호스트별로 읽어 허용 URL 만 요청, 요청 간 1.2초, 실행당 호스트별 MAX_PAGES(40)건 이하, 로그인·우회 없음.
네트워크는 전부 주입 가능: run(..., fetchers={"discover": f(kw)->[{"url","org","published","content"(bytes),"title"}]}).
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import secrets
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
# 실행당 총 요청 상한과 기관(호스트)별 몫 (T-04g). 호스트당 40 은 그대로 두고, 전체가 부풀지 않게 총 200 을 둔다.
# 근거: 200 요청 × 1.2초 = 최대 4분(한 번 실행이 너무 길어지지 않는 선). 현재 몫 합계는 90(여유 110 = 기관을 더 붙일 자리).
# 몫 = robots 1 + 목록/RSS 1 + 상세 N(=12) 를 기관마다 맞춘 값. korea.kr 만 사이트맵·기사 36건이라 40 을 다 쓴다.
TOTAL_MAX_PAGES = 200
HOST_CAPS = {"korea.kr": 40, "mohw.go.kr": 5, "moel.go.kr": 15, "fsc.go.kr": 15, "motir.go.kr": 15,
             "nts.go.kr": 15, "bok.or.kr": 15, "nps.or.kr": 15}  # T-04h: 새 호스트 각 15 (robots 1 + 목록 1 + 상세 12 = 14)
LIST_ITEMS = 12          # 목록형 기관(고용노동부·금융위·산업통상부)에서 실행마다 새로 받는 상세 페이지 상한
FSC_LIST = "https://www.fsc.go.kr/no010101"
FSC_VIEW = "https://www.fsc.go.kr/no010101/"
MOTIR_LIST = "https://www.motir.go.kr/kor/article/ATCL3f49a5a8c"
MOTIR_VIEW = "https://www.motir.go.kr/kor/article/ATCL3f49a5a8c/"
NTS_LIST = "https://www.nts.go.kr/nts/na/ntt/selectNttList.do?mi=2201&bbsId=1028"
NTS_VIEW = "https://www.nts.go.kr/nts/na/ntt/selectNttInfo.do?bbsId=1028&mi=2201&nttSn="
BOK_LIST = "https://www.bok.or.kr/portal/singl/newsData/listCont.do?menuNo=201263&pageIndex=1&syncMenuChekKey=1"
BOK_BASE = "https://www.bok.or.kr"
NPS_LIST = "https://www.nps.or.kr/pnsgdnc/nscvrgdata/getOHAE0002M0List.do?menuId=MN24000898"
NPS_VIEW = "https://www.nps.or.kr/pnsgdnc/nscvrgdata/getOHAE0002M1.do?menuId=MN24000898&hmpgCd=01&hmpgBbsCd=BS20240145&pstId="
MIN_BODY_CHARS = 200     # 본문이 이보다 짧으면(예: 한국은행 '붙임 문서를 참조') 읽을 본문 없음으로 보고 캐시에 '본문 구간을 읽지 못함' 기록
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
    if m:  # 표지가 든 여는 태그의 끝('>')부터 — 태그 조각이 본문 앞머리에 글자로 남지 않게
        gt = s.find(">", m.end())
        s = s[gt + 1:] if gt >= 0 else s[m.end():]
    t = html_to_text(strip_chrome(s))
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


def counts_as_agency(c, domains=None):
    """기관 수에 들어가는 후보인가 — verify G1 과 같은 판정(verify.counts_as_agency)을 그대로 호출. 기관명 또는 None."""
    from . import verify  # verify 가 research 를 import 하므로 호출 시점에 가져온다(순환 방지)
    return verify.counts_as_agency({"url": c.get("url", ""), "org": c.get("org") or org_of(c.get("url", "")),
                                    "org_known": org_is_known(c)}, domains)


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
class _RobotRules:
    """robots.txt 해석 — RFC 9309: 우리 토큰과 가장 구체적으로 맞는 그룹(없으면 *)에서 '가장 긴 경로 규칙'이 이기고(같으면 Allow),
    * 와 $ 를 지원한다. 파이썬 urllib.robotparser 는 위에서부터 첫 규칙을 쓰므로 'Disallow: / 다음 Allow: /portal/'(한국은행)을
    전부 불허로 읽는다 — 표준대로 읽어 명시 허용 경로만 열고, 그 밖은 계속 막는다."""

    def __init__(self):
        self.groups = []  # [(agents[lower], [(allow, pattern)])]

    def parse(self, lines):
        agents, rules, in_rules = [], [], False
        self.groups = []
        for raw in lines:
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = (x.strip() for x in line.split(":", 1))
            k = k.lower()
            if k == "user-agent":
                if in_rules:
                    self.groups.append((agents, rules))
                    agents, rules, in_rules = [], [], False
                agents.append(v.lower())
            elif k in ("allow", "disallow"):
                in_rules = True
                if v:  # 빈 Disallow = 전부 허용(규칙 없음)
                    rules.append((k == "allow", v))
        if agents:
            self.groups.append((agents, rules))

    @staticmethod
    def _match_len(pattern, path):
        """pattern 이 path 앞부분과 맞으면 pattern 길이, 아니면 -1."""
        rx = re.escape(pattern).replace(r"\*", ".*")
        if rx.endswith(r"\$"):
            rx = rx[:-2] + "$"
        return len(pattern) if re.match(rx, path) else -1

    def can_fetch(self, token, url):
        p = urlparse(url)
        path = (p.path or "/") + (("?" + p.query) if p.query else "")
        tok = token.lower()
        best_len, best, star = -1, None, None
        for agents, rules in self.groups:   # 같은 User-agent 그룹이 여러 번 나오면 규칙을 병합(RFC 9309 2.2.1)
            for a in agents:
                if a == "*":
                    star = (star or []) + rules
                elif a and a in tok:
                    if len(a) > best_len:
                        best_len, best = len(a), list(rules)
                    elif len(a) == best_len:
                        best = best + rules
        rules = best if best is not None else star
        if rules is None:
            return True
        win = None  # (길이, allow)
        for allow, pat in rules:
            n = self._match_len(pat, path)
            if n >= 0 and (win is None or n > win[0] or (n == win[0] and allow)):
                win = (n, allow)
        return True if win is None else win[1]


class PoliteFetcher:
    """robots.txt 준수 + 요청 간격 + 호스트당 상한. requests 는 여기서만 import.
    robots.txt 요청도 같은 간격·호스트 카운터에 들어간다. 리다이렉트는 직접 따라가며 매 홉마다
    공식 도메인·robots·호스트 상한을 다시 적용한다(공식 밖으로 나가는 리다이렉트는 거부)."""

    def __init__(self, max_pages=MAX_PAGES, interval=MIN_INTERVAL, sleep=time.sleep, domains=None,
                 max_total=TOTAL_MAX_PAGES, host_caps=None):
        self.max_pages, self.interval, self.sleep = max_pages, interval, sleep
        self.max_total = max_total
        self.host_caps = HOST_CAPS if host_caps is None else host_caps  # 호스트별 몫(없으면 max_pages). 둘 중 작은 값 적용
        self.total = 0
        self.count, self.last, self.robots = {}, 0.0, {}
        self.domains = domains or C.load_json(os.path.join(C.CONFIG, "official_domains.json"))

    def _tick(self, url):
        """요청 1건을 호스트 카운터·간격에 반영(robots 포함). 상한이면 예외."""
        host = org_of(url)
        cap = min(self.max_pages, self.host_caps.get(host, self.max_pages))
        if self.count.get(host, 0) >= cap:
            raise RuntimeError(f"호스트 상한 도달: {host} {cap}건")
        if self.total >= self.max_total:
            raise RuntimeError(f"실행당 총 상한 도달: {self.max_total}건")
        wait = self.interval - (time.monotonic() - self.last)
        if wait > 0:
            self.sleep(wait)
        self.last = time.monotonic()
        self.count[host] = self.count.get(host, 0) + 1
        self.total += 1

    def _allowed(self, url):
        import requests
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self.robots:
            rp = _RobotRules()
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


def resolve_saved_path(e, cache_dir):
    """index 의 saved_path 가 상대경로(새 줄)면 cache 디렉터리 기준 절대경로로 되돌린다. 옛 절대경로 줄은 그대로.
    SourceCache 와 verify.common_tokens 가 같이 쓴다(T-SRC4 — 해석 규칙 하나)."""
    sp = e.get("saved_path")
    if sp and not os.path.isabs(sp):
        e = {**e, "saved_path": os.path.normpath(os.path.join(cache_dir, sp))}
    return e


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
                            self.entries[e["url"]] = self._resolve(e)

    def _resolve(self, e):
        return resolve_saved_path(e, self.dir)

    def _relative(self, path):
        try:
            return os.path.relpath(path, self.dir).replace(os.sep, "/")
        except ValueError:  # 다른 드라이브 — 상대화 불가, 절대경로 그대로
            return path

    def has(self, url):
        return url in self.entries

    def _append(self, rec):
        os.makedirs(self.dir, exist_ok=True)
        rec = {"cached_at": ledger.now_iso(), **rec}
        disk = {**rec, "saved_path": self._relative(rec["saved_path"])} if rec.get("saved_path") else rec
        with open(self.index, "a", encoding="utf-8") as f:
            f.write(json.dumps(disk, ensure_ascii=False) + "\n")
        self.entries[rec["url"]] = self._resolve(disk)
        self._texts = None
        return self.entries[rec["url"]]

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

    @staticmethod
    def saved_date(raw):
        """저장본 자체에서 다시 뽑은 게시일(date) — index 의 published 값은 믿지 않는다. 못 뽑으면 None."""
        s_ = raw.decode("utf-8", "replace")
        for pat in (r"<p>게시일: ([^<]+)</p>", r"<dt>\s*등록일\s*</dt>\s*<dd>\s*(\d{4}-\d{2}-\d{2})",
                    r"<em>\s*등록일\s*</em>\s*<span>\s*(\d{4}-\d{2}-\d{2})",
                    r'<div class="day">\s*<span>\s*(\d{4}-\d{2}-\d{2})'):
            m = re.search(pat, s_)
            d = parse_date(m.group(1)) if m else None
            if d:
                return d
        return parse_date(korea_kr_shown_date(s_))

    def within(self, today, max_age=MAX_AGE_DAYS):
        """30일 창 안의 항목. 게시일은 저장본에서 다시 뽑은 값(sha 가 다르거나 못 읽거나 날짜를 못 뽑으면 제외)."""
        out = []
        for e in self.entries.values():
            if e.get("skip_reason") or not e.get("saved_path"):
                continue
            raw = self.read(e)
            if raw is None:
                continue
            d = self.saved_date(raw)
            if d is not None and 0 <= (today - d).days <= max_age:
                out.append({**e, "published": d.isoformat()})
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

class AllHostsFailed(RuntimeError):
    """모든 수집처(호스트)가 비-HTTP 예외로 실패 — run 이 status=error 로 기록한다."""


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
        # 게시일: JSON-LD → 기사 상단 표시일. 사이트맵 lastmod 는 수정일이라 쓰지 않는다(없으면 None + 사유)
        pub = pub or korea_kr_shown_date(seg)
        pd = parse_date(pub)  # 저장본 안에 게시일을 박아 둔다 — 캐시가 index 값이 아니라 저장본에서 날짜를 다시 읽는다
        doc = (f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(final)}</p>"
               + (f"<p>게시일: {pd.isoformat()}</p>" if pd else "") + f"{seg}</body></html>")
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


# ---------- 금융위원회·산업통상부 (T-04g) ----------
def parse_fsc_list(raw):
    """금융위 보도자료 목록 → [(상세 URL, 제목)] 최신(번호 큰 순)"""
    s_ = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    seen, out = set(), []
    for m in re.finditer(r'<a[^>]+href="/no010101/(\d+)[^"]*"[^>]*>(.*?)</a>', s_, re.S):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        # 목록 앵커 글은 '제목. 금일 등록된 게시글' 처럼 꼬리표가 붙을 수 있다
        title = re.sub(r"[.\s]*금일 등록된 게시글.*$", "", title).strip()
        out.append((FSC_VIEW + m.group(1), title))
    out.sort(key=lambda x: int(x[0].rsplit("/", 1)[1]), reverse=True)
    return out


def parse_fsc_view(raw, url, title=""):
    """금융위 상세 → 항목(본문 구간+등록일) 또는 None(본문 구간·날짜를 못 읽음)"""
    s_ = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    i = s_.find('class="board-view-wrap"')
    if i < 0:
        return None
    j = s_.find("이전글", i)
    seg = strip_chrome(re.sub(r"(?is)<script\b.*?</script>", " ", s_[i:(j if j > i else i + 40000)]))
    d = re.search(r'<div class="day">\s*<span>\s*(\d{4}-\d{2}-\d{2})', s_[i:])
    t = re.search(r'<div class="subject">(.*?)</div>', s_[i:], re.S)
    title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.group(1)))).strip() if t else title
    doc = (f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(url)}</p>"
           f'<div class="b_content">{seg}</div></body></html>')
    return {"url": url, "org": "금융위원회", "org_known": True, "published": d.group(1) if d else None,
            "content": doc.encode("utf-8"), "title": title,
            "date_note": None if d else "게시일 읽지 못함"}


def parse_motir_list(raw):
    """산업통상부 보도·참고자료 목록 → [(상세 URL, 제목)] 최신(번호 큰 순)"""
    s_ = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    seen, out = set(), []
    for m in re.finditer(r'<a[^>]+href="/kor/article/ATCL3f49a5a8c/(\d+)/view[^"]*"[^>]*>(.*?)</a>', s_, re.S):
        if m.group(1) in seen:
            continue
        seen.add(m.group(1))
        title = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        out.append((f"{MOTIR_VIEW}{m.group(1)}/view", title))
    out.sort(key=lambda x: int(x[0].split("/")[-2]), reverse=True)
    return out


def parse_motir_view(raw, url, title=""):
    s_ = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw
    i = s_.find('class="cont-tit"')
    if i < 0:
        return None
    k0 = s_.find("본문 시작", i)  # 제목 영역 바로 뒤의 '페이지 공유·프린트' 버튼 문구를 건너뛰고 본문부터
    if k0 > i:
        e0 = s_.find("-->", k0)
        start = e0 + 3 if e0 > 0 else k0
    else:
        start = i
    j = min([k for k in (s_.find(mk, start) for mk in ("이전글", "다음글")) if k > start] or [start + 30000])
    seg = strip_chrome(re.sub(r"(?is)<(script|style|link)\b[^>]*>(?:.*?</\1>)?", " ", s_[start:j]))
    seg = re.sub(r"(?is)<div[^>]*page-share.*?(?:프린트|print).*?</div>", " ", seg)
    d = re.search(r"<em>\s*등록일\s*</em>\s*<span>\s*(\d{4}-\d{2}-\d{2})", s_[i:])
    doc = (f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(url)}</p>"
           f'<div class="b_content">{seg}</div></body></html>')
    return {"url": url, "org": "산업통상부", "org_known": True, "published": d.group(1) if d else None,
            "content": doc.encode("utf-8"), "title": title, "date_note": None if d else "게시일 읽지 못함"}


def _detail_doc(title, url, date_iso, seg):
    """저장본 공통 틀 — 게시일을 '<p>게시일: …</p>' 로 박아 캐시가 저장본에서 날짜를 다시 읽게 한다."""
    return (f"<html><head><title>{html.escape(title)}</title></head><body><p>링크: {html.escape(url)}</p>"
            + (f"<p>게시일: {date_iso}</p>" if date_iso else "") + f'<div class="b_content">{seg}</div></body></html>')


def _iso(s):
    d = parse_date(s)
    return d.isoformat() if d else None


def _clean_seg(seg):
    seg = seg[seg.find(">") + 1:] if seg.lstrip()[:1] != "<" and ">" in seg[:200] else seg  # 표지 태그 중간(class="…">)부터 잘린 머리 조각 제거
    return strip_chrome(re.sub(r"(?is)<(script|style|link)\b[^>]*>(?:.*?</\1>)?", " ", seg))


def _plain(frag):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<!--.*?-->|<[^>]+>", " ", frag, flags=re.S))).strip()


def _decode(raw):
    return raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else raw


def parse_nts_list(raw):
    """국세청 보도자료 목록 → [(상세 URL, 제목)] 최신순. 항목은 <a class="nttInfoBtn" data-id=글번호 title=제목>(자바스크립트 폼 제출).
    상세는 같은 값으로 GET selectNttInfo.do?bbsId=1028&mi=2201&nttSn=글번호 가 읽힌다(2026-11-13 실측)."""
    s_ = _decode(raw)
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]*\bdata-id="(\d+)"[^>]*\btitle="([^"]*)"[^>]*class="nttInfoBtn"', s_):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((NTS_VIEW + m.group(1), html.unescape(m.group(2)).strip()))
    return out


def parse_nts_view(raw, url, title=""):
    s_ = _decode(raw)
    i = s_.find('class="bbsV_cont"')
    if i < 0:
        return None
    j = s_.find("bbsV_atchmnfl", i)
    seg = _clean_seg(s_[i:(j if j > i else i + 60000)])
    if len(html_to_text(seg).strip()) < MIN_BODY_CHARS:
        return None
    d = re.search(r"작성일자\s*</strong>\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})", s_)
    t = re.search(r'<div class="bbs_ViewA">\s*<h3>(.*?)</h3>', s_, re.S)
    title = _plain(t.group(1)) if t else title
    iso = _iso(d.group(1)) if d else None
    return {"url": url, "org": "국세청", "org_known": True, "published": iso,
            "content": _detail_doc(title, url, iso, seg).encode("utf-8"), "title": title,
            "date_note": None if iso else "게시일 읽지 못함"}


def parse_bok_list(raw):
    """한국은행 뉴스/자료 목록 조각(listCont.do) → [(상세 URL, 제목)]. 분류가 '보도자료' 인 것만(주간보도계획·공개시장운영 공지 등 제외)."""
    s_ = _decode(raw)
    out = []
    for m in re.finditer(r'<li class="bbsRowCls">(.*?)</li>', s_, re.S):
        blk = m.group(1)
        kind = re.search(r'<span class="t1">\s*(.*?)\s*</span>', blk, re.S)
        a = re.search(r'<a href="([^"]+/view\.do\?[^"]*nttId=\d+[^"]*)"[^>]*class="title"[^>]*>(.*?)</a>', blk, re.S)
        if not (kind and a and kind.group(1).strip() == "보도자료"):
            continue
        out.append((urljoin(BOK_BASE, html.unescape(a.group(1))), _plain(a.group(2))))
    return out


def parse_bok_view(raw, url, title=""):
    s_ = _decode(raw)
    i = s_.find('class="dbdata"')
    if i < 0:
        return None
    j = s_.find("</form>", i)
    seg = _clean_seg(s_[i:(j if j > i else i + 40000)])
    if len(html_to_text(seg).strip()) < MIN_BODY_CHARS:  # '붙임 문서를 참조' 처럼 본문이 첨부파일뿐
        return None
    d = re.search(r'<dd class="date">\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})', s_)
    t = re.search(r'<h2 class="subject">(.*?)</h2>', s_, re.S)
    title = _plain(t.group(1)) if t else title
    iso = _iso(d.group(1)) if d else None
    return {"url": url, "org": "한국은행", "org_known": True, "published": iso,
            "content": _detail_doc(title, url, iso, seg).encode("utf-8"), "title": title,
            "date_note": None if iso else "게시일 읽지 못함"}


def parse_nps_list(raw):
    """국민연금공단 보도자료 목록 → [(상세 URL, 제목)] 최신순. 링크 href 의 pstId 로 상세 GET."""
    s_ = _decode(raw)
    out, seen = [], set()
    for m in re.finditer(r'<a href="[^"]*getOHAE0002M1\.do\?[^"]*pstId=([A-Za-z0-9]+)[^"]*">(.*?)</a>', s_, re.S):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((NPS_VIEW + m.group(1), _plain(m.group(2))))
    return out


def parse_nps_view(raw, url, title=""):
    s_ = _decode(raw)
    i = s_.find('class="view-contents-wrap"')
    if i < 0:
        return None
    j = min([k for k in (s_.find(mk, i) for mk in ("이전글", "다음글", "bottom-btns")) if k > i] or [i + 60000])
    seg = _clean_seg(s_[i:j])
    if len(html_to_text(seg).strip()) < MIN_BODY_CHARS:
        return None
    d = re.search(r"<th[^>]*>\s*등록일\s*</th>\s*<td[^>]*>\s*(\d{4}[-./]\d{1,2}[-./]\d{1,2})", s_)
    t = re.search(r'<td[^>]*class="view-title"[^>]*>(.*?)</td>', s_, re.S)
    title = _plain(t.group(1)) if t else title
    iso = _iso(d.group(1)) if d else None
    return {"url": url, "org": "국민연금공단", "org_known": True, "published": iso,
            "content": _detail_doc(title, url, iso, seg).encode("utf-8"), "title": title,
            "date_note": None if iso else "게시일 읽지 못함"}


class ListViewProvider:
    """목록 페이지 + 상세 페이지 형태의 기관. refresh: 목록 1회 + 캐시에 없는 새 상세 최대 n건. 없으면 __call__ 로 최신 n건 메모리 매칭."""
    LIST_URL = None

    def __init__(self, fetcher, n=LIST_ITEMS):
        self.f, self.n, self.items = fetcher, n, None

    def parse_list(self, raw):
        raise NotImplementedError

    def parse_view(self, raw, url, title):
        raise NotImplementedError

    def _rows(self):
        try:
            body, _ = self.f.get(self.LIST_URL)
            return self.parse_list(body)
        except Exception:  # noqa: BLE001  robots 불허·상한·오류 모두 '이 기관은 오늘 건너뜀'
            return []

    def _fetch_one(self, url, title):
        try:
            raw, final = self.f.get(url)
        except Exception:  # noqa: BLE001
            return False
        return self.parse_view(raw, url, title)  # 항목 | None

    def refresh(self, cache, today):
        fresh = []
        for url, title in self._rows():
            if cache.has(url):
                cache.stats["known_skipped"] += 1
            else:
                fresh.append((url, title))
        for url, title in fresh[:self.n]:
            e = self._fetch_one(url, title)
            if e is False:
                continue
            if e is None:
                cache.add_negative(url, "본문 구간을 읽지 못함")
            else:
                cache.add(e)

    def _load(self):
        self.items = []
        for url, title in self._rows()[:self.n]:
            e = self._fetch_one(url, title)
            if e:
                self.items.append({**e, "_norm": _norm(html_to_text(e["content"]))})

    def __call__(self, kw):
        if self.items is None:
            self._load()
        return [{**{k: v for k, v in i.items() if k != "_norm"}, "relevance": relevance(kw, i["title"], i["content"])}
                for i in self.items if _norm(kw) in i["_norm"]]


class FscProvider(ListViewProvider):
    """금융위원회 보도자료(https://www.fsc.go.kr/no010101). robots.txt 는 User-agent:* Allow:/ . 키 불필요,
    상세에 등록일(<div class="day">)과 본문 전문."""
    LIST_URL = FSC_LIST
    parse_list = staticmethod(parse_fsc_list)

    def parse_view(self, raw, url, title):
        return parse_fsc_view(raw, url, title)


class MotirProvider(ListViewProvider):
    """산업통상부 보도·참고자료(https://www.motir.go.kr/kor/article/ATCL3f49a5a8c). robots.txt 는 /kor/search·/search·/attach/viewer 만
    Disallow(옛 도메인 motie.go.kr 은 motir.go.kr 로 301). 상세에 등록일(<em>등록일</em>)과 본문 전문."""
    LIST_URL = MOTIR_LIST
    parse_list = staticmethod(parse_motir_list)

    def parse_view(self, raw, url, title):
        return parse_motir_view(raw, url, title)


class NtsProvider(ListViewProvider):
    """국세청 보도자료(목록 selectNttList.do?mi=2201&bbsId=1028 → 상세 selectNttInfo.do GET). robots.txt Allow:/ . 기관=국세청."""
    LIST_URL = NTS_LIST
    parse_list = staticmethod(parse_nts_list)

    def parse_view(self, raw, url, title):
        return parse_nts_view(raw, url, title)


class BokProvider(ListViewProvider):
    """한국은행 보도자료(뉴스/자료 목록 조각 listCont.do → 상세 view.do). robots.txt 는 Disallow:/ 에 /portal/ 만 Allow(RFC 9309 해석).
    본문이 '붙임 문서 참조'뿐인 항목은 '본문 구간을 읽지 못함'으로 캐시에 기록(다시 요청하지 않음). 기관=한국은행."""
    LIST_URL = BOK_LIST
    parse_list = staticmethod(parse_bok_list)

    def parse_view(self, raw, url, title):
        return parse_bok_view(raw, url, title)


class NpsProvider(ListViewProvider):
    """국민연금공단 보도자료(목록 getOHAE0002M0List.do → 상세 getOHAE0002M1.do?pstId=). robots 는 /search/ 등 일부만 Disallow. 기관=국민연금공단."""
    LIST_URL = NPS_LIST
    parse_list = staticmethod(parse_nps_list)

    def parse_view(self, raw, url, title):
        return parse_nps_view(raw, url, title)



def default_discover(fetcher=None, cache=None, today=None, cache_dir=None):
    """기본 출처 탐색. 첫 호출 때 각 provider 가 '아직 안 받은 새 URL 만' 받아 캐시에 쌓고(요청 상한은 그대로),
    키워드 매칭은 캐시 전체 중 게시 30일 이내 기사에서 한다. discover.summary() 로 캐시 상태를 본다."""
    f = fetcher or PoliteFetcher()
    cache = cache or SourceCache(cache_dir)
    day = today or dt.date.today()
    providers = [KoreaKrProvider(f), MohwRssProvider(f), MoelProvider(f), FscProvider(f), MotirProvider(f),
                 NtsProvider(f), BokProvider(f), NpsProvider(f)]
    state = {"refreshed": False}
    host_errors = {}

    def discover(kw):
        if not state["refreshed"]:
            state["refreshed"] = True
            for p in providers:  # 한 호스트의 예외는 그 호스트만 건너뛰고 기록, 나머지는 계속
                try:
                    p.refresh(cache, day)
                except Exception as e:  # noqa: BLE001
                    host_errors[type(p).__name__] = f"{type(e).__name__}: {e}"[:200]
        if len(host_errors) == len(providers):
            raise AllHostsFailed("모든 수집처 실패: " + "; ".join(f"{k}={v}" for k, v in host_errors.items()))
        return cache.match(kw, day)

    def pairs(today_=None):
        """캐시 안 최근 발표 기관 문서 → 두 기관 같은 사안 묶음(find_pairs)."""
        t = today_ or day
        docs = []
        for e in cache.within(t):
            raw = cache.read(e)
            if raw is not None:
                docs.append({"url": e["url"], "org": e.get("org"), "org_known": bool(e.get("org_known")),
                             "published": e.get("published"), "title": e.get("title", ""), "content": raw})
        return find_pairs(docs, t)

    def summary():
        out = cache.summary(day)
        out["host_errors"] = dict(host_errors)
        out["requests"] = dict(getattr(f, "count", {}))
        out["requests_total"] = getattr(f, "total", None)
        return out
    discover.summary = summary
    discover.pairs = pairs
    discover.cache = cache
    discover.host_errors = host_errors
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
        rep = min(g, key=lambda x: (not counts_as_agency(x), x["published_date"]))
        for c in g:
            c["dup_of"] = None if c is rep else rep["url"]
        reps.append(rep)
    return reps


def run(acc, today=None, fetchers=None, ledger_dir=None, sources_dir=None, notify=None, min_sources=MIN_SOURCES,
        gate=True, stop_file=None, cache_dir=None, run_id=None, topic=None, rehearsal=False):
    """gate=True(기본): STOP 파일·paused 면 아무것도 하지 않고 {'status':'gated'} 를 돌려준다(원장 기록 없음). T-09 도 단계마다 재확인."""
    if topic is not None and not rehearsal:
        raise ValueError("--topic 은 --rehearsal 과 같이만 쓸 수 있다")
    if gate:
        ok_gate, why_gate = C.run_gate(acc, stop_file) if stop_file else C.run_gate(acc)
        if not ok_gate:
            return {"status": "gated", "reason": why_gate, "account_id": acc.get("account_id"), "kw": None, "n_sources": 0}
    today = today or dt.date.today()
    day = today.isoformat()
    run_id = run_id or f"research-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(3)}"
    domains = C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
    discover = (fetchers or {}).get("discover") or default_discover(today=today, cache_dir=cache_dir)
    out_dir = os.path.join(sources_dir or SOURCES_DIR, day)
    base = {"date": day, "account_id": acc["account_id"], "run_id": run_id}

    def final(status, reason, kw, saved=(), tried=(), evidence=None):
        rec = ledger.append("research_ledger", {
            **base, "type": "run", "kw": kw, "status": status, "reason": reason, "n_sources": len(saved),
            "orgs": sorted({s["org"] for s in saved if s.get("org_known")}), "source_urls": [s["url"] for s in saved],
            "tried": list(tried), "evidence": evidence,
            "cache": discover.summary() if callable(getattr(discover, "summary", None)) else None}, ledger_dir)
        if status == "hold" and notify:
            notify("warn", f"[{acc['account_id']}] 공식 출처 부족 — 카드뉴스 보류", reason)
        return rec

    if topic is not None:   # 리허설 전용 지정(run.py 가 --rehearsal 과 같이만 허용): 트렌드 순위 대신 두 기관 묶음 중 일치하는 것
        cands_kw, why = [], "topic 지정"
    else:
        cands_kw, why = candidate_keywords(acc["account_id"], today, ledger_dir)
    pair_kw, pair_notes = pair_candidates(acc, today, discover, domains, topic=topic, evidence_fn=(fetchers or {}).get("evidence"))
    for note in pair_notes:   # 범위 밖·금칙으로 걸러진 묶음도 흔적을 남긴다
        ledger.append("research_ledger", {**base, "type": "try", "src": "pair", "kw": note["kw"], "adopted": False,
                                          "reason": note["reason"]}, ledger_dir)
    if topic is not None and not pair_kw:
        avail = ", ".join(n["kw"] for n in pair_notes) or "(없음)"
        return final("hold", f"--topic {topic!r} 와 일치하는 두 기관 묶음이 없음(범위·금칙 통과 0건; 걸러진 묶음: {avail})", None)
    if not cands_kw and not pair_kw:
        return final("hold", why, None)
    from . import trends
    seen_kw = {trends._norm(c["kw"]) for c in cands_kw}   # 트렌드 후보와 같은 키워드(_norm 기준)인 묶음은 중복 시도 안 함
    cands_kw = cands_kw + [c for c in pair_kw if not (trends._norm(c["kw"]) in seen_kw or seen_kw.add(trends._norm(c["kw"])))]   # 트렌드 후보 먼저, 모두 안 되면 두 기관 묶음

    tried, logged = [], set()
    for rank, ck in enumerate(cands_kw, 1):
        kw = ck["kw"]
        meta = {"rank": rank, "src": ck["src"], "evidence": "indicator" if ck["evidence"] else "none"}
        try:
            cands = discover(kw) or []
        except AllHostsFailed as e:
            _log_host_errors(discover, base, ledger_dir, logged)
            return final("error", str(e)[:300], None, (), tried)
        except Exception as e:  # noqa: BLE001
            ledger.append("research_ledger", {**base, "type": "try", **meta, "kw": kw, "adopted": False,
                                              "reason": f"출처 검색 실패: {e!r}"[:200]}, ledger_dir)
            tried.append(kw)
            continue
        _log_host_errors(discover, base, ledger_dir, logged)
        keep, drop = screen(cands, today, domains)
        reps = group_releases(keep)
        orgs = {counts_as_agency(c, domains) for c in reps} - {None}   # G1(verify)와 같은 판정 함수
        n_unknown = sum(1 for c in keep if not counts_as_agency(c, domains))
        n_dup = sum(1 for c in keep if c.get("dup_of"))
        ok = len(orgs) >= min_sources
        # 더 엄격한 채택 기준(T-PAIR1): kw 가 제목 또는 본문 첫 단락에 실제로 나오는 기관이 min_sources 곳 이상이어야 한다.
        # (본문에서 스친 무관한 문서로 기관 수를 채워 놓고 정작 그 주제를 다루는 기관은 1곳뿐인 채택을 막는다)
        kw_orgs = {counts_as_agency(c, domains) for c in reps if kw_in_title_or_head(kw, c)} - {None}
        topical_fail = ok and len(kw_orgs) < min_sources
        unk = (f", 기관 미상 {n_unknown}건 제외" if n_unknown else "") + (f", 같은 보도자료 재게시 {n_dup}건 합산" if n_dup else "")
        reason = (f"확인된 서로 다른 기관 {len(orgs)}곳 채움{unk}" if ok
                  else f"확인된 서로 다른 기관 {len(orgs)}곳 (최소 {min_sources}곳 필요){unk}")
        if topical_fail:
            ok = False
            reason = (f"kw 가 제목·본문 첫 단락에 나오는 기관 {len(kw_orgs)}곳({', '.join(sorted(kw_orgs)) or '없음'}) — "
                      f"최소 {min_sources}곳 필요(기관 {len(orgs)}곳 중 나머지는 본문 스침) — 채택 안 함{unk}")
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
                "saved_path": path, "kw": kw, "org_known": org_is_known(c), "dup_of": c.get("dup_of"),
                "run_id": run_id}, ledger_dir))
        note = "" if ck["evidence"] else "; evidence=none(지표 근거 없음, 공식 출처만 있음)"
        if ck["src"] == "pair":
            note += f"; 두 기관 같은 사안 묶음({', '.join(ck.get('orgs', []))})"
        return final("ok", f"{reason}; 채택 키워드 {kw!r}(시도 {rank}번째, {ck['src']}), 저장 {len(saved)}건{note}",
                     kw, saved, tried, evidence=meta["evidence"])
    return final("hold", f"시도 {len(cands_kw)}개 키워드 모두 공식 출처(확인된 기관) {min_sources}곳을 못 채움: {', '.join(tried)}",
                 None, (), tried)


def _log_host_errors(discover, base, ledger_dir, logged):
    """수집처별 예외를 research_ledger 에 한 번씩(type=host_error) 남긴다."""
    for host, why in (getattr(discover, "host_errors", None) or {}).items():
        if host not in logged:
            logged.add(host)
            ledger.append("research_ledger", {**base, "type": "host_error", "host": host, "reason": why}, ledger_dir)


def sources_for_run(rrec, ledger_dir=None):
    """research.run 이 돌려준 기록(rrec)의 이번 실행(run_id) source_ledger 행만, (url, sha256) 중복 제거.
    같은 키워드를 여러 번 실행해 같은 줄이 쌓여도 이번 실행 몫만 돌려준다. run_id 가 없는 옛 줄은 포함하지 않는다."""
    rid = rrec.get("run_id")
    seen, out = set(), []
    for r in ledger.read("source_ledger", ledger_dir):
        key = (r.get("url"), r.get("sha256"))
        if rid and r.get("run_id") == rid and key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ---------- 두 기관 같은 사안 묶음 (T-PAIR1) ----------
PAIR_WINDOW_DAYS = 7      # 최근 발표분만
PAIR_GAP_DAYS = 3         # 묶음 안 발표일 차이
PAIR_MAX_TRIES = 5
PAIR_STEM_MIN = 3         # 제목 핵심어가 1개만 겹칠 때 그 길이 하한(2개 이상 겹치면 길이 무관)
TITLE_DF_MIN = 8          # 제목 핵심어 문서 빈도 상한 = max(8, 3%) — 넘으면 '정부·지원' 같은 흔한 말
TITLE_DF_RATIO = 0.03
TITLE_STOP = {"정부", "발표", "개최", "추진", "지원", "확대", "실시", "시행", "개정", "안내", "공고", "모집", "선정", "운영", "강화",
              "마련", "최초", "국내", "신규", "정책", "사업", "관련", "대응", "개선", "점검", "협의", "협력", "간담회", "브리핑",
              "보도자료", "설명", "공개", "현황", "결과", "전망", "올해", "내년", "오늘", "이번", "전국", "지역", "국민", "기관",
              "인정", "지정", "출범", "체결", "협약", "참석", "방문", "논의", "발간", "공동", "합동", "전환", "도입", "성장", "역량", "집중", "모두", "함께", "먼저", "찾아", "가동", "총력", "위한", "통한", "이후", "선제"}
_TITLE_TAIL = {"은", "는", "이", "가", "을", "를", "의", "에", "도", "로", "와", "과", "에서", "으로", "까지", "부터", "에는", "에도", "만", "이나"}


def kw_in_title_or_head(kw, c):
    """kw 가 이 문서의 제목 또는 본문 첫 단락(RELEVANCE_HEAD 자)에 있는가."""
    n = _norm(kw)
    if not n:
        return False
    if n in _norm(c.get("title") or ""):
        return True
    return n in _norm(body_text(c.get("content") or b"")[:RELEVANCE_HEAD])


def title_terms(title, org_names=frozenset()):
    """제목 핵심어(소문자). 숫자가 든 토큰·1글자·기관명·흔한 공문어(TITLE_STOP) 제외."""
    out = set()
    for t in re.findall(r"[0-9A-Za-z가-힣]+", (title or "").lower()):
        if len(t) < 2 or re.search(r"\d", t) or t in org_names or any(t.startswith(w) and t[len(w):] in ({""} | _TITLE_TAIL) for w in TITLE_STOP):
            continue
        out.add(t)
    return out


def _stem_match(a, b):
    """두 제목 토큰이 같은 말인가 — 같거나, 짧은 쪽이 긴 쪽의 앞부분이고 나머지가 조사. 맞으면 짧은 쪽(어간), 아니면 None."""
    if a == b:
        return a
    s, l = (a, b) if len(a) <= len(b) else (b, a)
    return s if len(s) >= 2 and l.startswith(s) and l[len(s):] in _TITLE_TAIL else None


def find_pairs(docs, today, domains=None, common=None, window=PAIR_WINDOW_DAYS, gap=PAIR_GAP_DAYS):
    """같은 사안을 서로 다른 기관이 각각 발표한 묶음. 순수 함수(네트워크·원장 없음).
    docs: [{url, org, org_known?, published, title, content}]. 기관 판정은 verify.counts_as_agency(G1 과 같은 함수).
    묶음 조건: 최근 window 일 발표 · 기관 2곳 이상 · 발표일 차이 gap 일 이내 · 제목 핵심어 공통(제목 빈도가 흔하면 제외) ·
    다른 기관끼리 같은 보도자료(same_release)면 짝으로 안 침(group_releases 가 1건으로 합치므로) ·
    묶음 안 각 기관 문서에 구별 숫자(단위 있는 숫자만, 날짜성·흔한 토큰·짧은 숫자 제외)가 1개 이상(없는 기관은 빼고, 2곳 미만이면 제외).
    common: verify.common_tokens 꼴 튜플(흔한 토큰 집합, 읽은 저장본 수, …). None 이면 실제 캐시로 계산. 저장본 0건이면 빈도를 못 믿어 빈 목록(fail-closed).
    반환 [{kw, kws, orgs, docs:[{url, org, published, title, distinct}], latest}] 기관 수·최신일 순."""
    from . import verify
    domains = domains or C.load_json(os.path.join(C.CONFIG, "official_domains.json"))
    cset, n_docs = (common if common is not None else verify.common_tokens())[:2]
    if n_docs <= 0:
        return []
    rows = []
    for c in docs:
        d = parse_date(c.get("published"))
        org = counts_as_agency(c, domains)
        if org and d and 0 <= (today - d).days <= window and c.get("title"):
            rows.append({**c, "_org": org, "_date": d})
    org_names = {re.sub(r"[^0-9a-z가-힣]", "", c["_org"].lower()) for c in rows}
    # 제목 핵심어 문서 빈도(전달받은 문서 전체 기준) — 흔한 말 제외
    all_titles = [c for c in docs if c.get("title")]
    df = {}
    for c in all_titles:
        for t in title_terms(c["title"], org_names):
            df[t] = df.get(t, 0) + 1
    df_limit = max(TITLE_DF_MIN, int(-(-len(all_titles) * TITLE_DF_RATIO // 1)))
    terms = [{t for t in title_terms(c["title"], org_names) if df.get(t, 0) <= df_limit} for c in rows]
    buckets = {}   # 어간 → 문서 번호 집합
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a["_org"] == b["_org"] or abs((a["_date"] - b["_date"]).days) > gap:
                continue
            stems = {s for ta in terms[i] for tb in terms[j] for s in [_stem_match(ta, tb)] if s}
            if len(stems) < 2 and not any(len(s) >= PAIR_STEM_MIN for s in stems):   # 짧은 낱말 하나만 겹치면('연구'·'대응') 같은 사안이 아님
                continue
            if same_release(a, b):
                continue
            for s in stems:
                buckets.setdefault(s, set()).update((i, j))
    sets = {}      # frozenset(문서 번호) → 어간들
    for s, idx in buckets.items():
        order = sorted(idx, key=lambda k: rows[k]["_date"])
        wins = []
        for k in order:
            w = frozenset(m for m in order if 0 <= (rows[m]["_date"] - rows[k]["_date"]).days <= gap)
            if len({rows[m]["_org"] for m in w}) >= 2:
                wins.append(w)
        for w in wins:
            if not any(w < o for o in wins):   # 더 큰 창에 들어가는 부분 집합은 버림
                sets.setdefault(w, set()).add(s)
    cache = {}

    def distinct(i):
        if i not in cache:
            toks = verify.source_tokens(rows[i]["content"])
            # G1 기여 판정과 같은 함수(단위 있는 숫자만 — 단위 없는 긴 숫자는 페이지 번호·기사 ID 일 수 있다)
            cache[i] = sorted(t for t in toks if verify.is_distinctive_number(t, cset))
        return cache[i]
    out, seen = [], {}
    for w, stems in sets.items():
        per_org = {}
        for m in sorted(w):
            if distinct(m):
                per_org.setdefault(rows[m]["_org"], []).append(m)
        if len(per_org) < 2:
            continue
        keep = sorted(m for ms in per_org.values() for m in ms)
        key = frozenset(rows[m]["url"] for m in keep)
        if key in seen:
            seen[key]["_stems"] |= stems
            continue
        b = {"_stems": set(stems), "orgs": sorted(per_org),
             "docs": [{"url": rows[m]["url"], "org": rows[m]["_org"], "published": rows[m]["_date"].isoformat(),
                       "title": rows[m]["title"], "distinct": distinct(m)[:5]} for m in keep],
             "latest": max(rows[m]["_date"] for m in keep).isoformat()}
        seen[key] = b
        out.append(b)
    for b in out:
        stems = sorted(b.pop("_stems"), key=lambda s: (-len(s), s))
        b["kw"], b["kws"] = stems[0], stems
    out.sort(key=lambda b: (-len(b["orgs"]), [-int(x) for x in b["latest"].split("-")], b["kw"]))
    return out


def pair_candidates(acc, today, discover, domains=None, topic=None, evidence_fn=None, max_tries=PAIR_MAX_TRIES):
    """discover.pairs(today)(두 기관 묶음)를 계정 범위·금칙에 거른 시도 후보 [{kw, src:'pair', evidence, orgs, ...}], 걸러진 묶음 [{kw, reason}].
    discover 에 pairs 가 없으면(시험용 주입 등) 후보 없음. topic 이 있으면 그 kw 와 일치(같거나 한쪽이 다른 쪽을 포함)하는 묶음만."""
    from . import trends
    fn = getattr(discover, "pairs", None)
    if not callable(fn):
        return [], []
    try:
        bundles = fn(today) or []
    except Exception:  # noqa: BLE001 — 묶음 탐색 실패가 트렌드 경로를 막지 않게
        return [], []
    banned = C.load_json(os.path.join(C.CONFIG, "common_banned.json"))["categories"]
    all_banned = {**banned}
    if acc.get("banned_topics_extra"):
        all_banned["account_extra"] = acc["banned_topics_extra"]
    seeds = acc.get("seed_keywords", [])
    out, notes = [], []
    nt = trends._norm(topic) if topic is not None else None
    for b in bundles:
        if nt is not None and not any(trends._norm(k) and (nt in trends._norm(k) or trends._norm(k) in nt) for k in b["kws"]):
            continue
        titles = [d["title"] for d in b["docs"]]
        cat = next((c for c in (trends.is_banned(x, all_banned) for x in [*b["kws"], *titles]) if c), None)
        if cat:
            notes.append({"kw": b["kw"], "reason": f"두 기관 묶음 — 금칙 분류 {cat}(키워드·제목) — 시도 안 함"})
            continue
        ok, why = trends.in_scope(b["kw"], titles, seeds)
        if not ok:
            notes.append({"kw": b["kw"], "reason": f"두 기관 묶음 — 계정 범위 밖({why}) — 시도 안 함"})
            continue
        if len(out) >= max_tries:
            continue
        ev = evidence_fn(b["kw"]) if evidence_fn else trends.indicator_evidence(b["kw"], today, whole_word=True)[0]
        out.append({"kw": b["kw"], "src": "pair", "evidence": bool(ev), "orgs": b["orgs"], "kws": b["kws"]})
    return out, notes


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
