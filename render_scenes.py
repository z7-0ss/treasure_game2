"""渲染真实游戏场景截图，肉眼检查美术与技能效果。"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
from level import Level
from entities import Enemy, Boss, Item

OUT = "preview"
os.makedirs(OUT, exist_ok=True)
screen = pygame.display.set_mode((WIDTH, HEIGHT))

def snap(name, lv):
    cam_x = max(0, min(lv.player.rect.centerx - WIDTH // 2, len(lv.map_data[0]) * TILE_SIZE - WIDTH))
    cam_y = max(0, min(lv.player.rect.centery - HEIGHT // 2, len(lv.map_data) * TILE_SIZE - HEIGHT))
    lv.draw(screen, cam_x, cam_y)
    pygame.image.save(screen, os.path.join(OUT, name))

def arena(weapon, level_idx, monsters, tile=(12, 8)):
    random.seed(9)
    lv = Level(level_idx, weapon)
    lv.enemies.clear()
    lv.items.clear()
    lv.player.invincible_timer = 0
    p = lv.player
    p.rect.x, p.rect.y = tile[0] * TILE_SIZE, tile[1] * TILE_SIZE
    for etype, dx, dy, elite in monsters:
        e = Enemy(p.rect.centerx + dx, p.rect.centery + dy, etype, elite, level_idx)
        e.hp = e.max_hp = 400
        lv.enemies.append(e)
    return lv

# 1. 剑士旋风斩（洞穴）
lv = arena(WEAPON_SWORD, 0, [("slime", 70, -20, False), ("mushroom", -80, 10, False),
                             ("butterfly", 40, -70, False), ("slime", -30, 60, True)])
lv.player.energy = MAX_ENERGY
lv.cast_skill()
for _ in range(13):
    lv.update()
snap("scene_sword.png", lv)

# 2. 弓箭手箭雨（开阔草原，箭矢看得清）
lv = arena(WEAPON_BOW, 1, [("slime", 190, -40, False), ("bat", 230, 10, False),
                           ("mushroom", 160, 60, True)])
lv.player.facing_right = True
lv.player.energy = MAX_ENERGY
lv.cast_skill()
for _ in range(4):
    lv.update()
snap("scene_bow.png", lv)

# 3. 法师冰霜新星 + 冻结（岩洞）
lv = arena(WEAPON_STAFF, 2, [("skeleton", 90, -30, False), ("bat", -90, 20, False),
                             ("tree", 60, 70, True), ("mushroom", -70, 70, False)])
lv.player.energy = MAX_ENERGY
lv.cast_skill()
for _ in range(12):
    lv.update()
snap("scene_staff.png", lv)

# 4. 怪物图鉴：全部 6 种 + BOSS（玩家站左侧）
lv = arena(WEAPON_SWORD, 1, [("slime", 130, -80, False), ("mushroom", 215, -80, False),
                             ("skeleton", 300, -80, False), ("bat", 130, 30, False),
                             ("butterfly", 215, 30, False), ("tree", 300, 30, False)])
lv.enemies.append(Boss(lv.player.rect.centerx + 330, lv.player.rect.centery + 130, level_idx=2))
for e in lv.enemies:
    e.hp = e.max_hp
for _ in range(4):
    lv.update()
snap("scene_monsters.png", lv)

# 5. 掉落物全展示
lv = arena(WEAPON_BOW, 0, [])
p = lv.player
items = [("weapon", Q_WHITE, WEAPON_BOW), ("weapon", Q_SILVER, WEAPON_BOW),
         ("weapon", Q_PURPLE, WEAPON_BOW), ("weapon", Q_GOLD, WEAPON_BOW),
         ("weapon", Q_RED, WEAPON_BOW), ("weapon", Q_GOLD, WEAPON_SWORD),
         ("weapon", Q_GOLD, WEAPON_STAFF), ("armor", Q_PURPLE, None),
         ("armor", Q_GOLD, None), ("helmet", Q_SILVER, None), ("helmet", Q_RED, None),
         ("key", "none", None), ("chest", "none", None)]
for i, (kind, q, wt) in enumerate(items):
    it = Item(p.rect.x + 40 + (i % 7) * 62, p.rect.y + 40 + (i // 7) * 76, kind, q, wt)
    for _ in range(6):
        it.update_physics()
    lv.items.append(it)
snap("scene_items.png", lv)
print("ok")
