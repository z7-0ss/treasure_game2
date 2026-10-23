"""渲染各关卡的画面 + 全图缩略图，便于肉眼检查通道宽度。"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
from settings import *
from level import Level, MAP_ROWS, MAP_COLS, CHEST_TILE, DOOR_TILE

OUT = "preview"
os.makedirs(OUT, exist_ok=True)
screen = pygame.display.set_mode((WIDTH, HEIGHT))

for idx, seed in ((0, 5), (1, 5), (2, 5)):
    random.seed(seed)
    lv = Level(idx, WEAPON_SWORD)
    cam_x = max(0, min(lv.player.rect.centerx - WIDTH // 2, MAP_COLS * TILE_SIZE - WIDTH))
    cam_y = max(0, min(lv.player.rect.centery - HEIGHT // 2, MAP_ROWS * TILE_SIZE - HEIGHT))
    lv.draw(screen, cam_x, cam_y)
    pygame.image.save(screen, os.path.join(OUT, f"level{idx}_spawn.png"))

    # 宝箱/门所在的房间
    cam_x = max(0, min(CHEST_TILE[1] * TILE_SIZE - WIDTH // 2, MAP_COLS * TILE_SIZE - WIDTH))
    cam_y = max(0, min(CHEST_TILE[0] * TILE_SIZE - HEIGHT // 2, MAP_ROWS * TILE_SIZE - HEIGHT))
    lv.draw(screen, cam_x, cam_y)
    pygame.image.save(screen, os.path.join(OUT, f"level{idx}_goal.png"))

# 全图缩略图：黑=墙，白=空地，蓝=出生点，绿=宝箱，黄=门
scale = 8
for idx, seed in ((0, 5), (1, 5), (2, 5)):
    random.seed(seed)
    lv = Level(idx, WEAPON_SWORD)
    surf = pygame.Surface((MAP_COLS * scale, MAP_ROWS * scale))
    surf.fill((245, 245, 245))
    for wall in lv.walls:
        pygame.draw.rect(surf, (35, 35, 45),
                         (wall.x // TILE_SIZE * scale, wall.y // TILE_SIZE * scale, scale, scale))
    pygame.draw.rect(surf, (60, 120, 255), (1 * scale, 1 * scale, scale * 2, scale * 2))
    pygame.draw.rect(surf, (40, 200, 80), (CHEST_TILE[1] * scale, CHEST_TILE[0] * scale, scale, scale))
    pygame.draw.rect(surf, (240, 180, 0), (DOOR_TILE[1] * scale, DOOR_TILE[0] * scale, scale, scale))
    pygame.image.save(surf, os.path.join(OUT, f"map{idx}.png"))
print(sorted(os.listdir(OUT)))
