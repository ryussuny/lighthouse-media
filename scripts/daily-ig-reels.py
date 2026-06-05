"""매일 인스타 릴스 1편 자동 생성 + 업로드
- 동기부여/위로/힐링/자기계발 주제 랜덤 선택
- 배경음악 포함 시네마틱 영상 (1080x1920, 30~40초)
- Instagram Reels + Facebook 자동 게시
- Usage:
    python daily-ig-reels.py              # 자동 주제 선택
    python daily-ig-reels.py comfort      # 특정 카테고리
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, base64, subprocess, shutil, random, hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════════════════════════
HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
CONFIG_DIR = os.path.join(REPO_DIR, "config")
BGM_DIR = os.path.join(REPO_DIR, "assets", "bgm")
OUT_DIR = os.path.join(REPO_DIR, "output", "reels")
os.makedirs(OUT_DIR, exist_ok=True)

tokens = json.load(open(os.path.join(CONFIG_DIR, "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"
IMGUR_ID = "546c25a59c58ad7"

FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

W, H = 1080, 1920
FPS = 2

# ═══════════════════════════════════════════════════════════════
# 폰트
# ═══════════════════════════════════════════════════════════════
def gf(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()

def gf_en(size):
    for p in ["C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def tc(d, y, text, font, fill, sp=0):
    for ln in text.split("\n"):
        bb = d.textbbox((0, 0), ln, font=font)
        d.text(((W - (bb[2] - bb[0])) / 2, y), ln, font=font, fill=fill)
        y += bb[3] - bb[1] + sp
    return y

# ═══════════════════════════════════════════════════════════════
# 릴스 콘텐츠 풀 (매일 다른 콘텐츠 선택)
# ═══════════════════════════════════════════════════════════════
REEL_POOL = {
    "comfort": [
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "\"You are allowed to be\nboth a masterpiece\nand a work in progress.\"",
                 "title": "당신은 이미\n충분히 아름답고\n동시에 성장 중입니다", "source": "- Sophia Bush"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "오늘 힘들었다면\n그건 약한 게 아니라\n살아있다는 증거입니다",
                 "body": "당신의 하루를\n응원합니다"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Be gentle with yourself.\nYou're doing the best you can.\"",
                 "title": "자신에게\n조금 더\n부드러워지세요", "source": ""},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "내일은 오늘보다\n조금 더 괜찮은\n하루가 될 겁니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "오늘 힘들었다면, 이 영상은 당신을 위한 것입니다.\n\n\"You are allowed to be both a masterpiece and a work in progress.\"\n\n자신에게 조금 더 부드러워지세요.\n내일은 조금 더 괜찮을 겁니다.\n\n이 글이 필요한 사람에게 보내주세요.\n\n#위로 #힐링 #오늘도수고했어 #직장인공감 #마음관리 #자기계발 #명언 #공감 #응원 #번아웃 #마음챙김 #당신은소중합니다 #selfcare #motivation #healing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "rain", "accent": (155, 89, 182),
                 "quote_en": "\"You don't have to be\nperfect to be amazing.\"",
                 "title": "완벽하지 않아도\n당신은 이미\n대단한 사람입니다", "source": ""},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"It's okay to not be okay.\"",
                 "title": "괜찮지 않아도\n괜찮습니다",
                 "body": "모든 감정은\n있는 그대로\n존중받을 자격이 있습니다"},
                {"dur": 7, "style": "golden", "accent": (29, 158, 117),
                 "quote_en": "", "title": "지금 이 순간에도\n당신을 응원하는\n사람이 있습니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신은 혼자가\n아닙니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "완벽하지 않아도 괜찮습니다.\n\n\"You don't have to be perfect to be amazing.\"\n\n괜찮지 않아도 괜찮아요.\n모든 감정은 있는 그대로 존중받을 자격이 있습니다.\n\n이 영상을 저장해두세요.\n\n#위로 #힘내 #괜찮아 #직장인힐링 #마음관리 #공감 #응원 #자존감 #selfcare #youarenotalone #mentalhealth #healing #motivation #keepgoing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The wound is the place\nwhere the light enters you.\"",
                 "title": "상처받은 곳으로\n빛이 들어옵니다", "source": "- Rumi"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "울어도 됩니다\n쉬어도 됩니다\n다만 포기하지 마세요",
                 "body": ""},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "\"Stars can't shine\nwithout darkness.\"",
                 "title": "어둠이 없으면\n별도 빛나지\n못합니다", "source": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "어두운 밤이 지나면\n반드시 새벽이 옵니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "상처받은 곳으로 빛이 들어옵니다.\n- Rumi\n\n울어도 됩니다. 쉬어도 됩니다.\n다만 포기하지 마세요.\n\n어둠이 없으면 별도 빛나지 못합니다.\n어두운 밤이 지나면 반드시 새벽이 옵니다.\n\n#힐링 #위로 #명언 #루미 #공감 #응원 #마음챙김 #자기계발 #직장인 #새벽 #희망 #healing #rumi #motivation #keepgoing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Nature does not hurry,\nyet everything\nis accomplished.\"",
                 "title": "자연은 서두르지 않지만\n모든 것을\n이루어냅니다", "source": "- Lao Tzu"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "지친 마음에\n쉼표를 찍으세요",
                 "body": "쉬는 것도\n용기입니다"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "멈춰도 괜찮습니다\n숨을 고르고\n다시 걸으면 됩니다",
                 "body": ""},
                {"dur": 5, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "당신의 속도로\n충분합니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "지친 마음에 쉼표를 찍으세요.\n\n\"Nature does not hurry, yet everything is accomplished.\"\n- Lao Tzu\n\n쉬는 것도 용기입니다.\n멈춰도 괜찮습니다. 숨을 고르고 다시 걸으면 됩니다.\n\n#위로 #쉼 #힐링 #노자 #명언 #마음관리 #직장인공감 #번아웃 #쉬어도괜찮아 #마음챙김 #selfcare #rest #laotzu #burnoutrecovery #slowdown",
        },
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (231, 76, 60),
                 "quote_en": "\"Comparison is the thief\nof joy.\"",
                 "title": "비교는\n기쁨을 빼앗는\n도둑입니다", "source": "- Theodore Roosevelt"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "남과 비교하는 순간\n나의 가치는\n보이지 않게 됩니다",
                 "body": ""},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Be yourself;\neveryone else is\nalready taken.\"",
                 "title": "당신 자체로\n이미 충분합니다", "source": "- Oscar Wilde"},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘은 나에게\n따뜻한 말\n한마디 해주세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "비교하지 마세요.\n\n\"Comparison is the thief of joy.\"\n- Theodore Roosevelt\n\n남과 비교하는 순간 나의 가치는 보이지 않게 됩니다.\n당신 자체로 이미 충분합니다.\n\n#비교금지 #자존감 #위로 #명언 #마음관리 #직장인 #자기사랑 #공감 #selfworth #dontcompare #beyourself #selfcare #motivation #healing",
        },
        {
            "scenes": [
                {"dur": 8, "style": "rain", "accent": (155, 89, 182),
                 "quote_en": "\"Vulnerability is not winning\nor losing. It's having the\ncourage to show up.\"",
                 "title": "완벽하지 않은 모습을\n보여줄 수 있는 것이\n진짜 용기입니다", "source": "- Brené Brown"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "완벽하지 않은\n하루도 괜찮습니다",
                 "body": "오늘 하루를 살아낸 것만으로\n당신은 대단합니다"},
                {"dur": 7, "style": "golden", "accent": (29, 158, 117),
                 "quote_en": "", "title": "실수해도 됩니다\n넘어져도 됩니다\n그래도 당신은\n사랑받을 자격이 있습니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘도 충분히\n잘하고 있습니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "완벽하지 않은 하루도 괜찮습니다.\n\n\"Vulnerability is not winning or losing. It's having the courage to show up.\"\n- Brené Brown\n\n오늘 하루를 살아낸 것만으로 당신은 대단합니다.\n실수해도 됩니다. 그래도 사랑받을 자격이 있습니다.\n\n#위로 #브레네브라운 #취약함 #용기 #직장인힐링 #괜찮아 #공감 #자존감 #selfcare #vulnerability #courage #youareenough #healing #imperfect",
        },
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Walking with a friend\nin the dark is better than\nwalking alone in the light.\"",
                 "title": "어둠 속에서\n친구와 함께 걷는 것이\n혼자 빛 속을\n걷는 것보다 낫습니다", "source": "- Helen Keller"},
                {"dur": 7, "style": "rain", "accent": (155, 89, 182),
                 "quote_en": "", "title": "혼자라고\n느낄 때가 있나요",
                 "body": "당신 곁에는\n보이지 않는 손길이\n있습니다"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "힘든 시간은\n영원하지 않습니다\n지나갑니다",
                 "body": ""},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신은\n혼자가 아닙니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "혼자라고 느낄 때.\n\n\"Walking with a friend in the dark is better than walking alone in the light.\"\n- Helen Keller\n\n당신 곁에는 보이지 않는 손길이 있습니다.\n힘든 시간은 영원하지 않습니다.\n\n#위로 #헬렌켈러 #외로움 #공감 #힘내 #당신은혼자가아닙니다 #마음관리 #힐링 #youarenotalone #helenkeller #loneliness #healing #friendship #comfort",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"There is a sacredness\nin tears. They are not\nthe mark of weakness\nbut of power.\"",
                 "title": "눈물에는\n신성함이 있습니다\n그것은 약함이 아닌\n힘의 증거입니다", "source": "- Washington Irving"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "울고 싶을 때\n참지 마세요",
                 "body": "눈물은 마음이\n스스로를 치유하는\n방법입니다"},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "감정을 느끼는 것은\n살아있다는\n증거입니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘 울어도 됩니다\n내일 다시\n웃으면 됩니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "눈물은 약함이 아닙니다.\n\n\"There is a sacredness in tears. They are not the mark of weakness but of power.\"\n- Washington Irving\n\n울고 싶을 때 참지 마세요.\n눈물은 마음이 스스로를 치유하는 방법입니다.\n\n#위로 #눈물 #감정 #힐링 #공감 #마음관리 #직장인 #울어도괜찮아 #tears #healing #emotions #itsoktonotbeok #selfcare #mentalhealth",
        },
    ],
    "motivation": [
        {
            "scenes": [
                {"dur": 7, "style": "dawn", "accent": (231, 76, 60),
                 "quote_en": "\"The only limit to our\nrealization of tomorrow\nis our doubts of today.\"",
                 "title": "내일의 가능성을\n제한하는 것은\n오늘의 의심뿐입니다", "source": "- F.D. Roosevelt"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Don't watch the clock.\nDo what it does. Keep going.\"",
                 "title": "시계를 보지 마세요\n시계처럼 하세요\n계속 가세요", "source": "- Sam Levenson"},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "1%의 변화가\n365일이면\n37배가 됩니다",
                 "body": "오늘 작은 한 걸음이\n내일의 큰 변화가 됩니다"},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "지금 이 순간이\n시작하기에\n가장 좋은 때입니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "멈추지 마세요.\n\n\"Don't watch the clock. Do what it does. Keep going.\"\n- Sam Levenson\n\n1%의 변화가 365일이면 37배가 됩니다.\n오늘 작은 한 걸음이 내일의 큰 변화가 됩니다.\n\n지금이 시작하기에 가장 좋은 때입니다.\n\n#동기부여 #명언 #도전 #성장 #자기계발 #직장인 #변화 #시작 #1퍼센트 #습관 #motivation #keepgoing #growth #nevergiveup #dailymotivation",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Fall seven times,\nstand up eight.\"",
                 "title": "일곱 번 넘어지면\n여덟 번\n일어나면 됩니다", "source": "- 일본 속담"},
                {"dur": 7, "style": "dawn", "accent": (231, 76, 60),
                 "quote_en": "\"Strength doesn't come from\nwhat you can do.\nIt comes from overcoming what\nyou thought you couldn't.\"",
                 "title": "진짜 강함은\n못한다고 생각한 것을\n해냈을 때 옵니다", "source": ""},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "실패는 끝이 아닙니다\n다시 시작할\n용기만 있다면",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신은 생각보다\n강한 사람입니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "넘어져도 괜찮습니다.\n\n\"Fall seven times, stand up eight.\"\n\n진짜 강함은 못한다고 생각한 것을 해냈을 때 옵니다.\n실패는 끝이 아닙니다. 다시 시작할 용기만 있다면.\n\n당신은 생각보다 강한 사람입니다.\n\n#동기부여 #명언 #도전 #실패 #성장 #자기계발 #용기 #강함 #직장인 #힘내 #motivation #strength #nevergiveup #resilience #keepgoing",
        },
        {
            "scenes": [
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Your time is limited.\nDon't waste it living\nsomeone else's life.\"",
                 "title": "당신의 시간은\n한정되어 있습니다\n남의 인생을\n살지 마세요", "source": "- Steve Jobs"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The future belongs to those\nwho believe in the beauty\nof their dreams.\"",
                 "title": "꿈의 아름다움을\n믿는 사람에게\n미래가 열립니다", "source": "- Eleanor Roosevelt"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "남들과 비교하지 마세요\n어제의 나와\n비교하세요",
                 "body": "당신만의 속도가 있습니다"},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신의 꿈을\n포기하지 마세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "남의 인생을 살지 마세요.\n\n\"Your time is limited. Don't waste it living someone else's life.\"\n- Steve Jobs\n\n남들과 비교하지 마세요. 어제의 나와 비교하세요.\n당신만의 속도가 있습니다.\n\n#동기부여 #스티브잡스 #명언 #꿈 #자기계발 #나만의속도 #비교 #성장 #직장인 #도전 #motivation #stevejobs #dreams #growthmindset #believeinyourself",
        },
        {
            "scenes": [
                {"dur": 7, "style": "night", "accent": (231, 76, 60),
                 "quote_en": "\"Courage is not the absence\nof fear, but the triumph\nover it.\"",
                 "title": "용기란\n두려움이 없는 것이\n아니라\n두려움을 이기는 것입니다", "source": "- Mark Twain"},
                {"dur": 7, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "두려움 앞에서\n한 발만\n내딛으세요",
                 "body": "그 한 발이\n모든 것을 바꿉니다"},
                {"dur": 7, "style": "golden", "accent": (29, 158, 117),
                 "quote_en": "\"Do the thing you fear\nand the death of fear\nis certain.\"",
                 "title": "두려운 일을 하면\n두려움이\n사라집니다", "source": "- Ralph W. Emerson"},
                {"dur": 5, "style": "dawn", "accent": (231, 76, 60),
                 "quote_en": "", "title": "오늘 두려운 것\n하나를 해보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "두려움을 넘어서세요.\n\n\"Courage is not the absence of fear, but the triumph over it.\"\n- Mark Twain\n\n두려움 앞에서 한 발만 내딛으세요.\n그 한 발이 모든 것을 바꿉니다.\n\n#동기부여 #용기 #두려움 #도전 #마크트웨인 #명언 #성장 #직장인 #courage #fear #motivation #marktwain #onestep #nevergiveup",
        },
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"A journey of a\nthousand miles begins\nwith a single step.\"",
                 "title": "천 리 길도\n한 걸음부터\n시작됩니다", "source": "- Lao Tzu"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "거창한 시작이\n필요한 게 아닙니다",
                 "body": "아주 작은 것부터\n시작하세요"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "오늘 5분만\n투자하세요\n그것이 시작입니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "작게 시작하세요\n꾸준히 하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "작게 시작하세요.\n\n\"A journey of a thousand miles begins with a single step.\"\n- Lao Tzu\n\n거창한 시작이 필요한 게 아닙니다.\n오늘 5분만 투자하세요. 그것이 시작입니다.\n\n#동기부여 #시작 #노자 #명언 #작은시작 #5분 #습관 #자기계발 #직장인 #도전 #motivation #laotzu #startsmall #firstep #dailyhabits",
        },
        {
            "scenes": [
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The biggest adventure\nyou can take is to live\nthe life of your dreams.\"",
                 "title": "당신이 할 수 있는\n가장 큰 모험은\n꿈꾸던 삶을\n사는 것입니다", "source": "- Oprah Winfrey"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "어제의 나보다\n오늘의 내가\n조금이라도 나으면\n그것이 성공입니다",
                 "body": ""},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Turn your wounds\ninto wisdom.\"",
                 "title": "상처를\n지혜로 바꾸세요", "source": "- Oprah Winfrey"},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "당신의 이야기는\n아직 끝나지\n않았습니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "어제보다 나은 오늘.\n\n\"The biggest adventure you can take is to live the life of your dreams.\"\n- Oprah Winfrey\n\n어제의 나보다 오늘의 내가 조금이라도 나으면 그것이 성공입니다.\n당신의 이야기는 아직 끝나지 않았습니다.\n\n#동기부여 #오프라윈프리 #명언 #꿈 #도전 #성장 #자기계발 #직장인 #변화 #성공 #motivation #oprah #dreams #growthmindset #bettereveryday",
        },
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (186, 117, 23),
                 "quote_en": "\"I have not failed.\nI've just found 10,000 ways\nthat won't work.\"",
                 "title": "나는 실패한 것이\n아닙니다\n안 되는 방법 만 가지를\n찾은 것뿐입니다", "source": "- Thomas Edison"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "실패는\n끝이 아니라\n데이터입니다",
                 "body": "한 번 더 시도할\n이유가 생긴 것입니다"},
                {"dur": 7, "style": "golden", "accent": (231, 76, 60),
                 "quote_en": "", "title": "넘어질 때마다\n일어설 때마다\n당신은 더\n강해지고 있습니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "실패를 두려워하지\n마세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "실패는 데이터입니다.\n\n\"I have not failed. I've just found 10,000 ways that won't work.\"\n- Thomas Edison\n\n한 번 더 시도할 이유가 생긴 것입니다.\n넘어질 때마다 일어설 때마다 당신은 더 강해지고 있습니다.\n\n#동기부여 #에디슨 #실패 #도전 #명언 #성장 #자기계발 #직장인 #다시시작 #resilience #edison #failure #motivation #nevergiveup #tryagain",
        },
        {
            "scenes": [
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Life is a journey,\nnot a destination.\"",
                 "title": "인생은 목적지가\n아니라\n여정입니다", "source": "- Ralph W. Emerson"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "결과에 집착하면\n과정의 아름다움을\n놓치게 됩니다",
                 "body": ""},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Enjoy the little things,\nfor one day you may\nlook back and realize\nthey were the big things.\"",
                 "title": "작은 것을\n즐기세요\n나중에 돌아보면\n그것이 큰 것이었습니다", "source": "- Robert Brault"},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘 이 순간을\n즐기세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "결과보다 과정을 즐기세요.\n\n\"Life is a journey, not a destination.\"\n- Ralph W. Emerson\n\n결과에 집착하면 과정의 아름다움을 놓치게 됩니다.\n작은 것을 즐기세요.\n\n#동기부여 #에머슨 #명언 #여정 #과정 #자기계발 #직장인 #마음관리 #성장 #현재 #motivation #emerson #journey #enjoytheprocess #littlethings",
        },
    ],
    "growth": [
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Small daily improvements\nare the key to staggering\nlong-term results.\"",
                 "title": "매일의 작은 개선이\n놀라운 결과를\n만들어냅니다", "source": ""},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "습관이 바뀌면\n인생이 바뀝니다",
                 "body": "아침 5분의 루틴이\n하루 전체를 바꿉니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"We are what we\nrepeatedly do.\nExcellence is not an act\nbut a habit.\"",
                 "title": "탁월함은\n행동이 아니라\n습관입니다", "source": "- Aristotle"},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘부터\n작게 시작하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "매일 1%씩 성장하세요.\n\n\"Small daily improvements are the key to staggering long-term results.\"\n\n습관이 바뀌면 인생이 바뀝니다.\n아침 5분의 루틴이 하루 전체를 바꿉니다.\n\n오늘부터 작게 시작하세요.\n\n#자기계발 #습관 #성장 #아침루틴 #1퍼센트 #아리스토텔레스 #명언 #직장인 #자기관리 #변화 #dailyhabits #growth #selfdevelopment #morningroutine #habits",
        },
        {
            "scenes": [
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The only person you are\ndestined to become\nis the person you decide\nto be.\"",
                 "title": "당신이 될 수 있는\n유일한 사람은\n당신이 되기로\n결심한 사람입니다", "source": "- Ralph W. Emerson"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "독서 10분\n운동 20분\n감사 5분",
                 "body": "이 35분이\n1년 후 당신을\n완전히 바꿉니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Invest in yourself.\nIt pays the best interest.\"",
                 "title": "자기 자신에게\n투자하세요\n그것이 최고의\n이자를 줍니다", "source": "- Benjamin Franklin"},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "성장은 선택입니다\n오늘 선택하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "자기 자신에게 투자하세요.\n\n\"Invest in yourself. It pays the best interest.\"\n- Benjamin Franklin\n\n독서 10분, 운동 20분, 감사 5분.\n이 35분이 1년 후 당신을 완전히 바꿉니다.\n\n성장은 선택입니다. 오늘 선택하세요.\n\n#자기계발 #자기투자 #성장 #독서 #운동 #감사 #벤자민프랭클린 #명언 #습관 #루틴 #selfdevelopment #investinyourself #reading #growth #dailyroutine",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"The more that you read,\nthe more things you will know.\nThe more that you learn,\nthe more places you'll go.\"",
                 "title": "더 많이 읽을수록\n더 많이 알게 되고\n더 많이 배울수록\n더 멀리 갑니다", "source": "- Dr. Seuss"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "하루 10분 독서가\n인생을 바꿉니다",
                 "body": "1년이면 책 12권\n10년이면 120권"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "책 한 권이\n인생의 방향을\n바꿀 수 있습니다",
                 "body": ""},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘 10분\n책을 펼쳐보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "독서가 바꾸는 인생.\n\n\"The more that you read, the more things you will know.\"\n- Dr. Seuss\n\n하루 10분 독서가 인생을 바꿉니다.\n1년이면 책 12권, 10년이면 120권.\n\n오늘 10분 책을 펼쳐보세요.\n\n#독서 #자기계발 #성장 #책 #습관 #10분독서 #명언 #직장인 #reading #books #growth #drseuss #dailyhabits #selfdevelopment #readmore",
        },
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"Gratitude turns what we\nhave into enough.\"",
                 "title": "감사는\n가진 것을\n충분하게\n만들어줍니다", "source": "- Melody Beattie"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "매일 감사한 것\n세 가지만\n적어보세요",
                 "body": "작은 것이라도\n괜찮습니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "감사하는 사람은\n불평하는 사람보다\n행복합니다",
                 "body": "이것은 과학이\n증명한 사실입니다"},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘 감사한 것\n하나를 떠올려보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "감사의 힘.\n\n\"Gratitude turns what we have into enough.\"\n- Melody Beattie\n\n매일 감사한 것 세 가지만 적어보세요.\n감사하는 사람은 불평하는 사람보다 행복합니다.\n\n#감사 #자기계발 #성장 #행복 #습관 #마음관리 #명언 #직장인 #gratitude #thankful #happiness #dailyhabits #selfcare #mentalhealth #growth",
        },
        {
            "scenes": [
                {"dur": 7, "style": "night", "accent": (231, 76, 60),
                 "quote_en": "\"Until we can manage time,\nwe can manage\nnothing else.\"",
                 "title": "시간을 관리하지\n못하면\n아무것도 관리할 수\n없습니다", "source": "- Peter Drucker"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "하루의 첫 1시간이\n나머지 23시간을\n결정합니다",
                 "body": ""},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "중요한 일을\n먼저 하세요\n급한 일에\n끌려다니지 마세요",
                 "body": ""},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "내일의 나를 위해\n오늘을 설계하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "시간 관리의 비밀.\n\n\"Until we can manage time, we can manage nothing else.\"\n- Peter Drucker\n\n하루의 첫 1시간이 나머지 23시간을 결정합니다.\n중요한 일을 먼저 하세요. 급한 일에 끌려다니지 마세요.\n\n#시간관리 #자기계발 #성장 #피터드러커 #명언 #직장인 #생산성 #루틴 #timemanagement #productivity #growth #peterdrucker #prioritize #morningroutine",
        },
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (52, 152, 219),
                 "quote_en": "\"Becoming is better\nthan being.\"",
                 "title": "되어가는 것이\n이미 된 것보다\n낫습니다", "source": "- Carol Dweck"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "마인드셋이\n전부입니다",
                 "body": "\"나는 아직 못해\"가 아니라\n\"나는 아직 배우는 중\""},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "\"The view of yourself\ncan determine everything.\"",
                 "title": "자신을 바라보는\n시선이\n모든 것을 결정합니다", "source": "- Carol Dweck"},
                {"dur": 5, "style": "dawn", "accent": (52, 152, 219),
                 "quote_en": "", "title": "성장하는 마음을\n선택하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "마인드셋이 전부입니다.\n\n\"Becoming is better than being.\"\n- Carol Dweck\n\n\"나는 아직 못해\"가 아니라 \"나는 아직 배우는 중\".\n자신을 바라보는 시선이 모든 것을 결정합니다.\n\n#마인드셋 #성장 #자기계발 #캐롤드웩 #명언 #변화 #성장마인드셋 #직장인 #mindset #growthmindset #caroldweck #becoming #selfdevelopment #growth",
        },
        {
            "scenes": [
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"Celebrate what you've\naccomplished, but raise\nthe bar a little higher\neach time you succeed.\"",
                 "title": "성취한 것을\n축하하되\n성공할 때마다\n기준을 높이세요", "source": "- Mia Hamm"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "작은 승리를\n축하하세요",
                 "body": "오늘 아침 일찍 일어난 것\n운동한 것\n책 한 페이지 읽은 것"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "작은 성취가 쌓여\n큰 변화가 됩니다",
                 "body": ""},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘의 작은 승리를\n기록하세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "작은 승리를 축하하세요.\n\n오늘 아침 일찍 일어난 것, 운동한 것, 책 한 페이지 읽은 것.\n이 모든 것이 승리입니다.\n\n작은 성취가 쌓여 큰 변화가 됩니다.\n\n#작은승리 #자기계발 #성장 #축하 #습관 #성취 #직장인 #자기관리 #smallwins #celebrate #dailyhabits #growth #selfdevelopment #progress #achievements",
        },
    ],
    "healing": [
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"In every walk with nature,\none receives far more\nthan he seeks.\"",
                 "title": "자연 속을 걸을 때\n우리는 구하는 것보다\n훨씬 더 많은 것을\n받습니다", "source": "- John Muir"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "바람 소리를\n들어보세요\n나뭇잎 흔들리는 것을\n바라보세요",
                 "body": "자연은 최고의\n치유자입니다"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "하루 10분\n하늘을 올려다보는\n것만으로도\n마음이 가벼워집니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘 잠깐\n바깥 공기를\n마셔보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "자연이 주는 위로.\n\n\"In every walk with nature, one receives far more than he seeks.\"\n- John Muir\n\n바람 소리를 들어보세요. 하늘을 올려다보세요.\n하루 10분이면 마음이 가벼워집니다.\n\n#힐링 #자연 #존뮤어 #명언 #마음관리 #산책 #치유 #쉼 #바람 #하늘 #nature #healing #johnmuir #mindfulness #peace #outdoors",
        },
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (155, 89, 182),
                 "quote_en": "\"Music expresses that which\ncannot be said and on which\nit is impossible to be silent.\"",
                 "title": "음악은\n말로 표현할 수 없지만\n침묵할 수도 없는 것을\n표현합니다", "source": "- Victor Hugo"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "좋아하는 음악을\n틀어보세요",
                 "body": "음악은 영혼의\n약입니다"},
                {"dur": 7, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "", "title": "시간이 음악처럼\n흘러가듯\n힘든 순간도\n지나갑니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (155, 89, 182),
                 "quote_en": "", "title": "오늘 마음을\n위로하는 음악\n한 곡 들어보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "음악처럼 흐르는 시간.\n\n\"Music expresses that which cannot be said.\"\n- Victor Hugo\n\n좋아하는 음악을 틀어보세요. 음악은 영혼의 약입니다.\n힘든 순간도 음악처럼 흘러갑니다.\n\n#힐링 #음악 #위로 #빅토르위고 #명언 #마음관리 #감성 #쉼 #healing #music #victorhugo #soulmusic #peace #comfort #mindfulness",
        },
        {
            "scenes": [
                {"dur": 8, "style": "rain", "accent": (52, 152, 219),
                 "quote_en": "\"All of humanity's problems\nstem from man's inability\nto sit quietly in a room\nalone.\"",
                 "title": "인간의 모든 문제는\n방 안에 조용히\n혼자 앉아있지\n못하는 데서 옵니다", "source": "- Blaise Pascal"},
                {"dur": 7, "style": "night", "accent": (29, 158, 117),
                 "quote_en": "", "title": "고요함 속에서\n나를 만나보세요",
                 "body": "소음을 끄고\n자신의 목소리를\n들어보세요"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "하루 5분의 침묵이\n마음의 소음을\n잠재웁니다",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (52, 152, 219),
                 "quote_en": "", "title": "오늘 5분\n조용히 앉아보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "고요함 속에서 찾는 나.\n\n\"All of humanity's problems stem from man's inability to sit quietly in a room alone.\"\n- Blaise Pascal\n\n소음을 끄고 자신의 목소리를 들어보세요.\n하루 5분의 침묵이 마음의 소음을 잠재웁니다.\n\n#힐링 #고요 #명상 #파스칼 #명언 #마음관리 #침묵 #내면 #silence #meditation #peace #pascal #mindfulness #innerpeace #quiettime",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"To love at all\nis to be vulnerable.\"",
                 "title": "사랑한다는 것은\n상처받을 수\n있다는 것입니다", "source": "- C.S. Lewis"},
                {"dur": 7, "style": "rain", "accent": (155, 89, 182),
                 "quote_en": "", "title": "감정을 느끼는\n용기를 가지세요",
                 "body": "아픈 만큼\n성숙해집니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Grief is the price\nwe pay for love.\"",
                 "title": "슬픔은\n사랑의 대가입니다", "source": "- Queen Elizabeth II"},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "사랑했기에\n아픈 겁니다\n그래서 아름답습니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "감정을 느끼는 용기.\n\n\"To love at all is to be vulnerable.\"\n- C.S. Lewis\n\n감정을 느끼는 용기를 가지세요.\n사랑했기에 아픈 겁니다. 그래서 아름답습니다.\n\n#힐링 #사랑 #CSLewis #명언 #감정 #위로 #마음관리 #치유 #love #vulnerability #cslewis #healing #emotions #grief #beauty",
        },
    ],
    "mindset": [
        {
            "scenes": [
                {"dur": 8, "style": "night", "accent": (186, 117, 23),
                 "quote_en": "\"The happiness of your life\ndepends upon the quality\nof your thoughts.\"",
                 "title": "당신 인생의 행복은\n당신 생각의 질에\n달려 있습니다", "source": "- Marcus Aurelius"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "생각이 바뀌면\n말이 바뀌고\n말이 바뀌면\n인생이 바뀝니다",
                 "body": ""},
                {"dur": 7, "style": "golden", "accent": (231, 76, 60),
                 "quote_en": "\"You have power over\nyour mind, not outside\nevents. Realize this,\nand you will find strength.\"",
                 "title": "당신은 외부 사건이\n아닌 자신의 마음을\n다스릴 수 있습니다", "source": "- Marcus Aurelius"},
                {"dur": 5, "style": "dawn", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘 어떤 생각을\n선택하시겠습니까",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "생각이 운명을 만듭니다.\n\n\"The happiness of your life depends upon the quality of your thoughts.\"\n- Marcus Aurelius\n\n생각이 바뀌면 말이 바뀌고, 말이 바뀌면 인생이 바뀝니다.\n오늘 어떤 생각을 선택하시겠습니까?\n\n#마음가짐 #스토아철학 #마르쿠스아우렐리우스 #명언 #생각 #마인드셋 #자기계발 #직장인 #mindset #stoicism #marcusaurelius #thoughts #philosophy #mentalstrength #selfcontrol",
        },
        {
            "scenes": [
                {"dur": 8, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "\"It's not what happens\nto you, but how you\nreact to it that matters.\"",
                 "title": "중요한 것은\n무슨 일이 일어났느냐가\n아니라\n어떻게 반응하느냐입니다", "source": "- Epictetus"},
                {"dur": 7, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "내가 통제할 수\n있는 것에\n집중하세요",
                 "body": "날씨는 못 바꾸지만\n우산은 챙길 수 있습니다"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "", "title": "감정에\n휘둘리지 마세요\n감정을\n관찰하세요",
                 "body": ""},
                {"dur": 5, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "오늘 반응하기 전에\n한 번만\n멈춰보세요",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "감정에 휘둘리지 않기.\n\n\"It's not what happens to you, but how you react to it that matters.\"\n- Epictetus\n\n내가 통제할 수 있는 것에 집중하세요.\n감정에 휘둘리지 말고 감정을 관찰하세요.\n\n#마음가짐 #에픽테토스 #스토아 #명언 #감정관리 #마인드셋 #자기계발 #직장인 #mindset #stoicism #epictetus #emotionalcontrol #selfawareness #mentalhealth #innerpeace",
        },
        {
            "scenes": [
                {"dur": 8, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "\"There are only two days\nin the year that nothing\ncan be done. One is called\nyesterday and the other\nis called tomorrow.\"",
                 "title": "아무것도 할 수 없는\n날은 딱 이틀입니다\n어제와 내일", "source": "- Dalai Lama"},
                {"dur": 7, "style": "dawn", "accent": (29, 158, 117),
                 "quote_en": "", "title": "과거에 머물지 마세요\n미래를 걱정하지 마세요",
                 "body": "지금 이 순간에\n온전히 머무세요"},
                {"dur": 7, "style": "night", "accent": (52, 152, 219),
                 "quote_en": "\"Be present.\nIt is the only moment\nthat matters.\"",
                 "title": "현재에 집중하세요\n그것이 유일하게\n중요한 순간입니다", "source": ""},
                {"dur": 5, "style": "golden", "accent": (186, 117, 23),
                 "quote_en": "", "title": "오늘에 집중하세요\n지금 이 순간이\n당신의 전부입니다",
                 "body": "@lighthouse_media77"},
            ],
            "cap": "오늘에 집중하세요.\n\n\"There are only two days in the year that nothing can be done. Yesterday and tomorrow.\"\n- Dalai Lama\n\n과거에 머물지 마세요. 미래를 걱정하지 마세요.\n지금 이 순간에 온전히 머무세요.\n\n#마음가짐 #달라이라마 #현재 #명언 #마인드셋 #마음관리 #직장인 #오늘 #mindset #dalailama #bepresent #mindfulness #today #letgo #innerpeace",
        },
    ],
}

# ═══════════════════════════════════════════════════════════════
# 프레임 생성
# ═══════════════════════════════════════════════════════════════
def make_frames(scenes, name):
    frames_dir = os.path.join(OUT_DIR, f"frames_{name}")
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    fnum = 0
    total_dur = sum(s.get("dur", 8) for s in scenes)

    for si, sc in enumerate(scenes):
        dur = sc.get("dur", 8)
        style = sc.get("style", "dark")
        accent = sc.get("accent", (29, 158, 117))
        elapsed = sum(scenes[j].get("dur", 8) for j in range(si))

        for f in range(dur * FPS):
            fp = f / max(dur * FPS, 1)
            tp = (elapsed + dur * fp) / total_dur
            fade = min(1.0, fp * 4)
            if fp > 0.8:
                fade = max(0, (1 - fp) * 5)

            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)

            # 배경
            seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
            if style == "dawn":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(10 + p * 40), int(15 + p * 30), int(35 + p * 45)))
            elif style == "night":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(5 + p * 3), int(5 + p * 5), int(15 + p * 10)))
                random.seed(seed)
                for _ in range(80):
                    x, y2 = random.randint(0, W), random.randint(0, H // 2)
                    br = random.randint(150, 255)
                    d.ellipse([x - 1, y2 - 1, x + 1, y2 + 1], fill=(br, br, br))
            elif style == "golden":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(25 + p * 30), int(15 + p * 18), int(5 + p * 8)))
            elif style == "rain":
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(8 + p * 4), int(10 + p * 6), int(18 + p * 10)))
                random.seed(int(fp * 100) + seed)
                for _ in range(30):
                    x = random.randint(0, W)
                    ys = random.randint(0, H - 80)
                    d.line([(x, ys), (x - 3, ys + 60)], fill=(50, 55, 70), width=1)
            else:
                for row in range(H):
                    p = row / H
                    d.line([(0, row), (W, row)], fill=(int(8 + p * 6), int(10 + p * 8), int(20 + p * 12)))

            # 시네마틱 바
            d.rectangle([0, 0, W, 70], fill=(0, 0, 0))
            d.rectangle([0, H - 70, W, H], fill=(0, 0, 0))

            bc = tuple(int(c * fade) for c in accent)
            d.rectangle([0, 70, W, 73], fill=bc)

            # 브랜드
            d.text((60, 85), "LIGHTHOUSE MEDIA", font=gf(18), fill=tuple(int(c * fade * 0.5) for c in accent))

            # 영어 명언
            qe = sc.get("quote_en", "")
            if qe:
                tc(d, 320, qe, gf_en(26), tuple(int(140 * fade) for _ in range(3)), 6)

            # 구분선
            lw = int(100 * min(1, fp * 3))
            if lw > 0:
                d.rectangle([W // 2 - lw, 490, W // 2 + lw, 492], fill=bc)

            # 한글 제목
            title = sc.get("title", "")
            tc(d, 540, title, gf(52, True), tuple(int(255 * fade) for _ in range(3)), 20)

            # 부제
            body = sc.get("body", "")
            if body:
                tc(d, 880, body, gf(26, False), tuple(int(160 * fade) for _ in range(3)), 10)

            # 출처
            src = sc.get("source", "")
            if src:
                tc(d, H - 220, src, gf(20, False), tuple(int(c * fade * 0.5) for c in accent))

            # 하단 장식
            d.rectangle([W // 2 - 25, H - 140, W // 2 + 25, H - 137], fill=bc)
            tc(d, H - 120, "@lighthouse_media77", gf(14, False), tuple(int(50 * fade) for _ in range(3)))

            # 진행바
            d.rectangle([0, H - 70, int(W * tp), H - 67], fill=bc)

            img.save(os.path.join(frames_dir, f"frame_{fnum:05d}.png"))
            fnum += 1

    return frames_dir, total_dur, fnum


# ═══════════════════════════════════════════════════════════════
# 영상 인코딩
# ═══════════════════════════════════════════════════════════════
def encode_video(frames_dir, total_dur, bgm_file, output_name):
    vpath = os.path.join(OUT_DIR, f"{output_name}.mp4")
    bgm_path = os.path.join(BGM_DIR, bgm_file)

    cmd = [FFMPEG, "-y",
           "-framerate", str(FPS), "-i", os.path.join(frames_dir, "frame_%05d.png"),
           "-i", bgm_path,
           "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k",
           "-filter_complex", f"[1:a]afade=t=in:d=1,afade=t=out:st={max(1, total_dur - 2)}:d=2,volume=0.3[a]",
           "-map", "0:v", "-map", "[a]",
           "-vf", f"scale={W}:{H},fps=30",
           "-t", str(total_dur), "-shortest",
           vpath]

    subprocess.run(cmd, capture_output=True, timeout=120)
    shutil.rmtree(frames_dir, ignore_errors=True)

    return vpath if os.path.exists(vpath) else None


# ═══════════════════════════════════════════════════════════════
# 업로드 (Instagram Reels + Facebook)
# ═══════════════════════════════════════════════════════════════
def upload_ig_reels(vpath, caption):
    # Imgur에 영상 업로드
    with open(vpath, 'rb') as f:
        enc = base64.b64encode(f.read()).decode()
    ir = requests.post('https://api.imgur.com/3/upload',
                       headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                       data={'video': enc, 'type': 'base64'}, timeout=120)
    vid_url = ir.json().get('data', {}).get('link')
    if not vid_url:
        print("    Imgur upload failed")
        return None

    print(f"    Imgur OK: {vid_url}")

    # 릴스 컨테이너 생성
    r = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media', data={
        'video_url': vid_url,
        'media_type': 'REELS',
        'caption': caption,
        'access_token': IG_TOKEN,
    }, timeout=30)
    d = r.json()
    if 'id' not in d:
        print(f"    IG container failed: {d}")
        return None

    container_id = d['id']
    print(f"    IG container: {container_id}")

    # 처리 대기
    for attempt in range(18):  # 최대 3분
        time.sleep(10)
        check = requests.get(
            f'https://graph.facebook.com/v21.0/{container_id}?fields=status_code&access_token={IG_TOKEN}',
            timeout=10)
        status = check.json().get('status_code', '')
        if status == 'FINISHED':
            r2 = requests.post(f'https://graph.facebook.com/v21.0/{IG_ID}/media_publish',
                               data={'creation_id': container_id, 'access_token': IG_TOKEN}, timeout=30)
            return r2.json().get('id')
        elif status == 'ERROR':
            print(f"    IG processing error")
            return None
        print(f"    Processing... ({(attempt + 1) * 10}s)")
    return None


def upload_fb_video(vpath, description):
    with open(vpath, 'rb') as f:
        r = requests.post(f'https://graph.facebook.com/v21.0/{FB_PAGE}/videos',
                          files={'source': (os.path.basename(vpath), f, 'video/mp4')},
                          data={'description': description[:500], 'access_token': FB_TOKEN}, timeout=120)
    return r.json()


# ═══════════════════════════════════════════════════════════════
# 오늘의 릴스 선택 (날짜 기반 결정적 랜덤)
# ═══════════════════════════════════════════════════════════════
def pick_today_reel(category=None):
    today = datetime.now().strftime("%Y-%m-%d")
    categories = list(REEL_POOL.keys())

    if category and category in REEL_POOL:
        cat = category
    else:
        # 날짜 기반으로 카테고리 순환
        day_num = int(datetime.now().strftime("%j"))  # 1~366
        cat = categories[day_num % len(categories)]

    pool = REEL_POOL[cat]
    # 날짜 기반으로 풀 내 선택
    seed = int(hashlib.md5(today.encode()).hexdigest()[:8], 16)
    idx = seed % len(pool)

    return cat, pool[idx], today


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════
def main():
    category = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("  DAILY INSTAGRAM REELS")
    print("=" * 60)

    cat, reel, today = pick_today_reel(category)
    name = f"daily-{today}-{cat}"

    print(f"\n  Date: {today}")
    print(f"  Category: {cat}")

    # BGM 선택
    bgm_files = [f for f in os.listdir(BGM_DIR) if f.endswith('.mp3')]
    bgm = random.choice(bgm_files)
    print(f"  BGM: {bgm}")

    # 프레임 생성
    print("\n  Generating frames...")
    frames_dir, total_dur, fnum = make_frames(reel["scenes"], name)
    print(f"  {fnum} frames ({total_dur}s)")

    # 영상 인코딩
    print("  Encoding video...")
    vpath = encode_video(frames_dir, total_dur, bgm, name)
    if not vpath:
        print("  ENCODE FAILED!")
        return
    sz = os.path.getsize(vpath) / (1024 * 1024)
    print(f"  Video: {vpath} ({sz:.1f}MB)")

    # Facebook 업로드
    print("\n  Uploading to Facebook...")
    fb = upload_fb_video(vpath, reel["cap"])
    print(f"  FB: {'OK (' + str(fb.get('id', '')) + ')' if 'id' in fb else fb}")
    time.sleep(3)

    # Instagram Reels 업로드
    print("\n  Uploading to Instagram Reels...")
    ig = upload_ig_reels(vpath, reel["cap"])
    print(f"  IG Reels: {'OK (' + str(ig) + ')' if ig else 'Failed or processing'}")

    print(f"\n{'=' * 60}")
    print(f"  DAILY REELS DONE!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
