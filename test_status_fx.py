"""界面修复 + 环境状态 + BOSS 技能校验。"""
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_status_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
screen = pygame.display.set_mode((960, 540))

import art
import audio
from settings import *
from level import Level
from entities import BossSkillFX
import main as gm


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


font, small_font = art.font(24), art.font(16)

# ---------- 1. 背包折叠 ----------
random.seed(1)
lv = Level(0, WEAPON_SWORD)
pl = lv.player
pl.inventory_weapons = [(Q_GOLD, "ocean")] * 4 + [(Q_PURPLE, "sky")] * 2
pl.inventory_armors = [(Q_SILVER, "forest")] * 3
pl.inventory_helmets = []
pl.inventory_boots = []
pl.inventory_pants = []
pl.inventory_bracelets = []
rects, actions = [], []
gm.draw_stats_panel(screen, lv, font, small_font, rects, actions)
check("相同装备折叠为一格", len(actions) == 3, actions)
check("折叠后格子数与组数一致", len(rects) == 3, len(rects))

# 点击折叠格只消耗其中一件
pl.weapon_quality = "none"
pl.weapon_set = "forest"
pl.inventory_weapons = [(Q_GOLD, "ocean")] * 4
before = len(pl.inventory_weapons)
gm.equip_from_inventory(pl, "weapon", 0)
check("穿戴折叠格只取走一件", len(pl.inventory_weapons) == before - 1,
      len(pl.inventory_weapons))
check("穿戴后品质与套装正确",
      pl.weapon_quality == Q_GOLD and pl.weapon_set == "ocean",
      (pl.weapon_quality, pl.weapon_set))

# ---------- 2. 音频状态 ----------
check("音频初始化成功", audio.init())
check("音频状态文本可读", "音频" in audio.status(), audio.status())

# ---------- 3. 全屏能力（dummy 驱动下只验证接口存在） ----------
check("支持 FULLSCREEN 标志", hasattr(pygame, "FULLSCREEN") and hasattr(pygame.display,
                                                                    "toggle_fullscreen"))

# ---------- 4. 海底减速 ----------
random.seed(4)
forest = Level(0, WEAPON_SWORD)
ocean = Level(5, WEAPON_SWORD)
for lv_test in (forest, ocean):
    lv_test.player.rect.center = (TILE_SIZE * 6, TILE_SIZE * 6)
    lv_test.player.vz = 0
forest.player.env_speed_mult = 1.0
ocean.player.env_speed_mult = 0.82
x0 = forest.player.rect.x
forest.player.move(1, 0, [])
x1 = forest.player.rect.x
o0 = ocean.player.rect.x
ocean.player.move(1, 0, [])
o1 = ocean.player.rect.x
check("海底移动更慢", (o1 - o0) < (x1 - x0), ((x1 - x0), (o1 - o0)))
ocean.update()
check("海底关卡自动套用减速", ocean.player.env_speed_mult < 1.0,
      ocean.player.env_speed_mult)

# 冰冻再减速
ocean.player.chill_timer = 100
x0 = ocean.player.rect.x
ocean.player.move(1, 0, [])
chilled_dx = ocean.player.rect.x - x0
check("冰冻时移动更慢", chilled_dx < (o1 - o0), (chilled_dx, o1 - o0))

# ---------- 5. 火山灼烧 ----------
random.seed(8)
vol = Level(13, WEAPON_SWORD)
lava = None
for r in range(len(vol.map_data)):
    for c in range(len(vol.map_data[0])):
        if vol.map_data[r][c] == "8":
            lava = (c, r)
            break
    if lava:
        break
check("火山关有岩浆陷阱", lava is not None)
vol.player.rect.center = (lava[0] * TILE_SIZE + TILE_SIZE // 2,
                          lava[1] * TILE_SIZE + TILE_SIZE // 2)
vol.update()
check("踩到岩浆会灼烧", vol.player.burn_timer > 0, vol.player.burn_timer)
hp_before = vol.player.hp
burn_hit = False
for _ in range(240):
    vol.update()
    if vol.player.hp < hp_before:
        burn_hit = True
        break
check("灼烧会持续掉血", burn_hit, (hp_before, vol.player.hp, vol.player.burn_timer))

# 火山 BOSS 命中会点燃
random.seed(8)
vol2 = Level(13, WEAPON_SWORD)
vol2.player.invincible_timer = 0
ignited = False
for _ in range(30):
    vol2.pop_player_damage(10)
    if vol2.player.burn_timer > 0:
        ignited = True
        break
check("火山受击会点燃", ignited, vol2.player.burn_timer)

# ---------- 6. 海底 BOSS 冰冻技能 ----------
random.seed(5)
oc = Level(5, WEAPON_SWORD)
oc.player.invincible_timer = 0
oc.player.rect.center = (oc.boss.rect.centerx - 40, oc.boss.rect.centery)
oc.player.hp = oc.player.max_hp
hp0 = oc.player.hp
oc.boss.pending_skill = "ice_nova"
oc.boss._release_skill(oc, oc.player)
check("海底 BOSS 冰冻技能有伤害", oc.player.hp < hp0, (hp0, oc.player.hp))
check("海底 BOSS 冰冻技能会减速玩家", oc.player.chill_timer > 0, oc.player.chill_timer)
check("冰冻技能有专属特效",
      any(isinstance(e, BossSkillFX) and e.kind == "ice_nova" for e in oc.effects),
      [getattr(e, "kind", None) for e in oc.effects])

# ---------- 7. BOSS 技能伤害提升 ----------
random.seed(6)
bt = Level(9, WEAPON_SWORD)
bt.player.invincible_timer = 0
bt.player.rect.center = (bt.boss.rect.centerx - 30, bt.boss.rect.centery)
bt.player.hp = bt.player.max_hp
dmg0 = bt.player.hp
bt.boss.pending_skill = "slam"
bt.boss._release_skill(bt, bt.player)
lost = dmg0 - bt.player.hp
check("BOSS 砸地伤害高于普攻", lost > bt.boss.attack_damage,
      (round(lost, 1), bt.boss.attack_damage))
check("BOSS 技能有专属特效",
      any(isinstance(e, BossSkillFX) for e in bt.effects),
      [type(e).__name__ for e in bt.effects])

# ---------- 8. 技能特效不再单一 ----------
random.seed(3)
sw = Level(13, WEAPON_SWORD)
sw.player.energy = MAX_ENERGY
sw.cast_skill(2)          # 裂地斩
from entities import GroundCracks
check("裂地斩有地面裂缝", any(isinstance(e, GroundCracks) for e in sw.effects),
      [type(e).__name__ for e in sw.effects])

random.seed(3)
bw = Level(9, WEAPON_BOW)
bw.player.energy = MAX_ENERGY
bw.cast_skill(2)          # 箭幕
from entities import ArrowStormFX
check("箭幕有箭雨特效", any(isinstance(e, ArrowStormFX) for e in bw.effects),
      [type(e).__name__ for e in bw.effects])

random.seed(3)
st = Level(0, WEAPON_STAFF)
st.player.energy = MAX_ENERGY
# 放几个怪保证连锁有目标
for _ in range(3):
    st.spawn_enemy()
st.cast_skill(1)          # 连锁闪电
from entities import LightningFX
check("连锁闪现有闪电特效", any(isinstance(e, LightningFX) for e in st.effects),
      [type(e).__name__ for e in st.effects])

print("\nUI / STATUS / BOSS SKILL CHECKS PASSED")
