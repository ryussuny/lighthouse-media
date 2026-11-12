# T01 정책·한도 조사 — 인스타 다계정 카드뉴스 자동 게시 + 네이버 데이터랩

- 조사일(접속일): 2026-11-12 (모든 URL 동일)
- 방법: 공식 페이지 원문을 직접 받아 문장 대조(Meta 고객센터는 JS 렌더라 HTML 내 원문 문자열을 추출해 확인). 계정 조작·로그인 없음.
- 신뢰도 표시: **공식 확인** / **제3자만** / **확인 못함**

---

## 한눈에 보는 핵심 숫자

| 항목 | 값 | 신뢰도 |
|---|---|---|
| 인스타 앱에서 동시에 로그인해 둘 수 있는 계정 | 최대 10개 | 공식 확인 |
| 계정 센터(Accounts Center)에 넣을 수 있는 페이스북 계정 | 1개 | 공식 확인 |
| 계정 센터 전체 계정 수 상한(인스타 포함) | — | 확인 못함 (제3자 검색 요약에 "25개"가 나왔으나 공식 원문에서 찾지 못함) |
| API 게시 한도(계정당 24시간) | 문서끼리 **100개 vs 50개로 서로 다름** → 설계는 50개로 | 공식 확인(불일치 자체가 사실) |
| 캐러셀 1건 = 게시물 몇 개? | 1개 | 공식 확인 |
| 캐러셀 장수 | 최대 20장 | 공식 확인 |
| 이미지 형식 | JPEG만 | 공식 확인 |
| AI 라벨 API 파라미터 | `is_ai_generated=true` (캐러셀은 부모 컨테이너에만) | 공식 확인 |
| 네이버 데이터랩 검색어트렌드 1일 호출 | 1,000회 | 공식 확인 |
| 요청당 주제어 그룹 | 최대 5개 | 공식 확인 |
| 그룹당 검색어 | 최대 20개 | 공식 확인 |
| 조회 시작 가능일 | 2016-01-01부터 | 공식 확인 |

---

## A. 인스타그램

### A1. 한 사람이 운영할 수 있는 계정 수

**답:** 인스타 앱에서 여러 계정을 추가해 로그아웃 없이 전환 가능하며, 동시에 로그인해 둘 수 있는 계정은 **최대 10개**. 계정 센터에는 **페이스북 계정은 1개만** 넣을 수 있다. "한 사람당 인스타 계정을 몇 개까지 만들 수 있다"는 공식 상한 문구는 찾지 못했다.

- 인용: "When you add multiple Instagram accounts, you can switch between them without having to log out and log back in."
- 인용: "Keep in mind that you can have up to 10 accounts logged in at one time."
  - URL: https://help.instagram.com/1696686240613595 (iphone-app / android / mobile-touch 버전 모두 같은 문장 확인)
  - 신뢰도: **공식 확인**
  - 참고: 검색엔진 요약·오래된 기사(제3자, 예: business.instagram.com 블로그·2016년 기사)에는 "최대 5개"로 나오나, 현재 고객센터 원문은 10개. 옛 정보로 판단.
- 인용: "You can only add one Facebook account to your Accounts Center."
  - URL: https://www.meta.com/help/accounts-center/589288436078759/ (페이지 수정일 2026-09-25)
  - 신뢰도: **공식 확인**
- 계정 센터 전체 상한(예: 25개): **확인 못함** — 검색 요약이 https://www.meta.com/help/quest/553151146004188/ 를 근거로 들었지만 원문을 받아 보니 해당 숫자 문장이 없었음.
- 같은 고객센터 글에 "같은 계정에 추가 프로필 만들기(Add another Instagram profile)" 기능도 있음(공식 확인, 같은 URL).

### A2. Graph API 게시 한도

**답:** 공식 문서 안에서 숫자가 엇갈린다.
- 콘텐츠 게시 가이드 "Rate limit" 절: **24시간 이동 구간에 100개**, 캐러셀은 1개로 계산.
  - 인용: "Instagram accounts are limited to 100 API-published posts within a 24-hour moving period. Carousels count as a single post."
- 같은 문서 캐러셀 절: **50개**.
  - 인용: "Accounts are limited to 50 published posts within a 24-hour period. Publishing a carousel counts as a single post."
  - URL: https://developers.facebook.com/docs/instagram-platform/content-publishing/ (마크다운 원문: https://developers.facebook.com/documentation/instagram-platform/content-publishing.md)
- `content_publishing_limit` 엔드포인트 문서: `quota_total` "currently 50", `quota_duration` "currently 86400 seconds, or 24 hours".
  - URL: https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit
  - 읽기 전용, `since`는 24시간 이내여야 함.
- 신뢰도: **공식 확인** (숫자 불일치 자체가 확인된 사실)
- 설계 권고: 하드코딩하지 말고 게시 전 `GET /<IG_ID>/content_publishing_limit?fields=quota_usage,config`로 실제 값을 읽어 판단. 기본 보수값 50. 단, 아래 A6처럼 스팸 판정은 API 한도와 별개이므로 실제 운영은 계정당 하루 1~3건 수준이 안전(이 운영 수치는 공식 수치가 아니라 권고).
- 기타 공식 제약(같은 게시 가이드): 캐러셀 최대 20장, 이미지는 JPEG만, 미디어는 게시 시점에 공개 URL로 접근 가능해야 함, 캐러셀 이미지는 첫 장 비율로 잘림(기본 1:1), 쇼핑 태그·필터 미지원.

### A3. API 게시 요건

**답:**
- 계정 유형: **프로페셔널 계정(비즈니스 또는 크리에이터)** 필수. 개인 계정은 불가.
  - 인용: "To use the APIs, your app users must have an Instagram professional account. An Instagram professional account can represent a business or creator."
- 페이스북 페이지: 로그인 방식에 따라 다름.
  - Instagram API with **Instagram Login** — 페이지 **불필요** ("serves Instagram professional accounts without requiring a linked Facebook Page.")
  - Instagram API with **Unified Login**(신규 통합 권장) — 페이지 불필요, 비즈니스 포트폴리오 필요.
  - Instagram API with **Facebook Login** — 페이지 **필요**, 그 페이지에 관리자급 작업 권한 필요. 페이지가 PPA(페이지 게시 인증)를 요구하면 완료 전 게시 불가.
- 권한: Instagram Login은 `instagram_business_basic` + `instagram_business_content_publish`, Facebook Login은 `instagram_basic` + `instagram_content_publish` + `pages_read_engagement`.
- 앱 1개로 여러 계정: 가능. "You can build an app that serves only an account you own or manage, or an app that serves app users' Instagram professional accounts." 본인 소유·관리 계정만 쓰면 **Standard Access로 충분**, 앱 심사(App Review)·비즈니스 인증은 남의 계정을 서비스할 때(Advanced Access)만 필요.
  - 인용: "If your app only serves your Instagram professional account or an account you manage, Standard Access is all your app needs."
  - 본인 계정만 쓰면 로그인 흐름 구현 없이 장기 토큰으로 호출 가능("you do not need to implement a login flow").
- 페이지 1개로 여러 인스타 계정을 묶을 수 있는지: **확인 못함**(공식 문서에서 1:N 여부 문장 못 찾음). Instagram Login 방식은 페이지가 필요 없으므로 설계상 이 문제를 피할 수 있음.
- URL: https://developers.facebook.com/docs/instagram-platform/overview (원문 .md: https://developers.facebook.com/documentation/instagram-platform/overview.md)
- 신뢰도: **공식 확인**

### A4. 자동화·다계정·스팸 관련 공식 문구

**허용(공식 경로):** 공식 Content Publishing API로 본인 프로페셔널 계정에 게시하는 것은 문서화된 정식 기능.
- 인용: "Your app can use the API to publish single images, videos, reels ... or posts containing multiple images and videos (carousel posts)" — https://developers.facebook.com/docs/instagram-platform/overview — **공식 확인**
- 계정 무결성 정책도 스크립트 금지에 "공식 경로" 예외를 둠: "Creating or using an account or other entity through automated means, such as scripting (unless the scripting activity occurs through authorized routes and does not otherwise violate our policies)" — https://transparency.meta.com/policies/community-standards/account-integrity/ — **공식 확인**

**금지:**
1. 인스타그램 이용약관(Terms of Use, 시행일 2025-01-01) — https://help.instagram.com/581066165581870 — **공식 확인**
   - "You can't attempt to create accounts or access or collect information in unauthorized ways."
   - "This includes creating accounts or accessing or collecting information in an automated way without our express permission, regardless of whether such automated access or collection is undertaken while logged-in to an Instagram account."
   - "You can't impersonate others or provide inaccurate information."
   - "you can't create an account for someone else unless you have their express permission."
   - "You can't do anything unlawful, misleading, or fraudulent or for an illegal or unauthorized purpose."
   - "You can't do, or attempt to do, anything to circumvent, by-pass, or override any technological measures that control or limit access to the Service or data."
   - "You can't sell, license, or purchase any account or data obtained from us or our Service"
   - 해석: **계정 생성은 사람이 직접**, 비공식 봇(브라우저 자동조작·비공식 API)로 로그인·게시·수집하면 위반. 공식 API 게시는 "express permission"에 해당하는 허가된 경로.
2. Meta 커뮤니티 규정(인스타에도 적용: "The Community Standards outline what is and isn't allowed on Facebook, Instagram, Messenger and Threads." — https://transparency.meta.com/policies/community-standards/) — **공식 확인**
   - 스팸 정책 https://transparency.meta.com/policies/community-standards/spam/ :
     - "We do not allow content that is designed to deceive, mislead, or overwhelm users in order to artificially increase viewership."
     - 금지: "Posting, sharing, engaging with content or creating accounts, Groups, Pages, Events or other assets, either manually or automatically, at very high frequencies."
     - "We may place restrictions on accounts that are acting at lower frequencies when other indicators of Spam (e.g., posting repetitive content) or signals of inauthenticity are present."
   - 가짜 계정: "we don't allow people to misrepresent themselves on our services, use fake accounts" — https://transparency.meta.com/policies/community-standards/inauthentic-behavior/ (2025-12-11 개정본 기준, WebFetch 요약으로 확인) — **공식 확인**
3. Meta 플랫폼 약관(최종 수정 2026-02-03) — https://developers.facebook.com/terms/ — **공식 확인**
   - 집행 회피 목적 앱 금지(§7.e): 집행 조치를 "우회하거나 우회하려고 시도하기 위해 앱을 생성하거나 유지한 경우".
   - 플랫폼 약관 자체에는 스팸·가짜 참여 조항은 없었고(커뮤니티 규정 쪽에 있음), 이용약관이 "Meta Platform Terms and Developer Policies" 준수를 요구.
4. 가짜 참여(좋아요·팔로워 구매·자동 좋아요 앱): 인스타 공식 발표(2018-11-19) "Recently, we've seen accounts use third-party apps to artificially grow their audience." / "Starting today, we will begin removing inauthentic likes, follows and comments" / "accounts that continue to use third-party apps to grow their audience may see their Instagram experience impacted." — https://about.instagram.com/blog/announcements/reducing-inauthentic-activity-on-instagram/ — **공식 확인**(단 2018년 글)
   - 인스타 커뮤니티 가이드라인 문구 "not artificially collecting likes, followers, or shares, posting repetitive comments or content..."는 현재 고객센터 원문(https://help.instagram.com/477434105621119)이 JS로만 렌더돼 본문 대조 **확인 못함**(법원 보관 사본 등 제3자 경로로만 확인 → **제3자만**).

**다계정 자체:** 인스타는 공식적으로 여러 계정 추가·전환 기능을 제공(A1). "한 사람이 주제별 인스타 계정을 여러 개 운영하는 것 금지"라는 공식 문구는 찾지 못함. 다만 "Use multiple Facebook accounts" 금지 문구는 **페이스북 계정** 대상(2024-07 판 인증 신원 정책, WebFetch 요약)이며 인스타에는 해당 기능이 공식 제공됨.

### A5. AI 생성물 라벨("AI 정보")

**답:**
- 의무 대상: **사실적인 영상, 사실적인 음성**. **이미지는 라벨 의무 없음**(Meta 예시: "Meta does not require you to label images").
  - 인용: "Meta requires you to label content you share that has photorealistic video or realistic-sounding audio that has been digitally generated or altered, including with AI."
  - 인용: "There may be penalties if you do not label content as required."
  - 인용: "Content may be labeled automatically when it contains AI signals" / 라벨 안 해도 "label may be applied if Meta detects that your content was AI-generated or AI-edited."
  - URL: https://help.instagram.com/761121959519495 — **공식 확인**
- API로 자진 표시: 2026-06-22 변경로그 — `POST /{ig_user_id}/media`에 `is_ai_generated=true`, "For carousels, set `is_ai_generated` on the carousel container only." Instagram Login·Facebook Login 둘 다 지원, `GET /{ig_media_id}?fields=is_ai_generated`로 확인 가능.
  - URL: https://developers.facebook.com/documentation/instagram-platform/changelog (2026-06-22 "AI Info Label") — **공식 확인**
- 권고: 카드뉴스 이미지는 의무는 아니나, AI 생성 이미지 사용 시 `is_ai_generated=true`를 켜 두는 것이 투명성·자동 감지 대비에 유리(권고, 공식 의무 아님).

### A6. 계정 제한·정지 계기

- 스팸 정책: 매우 높은 빈도 게시·계정 생성(수동·자동 불문), 낮은 빈도라도 **반복 콘텐츠** 신호가 있으면 제한 가능(A4 인용) — **공식 확인**
- 계정 무결성 정책 https://transparency.meta.com/policies/community-standards/account-integrity/ — **공식 확인**
  - "We may restrict or disable accounts ... that are: Owned by the same person or entity as an account that has been disabled"
  - "Created or repurposed to evade a previous account or entity removal, including those assessed to have common ownership and content as previously removed accounts"
  - "Close linkage with a network of accounts or other entities that violate or evade our policies"
  - → **한 계정이 정지되면 같은 소유자의 다른 계정들도 연쇄 제한될 수 있음**(다계정 운영의 최대 리스크).
- 추천 제외(정지는 아니나 노출 감소): 인스타 추천 가이드라인 — "Unoriginal content that is largely repurposed from another source with only minor, immaterial edits" 는 추천 대상에서 빠질 수 있음. — https://help.instagram.com/313829416281232 — **공식 확인**
  - → 주제만 바꾼 같은 틀·같은 문장의 카드 대량 복제는 반복 콘텐츠·비독창 콘텐츠로 묶일 위험.
- 참고(사내 이력): 2026-09 RetryIG가 같은 카드를 매일 재게시해 노출이 억제된 사례(CLAUDE.md)와 위 정책이 부합.

---

## B. 네이버 데이터랩 통합 검색어 트렌드 API

URL: https://developers.naver.com/docs/serviceapi/datalab/search/search.md — 전 항목 **공식 확인**

| 항목 | 값 | 원문 |
|---|---|---|
| 1일 호출 한도 | 1,000회 | "통합 검색어 트렌드 API의 하루 호출 한도는 1,000회입니다." |
| 요청당 주제어 그룹(keywordGroups) | 최대 5개 | "주제어와 주제어에 해당하는 검색어 묶음 쌍의 배열. 최대 5개의 쌍을 배열로 설정할 수 있습니다." |
| 그룹당 검색어(keywords) | 최대 20개 | "주제어에 해당하는 검색어. 최대 20개의 검색어를 배열로 설정할 수 있습니다." |
| 시작일(startDate) | 2016-01-01부터 | "2016년 1월 1일부터 조회할 수 있습니다." |
| 구간 단위(timeUnit) | date(일간)/week(주간)/month(월간) | 원문 표 |
| 선택 필터 | device(pc/mo), gender(m/f), ages(1~11: 0–12세 … 60세 이상) | 원문 표 |
| 반환값 ratio 의미 | 상대값(가장 큰 값=100) | "구간별 검색량의 상대적 비율. 구간별 결과에서 가장 큰 값을 100으로 설정한 상댓값입니다." |
| 인증 | 비로그인 방식(헤더에 Client ID/Secret), POST /v1/datalab/search | 원문 |

- 해석상 주의: ratio는 **절대 검색량이 아님**. 한 요청 결과 안에서 최댓값=100으로 맞춘 상대값이므로, 서로 다른 요청끼리 숫자를 직접 비교하면 안 됨(비교하려면 같은 요청에 기준 키워드를 함께 넣어야 함 — 이는 ratio 정의에서 나오는 추론).
- 종료일(endDate) 최대 범위·한 요청 최대 기간: 문서에 별도 상한 문구 없음 → **확인 못함**.
- NAVER API HUB / ncloud 쪽 별도 문서: 이번 조사에서 확인하지 않음(**확인 못함**).

---

## 리스크 요약

1. **연쇄 정지**: 같은 소유자 계정 하나가 정지되면 나머지도 제한 가능(계정 무결성 정책). 계정별 품질·독창성 관리가 필수.
2. **반복·비독창 콘텐츠**: 같은 템플릿·문장 재사용은 스팸 신호/추천 제외 대상. 계정별 내용 차별화 필요.
3. **게시 한도 수치 불일치(100 vs 50)**: 엔드포인트로 실측 후 판단, 기본 50 가정.
4. **계정 생성 자동화 금지**: 계정은 사람이 직접 만들고, 게시만 공식 API로.
5. **비공식 자동화 금지**: 브라우저 자동조작·비공식 앱으로 로그인·좋아요·팔로우는 약관 위반.
6. **AI 라벨**: 이미지는 의무 아님, 사실적 영상·음성은 의무. API `is_ai_generated` 사용 가능.
