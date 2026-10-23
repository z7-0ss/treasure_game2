# main.py
import pygame, sys, asyncio, math, random
from settings import *
from level import Level, generate_map
import art
import audio
import save
from entities import Player, Boss, Q_COLOR, FloatText


WIN_UI = {"continue": pygame.Rect(0, 0, 0, 0), "menu": pygame.Rect(0, 0, 0, 0)}
BAG_PAGE = {"page": 0}
EQUIP_RECTS = []
HOVER_TIP = {}
SELECT_UI = {"back": pygame.Rect(0, 0, 0, 0)}
STATS_UI = {"close": pygame.Rect(0, 0, 0, 0), "discard": pygame.Rect(0, 0, 0, 0)}
PET_UI = {"close": pygame.Rect(0, 0, 0, 0)}


# --------------------------------------------------------------------------
# 装备
# --------------------------------------------------------------------------
def equip_from_inventory(player, kind, idx):
    pairs = {
        "weapon": (player.inventory_weapons, "weapon_quality"),
        "armor": (player.inventory_armors, "armor_quality"),
        "helmet": (player.inventory_helmets, "helmet_quality"),
        "boots": (player.inventory_boots, "boots_quality"),
        "pants": (player.inventory_pants, "pants_quality"),
        "bracelet": (player.inventory_bracelets, "bracelet_quality"),
    }
    if kind not in pairs:
        return False
    bag, attr = pairs[kind]
    if idx >= len(bag):
        return False
    set_attr = attr.replace("_quality", "_set")
    old = getattr(player, attr)
    old_set = getattr(player, set_attr, "forest")
    entry = bag.pop(idx)
    if isinstance(entry, (list, tuple)) and len(entry) == 3:
        quality, set_key, hidden = entry
    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
        quality, set_key, hidden = entry[0], entry[1], None
    else:
        quality, set_key, hidden = entry, "forest", None
    old_hidden = getattr(player, set_attr.replace("_set", "_hidden"), None)
    setattr(player, attr, quality)
    setattr(player, set_attr, set_key)
    setattr(player, set_attr.replace("_set", "_hidden"), hidden)
    if old != "none" and old != "":
        bag.append((old, old_set, old_hidden))
    if attr == "pants_quality":
        player.hp = min(player.hp, player.max_hp)
    audio.play("pickup", 0.6)
    return True


GEAR_STAT_LABEL = {"weapon": "武器", "armor": "衣甲", "helmet": "头盔",
                   "boots": "鞋子", "pants": "裤子", "bracelet": "手镯"}
Q_ORDER = {Q_WHITE: 0, Q_SILVER: 1, Q_PURPLE: 2, Q_GOLD: 3, Q_RED: 4}


WEAPON_BONUS = {Q_WHITE: 0, Q_SILVER: DMG_BONUS_SILVER, Q_PURPLE: DMG_BONUS_PURPLE,
                Q_GOLD: DMG_BONUS_GOLD, Q_RED: DMG_BONUS_RED}


def gear_stats(kind, quality):
    """返回该装备提供的属性 dict（与角色面板一致）。"""
    if quality not in Q_ORDER:
        return {}
    if kind == "weapon":
        return {"攻击": WEAPON_BONUS[quality]}
    if kind == "armor":
        return {"防御": ARMOR_DEF[quality], "法抗": ARMOR_MRES[quality]}
    if kind == "helmet":
        return {"防御": HELMET_DEF[quality], "法抗": HELMET_MRES[quality]}
    if kind == "boots":
        return {"移速%": int(BOOTS_SPEED[quality] * 100), "防御": BOOTS_DEF[quality]}
    if kind == "pants":
        return {"生命": PANTS_HP[quality], "防御": PANTS_DEF[quality]}
    if kind == "bracelet":
        return {"攻击": BRACELET_ATK[quality], "法抗": BRACELET_MRES[quality]}
    return {}


def draw_item_tooltip(screen, font, small_font, kind, quality, set_key, player, anchor,
                      hidden=None):
    """鼠标悬停时的装备说明。"""
    gs = GEAR_SETS.get(set_key, GEAR_SETS["forest"])
    if kind == "weapon":
        name = f"{Q_NAME.get(quality, '')}·{gs['weapon'].get(player.weapon_type, '武器')}"
    else:
        name = f"{Q_NAME.get(quality, '')}·{gs[kind]}"
    if hidden:
        name += "（隐藏）"
    stats = gear_stats(kind, quality)
    cur_q = getattr(player, kind + "_quality", "none")
    cur_set = getattr(player, kind + "_set", "forest")
    cur_stats = gear_stats(kind, cur_q)

    lines = [(name, Q_COLOR.get(quality, (235, 235, 235)), True),
             (f"{GEAR_STAT_LABEL[kind]} · {gs['name']}系列 · {Q_NAME.get(quality, '')}",
              (185, 182, 200), False),
             ("", (0, 0, 0), False)]
    for label, value in stats.items():
        delta = value - cur_stats.get(label, 0)
        txt = f"{label} +{value}"
        if delta > 0:
            txt += f"  (↑{delta})"
        elif delta < 0:
            txt += f"  (↓{abs(delta)})"
        lines.append((txt, (150, 255, 190) if delta > 0 else
                      ((255, 170, 170) if delta < 0 else (220, 220, 230)), False))

    if cur_q in Q_ORDER:
        cur_name = (f"{Q_NAME[cur_q]}·{gs['weapon'].get(player.weapon_type, '武器')}"
                    if kind == "weapon" else f"{Q_NAME[cur_q]}·{gs[kind]}")
        lines.append(("", (0, 0, 0), False))
        lines.append((f"当前：{cur_name}", (190, 186, 205), False))
    else:
        lines.append(("", (0, 0, 0), False))
        lines.append(("当前：空", (150, 146, 162), False))

    if hidden:
        eff = HIDDEN_EFFECTS.get(hidden, ("隐藏", ""))
        lines.append((f"★ 隐藏属性：{eff[0]} — {eff[1]}", (255, 214, 120), True))
    else:
        lines.append(("集齐 6 件同系列：减免对应关卡负面效果", (150, 200, 230), False))

    pad = 14
    line_h = 20
    width = 120
    for text, _c, bold in lines:
        if text:
            width = max(width, (font if bold else small_font).size(text)[0])
    width = min(460, width + pad * 2)
    height = len(lines) * line_h + pad * 2 - 6
    x, y = anchor[0] + 18, anchor[1] + 14
    x = max(8, min(WIDTH - width - 8, x))
    y = max(8, min(HEIGHT - height - 8, y))
    box = pygame.Rect(x, y, width, height)
    art.panel(screen, box, accent=(255, 200, 230), fill=(24, 20, 32), alpha=250, radius=10)
    ty = y + pad
    for text, color, bold in lines:
        if text:
            surf = (font if bold else small_font).render(text, True, color)
            screen.blit(surf, (x + pad, ty))
        ty += line_h


def discard_from_inventory(player, kind, idx):
    bags = {
        "weapon": player.inventory_weapons, "armor": player.inventory_armors,
        "helmet": player.inventory_helmets, "boots": player.inventory_boots,
        "pants": player.inventory_pants, "bracelet": player.inventory_bracelets,
    }
    bag = bags.get(kind)
    if bag is None or idx >= len(bag):
        return None
    entry = bag.pop(idx)
    quality = entry[0] if isinstance(entry, (list, tuple)) else entry
    audio.play("hit", 0.4)
    return quality


# --------------------------------------------------------------------------
# 摇杆
# --------------------------------------------------------------------------
class Joystick:
    def __init__(self, center_x, center_y, radius=50):
        self.home_x, self.home_y = center_x, center_y
        self.center_x, self.center_y = center_x, center_y
        self.radius = radius
        self.knob_x, self.knob_y = center_x, center_y
        self.active = False
        self.dx, self.dy = 0, 0
        self.finger = None

    def reset(self):
        self.finger = None
        self.active = False
        self.dx = self.dy = 0
        self.center_x, self.center_y = self.home_x, self.home_y
        self.knob_x, self.knob_y = self.home_x, self.home_y

    def _apply_offset(self, pos):
        ox, oy = pos[0] - self.center_x, pos[1] - self.center_y
        dist = math.hypot(ox, oy)
        if dist > self.radius:
            ox, oy = (ox / dist) * self.radius, (oy / dist) * self.radius
        self.knob_x, self.knob_y = self.center_x + ox, self.center_y + oy
        self.dx = ox / self.radius
        self.dy = oy / self.radius

    def touch_start(self, finger_id, pos):
        self.finger = finger_id
        self.active = True
        self._apply_offset(pos)

    def touch_move(self, finger_id, pos):
        if self.finger == finger_id and self.active:
            self._apply_offset(pos)

    def touch_end(self, finger_id):
        if self.finger == finger_id:
            self.reset()

    def handle_event(self, event):
        if self.finger is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if math.dist(event.pos, (self.center_x, self.center_y)) < self.radius * 1.5:
                self.active = True
                self._apply_offset(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.reset()
        elif event.type == pygame.MOUSEMOTION and self.active:
            self._apply_offset(event.pos)

    def update(self):
        return

    def draw(self, screen):
        base = (92, 132, 186) if self.active else (98, 102, 126)
        glow_alpha = 78 if self.active else 42
        art.blit_glow(screen, self.center_x, self.center_y, self.radius + 24, base, glow_alpha)
        pygame.draw.circle(screen, (12, 16, 24, 110), (self.center_x, self.center_y), self.radius + 10)
        pygame.draw.circle(screen, (28, 34, 48), (self.center_x, self.center_y), self.radius + 2)
        pygame.draw.circle(screen, (54, 64, 90), (self.center_x, self.center_y), self.radius - 6)
        pygame.draw.circle(screen, _mix(base, (235, 245, 255), 0.55),
                           (self.center_x, self.center_y), self.radius + 2, 3)
        pygame.draw.circle(screen, (255, 255, 255, 30), (self.center_x, self.center_y),
                           self.radius - 18)
        for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
            ox = math.cos(angle) * (self.radius - 14)
            oy = math.sin(angle) * (self.radius - 14)
            inner = (int(self.center_x + ox * 0.48), int(self.center_y + oy * 0.48))
            outer = (int(self.center_x + ox), int(self.center_y + oy))
            pygame.draw.line(screen, (180, 198, 226), inner, outer, 2)

        knob_color = (132, 208, 255) if self.active else (172, 176, 190)
        knob_radius = 24 if self.active else 22
        pygame.draw.circle(screen, (8, 10, 18, 120), (int(self.knob_x), int(self.knob_y)), knob_radius + 5)
        pygame.draw.circle(screen, _mix(knob_color, (28, 32, 48), 0.35),
                           (int(self.knob_x), int(self.knob_y)), knob_radius)
        pygame.draw.circle(screen, _mix(knob_color, (255, 255, 255), 0.35),
                           (int(self.knob_x), int(self.knob_y)), knob_radius, 3)
        pygame.draw.circle(screen, (255, 255, 255, 35),
                           (int(self.knob_x - 6), int(self.knob_y - 7)), max(6, knob_radius // 3))


def _mix(color_a, color_b, t):
    return tuple(int(color_a[i] + (color_b[i] - color_a[i]) * t) for i in range(3))


def _octagon_points(center, radius):
    cut = max(6, int(radius * 0.38))
    cx, cy = center
    return [
        (cx - radius + cut, cy - radius),
        (cx + radius - cut, cy - radius),
        (cx + radius, cy - radius + cut),
        (cx + radius, cy + radius - cut),
        (cx + radius - cut, cy + radius),
        (cx - radius + cut, cy + radius),
        (cx - radius, cy + radius - cut),
        (cx - radius, cy - radius + cut),
    ]


def _scale_points(points, center, scale):
    cx, cy = center
    return [(int(cx + (x - cx) * scale), int(cy + (y - cy) * scale)) for x, y in points]


def _press_scale(pressed_at, now, duration=140, min_scale=0.9):
    if pressed_at is None:
        return 1.0
    age = now - pressed_at
    if age < 0 or age >= duration:
        return 1.0
    t = age / duration
    if t < 0.45:
        return 1.0 - (1.0 - min_scale) * (t / 0.45)
    return min_scale + (1.0 - min_scale) * ((t - 0.45) / 0.55)


def _pixel_pulse(now, speed=0.012, low=0.18, high=0.58):
    return low + (high - low) * (0.5 + 0.5 * math.sin(now * speed))


def _draw_touch_pill(screen, rect, fill, border, text, font, text_color):
    pygame.draw.rect(screen, (10, 12, 18, 120), rect.move(0, 2), border_radius=6)
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    shine = pygame.Rect(rect.x + 4, rect.y + 3, rect.w - 8, max(4, rect.h // 3))
    pygame.draw.rect(screen, (255, 255, 255, 24), shine, border_radius=4)
    for px, py in ((rect.left + 2, rect.top + 2), (rect.right - 4, rect.top + 2),
                   (rect.left + 2, rect.bottom - 4), (rect.right - 4, rect.bottom - 4)):
        pygame.draw.rect(screen, _mix(border, (255, 255, 255), 0.25), (px, py, 2, 2))
    surf = font.render(text, True, text_color)
    screen.blit(surf, surf.get_rect(center=rect.center))


def _draw_round_action_button(screen, center, radius, base_color, label, font,
                              text_color=(255, 255, 255), glow=None, tag=None, tag_font=None,
                              pressed_at=None, now=0):
    glow = glow or base_color
    scale = _press_scale(pressed_at, now, min_scale=0.9)
    outer = _scale_points(_octagon_points(center, radius + 6), center, scale)
    inner = _scale_points(_octagon_points(center, radius), center, scale)
    core = _scale_points(_octagon_points(center, max(12, radius - 8)), center, scale)
    art.blit_glow(screen, center[0], center[1], int((radius + 20) * scale), glow, 64)
    pygame.draw.polygon(screen, (12, 12, 20, 124), [(x, y + 4) for x, y in outer])
    pygame.draw.polygon(screen, (44, 36, 56), outer)
    pygame.draw.polygon(screen, _mix(base_color, (28, 24, 42), 0.45), inner)
    pygame.draw.polygon(screen, _mix(base_color, (255, 244, 220), 0.18), core)
    pygame.draw.polygon(screen, _mix(base_color, (255, 255, 255), 0.25), outer, 3)
    top_shine = _scale_points([(center[0] - radius // 2, center[1] - radius // 2),
                               (center[0] + radius // 2, center[1] - radius // 2),
                               (center[0] + radius // 3, center[1] - radius // 5),
                               (center[0] - radius // 3, center[1] - radius // 5)], center, scale)
    pygame.draw.polygon(screen, (255, 255, 255, 24), top_shine)
    icon = font.render(label, True, text_color)
    icon_rect = icon.get_rect(center=(center[0], center[1] - 2 + int((1.0 - scale) * 16)))
    screen.blit(icon, icon_rect)
    if tag and tag_font:
        pill = pygame.Rect(center[0] - 24, center[1] + radius - 4, 48, 18)
        _draw_touch_pill(screen, pill, (26, 24, 34), _mix(base_color, (255, 255, 255), 0.45),
                         tag, tag_font, (240, 236, 244))


# --------------------------------------------------------------------------
# 技能按钮
# --------------------------------------------------------------------------
def draw_skill_button(screen, rect, player, slot, font, small_font, key_label, pressed_at=None, now=0):
    skill = player.skill_at(slot)
    ready = player.skill_ready_at(slot)
    cd = player.skill_cds[slot]
    cd_max = max(1, player.skill_cd_maxs[slot])
    ratio = cd / cd_max
    scale = _press_scale(pressed_at, now, min_scale=0.88)
    accent = skill["color"] if ready else (104, 110, 124)
    ring_color = _mix(accent, (255, 242, 208), 0.22)
    outer = _scale_points(_octagon_points(rect.center, 36), rect.center, scale)
    inner = _scale_points(_octagon_points(rect.center, 31), rect.center, scale)
    core = _scale_points(_octagon_points(rect.center, 25), rect.center, scale)
    if ready:
        art.blit_glow(screen, rect.centerx, rect.centery, int(48 * scale), accent, 68)
    elif cd > 0:
        pulse_alpha = int(35 + 55 * _pixel_pulse(now, speed=0.01))
        art.blit_glow(screen, rect.centerx, rect.centery, int(42 * scale), accent, pulse_alpha)
    pygame.draw.polygon(screen, (8, 10, 18, 120), [(x, y + 4) for x, y in outer])
    pygame.draw.polygon(screen, (42, 34, 54), outer)
    pygame.draw.polygon(screen, _mix(accent, (26, 22, 38), 0.52), inner)
    pygame.draw.polygon(screen, _mix(accent, (255, 244, 220), 0.15), core)
    pygame.draw.polygon(screen, ring_color, outer, 3)
    highlight = _scale_points([(rect.centerx - 18, rect.centery - 18), (rect.centerx + 18, rect.centery - 18),
                               (rect.centerx + 12, rect.centery - 7), (rect.centerx - 12, rect.centery - 7)],
                              rect.center, scale)
    pygame.draw.polygon(screen, (255, 255, 255, 24), highlight)

    if cd > 0:
        cd_text = small_font.render(f"{cd / FPS:.1f}", True, (235, 235, 245))
        screen.blit(cd_text, cd_text.get_rect(center=(rect.centerx, rect.centery - 1 + int((1.0 - scale) * 14))))
        arc_rect = pygame.Rect(rect.centerx - 35, rect.centery - 35, 70, 70)
        pulse_col = _mix((255, 212, 234), accent, 0.25 + 0.25 * _pixel_pulse(now, speed=0.009))
        pygame.draw.arc(screen, pulse_col, arc_rect,
                        -math.pi / 2, -math.pi / 2 + math.tau * ratio, 5)
        pygame.draw.arc(screen, (120, 128, 144), arc_rect, -math.pi / 2,
                        -math.pi / 2 + math.tau, 2)
    else:
        icon_color = (16, 12, 20) if ready else (150, 150, 160)
        icon = font.render(skill["icon"], True, icon_color)
        screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 2 + int((1.0 - scale) * 14))))

    name_color = skill["color"] if ready else (130, 130, 140)
    name_surf = small_font.render(skill["name"], True, name_color)
    chip = pygame.Rect(rect.centerx - max(30, name_surf.get_width() // 2 + 10), rect.centery + 29,
                       max(60, name_surf.get_width() + 20), 20)
    _draw_touch_pill(screen, chip, (24, 24, 34), _mix(accent, (255, 255, 255), 0.36),
                     skill["name"], small_font, name_color)
    key_pill = pygame.Rect(rect.x - 2, rect.y - 4, 24, 18)
    _draw_touch_pill(screen, key_pill, (18, 18, 28), _mix(accent, (255, 255, 255), 0.45),
                     key_label, small_font, (255, 232, 245))


# --------------------------------------------------------------------------
# HUD
# --------------------------------------------------------------------------
def draw_hud(screen, level, font, small_font, item_rects, collected_digits, show_items=True):
    pl = level.player
    armor_color = (72, 132, 204) if pl.armor_quality == "none" else Q_COLOR[pl.armor_quality]
    head_color = HAIR_COLOR if pl.helmet_quality == "none" else Q_COLOR[pl.helmet_quality]

    hud_rect = pygame.Rect(18, 8, 430, 112)
    art.panel(screen, hud_rect, accent=(255, 178, 216))

    face = pygame.Rect(hud_rect.x + 12, hud_rect.y + 14, 62, 62)
    pygame.draw.rect(screen, (42, 34, 52), face, border_radius=10)
    dominant_set = pl.armor_set if pl.armor_quality != "none" else pl.weapon_set
    mini = art.player_sprite(armor_color, head_color, pl.weapon_type, dominant_set)
    screen.blit(mini, (face.centerx - mini.get_width() // 2,
                       face.centery - mini.get_height() // 2 + 2))
    pygame.draw.rect(screen, (255, 208, 236), face, 2, border_radius=10)

    chapter_name, level_name = level_title(level.level_index)
    bx = hud_rect.x + 86
    screen.blit(small_font.render(
        f"Lv.{pl.level} {CLASS_NAME[pl.weapon_type]} · {chapter_name} · {level_name}",
        True, (255, 226, 240)), (bx, hud_rect.y + 8))
    exp_ratio = pl.exp / max(1, pl.next_level_exp)
    pygame.draw.rect(screen, (40, 34, 48), (bx, hud_rect.y + 30, 258, 5), border_radius=2)
    pygame.draw.rect(screen, (120, 220, 255), (bx, hud_rect.y + 30, int(258 * exp_ratio), 5),
                     border_radius=2)

    hp_bar = pygame.Rect(bx, hud_rect.y + 40, 258, 18)
    pygame.draw.rect(screen, (52, 22, 28), hp_bar, border_radius=6)
    ratio = max(0.0, min(1.0, pl.hp / pl.max_hp))
    hp_col = (232, 62, 84) if ratio > 0.3 else (255, 126, 92)
    pygame.draw.rect(screen, hp_col, (hp_bar.x + 1, hp_bar.y + 1,
                                      int((hp_bar.w - 2) * ratio), hp_bar.h - 2), border_radius=5)
    pygame.draw.rect(screen, (255, 180, 190), (hp_bar.x + 3, hp_bar.y + 3,
                                               max(0, int((hp_bar.w - 6) * ratio)), 4))
    hp_txt = small_font.render(f"{int(round(pl.hp))} / {int(pl.max_hp)}", True, (255, 246, 248))
    screen.blit(hp_txt, (hp_bar.centerx - hp_txt.get_width() // 2, hp_bar.y - 1))

    mp_bar = pygame.Rect(bx, hud_rect.y + 62, 258, 9)
    pygame.draw.rect(screen, (24, 30, 48), mp_bar, border_radius=4)
    pygame.draw.rect(screen, (96, 158, 255), (mp_bar.x + 1, mp_bar.y + 1,
                                              int((mp_bar.w - 2) * pl.energy / MAX_ENERGY),
                                              mp_bar.h - 2), border_radius=3)

    screen.blit(small_font.render(f"防御 {pl.defense}", True, (170, 210, 255)), (bx, hud_rect.y + 76))
    screen.blit(small_font.render(f"法抗 {pl.magic_resist}", True, (190, 170, 255)), (bx + 78, hud_rect.y + 76))
    screen.blit(small_font.render(f"攻击 {pl.get_damage()}", True, (255, 220, 150)), (bx + 156, hud_rect.y + 76))
    screen.blit(small_font.render(f"碎片 {len(collected_digits)}/{TOTAL_LEVELS}", True, GOLD_COLOR),
                (bx, hud_rect.y + 94))

    obj_rect = pygame.Rect(WIDTH - 218, 8, 200, 74)
    art.panel(screen, obj_rect, accent=(255, 178, 216))
    key_ok, boss_ok = level.has_key, level.boss_defeated
    key_color = (140, 255, 170) if key_ok else (150, 150, 160)
    boss_color = (140, 255, 170) if boss_ok else (150, 150, 160)
    screen.blit(small_font.render(f"钥匙   {'已获得' if key_ok else '击杀BOSS掉落'}", True, key_color),
                (obj_rect.x + 12, obj_rect.y + 9))
    screen.blit(small_font.render(f"BOSS  {'已击败' if boss_ok else '未击败'}", True, boss_color),
                (obj_rect.x + 12, obj_rect.y + 31))
    gate_color = (140, 255, 170) if level.door_open else (255, 170, 130)
    screen.blit(small_font.render("传送门 已开启" if level.door_open else "传送门 未开启",
                                  True, gate_color), (obj_rect.x + 12, obj_rect.y + 53))

    # 环境 / 状态提示
    chips = []
    if level.theme == "ocean":
        loss = int(round((1 - pl.env_speed_mult) * 100))
        if loss > 0:
            chips.append((f"海水阻力 · 移速 -{loss}%", (140, 200, 255)))
        else:
            chips.append(("海底套装 · 免疫阻力", (150, 255, 200)))
    if getattr(pl, "freeze_timer", 0) > 0:
        chips.append((f"冻结 {pl.freeze_timer / FPS:.1f}s", (188, 235, 255)))
    if pl.chill_timer > 0:
        chips.append((f"冰冻 {pl.chill_timer / FPS:.1f}s · 抗性 "
                      f"{int(pl.status_resist('ocean') * 100)}%", (150, 220, 255)))
    if pl.burn_timer > 0:
        chips.append((f"灼烧 {pl.burn_timer / FPS:.1f}s · 抗性 "
                      f"{int(pl.status_resist('volcano') * 100)}%", (255, 150, 90)))
    for i, (text, color) in enumerate(chips[:3]):
        chip = small_font.render(text, True, color)
        bx = hud_rect.right + 12
        by = hud_rect.y + 6 + i * 20
        pygame.draw.rect(screen, (30, 28, 40), (bx - 6, by - 1, chip.get_width() + 12, 19),
                         border_radius=7)
        pygame.draw.rect(screen, color, (bx - 6, by - 1, chip.get_width() + 12, 19), 1,
                         border_radius=7)
        screen.blit(chip, (bx, by))

    level.draw_radar(screen, pygame.Rect(WIDTH - 208, 146, 200, 100))

    if show_items:
        for i, kind in enumerate(ITEM_SLOTS):
            rect = item_rects[i]
            count = pl.bag.get(kind, 0)
            accent = (255, 202, 232) if count > 0 else (92, 88, 106)
            art.panel(screen, rect, accent=accent, radius=10, alpha=195)
            art.draw_item_icon(screen, rect.x + 9, rect.y + 9, kind, Q_WHITE, None, 0)
            hot = small_font.render(ITEM_HOTKEY[kind], True, (255, 226, 244))
            screen.blit(hot, (rect.x + 4, rect.y + 1))
            cnt = small_font.render(f"×{count}", True, (255, 255, 255) if count else (150, 150, 160))
            screen.blit(cnt, (rect.right - cnt.get_width() - 4, rect.bottom - cnt.get_height() - 1))

    live_bosses = [e for e in level.enemies if e.is_boss]
    for e in live_bosses:
        if math.hypot(e.rect.centerx - pl.rect.centerx,
                      e.rect.centery - pl.rect.centery) > 560:
            continue
        panel_rect = pygame.Rect(WIDTH - 356, 92, 338, 38)
        art.panel(screen, panel_rect, accent=(255, 110, 170), radius=10, alpha=210)
        bar_rect = pygame.Rect(panel_rect.x + 8, panel_rect.y + 18, panel_rect.w - 16, 12)
        inner = pygame.Rect(bar_rect.x, bar_rect.y, bar_rect.w, bar_rect.h)
        pygame.draw.rect(screen, (40, 16, 24), inner, border_radius=5)
        ratio = max(0.0, e.hp / e.max_hp)
        pygame.draw.rect(screen, (214, 48, 112),
                         (inner.x, inner.y, int(inner.w * ratio), inner.h), border_radius=5)
        pygame.draw.rect(screen, (255, 188, 214), (inner.x + 2, inner.y + 2,
                                                    max(0, int((inner.w - 4) * ratio)), 3), border_radius=2)
        name_surf = small_font.render(e.name, True, (255, 240, 246))
        screen.blit(name_surf, (panel_rect.x + 10, panel_rect.y + 2))
        hp_surf = small_font.render(f"{max(0, int(e.hp))} / {int(e.max_hp)}",
                                    True, (255, 255, 255))
        screen.blit(hp_surf, (panel_rect.right - hp_surf.get_width() - 10, panel_rect.y + 2))
        if e.cast_timer > 0:
            warn = small_font.render("技能蓄力中！", True, (255, 190, 120))
            screen.blit(warn, (panel_rect.centerx - warn.get_width() // 2, panel_rect.bottom + 3))
        if len(live_bosses) > 1:
            rest = small_font.render(f"剩余 BOSS ×{len(live_bosses)}", True, (255, 170, 200))
            screen.blit(rest, (panel_rect.x + 10, panel_rect.bottom + 3))
        break


# --------------------------------------------------------------------------
# 角色 / 装备 / 背包
# --------------------------------------------------------------------------
def draw_stats_panel(screen, level, font, small_font, inv_rects, inv_actions, discard_mode=False):
    panel = pygame.Rect(WIDTH // 2 - 390, 6, 780, 528)
    art.panel(screen, panel, accent=(255, 170, 214), fill=(30, 24, 38), alpha=252, radius=14)
    pygame.draw.rect(screen, (44, 34, 54), (panel.x + 16, panel.y + 46, panel.w - 32, 2))
    screen.blit(font.render("角色 · 装备 · 背包", True, (255, 206, 232)), (panel.x + 24, panel.y + 14))
    screen.blit(small_font.render("按 I 关闭", True, (170, 170, 190)),
                (panel.right - 130, panel.y + 20))
    STATS_UI["close"] = pygame.Rect(panel.right - 46, panel.y + 8, 32, 32)
    pygame.draw.rect(screen, (58, 42, 62), STATS_UI["close"], border_radius=9)
    pygame.draw.rect(screen, (255, 190, 220), STATS_UI["close"], 1, border_radius=9)
    cross = font.render("×", True, (255, 220, 236))
    screen.blit(cross, (STATS_UI["close"].centerx - cross.get_width() // 2,
                        STATS_UI["close"].centery - cross.get_height() // 2 - 2))

    pl = level.player
    armor_color = (72, 132, 204) if pl.armor_quality == "none" else Q_COLOR[pl.armor_quality]
    head_color = HAIR_COLOR if pl.helmet_quality == "none" else Q_COLOR[pl.helmet_quality]
    dominant_set = pl.armor_set if pl.armor_quality != "none" else pl.weapon_set
    spr = art.player_sprite(armor_color, head_color, pl.weapon_type, dominant_set)
    base = pygame.Surface((spr.get_width() + 20, spr.get_height() + 20), pygame.SRCALPHA)
    base.blit(spr, (10, 18))
    art.draw_player_hat(base, 10, 18, pl.weapon_type, head_color)
    big = pygame.transform.scale(base, (base.get_width() * 2, base.get_height() * 2))
    cx, cy = panel.x + 100, panel.y + 128
    art.blit_glow(screen, cx, cy, 66, (255, 180, 215), 40)
    screen.blit(big, (cx - big.get_width() // 2, cy - big.get_height() // 2))

    slot_defs = [("weapon", "武器"), ("armor", "衣甲"), ("helmet", "头盔"),
                 ("boots", "鞋子"), ("pants", "裤子"), ("bracelet", "手镯")]
    quals = {k: getattr(pl, k + "_quality") for k, _ in slot_defs}
    EQUIP_RECTS.clear()
    for i, (kind, label) in enumerate(slot_defs):
        col, row = i % 3, i // 3
        rect = pygame.Rect(panel.x + 28 + col * 54, panel.y + 196 + row * 58, 46, 46)
        q = quals[kind]
        pygame.draw.rect(screen, (50, 42, 60), rect, border_radius=6)
        if q and q != "none":
            pygame.draw.rect(screen, Q_COLOR.get(q, (200, 200, 200)), rect, 2, border_radius=6)
            art.draw_item_icon(screen, rect.x + 5, rect.y + 5, kind, q,
                               pl.weapon_type if kind == "weapon" else None, 0,
                               set_color=GEAR_SETS.get(getattr(pl, kind + "_set", "forest"),
                                                       {}).get("color"),
                               set_key=getattr(pl, kind + "_set", "forest"))
        else:
            pygame.draw.rect(screen, (80, 74, 92), rect, 1, border_radius=6)
            empty = small_font.render("空", True, (110, 106, 122))
            screen.blit(empty, (rect.centerx - empty.get_width() // 2,
                                rect.centery - empty.get_height() // 2))
        lab = small_font.render(label, True, (190, 186, 205))
        screen.blit(lab, (rect.centerx - lab.get_width() // 2, rect.bottom + 1))
        if q and q != "none":
            EQUIP_RECTS.append((kind, q, getattr(pl, kind + "_set", "forest"), rect,
                                getattr(pl, kind + "_hidden", None)))

    def gear_name(kind, quality, set_key):
        if not quality or quality == "none":
            return "无"
        gs = GEAR_SETS.get(set_key, GEAR_SETS["forest"])
        if kind == "weapon":
            return f"{Q_NAME[quality]}·{gs['weapon'].get(pl.weapon_type, '武器')}"
        return f"{Q_NAME[quality]}·{gs[kind]}"

    if pl.weapon_type == WEAPON_SWORD:
        atk_range_text = f"近战范围: {40 + (pl.level // 2) * 5}"
    elif pl.weapon_type == WEAPON_BOW:
        atk_range_text = f"射击距离: {300 + (pl.level - 1) * 40}"
    else:
        atk_range_text = f"施法距离: {250 + (pl.level - 1) * 30}"

    stats = [
        (f"职业: {CLASS_NAME[pl.weapon_type]}   Lv.{pl.level}", GOLD_COLOR),
        (f"生命: {int(round(pl.hp))} / {int(pl.max_hp)}", (255, 190, 190)),
        (f"攻击力: {pl.get_damage()}    防御: {pl.defense}", (255, 220, 150)),
        (f"法抗: {pl.magic_resist}    移速: {pl.move_speed:.1f}", (190, 200, 255)),
        (atk_range_text, (200, 200, 200)),
        (gear_name("weapon", pl.weapon_quality, pl.weapon_set),
         Q_COLOR.get(pl.weapon_quality, (230, 230, 230))),
        (f"{gear_name('armor', pl.armor_quality, pl.armor_set)} / "
         f"{gear_name('helmet', pl.helmet_quality, pl.helmet_set)}",
         Q_COLOR.get(pl.helmet_quality, (230, 230, 230))),
        (f"{gear_name('boots', pl.boots_quality, pl.boots_set)} / "
         f"{gear_name('pants', pl.pants_quality, pl.pants_set)}",
         Q_COLOR.get(pl.pants_quality, (230, 230, 230))),
        (gear_name("bracelet", pl.bracelet_quality, pl.bracelet_set),
         Q_COLOR.get(pl.bracelet_quality, (230, 230, 230))),
        (f"跟宠: {level.pet.role_text}", (150, 255, 210)),
    ]
    for i, (text, color) in enumerate(stats):
        screen.blit(small_font.render(text, True, color), (panel.x + 206, panel.y + 56 + i * 22))

    inv_x = panel.x + 470
    inv_y = panel.y + 64
    entries = []
    for kind, bag in (("weapon", pl.inventory_weapons), ("armor", pl.inventory_armors),
                      ("helmet", pl.inventory_helmets), ("boots", pl.inventory_boots),
                      ("pants", pl.inventory_pants), ("bracelet", pl.inventory_bracelets)):
        for idx, entry in enumerate(bag):
            if isinstance(entry, (list, tuple)) and len(entry) == 3:
                q, set_key, hidden = entry
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                q, set_key, hidden = entry[0], entry[1], None
            else:
                q, set_key, hidden = entry, "forest", None
            entries.append((kind, q, set_key, idx, hidden))

    # 相同（部位 + 品质 + 套装）折叠成一格，角标显示数量
    groups = {}
    order = []
    for kind, q, set_key, idx, hidden in entries:
        key = (kind, q, set_key, hidden)
        if key not in groups:
            groups[key] = {"kind": kind, "q": q, "set": set_key, "count": 0,
                           "idx": idx, "hidden": hidden}
            order.append(key)
        groups[key]["count"] += 1
    slots = [groups[k] for k in order]

    screen.blit(small_font.render(f"背包 {len(entries)} / {INVENTORY_MAX} 件 · {len(slots)} 格",
                                  True, (210, 206, 225)), (inv_x, inv_y - 22))
    STATS_UI["discard"] = pygame.Rect(inv_x + 140, inv_y - 26, 118, 22)
    on = discard_mode
    pygame.draw.rect(screen, (120, 44, 56) if on else (54, 48, 64),
                     STATS_UI["discard"], border_radius=6)
    pygame.draw.rect(screen, (255, 160, 170) if on else (110, 104, 124),
                     STATS_UI["discard"], 1, border_radius=6)
    dlabel = small_font.render("丢弃模式: 开" if on else "丢弃模式: 关", True,
                               (255, 226, 232) if on else (190, 186, 205))
    screen.blit(dlabel, (STATS_UI["discard"].centerx - dlabel.get_width() // 2,
                         STATS_UI["discard"].centery - dlabel.get_height() // 2))

    per_page = 30
    pages = max(1, (len(slots) + per_page - 1) // per_page)
    page = max(0, min(BAG_PAGE["page"], pages - 1))
    BAG_PAGE["page"] = page
    page_slots = slots[page * per_page:(page + 1) * per_page]

    inv_rects.clear()
    inv_actions.clear()
    hover_items = []
    for i, g in enumerate(page_slots):
        col, row = i % 5, i // 5
        rect = pygame.Rect(inv_x + col * 44, inv_y + row * 44, 40, 40)
        pygame.draw.rect(screen, (54, 48, 64), rect, border_radius=5)
        pygame.draw.rect(screen, Q_COLOR.get(g["q"], (200, 200, 200)), rect, 1, border_radius=5)
        art.draw_item_icon(screen, rect.x + 3, rect.y + 3, g["kind"], g["q"],
                           pl.weapon_type if g["kind"] == "weapon" else None, 0,
                           set_color=GEAR_SETS.get(g["set"], {}).get("color"),
                           set_key=g["set"])
        if g["count"] > 1:
            badge = small_font.render(f"×{g['count']}", True, (255, 255, 255))
            pygame.draw.rect(screen, (24, 20, 30),
                             (rect.right - badge.get_width() - 3, rect.bottom - badge.get_height(),
                              badge.get_width() + 2, badge.get_height()))
            screen.blit(badge, (rect.right - badge.get_width() - 2,
                                rect.bottom - badge.get_height()))
        if g.get("hidden"):
            star = small_font.render("★", True, (255, 210, 110))
            screen.blit(star, (rect.x + 1, rect.y - 2))
        inv_rects.append(rect)
        inv_actions.append((g["kind"], g["idx"]))
        hover_items.append((g["kind"], g["q"], g["set"], rect, g.get("hidden")))

    # 翻页
    prev_btn = pygame.Rect(inv_x, inv_y + 6 * 44 + 4, 26, 22)
    next_btn = pygame.Rect(inv_x + 96, inv_y + 6 * 44 + 4, 26, 22)
    STATS_UI["prev"] = prev_btn
    STATS_UI["next"] = next_btn
    for btn, glyph in ((prev_btn, "<"), (next_btn, ">")):
        pygame.draw.rect(screen, (52, 46, 62), btn, border_radius=5)
        pygame.draw.rect(screen, (160, 150, 190), btn, 1, border_radius=5)
        g_surf = small_font.render(glyph, True, (225, 220, 240))
        screen.blit(g_surf, (btn.centerx - g_surf.get_width() // 2,
                             btn.centery - g_surf.get_height() // 2))
    page_txt = small_font.render(f"{page + 1} / {pages}", True, (210, 206, 225))
    screen.blit(page_txt, (inv_x + 36, inv_y + 6 * 44 + 5))

    # 悬停解释
    mouse = pygame.mouse.get_pos()
    for item in hover_items + EQUIP_RECTS:
        kind, q, set_key, rect = item[:4]
        hidden = item[4] if len(item) > 4 else getattr(pl, kind + "_hidden", None)
        if rect.collidepoint(mouse):
            draw_item_tooltip(screen, font, small_font, kind, q, set_key, pl,
                              (rect.right, rect.y), hidden)
            break

    sep_y = panel.y + 366
    pygame.draw.line(screen, (72, 60, 86), (inv_x, sep_y), (panel.right - 40, sep_y), 1)
    bag_y = sep_y + 28
    screen.blit(small_font.render("道具（数字键 1~4 使用）", True, (210, 206, 225)),
                (inv_x, bag_y - 22))
    for i, kind in enumerate(ITEM_SLOTS):
        rect = pygame.Rect(inv_x + i * 46, bag_y, 42, 42)
        pygame.draw.rect(screen, (54, 48, 64), rect, border_radius=5)
        art.draw_item_icon(screen, rect.x + 3, rect.y + 3, kind, Q_WHITE, None, 0)
        cnt = small_font.render(f"×{pl.bag.get(kind, 0)}", True, (255, 255, 255))
        screen.blit(cnt, (rect.right - cnt.get_width() - 2, rect.bottom - cnt.get_height()))

    tip = small_font.render("点装备穿戴 · 开「丢弃模式」后点击丢弃 · 电脑上也可右键丢弃",
                            True, (160, 156, 176))
    screen.blit(tip, (panel.x + 24, panel.bottom - 26))


# --------------------------------------------------------------------------
# 跟宠面板
# --------------------------------------------------------------------------
def draw_pet_panel(screen, level, font, small_font):
    pet = level.pet
    panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 190, 520, 380)
    art.panel(screen, panel, accent=(150, 255, 210), fill=(24, 34, 34), alpha=250, radius=14)
    screen.blit(font.render("跟宠", True, (190, 255, 226)), (panel.x + 24, panel.y + 14))

    PET_UI["close"] = pygame.Rect(panel.right - 46, panel.y + 10, 32, 32)
    pygame.draw.rect(screen, (44, 64, 60), PET_UI["close"], border_radius=9)
    pygame.draw.rect(screen, (170, 240, 210), PET_UI["close"], 1, border_radius=9)
    cross = font.render("×", True, (200, 255, 230))
    screen.blit(cross, (PET_UI["close"].centerx - cross.get_width() // 2,
                        PET_UI["close"].centery - cross.get_height() // 2 - 2))

    spr = art.pet_sprite(4 + pet.stage, False, pet.color)
    px, py = panel.x + 96, panel.y + 130
    art.blit_glow(screen, px, py, 60 + pet.stage * 10, pet.color, 60)
    screen.blit(spr, (px - spr.get_width() // 2, py - spr.get_height() // 2))

    name = art.label(f"{pet.stage_name}  Lv.{pet.level}", (210, 255, 236), 18, True)
    screen.blit(name, (px - name.get_width() // 2, py + 74))

    exp_need = max(1, pet.exp_need())
    exp_rect = pygame.Rect(panel.x + 30, py + 108, 132, 8)
    pygame.draw.rect(screen, (34, 52, 48), exp_rect, border_radius=4)
    pygame.draw.rect(screen, (120, 230, 190),
                     (exp_rect.x, exp_rect.y, int(exp_rect.w * pet.exp / exp_need), exp_rect.h),
                     border_radius=4)
    et = small_font.render(f"经验 {pet.exp}/{exp_need}", True, (170, 220, 200))
    screen.blit(et, (exp_rect.centerx - et.get_width() // 2, exp_rect.bottom + 2))

    tx = panel.x + 190
    ty = panel.y + 66
    base_atk = int((PET_ATTACK_DMG + level.player.level * 3 + pet.level * 3)
                   * (1 + pet.stage * 0.25))
    lines = [
        (f"定位: {pet.ROLE_TEXT.get(pet.kind, '')}", (200, 255, 230)),
        (f"等级: Lv.{pet.level}   阶段: {pet.stage_name} ({pet.stage + 1}/4)", (190, 210, 220)),
        (f"攻击: {base_atk}   冷却: {max(28, PET_ATTACK_CD - pet.stage * 10)} 帧", (220, 230, 240)),
        ("", (0, 0, 0)),
        ("技能", (255, 236, 200)),
    ]
    for i, (text, color) in enumerate(lines):
        if text:
            screen.blit(small_font.render(text, True, color), (tx, ty + i * 24))

    skills = PET_SKILLS[pet.kind]
    for i, (sname, sdesc, cd) in enumerate(skills):
        need = i + 1
        unlocked = pet.stage >= need
        y = ty + 5 * 24 + i * 40
        box = pygame.Rect(tx - 6, y - 4, panel.right - tx - 20, 34)
        pygame.draw.rect(screen, (36, 52, 48) if unlocked else (30, 32, 38), box, border_radius=6)
        pygame.draw.rect(screen, (120, 220, 180) if unlocked else (80, 82, 92), box, 1,
                         border_radius=6)
        title = f"{sname}" + ("" if unlocked else f"（阶段 {need} 解锁）")
        screen.blit(small_font.render(title, True,
                                      (220, 255, 236) if unlocked else (130, 132, 142)),
                    (box.x + 8, y))
        screen.blit(small_font.render(sdesc, True,
                                      (150, 180, 170) if unlocked else (110, 112, 122)),
                    (box.x + 8, y + 16))
        if unlocked:
            cd_left = max(0, pet.skill_cds[i])
            cd_txt = small_font.render("就绪" if cd_left == 0 else f"{cd_left / FPS:.1f}s",
                                       True, (170, 240, 200) if cd_left == 0 else (190, 200, 210))
            screen.blit(cd_txt, (box.right - cd_txt.get_width() - 8,
                                 box.centery - cd_txt.get_height() // 2))

    stage_y = panel.bottom - 34
    screen.blit(small_font.render("进化阶段:", True, (170, 200, 190)), (tx, stage_y))
    for i, nm in enumerate(PET_STAGE_NAMES):
        col = (120, 230, 190) if i <= pet.stage else (80, 90, 96)
        seg = pygame.Rect(tx + 74 + i * 62, stage_y - 1, 56, 18)
        pygame.draw.rect(screen, col, seg, border_radius=6)
        t = small_font.render(nm, True, (20, 30, 28) if i <= pet.stage else (140, 146, 150))
        screen.blit(t, (seg.centerx - t.get_width() // 2, seg.centery - t.get_height() // 2))

    screen.blit(small_font.render("每 3 级进化一次 · 技能自动释放 · 按 P 关闭", True, (140, 160, 155)),
                (panel.x + 24, panel.bottom - 20))


# --------------------------------------------------------------------------
# 通关页
# --------------------------------------------------------------------------
def draw_win_screen(screen, level, font, big_font, small_font):
    t = pygame.time.get_ticks() / 1000.0
    screen.fill((24, 17, 32))
    art.blit_glow(screen, WIDTH // 2, 190, 340, (255, 140, 200), 44)
    art.blit_glow(screen, WIDTH // 2, 470, 310, (140, 180, 255), 26)
    for i in range(52):
        px = (i * 137 + t * 24) % (WIDTH + 40) - 20
        py = (i * 71 + t * 44 + math.sin(t + i) * 12) % (HEIGHT + 40) - 20
        pygame.draw.ellipse(screen, (255, 188, 214), (px, py, 6, 3))
        pygame.draw.ellipse(screen, (255, 220, 236), (px + 1, py, 3, 2))

    panel = pygame.Rect(WIDTH // 2 - 300, 46, 600, 448)
    art.panel(screen, panel, accent=(255, 160, 210), fill=(32, 23, 42), alpha=245, radius=18)

    title = big_font.render("恭喜通关全部四大关卡！", True, (255, 206, 232))
    screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 10))
    sub = font.render("16 个小关全部通过，宝箱密码终于显现", True, (216, 200, 222))
    screen.blit(sub, (panel.centerx - sub.get_width() // 2, panel.y + 62))

    if level is not None:
        pl = level.player
        armor_color = (72, 132, 204) if pl.armor_quality == "none" else Q_COLOR[pl.armor_quality]
        head_color = HAIR_COLOR if pl.helmet_quality == "none" else Q_COLOR[pl.helmet_quality]
        dominant_set = pl.armor_set if pl.armor_quality != "none" else pl.weapon_set
        spr = art.player_sprite(armor_color, head_color, pl.weapon_type, dominant_set)
        base = pygame.Surface((spr.get_width() + 24, spr.get_height() + 24), pygame.SRCALPHA)
        base.blit(spr, (12, 20))
        art.draw_player_hat(base, 12, 20, pl.weapon_type, head_color)
        big = pygame.transform.scale(base, (base.get_width() * 2, base.get_height() * 2))
        px, py = panel.x + 92, panel.y + 186
        art.blit_glow(screen, px, py - 30, 64, (255, 190, 220), 60)
        screen.blit(big, (px - big.get_width() // 2, py - big.get_height() // 2))

        name = art.label(f"{CLASS_NAME[pl.weapon_type]}  Lv.{pl.level}", GOLD_COLOR, 17, True)
        screen.blit(name, (px - name.get_width() // 2, py + big.get_height() // 2 + 6))

        stats = [("攻击力", str(pl.get_damage())), ("防御力", str(pl.defense)),
                 ("法抗", str(pl.magic_resist)), ("跟宠", level.pet.role_text)]
        sy = panel.y + 116
        for label_text, value in stats:
            k = art.label(label_text, (190, 190, 210), 14)
            v = art.label(value, (255, 232, 240), 14, True)
            screen.blit(k, (panel.x + 206, sy))
            screen.blit(v, (panel.x + 320, sy))
            sy += 26

    code = FINAL_PASSWORD
    box_w, gap = 60, 16
    total_w = len(code) * box_w + (len(code) - 1) * gap
    bx = panel.centerx - total_w // 2
    by = panel.y + 268
    lab = art.label("宝箱密码", (255, 214, 160), 16, True)
    screen.blit(lab, (panel.centerx - lab.get_width() // 2, by - 32))
    for i, ch in enumerate(code):
        rect = pygame.Rect(bx + i * (box_w + gap), by, box_w, 70)
        pygame.draw.rect(screen, (48, 34, 60), rect, border_radius=10)
        pygame.draw.rect(screen, (255, 196, 120), rect, 2, border_radius=10)
        digit = big_font.render(ch, True, (255, 226, 150))
        screen.blit(digit, (rect.centerx - digit.get_width() // 2,
                            rect.centery - digit.get_height() // 2))

    WIN_UI["continue"] = pygame.Rect(panel.centerx - 214, panel.bottom - 62, 204, 44)
    WIN_UI["menu"] = pygame.Rect(panel.centerx + 10, panel.bottom - 62, 204, 44)
    for rect, text, accent, fill in (
            (WIN_UI["continue"], "继续挑战", (255, 200, 230), (62, 36, 62)),
            (WIN_UI["menu"], "返回主菜单", (190, 186, 205), (40, 34, 48))):
        art.panel(screen, rect, accent=accent, fill=fill, alpha=242, radius=10)
        t2 = font.render(text, True, (255, 240, 248))
        screen.blit(t2, (rect.centerx - t2.get_width() // 2, rect.centery - t2.get_height() // 2))


# --------------------------------------------------------------------------
# 主循环
# --------------------------------------------------------------------------
async def main():
    pygame.mixer.pre_init(22050, -16, 2, 1024)
    pygame.init()
    audio.init()
    prefs = save.load_prefs()
    if prefs.get("music") is False:
        audio.set_music_enabled(False)
    if prefs.get("sfx") is False:
        audio.set_sfx_enabled(False)
    audio.prewarm_music("boss", "victory")
    audio.play_music("menu")
    screen = None
    is_fullscreen = False
    is_web = (sys.platform == "emscripten")

    def apply_display(full):
        nonlocal screen, is_fullscreen
        if is_web:
            # 浏览器里尺寸由 canvas 决定，交给 pygbag 处理
            screen = pygame.display.set_mode((WIDTH, HEIGHT))
            is_fullscreen = False
            return
        is_fullscreen = full
        # 先试 SDL 自带的全屏切换（对 SCALED 最稳）
        try:
            surf = pygame.display.get_surface()
            if surf is not None and bool(surf.get_flags() & pygame.FULLSCREEN) != full:
                pygame.display.toggle_fullscreen()
                if bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN) == full:
                    return
        except Exception:
            pass
        # 再试重建显示表面
        flags = pygame.SCALED | (pygame.FULLSCREEN if full else pygame.RESIZABLE)
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except Exception:
            pass

    apply_display(False)
    pygame.display.set_caption("解密·四界征战")
    try:
        with open("audio_log.txt", "w", encoding="utf-8") as f:
            f.write(audio.diagnostics() + "\n")
    except Exception:
        pass
    print("[audio] " + audio.status().replace("\n", " "), flush=True)
    clock = pygame.time.Clock()
    font = art.font(24)
    big_font = art.font(42)
    small_font = art.font(16)

    game_state = "menu"
    saves = save.load_all()
    active_slot = saves["active"]

    def slot_data(i):
        return saves["slots"][i] if 0 <= i < len(saves["slots"]) else None

    def build_progress(slot):
        slot = slot or {}
        return {
            "weapon": slot.get("weapon", WEAPON_SWORD),
            "cleared": [int(x) for x in slot.get("cleared", [])
                        if isinstance(x, (int, float))],
            "player": slot.get("player"),
        }

    progress = build_progress(slot_data(active_slot))
    level = None
    current_level_idx = 0
    selected_weapon_type = WEAPON_SWORD
    collected_digits = []
    show_stats_panel = False
    show_map = False
    show_pet = False
    discard_mode = False
    retry_timer = 0

    joystick = Joystick(100, HEIGHT - 100, 60)
    attack_btn = pygame.Rect(WIDTH - 140, HEIGHT - 150, 90, 90)
    skill_btn = pygame.Rect(WIDTH - 240, HEIGHT - 160, 70, 70)
    skill2_btn = pygame.Rect(WIDTH - 330, HEIGHT - 160, 70, 70)
    skill3_btn = pygame.Rect(WIDTH - 420, HEIGHT - 160, 70, 70)
    jump_btn = pygame.Rect(WIDTH - 300, HEIGHT - 70, 60, 60)
    bag_btn = pygame.Rect(WIDTH - 80, 80, 50, 50)
    map_btn = pygame.Rect(WIDTH - 140, 80, 50, 50)
    pet_btn = pygame.Rect(WIDTH - 200, 80, 50, 50)
    menu_btn = pygame.Rect(WIDTH - 266, 80, 58, 50)

    item_rects = [pygame.Rect(WIDTH // 2 - 122 + i * 62, HEIGHT - 70, 54, 54)
                  for i in range(len(ITEM_SLOTS))]
    ui_feedback = {}

    inv_rects = []
    inv_actions = []

    menu_cards = [
        (WEAPON_SWORD, "剑士", "近战 · 高防", (116, 114, 170), pygame.Rect(104, 184, 186, 244)),
        (WEAPON_BOW, "弓箭手", "远程 · 灵活", (98, 158, 126), pygame.Rect(387, 184, 186, 244)),
        (WEAPON_STAFF, "法师", "远程 · 高伤", (154, 112, 172), pygame.Rect(670, 184, 186, 244)),
    ]
    level_cards = [pygame.Rect(104 + i * 192, 190, 170, 210) for i in range(LEVELS_PER_CHAPTER)]
    chapter_tabs = [pygame.Rect(60 + i * 216, 108, 204, 40) for i in range(len(CHAPTERS))]
    continue_btn = pygame.Rect(WIDTH // 2 - 248, 438, 496, 62)
    fs_btn = pygame.Rect(WIDTH - 152, 14, 134, 34)
    music_btn = pygame.Rect(WIDTH - 412, 14, 124, 34)
    sfx_btn = pygame.Rect(WIDTH - 282, 14, 124, 34)
    slot_tabs = [pygame.Rect(12 + i * 166, 10, 160, 46) for i in range(save.SLOT_COUNT)]
    quit_btn = pygame.Rect(WIDTH - 172, HEIGHT - 62, 160, 40)
    slot_del = [None] * save.SLOT_COUNT
    toast_timer = 0
    toast_text = ""
    select_chapter = 0

    def persist():
        nonlocal saves
        if level is not None and game_state in ("playing", "win"):
            progress["player"] = level.player.to_dict()
        save.write_slot(active_slot, {
            "weapon": progress["weapon"],
            "cleared": sorted(set(progress["cleared"])),
            "player": progress["player"],
        })
        saves = save.load_all()

    def switch_slot(i):
        nonlocal active_slot, progress, saves, game_state, level
        nonlocal show_stats_panel, show_map, show_pet, retry_timer, select_chapter
        if not (0 <= i < save.SLOT_COUNT) or i == active_slot:
            return
        persist()
        active_slot = i
        save.set_active(i)
        saves = save.load_all()
        progress = build_progress(saves["slots"][i])
        level = None
        game_state = "menu"
        show_stats_panel = show_map = show_pet = False
        retry_timer = 0
        if progress["cleared"]:
            select_chapter = min(len(CHAPTERS) - 1, max(progress["cleared"]) // 4)

    def delete_slot(i):
        nonlocal saves, progress, active_slot
        if not (0 <= i < save.SLOT_COUNT):
            return
        if i == active_slot:
            return                      # 当前槽请用“新游戏”覆盖，避免误删
        save.delete_slot(i)
        saves = save.load_all()

    def start_level(idx, fresh=False):
        nonlocal game_state, current_level_idx, level, collected_digits
        nonlocal show_stats_panel, show_map, show_pet, retry_timer, selected_weapon_type
        current_level_idx = idx
        collected_digits = []
        show_stats_panel = False
        show_map = False
        show_pet = False
        retry_timer = 0
        game_state = "playing"

        player_obj = None
        if not fresh and progress.get("player"):
            try:
                player_obj = Player.from_dict(progress["player"])
            except Exception:
                player_obj = None
        if player_obj is not None:
            selected_weapon_type = player_obj.weapon_type
        else:
            selected_weapon_type = progress.get("weapon", WEAPON_SWORD)
        level = Level(idx, selected_weapon_type, existing_player=player_obj)
        audio.play_music(level_theme(idx), force=True)
        joystick.reset()
        persist()

    def return_to_menu():
        nonlocal game_state, show_stats_panel, show_map, show_pet
        persist()
        show_stats_panel = False
        show_map = False
        show_pet = False
        game_state = "menu"
        audio.play_music("menu")

    def start_game(weapon_type):
        progress["weapon"] = weapon_type
        progress["cleared"] = []
        progress["player"] = None
        start_level(0, fresh=True)      # start_level 里的 persist 会写入当前槽

    def press_ui(name):
        ui_feedback[name] = pygame.time.get_ticks()

    def translate_event(raw):
        nonlocal show_stats_panel, show_map, show_pet
        if raw.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            pos = (raw.x * WIDTH, raw.y * HEIGHT)
            in_ui = (game_state != "playing") or show_stats_panel or show_map or show_pet or retry_timer > 0
            if in_ui:
                if raw.type == pygame.FINGERDOWN:
                    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
                if raw.type == pygame.FINGERUP:
                    return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})
                return None

            if raw.type == pygame.FINGERDOWN:
                fid = raw.finger_id
                if math.dist(pos, (joystick.center_x, joystick.center_y)) < joystick.radius * 1.9:
                    joystick.touch_start(fid, pos)
                elif attack_btn.collidepoint(pos):
                    press_ui("attack")
                    level.player.attack(level)
                elif skill_btn.collidepoint(pos):
                    press_ui("skill0")
                    level.cast_skill(0)
                elif skill2_btn.collidepoint(pos):
                    press_ui("skill1")
                    level.cast_skill(1)
                elif skill3_btn.collidepoint(pos):
                    press_ui("skill2")
                    level.cast_skill(2)
                elif jump_btn.collidepoint(pos):
                    press_ui("jump")
                    level.player.jump()
                elif bag_btn.collidepoint(pos):
                    press_ui("bag")
                    show_stats_panel = True
                elif map_btn.collidepoint(pos):
                    press_ui("map")
                    show_map = True
                elif pet_btn.collidepoint(pos):
                    press_ui("pet")
                    show_pet = True
                elif menu_btn.collidepoint(pos):
                    press_ui("menu")
                    return_to_menu()
                else:
                    for i, rect in enumerate(item_rects):
                        if rect.collidepoint(pos):
                            level.use_item(ITEM_SLOTS[i])
                            break
            elif raw.type == pygame.FINGERMOTION:
                joystick.touch_move(raw.finger_id, pos)
            else:
                joystick.touch_end(raw.finger_id)
            return None

        if getattr(raw, "touch", False) and raw.type in (
                pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            return None
        return raw

    running = True
    while running:
        for raw_event in pygame.event.get():
            event = translate_event(raw_event)
            if event is None:
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    apply_display(not is_fullscreen)
                if event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    delta = -0.06 if event.key == pygame.K_LEFTBRACKET else 0.06
                    audio.set_music_volume(audio.music_volume() + delta)
                if event.key in (pygame.K_MINUS, pygame.K_EQUALS):
                    delta = -0.08 if event.key == pygame.K_MINUS else 0.08
                    audio.set_sfx_volume(audio.sfx_volume() + delta)
                if event.key == pygame.K_ESCAPE:
                    if game_state == "playing":
                        return_to_menu()
                    elif game_state in ("win", "select"):
                        game_state = "menu"
                    else:
                        running = False

                if game_state == "menu":
                    if event.key == pygame.K_1:
                        start_game(WEAPON_SWORD)
                    elif event.key == pygame.K_2:
                        start_game(WEAPON_BOW)
                    elif event.key == pygame.K_3:
                        start_game(WEAPON_STAFF)
                    elif event.key == pygame.K_RETURN:
                        start_game(selected_weapon_type)
                    elif event.key == pygame.K_c:
                        if progress.get("player") or progress.get("cleared"):
                            game_state = "select"

                elif game_state == "playing":
                    if event.key in (pygame.K_i, pygame.K_TAB):
                        show_stats_panel = not show_stats_panel
                    if event.key == pygame.K_m:
                        show_map = not show_map
                    if event.key == pygame.K_p:
                        show_pet = not show_pet
                    if event.key == pygame.K_SPACE:
                        level.player.jump()
                    if event.key == pygame.K_j:
                        level.player.attack(level)
                    if event.key == pygame.K_k:
                        level.cast_skill(0)
                    if event.key == pygame.K_l:
                        level.cast_skill(1)
                    if event.key == pygame.K_u:
                        level.cast_skill(2)
                    for idx, hotkey in enumerate((pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)):
                        if event.key == hotkey:
                            level.use_item(ITEM_SLOTS[idx])

                elif game_state == "win":
                    if event.key == pygame.K_RETURN:
                        game_state = "select"

            if game_state == "menu":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, dr in enumerate(slot_del):
                        if dr is not None and dr.collidepoint(event.pos):
                            delete_slot(i)
                            break
                    else:
                        for i, tab in enumerate(slot_tabs):
                            if tab.collidepoint(event.pos):
                                switch_slot(i)
                                break
                    for w_type, _name, _desc, _color, rect in menu_cards:
                        if rect.collidepoint(event.pos):
                            start_game(w_type)
                            break
                    if (progress.get("player") or progress.get("cleared")) \
                            and continue_btn.collidepoint(event.pos):
                        game_state = "select"
                    if fs_btn.collidepoint(event.pos):
                        apply_display(not is_fullscreen)
                    if quit_btn.collidepoint(event.pos):
                        persist()
                        if is_web:
                            try:
                                import platform as _p
                                _p.window.location.reload()
                            except Exception:
                                pass
                        else:
                            running = False
                    if music_btn.collidepoint(event.pos):
                        audio.set_music_enabled(not audio.music_enabled())
                        save.save_prefs({"music": audio.music_enabled(),
                                         "sfx": audio.sfx_enabled()})
                        toast_text = "音乐已开启" if audio.music_enabled() else "音乐已关闭"
                        toast_timer = 90
                    if sfx_btn.collidepoint(event.pos):
                        audio.set_sfx_enabled(not audio.sfx_enabled())
                        save.save_prefs({"music": audio.music_enabled(),
                                         "sfx": audio.sfx_enabled()})
                        if audio.sfx_enabled():
                            audio.play("pickup", 0.9)
                        toast_text = "音效已开启" if audio.sfx_enabled() else "音效已关闭"
                        toast_timer = 90

            if game_state == "select":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    max_unlocked = (min(FINAL_LEVEL_INDEX, max(progress["cleared"]) + 1)
                                    if progress["cleared"] else 0)
                    for ci, tab in enumerate(chapter_tabs):
                        if tab.collidepoint(event.pos) and ci * 4 <= max_unlocked:
                            select_chapter = ci
                    for i, rect in enumerate(level_cards):
                        idx = select_chapter * 4 + i
                        if rect.collidepoint(event.pos) and idx <= max_unlocked:
                            start_level(idx)
                            break
                    if SELECT_UI["back"].collidepoint(event.pos):
                        game_state = "menu"

            if game_state == "win":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if WIN_UI["continue"].collidepoint(event.pos):
                        game_state = "select"
                    elif WIN_UI["menu"].collidepoint(event.pos):
                        game_state = "menu"

            if game_state == "playing" and retry_timer == 0:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if show_stats_panel:
                        if event.button == 1 and STATS_UI["close"].collidepoint(event.pos):
                            show_stats_panel = False
                            discard_mode = False
                        elif event.button == 1 and STATS_UI["discard"].collidepoint(event.pos):
                            discard_mode = not discard_mode
                        elif (event.button == 1 and "prev" in STATS_UI
                              and STATS_UI["prev"].collidepoint(event.pos)):
                            BAG_PAGE["page"] = max(0, BAG_PAGE["page"] - 1)
                        elif (event.button == 1 and "next" in STATS_UI
                              and STATS_UI["next"].collidepoint(event.pos)):
                            BAG_PAGE["page"] += 1
                        elif event.button == 1:
                            for rect, action in zip(inv_rects, inv_actions):
                                if rect.collidepoint(event.pos):
                                    if discard_mode:
                                        dropped = discard_from_inventory(
                                            level.player, action[0], action[1])
                                        if dropped:
                                            level.float_texts.append(FloatText(
                                                level.player.rect.centerx,
                                                level.player.rect.top - 10,
                                                f"丢弃 {Q_NAME[dropped]}装备",
                                                (220, 200, 220), 14, 50))
                                    else:
                                        equip_from_inventory(level.player, action[0], action[1])
                                    break
                        elif event.button == 3:
                            for rect, action in zip(inv_rects, inv_actions):
                                if rect.collidepoint(event.pos):
                                    dropped = discard_from_inventory(level.player, action[0], action[1])
                                    if dropped:
                                        level.float_texts.append(FloatText(
                                            level.player.rect.centerx, level.player.rect.top - 10,
                                            f"丢弃 {Q_NAME[dropped]}装备", (220, 200, 220), 14, 50))
                                    break
                        continue

                    if show_pet:
                        if event.button == 1 and PET_UI["close"].collidepoint(event.pos):
                            show_pet = False
                        continue

                    if show_map:
                        show_map = False
                        continue

                    if event.button == 1:
                        joystick.handle_event(event)
                        if attack_btn.collidepoint(event.pos):
                            press_ui("attack")
                            level.player.attack(level)
                        if skill_btn.collidepoint(event.pos):
                            press_ui("skill0")
                            level.cast_skill(0)
                        if skill2_btn.collidepoint(event.pos):
                            press_ui("skill1")
                            level.cast_skill(1)
                        if skill3_btn.collidepoint(event.pos):
                            press_ui("skill2")
                            level.cast_skill(2)
                        if jump_btn.collidepoint(event.pos):
                            press_ui("jump")
                            level.player.jump()
                        if bag_btn.collidepoint(event.pos):
                            press_ui("bag")
                            show_stats_panel = not show_stats_panel
                            if not show_stats_panel:
                                discard_mode = False
                        if map_btn.collidepoint(event.pos):
                            press_ui("map")
                            show_map = not show_map
                        if pet_btn.collidepoint(event.pos):
                            press_ui("pet")
                            show_pet = not show_pet
                        if menu_btn.collidepoint(event.pos):
                            press_ui("menu")
                            return_to_menu()
                        for idx, rect in enumerate(item_rects):
                            if rect.collidepoint(event.pos):
                                level.use_item(ITEM_SLOTS[idx])
        joystick.update()

        audio.ensure_music()
        if toast_timer > 0:
            toast_timer -= 1

        # ---------------- 更新 ----------------
        if game_state == "playing":
            if retry_timer > 0:
                retry_timer -= 1
                if retry_timer == 0:
                    level = Level(current_level_idx, selected_weapon_type,
                                  existing_player=level.player)
            elif not show_stats_panel and not show_map and not show_pet:
                keys = pygame.key.get_pressed()
                move_x, move_y = 0, 0
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    move_x = -1
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    move_x = 1
                if keys[pygame.K_UP] or keys[pygame.K_w]:
                    move_y = -1
                if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    move_y = 1

                if move_x == 0 and move_y == 0:
                    if abs(joystick.dx) > 0.1 or abs(joystick.dy) > 0.1:
                        move_x, move_y = joystick.dx, joystick.dy

                level.player.move(move_x, move_y, level.collision_walls())
                level.update()

                if level.player.hp <= 0:
                    retry_timer = 90
                else:
                    if level.door_open and level.player.rect.colliderect(level.door_rect):
                        collected_digits.append(str(random.randint(0, 9)))
                        if current_level_idx not in progress["cleared"]:
                            progress["cleared"].append(current_level_idx)
                        persist()
                        current_level_idx += 1
                        if current_level_idx >= TOTAL_LEVELS:
                            progress["cleared"] = list(range(TOTAL_LEVELS))
                            persist()
                            game_state = "win"
                            audio.play("win")
                        else:
                            level = Level(current_level_idx, selected_weapon_type,
                                          existing_player=level.player)

        # ---------------- 摄像机 ----------------
        map_w = len(level.map_data[0]) * TILE_SIZE if level else 0
        map_h = len(level.map_data) * TILE_SIZE if level else 0

        cam_x, cam_y = 0, 0
        if level:
            cam_x = max(0, min(level.player.rect.centerx - WIDTH // 2, map_w - WIDTH))
            cam_y = max(0, min(level.player.rect.centery - HEIGHT // 2, map_h - HEIGHT))
            if level.shake > 0:
                cam_x = max(0, min(cam_x + random.randint(-level.shake, level.shake), map_w - WIDTH))
                cam_y = max(0, min(cam_y + random.randint(-level.shake, level.shake), map_h - HEIGHT))

        # ---------------- 绘制 ----------------
        if game_state == "menu":
            if audio.music_name() != "menu":
                audio.play_music("menu")
            screen.fill((16, 14, 24))
            for y in range(0, HEIGHT, 6):
                shade = 18 + y // 12
                pygame.draw.rect(screen, (shade, shade - 2, shade + 10), (0, y, WIDTH, 6))
            art.blit_glow(screen, 170, 94, 150, (120, 210, 150), 30)
            art.blit_glow(screen, WIDTH // 2, 78, 220, (255, 164, 208), 38)
            art.blit_glow(screen, WIDTH - 170, 102, 170, (140, 180, 255), 28)

            hero_panel = pygame.Rect(WIDTH // 2 - 318, 50, 636, 104)
            art.panel(screen, hero_panel, accent=(255, 196, 230), fill=(30, 24, 42), alpha=245, radius=16)
            title = big_font.render("解密·四界征战", True, GOLD_COLOR)
            screen.blit(title, (hero_panel.centerx - title.get_width() // 2, hero_panel.y + 10))
            pygame.draw.line(screen, (96, 80, 116),
                             (hero_panel.x + 74, hero_panel.y + 42),
                             (hero_panel.right - 74, hero_panel.y + 42), 1)
            sub = small_font.render("选择职业，穿越森林 / 深海 / 天空 / 熔火四大关卡", True, (228, 216, 236))
            screen.blit(sub, (hero_panel.centerx - sub.get_width() // 2, hero_panel.y + 50))
            tags = [("森林", CHAPTERS[0]["color"]), ("海洋", CHAPTERS[1]["color"]),
                    ("天空", CHAPTERS[2]["color"]), ("火山", CHAPTERS[3]["color"])]
            for i, (label_txt, accent) in enumerate(tags):
                badge = pygame.Rect(hero_panel.x + 82 + i * 120, hero_panel.y + 74, 92, 20)
                art.panel(screen, badge, accent=accent, fill=(42, 32, 54), alpha=238, radius=8)
                tag = small_font.render(label_txt, True, (245, 238, 246))
                screen.blit(tag, (badge.centerx - tag.get_width() // 2, badge.centery - tag.get_height() // 2))

            mouse_pos = pygame.mouse.get_pos()

            # 三个角色存档槽
            for i, tab in enumerate(slot_tabs):
                info = save.slot_info(slot_data(i))
                is_active = (i == active_slot)
                accent = (255, 214, 238) if is_active else (128, 126, 152)
                art.panel(screen, tab, accent=accent,
                          fill=(60, 40, 72) if is_active else (28, 24, 36),
                          alpha=238, radius=10)
                head_txt = f"存档 {i + 1}"
                if not info["empty"]:
                    head_txt += f"   Lv.{info['level']}"
                head = small_font.render(head_txt, True,
                                         (255, 236, 246) if not info["empty"] else (150, 148, 164))
                screen.blit(head, (tab.x + 10, tab.y + 3))
                if info["empty"]:
                    sub_txt = "点击选择职业开始"
                else:
                    cls = CLASS_NAME.get(info["weapon"], "")
                    sub_txt = f"{cls} · {info['cleared']}/16"
                sub = small_font.render(sub_txt, True, (198, 194, 212))
                screen.blit(sub, (tab.x + 10, tab.y + 23))

                slot_del[i] = None
                if not info["empty"] and not is_active:
                    dr = pygame.Rect(tab.right - 22, tab.y + 4, 17, 17)
                    slot_del[i] = dr
                    pygame.draw.rect(screen, (92, 40, 50), dr, border_radius=5)
                    pygame.draw.rect(screen, (255, 160, 170), dr, 1, border_radius=5)
                    cross = small_font.render("×", True, (255, 200, 210))
                    screen.blit(cross, (dr.centerx - cross.get_width() // 2,
                                        dr.centery - cross.get_height() // 2 - 1))

            preview_sets = {WEAPON_SWORD: "volcano", WEAPON_BOW: "forest", WEAPON_STAFF: "sky"}
            preview_heads = {WEAPON_SWORD: (190, 120, 110), WEAPON_BOW: (96, 188, 126), WEAPON_STAFF: (164, 132, 214)}
            for w_type, name, desc, color, rect in menu_cards:
                hovered = rect.collidepoint(mouse_pos)
                is_selected = (w_type == selected_weapon_type)
                accent = GOLD_COLOR if is_selected else tuple(min(255, c + 36) for c in color)
                fill = (56, 40, 68) if hovered or is_selected else (34, 28, 44)
                art.panel(screen, rect, accent=accent, fill=fill, alpha=244, radius=16)
                if hovered:
                    pygame.draw.rect(screen, (255, 240, 250), rect.inflate(8, 8), 2, border_radius=20)

                art.blit_glow(screen, rect.centerx, rect.y + 72, 52, color, 36)
                spr = art.player_sprite((110, 126, 180), preview_heads[w_type],
                                        w_type, preview_sets[w_type])
                spr = pygame.transform.scale(spr, (spr.get_width() * 2, spr.get_height() * 2))
                screen.blit(spr, (rect.centerx - spr.get_width() // 2, rect.y + 26))
                art.draw_item_icon(screen, rect.centerx + 44, rect.y + 22, "weapon", Q_WHITE, w_type, 0,
                                   set_key=preview_sets[w_type])

                name_surf = font.render(name, True, (255, 248, 252))
                screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.y + 118))
                desc_surf = small_font.render(desc, True, (220, 216, 232))
                screen.blit(desc_surf, (rect.centerx - desc_surf.get_width() // 2, rect.y + 142))
                badge = pygame.Rect(rect.x + 18, rect.y + 18, 58, 18)
                art.panel(screen, badge, accent=color, fill=(34, 28, 40), alpha=232, radius=8)
                klass = small_font.render("已选" if is_selected else "职业", True, (244, 238, 245))
                screen.blit(klass, (badge.centerx - klass.get_width() // 2, badge.centery - klass.get_height() // 2))
                pygame.draw.line(screen, (88, 76, 102), (rect.x + 18, rect.y + 166), (rect.right - 18, rect.y + 166), 1)
                role_label = small_font.render("定位", True, (174, 168, 196))
                screen.blit(role_label, (rect.x + 22, rect.y + 146))
                skill_title = small_font.render("技能特性", True, (200, 196, 214))
                screen.blit(skill_title, (rect.x + 22, rect.y + 174))
                for i, _slot in enumerate((0, 1, 2)):
                    sk = [SKILL_BY_WEAPON, SKILL2_BY_WEAPON, SKILL3_BY_WEAPON][i][w_type]
                    key_hint = ("K", "L", "U")[i]
                    sk_surf = small_font.render(f"{key_hint}  {sk['name']}", True, sk["color"])
                    screen.blit(sk_surf, (rect.x + 22, rect.y + 194 + i * 15))

            # 全屏按钮
            if not is_web:
                fs_hover = fs_btn.collidepoint(mouse_pos)
                art.panel(screen, fs_btn, accent=(200, 220, 255) if fs_hover else (140, 150, 180),
                          fill=(30, 34, 46), alpha=225, radius=8)
                fs_label = small_font.render("窗口模式" if is_fullscreen else "全屏 F11",
                                             True, (225, 232, 250))
                screen.blit(fs_label, (fs_btn.centerx - fs_label.get_width() // 2,
                                       fs_btn.centery - fs_label.get_height() // 2))

            # 音频状态 + 音乐/音效开关
            st_color = (150, 255, 190) if audio.available() else (255, 160, 160)
            screen.blit(small_font.render(audio.status() + "   v1.1", True, st_color), (14, HEIGHT - 24))
            for btn, on, on_text, off_text in (
                    (music_btn, audio.music_enabled(), "音乐 开", "音乐 关"),
                    (sfx_btn, audio.sfx_enabled(), "音效 开", "音效 关")):
                hover = btn.collidepoint(mouse_pos)
                accent = (150, 255, 190) if on else (150, 120, 130)
                art.panel(screen, btn, accent=accent,
                          fill=(26, 40, 34) if on else (36, 26, 32), alpha=228, radius=8)
                if hover:
                    pygame.draw.rect(screen, (255, 240, 250), btn.inflate(4, 4), 1,
                                     border_radius=10)
                label = small_font.render(on_text if on else off_text, True,
                                          (200, 255, 226) if on else (230, 190, 196))
                screen.blit(label, (btn.centerx - label.get_width() // 2,
                                    btn.centery - label.get_height() // 2))

            has_progress = bool(progress.get("player")) or bool(progress.get("cleared"))
            if has_progress:
                hover = continue_btn.collidepoint(mouse_pos)
                art.panel(screen, continue_btn,
                          accent=(255, 220, 240) if hover else (255, 170, 214),
                          fill=(52, 34, 66), alpha=238, radius=14)
                lv_txt = ""
                if progress.get("player"):
                    lv_txt = (f"Lv.{progress['player'].get('level', 1)}  "
                              f"{CLASS_NAME.get(progress['player'].get('weapon_type', WEAPON_SWORD), '剑士')}  ")
                cont_main = font.render("继续冒险", True, (255, 232, 242))
                cont_sub = small_font.render(
                    f"存档 {active_slot + 1}  ·  {lv_txt}已通关 {len(progress['cleared'])}/{TOTAL_LEVELS}  ·  按 C",
                    True, (228, 206, 222))
                screen.blit(cont_main, (continue_btn.centerx - cont_main.get_width() // 2, continue_btn.y + 7))
                screen.blit(cont_sub, (continue_btn.centerx - cont_sub.get_width() // 2, continue_btn.y + 34))
            hint = small_font.render("点击职业卡片开始新游戏", True, (206, 200, 218))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 42))
            hint2 = small_font.render("快捷键：1 / 2 / 3 选择职业，回车确认当前职业", True, (170, 164, 188))
            screen.blit(hint2, (WIDTH // 2 - hint2.get_width() // 2, HEIGHT - 24))
            # 退出游戏
            q_hover = quit_btn.collidepoint(mouse_pos)
            art.panel(screen, quit_btn,
                      accent=(255, 170, 170) if q_hover else (150, 110, 120),
                      fill=(46, 24, 30) if q_hover else (30, 22, 28),
                      alpha=235, radius=10)
            q_text = "重新开始" if is_web else "退出游戏"
            q_label = small_font.render(q_text, True, (255, 200, 200))
            screen.blit(q_label, (quit_btn.centerx - q_label.get_width() // 2,
                                  quit_btn.centery - q_label.get_height() // 2))

            if toast_timer > 0:
                toast = font.render(toast_text, True, (255, 255, 255))
                box = pygame.Rect(0, 0, toast.get_width() + 36, 44)
                box.center = (WIDTH // 2, HEIGHT - 96)
                art.panel(screen, box, accent=(255, 220, 240), fill=(40, 28, 46), alpha=245,
                          radius=10)
                screen.blit(toast, (box.centerx - toast.get_width() // 2,
                                    box.centery - toast.get_height() // 2))

        elif game_state == "select":
            if audio.music_name() != "menu":
                audio.play_music("menu")
            screen.fill((20, 16, 30))
            art.blit_glow(screen, WIDTH // 2, 100, 300, (255, 150, 200), 32)
            title = big_font.render("选择关卡", True, (255, 206, 232))
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 22))
            sub = small_font.render("已通关的关卡可重复挑战 · 进度自动保存", True, (200, 196, 215))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 78))

            max_unlocked = (min(FINAL_LEVEL_INDEX, max(progress["cleared"]) + 1)
                            if progress["cleared"] else 0)
            mouse = pygame.mouse.get_pos()

            for ci, ch in enumerate(CHAPTERS):
                tab = chapter_tabs[ci]
                cleared_n = sum(1 for i in range(ci * 4, ci * 4 + 4)
                                if i in progress["cleared"])
                active = (ci == select_chapter)
                unlocked_chapter = ci * 4 <= max_unlocked
                accent = ch["color"] if (active or unlocked_chapter) else (86, 82, 100)
                art.panel(screen, tab, accent=accent,
                          fill=(50, 34, 58) if active else (28, 24, 36), alpha=240, radius=10)
                label = small_font.render(f"{ch['name']}  {cleared_n}/4", True,
                                          (255, 236, 246) if unlocked_chapter else (120, 118, 130))
                screen.blit(label, (tab.centerx - label.get_width() // 2,
                                    tab.centery - label.get_height() // 2))

            for i in range(LEVELS_PER_CHAPTER):
                idx = select_chapter * 4 + i
                rect = level_cards[i]
                cleared = idx in progress["cleared"]
                unlocked = idx <= max_unlocked
                hovered = unlocked and rect.collidepoint(mouse)
                accent = (255, 200, 230) if unlocked else (86, 82, 100)
                art.panel(screen, rect, accent=accent,
                          fill=(44, 32, 56) if unlocked else (26, 24, 32), alpha=238, radius=12)
                if hovered:
                    pygame.draw.rect(screen, (255, 226, 245), rect.inflate(6, 6), 2,
                                     border_radius=14)
                num = font.render(f"第 {idx + 1} 关", True,
                                  (255, 226, 240) if unlocked else (120, 118, 130))
                screen.blit(num, (rect.centerx - num.get_width() // 2, rect.y + 8))
                nm = small_font.render(CHAPTERS[select_chapter]["levels"][i], True,
                                       (225, 214, 232) if unlocked else (110, 108, 120))
                screen.blit(nm, (rect.centerx - nm.get_width() // 2, rect.y + 40))
                bt = small_font.render(f"BOSS ×{boss_count(idx)}", True,
                                       (255, 180, 190) if unlocked else (100, 98, 110))
                screen.blit(bt, (rect.centerx - bt.get_width() // 2, rect.y + 62))

                if unlocked:
                    roster = BOSS_ROSTER[level_theme(idx)]
                    spr = art.boss_sprite(roster[0][0], idx)
                    small_spr = pygame.transform.smoothscale(
                        spr, (max(1, spr.get_width() // 2), max(1, spr.get_height() // 2)))
                    art.blit_glow(screen, rect.centerx, rect.y + 124, 34,
                                  CHAPTERS[select_chapter]["color"], 45)
                    screen.blit(small_spr, (rect.centerx - small_spr.get_width() // 2,
                                            rect.y + 124 - small_spr.get_height() // 2))
                else:
                    lock_y = rect.y + 112
                    pygame.draw.rect(screen, (120, 118, 134),
                                     (rect.centerx - 12, lock_y + 8, 24, 18), border_radius=4)
                    pygame.draw.arc(screen, (120, 118, 134),
                                    (rect.centerx - 9, lock_y - 6, 18, 26), 0.2, math.pi - 0.2, 3)

                if cleared:
                    status, color = "已通关", (140, 255, 170)
                elif unlocked:
                    status, color = "可挑战", (255, 226, 150)
                else:
                    status, color = "未解锁", (130, 128, 140)
                st = small_font.render(status, True, color)
                screen.blit(st, (rect.centerx - st.get_width() // 2, rect.bottom - 28))

            SELECT_UI["back"] = pygame.Rect(WIDTH // 2 - 110, HEIGHT - 52, 220, 38)
            art.panel(screen, SELECT_UI["back"], accent=(200, 190, 215),
                      fill=(38, 30, 48), alpha=238, radius=10)
            back = small_font.render("返回主菜单", True, (225, 218, 236))
            screen.blit(back, (SELECT_UI["back"].centerx - back.get_width() // 2,
                               SELECT_UI["back"].centery - back.get_height() // 2))

        elif game_state == "playing":
            level.draw(screen, cam_x, cam_y)

            if retry_timer == 0 and not show_stats_panel:
                now = pygame.time.get_ticks()
                joystick.draw(screen)
                _draw_round_action_button(screen, attack_btn.center, 45, (214, 76, 126), "攻", font,
                                          glow=(255, 96, 150), tag="ATT", tag_font=small_font,
                                          pressed_at=ui_feedback.get("attack"), now=now)

                draw_skill_button(screen, skill_btn, level.player, 0, font, small_font, "K",
                                  pressed_at=ui_feedback.get("skill0"), now=now)
                draw_skill_button(screen, skill2_btn, level.player, 1, font, small_font, "L",
                                  pressed_at=ui_feedback.get("skill1"), now=now)
                draw_skill_button(screen, skill3_btn, level.player, 2, font, small_font, "U",
                                  pressed_at=ui_feedback.get("skill2"), now=now)

                _draw_round_action_button(screen, jump_btn.center, 30, (88, 196, 214), "跳", font,
                                          text_color=(8, 18, 26), glow=(110, 228, 244),
                                          tag="JMP", tag_font=small_font,
                                          pressed_at=ui_feedback.get("jump"), now=now)

                for key, btn, text, col in (("bag", bag_btn, "包", (200, 200, 200)),
                                            ("map", map_btn, "图", (190, 200, 220)),
                                            ("pet", pet_btn, "宠", (220, 190, 230)),
                                            ("menu", menu_btn, "菜单", (255, 200, 180))):
                    scale = _press_scale(ui_feedback.get(key), now, min_scale=0.93)
                    draw_rect = btn.inflate(int(btn.w * (scale - 1.0)), int(btn.h * (scale - 1.0)))
                    art.panel(screen, draw_rect, accent=col, fill=(40, 32, 54), alpha=228, radius=8)
                    shine = pygame.Rect(draw_rect.x + 4, draw_rect.y + 4,
                                        draw_rect.w - 8, max(6, draw_rect.h // 3))
                    pygame.draw.rect(screen, (255, 255, 255, 18), shine, border_radius=4)
                    pygame.draw.rect(screen, _mix(col, (255, 245, 220), 0.18),
                                     (draw_rect.x + 3, draw_rect.y + 3, draw_rect.w - 6, 2))
                    t = font.render(text, True, col)
                    screen.blit(t, (draw_rect.centerx - t.get_width() // 2,
                                    draw_rect.centery - t.get_height() // 2))

            draw_hud(screen, level, font, small_font, item_rects, collected_digits,
                     show_items=not show_stats_panel)

            if retry_timer > 0:
                shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                shade.fill((0, 0, 0, 180))
                screen.blit(shade, (0, 0))
                screen.blit(big_font.render("挑战失败，重新开始...", True, (255, 100, 120)),
                            (WIDTH // 2 - 220, HEIGHT // 2))

            if show_map:
                level.draw_map_overlay(screen)
            if show_stats_panel:
                draw_stats_panel(screen, level, font, small_font, inv_rects, inv_actions,
                                 discard_mode)
            if show_pet:
                draw_pet_panel(screen, level, font, small_font)

        elif game_state == "win":
            if audio.music_name() != "victory":
                audio.play_music("victory")
            draw_win_screen(screen, level, font, big_font, small_font)

        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)

    persist()
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
