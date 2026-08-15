# jarvis-updates-pin-timeout-fix-20260807 — done handoff

## 무엇을 했나
GET /api/jarvis-updates에 PIN 인증(requireDashboardPin) + 두 GitHub fetch 호출에 10초 타임아웃
(AbortSignal.timeout) 추가. jarvis.html의 openJarvisUpdates()도 PIN 헤더를 첨부하도록 수정. 증거:
`round/evidence/jarvis-updates-pin-timeout-fix-20260807/verification-log.md` +
`pin-authed-modal-success.jpg`. git commit `4e2c282`(로컬만, push 안 함).

## 왜 했나
reviewer-claude-2가 이전 티켓(jarvis-html-updates-feature-20260807, commit 0f8a5d8)의 REVISE 검토에서
실결함 2건 발견: ①GET /api/jarvis-updates가 무인증이라 누구나 반복 호출해 GitHub API rate limit을
소진시킬 수 있음(자기서비스거부) ②fetch에 timeout이 없어 GitHub 무응답 시 요청이 무기한 붙잡힘.
master가 코드로 직접 재확인 후 위임.

## 지금 상태
두 결함 모두 수리 완료, curl+타임아웃 강제발생 negative-case+Claude-in-Chrome 헤드리스로 검증 완료.
master 보고 대기 중.

## 남은 위험·주의
- 타임아웃 값(10초)은 하드코딩 상수(`JARVIS_UPDATES_FETCH_TIMEOUT_MS`) — env로 빼진 않음(이번 티켓
  요구사항 아님). 필요시 두 fetch 호출이 같은 상수를 참조하므로 한 곳만 바꾸면 됨.
- PIN이 서버/클라 불일치 상태로 배포되면(예: Render 환경변수 DASHBOARD_PIN을 클라 하드코딩값 1216과
  다르게 설정) 버튼이 조용히 "인증 필요" 실패만 보여줌 — 이번 검증에서 실제로 재현했고 UI가 안전하게
  처리하는 것도 확인했지만, 오너가 오해하지 않도록 안내 필요.
- 페이지네이션(per_page 100 초과)은 여전히 미대응 — 이번에도 범위 밖.

## 다음에 할 일
1. master 접수 확인 대기.
2. (오너 승인 시) Render에 DASHBOARD_PIN 실제 배포값 설정 — 클라 하드코딩 1216과 다르게 설정할 경우
   jarvis.html의 클라 PIN 상수도 함께 갱신해야 함(그렇지 않으면 버튼이 항상 401).
