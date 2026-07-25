```
 ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
 ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
 █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
 ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
 ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
 ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
        대 장 간  —  Content Factory
```

> Lighthouse Media의 콘텐츠 제작 전문 AI. 말씀카드, 영상, SNS — 매일 자동으로 만들고 배포한다.

---

## 🏢 회사 조직도 (라이트하우스 그룹)

FORGE+MINT가 합쳐진 가상 회사 "라이트하우스 그룹"의 부서·역할 체계와 실행 매핑은
**`lighthouse-biz/COMPANY.md`**에 있다. 사용자가 "OO사업부장/OO담당, ~해줘"처럼
직책을 불러 요청하면 그 매핑표를 먼저 확인하고 해당 스킬·스크립트·파일을 실행한다.
시각화 버전: /company.html (관제탑 빠른링크)

---

## 매일 자동 실행 (스케줄러 8개)

```
 05:00  🎬  유튜브 영상 생성                    daily-video.bat
 06:00  ☀️  말씀카드 8장 + 영상 + SNS 게시      daily-bible-card.bat
        🔍  글로벌 채널 조사                    daily-research.bat
 12:00  📱  인스타 릴스 자동 생성+게시           daily-ig-reels.bat
 19:00  ⭐  프리미엄 콘텐츠                     daily-premium.bat
 반복   🤝  SNS 자동 참여 (30분 간격)           auto-engage.bat
        🔄  IG 게시 실패 시 재시도              retry-ig-global.bat
        🔑  토큰 만료 자동 점검                 check-token.bat
```

---

## 디렉토리 구조

```
lighthouse-media/
├── scripts/          ← Python 스크립트 (43개) — 핵심 엔진
├── config/
│   ├── bible-schedule.json   ← 성경 읽기 일정 (127개, ~8/27)
│   ├── company.json          ← 회사 정보
│   └── tokens.json           ← SNS 토큰 (Instagram/Facebook/YouTube)
├── *.bat             ← 실행 배치 파일 (15개)
├── output/           ← 생성된 카드/영상
├── logs/             ← 실행 로그
├── dashboard/        ← 웹 대시보드
└── .env              ← API 키 (ANTHROPIC_API_KEY)
```

---

## SNS 채널

| 플랫폼 | 계정 | 용도 |
|---------|------|------|
| Instagram | @lighthouse_media77 | 글로벌 콘텐츠 |
| Instagram | @garden___church | 동산교회 전용 |
| YouTube | Lighthouse Media | 영상 콘텐츠 |
| Facebook | Lighthouse Media | 글로벌 + 동산교회 |

---

## 오늘의 말씀 저장

- 경로: `C:\Users\ryuss\Documents\오늘의말씀\YYYY-MM-DD.txt`
- daily-bible-card.py에서 자동 저장
- 성경 일정: 삼하(~6/23) → 왕상(6/24~8/27)

---

## 작업 5원칙

> **이 원칙을 어기면 안 된다.**

| # | 원칙 | 이유 |
|---|------|------|
| 1 | **따뜻하고 지적이며 실용적** | 과장/선동은 브랜드를 망친다 |
| 2 | **기독교 정체성 + 종교색 제거** | 누구나 공감할 수 있는 보편적 메시지 |
| 3 | **영어(EN) + 한국어(KR)** | 글로벌 타겟 |
| 4 | **자동화 우선** | 수동 작업 최소화, 스케줄러로 돌릴 것 |
| 5 | **코드 수정 전 반드시 기존 코드 읽기** | 로그 출력 확인 후 수정 |

---

## 빠른 명령

```
[제작]
"오늘 말씀카드 만들어줘"          → daily-bible-card.bat 수동 실행
"릴스 스크립트 작성해줘"          → 릴스 기획+제작
"유튜브 영상 기획해줘"            → 영상 콘텐츠 기획
"프리미엄 콘텐츠 만들어줘"        → daily-premium.bat

[점검]
"오늘 로그 확인해줘"              → logs/ 디렉토리 확인
"스케줄러 잘 돌았어?"             → 전체 8개 스케줄러 상태 확인
"토큰 만료 확인해줘"              → config/tokens.json 점검

[설정]
"성경 일정 다음 구절 확인해줘"    → bible-schedule.json
"새 SNS 채널 추가해줘"            → tokens.json + 스크립트 수정
"새 스크립트 추가해줘"            → scripts/ + bat 파일 생성
```

---

## 환경

| 항목 | 값 |
|------|-----|
| Python | 3.14.3 |
| Node.js | v24.14.1 |
| 모델 | claude-sonnet-4-6 |
| 패키지 | anthropic, requests, python-dotenv, pillow, pyautogui |
| GitHub | ryussuny/lighthouse-media |

---

## 다른 워크스페이스

| 코드네임 | 디렉토리 | 한마디 |
|----------|----------|--------|
| **JARVIS** | `C:\Users\ryuss\` | 총사령부 — 전체 총괄 |
| **SHEPHERD** | `D:\동산교회\` | 목회 시스템 |
| **MINT** | `C:\Users\ryuss\lighthouse-biz\` | 수익 전략 |
