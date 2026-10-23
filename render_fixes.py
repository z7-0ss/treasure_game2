"""渲染：BOSS 技能特效、裂地斩、箭幕、闪电链、背包折叠、环境状态。"""
import os, sys, asyncio, random
os.environ["TREASURE_SAVE"] = "/tmp/treasure_fix_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
import main as gm, audio, save as save_mod
from level import Level
from entities import (BossSkillFX, GroundCracks, ArrowStormFX, LightningFX,
                      FloatText, Shockwave, SparkBurst)

OUT = "preview"
screen = pygame.display.set_mode((WIDTH, HEIGHT))
audio.init()


def snap(level, name, frames=2):
    for _ in range(frames):
        level.update()
    map_w = len(level.map_data[0]) * TILE_SIZE
    map_h = len(level.map_data) * TILE_SIZE
    cam_x = max(0, min(level.player.rect.centerx - WIDTH // 2, map_w - WIDTH))
    cam_y = max(0, min(level.player.rect.centery - HEIGHT // 2, map_h - HEIGHT))
    level.draw(screen, cam_x, cam_y)
    pygame.image.save(screen, os.path.join(OUT, name))


# 海底 BOSS 冰冻
random.seed(5)
lv = Level(5, WEAPON_SWORD)
lv.player.invincible_timer = 10 ** 9
lv.player.rect.center = (lv.boss.rect.centerx - 90, lv.boss.rect.centery + 30)
lv.effects.append(BossSkillFX("ice_nova", lv.boss.rect.centerx, lv.boss.rect.centery + 20,
                              150, (140, 210, 255), 30))
lv.player.chill_timer = 120
lv.float_texts.append(FloatText(lv.player.rect.centerx, lv.player.rect.top - 24,
                                "冰冻！", (150, 220, 255), 17, 60))
lv.shake = 6
snap(lv, "scene_ice_nova.png", 4)

# 火山：灼烧 + 裂地斩裂缝
random.seed(7)
lv2 = Level(13, WEAPON_SWORD)
lv2.player.invincible_timer = 10 ** 9
lv2.player.rect.center = (lv2.boss.rect.centerx - 130, lv2.boss.rect.centery + 40)
lv2.player.burn_timer = 110
lv2.effects.append(GroundCracks(lv2.player.rect.centerx, lv2.player.rect.bottom, 170,
                                (255, 170, 110), 30))
lv2.effects.append(Shockwave(lv2.player.rect.centerx, lv2.player.rect.centery, 170,
                             (255, 170, 110), 28, 10, 0.2))
lv2.effects.append(SparkBurst(lv2.player.rect.centerx, lv2.player.rect.centery,
                              (255, 150, 60), 10, 2.4, 16, 2, -0.2))
lv2.float_texts.append(FloatText(lv2.player.rect.centerx, lv2.player.rect.top - 24,
                                 "灼烧！", (255, 150, 80), 16, 60))
snap(lv2, "scene_burning.png", 3)

# 箭幕 + 闪电链
random.seed(9)
lv3 = Level(9, WEAPON_BOW)
lv3.player.invincible_timer = 10 ** 9
lv3.player.rect.center = (lv3.boss.rect.centerx - 120, lv3.boss.rect.centery + 60)
lv3.effects.append(ArrowStormFX(lv3.player.rect.centerx, lv3.player.rect.centery,
                                240, (200, 255, 210), 34, 24))
lv3.effects.append(LightningFX(lv3.player.rect.centerx, lv3.player.rect.centery - 20,
                               lv3.boss.rect.centerx, lv3.boss.rect.centery,
                               (180, 220, 255), 14, 10))
lv3.float_texts.append(FloatText(lv3.boss.rect.centerx, lv3.boss.rect.top - 16,
                                 "暴击 812", (255, 220, 120), 19, 60))
snap(lv3, "scene_arrowstorm.png", 4)

# 背包折叠（重复装备）
fake_player = {
    "level": 30, "exp": 10, "next_level_exp": 200, "base_max_hp": 825, "hp": 825,
    "energy": 100, "weapon_type": WEAPON_SWORD,
    "weapon_quality": Q_GOLD, "armor_quality": Q_PURPLE, "helmet_quality": Q_SILVER,
    "boots_quality": Q_SILVER, "pants_quality": Q_PURPLE, "bracelet_quality": Q_GOLD,
    "weapon_set": "ocean", "armor_set": "ocean", "helmet_set": "sky",
    "boots_set": "forest", "pants_set": "volcano", "bracelet_set": "forest",
    "inventory_weapons": [[Q_GOLD, "ocean"]] * 4 + [[Q_PURPLE, "sky"]] * 3,
    "inventory_armors": [[Q_SILVER, "forest"]] * 5 + [[Q_GOLD, "volcano"]] * 2,
    "inventory_helmets": [[Q_PURPLE, "ocean"]] * 3,
    "inventory_boots": [[Q_WHITE, "forest"]] * 6,
    "inventory_pants": [[Q_GOLD, "sky"]] * 2,
    "inventory_bracelets": [[Q_RED, "volcano"]],
    "bag": {"potion_hp": 4, "potion_energy": 2, "potion_speed": 1, "bomb": 3},
    "pet_state": {"level": 20, "exp": 6},
}
save_mod.save({"weapon": WEAPON_SWORD, "cleared": list(range(0, 14)), "player": fake_player})


def run(name, script, save_at, frames=20):
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
    random.seed(2)
    asyncio.run(gm.main())


click = lambda pos: pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
key = lambda k: pygame.event.Event(pygame.KEYDOWN, {"key": k, "mod": 0, "unicode": ""})
run("scene_bag_stack.png",
    {2: [click((WIDTH // 2, 447))], 4: [click((180, 300))], 10: [key(pygame.K_i)]}, 18)
save_mod.remove()
print("ok")
