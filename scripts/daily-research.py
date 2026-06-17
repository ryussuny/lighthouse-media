"""매일 아침 6시: 글로벌 TOP 채널 조사 + 트렌드 분석"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os, requests
from datetime import datetime

API_KEY = ""
with open(os.path.join(os.path.expanduser("~"), "lighthouse-media", ".env")) as f:
    for line in f:
        if line.startswith("ANTHROPIC_API_KEY="):
            API_KEY = line.strip().split("=",1)[1]

TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT = os.path.join(os.path.expanduser("~"), "lighthouse-media", "output", TODAY)
os.makedirs(OUTPUT, exist_ok=True)

def claude(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 3000, "messages": [{"role": "user", "content": prompt}]})
    return r.json()["content"][0]["text"]

print(f"[{TODAY}] 일일 채널 조사 시작...")

# 1. 글로벌 트렌드 + TOP 채널 분석
research = claude(f"""오늘 날짜: {TODAY}

[TASK 1] 자기계발/힐링 분야 오늘의 글로벌 트렌드 키워드 10개
- 유튜브, 인스타, 틱톡에서 급상승 중인 주제
- 각 키워드의 우리 채널 적용 가능성 (1-10점)

[TASK 2] 이번 주 해외 TOP 채널 히트 콘텐츠 5개
- 채널명, 조회수, 제목, 성공 요인 분석

[TASK 3] 한국 자기계발 채널 이번 주 히트작 5개
- 채널명, 조회수, 제목, 우리가 배울 점

[TASK 4] 오늘 Lighthouse Media가 만들어야 할 콘텐츠 3개
- 유튜브 롱폼 1개 (제목 + 핵심 구조)
- 인스타 카드뉴스 1개 (제목 + 10장 텍스트)
- 숏폼 1개 (30초 스크립트)

TOP 채널의 성공 공식을 그대로 적용해서 제안해줘.
""")

with open(os.path.join(OUTPUT, "daily-research.md"), 'w', encoding='utf-8') as f:
    f.write(f"# 일일 채널 조사 — {TODAY}\n\n{research}")

print("  조사 완료! → output/" + TODAY + "/daily-research.md")
