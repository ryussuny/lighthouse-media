"""자동 참여: 유사 계정 게시물에 댓글 + 우리 게시물 댓글 자동 답변"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, random
from datetime import datetime

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"

ENGAGED_FILE = os.path.join(HOME, "lighthouse-media", "data", "engaged-media.json")
REPLIED_FILE = os.path.join(HOME, "lighthouse-media", "data", "replied-comments.json")

def load_json(path):
    if os.path.exists(path): return json.load(open(path, encoding='utf-8'))
    return []

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f)

comments_outreach = [
    "공감됩니다! 좋은 글이에요 :)",
    "이런 글이 정말 필요했어요",
    "많은 분들이 봤으면 좋겠네요",
    "오늘 하루도 힘내세요!",
    "따뜻한 글 감사합니다",
    "정말 도움이 되는 내용이에요",
    "저장해두고 자주 볼게요!",
    "이 글이 위로가 됩니다",
    "좋은 콘텐츠 감사합니다",
    "응원합니다! 파이팅!",
]

reply_templates = {
    "ebook": "@{user} 감사합니다! 무료 전자책 18권은 프로필 링크에서 바로 다운로드 가능합니다 :)",
    "empathy": "@{user} 공감해주셔서 감사해요. 혼자가 아니에요! 프로필에서 무료 전자책도 받아가세요 :)",
    "thanks": "@{user} 따뜻한 말씀 감사합니다! 앞으로도 도움되는 콘텐츠 만들겠습니다 :)",
    "vote": "@{user} 답변 감사합니다! 솔직한 공유가 서로에게 위로가 됩니다 :)",
    "default": "@{user} 댓글 감사합니다! 프로필 링크에서 무료 전자책 18권도 확인해보세요 :)",
}

def auto_engage_hashtags():
    """유사 계정 게시물에 댓글 달기"""
    engaged = load_json(ENGAGED_FILE)
    tags = ['직장인힐링', '마음관리', '번아웃극복', '자기계발', '동기부여', '직장인공감', '힐링', '멘탈케어']
    random.shuffle(tags)
    new_count = 0

    for tag in tags[:3]:  # 매번 3개 태그만 (속도 제한 방지)
        try:
            r = requests.get(f'https://graph.facebook.com/v21.0/ig_hashtag_search?q={tag}&user_id={IG_ID}&access_token={TOKEN}')
            data = r.json().get('data',[])
            if not data: continue
            tag_id = data[0]['id']

            r2 = requests.get(f'https://graph.facebook.com/v21.0/{tag_id}/recent_media?user_id={IG_ID}&fields=id&limit=5&access_token={TOKEN}')
            media = r2.json().get('data',[])

            for m in media[:2]:  # 태그당 2개만
                mid = m['id']
                if mid in engaged: continue

                comment = random.choice(comments_outreach)
                r3 = requests.post(f'https://graph.facebook.com/v21.0/{mid}/comments', data={
                    'message': comment, 'access_token': TOKEN
                })
                if 'id' in r3.json():
                    engaged.append(mid)
                    new_count += 1
                    print(f"  #{tag}: OK")
                time.sleep(8)
        except: pass

    save_json(ENGAGED_FILE, engaged)
    return new_count

def auto_reply_comments():
    """우리 게시물 댓글 자동 답변"""
    replied = load_json(REPLIED_FILE)
    new_count = 0

    r = requests.get(f'https://graph.facebook.com/v21.0/{IG_ID}/media?fields=id,comments_count&limit=20&access_token={TOKEN}')
    for post in r.json().get('data',[]):
        if post.get('comments_count',0) == 0: continue

        r2 = requests.get(f'https://graph.facebook.com/v21.0/{post["id"]}/comments?fields=id,text,username&limit=20&access_token={TOKEN}')
        for c in r2.json().get('data',[]):
            if c['id'] in replied: continue
            user = c.get('username','user')
            # 우리 자신의 댓글은 무시 (자문자답 방지)
            if user == 'lighthouse_media77': continue
            text = c.get('text','').lower()

            if any(kw in text for kw in ['전자책','다운','링크','무료','책']):
                tmpl = 'ebook'
            elif any(kw in text for kw in ['공감','나도','저도','맞아','진짜','ㅠ']):
                tmpl = 'empathy'
            elif any(kw in text for kw in ['좋아','감사','고마','최고']):
                tmpl = 'thanks'
            elif len(text) <= 3:
                tmpl = 'vote'
            else:
                tmpl = 'default'

            reply = reply_templates[tmpl].format(user=user)
            r3 = requests.post(f'https://graph.facebook.com/v21.0/{c["id"]}/replies', data={
                'message': reply, 'access_token': TOKEN
            })
            if 'id' in r3.json():
                replied.append(c['id'])
                new_count += 1
                print(f"  @{user}: replied")
            time.sleep(5)

    # 페이스북도
    r = requests.get(f'https://graph.facebook.com/v21.0/{FB_PAGE}/posts?fields=id&limit=10&access_token={FB_TOKEN}')
    for post in r.json().get('data',[]):
        r2 = requests.get(f'https://graph.facebook.com/v21.0/{post["id"]}/comments?fields=id,message,from&limit=10&access_token={FB_TOKEN}')
        for c in r2.json().get('data',[]):
            if c['id'] in replied: continue
            name = c.get('from',{}).get('name','')
            r3 = requests.post(f'https://graph.facebook.com/v21.0/{c["id"]}/comments', data={
                'message': f'{name}님 감사합니다! 무료 전자책: https://lighthouse-media.onrender.com/ebook-library.html',
                'access_token': FB_TOKEN
            })
            if 'id' in r3.json():
                replied.append(c['id'])
                new_count += 1
            time.sleep(3)

    save_json(REPLIED_FILE, replied)
    return new_count

def main():
    now = datetime.now().strftime('%H:%M')
    print(f"[{now}] Auto-engage start")

    e = auto_engage_hashtags()
    print(f"  Outreach: {e} comments")

    r = auto_reply_comments()
    print(f"  Replies: {r}")

    print(f"  Done!")

if __name__ == "__main__":
    main()
