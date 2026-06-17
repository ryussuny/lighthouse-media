"""Instagram 글로벌 포스트 재시도 — API 제한 풀린 후 실행"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, time, base64, requests
from PIL import Image

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
tokens = json.load(open(os.path.join(REPO, "config", "tokens.json"), encoding='utf-8'))
LH_TOKEN = tokens['instagram']
LH_IG_ID = '17841425580883266'
IMGUR_ID = "546c25a59c58ad7"
OUTPUT = os.path.join(REPO, "output", "global-cards")

POSTS = [
    ("global_01_self-worth.jpg", "self-worth", "✦ You were never meant to earn your worth. It was given to you.\n\nWe spend years trying to prove we're enough — to parents, bosses, even ourselves. But what if worth isn't something you earn? What if it was placed inside you before you ever achieved a single thing?\n\n—\n\n당신의 가치는 증명하는 것이 아니라 이미 주어진 것입니다.\n\n우리는 충분하다는 것을 증명하려고 수년을 보냅니다. 하지만 당신의 가치가 성취 이전에 이미 존재하는 것이라면요?\n\n—\nLighthouse Media | @lighthouse_media77\nFollow for daily wisdom & healing\n\n#selfworth #youareenough #mentalhealth #healing #motivation #selflove #innerpeace #identity #worthit #lighthouse"),
    ("global_02_rest.jpg", "rest", "✦ Rest is not a reward for finishing. It's fuel for beginning.\n\nHustle culture taught us that rest is weakness. But the most creative minds in history knew: restoration isn't laziness — it's strategy. You can't pour from an empty cup.\n\n—\n\n쉼은 끝낸 자의 보상이 아니라 시작하는 자의 연료입니다.\n\n쉬는 것은 약함이 아닙니다. 빈 컵으로는 아무것도 줄 수 없습니다.\n\n—\nLighthouse Media | @lighthouse_media77\nFollow for daily wisdom & healing\n\n#rest #burnoutrecovery #selfcare #mentalhealth #productivity #wellness #balance #mindfulness #restoration #lighthouse"),
    ("global_03_courage.jpg", "courage", "✦ Courage is not the absence of fear. It's one more step while shaking.\n\nEvery brave person you admire was terrified before they acted. The difference? They moved anyway. Your next breakthrough is hiding behind the thing you're most afraid of.\n\n—\n\n용기란 두려움이 없는 것이 아니라 떨리는 중에도 한 발 더 내딛는 것입니다.\n\n당신이 존경하는 모든 용감한 사람도 행동 전에는 두려웠습니다. 차이는 하나, 그래도 움직였다는 것.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#courage #bravery #fear #growth #mindset #motivation #inspiration #strength #keepgoing #lighthouse"),
    ("global_04_forgiveness.jpg", "forgiveness", "✦ Forgiveness is not saying 'it was okay.' It's saying 'I won't carry this anymore.'\n\nHolding onto resentment is like drinking poison and waiting for the other person to get sick. Letting go isn't about them — it's about freeing yourself.\n\n—\n\n용서는 '괜찮았어'가 아니라 '더 이상 이것을 짊어지지 않겠어'라는 선언입니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#forgiveness #lettinggo #healing #peace #freedom #mentalhealth #growth #innerpeace #emotional #lighthouse"),
    ("global_05_loneliness.jpg", "loneliness", "✦ Feeling alone in a crowded room is a signal, not a sentence.\n\nLoneliness isn't about the number of people around you. It's about the depth of connection. One real conversation can heal what a thousand surface-level interactions cannot.\n\n—\n\n사람들 속에서 외로움을 느끼는 것은 판결이 아니라 신호입니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#loneliness #connection #belonging #mentalhealth #community #realfriends #vulnerability #human #together #lighthouse"),
    ("global_06_failure.jpg", "failure", "✦ Failure is not the opposite of success. It's part of the journey.\n\nEdison failed 10,000 times. J.K. Rowling was rejected 12 times. Every 'no' brought them closer to 'yes.' Your failure isn't a dead end — it's a detour leading somewhere better.\n\n—\n\n실패는 성공의 반대가 아니라 여정의 일부입니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#failure #success #resilience #growth #nevergiveup #motivation #entrepreneur #mindset #comeback #lighthouse"),
    ("global_07_gratitude.jpg", "gratitude", "✦ Gratitude doesn't change your situation. It changes your eyes.\n\nNeuroscience confirms: gratitude literally rewires your brain. Just 3 things you're thankful for each day can shift your entire perspective.\n\n—\n\n감사는 상황을 바꾸지 않습니다. 당신의 시선을 바꿉니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#gratitude #thankful #mindfulness #positivity #mentalhealth #perspective #growth #neuroscience #happiness #lighthouse"),
    ("global_08_boundaries.jpg", "boundaries", "✦ 'No' is a complete sentence. You don't owe anyone an explanation.\n\nSetting boundaries isn't selfish — it's self-respect. The people who get upset when you set limits are the ones who benefited the most from you having none.\n\n—\n\n'아니요'는 완전한 문장입니다. 누구에게도 설명할 의무가 없습니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#boundaries #selfrespect #mentalhealth #toxicrelationships #healing #growth #selfcare #no #healthyrelationships #lighthouse"),
    ("global_09_patience.jpg", "patience", "✦ A seed doesn't become a tree overnight. Your growth is happening even when you can't see it.\n\nIn a world of instant results, patience feels like punishment. But the deepest roots grow in the darkest soil. Trust the process.\n\n—\n\n씨앗이 하룻밤에 나무가 되지 않습니다. 보이지 않아도 당신은 자라고 있습니다.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#patience #growth #trust #process #motivation #mindset #seedtotree #invisible #faith #lighthouse"),
    ("global_10_comparison.jpg", "comparison", "✦ Stop comparing your chapter 1 to someone else's chapter 20.\n\nSocial media shows highlight reels, not behind-the-scenes. That person you envy? They cried in their car last Tuesday. Everyone is fighting battles you can't see. Run your own race.\n\n—\n\n당신의 1장을 누군가의 20장과 비교하지 마세요.\n\n—\nLighthouse Media | @lighthouse_media77\n\n#comparison #beyourself #socialmedia #authenticity #journey #growth #selflove #ownpath #unique #lighthouse"),
]

def upload_imgur(path):
    for attempt in range(3):
        try:
            with open(path, 'rb') as f:
                enc = base64.b64encode(f.read()).decode()
            r = requests.post('https://api.imgur.com/3/image',
                headers={'Authorization': f'Client-ID {IMGUR_ID}'},
                data={'image': enc, 'type': 'base64'}, timeout=30)
            url = r.json().get('data',{}).get('link')
            if url: return url
        except: pass
        time.sleep(5)
    return None

def post_ig(image_url, caption):
    try:
        r = requests.post(f'https://graph.facebook.com/v21.0/{LH_IG_ID}/media',
            data={'image_url': image_url, 'caption': caption, 'access_token': LH_TOKEN}, timeout=30)
        cid = r.json().get('id')
        if not cid:
            err = r.json().get('error', {})
            if 'limit' in str(err.get('message','')).lower():
                return 'RATE_LIMITED'
            print(f"  IG fail: {r.json()}")
            return None
        time.sleep(8)
        r2 = requests.post(f'https://graph.facebook.com/v21.0/{LH_IG_ID}/media_publish',
            data={'creation_id': cid, 'access_token': LH_TOKEN}, timeout=30)
        if 'id' in r2.json():
            return r2.json()['id']
        return None
    except Exception as e:
        print(f"  IG error: {e}")
        return None

def main():
    print("Retrying Instagram posts for Lighthouse Media global content...")
    success = 0
    for filename, theme, caption in POSTS:
        path = os.path.join(OUTPUT, filename)
        if not os.path.exists(path):
            print(f"  SKIP: {filename} not found"); continue

        print(f"  {theme}...", end=' ')
        url = upload_imgur(path)
        if not url:
            print("Imgur fail"); continue

        result = post_ig(url, caption)
        if result == 'RATE_LIMITED':
            print("RATE LIMITED — stopping. Try again later.")
            break
        elif result:
            print(f"OK ({result})")
            success += 1
        else:
            print("FAIL")
        time.sleep(10)

    print(f"\nDone: {success}/10 posted to Instagram.")

if __name__ == '__main__':
    main()
