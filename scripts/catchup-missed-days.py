"""놓친 날짜 자동 감지 + 보충
- bible-schedule.json의 날짜 중 Documents/오늘의말씀/에 txt가 없는 날짜 찾기
- 오늘 이전 날짜만 대상
- 자동으로 묵상 생성 + txt 저장
- 실행: python scripts/catchup-missed-days.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, re, requests
from datetime import datetime

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
SCHEDULE_PATH = os.path.join(REPO, "config", "bible-schedule.json")
WORD_DIR = os.path.join(HOME, "Documents", "오늘의말씀")
ENV_PATH = os.path.join(REPO, ".env")

TODAY = datetime.now().strftime("%Y-%m-%d")
WEEKDAYS = ['월','화','수','목','금','토','일']

def load_api_key():
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding='utf-8'):
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.strip().split("=", 1)[1]
    return os.environ.get("ANTHROPIC_API_KEY", "")

def find_missed_days():
    """스케줄에 있지만 txt가 없는 과거 날짜 찾기"""
    with open(SCHEDULE_PATH, 'r', encoding='utf-8') as f:
        schedule = json.load(f)

    missed = []
    for entry in schedule:
        date_str = entry['date']
        if date_str >= TODAY:
            continue  # 미래 날짜는 건너뜀
        txt_path = os.path.join(WORD_DIR, f"{date_str}.txt")
        if not os.path.exists(txt_path):
            missed.append(entry)

    return missed

def generate_devotional(entry, api_key):
    """Claude API로 묵상 생성"""
    date_str = entry['date']
    ref = entry['ref']
    title = entry['title']
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_kr = WEEKDAYS[dt.weekday()]

    prompt = f"""오늘({date_str} {day_kr}요일) 인스타그램 말씀 카드용 묵상을 작성해줘.

본문: {ref}
제목: {title}

아래 구조를 정확히 따라 작성해줘:

📖 {ref}
"설교 제목을 한 줄 인용구 형태로"

(본문의 핵심 상황을 2-3문단으로 간결하게 풀어쓰기.
- 첫 문단: 성경 속 인물의 행동/상황 요약
- 둘째 문단: 그 행동의 결과 또는 교훈
- 셋째 문단: 오늘 우리 삶에 적용할 핵심 메시지
각 문단은 2-3문장. 따뜻하고 깊이 있되 간결하게.)

✦ 오늘의 묵상
"묵상 제목"

(4-5문단의 깊이 있는 묵상. 성경 본문을 구체적으로 인용하면서 오늘 삶에 적용하는 통찰. 각 문단은 완결된 문장으로 끝나야 함.)

✦ 오늘의 질문
(자기 성찰적 질문 1개)

✦ 오늘의 실천
(구체적인 하루 실천 2문장)

🙏 오늘의 기도
(본문 메시지와 연결된 짧고 진심 어린 기도. 2-3줄. 아멘으로 끝.)

동산감리교회
@garden___church

#오늘의말씀 #{ref.replace(' ','').replace(':','')} #성경말씀 #묵상 #기도 #교회
#말씀카드 #동산감리교회 #매일묵상 #성경 #은혜
#거룩 #순종 #예배 #기독교 #새벽기도 #하나님
#BibleVerse #DailyDevotional #ChurchLife

[중요]
- 전체 분량: 인스타그램 캡션에 적합한 길이
- 묵상 본문은 성경 원문 나열 아닌, 핵심 메시지 중심 풀어쓰기
- 따뜻하고 깊이 있되 과장하지 않는 문체
- 이모지는 📖, ✦, 🙏만 사용
- 새번역 성경 기준"""

    r = requests.post("https://api.anthropic.com/v1/messages", headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }, json={
        "model": "claude-sonnet-4-6",
        "max_tokens": 3000,
        "messages": [{"role": "user", "content": prompt}]
    }, timeout=60)

    return r.json()["content"][0]["text"]

def main():
    print("=" * 50)
    print("  놓친 말씀 자동 보충")
    print("=" * 50)

    missed = find_missed_days()
    if not missed:
        print("  ✓ 놓친 날짜 없음 — 모든 말씀이 있습니다!")
        return

    print(f"  놓친 날짜: {len(missed)}개")
    for m in missed:
        print(f"    {m['date']} — {m['ref']} {m['title']}")

    api_key = load_api_key()
    if not api_key:
        print("\n  ✗ API 키 없음 — .env 파일 확인 필요")
        return

    os.makedirs(WORD_DIR, exist_ok=True)

    for i, entry in enumerate(missed):
        print(f"\n  [{i+1}/{len(missed)}] {entry['date']} {entry['ref']}...")
        try:
            content = generate_devotional(entry, api_key)
            txt_path = os.path.join(WORD_DIR, f"{entry['date']}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    ✓ 저장됨: {txt_path}")
        except Exception as e:
            print(f"    ✗ 실패: {e}")

    print(f"\n{'=' * 50}")
    print(f"  완료! {len(missed)}개 보충됨")
    print(f"{'=' * 50}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[FATAL ERROR] {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
