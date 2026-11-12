# -*- coding: utf-8 -*-
"""T-07 design — draft 글 + 배경 → 카드 PNG 5장(1080x1350) + manifest.

배경: data/backgrounds/manifest.json 항목만(origin=higgsfield|owned, 파일은 data/backgrounds/ 안).
      비어 있으면 PIL 그라데이션(origin="owned", generator="local-gradient"). 이 모듈은 외부 호출 0.
글자: 허용 글꼴(config/fonts_allowed.json)만. 기본 'Noto Sans KR'. 자동 줄바꿈·크기 맞춤.
      밝은 판(흰색 88%·둥근 모서리·옅은 그림자)+진한 글자(brand.primary_color), brand.accent_color 는 제목 밑 막대·강조상자 포인트에만.
      판 높이는 글 양에 맞추고 배경이 판 바깥으로 보인다. 표지(1장)=큰 제목, 마지막 장=고정 문구 강조 상자.
      WCAG AA(4.5:1) 대비를 코드로 계산(판 아래 가장 어두운 배경 기준)해 미달이면 DesignError.
      최소 크기로도 판 안에 안 들어가면 글자를 자르지 않고 DesignError(수치·문구 훼손 방지 → compose 가 짧게 다시).
draft 의 각 card 에 image_path·bg_path·bg_origin·font 를 채운다(guard G4·G7 이 그대로 읽음). 반환 = manifest.
backgrounds manifest 항목: {"file": "bg1.png", "origin": "higgsfield|owned", "job_id": "..."}  (file 은 backgrounds 폴더 기준)
"""
import hashlib
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config as C

ROOT = C.ROOT
BG_DIR = os.path.join(ROOT, "data", "backgrounds")
BG_MANIFEST = os.path.join(BG_DIR, "manifest.json")
W, H = 1080, 1350
DEFAULT_FONT = "Noto Sans KR"
ORIGINS_OK = {"higgsfield", "owned"}
MARGIN = 70
PAD = 56
TITLE_SIZES = (84, 72, 62, 54, 48, 42)
BODY_SIZES = (50, 46, 42, 38, 34, 30)
DEFAULT_BRAND = ("#1F3A5F", "#0B1626")  # 어두운 기본(폴백 그라데이션은 gradient_for 가 밝게 만든다)


class DesignError(ValueError):
    pass


def load_font_table(path=None):
    p = path or os.path.join(C.CONFIG, "fonts_allowed.json")
    return {f["name"]: f for f in C.load_json(p)["fonts"]}


def load_bg_manifest(path=BG_MANIFEST):
    if not os.path.exists(path):
        return []
    items = C.load_json(path)
    items = items.get("items", []) if isinstance(items, dict) else items
    return items


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def gradient(colors=DEFAULT_BRAND, size=(W, H)):
    top, bot = _hex(colors[0]), _hex(colors[1])
    im = Image.new("RGB", size)
    d = ImageDraw.Draw(im)
    for y in range(size[1]):
        t = y / (size[1] - 1)
        d.line([(0, y), (size[0], y)], fill=tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    return im


def cover(im, size=(W, H)):
    im = im.convert("RGB")
    s = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((x, y, x + size[0], y + size[1]))


def _font(path, size, bold=False):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_name("Bold" if bold else "Regular")
    except Exception:  # noqa: BLE001 — 가변 글꼴이 아니거나 FreeType 미지원이면 기본 굵기
        pass
    return f


_HOLD = chr(0)  # 숫자 표현 안의 공백을 줄바꿈 후보에서 숨기는 표식


def _words(para):
    """공백 단위 낱말. verify.NUM_RE 가 잡는 숫자 표현('36만 7000원'·'144만 가구')은 안의 공백까지 한 덩어리."""
    from .verify import NUM_RE
    prot = NUM_RE.sub(lambda m: m.group(0).replace(" ", _HOLD), para)
    return [w.replace(_HOLD, " ") for w in prot.split(" ")]


def wrap(draw, text, font, max_w):
    """단어(공백) 단위로 줄바꿈, 한 단어가 폭보다 길면 글자 단위로 쪼갠다. 원문 글자는 하나도 버리지 않음.
    숫자 표현은 중간에서 끊지 않는다(덩어리가 한 줄보다 길 때만 글자 단위로 쪼갬)."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in _words(para):
            cand = word if not cur else cur + " " + word
            if draw.textlength(cand, font=font) <= max_w:
                cur = cand
                continue
            if cur:
                lines.append(cur)
                cur = ""
            while draw.textlength(word, font=font) > max_w:
                k = len(word)
                while k > 1 and draw.textlength(word[:k], font=font) > max_w:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            cur = word
        lines.append(cur)
    return lines


# ---- WCAG 대비 ----
MIN_CONTRAST = 4.5  # WCAG AA(일반 글자)
PANEL_ALPHA = 0.88  # 흰 판 불투명도(85~90%)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = rgb[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _mix(c1, c2, t):
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def brand_palette(brand=None):
    brand = brand or {}
    primary = _hex(brand.get("primary_color") or DEFAULT_BRAND[0])
    accent = _hex(brand.get("accent_color") or "#F2A541")
    return {"primary": primary, "accent": accent, "body": _mix(primary, (0, 0, 0), 0.45)}


def panel_worst_color(bg, box):
    """판 아래 배경에서 가장 어두운 곳의 합성 색(흰 판 88% + 배경 12%). 글자 대비는 이 최악 색 기준으로 잰다."""
    px = bg.convert("RGB").load()
    worst = (255, 255, 255)
    for y in range(box[1], box[3], 8):
        for x in range(box[0], box[2], 8):
            c = tuple(round(255 * PANEL_ALPHA + v * (1 - PANEL_ALPHA)) for v in px[x, y])
            if luminance(c) < luminance(worst):
                worst = c
    return worst


def check_contrast(pal, panel_color):
    """미달이면 DesignError. 반환 = 측정값 dict."""
    pairs = {"제목(primary)/판": (pal["primary"], panel_color), "본문/판": (pal["body"], panel_color),
             "강조상자 글자(흰색)/primary": ((255, 255, 255), pal["primary"])}
    out = {}
    for name, (fg, bg) in pairs.items():
        r = contrast(fg, bg)
        out[name] = round(r, 2)
        if r < MIN_CONTRAST:
            raise DesignError(f"명도 대비 미달(WCAG AA {MIN_CONTRAST}:1): {name} {r:.2f}:1")
    return out


# ---- 글자 배치 ----
COVER_TITLE_SIZES = (120, 106, 94, 82, 72, 62)
COVER_BODY_SIZES = (46, 42, 38, 34, 32, 30)
GAP = 36           # 제목 밑줄 ↔ 본문
BAR_H = 8          # 제목 밑 강조 막대
NOTICE_SIZES = (44, 40, 36, 32)


def split_notice(card, idx, total):
    """마지막 카드 본문에 고정 문구가 있으면 본문과 분리해 강조 상자로."""
    from .compose import NOTICE
    body = card["body"]
    if idx == total and NOTICE in body:
        return body.replace(NOTICE, "").strip(), NOTICE
    return body, None


def fit_text(draw, title, body, font_path, max_w, max_h, cover=False, notice=None):
    """(title_font, title_lines, body_font, body_lines, notice_font, notice_lines, total_h). 안 들어가면 DesignError."""
    tsz, bsz = (COVER_TITLE_SIZES, COVER_BODY_SIZES) if cover else (TITLE_SIZES, BODY_SIZES)
    for k, (ts, bs) in enumerate(zip(tsz, bsz)):
        tf, bf = _font(font_path, ts, True), _font(font_path, bs)
        tl, bl = wrap(draw, title, tf, max_w), (wrap(draw, body, bf, max_w) if body else [])
        h = len(tl) * round(ts * 1.3) + BAR_H + GAP + len(bl) * round(bs * 1.5)
        nf, nl = None, []
        if notice:
            nf = _font(font_path, NOTICE_SIZES[min(k, len(NOTICE_SIZES) - 1)], True)
            nl = wrap(draw, notice, nf, max_w - 80)
            h += 36 + len(nl) * round(nf.size * 1.45) + 56
        if h <= max_h:
            return tf, tl, bf, bl, nf, nl, h
    raise DesignError(f"글이 판에 안 들어감(최소 크기 {bsz[-1]}px): {title!r}")


def render_card(card, bg, font_path, idx, total, brand=None):
    """밝은 판(흰색 88%·둥근 모서리·옅은 그림자) + 진한 글자. 판 높이는 글 양에 맞추고 위아래 배경을 넉넉히 보인다.
    반환 (RGB 이미지, {"panel": box, "contrast": {...}})."""
    pal = brand_palette(brand)
    base = bg.copy().convert("RGBA")
    d0 = ImageDraw.Draw(base)
    max_w = W - 2 * MARGIN - 2 * PAD
    max_content = H - 2 * MARGIN - 2 * PAD
    body, notice = split_notice(card, idx, total)
    tf, tl, bf, bl, nf, nl, h = fit_text(d0, card["title"], body, font_path, max_w, max_content, cover=(idx == 1), notice=notice)
    ph = max(h + 2 * PAD, 520)
    top = (H - ph) // 2
    box = (MARGIN, top, W - MARGIN, top + ph)
    panel_color = panel_worst_color(bg, box)
    measured = check_contrast(pal, panel_color)
    # 그림자
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((box[0], box[1] + 10, box[2], box[3] + 10), radius=40, fill=(20, 30, 50, 70))
    base = Image.alpha_composite(base, sh.filter(ImageFilter.GaussianBlur(18)))
    pl = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(pl).rounded_rectangle(box, radius=40, fill=(255, 255, 255, round(255 * PANEL_ALPHA)))
    im = Image.alpha_composite(base, pl)
    d = ImageDraw.Draw(im)
    x0, y = box[0] + PAD, box[1] + PAD
    for line in tl:
        d.text((x0, y), line, font=tf, fill=pal["primary"])
        y += round(tf.size * 1.3)
    d.rounded_rectangle((x0, y + 2, x0 + 120, y + 2 + BAR_H), radius=4, fill=pal["accent"])  # 강조색은 막대·포인트에만
    y += BAR_H + GAP
    for line in bl:
        d.text((x0, y), line, font=bf, fill=pal["body"])
        y += round(bf.size * 1.5)
    if notice:
        y += 36
        nh = len(nl) * round(nf.size * 1.45) + 56
        d.rounded_rectangle((x0, y, box[2] - PAD, y + nh), radius=24, fill=pal["primary"])
        d.rounded_rectangle((x0, y, x0 + 14, y + nh), radius=7, fill=pal["accent"])
        ty = y + 28
        for line in nl:
            d.text((x0 + 44, ty), line, font=nf, fill=(255, 255, 255))
            ty += round(nf.size * 1.45)
    d.text((box[2] - 28, box[3] - 22), f"{idx}/{total}", font=_font(font_path, 28), fill=pal["body"], anchor="rs")
    return im.convert("RGB"), {"panel": box, "contrast": measured}


def design(draft, bg_manifest, out_dir, font_name=None, fonts_path=None, brand=None, backgrounds_dir=BG_DIR):
    """draft(in-place 로 image_path·bg_path·bg_origin·font 채움) → manifest dict(out_dir/manifest.json 에도 저장)."""
    fonts = load_font_table(fonts_path)
    font_name = font_name or (brand or {}).get("font") or DEFAULT_FONT
    if font_name not in fonts:
        raise DesignError(f"허용 글꼴 아님: {font_name!r} (허용: {sorted(fonts)})")
    finfo = fonts[font_name]
    if not os.path.exists(finfo["file"]):
        raise DesignError(f"글꼴 파일 없음: {finfo['file']}")
    cards = draft["cards"]
    if len(cards) != 5:
        raise DesignError(f"카드 {len(cards)}장 (5장이어야 함)")
    for it in bg_manifest:
        if it.get("origin") not in ORIGINS_OK:
            raise DesignError(f"배경 origin {it.get('origin')!r} 허용 안 됨(higgsfield|owned): {it.get('file')}")
        if it["origin"] == "higgsfield" and not (it.get("sha256") and it.get("job_id")):
            # origin 은 자기 신고라, 폴더에 외부 이미지를 넣고 higgsfield 라고 적는 것을 막는다(생성 job_id 와 파일 해시가 모두 있어야 함)
            raise DesignError(f"higgsfield 배경은 sha256·job_id 필수: {it.get('file')}")
    os.makedirs(out_dir, exist_ok=True)
    entries = []
    for i, c in enumerate(cards):
        if bg_manifest:
            it = bg_manifest[i % len(bg_manifest)]
            bg_path = os.path.join(backgrounds_dir, it["file"])
            if not os.path.exists(bg_path):
                raise DesignError(f"배경 파일 없음: {bg_path}")
            if it.get("sha256"):
                with open(bg_path, "rb") as fh:
                    if hashlib.sha256(fh.read()).hexdigest() != it["sha256"]:
                        raise DesignError(f"배경 sha256 불일치(파일이 바뀜): {bg_path}")
            with Image.open(bg_path) as raw:
                bg = cover(raw)
            origin, job_id, gen = it["origin"], it.get("job_id"), it.get("generator", "higgsfield-mcp" if it["origin"] == "higgsfield" else "owned")
        else:
            bg_path = os.path.join(out_dir, f"bg_{i + 1}.png")
            pal = brand_palette(brand)
            bg = gradient(("#%02x%02x%02x" % _mix(pal["primary"], (255, 255, 255), 0.88), "#%02x%02x%02x" % _mix(pal["accent"], (255, 255, 255), 0.7)))
            bg.save(bg_path)
            origin, job_id, gen = "owned", None, "local-gradient"
        img, info = render_card(c, bg, finfo["file"], i + 1, len(cards), brand)
        assert img.size == (W, H)
        out = os.path.join(out_dir, f"card_{i + 1}.png")
        img.save(out)
        c.update({"image_path": out, "bg_path": bg_path, "bg_origin": origin, "font": font_name})
        entries.append({"card": i + 1, "image_path": out, "bg_file": bg_path, "bg_origin": origin,
                        "job_id": job_id, "bg_generator": gen, "panel": list(info["panel"]), "contrast": info["contrast"], "bg_sha256": it.get("sha256") if bg_manifest else None})
    manifest = {"account_id": draft.get("account_id"), "kw": draft.get("kw"), "size": [W, H],
                "font": {"name": font_name, "file": finfo["file"], "license": finfo.get("license", ""),
                         "license_url": finfo.get("license_url", "")},
                "cards": entries}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    return manifest
