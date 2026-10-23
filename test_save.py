"""存档与选关校验：通关写档、重开读档、已通关卡可重复挑战、右键丢弃。"""
import asyncio
import os
import random
import shutil
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import *
import save as save_mod
import main as gm
from entities import Player

SAVE_PATH = save_mod._PATH
BACKUP = SAVE_PATH + ".testbak"


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# 备份玩家真实存档
if os.path.isfile(SAVE_PATH):
    shutil.copy2(SAVE_PATH, BACKUP)
save_mod.remove()

RealLevel = gm.Level


def run(frames_script, level_cls, frames=30):
    created = []

    class Rec(level_cls):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            created.append(self)

    gm.Level = Rec
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return frames_script.get(i, [])

    gm.pygame.event.get = fake_get
    gm.pygame.display.flip = lambda: None
    random.seed(1)
    asyncio.run(gm.main())
    gm.Level = RealLevel
    return created


class AutoClear(RealLevel):
    """第一关自动通关，用来产生存档。"""

    def __init__(self, level_index, weapon_type, existing_player=None):
        super().__init__(level_index, weapon_type, existing_player)
        self.has_key = True
        self.boss_defeated = True
        self._refresh_door()
        self.player.rect.center = self.door_rect.center


click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
quit_ev = pygame.event.Event(pygame.QUIT)

# ---------- 1. 首次通关写入存档 ----------
created = run({0: [click((220, 320))], 20: [quit_ev]}, AutoClear)
check("通关后会生成存档文件", os.path.isfile(SAVE_PATH))
data = save_mod.load() or {}
check("存档记录了通关进度", 0 in data.get("cleared", []), data.get("cleared"))
check("存档里有角色数据", isinstance(data.get("player"), dict), type(data.get("player")))
saved_level = data["player"].get("level", 1)

# ---------- 2. 重开游戏能读档，并且可以重复挑战第一关 ----------
game = run({2: [click((WIDTH // 2, 447))],      # 继续冒险
            4: [click((180, 300))],             # 第一关卡片
            14: [quit_ev]}, RealLevel)
check("从选关界面进入了关卡", len(game) >= 1, len(game))
check("读档后关卡索引正确", game[0].level_index == 0, game[0].level_index)
check("读档保留角色等级", game[0].player.level == saved_level,
      (game[0].player.level, saved_level))

# ---------- 3. 存档序列化往返 ----------
p = Player(0, 0, WEAPON_BOW)
p.level = 6
p.weapon_quality = Q_GOLD
p.pants_quality = Q_RED
p.inventory_boots = [Q_SILVER, Q_PURPLE]
p.bag["bomb"] = 4
p.pet_state = {"level": 5, "exp": 2}
clone = Player.from_dict(p.to_dict())
check("存档往返保留等级", clone.level == 6)
check("存档往返保留装备", clone.weapon_quality == Q_GOLD and clone.pants_quality == Q_RED)
check("存档往返保留背包",
      [e[0] for e in clone.inventory_boots] == [Q_SILVER, Q_PURPLE],
      clone.inventory_boots)
check("存档往返保留道具", clone.bag["bomb"] == 4)
check("存档往返保留跟宠", clone.pet_state["level"] == 5)
check("裤子加成写入血量上限",
      clone.max_hp == clone.base_max_hp + PANTS_HP[Q_RED], clone.max_hp)

# ---------- 4. 右键丢弃 ----------
p2 = Player(0, 0, WEAPON_SWORD)
p2.inventory_weapons = [Q_SILVER, Q_GOLD]
removed = gm.discard_from_inventory(p2, "weapon", 0)
check("丢弃返回被丢的装备", removed == Q_SILVER, removed)
check("丢弃后背包减少", p2.inventory_weapons == [Q_GOLD], p2.inventory_weapons)

# 还原玩家真实存档
save_mod.remove()
if os.path.isfile(BACKUP):
    shutil.move(BACKUP, SAVE_PATH)

print("\nSAVE / SELECT CHECKS PASSED")
