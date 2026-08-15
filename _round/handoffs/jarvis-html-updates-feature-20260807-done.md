# jarvis-html-updates-feature-20260807 — done handoff

## 무엇을 했나
jarvis.html에 "🔄 자비스 업데이트" 기능 신설 — GET /api/jarvis-updates(신규)로 idoforgod/cys-terminal의
open 이슈+PR을 번호순 조회, risk_flag 키워드 배지 표시, 적용요청 버튼으로 기존 POST /api/directives에
큐잉. 증거: `round/evidence/jarvis-html-updates-feature-20260807/verification-log.md` +
`modal-list-badges.jpg`. git commit `0f8a5d8`(로컬만, push 안 함).

## 왜 했나
master 위임(오너 컨펌 완료) — cys-terminal(호스트 CLI) 저장소의 이슈/PR을 JARVIS 대시보드에서 바로
확인하고, 적용이 필요하면 기존 업무지시 큐(company.html 조직도와 공유)에 등록해 추적할 수 있게 함.
로컬 pack 패치 적용·git push는 이 기능의 책임이 아니다(그건 master가 지시함 확인 후 별도 처리).

## 지금 상태
server.js/jarvis.html 수정 완료, curl로 API 동작(병합·중복제거·정렬·risk_flag·502 negative-case) +
Claude-in-Chrome 헤드리스 렌더로 버튼·모달·배지 확인 + curl로 적용요청 종단 플로우까지 검증 완료.
master 보고 대기 중(아직 접수 확인 안 받음).

## 남은 위험·주의
- DEPARTMENTS 화이트리스트에 "CI/CD/PR"을 추가한 판단포인트가 master 정정 대상일 수 있음(진행하며
  병행보고했으나 이 handoff 작성 시점까지 회신 미확인 — verification-log.md 참고).
- risk_flag는 키워드 휴리스틱일 뿐이라 오탐/미탐 가능 — UI에 과신금지 문구는 있지만 사람이 실제로
  안 읽고 그냥 적용요청을 누를 위험은 구조적으로 남음.
- server.js가 DATA_DIR을 환경변수로 분리하지 않아 로컬 테스트마다 실데이터 오염 위험이 반복됨(이번에도
  발생·즉시 수습) — 근본 해결은 이번 티켓 범위 밖, 후속 과제로 제안.
- GitHub API 무인증 폴백은 시간당 60회 rate limit — 반복 클릭이 잦아지면 걸릴 수 있음(캐싱 없음, 이번
  티켓에서 요구 안 해 구현 안 함).

## 다음에 할 일
1. master 접수 확인·CI/CD/PR department 판단 최종 컨펌 대기.
2. (오너 승인 시) Render에 GITHUB_TOKEN 환경변수 설정 검토 — rate limit 여유 확보.
3. server.js DATA_DIR 테스트 격리 구조 개선(후속 제안, 미착수).
