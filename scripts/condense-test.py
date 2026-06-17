"""묵상을 카드용 핵심 문장으로 압축 테스트"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

def claude(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 500, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

# 오늘 묵상 읽기
import re
content = open(os.path.join(HOME, "Documents", "오늘의말씀", "2026-04-28.txt"), 'r', encoding='utf-8').read()
med = re.search(r'\*\s*오늘의 묵상.*?\n"?(.+?)"?\s*\n\n(.+?)(?=\*\s*묵상을 위한 질문)', content, re.DOTALL)
title = med.group(1).strip() if med else ""
meditation = med.group(2).strip() if med else ""

result = claude(
    "다음 묵상을 인스타 카드용으로 압축해줘.\n\n"
    "[제목] " + title + "\n\n"
    "[원본 묵상]\n" + meditation + "\n\n"
    "[규칙]\n"
    "- 카드 3장으로 나누기\n"
    "- 각 카드에 핵심 문장 2~3줄만\n"
    "- 한 줄 최대 10자\n"
    "- JSON으로 출력: {\"cards\": [\"줄1\\n줄2\\n줄3\", \"줄1\\n줄2\", \"줄1\\n줄2\\n줄3\"]}\n"
    "- 감동적이고 임팩트 있게\n"
    "- 원본의 핵심 메시지를 빠짐없이 담되 간결하게\n"
    "- 마지막 카드는 예수님과의 연결"
)

print(result)

# JSON 추출
start = result.find("{")
end = result.rfind("}") + 1
if start >= 0:
    data = json.loads(result[start:end])
    print("\n=== 카드별 내용 ===")
    for i, card in enumerate(data.get("cards", [])):
        print(f"\n카드 {i+1}:")
        for ln in card.split("\n"):
            print(f"  [{len(ln)}자] {ln}")
