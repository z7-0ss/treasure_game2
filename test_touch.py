"""手机/触摸适配校验：手指事件驱动按钮、摇杆、多点触控、通关页按钮。"""
import asyncio
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_touch_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import *
import main as gm
from entities import Player

DOWN, UP, MOTION = pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


def finger(kind, fid, pos):
    return pygame.event.Event(kind, {
        "finger_id": fid, "x": pos[0] / WIDTH, "y": pos[1] / HEIGHT,
        "dx": 0, "dy": 0, "touch": True, "window": 1,
    })


quit_ev = pygame.event.Event(pygame.QUIT)
RealLevel = gm.Level

# 统计攻击/跳跃次数
counts = {"attack": 0, "jump": 0, "skill3": 0}
real_attack, real_jump = Player.attack, Player.jump


def spy_attack(self):
    counts["attack"] += 1
    return real_attack(self)


def spy_jump(self):
    counts["jump"] += 1
    return real_jump(self)


Player.attack = spy_attack
Player.jump = spy_jump

import level as level_mod
real_cast = level_mod.Level.cast_skill


def spy_cast(self, slot=0):
    if slot == 2:
        counts["skill3"] += 1
    return real_cast(self, slot)


level_mod.Level.cast_skill = spy_cast


class RecLevel(RealLevel):
    positions = []

    def update(self):
        super().update()
        RecLevel.positions.append(self.player.rect.x)


def run(script, level_cls=RecLevel, frames=40):
    created = []

    class Rec(level_cls):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            created.append(self)

    gm.Level = Rec
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
    random.seed(5)
    asyncio.run(gm.main())
    gm.Level = RealLevel
    return created


# ---------- 1. 手指点击职业卡开始游戏 ----------
created = run({
    0: [finger(DOWN, 0, (220, 320)), finger(UP, 0, (220, 320))],
    30: [],
})
check("手指点职业卡能开始游戏", len(created) == 1, len(created))
player = created[0].player

# ---------- 2. 触摸攻击 / 跳跃按钮 ----------
counts["attack"] = counts["jump"] = 0
run({
    0: [finger(DOWN, 0, (220, 320)), finger(UP, 0, (220, 320))],
    4: [finger(DOWN, 1, (865, 445)), finger(UP, 1, (865, 445))],
    8: [finger(DOWN, 2, (690, 500)), finger(UP, 2, (690, 500))],
    10: [finger(DOWN, 5, (575, 415)), finger(UP, 5, (575, 415))],
    20: [],
})
check("触摸攻击按钮能攻击", counts["attack"] >= 1, counts["attack"])
check("触摸跳跃按钮能跳跃", counts["jump"] >= 1, counts["jump"])
check("触摸第三技能按钮能放技能", counts.get("skill3", 0) >= 1, counts.get("skill3"))

# ---------- 3. 摇杆拖动 + 多点触控（按住摇杆同时点攻击） ----------
RecLevel.positions.clear()
counts["attack"] = 0
run({
    0: [finger(DOWN, 0, (220, 320)), finger(UP, 0, (220, 320))],
    4: [finger(DOWN, 10, (100, 440))],          # 左手按摇杆
    5: [finger(MOTION, 10, (150, 440))],        # 往右推
    6: [finger(MOTION, 10, (160, 440)),
        finger(DOWN, 11, (865, 445)),           # 右手同时点攻击
        finger(UP, 11, (865, 445))],
    12: [],                                      # 摇杆继续按住
    16: [finger(UP, 10, (160, 440))],
    24: [],
})
check("摇杆拖动让角色移动", RecLevel.positions and max(RecLevel.positions) > RecLevel.positions[0] + 8,
      (RecLevel.positions[:1], max(RecLevel.positions) if RecLevel.positions else None))
check("多点触控时另一根手指能攻击", counts["attack"] >= 1, counts["attack"])

# ---------- 4. 通关页按钮：继续挑战 → 选关 → 重打第一关 ----------
class AutoClear(RealLevel):
    def __init__(self, level_index, weapon_type, existing_player=None):
        super().__init__(level_index, weapon_type, existing_player)
        self.has_key = True
        self.boss_defeated = True
        self._refresh_door()
        self.player.rect.center = self.door_rect.center


created = run({
    0: [finger(DOWN, 0, (220, 320)), finger(UP, 0, (220, 320))],
    30: [finger(DOWN, 2, (368, 441)), finger(UP, 2, (368, 441))],   # 继续挑战
    34: [finger(DOWN, 3, (180, 300)), finger(UP, 3, (180, 300))],   # 第一关
    44: [],
}, level_cls=AutoClear)
check("通关页触摸继续挑战能进选关再开新关",
      len(created) >= 5 and any(lv.level_index == 0 for lv in created[4:]),
      [lv.level_index for lv in created])

# ---------- 5. SCALED 显示模式可用（手机等比缩放） ----------
screen = pygame.display.get_surface()
check("显示表面是逻辑分辨率 960x540",
      screen is None or screen.get_size() == (WIDTH, HEIGHT),
      None if screen is None else screen.get_size())

Player.attack, Player.jump = real_attack, real_jump
print("\nTOUCH / MOBILE CHECKS PASSED")
