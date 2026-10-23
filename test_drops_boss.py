"""掉落回调 / BOSS 3 件 / 神话隐藏属性 / BOSS 难度 / 退出按钮 校验。"""
import asyncio
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_drop_boss.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
screen = pygame.display.set_mode((960, 540))

import art
import audio
import level as level_mod
import main as gm
import save as save_mod
from level import Level
from settings import *

audio.init()
font, small_font = art.font(24), art.font(16)


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


GEAR = ("weapon", "armor", "helmet", "boots", "pants", "bracelet")

# ---------- 1. 普通怪爆率回调 ----------
random.seed(11)
lv = Level(3, WEAPON_SWORD)
enemy = lv.enemies[0] if lv.enemies else None
if enemy is None:
    lv.spawn_enemy()
    enemy = lv.enemies[-1]
enemy.is_elite = False
lv.items.clear()
N = 3000
for _ in range(N):
    lv.handle_drops(enemy, drop_key=False)
gear_drops = sum(1 for i in lv.items if i.type in GEAR)
rate = gear_drops / N
check("普通装备爆率明显下调（< 22%）", rate < 0.22, round(rate, 3))
check("普通装备爆率不会过低（> 8%）", rate > 0.08, round(rate, 3))

# ---------- 2. BOSS 只掉 3 件 ----------
random.seed(12)
lv2 = Level(6, WEAPON_BOW)
boss = lv2.boss
lv2.items.clear()
lv2.handle_drops(boss, drop_key=True)
gear = [i for i in lv2.items if i.type in GEAR]
keys = [i for i in lv2.items if i.type == "key"]
check("BOSS 只掉 3 件装备", len(gear) == BOSS_DROP_COUNT, len(gear))
check("BOSS 仍然掉钥匙", len(keys) == 1, len(keys))
check("BOSS 掉落不再铺满一地", len(lv2.items) <= BOSS_DROP_COUNT + 2, len(lv2.items))

# ---------- 3. 神话装备与隐藏属性 ----------
random.seed(13)
lv3 = Level(15, WEAPON_SWORD)
lv3.items.clear()
level_mod.MYTHIC_HIDDEN_CHANCE = 1.0
lv3.get_drop_quality = lambda is_boss=False: Q_RED
lv3.handle_drops(lv3.boss, drop_key=True)
reds = [i for i in lv3.items if i.quality == Q_RED]
check("后期 BOSS 能掉神话", len(reds) > 0, len(reds))
check("神话装备可带隐藏属性", all(i.hidden for i in reds), [i.hidden for i in reds])
check("隐藏装备名字有标注", all("隐藏" in i.display_name() for i in reds),
      [i.display_name() for i in reds])

level_mod.MYTHIC_HIDDEN_CHANCE = 0.0
lv3.items.clear()
lv3.handle_drops(lv3.boss, drop_key=True)
plain = [i for i in lv3.items if i.quality == Q_RED]
check("普通神话没有隐藏功能", all(i.hidden is None for i in plain),
      [i.hidden for i in plain])
check("普通神话名字不带隐藏", all("隐藏" not in i.display_name() for i in plain),
      [i.display_name() for i in plain])
level_mod.MYTHIC_HIDDEN_CHANCE = 0.30

# 隐藏属性生效
random.seed(14)
lv4 = Level(0, WEAPON_SWORD)
pl = lv4.player
base_crit = pl.crit_chance
pl.weapon_hidden = "crit"
check("隐藏·致命提升暴击率", pl.crit_chance > base_crit + 0.05,
      (base_crit, pl.crit_chance))

pl.armor_hidden = "guard"
pl.invincible_timer = 0
hp_before = pl.hp
pl.take_damage(100, DMG_PHYS)
guarded = hp_before - pl.hp
pl.hp = hp_before
pl.armor_hidden = None
pl.invincible_timer = 0
pl.take_damage(100, DMG_PHYS)
plain_dmg = hp_before - pl.hp
check("隐藏·守护减少受伤", guarded < plain_dmg, (guarded, plain_dmg))

pl.hp = 30
pl.weapon_hidden = "lifesteal"
pl.invincible_timer = 10 ** 9
lv4.effects.clear()
lv4.float_texts.clear()
target = lv4.enemies[0] if lv4.enemies else None
if target is None:
    lv4.spawn_enemy()
    target = lv4.enemies[-1]
lv4._hit_feedback(target, 100)
check("隐藏·吸血能回血", pl.hp > 30, pl.hp)

pl.weapon_hidden = "swift"
pl.chill_timer = 0
pl.env_speed_mult = 1.0
x0 = pl.rect.x
for _ in range(10):
    pl.move(1, 0, [])
swift_dx = pl.rect.x - x0
pl.weapon_hidden = None
x0 = pl.rect.x
for _ in range(10):
    pl.move(1, 0, [])
plain_dx = pl.rect.x - x0
check("隐藏·疾行提高移速", swift_dx > plain_dx, (swift_dx, plain_dx))

pl.weapon_hidden = "mana"
pl.energy = 0
pl.attack()
check("隐藏·灵泉攻击多回蓝", pl.energy > 15, pl.energy)
pl.weapon_hidden = None

# ---------- 4. BOSS 难度提升 ----------
random.seed(15)
lv5 = Level(15, WEAPON_SWORD)
boss = lv5.boss
check("后期 BOSS 血量 > 10000", boss.max_hp > 10000, boss.max_hp)
check("后期 BOSS 攻击 > 100", boss.attack_damage > 100, boss.attack_damage)
check("BOSS 技能更频繁（CD <= 170）", boss.skill_cd <= 170, boss.skill_cd)
check("BOSS 移动更快（>= 4.0）", boss.speed >= 4.0, boss.speed)

# ---------- 5. 退出游戏按钮 ----------
save_mod.remove()
calls = {"n": 0}


def fake_get():
    calls["n"] += 1
    if calls["n"] == 3:
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   {"pos": (WIDTH - 172 + 80, HEIGHT - 62 + 20),
                                    "button": 1})]
    return []


gm.pygame.event.get = fake_get
gm.pygame.display.flip = lambda: None
random.seed(2)
asyncio.run(gm.main())
check("点击退出游戏能结束主循环", calls["n"] >= 3, calls["n"])

print("\nDROP / BOSS / HIDDEN / QUIT CHECKS PASSED")
