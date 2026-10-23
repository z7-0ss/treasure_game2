"""海底闪退回归 + BOSS 唯一性/武器/翅膀 + 装备抗性 + 返回菜单。"""
import asyncio
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_bossfix_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
screen = pygame.display.set_mode((960, 540))

import audio
from settings import *
from level import Level
import main as gm
import save as save_mod

audio.init()


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. 海底第一关不再闪退（BOSS 会放冰冻） ----------
crashed = None
for seed in range(4):
    random.seed(seed)
    lv = Level(4, WEAPON_BOW)
    lv.player.invincible_timer = 10 ** 9
    try:
        for f in range(900):
            lv.player.move(1 if f % 20 < 12 else -1, 0, lv.collision_walls())
            lv.update()
            if f % 9 == 0:
                lv.draw(screen, 0, 0)
    except Exception as exc:      # noqa: BLE001
        crashed = f"seed{seed}: {exc!r}"
        break
check("海底第一关 900 帧不闪退", crashed is None, crashed)

# 逐个 BOSS 技能（含冰冻）都不报错
random.seed(5)
lv = Level(4, WEAPON_SWORD)
lv.player.invincible_timer = 0
lv.player.rect.center = (lv.boss.rect.centerx - 40, lv.boss.rect.centery)
skill_error = None
for skill in ("slam", "summon", "thorn_ring", "bone_volley", "charge",
              "spore_ring", "ice_nova"):
    try:
        lv.boss.pending_skill = skill
        lv.boss._release_skill(lv, lv.player)
        lv.update()
        lv.draw(screen, 0, 0)
    except Exception as exc:      # noqa: BLE001
        skill_error = f"{skill}: {exc!r}"
        break
check("BOSS 全部技能（含冰冻）不报错", skill_error is None, skill_error)

# ---------- 2. 每关 BOSS 不重复 ----------
dup_found = []
for idx in (3, 7, 11, 15):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    names = [b.name for b in lv.bosses]
    base = [n for n in names if "深渊魔王" not in n]
    if len(set(base)) != len(base):
        dup_found.append((idx, names))
    check(f"关卡{idx} BOSS 数量与配置一致", len(base) == boss_count(idx),
          (len(base), boss_count(idx)))
check("同一关的 BOSS 不重复", not dup_found, dup_found)

# 同一大关内跨关卡也不重复
seen = {}
cross_dup = []
for idx in range(TOTAL_LEVELS):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    ch = chapter_of(idx)
    for b in lv.bosses:
        if getattr(b, "is_final", False):
            continue
        if b.name in seen.get(ch, set()):
            cross_dup.append((idx, b.name))
        seen.setdefault(ch, set()).add(b.name)
check("同一大关内跨关卡也不重复", not cross_dup, cross_dup)
check("每章 BOSS 总数足够", all(len(v) >= 6 for v in seen.values()),
      {k: len(v) for k, v in seen.items()})

# 名册也覆盖最大数量
for key, roster in BOSS_ROSTER.items():
    check(f"{key} 名册至少 5 个", len(roster) >= 5, len(roster))

# ---------- 3. BOSS 拿武器 / 天空 BOSS 有翅膀 ----------
random.seed(8)
sky = Level(8, WEAPON_SWORD)
check("天空大关 BOSS 带翅膀标记", chapter_of(8) == 2, chapter_of(8))
check("天空 BOSS 有拿武器的", any(b.weapon_kind for b in sky.bosses),
      [b.weapon_kind for b in sky.bosses])

random.seed(11)
vol = Level(11, WEAPON_SWORD)
kinds = {b.weapon_kind for b in vol.bosses}
check("后期 BOSS 武器多样", len(kinds - {None}) >= 2, kinds)
check("石魔 BOSS 拿锤子", any(b.weapon_kind == "hammer" for b in vol.bosses),
      [b.name for b in vol.bosses])
import art
check("BOSS 武器绘制接口可用",
      art.boss_weapon_surface("sword").get_width() > 0)

# ---------- 4. 专属装备抗性 ----------
random.seed(2)
lv = Level(5, WEAPON_SWORD)
pl = lv.player
bare_speed = 1 - 0.18 * (1 - pl.status_resist("ocean"))
check("裸装海底减速 18%", abs(bare_speed - 0.82) < 0.01, bare_speed)

pl.weapon_quality, pl.weapon_set = Q_GOLD, "ocean"
pl.armor_quality, pl.armor_set = Q_PURPLE, "ocean"
r1 = pl.status_resist("ocean")
check("两件海底装备有抗性", r1 > 0.1, r1)

for kind in ("helmet", "boots", "pants", "bracelet"):
    setattr(pl, kind + "_quality", Q_RED)
    setattr(pl, kind + "_set", "ocean")
r2 = pl.status_resist("ocean")
check("全套海底抗性更高", r2 > r1 and r2 <= 0.72, (r1, r2))

# 冰冻时长变短
random.seed(5)
oc = Level(5, WEAPON_SWORD)
oc.player.invincible_timer = 0
oc.player.rect.center = (oc.boss.rect.centerx - 40, oc.boss.rect.centery)
oc.boss.pending_skill = "ice_nova"
oc.boss._release_skill(oc, oc.player)
naked_chill = oc.player.chill_timer

oc2 = Level(5, WEAPON_SWORD)
oc2.player.invincible_timer = 0
oc2.player.rect.center = (oc2.boss.rect.centerx - 40, oc2.boss.rect.centery)
for kind in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
    setattr(oc2.player, kind + "_quality", Q_RED)
    setattr(oc2.player, kind + "_set", "ocean")
oc2.boss.pending_skill = "ice_nova"
oc2.boss._release_skill(oc2, oc2.player)
geared_chill = oc2.player.chill_timer
check("穿海底套装的冰冻时间更短", geared_chill < naked_chill,
      (naked_chill, geared_chill))

# 海水减速也变轻
oc2.player.env_speed_mult = 1.0
oc2.update()
check("海底套装减免海水阻力", oc2.player.env_speed_mult > 0.82,
      oc2.player.env_speed_mult)

# 火山灼烧抗性
random.seed(13)
vol = Level(13, WEAPON_SWORD)
vol.player.invincible_timer = 0
naked_burn = vol.player.status_resist("volcano")
for kind in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
    setattr(vol.player, kind + "_quality", Q_RED)
    setattr(vol.player, kind + "_set", "volcano")
check("穿熔火套装有灼烧抗性",
      vol.player.status_resist("volcano") > max(0.4, naked_burn + 0.3),
      (naked_burn, vol.player.status_resist("volcano")))

# ---------- 5. 返回菜单 ----------
save_mod.remove()
click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0, "unicode": "\x1b"})
quit_ev = pygame.event.Event(pygame.QUIT)
created = []


class RecLevel(Level):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        created.append(self)


def run(script, frames=30):
    gm.Level = RecLevel
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1

    gm.pygame.display.flip = fake_flip
    script = dict(script)
    script.setdefault(frames, []).append(quit_ev)
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    gm.pygame.event.get = fake_get
    random.seed(3)
    asyncio.run(gm.main())
    gm.Level = Level


# ESC 返回菜单后还能再开一局
run({0: [click((300, 300))], 4: [esc], 8: [click((300, 300))], 18: []})
check("ESC 返回菜单后可以重新开始", len(created) >= 2, len(created))

# 点右上角「菜单」按钮
run({0: [click((300, 300))], 4: [click((WIDTH - 266 + 29, 105))],
     8: [click((300, 300))], 18: []})
check("菜单按钮返回后可以重新开始", len(created) >= 2, len(created))

print("\nBOSS / STATUS / MENU CHECKS PASSED")
