"""쇼츠 렌더러 — AI 배경(Ken Burns) + 위쪽 제목 + 나레이션에 맞춘 자막 박스 (daily-video.py 품질 모드용)

daily-ig-reels.py 의 렌더 방식(느린 줌·반투명 박스+흰 글씨 자막·알파 페이드·장면 크로스페이드)을 같은 사양으로 옮긴 모듈이다.
릴스 스크립트는 파일 이름에 하이픈이 있고 import 시 토큰을 읽는 부작용이 있어 직접 import 할 수 없고(스케줄러가 매일 돌리는
파일이라 수정도 하지 않는다), 필요한 부분(자막 박스·Ken Burns)만 이 모듈에 다시 구현했다.

입력은 타임라인(초 단위)이고, 타임라인은 호출부가 TTS 청크의 실제 길이로 만든다 → 자막은 해당 음성 구간에 켜지고 꺼진다.
프레임은 PIL로 그려 ffmpeg 표준입력(rawvideo)으로 보내므로 디스크에 프레임 파일을 남기지 않는다.
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 24
KB_ZOOM_END = 1.15      # 장면 재생 중 1.0 -> 1.15 (reels 와 같은 값)
XFADE_SEC = 0.40        # 장면 사이 크로스페이드
DARKEN = 0.92           # 배경을 아주 조금만 어둡게 — 글자는 반투명 박스가 받쳐 준다(오너 10/05 "배경이 어둡다" 피드백 반영, reels 는 25% 어둡게)
SAFE_TOP, SAFE_BOTTOM = 200, 280   # 유튜브 쇼츠 UI가 가리는 위·아래 여백(루브릭 T2)
SUB_FONT_PX = 64
SUB_MAX_CHARS = 16
TITLE_FONT_PX = 66
YELLOW = (255, 222, 64)
WHITE = (255, 255, 255)


def font(size, bold=True):
    p = "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def wrap_chars(text, max_chars=SUB_MAX_CHARS):
    """공백 기준 그리디 줄바꿈(한 줄 max_chars자 이하). 공백 없는 긴 낱말은 글자 수로 자른다."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        while len(w) > max_chars:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:max_chars])
            w = w[max_chars:]
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def split_sentence(text, max_lines=2, max_chars=SUB_MAX_CHARS):
    """한 문장을 '자막 카드' 여러 장으로 나눈다(카드당 max_lines줄 이하). 반환: [(카드 텍스트(줄바꿈 포함), 글자수)].
    줄이 max_lines를 넘으면 단어를 글자 수가 비슷하게 카드 수만큼 나눠 각 카드를 다시 줄바꿈한다 — 한두 글자짜리 꼬리 카드가 생기지 않게."""
    lines = wrap_chars(text, max_chars)
    if len(lines) <= max_lines:
        return [("\n".join(lines), sum(len(x) for x in lines))]
    n_cards = -(-len(lines) // max_lines)
    words = text.split()
    total = sum(len(w) for w in words) or 1
    groups, cur, acc = [], [], 0
    for w in words:
        cur.append(w)
        acc += len(w)
        if len(groups) < n_cards - 1 and acc >= total * (len(groups) + 1) / n_cards:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    cards = []
    for g in groups:
        ls = wrap_chars(" ".join(g), max_chars)
        cards.append(("\n".join(ls), sum(len(x) for x in ls)))
    return cards


def boxed_layer(text, fnt, rgb, y, box_alpha=150, pad_x=38, pad_y=20, radius=26, spacing=12, align_center=True):
    """반투명 박스+그림자 위에 rgb 글씨를 얹은 RGBA 조각과 (x, y) 위치를 반환한다."""
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    lines = text.split("\n")
    sizes = [probe.textbbox((0, 0), ln, font=fnt) for ln in lines]
    ws = [b[2] - b[0] for b in sizes]
    hs = [fnt.size + 6 for _ in lines]
    block_w, block_h = max(ws), sum(hs) + spacing * (len(lines) - 1)
    w, h = block_w + 2 * pad_x, block_h + 2 * pad_y
    layer = Image.new("RGBA", (w, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 6, w, h + 6], radius=radius, fill=(0, 0, 0, box_alpha // 2))   # 그림자
    d.rounded_rectangle([0, 0, w, h], radius=radius, fill=(0, 0, 0, box_alpha))
    ty = pad_y
    for ln, wd, hh, bb in zip(lines, ws, hs, sizes):
        d.text(((w - wd) / 2 - bb[0] if align_center else pad_x, ty - bb[1] + 3), ln, font=fnt, fill=rgb + (255,))
        ty += hh + spacing
    return layer, (int((W - w) / 2), int(y))


def _cover(path):
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    scale = max(W / sw, H / sh) * 1.0
    src = src.resize((max(W, int(sw * scale)), max(H, int(sh * scale))), Image.LANCZOS)
    # 배경을 약간 어둡게 — 글자 가독성(자막 박스가 따로 있어 과하게 어둡히지 않는다)
    return Image.eval(src, lambda v: int(v * DARKEN))


class KenBurns:
    """이미지 한 장의 느린 줌. direction: 'in'(1.0->1.15) | 'out'(1.15->1.0), pan: -1/0/1 (좌/가운데/우로 미세 이동)."""

    def __init__(self, path, direction="in", pan=0):
        self.src = _cover(path)
        self.direction, self.pan = direction, pan

    def frame(self, fp):
        fp = max(0.0, min(1.0, fp))
        z = 1.0 + (KB_ZOOM_END - 1.0) * (fp if self.direction == "in" else 1.0 - fp)
        sw, sh = self.src.size
        cw, ch = W / z, H / z
        cx = sw / 2 + self.pan * (sw - cw) * 0.25 * (fp - 0.5)
        cy = sh / 2
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        return self.src.crop(tuple(int(round(v)) for v in box)).resize((W, H), Image.BICUBIC)


def build_layers(title_lines, subs):
    """title_lines: 위쪽 제목 줄들(2줄 이하). subs: [{'start','end','text'}]. 반환: (title_layer, [(start,end,layer,pos)])."""
    t_layer = boxed_layer("\n".join(title_lines), font(TITLE_FONT_PX), YELLOW, SAFE_TOP + 40, box_alpha=165)
    sub_layers = []
    for s in subs:
        layer, (x, _) = boxed_layer(s["text"], font(SUB_FONT_PX), WHITE, 0, box_alpha=150)
        y = int(H * 0.58)  # 박스 윗변 기준 — 1줄·2줄 모두 같은 높이에서 시작(눈이 같은 자리를 본다)
        sub_layers.append((s["start"], s["end"], layer, (x, y)))
    return t_layer, sub_layers


def render_video(scenes, title_lines, subs, total_sec, silent_path, ffmpeg="ffmpeg", progress=True):
    """scenes: [{'image','start','end'}] (연속, 마지막 end >= total_sec). subs: [{'start','end','text'}].
    무음 H.264 mp4(silent_path)를 만든다. 오디오는 호출부가 입힌다."""
    kbs = []
    for i, sc in enumerate(scenes):
        kbs.append(KenBurns(sc["image"], direction="in" if i % 2 == 0 else "out", pan=(-1, 1, 0)[i % 3]))
    t_layer, sub_layers = build_layers(title_lines, subs)
    n_frames = int(round(total_sec * FPS))
    cmd = [ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-movflags", "+faststart", silent_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for fi in range(n_frames):
            t = fi / FPS
            idx = next((i for i, sc in enumerate(scenes) if sc["start"] <= t < sc["end"]), len(scenes) - 1)
            sc = scenes[idx]
            fp = (t - sc["start"]) / max(sc["end"] - sc["start"], 0.001)
            img = kbs[idx].frame(fp)
            # 장면 끝 XFADE_SEC 동안 다음 장면과 크로스페이드
            if idx + 1 < len(scenes) and t > sc["end"] - XFADE_SEC:
                a = (t - (sc["end"] - XFADE_SEC)) / XFADE_SEC
                nxt = kbs[idx + 1].frame(0.0)
                img = Image.blend(img, nxt, max(0.0, min(1.0, a)))
            base = img.convert("RGBA")
            base.alpha_composite(t_layer[0], t_layer[1])
            for s0, s1, layer, pos in sub_layers:
                if s0 <= t < s1:
                    base.alpha_composite(layer, pos)
                    break
            p.stdin.write(base.convert("RGB").tobytes())
            if progress and fi % (FPS * 5) == 0:
                print(f"    frame {fi}/{n_frames}")
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", "ignore")
        rc = p.wait()
    except Exception:
        p.kill()
        raise
    if rc != 0 or not os.path.exists(silent_path):
        raise RuntimeError("ffmpeg 인코딩 실패: " + err[-400:])
    return silent_path
