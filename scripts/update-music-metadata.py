"""EP01 유튜브 영상 제목/설명 일괄 최적화 (검색형 제목 + 풍부한 설명)"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, os, re, glob

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

HOME = os.path.expanduser("~")
MUSIC = os.path.join(HOME, "lighthouse-biz", "music", "pilot-ep01")
BOARD = os.path.join(HOME, "lighthouse-media", "config", "jarvis-board.json")
TOKEN = os.path.join(HOME, "OneDrive", "바탕 화면", "lighthouse_media", "token_lighthouse.json")
PLAYLIST = "https://youtube.com/playlist?list=PLTt-NE3XVRRs"

# 트랙별 검색형 제목 + 무드 소개
META = {
    1: ("Be Still — 잠들기 전 듣는 잔잔한 워십 | Calm Worship for Sleep & Prayer",
        "소음이 멈추지 않는 하루 끝, 마음을 내려놓는 시간.", "Let the noise fade. Rest in stillness."),
    2: ("Anchor for My Soul — 흔들리는 마음을 붙드는 찬양 | Worship for Anxious Hearts",
        "불안한 파도 속에서도 흔들리지 않는 닻이 있습니다.", "An anchor that holds through every storm."),
    3: ("Rest in You — 지친 하루를 위로하는 워십 | Peaceful Worship for Rest",
        "애쓰지 않아도 괜찮은 시간, 그분 안에서 쉼.", "Not by striving — resting in You."),
    4: ("Quiet Waters — 묵상 기도 배경음악 | Quiet Worship for Meditation & Prayer",
        "잔잔한 물가로 인도하시는 음성을 따라.", "Beside quiet waters, He restores my soul."),
    5: ("Morning Light — 아침에 듣는 은혜의 찬양 | Morning Worship Music",
        "새 아침, 새 긍휼. 하루를 여는 빛의 노래.", "New mercies with every sunrise."),
    6: ("Carry Me Home — 위로가 필요한 밤의 워십 | Comforting Worship for Hard Days",
        "지쳐 쓰러진 밤, 집으로 업고 가시는 손길.", "When I can't walk, He carries me home."),
    7: ("잠잠하라 — 시편 46편 묵상 찬양 | Be Still (Korean Worship)",
        "\"너희는 가만히 있어 내가 하나님 됨을 알지어다\" (시 46:10)", "Korean worship on Psalm 46:10."),
    8: ("잔잔한 물가 — 시편 23편 잔잔한 CCM | Still Waters (Korean Worship)",
        "쉴 만한 물가로 인도하시는 목자의 노래. (시 23편)", "A Korean worship song on Psalm 23."),
    9: ("다시 일어나 — 힘이 필요할 때 듣는 찬양 | Worship for New Strength",
        "넘어진 자리에서 다시 일어나게 하는 힘.", "Rise again — strength for a new beginning."),
    10: ("평온 — 잠들기 전 듣는 고요한 CCM | Peaceful Korean Worship for Sleep",
         "하루의 끝, 마음이 가라앉는 고요한 평안.", "Deep peace for the end of your day."),
    0: ("Quiet Before You — 새벽기도 묵상 음악 | Quiet Worship for Early Prayer",
        "말보다 먼저, 고요함으로 그분 앞에.", "Before words — quiet before You."),
}

def lyrics_snippet(no):
    for p in glob.glob(os.path.join(MUSIC, "lyrics", f"{no:02d}-*.md")):
        txt = open(p, encoding="utf-8").read()
        body = re.sub(r"^---.*?---", "", txt, flags=re.S)
        body = re.sub(r"^#.*$", "", body, flags=re.M).strip()
        return body[:500]
    return ""

def build_desc(no, title_kr, mood_kr, mood_en):
    lyr = lyrics_snippet(no) if no else ""
    return (f"{title_kr} · EP01 「Rest / 안식」 — Lighthouse Worship\n\n"
            f"{mood_kr}\n{mood_en}\n\n"
            f"🎧 EP01 전곡 연속듣기: {PLAYLIST}\n"
            f"🔔 구독하시면 새로운 묵상 워십을 가장 먼저 들으실 수 있습니다.\n\n"
            + (f"[가사]\n{lyr}\n\n" if lyr else "")
            + "* 본 음원은 AI 작곡 도구의 도움을 받아 제작되었습니다.\n\n"
            "#worship #ccm #찬양 #묵상음악 #수면음악 #기도음악 #새벽기도 #LighthouseWorship")

def main():
    creds = Credentials.from_authorized_user_info(json.load(open(TOKEN)))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN, "w") as f: f.write(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)

    board = json.load(open(BOARD, encoding="utf-8"))
    for t in board["music"]["tracks"]:
        vid, no = t.get("youtube"), t["no"]
        if not vid or no not in META: continue
        title, mood_kr, mood_en = META[no]
        body = {"id": vid, "snippet": {
            "title": title[:100],
            "description": build_desc(no, t["title"], mood_kr, mood_en)[:4900],
            "tags": ["worship","ccm","찬양","묵상음악","수면음악","기도음악","새벽기도","christian music","calm worship","sleep worship","lighthouse worship"],
            "categoryId": "10", "defaultLanguage": "ko"}}
        yt.videos().update(part="snippet", body=body).execute()
        print(f"✅ {no}. {title[:60]}")
    print("\n전체 제목/설명 최적화 완료")

if __name__ == "__main__":
    main()
