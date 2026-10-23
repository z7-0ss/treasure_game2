"""art.py —— 像素美术：怪物精灵、掉落物图标、地图地格与光效。"""
import math
import os

import pygame

from settings import *


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
_sprite_cache = {}
_glow_cache = {}


def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def _light(color, amount=0.35):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color[:3])


def _blend(color_a, color_b, t):
    return tuple(int(color_a[i] + (color_b[i] - color_a[i]) * t) for i in range(3))


def _check_grid(name, grid):
    width = len(grid[0])
    for row in grid:
        if len(row) != width:
            raise ValueError(f"{name} 行宽不一致: {row!r} ({len(row)} != {width})")
    return width


def sprite(name, grid, palette, scale, flip=False):
    """把字符画渲染成带缓存的 Surface（同一份资源只渲染一次）。"""
    key = (name, scale, flip, tuple(sorted(palette.items())))
    surf = _sprite_cache.get(key)
    if surf is not None:
        return surf

    width = _check_grid(name, grid)
    surf = pygame.Surface((width * scale, len(grid) * scale), pygame.SRCALPHA)
    for row_i, row in enumerate(grid):
        for col_i, ch in enumerate(row):
            color = palette.get(ch)
            if color is None:
                continue
            x = (width - 1 - col_i) * scale if flip else col_i * scale
            surf.fill(color, (x, row_i * scale, scale, scale))
    _sprite_cache[key] = surf
    return surf


def silhouette(surf, color=(255, 255, 255, 230)):
    """生成纯色剪影，用于受击闪白。"""
    key = ("sil", id(surf))
    out = _sprite_cache.get(key)
    if out is None:
        out = surf.copy()
        out.fill((255, 255, 255, 0), special_flags=0)
        mask = pygame.mask.from_surface(surf)
        out = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
        _sprite_cache[key] = out
    return out


def glow_surface(radius, color, alpha=90):
    """径向渐变光晕（缓存）。

    BLEND_ADD 会忽略 alpha，所以这里把颜色按 alpha 预乘，
    叠加时才会得到由内到外渐隐的光晕。
    """
    key = (radius, color, alpha)
    surf = _glow_cache.get(key)
    if surf is not None:
        return surf
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = max(8, radius // 2)
    for i in range(steps):
        t = i / steps                      # 0 = 外圈
        r = radius * (1 - t)
        a = alpha * (t ** 1.7)
        col = (int(color[0] * a / 255), int(color[1] * a / 255), int(color[2] * a / 255), 255)
        pygame.draw.circle(surf, col, (radius, radius), max(1, int(r)))
    _glow_cache[key] = surf
    return surf


_shadow_cache = {}


def shadow(screen, x, y, w, h=8, alpha=90):
    """椭圆落地影子（缓存）。"""
    key = (w, h, alpha)
    surf = _shadow_cache.get(key)
    if surf is None:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (0, 0, 0, alpha), (0, 0, w, h))
        _shadow_cache[key] = surf
    screen.blit(surf, (int(x), int(y)))


def blit_glow(screen, cx, cy, radius, color, alpha=90):
    surf = glow_surface(radius, color, alpha)
    screen.blit(surf, (cx - radius, cy - radius), special_flags=pygame.BLEND_ADD)


# --------------------------------------------------------------------------
# 怪物字符画
# --------------------------------------------------------------------------
SLIME = (
    "............",
    "............",
    "....oooo....",
    "..oo####oo..",
    ".o##++++##o.",
    ".o##+##+##o.",
    "o##e####e##o",
    "o##p####p##o",
    "o##########o",
    ".o########o.",
    "..o######o..",
    "...oooooo...",
)

MUSHROOM = (
    "....oooo....",
    "..oo####oo..",
    ".o##++++##o.",
    "o###+##+###o",
    "o##########o",
    "o----------o",
    ".o########o.",
    ".o#e####e#o.",
    ".o#p####p#o.",
    ".o########o.",
    "..o######o..",
    "...oooooo...",
)

SKELETON = (
    "....oooo....",
    "...o#++#o...",
    "..o######o..",
    "..o#e##e#o..",
    "..o#p##p#o..",
    "..o######o..",
    "...o#mm#o...",
    "....o##o....",
    "...oo##oo...",
    "..o#o##o#o..",
    "..o#o##o#o..",
    "...oo..oo...",
)

BAT_UP = (
    "o..........o",
    "oo........oo",
    "o#o..oo..o#o",
    "o##o####o##o",
    ".o##e##e##o.",
    "..o#p##p#o..",
    "...o####o...",
    "....o..o....",
    "............",
    "............",
    "............",
    "............",
)

BAT_DOWN = (
    "............",
    "............",
    "....oooo....",
    "...o####o...",
    "o##oe##eo##o",
    "o###p##p###o",
    "o##o####o##o",
    ".o..o##o..o.",
    "....o..o....",
    "............",
    "............",
    "............",
)

GOLEM = (
    "............",
    "...oooooo...",
    "..o######o..",
    "..o#e##e#o..",
    "..o######o..",
    ".oo#+mm+#oo.",
    "o###o##o###o",
    "o##o#--#o##o",
    "o##o#--#o##o",
    ".oo.o##o.oo.",
    "....o##o....",
    "....oooo....",
)

BUTTERFLY_OPEN = (
    "............",
    "..oo....oo..",
    ".o##o..o##o.",
    "o#++#oo#++#o",
    "o#++#oo#++#o",
    "o####oo####o",
    ".o##o##o##o.",
    "..oo####oo..",
    "....oooo....",
    "............",
    "............",
    "............",
)

BUTTERFLY_CLOSE = (
    "............",
    "....oooo....",
    "...o#++#o...",
    "..o#+##+#o..",
    ".o##o##o##o.",
    "o###o##o###o",
    "o##oo##oo##o",
    ".o#o####o#o.",
    "..o.o##o.o..",
    "....oooo....",
    "............",
    "............",
)

PET = (
    "............",
    "....oo......",
    "...o##o.....",
    "..o#++#oo...",
    ".o#++++##o..",
    ".o#+e##e#o..",
    "..o##pp##o..",
    "...o####o...",
    "..oo#oo#oo..",
    ".o###o..o#o.",
    "..ooo....oo.",
    "............",
)

TREE = (
    "..gggggggg..",
    ".g#gggggg#g.",
    "gg##gggg##gg",
    "ggg######ggg",
    ".gg######gg.",
    "..o######o..",
    "..o#e##e#o..",
    "..o#p##p#o..",
    "..o######o..",
    "..o#o##o#o..",
    "..o######o..",
    "...oooooo...",
)


# 怪物配色：o 描边 / # 主体 / + 高光 / - 阴影 / e 眼白 / p 瞳孔 / m 嘴 / g 副色
def _monster_palette(body, outline, accent, elite=False):
    return {
        "o": outline,
        "#": body,
        "+": _light(body, 0.45),
        "-": _shade(body, 0.72),
        "e": (250, 250, 255),
        "p": (18, 12, 26),
        "m": accent,
        "g": _shade(body, 0.8) if elite else accent,
    }


MONSTER_ART = {
    "slime": {
        "frames": [SLIME],
        "body": (128, 62, 196), "outline": (36, 12, 56), "accent": (92, 42, 150),
        "scale": 3, "fly": False,
    },
    "mushroom": {
        "frames": [MUSHROOM],
        "body": (198, 64, 72), "outline": (48, 14, 20), "accent": (236, 224, 200),
        "scale": 3, "fly": False,
    },
    "skeleton": {
        "frames": [SKELETON],
        "body": (222, 218, 206), "outline": (48, 46, 54), "accent": (190, 60, 70),
        "scale": 3, "fly": False,
    },
    "bat": {
        "frames": [BAT_UP, BAT_DOWN],
        "body": (96, 70, 150), "outline": (26, 18, 38), "accent": (188, 120, 230),
        "scale": 3, "fly": True,
    },
    "butterfly": {
        "frames": [BUTTERFLY_OPEN, BUTTERFLY_CLOSE],
        "body": (244, 150, 206), "outline": (86, 32, 70), "accent": (255, 224, 240),
        "scale": 3, "fly": True,
    },
    "golem": {
        "frames": [GOLEM],
        "body": (156, 158, 172), "outline": (40, 42, 54), "accent": (110, 116, 140),
        "scale": 4, "fly": False,
    },
    "tree": {
        "frames": [TREE],
        "body": (74, 132, 66), "outline": (26, 48, 24), "accent": (52, 104, 46),
        "scale": 4, "fly": False,
    },
}

ELITE_BODY = {
    "slime": (196, 92, 92),
    "mushroom": (226, 140, 52),
    "skeleton": (150, 200, 240),
    "bat": (206, 92, 120),
    "butterfly": (150, 130, 250),
    "tree": (150, 120, 60),
}


def monster_sprite(enemy_type, elite=False, frame=0, flip=False):
    art = MONSTER_ART.get(enemy_type, MONSTER_ART["slime"])
    body = ELITE_BODY.get(enemy_type, art["body"]) if elite else art["body"]
    palette = _monster_palette(body, art["outline"], art["accent"], elite)
    if elite:
        # 精英怪：描边带一圈暗金光
        palette["o"] = (120, 92, 24)
    frames = art["frames"]
    grid = frames[frame % len(frames)]
    return sprite(f"mob:{enemy_type}:{elite}:{frame}", grid, palette, art["scale"], flip)


_WEAPON_CACHE = {}
_WEAPON_ROT_CACHE = {}
_WING_CACHE = {}
_BOSS_CACHE = {}


def boss_weapon_surface(kind, color=(210, 214, 226), scale=3):
    key = (kind, color, scale)
    if key in _WEAPON_CACHE:
        return _WEAPON_CACHE[key]
    surf = pygame.Surface((16 * scale, 16 * scale), pygame.SRCALPHA)
    dark = _shade(color, 0.55)
    wood = (120, 84, 52)
    if kind == "sword":
        surf.fill(dark, (7 * scale, 2 * scale, 2 * scale, 8 * scale))
        surf.fill(color, (7 * scale, 2 * scale, 1 * scale, 8 * scale))
        surf.fill((236, 226, 180), (5 * scale, 8 * scale, 6 * scale, 1 * scale))
        surf.fill(wood, (7 * scale, 9 * scale, 2 * scale, 3 * scale))
        surf.fill((250, 226, 120), (6 * scale, 12 * scale, 4 * scale, 1 * scale))
    elif kind == "axe":
        surf.fill(wood, (7 * scale, 4 * scale, 2 * scale, 10 * scale))
        surf.fill(color, (3 * scale, 2 * scale, 6 * scale, 5 * scale))
        surf.fill(dark, (3 * scale, 2 * scale, 6 * scale, 1 * scale))
        surf.fill((236, 226, 180), (3 * scale, 6 * scale, 6 * scale, 1 * scale))
    elif kind == "hammer":
        surf.fill(wood, (7 * scale, 4 * scale, 2 * scale, 10 * scale))
        surf.fill(color, (3 * scale, 1 * scale, 10 * scale, 5 * scale))
        surf.fill(dark, (3 * scale, 1 * scale, 10 * scale, 1 * scale))
        surf.fill(dark, (3 * scale, 5 * scale, 10 * scale, 1 * scale))
    elif kind == "staff":
        surf.fill(wood, (7 * scale, 3 * scale, 2 * scale, 12 * scale))
        pygame.draw.circle(surf, color, (8 * scale, 3 * scale), 3 * scale)
        pygame.draw.circle(surf, (255, 255, 255), (7 * scale, 2 * scale), 1 * scale)
    else:  # club
        surf.fill(wood, (7 * scale, 6 * scale, 2 * scale, 8 * scale))
        surf.fill(color, (5 * scale, 1 * scale, 6 * scale, 6 * scale))
        surf.fill(dark, (5 * scale, 1 * scale, 6 * scale, 1 * scale))
    _WEAPON_CACHE[key] = surf
    return surf


def draw_boss_weapon(screen, x, y, kind, facing_right=False, swing=0.0, color=(214, 218, 230)):
    step = max(0, min(12, int(round(swing * 12))))
    angle = -28 + step * (26 / 12)
    if not facing_right:
        angle = 28 - step * (26 / 12)
    key = (kind, color, facing_right, step)
    rot = _WEAPON_ROT_CACHE.get(key)
    if rot is None:
        surf = boss_weapon_surface(kind, color)
        rot = pygame.transform.rotate(surf, angle)
        _WEAPON_ROT_CACHE[key] = rot
    screen.blit(rot, (int(x - rot.get_width() // 2), int(y - rot.get_height() // 2)))


def draw_wings(screen, x, y, color=(220, 230, 255), flap=0.0):
    """天空 BOSS 的翅膀（在身体后面画）。"""
    spread = 0.6 + 0.4 * abs(math.sin(flap))
    for side in (-1, 1):
        w = int(52 * spread)
        h = 34
        key = (side, color, w, h)
        cached = _WING_CACHE.get(key)
        if cached is None:
            pts = [(0, 0),
                   (side * w, -h * 0.55),
                   (side * (w + 14), -h * 0.1),
                   (side * w * 0.8, h * 0.4)]
            surf = pygame.Surface((abs(side * (w + 16)) + 8, h * 2 + 8), pygame.SRCALPHA)
            ox = 4 if side > 0 else abs(side * (w + 16)) + 4
            local = [(ox + px, py + h + 4) for px, py in pts]
            pygame.draw.polygon(surf, (*color, 150), local)
            pygame.draw.polygon(surf, (*_shade(color, 0.7), 220), local, 2)
            cached = (surf, ox)
            _WING_CACHE[key] = cached
        surf, ox = cached
        screen.blit(surf, (x - ox, y - h - 4))


def _boss_decor(surface, enemy_type, chapter, variant):
    w, h = surface.get_width(), surface.get_height()
    cx = w // 2
    outline = (28, 16, 36)
    chapter_cols = {
        0: ((118, 210, 138), (214, 255, 196)),
        1: ((92, 196, 238), (210, 246, 255)),
        2: ((198, 210, 252), (255, 252, 232)),
        3: ((255, 142, 94), (255, 228, 142)),
    }
    trim, glow = chapter_cols.get(chapter, ((200, 180, 230), (255, 236, 186)))
    rage = (230, 92, 88)
    ancient = (168, 128, 240)
    abyss = (78, 58, 118)
    if enemy_type == "slime":
        pygame.draw.arc(surface, outline, (cx - 28, 12, 56, 24), math.pi, math.tau, 3)
        pygame.draw.arc(surface, trim, (cx - 26, 10, 52, 20), math.pi, math.tau, 2)
        pygame.draw.circle(surface, glow, (cx, h // 2 - 6), 7, 2)
    elif enemy_type == "mushroom":
        pygame.draw.arc(surface, outline, (cx - 34, 8, 68, 28), math.pi, math.tau, 4)
        pygame.draw.arc(surface, trim, (cx - 32, 10, 64, 22), math.pi, math.tau, 2)
        for dx in (-16, 0, 16):
            pygame.draw.circle(surface, glow, (cx + dx, 22), 4)
    elif enemy_type == "skeleton":
        pygame.draw.polygon(surface, outline, [(cx - 26, 22), (cx - 10, 8), (cx + 10, 8), (cx + 26, 22)], 0)
        pygame.draw.polygon(surface, trim, [(cx - 22, 22), (cx - 8, 11), (cx + 8, 11), (cx + 22, 22)], 0)
        pygame.draw.rect(surface, glow, (cx - 10, 26, 20, 4))
    elif enemy_type == "golem":
        pygame.draw.rect(surface, outline, (cx - 30, 14, 60, 12), border_radius=3)
        pygame.draw.rect(surface, trim, (cx - 26, 16, 52, 8), border_radius=2)
        pygame.draw.circle(surface, glow, (cx, h // 2 - 4), 6)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 2, h // 2 - 6), 2)
    elif enemy_type == "tree":
        pygame.draw.line(surface, outline, (cx - 10, 18), (cx - 28, 2), 4)
        pygame.draw.line(surface, outline, (cx + 10, 18), (cx + 28, 2), 4)
        pygame.draw.line(surface, trim, (cx - 8, 18), (cx - 26, 4), 2)
        pygame.draw.line(surface, trim, (cx + 8, 18), (cx + 26, 4), 2)
        pygame.draw.circle(surface, glow, (cx, h // 2 - 2), 4)

    if variant >= 1:
        if enemy_type in ("slime", "skeleton", "golem"):
            pygame.draw.polygon(surface, rage, [(cx - 20, 18), (cx - 8, 4), (cx - 2, 18)])
            pygame.draw.polygon(surface, rage, [(cx + 20, 18), (cx + 8, 4), (cx + 2, 18)])
        else:
            pygame.draw.circle(surface, rage, (cx - 16, 18), 5)
            pygame.draw.circle(surface, rage, (cx + 16, 18), 5)
    if variant >= 2:
        for dx in (-18, 0, 18):
            pygame.draw.rect(surface, ancient, (cx + dx - 2, h - 30, 4, 12))
            pygame.draw.rect(surface, glow, (cx + dx - 1, h - 28, 2, 8))
    if variant >= 3:
        pygame.draw.arc(surface, abyss, (cx - 34, h - 34, 68, 20), 0, math.pi, 4)
        pygame.draw.arc(surface, outline, (cx - 34, h - 36, 68, 22), 0, math.pi, 1)
        pygame.draw.circle(surface, abyss, (cx, h // 2 + 8), 8, 2)


def boss_sprite(enemy_type, level_idx, flip=False, variant=0):
    key = (enemy_type, level_idx, flip, variant)
    cached = _BOSS_CACHE.get(key)
    if cached is not None:
        return cached
    art = MONSTER_ART.get(enemy_type, MONSTER_ART["slime"])
    chapter = chapter_of(level_idx)
    body = {
        0: (170, 60, 190),
        1: (60, 150, 210),
        2: (170, 190, 240),
        3: (220, 80, 40),
    }[chapter]
    if variant:
        mix = {1: (210, 70, 70), 2: (150, 90, 230), 3: (70, 50, 110)}.get(variant, (0, 0, 0))
        body = tuple(max(0, min(255, int(body[i] * 0.55 + mix[i] * 0.6))) for i in range(3))
    palette = _monster_palette(body, art["outline"], art["accent"], True)
    palette["+"] = _light(body, 0.6)
    palette["o"] = (18, 10, 24)
    base = sprite(f"boss:{enemy_type}:{level_idx}", art["frames"][0], palette, art["scale"] + 4, flip)
    surf = base.copy()
    _boss_decor(surf, enemy_type, chapter, variant)
    _BOSS_CACHE[key] = surf
    return surf


PLAYER_BODY = (
    "....hhhh....",
    "...hhhhhh...",
    "...hssssh...",
    "...sessse...",
    "...ssssss...",
    "....ssss....",
    "..aaaaaaaa..",
    ".bsaaaaaasb.",
    ".bsaaaaaasb.",
    "..aaaaaaaa..",
    "..aaaaaaaa..",
    "..pppppppp..",
    "...pp..pp...",
    "...ll..ll...",
)
PLAYER_BODIES = {
    WEAPON_SWORD: (
        "...hhhhhh...",
        "..hhhhhhhh..",
        "..hssccssh..",
        "..hssrrssh..",
        "...assssa...",
        "..taaaaatt..",
        ".ttaaaammtt.",
        ".ttaaaammtt.",
        "..taaaaatt..",
        "...appppa...",
        "..pppppppp..",
        "..ppp..ppp..",
        "...ll..ll...",
        "...ll..ll...",
    ),
    WEAPON_BOW: (
        "...hhhhhh...",
        "..hhhhhhhh..",
        "..hsessesh..",
        ".hssrrrsssh.",
        ".mtaaaaattm.",
        ".mtaaaaattm.",
        ".mmaaataamm.",
        "..taaaaatt..",
        "..taaaaatt..",
        "...appppa...",
        "..pppppppp..",
        "..ppp..ppp..",
        "..lll..lll..",
        "...ll..ll...",
    ),
    WEAPON_STAFF: (
        "...hhhhhh...",
        "..hhhhhhhh..",
        "...hseseh...",
        "..mmssrrmm..",
        "..mmaaaamm..",
        ".mmmaaaaamm.",
        ".mttaaaattm.",
        ".mttaaaattm.",
        "..mtaaattm..",
        "..pppppppp..",
        "..pppppppp..",
        "..ppp..ppp..",
        "...ll..ll...",
        "..lll..lll..",
    ),
}
PLAYER_SCALE = 3

GEAR_STYLE = {
    "forest": {"trim": (118, 210, 138), "rune": (224, 255, 186), "cloak": (58, 120, 74),
               "metal": (182, 214, 154), "glow": (132, 230, 150)},
    "ocean": {"trim": (92, 196, 238), "rune": (210, 246, 255), "cloak": (38, 86, 132),
              "metal": (186, 234, 255), "glow": (120, 214, 255)},
    "sky": {"trim": (198, 210, 252), "rune": (255, 252, 232), "cloak": (104, 112, 170),
            "metal": (240, 242, 255), "glow": (220, 226, 255)},
    "volcano": {"trim": (255, 142, 94), "rune": (255, 228, 142), "cloak": (124, 54, 36),
                "metal": (255, 196, 150), "glow": (255, 150, 108)},
}


def gear_style(set_key):
    return GEAR_STYLE.get(set_key, GEAR_STYLE["forest"])


def player_sprite(armor, head, weapon_type=WEAPON_SWORD, set_key="forest",
                  pants=(46, 54, 84), boots=(92, 64, 40), skin=SKIN_COLOR):
    body = PLAYER_BODIES.get(weapon_type, PLAYER_BODY)
    style = gear_style(set_key)
    mantle = _blend(style["cloak"], armor, 0.3)
    trim = _blend(style["trim"], armor, 0.45)
    rune = style["rune"]
    palette = {
        "h": head, "s": skin, "e": (26, 22, 34), "a": armor,
        "b": _shade(skin, 0.92), "p": pants, "l": boots,
        "t": trim, "r": rune, "m": mantle, "c": _light(trim, 0.28),
    }
    return sprite(f"player:{weapon_type}:{set_key}", body, palette, PLAYER_SCALE)


def draw_player_hat(screen, x, y, weapon_type, color):
    """在头顶画职业头饰（x,y 是小人左上角，宽 36）。"""
    cx = x + 18
    if weapon_type == WEAPON_STAFF:
        # 露出脸部的尖顶巫师帽
        pygame.draw.polygon(screen, _shade(color, 0.75),
                            [(cx, y - 14), (cx - 11, y + 5), (cx + 11, y + 5)])
        pygame.draw.polygon(screen, color, [(cx, y - 14), (cx - 8, y + 4), (cx + 9, y + 4)])
        pygame.draw.polygon(screen, _light(color, 0.3), [(cx - 1, y - 12), (cx - 4, y + 2), (cx + 2, y + 2)])
        pygame.draw.rect(screen, _shade(color, 0.6), (cx - 14, y + 3, 28, 4))
        pygame.draw.rect(screen, color, (cx - 11, y + 4, 22, 3))
        pygame.draw.rect(screen, (255, 230, 140), (cx - 4, y - 5, 8, 3))
    elif weapon_type == WEAPON_BOW:
        # 游侠兜帽 + 羽饰，脸部更清楚
        pygame.draw.polygon(screen, _shade(color, 0.72),
                            [(cx - 12, y + 9), (cx - 8, y - 2), (cx, y - 11),
                             (cx + 10, y - 1), (cx + 12, y + 9)])
        pygame.draw.polygon(screen, color,
                            [(cx - 10, y + 8), (cx - 6, y), (cx, y - 8),
                             (cx + 8, y), (cx + 10, y + 8)])
        pygame.draw.rect(screen, _shade(color, 0.58), (cx - 11, y + 8, 22, 3))
        pygame.draw.line(screen, _light(color, 0.35), (cx + 3, y - 5), (cx + 8, y + 4), 2)
        pygame.draw.line(screen, (188, 245, 210), (cx + 8, y - 9), (cx + 12, y - 1), 2)
        pygame.draw.line(screen, (236, 255, 210), (cx + 10, y - 8), (cx + 14, y - 2), 1)
    else:
        # 战士：盔缨
        pygame.draw.rect(screen, _shade(color, 0.7), (cx - 12, y - 2, 24, 8))
        pygame.draw.rect(screen, color, (cx - 12, y - 3, 24, 7))
        pygame.draw.rect(screen, _light(color, 0.5), (cx - 12, y - 3, 24, 2))
        pygame.draw.polygon(screen, (240, 96, 112), [(cx, y - 13), (cx + 5, y - 3), (cx - 5, y - 3)])
        pygame.draw.polygon(screen, (255, 170, 180), [(cx, y - 13), (cx + 2, y - 5), (cx - 1, y - 5)])


PET_PALETTE = {
    "o": (18, 52, 48), "#": (120, 240, 200), "+": (210, 255, 240),
    "e": (250, 255, 255), "p": (20, 70, 62),
}


def pet_sprite(scale=3, flip=False, color=None):
    if color is None:
        return sprite("pet", PET, PET_PALETTE, scale, flip)
    palette = dict(PET_PALETTE)
    palette["#"] = color
    palette["+"] = _light(color, 0.55)
    palette["o"] = _shade(color, 0.24)
    return sprite(f"pet:{color}", PET, palette, scale, flip)


def draw_crown(screen, cx, top_y, t):
    """精英/BOSS 小王冠。"""
    bob = int(math.sin(t * 3) * 1)
    y = top_y + bob
    pygame.draw.rect(screen, (255, 196, 40), (cx - 9, y, 18, 5))
    for dx in (-9, 0, 9):
        pygame.draw.rect(screen, (255, 226, 120), (cx + dx - 2, y - 4, 4, 4))
    pygame.draw.rect(screen, (160, 96, 0), (cx - 9, y + 4, 18, 2))


# --------------------------------------------------------------------------
# 掉落物图标
# --------------------------------------------------------------------------
ITEM_BOX = 36


def _sword_icon(screen, x, y, col):
    dark = _shade(col, 0.55)
    pygame.draw.polygon(screen, dark, [(x + 12, y + 4), (x + 18, y + 4), (x + 21, y + 8),
                                       (x + 21, y + 22), (x + 9, y + 22), (x + 9, y + 8)])
    pygame.draw.rect(screen, col, (x + 13, y + 3, 4, 21))
    pygame.draw.rect(screen, _light(col, 0.55), (x + 13, y + 3, 2, 19))
    # 护手与握把
    pygame.draw.rect(screen, (206, 158, 54), (x + 6, y + 24, 16, 4))
    pygame.draw.rect(screen, (120, 72, 32), (x + 12, y + 28, 5, 7))
    pygame.draw.rect(screen, (206, 158, 54), (x + 10, y + 34, 9, 3))


def _bow_icon(screen, x, y, col):
    wood = (168, 116, 62)
    pygame.draw.lines(screen, _shade(wood, 0.7), False,
                      [(x + 10, y + 3), (x + 18, y + 9), (x + 20, y + 17),
                       (x + 18, y + 25), (x + 10, y + 31)], 4)
    pygame.draw.lines(screen, wood, False,
                      [(x + 10, y + 3), (x + 18, y + 9), (x + 20, y + 17),
                       (x + 18, y + 25), (x + 10, y + 31)], 2)
    pygame.draw.line(screen, (232, 232, 240), (x + 10, y + 4), (x + 10, y + 30), 1)
    # 搭在弦上的箭
    pygame.draw.rect(screen, col, (x + 8, y + 16, 16, 2))
    pygame.draw.polygon(screen, _light(col, 0.4), [(x + 24, y + 13), (x + 30, y + 17), (x + 24, y + 21)])


def _staff_icon(screen, x, y, col):
    pygame.draw.rect(screen, (118, 74, 40), (x + 15, y + 8, 5, 26))
    pygame.draw.rect(screen, (86, 52, 26), (x + 15, y + 8, 2, 26))
    pygame.draw.circle(screen, _shade(col, 0.6), (x + 17, y + 9), 9)
    pygame.draw.circle(screen, col, (x + 17, y + 9), 7)
    pygame.draw.circle(screen, _light(col, 0.6), (x + 14, y + 6), 3)


def _armor_icon(screen, x, y, col):
    dark = _shade(col, 0.6)
    pygame.draw.rect(screen, dark, (x + 7, y + 7, 22, 23))
    pygame.draw.rect(screen, col, (x + 8, y + 8, 20, 20))
    pygame.draw.rect(screen, _light(col, 0.4), (x + 8, y + 8, 20, 4))
    pygame.draw.rect(screen, col, (x + 3, y + 9, 6, 11))
    pygame.draw.rect(screen, col, (x + 27, y + 9, 6, 11))
    pygame.draw.rect(screen, dark, (x + 16, y + 12, 4, 16))


def _helmet_icon(screen, x, y, col):
    dark = _shade(col, 0.6)
    pygame.draw.rect(screen, dark, (x + 6, y + 7, 24, 15))
    pygame.draw.rect(screen, col, (x + 7, y + 8, 22, 13))
    pygame.draw.rect(screen, col, (x + 9, y + 3, 18, 6))
    pygame.draw.rect(screen, _light(col, 0.5), (x + 11, y + 4, 6, 3))
    pygame.draw.rect(screen, (24, 22, 30), (x + 10, y + 13, 16, 4))
    pygame.draw.rect(screen, dark, (x + 8, y + 22, 20, 3))


def _boots_icon(screen, x, y, col):
    dark = _shade(col, 0.6)
    pygame.draw.rect(screen, dark, (x + 9, y + 5, 14, 19))
    pygame.draw.rect(screen, col, (x + 10, y + 6, 12, 17))
    pygame.draw.rect(screen, col, (x + 10, y + 21, 19, 8))
    pygame.draw.rect(screen, dark, (x + 10, y + 29, 19, 3))
    pygame.draw.rect(screen, _light(col, 0.45), (x + 12, y + 8, 3, 11))
    pygame.draw.rect(screen, _light(col, 0.2), (x + 12, y + 22, 15, 2))


def _pants_icon(screen, x, y, col):
    dark = _shade(col, 0.6)
    pygame.draw.rect(screen, col, (x + 8, y + 4, 20, 8))      # 腰带
    pygame.draw.rect(screen, col, (x + 8, y + 10, 8, 20))     # 左裤腿
    pygame.draw.rect(screen, col, (x + 20, y + 10, 8, 20))    # 右裤腿
    pygame.draw.rect(screen, _light(col, 0.4), (x + 9, y + 5, 18, 3))
    pygame.draw.rect(screen, dark, (x + 8, y + 28, 8, 2))
    pygame.draw.rect(screen, dark, (x + 20, y + 28, 8, 2))


def _bracelet_icon(screen, x, y, col):
    pygame.draw.circle(screen, _shade(col, 0.55), (x + 18, y + 19), 12, 5)
    pygame.draw.circle(screen, col, (x + 18, y + 19), 11, 3)
    pygame.draw.circle(screen, _light(col, 0.55), (x + 18, y + 8), 4)
    pygame.draw.circle(screen, (255, 255, 255), (x + 17, y + 7), 2)


def _gear_series_overlay(screen, x, y, set_key, color, kind, weapon_type=None):
    if set_key == "forest":
        pygame.draw.line(screen, _shade(color, 0.7), (x + 6, y + 30), (x + 12, y + 10), 2)
        pygame.draw.polygon(screen, _light(color, 0.35), [(x + 12, y + 10), (x + 16, y + 6), (x + 18, y + 12)])
        pygame.draw.polygon(screen, color, [(x + 8, y + 20), (x + 4, y + 16), (x + 10, y + 14)])
    elif set_key == "ocean":
        pygame.draw.arc(screen, _light(color, 0.35), (x + 4, y + 10, 20, 12), 0.2, 2.9, 2)
        pygame.draw.circle(screen, (235, 250, 255), (x + 25, y + 9), 2)
        pygame.draw.circle(screen, color, (x + 28, y + 14), 3, 1)
    elif set_key == "sky":
        pygame.draw.line(screen, _light(color, 0.4), (x + 8, y + 24), (x + 18, y + 12), 2)
        pygame.draw.line(screen, _light(color, 0.4), (x + 18, y + 12), (x + 28, y + 24), 2)
        pygame.draw.circle(screen, (255, 244, 214), (x + 18, y + 11), 2)
    elif set_key == "volcano":
        pygame.draw.line(screen, _shade(color, 0.78), (x + 7, y + 29), (x + 15, y + 18), 2)
        pygame.draw.line(screen, _shade(color, 0.78), (x + 15, y + 18), (x + 24, y + 29), 2)
        pygame.draw.circle(screen, (255, 214, 150), (x + 18, y + 10), 2)
        pygame.draw.circle(screen, color, (x + 22, y + 7), 2)
    if kind == "weapon" and weapon_type == WEAPON_STAFF:
        pygame.draw.circle(screen, (255, 255, 255), (x + 18, y + 6), 1)
    elif kind == "bracelet":
        pygame.draw.circle(screen, (255, 255, 255), (x + 18, y + 19), 1)


def _key_icon(screen, x, y, t):
    gold, dark = (255, 214, 64), (156, 108, 12)
    bob = int(math.sin(t * 4) * 1)
    y += bob
    pygame.draw.circle(screen, dark, (x + 11, y + 11), 8)
    pygame.draw.circle(screen, gold, (x + 11, y + 11), 6)
    pygame.draw.circle(screen, (60, 40, 10), (x + 11, y + 11), 2)
    pygame.draw.rect(screen, gold, (x + 17, y + 9, 12, 4))
    pygame.draw.rect(screen, gold, (x + 25, y + 13, 4, 6))
    pygame.draw.rect(screen, gold, (x + 19, y + 13, 4, 5))


def _chest_icon(screen, x, y, t):
    glow = 0.5 + 0.5 * math.sin(t * 3)
    blit_glow(screen, x + 18, y + 18, 26, (255, 200, 60), int(40 + 40 * glow))
    pygame.draw.rect(screen, (92, 54, 24), (x + 4, y + 14, 28, 18))
    pygame.draw.rect(screen, (146, 92, 42), (x + 5, y + 15, 26, 16))
    pygame.draw.rect(screen, (116, 68, 30), (x + 3, y + 6, 30, 10))
    pygame.draw.rect(screen, (168, 108, 52), (x + 4, y + 7, 28, 8))
    pygame.draw.rect(screen, (255, 214, 64), (x + 4, y + 13, 28, 3))
    pygame.draw.rect(screen, (255, 214, 64), (x + 16, y + 12, 4, 10))
    pygame.draw.rect(screen, (255, 244, 180), (x + 17, y + 16, 2, 3))


def _potion_icon(screen, x, y, color, t):
    pulse = 0.5 + 0.5 * math.sin(t * 4)
    blit_glow(screen, x + 18, y + 20, 20, color, int(30 + 25 * pulse))
    pygame.draw.rect(screen, (150, 112, 64), (x + 12, y + 1, 12, 5))     # 木塞
    pygame.draw.rect(screen, (214, 226, 236), (x + 12, y + 6, 12, 6))    # 瓶颈
    pygame.draw.rect(screen, (198, 212, 224), (x + 10, y + 11, 16, 22))  # 瓶身
    pygame.draw.rect(screen, color, (x + 11, y + 19, 14, 13))            # 液体
    pygame.draw.rect(screen, _light(color, 0.45), (x + 12, y + 20, 5, 4))
    pygame.draw.rect(screen, (255, 255, 255), (x + 12, y + 13, 3, 12))   # 高光
    pygame.draw.rect(screen, (120, 132, 146), (x + 10, y + 30, 16, 3))   # 瓶底


def _bomb_icon(screen, x, y, t):
    pulse = 0.5 + 0.5 * math.sin(t * 8)
    blit_glow(screen, x + 18, y + 22, 20, (255, 140, 60), int(40 + 50 * pulse))
    pygame.draw.circle(screen, (16, 16, 22), (x + 18, y + 22), 13)
    pygame.draw.circle(screen, (52, 52, 66), (x + 18, y + 22), 11)
    pygame.draw.circle(screen, (92, 92, 110), (x + 14, y + 18), 4)
    pygame.draw.circle(screen, (130, 130, 150), (x + 13, y + 17), 2)
    pygame.draw.rect(screen, (120, 92, 60), (x + 20, y + 6, 4, 8))
    pygame.draw.line(screen, (200, 170, 90), (x + 22, y + 6), (x + 27, y + 1), 2)
    pygame.draw.circle(screen, (255, 220, 120), (x + 27, y + 1), int(2 + 2 * pulse))
    pygame.draw.circle(screen, (255, 250, 220), (x + 27, y + 1), 1)


def draw_item_icon(screen, x, y, kind, quality, weapon_type, t, set_color=None, set_key=None):
    """在 (x, y) 处画 36x36 的掉落物图标。"""
    color = Q_COLOR.get(quality, (235, 235, 235))
    if set_key and not set_color:
        set_color = GEAR_SETS.get(set_key, GEAR_SETS["forest"]).get("color")
    gear_kind = kind in ("weapon", "armor", "boots", "pants", "bracelet", "helmet")
    if gear_kind and set_color:
        color = _blend(color, set_color, 0.68 if quality == Q_WHITE else 0.35)
    if kind == "weapon":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 60)
        if weapon_type == WEAPON_BOW:
            _bow_icon(screen, x, y, color)
        elif weapon_type == WEAPON_STAFF:
            _staff_icon(screen, x, y, color)
        else:
            _sword_icon(screen, x, y, color)
    elif kind == "armor":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 55)
        _armor_icon(screen, x, y, color)
    elif kind == "boots":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 55)
        _boots_icon(screen, x, y, color)
    elif kind == "pants":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 55)
        _pants_icon(screen, x, y, color)
    elif kind == "bracelet":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 60)
        _bracelet_icon(screen, x, y, color)
    elif kind == "helmet":
        if quality != Q_WHITE:
            blit_glow(screen, x + 18, y + 18, 24, color, 55)
        _helmet_icon(screen, x, y, color)
    elif kind == "potion_speed":
        _potion_icon(screen, x, y, (255, 206, 76), t)
        for i in range(2):
            ly = y + 14 + i * 9
            pygame.draw.rect(screen, (255, 240, 190), (x + 2 + i * 2, ly, 5, 2))
        _ = quality
    elif kind == "bomb":
        _bomb_icon(screen, x, y, t)
    elif kind == "potion_hp":
        _potion_icon(screen, x, y, (232, 68, 84), t)
    elif kind == "potion_energy":
        _potion_icon(screen, x, y, (78, 168, 252), t)
    elif kind == "key":
        _key_icon(screen, x, y, t)
    elif kind == "chest":
        _chest_icon(screen, x, y, t)

    if gear_kind and set_key:
        _gear_series_overlay(screen, x, y, set_key, set_color or color, kind, weapon_type)

    # 套装标记：右上角一颗小宝石
    if set_color and kind in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
        pygame.draw.circle(screen, _shade(set_color, 0.5), (x + 29, y + 7), 5)
        pygame.draw.circle(screen, set_color, (x + 29, y + 7), 4)
        pygame.draw.circle(screen, (255, 255, 255), (x + 28, y + 6), 1)


# --------------------------------------------------------------------------
# 地图地格
# --------------------------------------------------------------------------
CAVE_FLOOR_A = (34, 29, 45)
CAVE_FLOOR_B = (37, 32, 49)
GRASS_FLOOR_A = (55, 143, 65)
GRASS_FLOOR_B = (58, 147, 68)

# 主题配色：地板 A/B、墙顶/墙身/描边、点缀色
THEME_COLORS = {
    "forest": {
        "floor": ((40, 52, 38), (44, 57, 42)),
        "wall": ((116, 132, 92), (88, 104, 72), (44, 56, 36)),
    },
    "ocean": {
        "floor": ((22, 52, 78), (26, 60, 88)),
        "wall": ((94, 148, 168), (70, 116, 138), (24, 52, 70)),
    },
    "sky": {
        "floor": ((86, 100, 138), (94, 108, 148)),
        "wall": ((206, 214, 246), (168, 178, 216), (86, 96, 132)),
    },
    "volcano": {
        "floor": ((54, 28, 26), (62, 32, 28)),
        "wall": ((122, 76, 66), (96, 58, 52), (48, 24, 22)),
    },
}


def _noise(*nums):
    h = 2166136261
    for n in nums:
        h = ((h ^ (int(n) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return (h % 100000) / 100000.0


def paint_floor(surf, x, y, r, c, level_idx):
    theme = level_theme(level_idx)
    grass = theme == "forest"
    base, alt = THEME_COLORS[theme]["floor"]
    n = _noise(r, c, level_idx)
    surf.fill(base, (x, y, TILE_SIZE, TILE_SIZE))
    surf.fill(_light(base, 0.08), (x, y, TILE_SIZE, 4))
    surf.fill(_shade(base, 0.84), (x, y + TILE_SIZE - 5, TILE_SIZE, 5))
    surf.fill(_shade(base, 0.9), (x, y, 3, TILE_SIZE))
    surf.fill(_shade(base, 0.94), (x + TILE_SIZE - 2, y, 2, TILE_SIZE))
    center = pygame.Rect(x + 6, y + 6, TILE_SIZE - 12, TILE_SIZE - 12)
    pygame.draw.rect(surf, _light(base, 0.04), center, 1)

    if grass:
        # 不规则色斑（画成小块而不是整格，避免出现棋盘格子感）
        for i in range(3):
            px = x + int(_noise(r, c, i, 31) * (TILE_SIZE - 14))
            py = y + int(_noise(r, c, i, 41) * (TILE_SIZE - 10))
            shade = alt if i % 2 == 0 else _shade(base, 0.94)
            surf.fill(shade, (px, py, 12, 8))
        if n > 0.48:
            pygame.draw.line(surf, (62, 124, 70), (x + 8, y + 29), (x + 16, y + 15), 1)
            pygame.draw.line(surf, (86, 156, 92), (x + 18, y + 31), (x + 25, y + 18), 1)
        # 草叶
        for i in range(3):
            gx = x + int(_noise(r, c, i, 11) * (TILE_SIZE - 6)) + 3
            gy = y + int(_noise(r, c, i, 22) * (TILE_SIZE - 8)) + 4
            pygame.draw.rect(surf, _shade(base, 0.82), (gx, gy, 2, 5))
            pygame.draw.rect(surf, _light(base, 0.12), (gx + 2, gy + 1, 2, 4))
        if n > 0.88:
            fx = x + int(_noise(r, c, 33) * (TILE_SIZE - 10)) + 5
            fy = y + int(_noise(r, c, 44) * (TILE_SIZE - 10)) + 5
            pygame.draw.rect(surf, (250, 240, 150), (fx, fy, 3, 3))
            pygame.draw.rect(surf, (255, 255, 255), (fx + 1, fy + 1, 1, 1))
    elif theme == "ocean":
        surf.fill(alt if n < 0.3 else base, (x, y, TILE_SIZE, TILE_SIZE))
        # 水波光斑
        if n > 0.6:
            wx = x + int(_noise(r, c, 71) * 24) + 6
            wy = y + int(_noise(r, c, 72) * 24) + 6
            pygame.draw.arc(surf, (90, 160, 200), (wx, wy, 14, 8), 0.2, 2.9, 1)
        if n > 0.42:
            pygame.draw.arc(surf, (74, 136, 182), (x + 5, y + 12, 22, 12), 0.1, 2.6, 1)
            pygame.draw.arc(surf, (132, 198, 226), (x + 10, y + 22, 16, 8), 0.1, 2.8, 1)
        if n > 0.93:
            bx = x + int(_noise(r, c, 73) * 20) + 8
            by = y + int(_noise(r, c, 74) * 20) + 8
            pygame.draw.circle(surf, (150, 210, 235), (bx, by), 2, 1)
    elif theme == "sky":
        surf.fill(alt if n < 0.35 else base, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.line(surf, (134, 146, 188), (x + 6, y + 30), (x + 18, y + 14), 1)
        if n > 0.55:
            cx = x + int(_noise(r, c, 81) * 20) + 8
            cy = y + int(_noise(r, c, 82) * 20) + 8
            pygame.draw.rect(surf, (120, 132, 170), (cx, cy, 12, 3))
            pygame.draw.rect(surf, (108, 120, 158), (cx + 4, cy - 3, 8, 3))
        if n > 0.9:
            sx = x + int(_noise(r, c, 83) * 28) + 5
            sy = y + int(_noise(r, c, 84) * 28) + 5
            pygame.draw.rect(surf, (235, 240, 255), (sx, sy, 2, 2))
    elif theme == "volcano":
        surf.fill(alt if n < 0.35 else base, (x, y, TILE_SIZE, TILE_SIZE))
        pygame.draw.line(surf, (98, 42, 34), (x + 8, y + 10), (x + 18, y + 22), 1)
        pygame.draw.line(surf, (158, 72, 46), (x + 17, y + 22), (x + 28, y + 13), 1)
        if n > 0.55:
            lx = x + int(_noise(r, c, 91) * 18) + 8
            ly = y + int(_noise(r, c, 92) * 18) + 8
            pygame.draw.lines(surf, (170, 70, 40), False,
                              [(lx, ly), (lx + 6, ly + 4), (lx + 3, ly + 9), (lx + 10, ly + 12)], 2)
            pygame.draw.line(surf, (255, 190, 90), (lx + 1, ly + 1), (lx + 5, ly + 5), 1)
        if n > 0.92:
            ex = x + int(_noise(r, c, 93) * 26) + 6
            ey = y + int(_noise(r, c, 94) * 26) + 6
            pygame.draw.rect(surf, (255, 150, 60), (ex, ey, 2, 2))
    else:
        surf.fill(alt if n < 0.3 else base, (x, y, TILE_SIZE, TILE_SIZE))
        # 石板裂纹与小石子
        for i in range(2):
            gx = x + int(_noise(r, c, i, 7) * (TILE_SIZE - 8)) + 4
            gy = y + int(_noise(r, c, i, 9) * (TILE_SIZE - 8)) + 4
            pygame.draw.rect(surf, _shade(base, 0.72), (gx, gy, 3, 2))
        if n > 0.9:
            gx = x + int(_noise(r, c, 55) * 24) + 8
            gy = y + int(_noise(r, c, 66) * 24) + 8
            pygame.draw.lines(surf, _shade(base, 0.7), False,
                              [(gx, gy), (gx + 4, gy + 3), (gx + 2, gy + 7)], 1)


def paint_low_wall(surf, x, y, r, c, level_idx):
    """矮墙：只有半格高，跳起来就能过去。"""
    paint_floor(surf, x, y, r, c, level_idx)
    theme = level_theme(level_idx)
    base = {
        "forest": (110, 132, 92), "ocean": (96, 150, 170),
        "sky": (176, 186, 220), "volcano": (130, 84, 70),
    }.get(theme, (104, 104, 128))
    pygame.draw.rect(surf, _shade(base, 0.55), (x, y + 15, TILE_SIZE, TILE_SIZE - 15))
    pygame.draw.rect(surf, base, (x + 1, y + 16, TILE_SIZE - 2, TILE_SIZE - 18))
    pygame.draw.rect(surf, _light(base, 0.3), (x + 1, y + 16, TILE_SIZE - 2, 5))
    pygame.draw.rect(surf, _shade(base, 0.6), (x + 1, y + TILE_SIZE - 5, TILE_SIZE - 2, 4))
    for i in range(2):
        bx = x + 6 + i * 16
        pygame.draw.rect(surf, _shade(base, 0.75), (bx, y + 23, 7, 5))


def paint_platform(surf, x, y, r, c, level_idx):
    """悬空平台：跳上去可以站着，看起来比矮墙高一截。"""
    paint_floor(surf, x, y, r, c, level_idx)
    base = {
        "forest": (92, 122, 90), "ocean": (100, 156, 176),
        "sky": (190, 200, 230), "volcano": (140, 90, 76),
    }.get(level_theme(level_idx), (96, 100, 134))
    # 下方阴影
    shadow = pygame.Surface((TILE_SIZE, 10), pygame.SRCALPHA)
    for i in range(10):
        shadow.fill((0, 0, 0, int(80 * (1 - i / 10))), (0, i, TILE_SIZE, 1))
    surf.blit(shadow, (x, y + 34))
    pygame.draw.rect(surf, _shade(base, 0.55), (x, y + 16, TILE_SIZE, 22))
    pygame.draw.rect(surf, base, (x, y + 18, TILE_SIZE, 18))
    pygame.draw.rect(surf, _light(base, 0.32), (x, y + 14, TILE_SIZE, 6))
    pygame.draw.rect(surf, _light(base, 0.12), (x, y + 18, TILE_SIZE, 3))
    pygame.draw.rect(surf, _shade(base, 0.4), (x, y + 16, TILE_SIZE, 22), 1)
    for i in range(2):
        pygame.draw.rect(surf, _shade(base, 0.7), (x + 6 + i * 15, y + 25, 8, 4))


def paint_spike(surf, x, y, r, c, level_idx):
    paint_floor(surf, x, y, r, c, level_idx)
    pygame.draw.rect(surf, (54, 52, 62), (x + 2, y + 32, TILE_SIZE - 4, 6))
    for i in range(4):
        sx = x + 3 + i * 9
        pygame.draw.polygon(surf, (198, 204, 218), [(sx, y + 34), (sx + 4, y + 14), (sx + 9, y + 34)])
        pygame.draw.polygon(surf, (126, 132, 148), [(sx + 4, y + 14), (sx + 9, y + 34), (sx + 5, y + 34)])
        pygame.draw.line(surf, (240, 246, 255), (sx + 4, y + 16), (sx + 4, y + 30), 1)


def paint_crate(surf, x, y, r, c, level_idx):
    paint_floor(surf, x, y, r, c, level_idx)
    pygame.draw.rect(surf, (70, 44, 22), (x + 4, y + 6, 32, 32))
    pygame.draw.rect(surf, (156, 108, 58), (x + 5, y + 7, 30, 30))
    pygame.draw.rect(surf, (186, 134, 76), (x + 5, y + 7, 30, 8))
    pygame.draw.line(surf, (110, 70, 34), (x + 5, y + 8), (x + 34, y + 36), 3)
    pygame.draw.line(surf, (110, 70, 34), (x + 34, y + 8), (x + 5, y + 36), 3)
    pygame.draw.rect(surf, (96, 60, 30), (x + 4, y + 6, 32, 32), 2)


def paint_wall(surf, x, y, r, c, level_idx):
    theme = level_theme(level_idx)
    grass = theme == "forest"
    top, body, edge = THEME_COLORS[theme]["wall"]

    surf.fill(body, (x, y, TILE_SIZE, TILE_SIZE))
    # 顶面高光 + 底部阴影，做出立体砖块感
    surf.fill(top, (x, y, TILE_SIZE, 7))
    surf.fill(_light(top, 0.18), (x, y, TILE_SIZE, 3))
    surf.fill(_shade(body, 0.72), (x, y + TILE_SIZE - 6, TILE_SIZE, 6))
    surf.fill(_light(body, 0.1), (x, y, 3, TILE_SIZE))
    surf.fill(_shade(body, 0.8), (x + TILE_SIZE - 3, y, 3, TILE_SIZE))
    pygame.draw.rect(surf, edge, (x, y, TILE_SIZE, TILE_SIZE), 1)

    n = _noise(r, c, level_idx, 3)
    if n > 0.55:
        rx = x + int(_noise(r, c, 5) * 22) + 8
        ry = y + int(_noise(r, c, 6) * 18) + 10
        pygame.draw.rect(surf, _shade(body, 0.62), (rx, ry, 5, 4))
        pygame.draw.rect(surf, _light(body, 0.2), (rx + 4, ry, 3, 2))
    if n > 0.4:
        pygame.draw.line(surf, _shade(edge, 0.9), (x + 8, y + 11), (x + 18, y + 20), 1)
        pygame.draw.line(surf, _light(top, 0.12), (x + 18, y + 20), (x + 28, y + 13), 1)
    if grass and n > 0.7:
        pygame.draw.rect(surf, (96, 150, 80), (x + 6, y + 2, 8, 4))
    elif theme == "ocean" and n > 0.65:
        pygame.draw.rect(surf, (70, 170, 160), (x + 5, y + 2, 9, 5))
        pygame.draw.rect(surf, (110, 210, 190), (x + 7, y + 3, 4, 3))
    elif theme == "sky" and n > 0.7:
        pygame.draw.rect(surf, (235, 240, 255), (x + 4, y + 1, 12, 4))
    elif theme == "volcano" and n > 0.7:
        pygame.draw.rect(surf, (190, 80, 44), (x + 6, y + 2, 10, 3))


def paint_map(surface, map_rows, level_idx):
    """把静态地形（地板 + 墙 + 装饰）一次性画进大 Surface。"""
    rows, cols = len(map_rows), len(map_rows[0])
    for r in range(rows):
        for c in range(cols):
            x, y = c * TILE_SIZE, r * TILE_SIZE
            char = map_rows[r][c]
            if char == "1":
                paint_wall(surface, x, y, r, c, level_idx)
            elif char == "6":
                paint_low_wall(surface, x, y, r, c, level_idx)
            elif char == "7":
                paint_platform(surface, x, y, r, c, level_idx)
            elif char == "8":
                paint_spike(surface, x, y, r, c, level_idx)
            elif char == "9":
                paint_crate(surface, x, y, r, c, level_idx)
            else:
                paint_floor(surface, x, y, r, c, level_idx)

    # 墙脚投影：让墙看起来是“立起来”的
    shadow = pygame.Surface((TILE_SIZE, 8), pygame.SRCALPHA)
    for i in range(8):
        shadow.fill((0, 0, 0, int(70 * (1 - i / 8))), (0, i, TILE_SIZE, 1))
    for r in range(rows):
        for c in range(cols):
            if map_rows[r][c] == "1" and r + 1 < rows and map_rows[r + 1][c] not in ("1", "6"):
                surface.blit(shadow, (c * TILE_SIZE, (r + 1) * TILE_SIZE))

    _decorate(surface, map_rows, level_idx)
    return surface


def _decorate(surface, map_rows, level_idx):
    rows, cols = len(map_rows), len(map_rows[0])
    theme = level_theme(level_idx)
    grass = theme == "forest"
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if map_rows[r][c] in ("1", "6", "7", "8", "9"):
                continue
            x, y = c * TILE_SIZE, r * TILE_SIZE
            n = _noise(r, c, 91)
            neighbors = (map_rows[r - 1][c], map_rows[r + 1][c],
                         map_rows[r][c - 1], map_rows[r][c + 1])
            wall_below = neighbors[1] == "1"

            if theme == "ocean":
                if n > 0.96:
                    # 珊瑚
                    for i, col in enumerate([(230, 110, 140), (255, 150, 170)]):
                        bx = x + 10 + i * 10
                        pygame.draw.rect(surface, col, (bx, y + 18, 3, 12))
                        pygame.draw.rect(surface, col, (bx - 4, y + 20, 4, 3))
                        pygame.draw.rect(surface, col, (bx + 3, y + 24, 4, 3))
                elif n > 0.92:
                    # 海草
                    for i in range(3):
                        gx = x + 12 + i * 6
                        pygame.draw.lines(surface, (70, 170, 120), False,
                                          [(gx, y + 32), (gx + 2, y + 24), (gx, y + 16)], 2)
                elif n > 0.88:
                    # 气泡
                    blit_glow(surface, x + 20, y + 18, 10, (150, 220, 255), 50)
                    pygame.draw.circle(surface, (190, 240, 255), (x + 20, y + 18), 3, 1)
                continue

            if theme == "sky":
                if n > 0.95:
                    # 云团
                    for i in range(3):
                        pygame.draw.ellipse(surface, (225, 232, 252),
                                            (x + 6 + i * 8, y + 18 + (i % 2) * 4, 16, 8))
                elif n > 0.9:
                    # 星星
                    sx, sy = x + 18, y + 18
                    pygame.draw.line(surface, (255, 246, 200), (sx - 3, sy), (sx + 3, sy), 1)
                    pygame.draw.line(surface, (255, 246, 200), (sx, sy - 3), (sx, sy + 3), 1)
                elif n > 0.86:
                    pygame.draw.circle(surface, (245, 250, 255), (x + 20, y + 22), 2)
                continue

            if theme == "volcano":
                if n > 0.96:
                    # 岩浆池
                    pygame.draw.ellipse(surface, (120, 40, 20), (x + 8, y + 20, 24, 12))
                    pygame.draw.ellipse(surface, (255, 120, 40), (x + 10, y + 22, 20, 8))
                    pygame.draw.ellipse(surface, (255, 210, 110), (x + 14, y + 24, 10, 4))
                    blit_glow(surface, x + 20, y + 26, 26, (255, 130, 50), 55)
                elif n > 0.92:
                    # 余烬
                    ex, ey = x + 18, y + 20
                    pygame.draw.rect(surface, (255, 170, 80), (ex, ey, 2, 2))
                    blit_glow(surface, ex, ey, 10, (255, 140, 60), 45)
                continue

            if not grass:
                if wall_below and n > 0.972:
                    # 墙边火把
                    tx, ty = x + TILE_SIZE // 2, y + TILE_SIZE - 16
                    blit_glow(surface, tx, ty, 58, (255, 168, 70), 58)
                    pygame.draw.rect(surface, (92, 62, 34), (tx - 2, ty + 6, 4, 7))
                    pygame.draw.rect(surface, (255, 140, 40), (tx - 3, ty - 2, 6, 8))
                    pygame.draw.rect(surface, (255, 214, 90), (tx - 1, ty - 1, 3, 5))
                    pygame.draw.rect(surface, (255, 250, 220), (tx, ty + 1, 1, 2))
                elif n > 0.958:
                    # 骨头
                    pygame.draw.rect(surface, (198, 196, 184), (x + 12, y + 22, 12, 3))
                    pygame.draw.rect(surface, (198, 196, 184), (x + 10, y + 20, 3, 3))
                    pygame.draw.rect(surface, (198, 196, 184), (x + 23, y + 24, 3, 3))
                elif n > 0.942:
                    # 发光蘑菇
                    pygame.draw.rect(surface, (206, 214, 226), (x + 17, y + 26, 4, 6))
                    pygame.draw.rect(surface, (86, 196, 220), (x + 13, y + 21, 12, 6))
                    pygame.draw.rect(surface, (170, 240, 255), (x + 15, y + 22, 3, 2))
                    blit_glow(surface, x + 19, y + 24, 20, (90, 210, 235), 40)
                elif n > 0.928:
                    # 水晶簇
                    pygame.draw.polygon(surface, (120, 190, 255),
                                        [(x + 18, y + 18), (x + 24, y + 30), (x + 12, y + 30)])
                    pygame.draw.polygon(surface, (190, 230, 255),
                                        [(x + 18, y + 18), (x + 22, y + 28), (x + 18, y + 28)])
                    blit_glow(surface, x + 18, y + 26, 22, (90, 170, 255), 42)
            else:
                if n > 0.96:
                    # 花丛
                    for i, col in enumerate([(250, 240, 160), (255, 180, 210), (240, 240, 255)]):
                        fx = x + 10 + i * 8
                        fy = y + 20 + (i % 2) * 6
                        pygame.draw.rect(surface, (48, 118, 54), (fx + 1, fy + 3, 1, 5))
                        pygame.draw.rect(surface, col, (fx, fy, 4, 4))
                elif n > 0.93:
                    # 灌木
                    pygame.draw.rect(surface, (40, 110, 48), (x + 12, y + 22, 16, 10))
                    pygame.draw.rect(surface, (52, 132, 58), (x + 14, y + 20, 12, 8))
                    pygame.draw.rect(surface, (66, 152, 72), (x + 16, y + 19, 6, 4))


# --------------------------------------------------------------------------
# 技能 / 特效
# --------------------------------------------------------------------------
def tint(surf, color=(120, 200, 255, 150)):
    """给精灵套一层颜色剪影（冰冻/中毒等状态）。"""
    key = ("tint", id(surf), color)
    out = _sprite_cache.get(key)
    if out is None:
        out = surf.copy()
        mask = pygame.mask.from_surface(surf)
        out.blit(mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0)), (0, 0))
        _sprite_cache[key] = out
    return out


_fonts = {}
_labels = {}
_font_family = None
_FONT_CANDIDATES = (
    "hiraginosansgb",      # macOS：Hiragino Sans GB，汉字覆盖完整
    "pingfangsc", "pingfang",
    "microsoftyahei", "msyh",
    "notosanscjksc", "notosanscjk",
    "stheitimedium", "wenquanyimicrohei", "simhei",
)
# 这几个字在部分字体里会缺字（PingFang 经 SDL_ttf 加载时就缺“敌/远/鉴”）
_COVERAGE_PROBE = "敌远鉴技能冰霜旋风箭雨"


def _resolve_font_family():
    """挑一个既存在、又能完整显示游戏汉字的字体。"""
    global _font_family
    if _font_family is not None:
        return _font_family
    for name in _FONT_CANDIDATES:
        if not pygame.font.match_font(name):
            continue
        probe = pygame.font.SysFont(name, 24)
        if all(probe.render(ch, True, (255, 255, 255)).get_bounding_rect().width > 0
               for ch in _COVERAGE_PROBE):
            _font_family = name
            return name
    _font_family = ""
    return _font_family


FONT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "font.ttf")


def font(size=16, bold=False):
    key = (size, bold)
    f = _fonts.get(key)
    if f is not None:
        try:
            f.get_height()
            return f
        except pygame.error:      # pygame 重启过，旧 Font 已失效
            _fonts.clear()
    # 优先用随包字体（网页/安卓上没有系统中文字体）
    if os.path.isfile(FONT_FILE):
        try:
            f = pygame.font.Font(FONT_FILE, size)
            f.set_bold(bold)
            _fonts[key] = f
            return f
        except pygame.error:
            pass
    f = pygame.font.SysFont(_resolve_font_family() or None, size, bold=bold)
    _fonts[key] = f
    return f


def label(text, color, size=16, bold=False):
    """带描边的文字（缓存）。"""
    key = (text, tuple(color), size, bold)
    surf = _labels.get(key)
    if surf is None:
        f = font(size, bold)
        shadow = f.render(text, True, (14, 10, 16))
        body = f.render(text, True, color)
        surf = pygame.Surface((body.get_width() + 2, body.get_height() + 2), pygame.SRCALPHA)
        surf.blit(shadow, (1, 1))
        surf.blit(body, (0, 0))
        _labels[key] = surf
    return surf


def panel(screen, rect, accent=(255, 170, 214), fill=(24, 18, 32), alpha=215,
          radius=12, border=2):
    """渐变 + 双层描边的 UI 面板，统一界面风格。"""
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*fill, alpha), surf.get_rect(), border_radius=radius)
    # 顶部高光用 blit 叠加，直接画会覆盖掉底色透明度
    hi = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(hi, (*_light(fill, 0.18), 70), (0, 0, rect.w, rect.h // 2),
                     border_radius=radius)
    surf.blit(hi, (0, 0))
    screen.blit(surf, rect.topleft)
    pygame.draw.rect(screen, accent, rect, border, border_radius=radius)
    pygame.draw.rect(screen, _shade(accent, 0.5), rect.inflate(-5, -5), 1,
                     border_radius=max(2, radius - 3))


def draw_damage_number(screen, x, y, value, color=(255, 236, 140), size=16):
    surf = label(str(value), color, size, True)
    screen.blit(surf, (int(x) - surf.get_width() // 2, int(y)))
