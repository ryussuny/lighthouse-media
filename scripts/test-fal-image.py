#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fal.ai 이미지 생성 테스트 (자비스 성장 — 이미지/영상 연료 점검)
사용법:
  1) lighthouse-media/.env 의 FAL_KEY= 뒤에 fal.ai 키를 붙여넣는다 (https://fal.ai → Keys)
  2) py lighthouse-media/scripts/test-fal-image.py            # 기본 테스트 이미지 1장
     py lighthouse-media/scripts/test-fal-image.py "프롬프트"  # 원하는 이미지
결과: lighthouse-media/output/fal-test-*.png 저장
"""
import sys, os, json, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8")

HOME = os.path.expanduser("~")
ENV = os.path.join(HOME, "lighthouse-media", ".env")
OUT = os.path.join(HOME, "lighthouse-media", "output")
MODEL = "fal-ai/nano-banana-pro"   # 고품질 이미지. 영상은 fal-ai/kling-video 등 경로만 교체

def load_key():
    if not os.path.exists(ENV):
        sys.exit("❌ .env 없음: " + ENV)
    for line in open(ENV, encoding="utf-8"):
        if line.strip().startswith("FAL_KEY="):
            k = line.split("=", 1)[1].strip()
            if not k:
                sys.exit("❌ FAL_KEY가 비어있음. https://fal.ai 에서 키 발급 후 .env의 FAL_KEY= 뒤에 붙여넣으세요.")
            return k
    sys.exit("❌ .env에 FAL_KEY 항목 없음.")

def post(url, key, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())

def main():
    key = load_key()
    prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "A serene worship scene: soft dawn light through clouds over calm water, "
        "peaceful, cinematic, hopeful, warm golden tones, high detail")
    os.makedirs(OUT, exist_ok=True)
    print(f"🎨 모델: {MODEL}\n📝 프롬프트: {prompt}\n생성 중...")
    try:
        res = post(f"https://fal.run/{MODEL}", key,
                   {"prompt": prompt, "aspect_ratio": "1:1", "resolution": "2K", "num_images": 1})
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ fal.ai 오류 {e.code}: {e.read().decode()[:300]}\n(키가 유효한지, 잔액이 있는지 확인)")
    imgs = res.get("images") or res.get("output", {}).get("images") or []
    if not imgs:
        sys.exit("❌ 이미지 URL 없음. 응답: " + json.dumps(res)[:400])
    url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    path = os.path.join(OUT, f"fal-test-{int(time.time())}.png")
    urllib.request.urlretrieve(url, path)
    print(f"✅ 성공! 저장됨: {path}\n   → fal.ai 이미지 생성이 정상 작동합니다. 이제 media-gen 스킬 전부 사용 가능.")

if __name__ == "__main__":
    main()
