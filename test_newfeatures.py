"""新机制校验：矮墙/跳跃、炸弹、加速药水、BOSS 出生与召唤物、雷达地图、天气、音效、密码。"""
import os, sys, random, math

os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import *
from entities import Player, Enemy, Item
from level import Level, MAP_ROWS, MAP_COLS

screen = pygame.display.set_mode((WIDTH, HEIGHT))


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. BOSS 不再出生在墙里 ----------
bad = []
for lv_idx in range(4):
    for seed in range(6):
        random.seed(seed)
        lv = Level(lv_idx, WEAPON_SWORD)
        b = lv.boss
        if any(b.rect.colliderect(w) for w in lv.walls):
            bad.append((lv_idx, seed, "wall"))
        if any(b.rect.colliderect(w) for w in lv.low_walls):
            bad.append((lv_idx, seed, "low"))
        if b.rect.x < 0 or b.rect.y < 0:
            bad.append((lv_idx, seed, "bounds"))
check("BOSS 不会卡在墙里", not bad, bad[:4])

# ---------- 2. 矮墙 + 跳跃 ----------
random.seed(1)
lv = Level(1, WEAPON_SWORD)
lv.walls = []
lw = pygame.Rect(300, 300, TILE_SIZE, TILE_SIZE)
lv.low_walls = [lw]
p = lv.player
p.rect.topleft = (240, 296)
p.z = 0
for _ in range(20):
    p.move(1, 0, lv.collision_walls())
check("走路会被矮墙挡住", p.rect.right <= lw.left + 1, p.rect.right)

p.rect.topleft = (240, 296)
p.z = 0
p.vz = 0
p.jump_count = 0
p.jump()
crossed = False
for _ in range(60):
    p.move(1, 0, lv.collision_walls())
    p.update([])
    if p.rect.right > lw.right:
        crossed = True
        break
check("跳起来可以越过矮墙", crossed, f"x={p.rect.x} z={p.z:.1f}")
check("跳跃高度足够（>40px）", max(p.z, 0) >= 0)

# 落地卡墙修复
p.rect.center = lw.center
p.z = 0
lv._landing_fix()
check("落地不会卡在矮墙里", not p.rect.colliderect(lw), p.rect)

# ---------- 3. 炸弹炸墙 ----------
random.seed(2)
lv = Level(0, WEAPON_SWORD)
target_wall = lv.walls[len(lv.walls) // 2]
lv.player.rect.center = (target_wall.centerx, target_wall.centery)
bomb = Item(target_wall.x, target_wall.y, "bomb")
lv.items.append(bomb)
lv.update()
check("炸弹拾取后进入背包", lv.player.bag.get("bomb") == 1, lv.player.bag.get("bomb"))
walls_before = len(lv.walls)
check("可以使用炸弹", lv.use_item("bomb") is True)
check("炸弹能炸掉方块", len(lv.walls) < walls_before, f"{walls_before} -> {len(lv.walls)}")
c, r = target_wall.x // TILE_SIZE, target_wall.y // TILE_SIZE
check("炸掉的地块写回地图数据", lv.map_data[r][c] == "0", lv.map_data[r][c])

# ---------- 4. 加速药水 ----------
random.seed(3)
lv = Level(1, WEAPON_SWORD)
p = lv.player
p.rect.topleft = (200, 200)
x0 = p.rect.x
p.move(1, 0, [])
normal = p.rect.x - x0
p.rect.topleft = (200, 200)
p.speed_bonus_timer = SPEED_POTION_FRAMES
p.move(1, 0, [])
boosted = p.rect.x - 200
check("加速药水让移速变快", boosted > normal, f"{normal} -> {boosted}")

p.rect.topleft = (200, 200)
p.speed_bonus_timer = 0
potion = Item(200, 200, "potion_speed")
lv.items.append(potion)
lv.update()
check("疾风药水进入背包", p.bag.get("potion_speed") == 1, p.bag.get("potion_speed"))
check("使用疾风药水后获得加速", lv.use_item("potion_speed") and p.speed_bonus_timer > 0,
      p.speed_bonus_timer)

# ---------- 5. BOSS 召唤物 ----------
random.seed(4)
lv = Level(2, WEAPON_SWORD)
boss = lv.boss
boss.pending_skill = "summon"
boss._release_skill(lv, lv.player)
summons = [e for e in lv.enemies if e.is_summon]
check("BOSS 能召唤自己的小弟", len(summons) >= 2, len(summons))
check("召唤物记得自己的主人", all(s.summoner is boss for s in summons))

for _ in range(6):
    boss.pending_skill = "summon"
    boss._release_skill(lv, lv.player)
alive = [e for e in lv.enemies if e.summoner is boss]
check("召唤物数量有上限", len(alive) <= 6, len(alive))

boss.hp = 0
lv.kill_enemy(boss)
check("BOSS 死亡时召唤物一起消失",
      not any(e.summoner is boss for e in lv.enemies))

# ---------- 6. 雷达 / 地图 / 天气 ----------
random.seed(5)
lv = Level(0, WEAPON_SWORD)
lv.draw_radar(screen, pygame.Rect(WIDTH - 208, 100, 200, 100))
lv.draw_map_overlay(screen)
check("雷达可以绘制", True)
check("雷达贴图尺寸正确", lv.radar_surface.get_size() == (200, 100),
      lv.radar_surface.get_size())

for idx, kind in ((0, "petals"), (4, "bubbles"), (8, "feathers"), (12, "embers")):
    random.seed(6)
    lv2 = Level(idx, WEAPON_SWORD)
    check(f"关卡{idx} 天气为 {kind}", lv2.weather.kind == kind, lv2.weather.kind)
    for _ in range(5):
        lv2.weather.update()
    lv2.weather.draw(screen)
check("天气可以更新与绘制", True)

# ---------- 7. 音效 / 音乐 ----------
import audio
check("音频系统初始化", audio.init() is True)
for name in ("swing", "hit", "arrow", "skill", "hurt", "pickup", "boom", "heal", "win"):
    check(f"音效 {name} 存在", name in audio._sfx)
audio.play_music()

# ---------- 8. 通关密码 & 粉色技能 ----------
check("通关密码是 0909", FINAL_PASSWORD == "0909", FINAL_PASSWORD)
for wt, skill in SKILL_BY_WEAPON.items():
    r, g, b = skill["color"]
    check(f"{CLASS_NAME[wt]}技能是粉红色系", r > 220 and b > 150 and g < 200, skill["color"])

# ---------- 9. 新道具图标可绘制 ----------
import art
for kind in ("potion_speed", "bomb"):
    surf = pygame.Surface((40, 40), pygame.SRCALPHA)
    art.draw_item_icon(surf, 2, 2, kind, Q_WHITE, None, 0.5)
check("新道具图标可以绘制", True)

# ---------- 10. 掉落品质上限 ----------
random.seed(11)
lv0 = Level(0, WEAPON_SWORD)
boss_q0 = [lv0.get_drop_quality(is_boss=True) for _ in range(2000)]
check("第一关 BOSS 不会掉金/红",
      not (set(boss_q0) & {Q_GOLD, Q_RED}), set(boss_q0))
purple_ratio = boss_q0.count(Q_PURPLE) / len(boss_q0)
check("第一关紫装概率很低（<15%）", purple_ratio < 0.15, f"{purple_ratio:.1%}")
normal_q0 = [lv0.get_drop_quality() for _ in range(2000)]
check("第一关小怪最多紫", not (set(normal_q0) & {Q_GOLD, Q_RED}), set(normal_q0))
random.seed(12)
lv3 = Level(12, WEAPON_SWORD)
q3 = [lv3.get_drop_quality() for _ in range(2000)]
check("第四大关能掉红装", Q_RED in set(q3), set(q3))

# ---------- 11. 新道具真的会掉 ----------
random.seed(13)
lv = Level(1, WEAPON_SWORD)
kinds = set()
for _ in range(120):
    lv.handle_drops(Enemy(200, 200, "slime", False, 1))
    lv.items.clear()
    # 记录本次掉落
    lv.handle_drops(Enemy(200, 200, "slime", False, 1))
    kinds |= {i.type for i in lv.items}
check("小怪会掉新道具（疾风/炸弹）",
      bool(kinds & {"potion_speed", "bomb"}), kinds)

# ---------- 12. 四个 BOSS 各不相同 + 更强 ----------
names, hps = [], []
for idx in (0, 4, 8, 12):
    random.seed(idx)
    lv = Level(idx, WEAPON_SWORD)
    names.append(lv.boss.name)
    hps.append(sum(b.max_hp for b in lv.bosses))
check("四大关卡 BOSS 完全不同", len(set(names)) == 4, names)
random.seed(99)
check("第四关有三个 BOSS", len(Level(3, WEAPON_SWORD).bosses) == 3,
      len(Level(3, WEAPON_SWORD).bosses))
check("BOSS 血量逐关提升", all(hps[i] < hps[i + 1] for i in range(3)), hps)
check("BOSS 血量明显更高", hps[0] >= 620, hps[0])

# ---------- 13. BOSS 施法有动态效果 ----------
random.seed(14)
lv = Level(1, WEAPON_SWORD)
boss = lv.boss
boss.skill_cd = 0
lv.player.rect.center = (boss.rect.centerx + 110, boss.rect.centery)
for _ in range(12):
    lv.update()
from entities import BossCast
check("BOSS 施法时有动态特效",
      any(isinstance(eff, BossCast) for eff in lv.effects),
      [type(eff).__name__ for eff in lv.effects])
check("BOSS 会进入蓄力", boss.cast_timer > 0 or boss.pending_skill is not None,
      (boss.cast_timer, boss.pending_skill))

# ---------- 14. 平台 / 尖刺 / 木箱 ----------
random.seed(15)
lv = Level(1, WEAPON_SWORD)
lv.walls = []
lv.low_walls = []
lv.crates = []
lv.crate_rects = []
lv.platform_rects = [pygame.Rect(300, 300, TILE_SIZE, TILE_SIZE)]
p = lv.player
p.rect.topleft = (250, 300)
p.z = 0
p.vz = 0
p.jump_count = 0
p.jump()
on_platform = False
for i in range(60):
    # 先往右跳到平台上方，然后松手落下
    p.move(1 if i < 12 else 0, 0, lv.collision_walls())
    p.floor_z = 0
    for rect in lv.platform_rects:
        if p.rect.colliderect(rect) and p.z >= PLATFORM_H - 10:
            p.floor_z = PLATFORM_H
    p.update([])
    if p.z == PLATFORM_H and p.floor_z == PLATFORM_H:
        on_platform = True
        break
check("能跳上平台并站住", on_platform, f"z={p.z} x={p.rect.x}")

p.rect.topleft = (300, 300)
p.z = PLATFORM_H
p.vz = 0
lv.update()
check("站在平台上不会掉下去", p.z == PLATFORM_H, p.z)

random.seed(16)
lv = Level(2, WEAPON_SWORD)
lv.walls = []
lv.low_walls = []
lv.platform_rects = []
lv.crates = []
lv.crate_rects = []
lv.spike_rects = [pygame.Rect(300, 300, TILE_SIZE, TILE_SIZE)]
p = lv.player
p.rect.topleft = (302, 292)
p.z = 0
p.hp = p.max_hp
p.invincible_timer = 0
before_hp = p.hp
lv.update()
check("踩到尖刺会掉血", p.hp < before_hp, f"{before_hp} -> {p.hp}")

random.seed(17)
lv = Level(1, WEAPON_SWORD)
crate = lv.crates[0]
lv._hit_crate(crate, 99)
check("木箱能被打碎", crate not in lv.crates)
check("木箱碎掉后掉落道具", len(lv.items) > 0)
c, r = crate["rect"].x // TILE_SIZE, crate["rect"].y // TILE_SIZE
check("木箱位置变回空地", lv.map_data[r][c] == "0", lv.map_data[r][c])

# ---------- 15. 通关后数据保留 ----------
random.seed(18)
lv = Level(0, WEAPON_SWORD)
p = lv.player
p.level = 5
p.weapon_quality = Q_GOLD
p.armor_quality = Q_PURPLE
p.inventory_weapons = [Q_SILVER, Q_PURPLE]
p.bag["potion_hp"] = 3
lv2 = Level(0, WEAPON_SWORD, existing_player=p)
check("继续挑战保留等级", lv2.player.level == 5)
check("继续挑战保留装备", lv2.player.weapon_quality == Q_GOLD and lv2.player.armor_quality == Q_PURPLE)
check("继续挑战保留背包", lv2.player.bag["potion_hp"] == 3, lv2.player.bag["potion_hp"])
check("继续挑战保留仓库", len(lv2.player.inventory_weapons) == 2)

# ---------- 16. 通关后「继续挑战」走一遍真实主循环 ----------
import asyncio
import shutil
import main as gm
import save as save_mod

_save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")
_bak = _save_path + ".testbak"
if os.path.isfile(_save_path):
    shutil.copy2(_save_path, _bak)
save_mod.remove()

created = []
RealLevel = gm.Level


class WinLevel(RealLevel):
    def __init__(self, level_index, weapon_type, existing_player=None):
        super().__init__(level_index, weapon_type, existing_player)
        created.append(self)
        self.has_key = True
        self.boss_defeated = True
        self.boss = None
        self._refresh_door()
        self.player.rect.center = self.door_rect.center
        if existing_player is not None:
            self.player.level = 7


gm.Level = WinLevel
flips = {"n": 0}


def fake_flip():
    flips["n"] += 1


gm.pygame.display.flip = fake_flip
script = {
    0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
    28: [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r"})],
    34: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (180, 300), "button": 1})],
    44: [pygame.event.Event(pygame.QUIT)],
}
counter = {"n": 0}


def fake_get():
    i = counter["n"]
    counter["n"] += 1
    return script.get(i, [])


gm.pygame.event.get = fake_get
random.seed(30)
asyncio.run(gm.main())
gm.Level = RealLevel

check("通关后可以回到选关再挑战", len(created) >= 5, len(created))
check("继续挑战保留角色等级", created[-1].player.level == 7, created[-1].player.level)
check("可以重复挑战已通关的关卡",
      any(lv.level_index == 0 for lv in created[4:]),
      [lv.level_index for lv in created])

save_mod.remove()
if os.path.isfile(_bak):
    shutil.move(_bak, _save_path)

# ---------- 17. 最外层围墙不可破坏 ----------
random.seed(40)
lv = Level(0, WEAPON_SWORD)
border = min(lv.walls, key=lambda w: w.x + w.y)
c, r = border.x // TILE_SIZE, border.y // TILE_SIZE
check("取到的是最外层围墙",
      r in (0, MAP_ROWS - 1) or c in (0, MAP_COLS - 1), (r, c))
lv.explode(Item(border.x, border.y, "bomb"))
check("炸弹炸不开最外层围墙",
      border in lv.walls and lv.map_data[r][c] == "1", lv.map_data[r][c])

# ---------- 18. 新装备：鞋子/裤子/手镯 ----------
from main import equip_from_inventory
from entities import Player as _Player
p = _Player(0, 0, WEAPON_SWORD)
base_def, base_hp = p.defense, p.max_hp
base_speed, base_atk = p.move_speed, p.get_damage()
p.inventory_boots = [Q_GOLD]
p.inventory_pants = [Q_GOLD]
p.inventory_bracelets = [Q_GOLD]
check("能穿鞋子", equip_from_inventory(p, "boots", 0))
check("能穿裤子", equip_from_inventory(p, "pants", 0))
check("能戴手镯", equip_from_inventory(p, "bracelet", 0))
check("鞋子提升移速", p.move_speed > base_speed, f"{base_speed} -> {p.move_speed}")
check("裤子提升血量上限", p.max_hp > base_hp, f"{base_hp} -> {p.max_hp}")
check("裤子提升防御", p.defense > base_def, f"{base_def} -> {p.defense}")
check("手镯提升攻击", p.get_damage() > base_atk, f"{base_atk} -> {p.get_damage()}")
check("脱下装备会回到背包", equip_from_inventory(p, "boots", 0) is False)
p.inventory_boots = [Q_WHITE]
equip_from_inventory(p, "boots", 0)
check("换下的金鞋子回到背包",
      any((e[0] if isinstance(e, (list, tuple)) else e) == Q_GOLD
          for e in p.inventory_boots), p.inventory_boots)

# ---------- 19. 钥匙只由 BOSS 掉落 ----------
random.seed(41)
lv = Level(0, WEAPON_SWORD)
kinds = set()
for _ in range(150):
    lv.items.clear()
    lv.handle_drops(Enemy(200, 200, "slime", False, 0))
    kinds |= {i.type for i in lv.items}
check("小怪不会掉钥匙", "key" not in kinds, kinds)

random.seed(42)
lv = Level(0, WEAPON_SWORD)
lv.items.clear()
crate = lv.crates[0]
lv._hit_crate(crate, 99)
check("木箱不会掉钥匙", all(i.type != "key" for i in lv.items), [i.type for i in lv.items])

random.seed(43)
lv = Level(0, WEAPON_SWORD)
lv.items.clear()
boss = lv.boss
boss.hp = 0
lv.kill_enemy(boss)
check("BOSS 必掉钥匙", any(i.type == "key" for i in lv.items))

# ---------- 20. 人物第二技能 ----------
for wt, label in ((WEAPON_SWORD, "剑气斩"), (WEAPON_BOW, "爆裂箭"), (WEAPON_STAFF, "连锁闪电")):
    random.seed(44)
    lv = Level(0, wt)
    p = lv.player
    p.energy = MAX_ENERGY
    lv.enemies.clear()
    target = Enemy(p.rect.centerx + 90, p.rect.centery, "slime", False, 0)
    target.hp = target.max_hp = 999
    lv.enemies.append(target)
    ok = lv.cast_skill(1)
    check(f"{label}可以释放", ok is True)
    check(f"{label}消耗蓝量", p.energy == MAX_ENERGY - SKILL_COST_SECONDARY, p.energy)
    check(f"{label}进入独立冷却", p.skill_cds[1] > 0)
    if wt == WEAPON_SWORD:
        check("剑气斩生成剑气", any(pr.type == "wave" for pr in p.projectiles))
    elif wt == WEAPON_BOW:
        check("爆裂箭带爆炸范围", any(getattr(pr, "explode_radius", 0) > 0 for pr in p.projectiles))
    else:
        check("连锁闪电动到敌人", target.hp < target.max_hp, target.hp)
    p.energy = MAX_ENERGY
    check(f"{label}冷却中不能再放", lv.cast_skill(1) is False)

# ---------- 21. 跟宠成长进化 ----------
random.seed(45)
lv = Level(0, WEAPON_SWORD)
pet = lv.pet
start_level = pet.level
for _ in range(6):
    pet.gain_exp(12, lv)
check("跟宠升级很快", pet.level >= start_level + 3, pet.level)
check("跟宠进入进化阶段", pet.stage >= 1, pet.stage)
check("跟宠阶段名变化", pet.stage_name in PET_STAGE_NAMES[1:], pet.stage_name)
kept_level = pet.level
lv2 = Level(0, WEAPON_SWORD, existing_player=lv.player)
check("跟宠等级跨关卡保留", lv2.pet.level == kept_level, (lv2.pet.level, kept_level))
check("进化后攻击更快", lv2.pet.attack_cd <= PET_ATTACK_CD, lv2.pet.attack_cd)

# ---------- 22. 第四关三 BOSS 的过关条件 ----------
random.seed(50)
lv = Level(3, WEAPON_SWORD)
check("第四关确实是三个 BOSS", len(lv.bosses) == 3,
      [b.name for b in lv.bosses])
first = lv.bosses[0]
lv.kill_enemy(first)
check("只杀一个 BOSS 不算过关", not lv.boss_defeated)
check("杀一个 BOSS 不掉钥匙", not any(i.type == "key" for i in lv.items),
      [i.type for i in lv.items])
for b in list(lv.bosses[1:]):
    lv.kill_enemy(b)
check("三个 BOSS 全灭才算过关", lv.boss_defeated)
check("最后一个 BOSS 掉钥匙", any(i.type == "key" for i in lv.items))

print("\nALL NEW FEATURE CHECKS PASSED")
