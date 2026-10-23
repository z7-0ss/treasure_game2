"""渲染新内容：角色三职业、矮墙/天气/新道具、雷达、地图、BOSS 竞技场、通关页。"""
import os, sys, asyncio, random
os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
pygame.mixer.init = lambda *a, **k: None      # 渲染时不占用声卡
from settings import *
import art
import main as game_main
from entities import Item
from level import MAP_COLS, MAP_ROWS

OUT = "preview"
os.makedirs(OUT, exist_ok=True)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
RealLevel = game_main.Level

# ---------------- 1. 角色三职业立绘 ----------------
def render_characters():
    surf = pygame.Surface((760, 420))
    surf.fill((26, 22, 34))
    font = art.font(15)
    cols = [WEAPON_SWORD, WEAPON_BOW, WEAPON_STAFF]
    gears = [(Q_WHITE, "none"), (Q_SILVER, Q_SILVER), (Q_GOLD, Q_GOLD), (Q_RED, Q_RED)]
    for ci, wt in enumerate(cols):
        for gi, (armor_q, helmet_q) in enumerate(gears):
            armor = (72, 132, 204) if armor_q == Q_WHITE else Q_COLOR[armor_q]
            head = HAIR_COLOR if helmet_q == "none" else Q_COLOR[helmet_q]
            spr = art.player_sprite(armor, head)
            big = pygame.transform.scale(spr, (spr.get_width() * 3, spr.get_height() * 3))
            x = 40 + ci * 240 + gi * 52
            y = 120
            surf.blit(big, (x, y))
            art.draw_player_hat(surf, x, y, wt, head)
    for ci, wt in enumerate(cols):
        t = font.render(CLASS_NAME[wt], True, (255, 220, 235))
        surf.blit(t, (40 + ci * 240, 60))
    t = font.render("角色立绘：不同职业头饰 + 装备品质配色（白/银/金/红）", True, (210, 210, 220))
    surf.blit(t, (40, 20))
    pygame.image.save(surf, os.path.join(OUT, "scene_characters.png"))


# ---------------- 2. 游戏内：矮墙 / 天气 / 新道具 ----------------
def make_world(kind):
    class Demo(RealLevel):
        def __init__(self, level_index, *a, **k):
            super().__init__(kind, *a, **k)
            p = self.player
            p.invincible_timer = 0
            p.armor_quality = Q_GOLD
            p.helmet_quality = Q_GOLD
            p.boots_quality = Q_SILVER
            p.pants_quality = Q_GOLD
            p.bracelet_quality = Q_PURPLE
            p.inventory_weapons = [Q_SILVER, Q_PURPLE, Q_GOLD]
            p.inventory_armors = [Q_SILVER, Q_GOLD]
            p.inventory_helmets = [Q_PURPLE]
            p.inventory_boots = [Q_WHITE, Q_PURPLE]
            p.inventory_pants = [Q_SILVER]
            p.inventory_bracelets = [Q_GOLD]
            p.bag["potion_hp"] = 3
            p.bag["potion_speed"] = 1
            p.bag["bomb"] = 2
            self.pet.level = 7
            self.has_key = True
            self._refresh_door()
            # 在玩家附近摆上新道具
            self.items += [
                Item(p.rect.x + 70, p.rect.y + 60, "potion_speed"),
                Item(p.rect.x + 130, p.rect.y + 60, "bomb"),
                Item(p.rect.x - 40, p.rect.y + 60, "potion_hp"),
            ]
            self.float_texts.clear()
    return Demo


def render_world(name, level_idx, save_at=14):
    game_main.Level = make_world(level_idx)
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == save_at:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              40: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(2)
    asyncio.run(game_main.main())


# ---------------- 3. 地图界面 ----------------
def render_map(name="scene_map.png"):
    game_main.Level = make_world(1)
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 22:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              10: [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_m, "mod": 0, "unicode": "m"})],
              40: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(3)
    asyncio.run(game_main.main())


# ---------------- 4. 通关页面 ----------------
def render_win(name="scene_win.png"):
    class WinDemo(RealLevel):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.has_key = True
            self.boss_defeated = True
            self.door_open = True
            self.player.rect.center = self.door_rect.center

    game_main.Level = WinDemo
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 18:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              60: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(4)
    asyncio.run(game_main.main())


# ---------------- 5. BOSS 竞技场 ----------------
def render_boss_arena(name="scene_arena.png"):
    class ArenaDemo(RealLevel):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            p = self.player
            p.invincible_timer = 0
            self.has_key = True
            self._refresh_door()
            # 把玩家传送到竞技场边缘
            self.player.rect.center = (self.boss_center[0] - 140, self.boss_center[1] + 60)
            self.boss.hp = int(self.boss.max_hp * 0.7)
            self.boss.skill_cd = 30
    game_main.Level = ArenaDemo
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 40:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              70: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(5)
    asyncio.run(game_main.main())


render_characters()
render_world("scene_world_maze.png", 0)
render_world("scene_world_rain.png", 2)
render_map()
render_win()
render_boss_arena()
print("ok")

# ---------------- 6. 角色/装备/背包界面 ----------------
def render_stats(name="scene_stats.png"):
    game_main.Level = make_world(1)
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
    random.seed(7)
    asyncio.run(game_main.main())


render_stats()


# ---------------- 8. 新地形：平台/尖刺/木箱 ----------------
def render_terrain(name="scene_terrain.png"):
    class TerrainDemo(RealLevel):
        def __init__(self, level_index, *a, **k):
            super().__init__(1, *a, **k)
            self.player.invincible_timer = 0
            self.has_key = True
            self._refresh_door()
            p = self.player
            base_c = p.rect.centerx // TILE_SIZE + 3
            base_r = p.rect.centery // TILE_SIZE
            layout = [(0, 0, "7"), (-1, 0, "7"), (0, 2, "8"), (0, 3, "8"), (0, 5, "9")]
            for dr, dc, ch in layout:
                r, c = base_r + dr, base_c + dc
                if 0 < r < len(self.map_data) - 1 and 0 < c < len(self.map_data[0]) - 1:
                    self.map_data[r] = self.map_data[r][:c] + ch + self.map_data[r][c + 1:]
                    x, y = c * TILE_SIZE, r * TILE_SIZE
                    if ch == "7" and pygame.Rect(x, y, TILE_SIZE, TILE_SIZE) not in self.platform_rects:
                        self.platform_rects.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                    if ch == "8" and pygame.Rect(x, y, TILE_SIZE, TILE_SIZE) not in self.spike_rects:
                        self.spike_rects.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                    if ch == "9":
                        rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                        self.crates.append({"rect": rect, "hp": 3, "max_hp": 3})
                        self.crate_rects.append(rect)
            self.items += [Item(p.rect.x + 40, p.rect.y + 80, "potion_hp"),
                           Item(p.rect.x + 100, p.rect.y + 80, "bomb")]
            size = (len(self.map_data[0]) * TILE_SIZE, len(self.map_data) * TILE_SIZE)
            self.map_surface = art.paint_map(pygame.Surface(size), self.map_data, 1)
            self.minimap = pygame.transform.smoothscale(self.map_surface, (MAP_COLS * 4, MAP_ROWS * 4))
            self.radar_surface = pygame.transform.smoothscale(self.minimap, (200, 100))
    game_main.Level = TerrainDemo
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 16:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              40: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(21)
    asyncio.run(game_main.main())


render_terrain()
print("terrain ok")

# ---------------- 7. BOSS 召唤物 ----------------
def render_summons(name="scene_summons.png"):
    class SummonDemo(RealLevel):
        def __init__(self, level_index, *a, **k):
            super().__init__(2, *a, **k)
            self.player.invincible_timer = 0
            self.has_key = True
            self._refresh_door()
            self.player.rect.center = (self.boss_center[0] - 150, self.boss_center[1] + 70)
            self.boss.hp = int(self.boss.max_hp * 0.8)
            self.boss.pending_skill = "summon"
            self.boss._release_skill(self, self.player)
            self.boss.skill_cd = 9999
    game_main.Level = SummonDemo
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 30:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              50: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(9)
    asyncio.run(game_main.main())


render_summons()
print("summons ok")

# ---------------- 9. BOSS 施法动态效果 ----------------
def render_bosscast(name="scene_bosscast.png"):
    class CastDemo(RealLevel):
        def __init__(self, level_index, *a, **k):
            super().__init__(1, *a, **k)
            self.player.invincible_timer = 0
            self.has_key = True
            self._refresh_door()
            self.player.rect.center = (self.boss_center[0] - 150, self.boss_center[1] + 40)
            self.boss.skill_cd = 0
            self.boss.hp = int(self.boss.max_hp * 0.8)
    game_main.Level = CastDemo
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == 22:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    game_main.pygame.display.flip = fake_flip
    script = {0: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (220, 320), "button": 1})],
              40: [pygame.event.Event(pygame.QUIT)]}
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    random.seed(23)
    asyncio.run(game_main.main())


render_bosscast()
print("bosscast ok")
