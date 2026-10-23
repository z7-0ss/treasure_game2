"""渲染战斗相关场景：BOSS 技能、跟宠治疗、药水掉落、新 HUD。"""
import os, sys, asyncio, random
os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
import main as game_main
from settings import *
from entities import Enemy, Boss, Item

OUT = "preview"
os.makedirs(OUT, exist_ok=True)
RealLevel = game_main.Level


def make_demo(hp=62, boss_skill="slam", spawn_items=True, pet_heal=False):
    class Demo(RealLevel):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            p = self.player
            p.invincible_timer = 0
            p.armor_quality = Q_GOLD
            p.helmet_quality = Q_GOLD
            p.hp = hp
            p.energy = MAX_ENERGY
            p.inventory_weapons = [Q_SILVER, Q_PURPLE, Q_GOLD]
            p.inventory_armors = [Q_SILVER, Q_GOLD]
            p.inventory_helmets = [Q_PURPLE]
            self.has_key = True
            self._refresh_door()
            self.effects.clear()
            self.float_texts.clear()

            # BOSS 挪到玩家旁边，并准备放技能
            self.boss.rect.x = p.rect.x + 230
            self.boss.rect.y = p.rect.y - 30
            self.boss.skill_cd = 9999
            self.boss.cast_timer = 22
            self.boss.pending_skill = boss_skill
            self.boss.hp = int(self.boss.max_hp * 0.62)

            # 几个小怪 + 掉落物
            for et, dx, dy in (("skeleton", 140, 70), ("bat", -120, -40), ("mushroom", 90, 110)):
                e = Enemy(p.rect.centerx + dx, p.rect.centery + dy, et, False, self.level_index)
                e.hp = e.max_hp
                self.enemies.append(e)
            if spawn_items:
                self.items += [
                    Item(p.rect.x + 10, p.rect.y + 70, "potion_hp"),
                    Item(p.rect.x + 60, p.rect.y + 70, "potion_energy"),
                    Item(p.rect.x - 40, p.rect.y + 70, "key"),
                    Item(p.rect.x + 110, p.rect.y + 70, "weapon", Q_GOLD, p.weapon_type),
                ]
            if pet_heal:
                self.pet.heal_cd = 0
    return Demo


def render(name, weapon_click, save_at, demo_kwargs, frames=40, seed=3):
    game_main.Level = make_demo(**demo_kwargs)
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] in save_at:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": weapon_click, "button": 1})],
              frames: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(seed)
    asyncio.run(game_main.main())


render("scene_boss.png", (220, 320), {20}, dict(hp=62, boss_skill="slam"))
render("scene_pet.png", (220, 320), {30}, dict(hp=34, pet_heal=True, spawn_items=False))
render("scene_drops2.png", (220, 320), {14}, dict(hp=88, boss_skill="summon"))
print("ok")

# 角色/背包页面（按 I）
def render_stats(name):
    game_main.Level = make_demo(hp=72, spawn_items=False)
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 26:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {
        0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
        8: [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_i, "mod": 0, "unicode": "i"})],
        40: [pygame.event.Event(pygame.QUIT)],
    }
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(3)
    asyncio.run(game_main.main())

render_stats("scene_stats.png")
print("stats scene ok")
