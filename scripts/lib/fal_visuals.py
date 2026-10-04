"""fal.ai 릴스 비주얼 생성 + 비용가드 (cost-preview-confirm 규약)

daily-ig-reels.py 가 호출하는 얇은 헬퍼 모듈:
  - FAL_KEY 런타임 로드 (suite-runtime-keys 규약 — 없으면 deny-by-default, 예외 아님)
  - 장면별 배경 이미지 생성 (fal-ai 이미지 모델, 기존 scripts/test-fal-image.py와 동일한
    urllib + "Authorization: Key {FAL_KEY}" 호출 패턴 재사용 — 신규 SDK 의존 추가 안 함)
  - 호출 전 예상비용 계산·표시·누적기록 (cost-preview-confirm §1~4)
  - 실패/예산초과 시 예외를 던지지 않고 (None, reason) 을 반환 — 호출부가 절차적 폴백을 결정

가격 상수는 fal.ai get_pricing 실측값이며 출처·일자를 주석에 남긴다(할루시네이션 방지 — 값이
바뀌면 이 상수만 갱신하면 된다).
"""
import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
REPO_DIR = os.path.join(HOME, "lighthouse-media")
ENV_PATH = os.path.join(REPO_DIR, ".env")
OUT_DIR = os.path.join(REPO_DIR, "output", "reels")
RUN_COST_PATH = os.path.join(OUT_DIR, "run-cost.json")
MANIFEST_PATH = os.path.join(OUT_DIR, "media-manifest.jsonl")

# ═══════════════════════════════════════════════════════════════
# 모델·가격 (출처: fal.ai get_pricing MCP 실측 조회, 2026-09-29 — worker-2)
# ═══════════════════════════════════════════════════════════════
# 실측 비교(2026-09-29 get_pricing 결과, 참고용 — 값이 바뀌면 이 주석과 아래 상수를 함께 갱신):
#   fal-ai/nano-banana-pro          $0.15 / image   (장당 정액) → 7~9장이면 $1.05~$1.35, 편당 예산
#                                                       $0.30 초과 확정 — 채택 불가
#   fal-ai/flux/dev                 $0.025 / megapixel → 1080x1920(1.9944MP)=$0.0499/장, 9장=$0.449 → 초과
#   bytedance/seedream/v5/lite      $0.035 / image (정액) → 9장=$0.315 → 예산선상(마진 거의 없음)
#   fal-ai/flux/schnell             $0.003 / megapixel → 1080x1920=$0.00598/장, 9장=$0.0538 → 채택
#     (배경용도: 전신 텍스트박스+Ken Burns 크롭+25% 어둡게 합성이 뒤따르므로 schnell의 상대적으로
#      낮은 디테일이 실사용 화면에서 크게 두드러지지 않음 — 마진이 커서 필요시 dev로 업그레이드 여지도 있음)
IMAGE_MODEL = "fal-ai/flux/schnell"
IMAGE_MODEL_WIDTH = 1080
IMAGE_MODEL_HEIGHT = 1920
_IMAGE_MODEL_PRICE_PER_MEGAPIXEL = 0.003  # 출처: get_pricing("fal-ai/flux/schnell"), 2026-09-29
IMAGE_MODEL_COST_USD = round((IMAGE_MODEL_WIDTH * IMAGE_MODEL_HEIGHT / 1_000_000) * _IMAGE_MODEL_PRICE_PER_MEGAPIXEL, 5)

PRICING_SOURCE = "fal.ai get_pricing MCP (실측, 2026-09-29) — $0.003/megapixel, 1080x1920=1.9944MP"

PER_REEL_BUDGET_USD = 0.30


def load_fal_key():
    """FAL_KEY를 .env에서 런타임 로드. 없으면 None (deny-by-default — 예외 아님)."""
    if not os.path.exists(ENV_PATH):
        return None
    for line in open(ENV_PATH, encoding="utf-8"):
        if line.strip().startswith("FAL_KEY="):
            k = line.split("=", 1)[1].strip()
            return k or None
    return None


def _post(url, key, body, timeout=180):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": "Key " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ═══════════════════════════════════════════════════════════════
# 비용 미리보기·확인·누적 (cost-preview-confirm §1~4)
# ═══════════════════════════════════════════════════════════════
def estimate_reel_cost(n_images, cost_per_image=None):
    """편당 예상비용 계산. cost_per_image 미확정이면 (None, 사유) 반환 — 안전측 폴백 유도."""
    cpi = cost_per_image if cost_per_image is not None else IMAGE_MODEL_COST_USD
    if cpi is None:
        return None, "IMAGE_MODEL_COST_USD 미확정(가격 미조회) — AI비주얼 생략"
    total = round(n_images * cpi, 4)
    return total, None


def preview_and_gate(n_images, reel_name, cost_per_image=None):
    """[작업 · 수량 · 모델 · 예상 $X · 누적 세션 $Y] 한 줄 표시 + 예산 게이트.
    반환: (진행가능 bool, 예상비용 or None, 사유)"""
    total, reason = estimate_reel_cost(n_images, cost_per_image)
    if total is None:
        print(f"  [비용미리보기] 산출 불가 — {reason}")
        return False, None, reason

    session_total = _session_cumulative_usd() + total
    print(
        f"  [비용미리보기] 이미지생성 · {n_images}장 · {IMAGE_MODEL} · "
        f"예상 ${total:.4f} · 세션누적(예정) ${session_total:.4f} · 출처: {PRICING_SOURCE}"
    )

    if total > PER_REEL_BUDGET_USD:
        reason = f"편당 예산 ${PER_REEL_BUDGET_USD:.2f} 초과(예상 ${total:.4f}) — 호출 생략, master 보고 대상"
        print(f"  [비용게이트] {reason}")
        return False, total, reason

    return True, total, None


def _session_cumulative_usd():
    try:
        rows = json.load(open(RUN_COST_PATH, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    return round(sum(r.get("est_usd", 0.0) for r in rows), 4)


def log_run_cost(step, model, qty, est_usd, actual_usd=None, reel_name=""):
    """run-cost.json에 append (cost-preview-confirm §4 누적 추적)."""
    try:
        rows = json.load(open(RUN_COST_PATH, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        rows = []
    rows.append({
        "step": step,
        "model": model,
        "qty": qty,
        "est_usd": est_usd,
        "actual_usd": actual_usd,
        "reel_name": reel_name,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(rows, open(RUN_COST_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def _append_manifest(record):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════════════════════
# 장면 프롬프트 (카테고리 × 스타일 → 사진풍 배경 프롬프트, 브랜드 원칙: 보편적·비종교적·인물 클로즈업 금지)
# ═══════════════════════════════════════════════════════════════
# 2026-10-05 오너 피드백 "배경이 전체적으로 어둡다" → night/rain의 dark·moody 표현 제거, 밝은 자연광 지시 추가
STYLE_MOOD = {
    "dawn": "bright soft dawn light breaking through clouds, gentle warm blue-gold sky, calm horizon, airy and luminous",
    "night": "blue hour twilight just after sunset, glowing lavender and soft blue sky, first stars, luminous and peaceful",
    "golden": "warm golden hour sunlight, soft amber glow, bright warm tones, gentle lens flare",
    "rain": "light rain just ending, sunlight breaking through, soft silver-blue tones, fresh and bright, glistening wet surfaces",
}

CATEGORY_SUBJECT = {
    "comfort": "a cozy quiet indoor scene by a window, soft blanket or armchair, empty peaceful space suggesting rest, no people",
    "motivation": "a wide open path or mountain trail at sunrise, sense of a new beginning and forward movement, no people",
    "growth": "a small plant or seedling in soft light, or an open notebook and coffee cup on a wooden desk, quiet productive morning, no people",
    "healing": "calm nature scene, still water or misty forest, soft light filtering through trees, deep sense of peace, no people",
}


def build_scene_prompt(category, style):
    cat = CATEGORY_SUBJECT.get(category, CATEGORY_SUBJECT["comfort"])
    mood = STYLE_MOOD.get(style, STYLE_MOOD["dawn"])
    return (
        f"{cat}, {mood}, vertical portrait composition, bright natural light, well exposed, "
        f"light and airy photography, shallow depth of field, high detail, "
        f"no text, no logos, no watermark, no visible human faces"
    )


# ═══════════════════════════════════════════════════════════════
# 이미지 생성 (fal.ai 동기 호출 — scripts/test-fal-image.py와 동일 urllib 패턴)
# ═══════════════════════════════════════════════════════════════
def generate_scene_image(prompt, out_path, key=None):
    """성공: (out_path, None). 실패: (None, 사유문자열) — 예외를 던지지 않는다(호출부 폴백 유도)."""
    key = key or load_fal_key()
    if not key:
        return None, "FAL_KEY 없음 — deny-by-default"

    try:
        res = _post(
            f"https://fal.run/{IMAGE_MODEL}",
            key,
            {
                "prompt": prompt,
                "image_size": {"width": IMAGE_MODEL_WIDTH, "height": IMAGE_MODEL_HEIGHT},
                "num_images": 1,
                "output_format": "png",
            },
        )
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()[:300]
        except Exception:
            body = ""
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, f"예외: {e}"

    imgs = res.get("images") or res.get("output", {}).get("images") or []
    if not imgs:
        return None, f"이미지 URL 없음. 응답: {json.dumps(res)[:300]}"

    url = imgs[0]["url"] if isinstance(imgs[0], dict) else imgs[0]
    try:
        urllib.request.urlretrieve(url, out_path)
    except Exception as e:
        return None, f"다운로드 실패: {e}"

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None, "다운로드된 파일이 비어있음"

    return out_path, None


def generate_all_scene_images(scenes, category, images_dir, reel_name):
    """전 장면 이미지를 생성한다. 하나라도 실패하면 즉시 (None, 사유) 반환 — 부분 AI 화면 섞임 방지
    (한 영상 안에서 AI사진/그라디언트가 섞이면 시각 일관성이 깨지므로 전부-아니면-전무 정책)."""
    os.makedirs(images_dir, exist_ok=True)
    key = load_fal_key()
    if not key:
        return None, "FAL_KEY 없음 — deny-by-default"

    n = len(scenes)
    ok, est_total, reason = preview_and_gate(n, reel_name)
    if not ok:
        return None, reason

    paths = []
    for i, sc in enumerate(scenes):
        style = sc.get("style", "dawn")
        prompt = build_scene_prompt(category, style)
        out_path = os.path.join(images_dir, f"scene_{i:02d}.png")
        path, err = generate_scene_image(prompt, out_path, key=key)
        if not path:
            return None, f"장면 {i} 생성 실패: {err}"
        paths.append(path)
        actual = None  # fal.run 동기 응답엔 실과금 필드가 기본 노출 안 됨 — 추산치로 기록(사후실측 TODO)
        _append_manifest({
            "reel_name": reel_name, "scene_index": i, "model": IMAGE_MODEL,
            "prompt": prompt, "width": IMAGE_MODEL_WIDTH, "height": IMAGE_MODEL_HEIGHT,
            "path": path, "est_usd": IMAGE_MODEL_COST_USD, "actual_usd": actual,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    log_run_cost("image_batch", IMAGE_MODEL, n, est_total, reel_name=reel_name)
    return paths, None
