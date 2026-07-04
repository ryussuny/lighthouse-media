# -*- coding: utf-8 -*-
r"""애니메이션 장면 엔진 — 심리스 루프 배경 영상 생성 (1920x1080 24fps)
정지 커버 → 살아있는 화면: 빛망울 부유, 별 반짝임, 김/불꽃, 빛줄기 호흡, 배경 줌 호흡
모든 움직임은 주기가 루프 길이의 정수배 → 이음새 없는 무한 반복
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 24
LOOP_SEC = 24
FRAMES = FPS * LOOP_SEC
TAU = 2 * math.pi

F_KR = "C:/Windows/Fonts/malgunbd.ttf"
F_EN = "C:/Windows/Fonts/georgiab.ttf"
F_EN_I = "C:/Windows/Fonts/georgiai.ttf"
F_SUB = "C:/Windows/Fonts/georgia.ttf"

# ───────────────────── 배경 ─────────────────────
def gradient(stops, w=W, h=H):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n = len(stops) - 1
    ys = np.linspace(0, n, h)
    for i in range(n):
        mask = (ys >= i) & (ys <= i + 1)
        t = (ys[mask] - i)[:, None, None]          # (rows,1,1)
        c0, c1 = np.array(stops[i], float), np.array(stops[i + 1], float)
        rows = (c0 + (c1 - c0) * t)                 # (rows,1,3)
        arr[mask] = np.repeat(rows, w, axis=1).astype(np.uint8)
    return Image.fromarray(arr)

def vignette(img, strength=100):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([-img.width*0.25, -img.height*0.35, img.width*1.25, img.height*1.35], fill=strength)
    mask = mask.filter(ImageFilter.GaussianBlur(160))
    inv = mask.point(lambda p: strength - p)
    img.paste(Image.new("RGB", img.size, (5, 4, 8)), (0, 0), inv)
    return img

# ───────────────────── 애니메이션 요소 ─────────────────────
class Element:
    def draw(self, layer, t): ...

def _sprite_circle(r, color, soft=2.2):
    """부드러운 원 스프라이트"""
    s = Image.new("RGBA", (r*4, r*4), (0,0,0,0))
    d = ImageDraw.Draw(s)
    d.ellipse([r, r, r*3, r*3], fill=color + (255,))
    return s.filter(ImageFilter.GaussianBlur(r/soft))

class Bokeh(Element):
    """떠다니는 빛망울 — 위로 느리게 부유 + 알파 맥동"""
    def __init__(self, rng, n=18, colors=((255,235,200),), rmin=12, rmax=64, amax=60):
        self.p = []
        for _ in range(n):
            r = rng.randint(rmin, rmax)
            self.p.append(dict(
                x=rng.uniform(0, W), y=rng.uniform(0, H),
                wraps=rng.choice([1, 1, 2]), swayA=rng.uniform(10, 50), swayN=rng.choice([1, 2]),
                phase=rng.uniform(0, 1), pulseN=rng.choice([1, 2, 3]), amax=rng.randint(amax//2, amax),
                sprite=_sprite_circle(r, rng.choice(list(colors)))))
    def draw(self, layer, t):
        span = H + 300
        for q in self.p:
            y = (q["y"] - q["wraps"] * span * t) % span - 150
            x = q["x"] + q["swayA"] * math.sin(TAU * (q["swayN"] * t + q["phase"]))
            a = q["amax"] * (0.55 + 0.45 * math.sin(TAU * (q["pulseN"] * t + q["phase"])))
            sp = q["sprite"]
            tinted = sp.copy()
            tinted.putalpha(tinted.getchannel("A").point(lambda p, a=a: int(p * a / 255)))
            layer.alpha_composite(tinted, (int(x)-sp.width//2, int(y)-sp.height//2))

class Stars(Element):
    """반짝이는 별"""
    def __init__(self, rng, n=110, ymax=0.62):
        self.p = [dict(x=rng.randint(0, W), y=rng.randint(0, int(H*ymax)),
                       r=rng.choice([1,1,2,2,3]), n=rng.choice([1,2,3,4]),
                       phase=rng.uniform(0,1), base=rng.randint(70,150)) for _ in range(n)]
    def draw(self, layer, t):
        d = ImageDraw.Draw(layer)
        for q in self.p:
            a = int(q["base"] * (0.45 + 0.55 * (0.5 + 0.5*math.sin(TAU*(q["n"]*t + q["phase"])))))
            d.ellipse([q["x"]-q["r"], q["y"]-q["r"], q["x"]+q["r"], q["y"]+q["r"]], fill=(255,255,246,a))

class Rays(Element):
    """숨쉬는 빛줄기"""
    def __init__(self, cx, cy, color=(255,250,230), n_rays=3, width=140, breathe=1):
        self.cx, self.cy, self.color, self.n, self.w, self.breathe = cx, cy, color, n_rays, width, breathe
        base = Image.new("RGBA", (W, H), (0,0,0,0))
        d = ImageDraw.Draw(base)
        for i in range(self.n):
            w = self.w + i * 130
            a = 44 - i * 12
            d.polygon([(cx - w//3, cy), (cx + w//3, cy), (cx + w, H), (cx - w, H)], fill=color + (max(a,10),))
        self.base = base.filter(ImageFilter.GaussianBlur(22))
    def draw(self, layer, t):
        k = 0.62 + 0.38 * (0.5 + 0.5 * math.sin(TAU * self.breathe * t))
        f = self.base.copy()
        f.putalpha(f.getchannel("A").point(lambda p: int(p * k)))
        layer.alpha_composite(f)

class Steam(Element):
    """피어오르는 김"""
    def __init__(self, rng, cx, cy, n=14, spread=90, color=(255,248,238)):
        self.p = [dict(x0=cx + rng.uniform(-spread, spread), y0=cy, wraps=rng.choice([1,2]),
                       swayA=rng.uniform(14, 40), swayN=rng.choice([1,2]), phase=rng.uniform(0,1),
                       rise=rng.uniform(H*0.36, H*0.6),
                       sprite=_sprite_circle(rng.randint(16, 34), color, soft=1.4)) for _ in range(n)]
    def draw(self, layer, t):
        for q in self.p:
            prog = (q["wraps"] * t + q["phase"]) % 1.0
            y = q["y0"] - prog * q["rise"]
            x = q["x0"] + q["swayA"] * math.sin(TAU * (q["swayN"] * t + q["phase"] * 3))
            a = int(70 * math.sin(math.pi * prog))  # 위로 갈수록 소멸
            sp = q["sprite"].copy()
            sp.putalpha(sp.getchannel("A").point(lambda p, a=a: int(p * a / 255)))
            layer.alpha_composite(sp, (int(x)-sp.width//2, int(y)-sp.height//2))

class Embers(Element):
    """피어오르는 불씨/금빛 입자"""
    def __init__(self, rng, n=34, colors=((255,190,110),(255,150,70),(255,220,150))):
        self.p = [dict(x=rng.uniform(0, W), y=rng.uniform(0, H), wraps=rng.choice([1,2,3]),
                       swayA=rng.uniform(16, 60), swayN=rng.choice([1,2]), phase=rng.uniform(0,1),
                       pulseN=rng.choice([2,3,4]),
                       sprite=_sprite_circle(rng.randint(4, 13), rng.choice(list(colors)), soft=1.6)) for _ in range(n)]
    def draw(self, layer, t):
        span = H + 200
        for q in self.p:
            y = (q["y"] - q["wraps"] * span * t) % span - 100
            x = q["x"] + q["swayA"] * math.sin(TAU * (q["swayN"] * t + q["phase"]))
            a = 150 * (0.5 + 0.5 * math.sin(TAU * (q["pulseN"] * t + q["phase"])))
            sp = q["sprite"].copy()
            sp.putalpha(sp.getchannel("A").point(lambda p, a=a: int(p * a / 255)))
            layer.alpha_composite(sp, (int(x)-sp.width//2, int(y)-sp.height//2))

class CandleGlow(Element):
    """흔들리는 촛불 광원"""
    def __init__(self, cx, cy, color=(255,200,120), r=240):
        self.cx, self.cy, self.r = cx, cy, r
        self.sprite = _sprite_circle(r, color, soft=1.1)
    def draw(self, layer, t):
        flick = (0.72 + 0.18 * math.sin(TAU*3*t) + 0.10 * math.sin(TAU*7*t + 1.3))
        sp = self.sprite.copy()
        sp.putalpha(sp.getchannel("A").point(lambda p: int(p * 0.9 * flick)))
        dx = int(5 * math.sin(TAU * 2 * t))
        layer.alpha_composite(sp, (self.cx - sp.width//2 + dx, self.cy - sp.height//2))

class WaveLines(Element):
    """잔잔한 수면 물결"""
    def __init__(self, cy, n=7, color=(235,250,248)):
        self.cy, self.n, self.color = cy, n, color
    def draw(self, layer, t):
        d = ImageDraw.Draw(layer)
        for i in range(self.n):
            y0 = self.cy + i * 46
            amp = 5 + i * 1.6
            a = max(10, 52 - i * 7)
            pts = [(x, y0 + amp * math.sin(TAU * (x / 640 + t * (1 + i % 2) + i * 0.35)))
                   for x in range(-20, W + 21, 24)]
            d.line(pts, fill=self.color + (int(a),), width=3)

class Moon(Element):
    def __init__(self, cx, cy, r=66):
        self.cx, self.cy, self.r = cx, cy, r
        self.glow = _sprite_circle(220, (230,238,255), soft=1.1)
    def draw(self, layer, t):
        k = 0.75 + 0.25 * (0.5 + 0.5 * math.sin(TAU * t))
        g = self.glow.copy()
        g.putalpha(g.getchannel("A").point(lambda p: int(p * 0.75 * k)))
        layer.alpha_composite(g, (self.cx - g.width//2, self.cy - g.height//2))
        d = ImageDraw.Draw(layer)
        d.ellipse([self.cx-self.r, self.cy-self.r, self.cx+self.r, self.cy+self.r], fill=(246,248,252,255))

class SunGlow(Element):
    def __init__(self, cx, cy, color=(255,215,150), r=320, disc=120):
        self.cx, self.cy, self.disc = cx, cy, disc
        self.glow = _sprite_circle(r, color, soft=1.1)
    def draw(self, layer, t):
        k = 0.8 + 0.2 * math.sin(TAU * t)
        g = self.glow.copy()
        g.putalpha(g.getchannel("A").point(lambda p: int(p * 0.85 * k)))
        layer.alpha_composite(g, (self.cx - g.width//2, self.cy - g.height//2))
        d = ImageDraw.Draw(layer)
        d.ellipse([self.cx-self.disc, self.cy-self.disc, self.cx+self.disc, self.cy+self.disc],
                  fill=(255, 235, 190, 255))

# ───────────────────── 텍스트 오버레이 ─────────────────────
def text_overlay(title, lang, sub="LIGHTHOUSE WORSHIP", pos=0.14):
    """상단 타이틀 오버레이 (가사 자막은 하단이므로 충돌 없음)"""
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    fpath = F_KR if lang == "KR" else F_EN
    fsize = 88 if lang == "KR" else (76 if len(title) > 16 else 86)
    font = ImageFont.truetype(fpath, fsize)
    bbox = d.textbbox((0,0), title, font=font)
    tx, ty = (W-(bbox[2]-bbox[0]))//2, int(H*pos)
    d.text((tx+4, ty+5), title, font=font, fill=(0,0,0,130))
    d.text((tx, ty), title, font=font, fill=(255,252,245,255))
    f2 = ImageFont.truetype(F_SUB, 30)
    s = "  ".join(sub)
    b2 = d.textbbox((0,0), s, font=f2)
    d.text(((W-(b2[2]-b2[0]))//2, ty + fsize + 26), s, font=f2, fill=(255,250,238,190))
    return layer

def playlist_overlay(main, sub, accent=(120,64,30)):
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    f_main = ImageFont.truetype(F_KR, 100)
    bbox = d.textbbox((0,0), main, font=f_main)
    tx, ty = (W-(bbox[2]-bbox[0]))//2, int(H*0.38)
    d.text((tx+5, ty+6), main, font=f_main, fill=(0,0,0,150))
    d.text((tx, ty), main, font=f_main, fill=(255,252,244,255))
    f_sub = ImageFont.truetype(F_EN_I, 44)
    b2 = d.textbbox((0,0), sub, font=f_sub)
    d.text(((W-(b2[2]-b2[0]))//2, ty+136), sub, font=f_sub, fill=accent+(235,))
    small = "L I G H T H O U S E   W O R S H I P"
    f_s = ImageFont.truetype(F_SUB, 28)
    b3 = d.textbbox((0,0), small, font=f_s)
    d.text(((W-(b3[2]-b3[0]))//2, ty+212), small, font=f_s, fill=(255,250,238,170))
    return layer

# ───────────────────── 렌더러 ─────────────────────
def render_loop(bg, elements, overlay, out_path, zoom_breathe=0.012):
    """배경 + 요소 + 오버레이 → 심리스 루프 mp4 (ffmpeg rawvideo 파이프)"""
    bigW, bigH = int(W * 1.05), int(H * 1.05)
    bg_big = bg.resize((bigW, bigH), Image.LANCZOS)
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-crf", "20", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in range(FRAMES):
        t = f / FRAMES
        # 배경 줌 호흡 (심리스: sin 1주기)
        k = 1.0 + zoom_breathe * (0.5 + 0.5 * math.sin(TAU * t))
        cw, chh = int(W / k), int(H / k)
        x0, y0 = (bigW - cw)//2, (bigH - chh)//2
        frame = bg_big.crop((x0, y0, x0+cw, y0+chh)).resize((W, H), Image.BILINEAR).convert("RGBA")
        layer = Image.new("RGBA", (W, H), (0,0,0,0))
        for el in elements:
            el.draw(layer, t)
        frame.alpha_composite(layer)
        if overlay is not None:
            frame.alpha_composite(overlay)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    return out_path
