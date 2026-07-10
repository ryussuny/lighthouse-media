# 🔍 키워드 검색량 조회 도구 (Keyword Tool)

키워드를 입력하면 **월간 검색량(PC/모바일), 12개월 검색 추이, 연관 키워드와 광고 경쟁도**를
보여주는 웹 앱입니다. loword.co.kr 같은 키워드 인텔리전스 도구의 핵심 기능 v1입니다.

## 데이터 소스 (자동 선택)

| 데이터 | 실데이터 소스 | 폴백 |
|--------|--------------|------|
| 검색량·연관키워드·경쟁도 | 네이버 검색광고 API | 데모 데이터 |
| 12개월 검색 추이 | 네이버 데이터랩 API | 데모 데이터 |

API 키가 없거나 호출이 실패해도 **항상 결과가 나옵니다**(결정적 데모 데이터 — 같은 키워드는
항상 같은 숫자). 화면의 배지로 `네이버 실데이터` / `데모 데이터` 여부를 표시합니다.

## 실행

```bash
npm install          # 저장소 루트에서 한 번만
npm run keyword      # → http://localhost:3400
```

## 실데이터 연동 (무료 발급)

1. **네이버 검색광고 API** — https://manage.searchad.naver.com → 도구 > API 사용 관리
   ```
   NAVER_AD_ACCESS_KEY=...
   NAVER_AD_SECRET_KEY=...
   NAVER_AD_CUSTOMER_ID=...
   ```
2. **네이버 데이터랩 API** — https://developers.naver.com → 애플리케이션 등록 (검색어 트렌드)
   ```
   NAVER_CLIENT_ID=...
   NAVER_CLIENT_SECRET=...
   ```
`.env`에 위 값을 넣고 서버를 재시작하면 됩니다. 두 소스는 독립적이라 하나만 넣어도 그 부분만 실데이터가 됩니다.

## 구성

- `server.js` — Express 서버 + `GET /api/keyword?q=키워드`
- `naver.js` — 검색광고 API(HMAC 서명)·데이터랩 API 클라이언트 + 데모 생성기
- `public/index.html` — 검색 UI + 스탯 타일 + SVG 추이 차트(크로스헤어 툴팁) + 연관 키워드 테이블

## API

`GET /api/keyword?q=캠핑의자`
```json
{
  "keyword": "캠핑의자",
  "engines": { "stats": "naver|demo", "trend": "datalab|demo" },
  "self": { "keyword": "캠핑의자", "pc": 12000, "mobile": 48000, "total": 60000, "compIdx": "높음", "adDepth": 15 },
  "related": [ { "keyword": "캠핑의자 추천", "pc": 3000, "mobile": 9000, "total": 12000, "compIdx": "중간" } ],
  "trend": [ { "month": "2025-08", "ratio": 72 } ]
}
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `KEYWORD_TOOL_PORT` | `3400` | 서버 포트 |
| `NAVER_AD_*` 3종 | (선택) | 검색광고 API — 검색량 실데이터 |
| `NAVER_CLIENT_*` 2종 | (선택) | 데이터랩 API — 추이 실데이터 |

## 다음 단계 후보 (v2)

- 대량 키워드 조회 (여러 키워드 한 번에)
- CSV 다운로드
- 블로그 지수/문서 수 확인
- 회원/구독 (유료 플랜)
