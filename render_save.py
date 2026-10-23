"""渲染：带存档的主菜单、选关界面、第四关三 BOSS、角色面板。"""
import os, sys, asyncio, random, shutil
os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
import main as gm
from settings import *
import save as save_mod

OUT = "preview"
os.makedirs(OUT, exist_ok=True)
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")
BAK = SAVE + ".renderbak"
if os.path.isfile(SAVE):
    shutil.copy2(SAVE, BAK)

# 造一个进度：已通 3 关，角色 Lv.6
fake_player = {
    "level": 6, "exp": 30, "next_level_exp": 150, "base_max_hp": 225, "hp": 225,
    "energy": 100, "weapon_type": WEAPON_SWORD,
    "weapon_quality": Q_GOLD, "armor_quality": Q_PURPLE, "helmet_quality": Q_PURPLE,
    "boots_quality": Q_SILVER, "pants_quality": Q_GOLD, "bracelet_quality": Q_PURPLE,
    "inventory_weapons": [Q_SILVER, Q_PURPLE, Q_GOLD],
    "inventory_armors": [Q_SILVER, Q_GOLD], "inventory_helmets": [Q_PURPLE],
    "inventory_boots": [Q_WHITE, Q_PURPLE], "inventory_pants": [Q_SILVER],
    "inventory_bracelets": [Q_GOLD],
    "bag": {"potion_hp": 3, "potion_energy": 1, "potion_speed": 0, "bomb": 2},
    "pet_state": {"level": 7, "exp": 4},
}
save_mod.save({"weapon": WEAPON_SWORD, "cleared": [0, 1, 2], "player": fake_player})


class TripleDemo(gm.Level):
    def __init__(self, level_index, *a, **k):
        super().__init__(level_index, *a, **k)
        self.player.invincible_timer = 0
        if self.level_index == 3:
            self.player.rect.center = (self.boss_center[0] - 175, self.boss_center[1] + 95)
            for b in self.bosses:
                b.hp = int(b.max_hp * 0.75)


def run(name, script, save_at, level_cls=None, frames=40):
    gm.Level = level_cls or gm.Level
    flips = {"n": 0}

    def fake_flip():
        flips["n"] += 1
        if flips["n"] == save_at:
            pygame.image.save(pygame.display.get_surface(), os.path.join(OUT, name))

    gm.pygame.display.flip = fake_flip
    script = dict(script)
    script.setdefault(frames, []).append(pygame.event.Event(pygame.QUIT))
    counter = {"n": 0}

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        return script.get(i, [])

    gm.pygame.event.get = fake_get
    random.seed(3)
    asyncio.run(gm.main())


click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})

run("scene_menu_save.png", {}, 4)
run("scene_select.png", {2: [click((WIDTH // 2, 447))]}, 8)
run("scene_triple.png", {2: [click((WIDTH // 2, 447))], 4: [click((765, 300))]},
    26, level_cls=TripleDemo)
run("scene_stats2.png", {2: [click((WIDTH // 2, 447))], 4: [click((180, 300))],
                         10: [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_i, "mod": 0, "unicode": "i"})]},
    20)

save_mod.remove()
if os.path.isfile(BAK):
    shutil.move(BAK, SAVE)
print("ok")
