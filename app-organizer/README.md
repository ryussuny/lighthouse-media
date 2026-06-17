# 📱 앱 정리 도우미 (App Organizer)

설치된 스마트폰 앱 이름을 입력하면 **Claude(AI)가 종류별 폴더로 자동 분류**해 주는 웹 앱입니다.
실제 핸드폰 홈 화면을 원격으로 바꿀 수는 없으므로, 이 앱은 **어떤 폴더에 무엇을 넣을지 정리안**을 보여줍니다.
결과를 보고 직접 같은 이름의 폴더를 만들어 옮기시면 됩니다.

## 실행 방법

1. 의존성 설치 (저장소 루트에서 한 번만):
   ```bash
   npm install
   ```
2. `.env`에 Anthropic API 키 설정 (`.env.example` 참고):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. 서버 실행:
   ```bash
   npm run organizer
   ```
4. 브라우저에서 접속: http://localhost:3300

## 사용법

1. 앱 이름을 한 줄에 하나씩(또는 쉼표로 구분) 붙여넣습니다. — `예시 채우기` 버튼으로 샘플을 넣어볼 수 있습니다.
2. **✨ 폴더로 정리하기** 클릭 → AI가 5~9개 폴더로 분류합니다.
3. 결과를 **📋 텍스트로 복사**해서 메모장 등에 저장해 두고, 핸드폰에서 그대로 폴더를 만들면 됩니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | (필수) | Claude API 키 |
| `APP_ORGANIZER_PORT` | `3300` | 서버 포트 |
| `ORGANIZER_MODEL` | `claude-sonnet-4-6` | 분류에 사용할 모델 |

## 구성

- `server.js` — Express 서버 + `/api/organize` (AI 분류 API)
- `public/index.html` — 프론트엔드 (입력 폼 + 결과 카드)

## API

`POST /api/organize`
```json
{ "apps": "카카오톡\n토스\n유튜브" }
```
응답:
```json
{
  "folders": [
    { "name": "소통", "emoji": "💬", "apps": ["카카오톡"] },
    { "name": "금융", "emoji": "💰", "apps": ["토스"] },
    { "name": "미디어", "emoji": "🎬", "apps": ["유튜브"] }
  ],
  "total": 3
}
```
서버는 AI 응답을 검증하여 입력에 없던 앱은 제거하고, 누락된 앱은 자동으로 `기타` 폴더에 모읍니다.
