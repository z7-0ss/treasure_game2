"""多存档 / 150 格背包 / 悬停解释 / 最终通关画面 校验。"""
import json
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_saves_bag.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
screen = pygame.display.set_mode((960, 540))

import art
import audio
import main as gm
import save as save_mod
from entities import Item, Player
from level import Level
from settings import *

audio.init()
font, small_font = art.font(24), art.font(16)


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. 旧存档迁移 ----------
save_mod.remove()
with open(save_mod._PATH, "w", encoding="utf-8") as f:
    json.dump({"weapon": WEAPON_BOW, "cleared": [0, 1],
               "player": {"level": 6, "weapon_type": WEAPON_BOW}}, f)
info = save_mod.load_all()
check("旧版单存档迁移到 1 号槽", info["slots"][0] is not None, info["slots"])
check("迁移后职业保留", info["slots"][0]["player"]["weapon_type"] == WEAPON_BOW)
check("迁移后进度保留", info["slots"][0]["cleared"] == [0, 1])

# ---------- 2. 三个角色存档 ----------
save_mod.remove()
save_mod.write_slot(0, {"weapon": WEAPON_SWORD, "cleared": list(range(5)),
                        "player": {"level": 12, "weapon_type": WEAPON_SWORD}})
save_mod.write_slot(1, {"weapon": WEAPON_BOW, "cleared": list(range(9)),
                        "player": {"level": 30, "weapon_type": WEAPON_BOW}})
save_mod.write_slot(2, {"weapon": WEAPON_STAFF, "cleared": list(range(16)),
                        "player": {"level": 45, "weapon_type": WEAPON_STAFF}})
info = save_mod.load_all()
check("支持 3 个存档槽", len(info["slots"]) == 3)
check("三个角色互不覆盖",
      [s["player"]["weapon_type"] for s in info["slots"]] == [WEAPON_SWORD, WEAPON_BOW, WEAPON_STAFF],
      [s["player"]["weapon_type"] for s in info["slots"]])
check("等级分别保存", [s["player"]["level"] for s in info["slots"]] == [12, 30, 45],
      [s["player"]["level"] for s in info["slots"]])

save_mod.set_active(1)
check("切换激活槽", save_mod.load()["player"]["weapon_type"] == WEAPON_BOW)
check("激活槽持久化", save_mod.load_all()["active"] == 1)

save_mod.delete_slot(2)
info = save_mod.load_all()
check("删除指定槽", info["slots"][2] is None)
check("删除不影响其它槽", info["slots"][0] is not None and info["slots"][1] is not None)

info2 = save_mod.slot_info(info["slots"][1])
check("存档摘要包含等级与进度",
      info2["level"] == 30 and info2["cleared"] == 9, info2)
empty = save_mod.slot_info(None)
check("空槽摘要", empty["empty"] and empty["sub"])

# ---------- 3. 150 格背包 ----------
random.seed(4)
lv = Level(0, WEAPON_SWORD)
pl = lv.player
pl.inventory_boots = [(Q_WHITE, "forest")] * INVENTORY_MAX
item = Item(pl.rect.centerx, pl.rect.centery, "boots", quality=Q_SILVER, set_key="forest")
lv.items.append(item)
lv._pickup(item)
check("背包上限 150", len(pl.inventory_boots) == INVENTORY_MAX, len(pl.inventory_boots))
check("满包时拾取被拒绝并提示",
      any("背包已满" in f.text for f in lv.float_texts),
      [f.text for f in lv.float_texts][:3])

pl.inventory_boots = []
lv._pickup(Item(pl.rect.centerx, pl.rect.centery, "boots", quality=Q_SILVER, set_key="forest"))
check("未满时可以拾取", len(pl.inventory_boots) == 1)

# ---------- 4. 背包分页 ----------
random.seed(5)
lv2 = Level(5, WEAPON_BOW)
pl2 = lv2.player
name_map = {"weapon": "inventory_weapons", "armor": "inventory_armors",
            "helmet": "inventory_helmets", "boots": "inventory_boots",
            "pants": "inventory_pants", "bracelet": "inventory_bracelets"}
kinds = list(name_map)
qs = [Q_WHITE, Q_SILVER, Q_PURPLE, Q_GOLD, Q_RED]
sets = ["forest", "ocean", "sky", "volcano"]
for i in range(150):
    getattr(pl2, name_map[kinds[i % 6]]).append((qs[(i // 6) % 5], sets[(i // 30) % 4]))

gm.BAG_PAGE["page"] = 0
rects, actions = [], []
gm.draw_stats_panel(screen, lv2, font, small_font, rects, actions)
total_groups = len(actions) if False else None
check("一页最多 30 格", len(rects) <= 30, len(rects))
check("有翻页按钮", "prev" in gm.STATS_UI and "next" in gm.STATS_UI)

gm.BAG_PAGE["page"] = 3
rects3, actions3 = [], []
gm.draw_stats_panel(screen, lv2, font, small_font, rects3, actions3)
check("可以翻页", len(rects3) > 0 and gm.BAG_PAGE["page"] == 3, gm.BAG_PAGE["page"])

# ---------- 5. 悬停解释 ----------
target = rects3[0]
gm.pygame.mouse.get_pos = lambda: target.center
gm.draw_stats_panel(screen, lv2, font, small_font, rects3, actions3)
check("悬停装备不报错", True)
check("装备槽记录可用", isinstance(gm.EQUIP_RECTS, list))

# 属性数值
check("武器属性按品质",
      gm.gear_stats("weapon", Q_GOLD)["攻击"] == DMG_BONUS_GOLD,
      gm.gear_stats("weapon", Q_GOLD))
check("裤子提供生命", gm.gear_stats("pants", Q_PURPLE)["生命"] == PANTS_HP[Q_PURPLE])
check("鞋子提供移速", gm.gear_stats("boots", Q_RED)["移速%"] == int(BOOTS_SPEED[Q_RED] * 100))

# ---------- 6. 最终通关画面 ----------
random.seed(9)
lv3 = Level(15, WEAPON_SWORD)
lv3.player.level = MAX_PLAYER_LEVEL
lv3.player.hp = lv3.player.max_hp
gm.draw_win_screen(screen, lv3, font, art.font(42), small_font)
check("通关页出现两个按钮",
      gm.WIN_UI["continue"].width > 0 and gm.WIN_UI["menu"].width > 0, gm.WIN_UI)
check("最终密码是 0909", FINAL_PASSWORD == "0909")
check("通关页渲染成功", True)

save_mod.remove()
print("\nSAVES / BAG / TOOLTIP / WIN CHECKS PASSED")
