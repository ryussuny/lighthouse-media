"""인스타 댓글 자동 답변 + 전자책 링크 자동 발송"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, requests, time, re
from datetime import datetime

HOME = os.path.expanduser("~")
tokens = json.load(open(os.path.join(HOME, "lighthouse-media", "config", "tokens.json"), encoding='utf-8'))
IG_TOKEN = tokens['instagram']
FB_TOKEN = tokens['facebook_page']
IG_ID = "17841425580883266"
FB_PAGE = "1097948196731052"

SITE_URL = "https://lighthouse-media.onrender.com"
REPLIED_FILE = os.path.join(HOME, "lighthouse-media", "data", "replied-comments.json")

def load_replied():
    if os.path.exists(REPLIED_FILE):
        return json.load(open(REPLIED_FILE, encoding='utf-8'))
    return []

def save_replied(ids):
    os.makedirs(os.path.dirname(REPLIED_FILE), exist_ok=True)
    with open(REPLIED_FILE, 'w', encoding='utf-8') as f:
        json.dump(ids, f)

def reply_comment(comment_id, message):
    """댓글에 답글 달기"""
    r = requests.post(
        f'https://graph.facebook.com/v21.0/{comment_id}/replies',
        data={'message': message, 'access_token': IG_TOKEN}
    )
    return r.json()

def get_auto_reply(text, username):
    """댓글 내용에 따라 자동 답변 생성"""
    text_lower = text.lower().strip()

    # 전자책 요청 키워드
    ebook_keywords = ['전자책', '책', 'ebook', 'pdf', '다운', '받고', '보내', '링크', '무료', '나도', '저도', '부탁']
    # 공감 키워드
    empathy_keywords = ['공감', '맞아', '나도', '저도', '진짜', 'ㅠ', 'ㅜ', '힘들', '지친', '피곤', '죽겠', '그만두고']
    # 투표/선택 키워드
    vote_keywords = ['a', 'b', 'c', 'd', 'e', '1', '2', '3', '4', '5', 'lv']
    # 레벨 키워드
    level_keywords = ['lv.', 'lv1', 'lv2', 'lv3', 'lv4', 'lv5', '레벨']
    # 칭찬 키워드
    praise_keywords = ['좋아요', '감사', '고마', '도움', '좋은', '최고', '짱', '굿']
    # 손/이모지
    hand_keywords = ['손', '🙋', '✋', '🖐']
    # 태그
    tag_pattern = re.compile(r'@\w+')

    # 전자책 요청
    if any(kw in text_lower for kw in ebook_keywords):
        return f"@{username} 감사합니다! 무료 전자책은 프로필 링크에서 바로 다운로드할 수 있어요 {SITE_URL}/ebook-library.html 18권 모두 무료입니다 :)"

    # 레벨 선택
    if any(kw in text_lower for kw in level_keywords):
        return f"@{username} 솔직하게 공유해주셔서 감사해요. 같은 레벨인 분들이 많답니다. 프로필에서 무료 전자책 받아가세요, 도움이 될 거예요!"

    # 투표 답변
    if len(text_lower) <= 3 and any(kw in text_lower for kw in vote_keywords):
        return f"@{username} 답변 감사합니다! 솔직한 공유가 서로에게 위로가 됩니다. 프로필에서 관련 무료 전자책도 확인해보세요 :)"

    # 손 들기
    if any(kw in text for kw in hand_keywords):
        return f"@{username} 손 들어주셔서 감사해요! 당신만 그런 게 아닙니다. 같이 이겨내요. 프로필에서 무료 전자책 받아가세요!"

    # 친구 태그
    if tag_pattern.search(text):
        return f"@{username} 소중한 친구를 태그해주셨군요! 그 친구에게도 무료 전자책을 선물해주세요: {SITE_URL}/ebook-library.html"

    # 공감/힘듦
    if any(kw in text_lower for kw in empathy_keywords):
        return f"@{username} 공감해주셔서 감사해요. 혼자가 아니에요. 프로필에서 무료 전자책 받아가시면 작은 도움이 될 거예요 :)"

    # 칭찬
    if any(kw in text_lower for kw in praise_keywords):
        return f"@{username} 따뜻한 말씀 감사합니다! 앞으로도 도움되는 콘텐츠 만들겠습니다. 무료 전자책도 확인해보세요 :)"

    # 기본 답변
    return f"@{username} 댓글 감사합니다! 프로필 링크에서 무료 전자책 18권을 다운로드할 수 있어요 :)"


def process_instagram_comments():
    """인스타 모든 게시물의 새 댓글 확인 + 자동 답변"""
    replied = load_replied()
    new_replies = 0

    # 최근 게시물 30개 확인
    r = requests.get(f'https://graph.facebook.com/v21.0/{IG_ID}/media?fields=id,comments_count&limit=30&access_token={IG_TOKEN}')
    posts = r.json().get('data', [])

    for post in posts:
        if post.get('comments_count', 0) == 0:
            continue

        # 댓글 가져오기
        r2 = requests.get(f'https://graph.facebook.com/v21.0/{post["id"]}/comments?fields=id,text,username,timestamp&limit=50&access_token={IG_TOKEN}')
        comments = r2.json().get('data', [])

        for comment in comments:
            cid = comment['id']
            if cid in replied:
                continue

            username = comment.get('username', 'user')
            text = comment.get('text', '')

            # 자기 댓글은 무시 (자문자답 방지)
            if username == 'lighthouse_media77':
                replied.append(cid)
                continue

            # 자동 답변 생성
            reply_text = get_auto_reply(text, username)

            # 답글 달기
            result = reply_comment(cid, reply_text)
            if 'id' in result:
                print(f"  @{username}: {text[:30]}...")
                print(f"    -> {reply_text[:50]}...")
                replied.append(cid)
                new_replies += 1
            else:
                print(f"  @{username}: FAIL - {result}")

            time.sleep(3)  # API 속도 제한 방지

    save_replied(replied)
    return new_replies


def process_facebook_comments():
    """페이스북 페이지 게시물 댓글 자동 답변"""
    replied = load_replied()
    new_replies = 0

    # 최근 게시물
    r = requests.get(f'https://graph.facebook.com/v21.0/{FB_PAGE}/posts?fields=id,message&limit=20&access_token={FB_TOKEN}')
    posts = r.json().get('data', [])

    for post in posts:
        # 댓글 가져오기
        r2 = requests.get(f'https://graph.facebook.com/v21.0/{post["id"]}/comments?fields=id,message,from&limit=50&access_token={FB_TOKEN}')
        comments = r2.json().get('data', [])

        for comment in comments:
            cid = comment['id']
            if cid in replied:
                continue

            name = comment.get('from', {}).get('name', 'friend')
            text = comment.get('message', '')

            # 자기 댓글은 무시 (자문자답 방지)
            if name in ('Lighthouse Media', 'lighthouse_media77'):
                replied.append(cid)
                continue

            # 자동 답변
            reply = f"{name}님 댓글 감사합니다! 무료 전자책 18권을 여기서 받아가세요: {SITE_URL}/ebook-library.html"

            # 전자책 키워드면 더 자세한 답변
            if any(kw in text for kw in ['전자책', '책', '다운', '받고', '링크', '무료', '부탁']):
                reply = f"{name}님! 무료 전자책은 이 링크에서 바로 다운로드 가능합니다: {SITE_URL}/ebook-library.html 번아웃 회복, 감정 관리, 습관 설계 등 18권 모두 무료입니다!"

            r3 = requests.post(f'https://graph.facebook.com/v21.0/{cid}/comments', data={
                'message': reply, 'access_token': FB_TOKEN
            })

            if 'id' in r3.json():
                print(f"  FB {name}: {text[:30]}...")
                print(f"    -> 답변 완료")
                replied.append(cid)
                new_replies += 1
            time.sleep(2)

    save_replied(replied)
    return new_replies


def main():
    print("=" * 50)
    print("  AUTO COMMENT REPLY")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    print("\n[1/2] Instagram comments...")
    ig_count = process_instagram_comments()
    print(f"  {ig_count} new replies")

    print("\n[2/2] Facebook comments...")
    fb_count = process_facebook_comments()
    print(f"  {fb_count} new replies")

    print(f"\n  Total: {ig_count + fb_count} replies sent")
    print("=" * 50)


if __name__ == "__main__":
    main()
