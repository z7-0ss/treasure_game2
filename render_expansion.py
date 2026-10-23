"""渲染四大关卡：选关、海底、天空、火山、最终 BOSS、跟宠面板。"""
import os, sys, asyncio, random, shutil
os.environ["TREASURE_SAVE"] = "/tmp/treasure_render_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
import main as gm
from settings import *
import save as save_mod

OUT = "preview"
os.makedirs(OUT, exist_ok=True)

fake_player = {
    "level": 40, "exp": 120, "next_level_exp": 180, "base_max_hp": 1075, "hp": 1075,
    "energy": 100, "weapon_type": WEAPON_STAFF,
    "weapon_quality": Q_RED, "armor_quality": Q_GOLD, "helmet_quality": Q_GOLD,
    "boots_quality": Q_PURPLE, "pants_quality": Q_GOLD, "bracelet_quality": Q_PURPLE,
    "weapon_set": "volcano", "armor_set": "volcano", "helmet_set": "ocean",
    "boots_set": "sky", "pants_set": "ocean", "bracelet_set": "sky",
    "inventory_weapons": [[Q_GOLD, "ocean"], [Q_PURPLE, "sky"], [Q_RED, "volcano"]],
    "inventory_armors": [[Q_SILVER, "forest"], [Q_GOLD, "ocean"]],
    "inventory_helmets": [[Q_PURPLE, "sky"]],
    "inventory_boots": [[Q_WHITE, "forest"], [Q_PURPLE, "ocean"]],
    "inventory_pants": [[Q_SILVER, "sky"]],
    "inventory_bracelets": [[Q_GOLD, "volcano"]],
    "bag": {"potion_hp": 3, "potion_energy": 2, "potion_speed": 1, "bomb": 2},
    "pet_state": {"level": 13, "exp": 5},
}
save_mod.save({"weapon": WEAPON_STAFF, "cleared": list(range(0, 15)), "player": fake_player})


class Demo(gm.Level):
    """把玩家放到 BOSS 竞技场旁边，方便截图。"""

    def __init__(self, level_index, *a, **k):
        super().__init__(level_index, *a, **k)
        self.player.invincible_timer = 10 ** 9
        self.player.rect.center = (self.boss_center[0] - 120, self.boss_center[1] + 96)
        for b in self.bosses:
            b.hp = int(b.max_hp * 0.66)
        final = [b for b in self.bosses if getattr(b, "is_final", False)]
        if final:
            fb = final[0]
            fb.hp = int(fb.max_hp * 0.72)
            self.player.rect.center = (fb.rect.centerx - 40, fb.rect.bottom + 6)


def run(name, script, save_at, level_cls=None, frames=50):
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
    random.seed(4)
    asyncio.run(gm.main())


click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
key = lambda k: pygame.event.Event(pygame.KEYDOWN, {"key": k, "mod": 0, "unicode": ""})

# 选关（第四章标签）
run("scene_select_ch4.png",
    {2: [click((WIDTH // 2, 447))], 6: [click((60 + 3 * 216 + 100, 128))]}, 12)
# 海底 / 天空 / 火山 / 最终关
run("scene_ocean.png", {2: [click((WIDTH // 2, 447))],
                        4: [click((60 + 216 + 100, 128))], 6: [click((180, 300))]}, 26, Demo)
run("scene_sky.png", {2: [click((WIDTH // 2, 447))],
                      4: [click((60 + 2 * 216 + 100, 128))], 6: [click((372, 300))]}, 26, Demo)
run("scene_volcano.png", {2: [click((WIDTH // 2, 447))],
                          4: [click((60 + 3 * 216 + 100, 128))], 6: [click((180, 300))]}, 26, Demo)
run("scene_final_boss.png", {2: [click((WIDTH // 2, 447))],
                             4: [click((60 + 3 * 216 + 100, 128))], 6: [click((765, 300))]}, 32, Demo)
# 跟宠面板
run("scene_pet_panel.png", {2: [click((WIDTH // 2, 447))], 4: [click((180, 300))],
                            10: [key(pygame.K_p)]}, 18)
# 角色页（套装）
run("scene_gear_sets.png", {2: [click((WIDTH // 2, 447))], 4: [click((180, 300))],
                            10: [key(pygame.K_i)]}, 18)

save_mod.remove()
print("ok")
