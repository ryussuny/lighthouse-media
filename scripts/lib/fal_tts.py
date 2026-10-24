"""fal.ai 한국어 TTS 나레이션 + 비용가드 (cost-preview-confirm 규약 — fal_visuals.py와 같은 패턴)

daily-video.py(품질 모드)가 호출하는 헬퍼:
  - FAL_KEY 는 fal_visuals.load_fal_key() 재사용(.env 런타임 로드, 없으면 deny-by-default)
  - 문장(청크)별로 나눠 합성하고 각 청크의 실제 길이(duration_ms, ffprobe 교차확인)를 돌려준다
    → 호출부가 청크 길이로 자막·장면 타이밍을 맞춘다(문자 정렬 API 없이도 정확한 구간 시각)
  - 호출 전 예상비용을 표시하고 편당 한도를 넘으면 호출하지 않는다 — 예외 대신 (None, 사유) 반환

가격은 fal.ai get_pricing 실측값(출처·일자는 주석). 값이 바뀌면 TTS_PRICE_PER_1000_CHARS만 고친다.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fal_visuals as fv  # noqa: E402  (load_fal_key, _post, log_run_cost 재사용)
from ko_numbers import speakable  # noqa: E402  ('3가지'→'세 가지' — 2026-10-24 오너 지시)

# ═══════════════════════════════════════════════════════════════
# 모델·가격 (출처: fal.ai get_pricing MCP 실측 조회, 2026-10-15 — worker-3)
#   fal-ai/minimax/speech-2.8-hd     $0.10 / 1000 characters  ← 채택(한국어 language_boost 지원, 말투 지시·속도 조절)
#   fal-ai/minimax/speech-2.8-turbo  $0.06 / 1000 characters
#   elevenlabs/tts/eleven-v4         $0.08 / 1000 characters
#   fal-ai/elevenlabs/tts/turbo-v2.5 $0.05 / 1000 characters
#   google/gemini-3.8-flash-tts      $0.045 / 1000 characters
#   google/gemini-3.8-flash-lite-tts $0.03 / 1000 characters
#   fal-ai/bytedance/seed-speech/tts/v2 $0.03 / 1000 characters
# 어느 모델이든 한국어 나레이션 400자 안팎(45초)은 $0.012~$0.04 — 편당 한도 $0.20에 비해 작다.
# ═══════════════════════════════════════════════════════════════
TTS_MODEL = "fal-ai/minimax/speech-2.8-hd"
TTS_PRICE_PER_1000_CHARS = 0.10  # 출처: get_pricing("fal-ai/minimax/speech-2.8-hd"), 2026-10-15
TTS_PRICING_SOURCE = "fal.ai get_pricing MCP (실측, 2026-10-15) — fal-ai/minimax/speech-2.8-hd $0.10/1000자"

# 목소리: 차분하고 따뜻한 중년 — 확정은 오너가 샘플을 듣고 정한다(aud 폴더). 기본값은 샘플 비교 결과(RESULT.md)로 정한다.
DEFAULT_VOICE = "Calm_Woman"
DEFAULT_SPEED = 1.15  # 1.0 = 모델 기본(음성 시험: Calm_Woman 1.0 → 4.5 음절/초). 벤치마크 쇼츠 중앙 ≈6 음절/초 쪽으로 올림 — 실측은 RESULT.md


def estimate_tts_cost(n_chars):
    return round(n_chars / 1000.0 * TTS_PRICE_PER_1000_CHARS, 5)


def synth_chunk(text, out_path, voice=None, speed=None, key=None, emotion=None):
    """한 청크를 합성해 mp3로 저장. 성공: ({'path','duration_ms','chars','est_usd'}, None). 실패: (None, 사유)."""
    key = key or fv.load_fal_key()
    if not key:
        return None, "FAL_KEY 없음 — deny-by-default"
    vs = {"voice_id": voice or DEFAULT_VOICE, "speed": speed if speed is not None else DEFAULT_SPEED, "vol": 1, "pitch": 0}
    if emotion:
        vs["emotion"] = emotion
    body = {
        "prompt": speakable(text),   # 자막은 원문 그대로, 읽기만 사람처럼
        "voice_setting": vs,
        "language_boost": "Korean",
        "output_format": "url",
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
    }
    try:
        res = fv._post(f"https://fal.run/{TTS_MODEL}", key, body)
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode()[:300]
        except Exception:
            msg = ""
        return None, f"HTTP {e.code}: {msg}"
    except Exception as e:
        return None, f"예외: {e}"
    audio = res.get("audio") or {}
    url = audio.get("url") if isinstance(audio, dict) else None
    if not url:
        return None, f"오디오 URL 없음. 응답: {json.dumps(res)[:300]}"
    try:
        urllib.request.urlretrieve(url, out_path)
    except Exception as e:
        return None, f"다운로드 실패: {e}"
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None, "다운로드된 파일이 비어있음"
    return {"path": out_path, "duration_ms": res.get("duration_ms"), "chars": len(text), "est_usd": estimate_tts_cost(len(text))}, None


def synth_chunks(chunks, out_dir, name, per_video_budget_usd, spent_usd=0.0, voice=None, speed=None):
    """chunks: 문장 문자열 목록. 호출 전 총 비용을 표시·게이트한다. 하나라도 실패하면 (None, 사유) — 부분 나레이션 금지.
    성공: (list of chunk dict, None)."""
    os.makedirs(out_dir, exist_ok=True)
    total_chars = sum(len(c) for c in chunks)
    est = estimate_tts_cost(total_chars)
    print(f"  [비용미리보기] TTS · {len(chunks)}청크 {total_chars}자 · {TTS_MODEL} · 예상 ${est:.4f} · 출처: {TTS_PRICING_SOURCE}")
    if spent_usd + est > per_video_budget_usd:
        reason = f"편당 예산 ${per_video_budget_usd:.2f} 초과(이미 ${spent_usd:.4f} + TTS ${est:.4f}) — 호출 생략, master 보고 대상"
        print(f"  [비용게이트] {reason}")
        return None, reason
    out = []
    for i, text in enumerate(chunks):
        p = os.path.join(out_dir, f"tts_{i:02d}.mp3")
        r, err = synth_chunk(text, p, voice=voice, speed=speed)
        if not r:
            return None, f"청크 {i} 합성 실패: {err}"
        out.append(r)
    fv.log_run_cost("tts_batch", TTS_MODEL, total_chars, est, reel_name=name)
    return out, None
