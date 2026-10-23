"""渲染战斗特效：刀光、火花、魔法阵、暴击、BOSS 蓄力。"""
import os, sys, random
os.environ["TREASURE_SAVE"] = "/tmp/treasure_fx_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
import art, audio
from level import Level
from entities import SparkBurst, SlashArc, CastCircle, FloatText, Shockwave, BossCast, MeteorStrike

screen = pygame.display.set_mode((WIDTH, HEIGHT))
audio.init()


def snap(level, name, frames=3):
    for _ in range(frames):
        level.update()
    map_w = len(level.map_data[0]) * TILE_SIZE
    map_h = len(level.map_data) * TILE_SIZE
    cam_x = max(0, min(level.player.rect.centerx - WIDTH // 2, map_w - WIDTH))
    cam_y = max(0, min(level.player.rect.centery - HEIGHT // 2, map_h - HEIGHT))
    level.draw(screen, cam_x, cam_y)
    pygame.image.save(screen, os.path.join("preview", name))


random.seed(4)
# ---------- 近战：刀光 + 火花 + 暴击 ----------
lv = Level(13, WEAPON_SWORD)
lv.player.invincible_timer = 10 ** 9
lv.player.level = 42
enemy = lv.enemies[0]
enemy.hp = enemy.max_hp = 9999
lv.player.rect.center = (enemy.rect.centerx - 44, enemy.rect.centery)
lv.player.facing_right = True
lv.update()
for i in range(3):
    lv.player.attack()
    lv.update()
enemy.hit_timer = 6
lv.effects.append(SlashArc(lv.player.rect.centerx + 30, lv.player.rect.centery, 1,
                           (255, 236, 190), 62))
lv.effects.append(SparkBurst(enemy.rect.centerx, enemy.rect.centery, (255, 232, 130),
                             18, 5.0, 22, 4))
lv.float_texts.append(FloatText(enemy.rect.centerx, enemy.rect.top - 18,
                                "暴击 386", (255, 220, 120), 19, 60))
lv.shake = 4
snap(lv, "scene_crit.png", 2)

# ---------- 法师：陨石 + 魔法阵 ----------
random.seed(6)
lv2 = Level(9, WEAPON_STAFF)
lv2.player.invincible_timer = 10 ** 9
lv2.player.level = 40
lv2.player.rect.center = (lv2.boss.rect.centerx - 120, lv2.boss.rect.centery + 40)
lv2.cast_skill(2)
lv2.effects.append(CastCircle(lv2.player.rect.centerx, lv2.player.rect.bottom, (150, 200, 255)))
lv2.effects.append(SparkBurst(lv2.boss.rect.centerx, lv2.boss.rect.centery,
                              (255, 200, 140), 16, 4.2, 24, 4))
lv2.float_texts.append(FloatText(lv2.boss.rect.centerx, lv2.boss.rect.top - 16,
                                 "暴击 921", (255, 220, 120), 20, 60))
snap(lv2, "scene_meteor.png", 6)

# ---------- BOSS 蓄力 + 召唤 ----------
random.seed(8)
lv3 = Level(12, WEAPON_BOW)
lv3.player.invincible_timer = 10 ** 9
lv3.player.rect.center = (lv3.boss.rect.centerx - 140, lv3.boss.rect.centery + 60)
lv3.boss.pending_skill = "summon"
lv3.boss.cast_timer = 20
lv3.effects.append(BossCast(lv3.boss.rect.centerx, lv3.boss.rect.centery,
                            lv3.boss.rect.width, duration=34, color=(255, 140, 90)))
lv3.effects.append(Shockwave(lv3.boss.rect.centerx, lv3.boss.rect.centery, 160,
                             (255, 150, 90), 26, 8, 0.18))
lv3.float_texts.append(FloatText(lv3.boss.rect.centerx, lv3.boss.rect.top - 26,
                                 "召唤！", (255, 220, 160), 20, 70))
snap(lv3, "scene_boss_cast2.png", 2)

print("ok")
