"""트렌디한 릴스 배경음악 라이브러리 생성 (fal.ai Lyria 2 · 상업 이용 가능 · 곡당 30초 · $0.10)
- 결과: assets/bgm/trend-<카테고리>-<번호>.mp3 (보컬 없음)
- 이미 있는 파일은 건너뜀(재실행해도 중복 과금 없음)
- Usage: py scripts/gen-trend-bgm.py
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, json, subprocess, requests, concurrent.futures as cf

HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "lighthouse-media")
BGM_DIR = os.path.join(REPO, "assets", "bgm")
FFMPEG = os.path.join(HOME, "AppData", "Local", "Microsoft", "WinGet", "Links", "ffmpeg.exe")
if not os.path.exists(FFMPEG): FFMPEG = "ffmpeg"
KEY = next(l.split("=", 1)[1].strip() for l in open(os.path.join(REPO, ".env"), encoding="utf-8") if l.startswith("FAL_KEY="))
NEG = "vocals, singing, voice, lyrics, low quality, distorted, harsh, aggressive, heavy metal, EDM drop"

TRACKS = {
    "comfort-1": "lo-fi chill hop, warm Rhodes electric piano, soft vinyl crackle, mellow boom-bap drums at 80 bpm, cozy late-night instrumental, emotional and comforting",
    "comfort-2": "warm acoustic guitar fingerpicking with soft piano, gentle shaker, indie folk instrumental, intimate and heartfelt, 85 bpm",
    "comfort-3": "emotional modern piano with soft ambient pads and subtle chill beat, cinematic lo-fi, tender and hopeful, 75 bpm",
    "motivation-1": "uplifting indie pop instrumental, bright electric guitar riff, hand claps, punchy drums, sunny and energetic, 110 bpm",
    "motivation-2": "inspiring cinematic pop, building piano ostinato, airy synths, steady four-on-the-floor kick, hopeful and driving, 118 bpm",
    "motivation-3": "light future bass instrumental, soft chopped synth chords, crisp snaps, optimistic and modern, no drop, 100 bpm",
    "growth-1": "chill house morning groove, soft plucked synths, warm bass, gentle percussion, fresh and productive, 115 bpm",
    "growth-2": "acoustic pop instrumental, ukulele and light piano, finger snaps, cheerful morning coffee vibe, 105 bpm",
    "growth-3": "minimal lo-fi study beat, mellow jazz guitar chords, dusty drums, focused and calm, 85 bpm",
    "healing-1": "ambient piano with gentle rain texture and soft strings, slow and peaceful, meditative instrumental, 60 bpm",
    "healing-2": "dreamy synth pads, soft felt piano, distant chimes, floating ambient, healing and serene",
    "healing-3": "slow lo-fi with soft guitar, ocean-wave texture, warm bass, relaxed sunset instrumental, 70 bpm",
}


def make(name, prompt):
    out = os.path.join(BGM_DIR, f"trend-{name}.mp3")
    if os.path.exists(out):
        return name, "이미 있음"
    r = requests.post("https://fal.run/fal-ai/lyria2", headers={"Authorization": f"Key {KEY}"},
                      json={"prompt": prompt, "negative_prompt": NEG}, timeout=300)
    if not r.ok:
        return name, f"실패 HTTP {r.status_code}: {r.text[:120]}"
    url = r.json()["audio"]["url"]
    wav = out.replace(".mp3", ".wav")
    with open(wav, "wb") as f:
        f.write(requests.get(url, timeout=120).content)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav, "-b:a", "192k", out], timeout=120)
    os.remove(wav)
    return name, "OK" if os.path.exists(out) else "변환 실패"


if __name__ == "__main__":
    os.makedirs(BGM_DIR, exist_ok=True)
    todo = {k: v for k, v in TRACKS.items() if not os.path.exists(os.path.join(BGM_DIR, f"trend-{k}.mp3"))}
    print(f"[비용미리보기] Lyria 2 · {len(todo)}곡 · 곡당 $0.10 · 예상 ${0.10 * len(todo):.2f}")
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        for name, res in ex.map(lambda kv: make(*kv), todo.items()):
            print(f"  {name}: {res}")
