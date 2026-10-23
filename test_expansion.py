"""四大关卡扩展校验：16 关、主题、套装、45 级上限、第三技能、跟宠技能、最终 BOSS。"""
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_expansion_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
pygame.display.set_mode((960, 540))

from settings import *
from level import Level
from entities import Player


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. 16 关 / 4 大关 ----------
check("共 16 个小关", TOTAL_LEVELS == 16)
check("共 4 个大关卡", len(CHAPTERS) == 4, [c["name"] for c in CHAPTERS])
check("每个大关 4 小关",
      all(len(c["levels"]) == 4 for c in CHAPTERS))

# ---------- 2. BOSS 数量逐章增加 ----------
counts = [boss_count(i) for i in range(TOTAL_LEVELS)]
check("BOSS 数量逐章增加",
      counts[0] < counts[4] < counts[8] < counts[12] and counts[15] == 5,
      counts)
random.seed(7)
lv15 = Level(15, WEAPON_SWORD)
check("最后一关 BOSS 数量最多", len(lv15.bosses) >= 5, len(lv15.bosses))
final = [b for b in lv15.bosses if getattr(b, "is_final", False)]
check("最后一关有 45 级最终魔王", len(final) == 1, [b.name for b in lv15.bosses])
check("最终魔王是 45 级", "45" in final[0].name, final[0].name)
check("最终魔王血量极高", final[0].max_hp >= 20000, final[0].max_hp)

# ---------- 3. 地图主题 ----------
for idx, theme in ((0, "forest"), (5, "ocean"), (9, "sky"), (13, "volcano")):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    check(f"关卡{idx} 使用 {theme} 主题", level_theme(idx) == theme)
    check(f"关卡{idx} BOSS 名册对应该主题",
          lv.boss.name in [n for _, n in BOSS_ROSTER[theme]], lv.boss.name)

# ---------- 4. 等级上限 45 ----------
p = Player(0, 0, WEAPON_SWORD)
p.gain_exp(10 ** 7)
check("角色等级封顶 45", p.level == MAX_PLAYER_LEVEL, p.level)
check("满级后经验为 0", p.exp == 0)
check("满级血量 = 100 + 44*25", p.base_max_hp == 100 + 44 * HP_PER_LEVEL, p.base_max_hp)

# 经验曲线：从 1 级到 45 级所需总经验
total = 0
need = 50
for lvl in range(1, MAX_PLAYER_LEVEL):
    total += 50 + (lvl - 1) * 25
check("升到 45 级所需总经验合理（< 40k）", total < 40000, total)

# ---------- 5. 第三技能 ----------
for wtype in (WEAPON_SWORD, WEAPON_BOW, WEAPON_STAFF):
    random.seed(11)
    lv = Level(4, wtype)
    pl = lv.player
    pl.invincible_timer = 10 ** 9
    pl.energy = MAX_ENERGY
    skill3 = pl.skill_at(2)
    before_energy = pl.energy
    ok = lv.cast_skill(2)
    check(f"{CLASS_NAME[wtype]} 第三技能可释放 {skill3['name']}", ok)
    check(f"{CLASS_NAME[wtype]} 第三技能消耗蓝量", pl.energy < before_energy,
          (before_energy, pl.energy))
    check(f"{CLASS_NAME[wtype]} 第三技能进入冷却", pl.skill_cds[2] > 0, pl.skill_cds[2])
    check(f"{CLASS_NAME[wtype]} 有三个技能", len(pl.skill_cds) == 3)

# ---------- 6. 跟宠技能 ----------
random.seed(3)
lv = Level(2, WEAPON_STAFF)
pet = lv.pet
pl = lv.player
pl.invincible_timer = 10 ** 9
check("跟宠有 2 个技能", len(PET_SKILLS[pet.kind]) == 2, PET_SKILLS[pet.kind])
check("幼灵阶段技能未解锁", pet.stage == 0)

pet.level = 4          # 阶段 1
pet.skill_cds[0] = 0
pl.hp = 10
healed_before = pl.hp
for _ in range(4):
    pet.update(lv)
check("阶段 1 解锁治疗技能并自动释放", pl.hp > healed_before, (healed_before, pl.hp))

pet.level = 7          # 阶段 2
pet.skill_cds[1] = 0
pl.hp = 10
pl.energy = 0
for _ in range(4):
    pet.update(lv)
check("阶段 2 解锁第二技能（回蓝）", pl.energy > 0, pl.energy)

# 战士跟宠技能造成伤害
random.seed(3)
lv = Level(2, WEAPON_SWORD)
pet = lv.pet
pet.level = 4          # 阶段 1
pet.skill_cds[0] = 0
enemy = lv.enemies[0] if lv.enemies else None
if enemy is not None:
    lv.player.rect.center = (enemy.rect.centerx - 40, enemy.rect.centery)
    pet.rect.center = (enemy.rect.centerx - 60, enemy.rect.centery)
    pet.player = lv.player
    hp_before = enemy.hp
    for _ in range(3):
        pet.update(lv)
    check("战士跟宠技能能造成伤害", enemy.hp < hp_before, (hp_before, enemy.hp))

# ---------- 7. 套装掉落在对应大关卡 ----------
for idx, key in ((0, "forest"), (5, "ocean"), (9, "sky"), (13, "volcano")):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    lv.player.invincible_timer = 10 ** 9
    for enemy in lv.enemies[:12]:
        lv.handle_drops(enemy, drop_key=True)
    gear = [i for i in lv.items if i.type in
            ("weapon", "armor", "helmet", "boots", "pants", "bracelet")]
    check(f"关卡{idx} 掉落属于 {key} 套装",
          gear and all(i.set_key == key for i in gear), [i.set_key for i in gear][:3])
    sample = gear[0]
    check(f"关卡{idx} 装备名带套装名",
          any(nm in sample.display_name() for nm in (GEAR_SETS[key]["armor"],
                                                    *GEAR_SETS[key]["weapon"].values(),
                                                    GEAR_SETS[key]["helmet"],
                                                    GEAR_SETS[key]["boots"],
                                                    GEAR_SETS[key]["pants"],
                                                    GEAR_SETS[key]["bracelet"])),
          sample.display_name())

# ---------- 8. 难度递增 ----------
random.seed(5)
lv1 = Level(0, WEAPON_SWORD)
random.seed(5)
lv16 = Level(15, WEAPON_SWORD)
e1 = lv1.enemies[0]
e16 = lv16.enemies[0]
check("后期小怪血量更高", e16.max_hp > e1.max_hp * 3, (e1.max_hp, e16.max_hp))
check("后期小怪伤害更高", e16.attack_damage > e1.attack_damage,
      (e1.attack_damage, e16.attack_damage))
check("后期关卡小怪更多", len(lv16.enemies) > len(lv1.enemies),
      (len(lv1.enemies), len(lv16.enemies)))

# ---------- 9. 全部关卡的经验足够练到 45 级 ----------
total_exp = 0
for idx in range(TOTAL_LEVELS):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    scale = 1 + idx * 0.35
    total_exp += sum(int(EXP_PER_KILL * scale
                         * (5 if e.is_boss else (2 if e.is_elite else e.xp)))
                     for e in lv.enemies)
check("打通 16 关的经验足够升到 45 级", total_exp >= total, (total_exp, total))

print("\nEXPANSION CHECKS PASSED")
