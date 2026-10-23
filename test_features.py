"""功能校验：三职业技能、怪物池、掉落与本职业一致。"""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import *
from entities import Enemy, Item, Boss, Projectile
from level import Level, MAP_COLS, MAP_ROWS
from settings import level_theme

screen = pygame.display.set_mode((WIDTH, HEIGHT))


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


def make_level(weapon, level_idx=0, enemy_type="slime", dist=70, hp=None):
    random.seed(1)
    lv = Level(level_idx, weapon)
    lv.enemies.clear()
    p = lv.player
    e = Enemy(p.rect.centerx + dist, p.rect.centery - 10, enemy_type, False, 0)
    if hp:
        e.hp = e.max_hp = hp
    lv.enemies.append(e)
    return lv, e


# ---------- 1. 剑士：旋风斩 ----------
lv, e = make_level(WEAPON_SWORD)
lv.player.energy = MAX_ENERGY
ok = lv.cast_skill()
check("剑士技能可以释放", ok is True)
check("旋风斩造成伤害", e.hp < e.max_hp, f"hp={e.hp}/{e.max_hp}")
check("旋风斩击退敌人", e.knockback_x != 0, f"kb={e.knockback_x}")
check("旋风斩有特效", len(lv.effects) > 0)
check("释放后扣除能量并进入冷却",
      lv.player.energy == MAX_ENERGY - SKILL_COST_PRIMARY and lv.player.skill_cd > 0,
      lv.player.energy)
from entities import SpinBlades
check("旋风斩带旋转刀光特效", any(isinstance(eff, SpinBlades) for eff in lv.effects))
for eff in lv.effects:
    eff.draw(screen, 0, 0)
check("技能特效能正常绘制", True)

# ---------- 2. 弓箭手：箭雨 ----------
lv, e = make_level(WEAPON_BOW, dist=60)
lv.player.energy = MAX_ENERGY
lv.cast_skill()
arrows = [p for p in lv.player.projectiles]
check("箭雨发射 7 支箭", len(arrows) == 7, f"{len(arrows)}")
check("箭雨可以穿透", all(p.pierce == 3 for p in arrows))
check("箭雨箭矢有散开的纵向速度", len({round(p.vy, 3) for p in arrows}) == 7)
for _ in range(20):
    lv.update()
check("箭雨命中目标", e.hp < e.max_hp, f"hp={e.hp}/{e.max_hp}")

# ---------- 3. 法师：冰霜新星 ----------
lv, e = make_level(WEAPON_STAFF, dist=80)
lv.player.energy = MAX_ENERGY
lv.cast_skill()
check("冰霜新星造成伤害", e.hp < e.max_hp, f"hp={e.hp}/{e.max_hp}")
check("冰霜新星冻结敌人", e.freeze_timer > 0, f"freeze={e.freeze_timer}")
before = e.rect.topleft
for _ in range(10):
    e.update(lv.walls, lv.player)
check("冻结期间怪物不动", e.rect.topleft == before, f"{before} -> {e.rect.topleft}")

# ---------- 4. 冷却中不能再放 ----------
lv.player.energy = MAX_ENERGY
check("冷却中无法再次释放", lv.cast_skill() is False)
for _ in range(lv.player.skill_cd_max + 2):
    lv.player.update(lv.walls)
lv.player.energy = MAX_ENERGY
check("冷却结束后可以再放", lv.cast_skill() is True)

# ---------- 4.5 普通攻击三种武器都能命中 ----------
for wt, name in ((WEAPON_SWORD, "剑士"), (WEAPON_BOW, "弓箭手"), (WEAPON_STAFF, "法师")):
    random.seed(1)
    lv = Level(0, wt)
    lv.enemies.clear()
    p = lv.player
    e = Enemy(p.rect.right + 30, p.rect.y + 4, "slime", False, 0)
    e.hp = e.max_hp = 500
    lv.enemies.append(e)
    hp0 = e.hp
    p.facing_right = True
    for i in range(60):
        if i % 10 == 0:
            p.attack()
        lv.update()
    check(f"{name}普通攻击能命中怪物", e.hp < hp0, f"{hp0} -> {e.hp}")

# ---------- 5. 怪物池 / 多样化 ----------
for lvl_idx in (0, 1, 2, 3):
    random.seed(3)
    lv = Level(lvl_idx, WEAPON_SWORD)
    types = {e.enemy_type for e in lv.enemies if not e.is_boss}
    allowed = set(Level.CHAPTER_POOL[level_theme(lvl_idx)])
    check(f"关卡{lvl_idx} 怪物都在本关池内", types <= allowed, f"{types}")
    check(f"关卡{lvl_idx} 至少出现 2 种怪物", len(types) >= 2, f"{types}")
    if lvl_idx >= 1:
        check(f"关卡{lvl_idx} 有 BOSS", any(e.is_boss for e in lv.enemies))

# ---------- 6. 掉落武器必须是本职业武器 ----------
for wt, label in ((WEAPON_SWORD, "剑士"), (WEAPON_BOW, "弓箭手"), (WEAPON_STAFF, "法师")):
    random.seed(5)
    lv = Level(0, wt)
    got = []
    for _ in range(60):
        e = Enemy(200, 200, "slime", True, 0)
        lv.handle_drops(e)
        got += [i for i in lv.items if i.type == "weapon" and i not in got]
    check(f"{label}掉落物全部是{label}的武器",
          got and all(i.weapon_type == wt for i in got), f"{len(got)} 件")

# ---------- 7. 掉落物绘制 / 名称 ----------
lvl = Level(0, WEAPON_BOW)
for kind, wt in (("weapon", WEAPON_BOW), ("armor", None), ("helmet", None), ("key", None), ("chest", None)):
    for q in (Q_WHITE, Q_SILVER, Q_PURPLE, Q_GOLD, Q_RED):
        it = Item(0, 0, kind, q, wt)
        for _ in range(5):
            it.update_physics()
        it.draw(screen, 0, 0)
bow_item = Item(0, 0, "weapon", Q_GOLD, WEAPON_BOW)
check("弓掉落显示为套装名",
      bow_item.display_name() == f"{Q_NAME[Q_GOLD]}·{GEAR_SETS['forest']['weapon'][WEAPON_BOW]}",
      bow_item.display_name())
sword_item = Item(0, 0, "weapon", Q_SILVER, WEAPON_SWORD)
check("剑掉落显示为套装名",
      sword_item.display_name() == f"{Q_NAME[Q_SILVER]}·{GEAR_SETS['forest']['weapon'][WEAPON_SWORD]}",
      sword_item.display_name())

# ---------- 8. 地图整图缓存 + 绘制 ----------
lv = Level(2, WEAPON_STAFF)
check("地图缓存尺寸正确", lv.map_surface.get_size() == (MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE))
for _ in range(30):
    lv.update()
lv.draw(screen, 0, 0)
check("关卡可以正常绘制", True)

# ---------- 9. 长时间运行不崩 ----------
lv = Level(1, WEAPON_BOW)
lv.player.invincible_timer = 99999   # 只测流程
for i in range(600):
    if i % 40 == 0:
        lv.player.energy = MAX_ENERGY
        lv.cast_skill()
    if i % 7 == 0:
        lv.player.attack()
    lv.player.move(1, 0, lv.walls)
    lv.update()
    if i % 30 == 0:
        lv.draw(screen, 0, 0)
check("600 帧混合操作无异常", True)

# ---------- 10. 死亡后重开 ----------
lv = Level(0, WEAPON_SWORD)
lv.enemies = [Enemy(lv.player.rect.centerx, lv.player.rect.centery, "slime")]
lv.player.hp = 0.1
lv.player.invincible_timer = 0
for _ in range(6):
    lv.update()
check("玩家会被打死", lv.player.hp <= 0, f"hp={lv.player.hp}")
lv2 = Level(1, WEAPON_SWORD, existing_player=lv.player)
check("死亡后重开新关卡不崩", lv2.player.hp > 0 and lv2.player.rect.topleft == lv2.player.rect.topleft)

print("\nALL FEATURE CHECKS PASSED")
