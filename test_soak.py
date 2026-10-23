"""压力测试：四种武器 × 四个关卡，随机操作各 900 帧，含绘制。"""
import os, sys, random
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
from level import Level

screen = pygame.display.set_mode((WIDTH, HEIGHT))
random.seed(0)
total_frames = 0
kills = 0
for weapon in (WEAPON_SWORD, WEAPON_BOW, WEAPON_STAFF):
    for lvl_idx in (0, 1, 2, 3):
        lv = Level(lvl_idx, weapon)
        lv.player.invincible_timer = 10**9   # 只压测流程，不死
        for frame in range(900):
            dx = random.choice((-1, 0, 1))
            dy = random.choice((-1, 0, 1))
            lv.player.move(dx, dy, lv.walls)
            if frame % 9 == 0:
                lv.player.attack()
            if frame % 37 == 0:
                lv.player.jump()
            if frame % 60 == 0:
                lv.player.energy = MAX_ENERGY
                lv.cast_skill()
            before = len(lv.enemies)
            lv.update()
            kills += max(0, before - len(lv.enemies))
            if frame % 12 == 0:
                lv.draw(screen, 0, 0)
            total_frames += 1
print(f"soak ok: {total_frames} 帧, 击杀 {kills}, 掉落 {len(lv.items)} 件")
