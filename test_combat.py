"""新战斗系统校验：伤害类型/防御、远程怪、BOSS 技能、精英技能、跟宠、药水、过关条件。"""
import os, sys, random, math

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import *
from entities import Player, Enemy, Boss, Item
from level import Level

screen = pygame.display.set_mode((WIDTH, HEIGHT))


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. 初始攻击力上调 ----------
sword = Player(0, 0, WEAPON_SWORD)
bow = Player(0, 0, WEAPON_BOW)
staff = Player(0, 0, WEAPON_STAFF)
check("剑士初始攻击力 ~14", sword.get_damage() == 14, sword.get_damage())
check("弓箭手初始攻击力 ~11", bow.get_damage() == 11, bow.get_damage())
check("法师初始攻击力 ~16", staff.get_damage() == 16, staff.get_damage())
check("玩家血量是具体数值 100", sword.max_hp == 100, sword.max_hp)

# ---------- 2. 防御 / 法抗 ----------
p = Player(100, 100, WEAPON_SWORD)
p.invincible_timer = 0
raw = sword.take_damage(40, DMG_PHYS)
check("无护甲时吃满物理伤害", raw == 40, raw)
p.armor_quality = Q_GOLD
p.helmet_quality = Q_GOLD
p.invincible_timer = 0
mitigated = p.take_damage(40, DMG_PHYS)
check("穿金装后物理伤害被防御减免", mitigated < raw, f"{raw} -> {mitigated}")
check("角色面板有防御力", p.defense > 0, p.defense)

p2 = Player(100, 100, WEAPON_SWORD)
p2.helmet_quality = Q_RED
p2.invincible_timer = 0
magic_mitigated = p2.take_damage(40, DMG_MAGIC)
check("法抗减免法术伤害", magic_mitigated < 40, magic_mitigated)
check("角色面板有法抗", p2.magic_resist > 0, p2.magic_resist)

# ---------- 3. 远程怪：骷髅射箭（物理）/ 蝙蝠法弹（法术） ----------
random.seed(1)
lv = Level(1, WEAPON_SWORD)
lv.enemies.clear()
lv.enemy_shots.clear()
p = lv.player
p.invincible_timer = 10 ** 9
p.hp = p.max_hp

archer = Enemy(p.rect.centerx + 220, p.rect.centery, "skeleton", False, 1)
archer.shoot_cd = 0
lv.enemies.append(archer)
for _ in range(6):
    lv.update()
check("骷髅会射箭", len(lv.enemy_shots) > 0, len(lv.enemy_shots))
check("骷髅的箭是物理伤害",
      all(b.dmg_type == DMG_PHYS for b in lv.enemy_shots))
check("骷髅是弓箭手定位", archer.role == "archer")

lv.enemies.clear()
lv.enemy_shots.clear()
mage = Enemy(p.rect.centerx + 200, p.rect.centery, "bat", False, 1)
mage.shoot_cd = 0
lv.enemies.append(mage)
for _ in range(6):
    lv.update()
check("蝙蝠会放法术弹", len(lv.enemy_shots) > 0, len(lv.enemy_shots))
check("法师的弹是法术伤害",
      all(b.dmg_type == DMG_MAGIC for b in lv.enemy_shots))
check("蝙蝠是法师定位", mage.role == "mage")

# 敌方弹幕真的能打到玩家
lv.enemies.clear()
lv.enemy_shots.clear()
p.invincible_timer = 0
p.hp = p.max_hp
mage = Enemy(p.rect.centerx + 120, p.rect.centery, "bat", False, 1)
mage.shoot_cd = 0
lv.enemies.append(mage)
for _ in range(120):
    lv.update()
    if p.hp < p.max_hp:
        break
check("法术弹命中玩家会掉血", p.hp < p.max_hp, f"{p.hp}/{p.max_hp}")
check("玩家受击有飘字", len(lv.float_texts) > 0)

# ---------- 4. BOSS：每关不同 + 技能 ----------
boss_types = {}
for idx in (0, 4, 8, 12):
    random.seed(idx)
    lv2 = Level(idx, WEAPON_SWORD)
    boss = lv2.boss
    check(f"关卡{idx} 有 BOSS", boss is not None and boss.is_boss)
    boss_types[idx] = (boss.name, sum(b.max_hp for b in lv2.bosses))
check("BOSS 名册随大关卡变化", len({t for t, _ in boss_types.values()}) >= 4,
      {k: v[0] for k, v in boss_types.items()})
chapter_keys = [0, 4, 8, 12]
check("BOSS 血量逐章提升",
      all(boss_types[chapter_keys[i]][1] < boss_types[chapter_keys[i + 1]][1]
          for i in range(3)),
      {k: v[1] for k, v in boss_types.items()})

# 逐个技能验证
random.seed(2)
lv = Level(2, WEAPON_SWORD)          # 树妖王：荆棘环射 + 砸地
boss = lv.boss
p = lv.player
p.invincible_timer = 0
p.hp = p.max_hp
lv.enemy_shots.clear()

boss.pending_skill = "thorn_ring"
boss._release_skill(lv, p)
check("树妖王·荆棘环射发出 12 发弹幕", len(lv.enemy_shots) == 12, len(lv.enemy_shots))

p.rect.center = (boss.rect.centerx + 60, boss.rect.centery)
p.invincible_timer = 0
p.hp = p.max_hp
boss.pending_skill = "slam"
boss._release_skill(lv, p)
check("树妖王·砸地对范围内玩家造成伤害", p.hp < p.max_hp, f"{p.hp}/{p.max_hp}")

lv3 = Level(3, WEAPON_SWORD)
boss3 = lv3.boss
n0 = len(lv3.enemies)
boss3.pending_skill = "summon"
boss3._release_skill(lv3, lv3.player)
check("骷髅王·召唤出小怪", len(lv3.enemies) == n0 + 3, len(lv3.enemies) - n0)

lv3.enemy_shots.clear()
boss3.pending_skill = "bone_volley"
boss3._release_skill(lv3, lv3.player)
check("骷髅王·骨矛齐射", len(lv3.enemy_shots) >= 5, len(lv3.enemy_shots))

boss3.pending_skill = "charge"
boss3._release_skill(lv3, lv3.player)
check("骷髅王·冲锋进入冲刺状态", boss3.dash_timer > 0, boss3.dash_timer)

check("BOSS 有多个技能", all(len(Boss.SKILLS[t]) >= 2 for t in Boss.SKILLS))

# ---------- 5. 精英怪技能 ----------
random.seed(3)
lv = Level(2, WEAPON_SWORD)
lv.enemies.clear()
lv.enemy_shots.clear()
p = lv.player
elite_warrior = Enemy(p.rect.centerx + 60, p.rect.centery, "slime", True, 2)
elite_warrior._release_skill(lv, p)
check("精英战士会冲锋", elite_warrior.dash_timer > 0, elite_warrior.dash_timer)

lv.enemy_shots.clear()
elite_archer = Enemy(p.rect.centerx + 150, p.rect.centery, "skeleton", True, 2)
elite_archer._release_skill(lv, p)
check("精英弓箭手三连矢", len(lv.enemy_shots) == 3, len(lv.enemy_shots))

lv.enemy_shots.clear()
elite_mage = Enemy(p.rect.centerx + 150, p.rect.centery, "bat", True, 2)
elite_mage._release_skill(lv, p)
check("精英法师环形弹幕", len(lv.enemy_shots) == 8, len(lv.enemy_shots))

# 精英会自己进入蓄力
elite_mage.elite_skill_cd = 0
elite_mage.cast_timer = 0
elite_mage.update(lv.walls, p, lv)
check("精英怪会主动蓄力放技能", elite_mage.cast_timer > 0, elite_mage.cast_timer)

# ---------- 6. 跟宠（按职业分工） ----------
# 战士跟宠：远程攻击，不治疗
random.seed(4)
lv = Level(0, WEAPON_SWORD)
lv.enemies.clear()
p = lv.player
pet = lv.pet
p.hp = 40
pet.heal_cd = 0
pet.update(lv)
check("战士跟宠不负责治疗", p.hp == 40, p.hp)

target = Enemy(p.rect.centerx + 90, p.rect.centery, "slime", False, 0)
target.hp = target.max_hp = 500
lv.enemies.append(target)
pet.attack_cd = 0
pet.update(lv)
check("战士跟宠远程协助攻击", target.hp < target.max_hp, f"{target.hp}/{target.max_hp}")

# 弓箭手跟宠：提供攻速加成
random.seed(4)
lv_bow = Level(0, WEAPON_BOW)
lb = lv_bow.pet
lb.update(lv_bow)
check("弓箭手跟宠提供攻速加成", lv_bow.player.pet_haste is True)
check("弓箭手跟宠不治疗", lv_bow.player.hp == lv_bow.player.max_hp)
base_cd = 22
lv_bow.player.attack_cooldown = 0
lv_bow.player.attack()
check("攻速加成让攻击冷却变短", lv_bow.player.attack_cooldown < base_cd,
      lv_bow.player.attack_cooldown)

# 法师跟宠：回蓝 + 回血
random.seed(4)
lv_staff = Level(0, WEAPON_STAFF)
ls = lv_staff.pet
ls.player.hp = 40
ls.player.energy = 10
ls.heal_cd = 0
ls.energy_cd = 0
ls.update(lv_staff)
check("法师跟宠回血", ls.player.hp > 40, f"{ls.player.hp}/100")
check("法师跟宠回蓝", ls.player.energy > 10, ls.player.energy)

# ---------- 7. 药水掉落 ----------
random.seed(5)
lv = Level(0, WEAPON_SWORD)
p = lv.player
p.hp = 40
potion = Item(p.rect.x, p.rect.y, "potion_hp")
lv.items.append(potion)
lv.update()
check("生命药水进背包", p.bag.get("potion_hp") == 1)
check("使用生命药水能回血", lv.use_item("potion_hp") and p.hp > 40, f"{p.hp}/100")

p.energy = 10
energy = Item(p.rect.x, p.rect.y, "potion_energy")
lv.items.append(energy)
lv.update()
check("能量药水进背包", p.bag.get("potion_energy") == 1)
check("使用能量药水能回能量", lv.use_item("potion_energy") and p.energy > 10, p.energy)

# 掉落表里会出现药水
random.seed(6)
lv = Level(1, WEAPON_SWORD)
for _ in range(40):
    lv.handle_drops(Enemy(200, 200, "slime", False, 1))
kinds = {i.type for i in lv.items}
check("掉落包含药水", "potion_hp" in kinds or "potion_energy" in kinds, kinds)

# ---------- 8. 过关条件：钥匙 + BOSS ----------
random.seed(7)
lv = Level(0, WEAPON_SWORD)
check("初始门是关的", not lv.door_open)
lv.has_key = True
lv._refresh_door()
check("只有钥匙不能开门", not lv.door_open)
lv.has_key = False
lv.boss_defeated = True
lv._refresh_door()
check("只杀 BOSS 也不能开门", not lv.door_open)
lv.has_key = True
lv._refresh_door()
check("钥匙 + BOSS 才能开门", lv.door_open)

# 钥匙拾取
lv2 = Level(0, WEAPON_SWORD)
key_item = Item(lv2.player.rect.x, lv2.player.rect.y, "key")
lv2.items.append(key_item)
lv2.update()
check("走到钥匙上会拾取", lv2.has_key and key_item.collected)

# ---------- 9. 击杀 BOSS 会推进状态 ----------
random.seed(8)
lv3 = Level(1, WEAPON_SWORD)
boss = lv3.boss
boss.hp = 0
lv3.kill_enemy(boss)
check("击杀 BOSS 后记录状态", lv3.boss_defeated)
check("BOSS 死亡会掉落装备", any(i.type == "weapon" for i in lv3.items))

print("\nALL COMBAT CHECKS PASSED")
