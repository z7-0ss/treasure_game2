"""无头渲染：主菜单（含悬停）、游戏内 HUD、技能就绪/释放瞬间。"""
import os, sys, asyncio, random
os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
import main as game_main
from settings import MAX_ENERGY, WIDTH, HEIGHT

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")
os.makedirs(OUT, exist_ok=True)

RealLevel = game_main.Level


class EnergyLevel(RealLevel):
    """渲染用：开局能量拉满，便于展示技能按钮。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player.energy = MAX_ENERGY


game_main.Level = EnergyLevel


def render(name, script_frames, save_at, seed=3, hover=None, frames=120):
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] in save_at:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    if hover:
        game_main.pygame.mouse.get_pos = lambda: hover

    script = {}
    for f, events in script_frames.items():
        script[f] = events
    script.setdefault(frames, []).append(pygame.event.Event(pygame.QUIT))

    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(seed)
    asyncio.run(game_main.main())


click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})

# 菜单（悬停在弓箭手上）
render("01_menu.png", {}, save_at={4}, hover=(470, 320), frames=6)

# 游戏内 HUD：技能就绪
render("hud_ready.png", {0: [click((220, 320))]}, save_at={20}, frames=30)

# 剑士技能释放瞬间 + 冷却环
render("hud_skill.png", {0: [click((220, 320))], 12: [click((755, 455))]},
       save_at={22}, frames=40)
print("ok", os.listdir(OUT))
