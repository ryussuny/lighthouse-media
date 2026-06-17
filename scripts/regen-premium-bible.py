"""새벽강해 개요 참고 — 고퀄리티 말씀 묵상 재작성 + 프리미엄 카드"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time
from datetime import datetime

HOME = os.path.expanduser("~")
API_KEY = ""
for line in open(os.path.join(HOME, "lighthouse-media", ".env")):
    if line.startswith("ANTHROPIC_API_KEY="): API_KEY = line.strip().split("=",1)[1]

schedule = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "bible-schedule.json"), encoding='utf-8'))
overview = open(os.path.join(HOME, "Downloads", "사무엘하_새벽강해_전체개요.txt"), 'r', encoding='utf-8').read()

WEEKDAYS = ['월','화','수','목','금','토','일']

def claude(prompt):
    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json",
    }, json={"model": "claude-sonnet-4-6", "max_tokens": 4000, "messages": [{"role":"user","content":prompt}]})
    return r.json()["content"][0]["text"]

# 해당 설교의 개요 찾기
def find_overview(ref, title):
    lines = overview.split("\n")
    found = []
    capturing = False
    for line in lines:
        if title in line or ref in line:
            capturing = True
        if capturing:
            found.append(line)
            if len(found) > 15:
                break
        if capturing and line.strip() == "" and len(found) > 3:
            break
    return "\n".join(found) if found else ""

targets = [s for s in schedule if s['date'] <= '2026-04-30']

prev = "사무엘상 31장에서 사울이 길보아 산에서 전사하고, 야베스 길르앗 용사들이 그의 시체를 거두어 장사하였습니다. 사무엘상의 마지막은 끝이 아니라 다윗이라는 새 시작을 향한 전환점이었습니다."

print("=" * 50)
print("  Premium Bible Devotions")
print("  (with sermon overview reference)")
print("=" * 50)

for item in targets:
    ds = item['date']
    ref = item['ref']
    title = item['title']
    dt = datetime.strptime(ds, "%Y-%m-%d")
    dk = dt.strftime("%m/%d")
    dw = WEEKDAYS[dt.weekday()]

    # 개요에서 복음 포인트 찾기
    ov = find_overview(ref, title)

    wp = os.path.join(HOME, "Documents", "오늘의말씀", ds + ".txt")
    dp = os.path.join(HOME, "OneDrive", "바탕 화면", "오늘의말씀", ds + ".txt")

    print(f"\n[{ds} ({dw})] {ref} — {title}")

    prompt = (
        "너는 동산감리교회 전도사의 인스타그램 말씀 카드 작가다.\n\n"
        "[이전 묵상 흐름]\n" + prev + "\n\n"
        "[오늘 본문]\n" + ref + " (새번역)\n\n"
        "[설교 제목]\n" + title + "\n\n"
    )

    if ov:
        prompt += "[설교 개요 — 이 내용을 묵상에 반영할 것]\n" + ov + "\n\n"

    prompt += (
        "[작성 형식 — 아래 구조를 정확히 따라줘]\n\n"
        "📖 " + ref + "\n"
        '"설교 제목을 한 줄 인용구 형태로"\n\n'
        "(본문의 핵심 상황을 2-3문단으로 간결하게 풀어쓰기.\n"
        "- 첫 문단: 성경 속 인물의 행동/상황 요약\n"
        "- 둘째 문단: 그 행동의 결과 또는 교훈\n"
        "- 셋째 문단: 오늘 우리 삶에 적용할 핵심 메시지\n"
        "각 문단은 2-3문장. 따뜻하고 깊이 있되 간결하게.\n"
        "설교 개요의 복음 포인트를 자연스럽게 녹여서.\n"
        "이전 묵상과 자연스럽게 연결.)\n\n"
        "✦ 오늘의 질문\n"
        '"자기 성찰적 질문 1개 (설교 제목 \'' + title + '\'과 연결)"\n\n'
        "✦ 오늘의 실천\n"
        "(구체적인 하루 실천 2문장. 행동 + 마음가짐)\n\n"
        "🙏 오늘의 기도\n"
        '"하나님/거룩하신 주님으로 시작,\n'
        "본문 메시지와 연결된 짧고 진심 어린 기도. 2-3줄. 아멘으로 끝.\"\n\n"
        "동산감리교회\n"
        "@garden___church\n\n"
        "#오늘의말씀 #사무엘하 #성경말씀 #묵상 #기도 #교회\n"
        "#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜\n"
        "#거룩 #순종 #예배 #기독교 #새벽기도 #하나님\n"
        "#BibleVerse #DailyDevotional #ChurchLife\n\n"
        "[중요]\n"
        "- 설교 제목 '" + title + "'의 메시지를 묵상의 핵심으로\n"
        "- 설교 개요의 복음 포인트를 반드시 반영\n"
        "- 전체 분량: 인스타그램 캡션에 적합한 길이 (너무 길지 않게)\n"
        "- 성경 원문 나열이 아닌 핵심 메시지 중심 풀어쓰기\n"
        "- 이모지는 📖, ✦, 🙏만 사용\n"
        "- 따뜻하고 깊이 있게, 과장하지 않고\n"
        "- 새번역 성경 기준"
    )

    word = claude(prompt)

    with open(wp, 'w', encoding='utf-8') as f:
        f.write(word)
    os.makedirs(os.path.dirname(dp), exist_ok=True)
    with open(dp, 'w', encoding='utf-8') as f:
        f.write(word)
    print("  OK — saved")

    # 다음 연결고리 (새 인스타 형식: 📖 이후 본문 부분 추출)
    if "📖" in word:
        s = word.find("📖")
        e = word.find("✦") if "✦" in word else s + 400
        prev = word[s:e][:300]
    elif "*오늘의 묵상" in word:
        s = word.find("*오늘의 묵상")
        e = word.find("*묵상을 위한 질문") if "*묵상을 위한 질문" in word else s + 300
        prev = word[s:e][:300]

    time.sleep(3)

print("\n" + "=" * 50)
print(f"  {len(targets)}일치 프리미엄 묵상 완료!")
print("=" * 50)
