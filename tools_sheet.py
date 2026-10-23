"""生成美术校对图：怪物精灵 + 掉落物 + 地砖（放大 3 倍）。"""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
import art

os.makedirs("preview", exist_ok=True)
font = pygame.font.SysFont("pingfang", 14)

def sheet_monsters():
    types = ["slime", "mushroom", "skeleton", "bat", "butterfly", "tree"]
    cols = 3
    cell_w, cell_h = 150, 140
    W = cell_w * cols + 40
    H = cell_h * len(types) + 40
    screen = pygame.display.set_mode((W, H))
    screen.fill((24, 22, 32))
    for row, name in enumerate(types):
        sprites = [("普通", art.monster_sprite(name, False, 0)),
                   ("帧1", art.monster_sprite(name, False, 1)),
                   ("精英", art.monster_sprite(name, True, 0))]
        for col, (label, spr) in enumerate(sprites):
            big = pygame.transform.scale(spr, (spr.get_width() * 3, spr.get_height() * 3))
            cx = 20 + col * cell_w + cell_w // 2
            cy = 20 + row * cell_h + 45
            screen.blit(big, (cx - big.get_width() // 2, cy - big.get_height() // 2))
            if label == "精英":
                art.draw_crown(screen, cx, cy - big.get_height() // 2 - 10, 0)
            t = font.render(f"{name} {label}", True, (230, 230, 230))
            screen.blit(t, (cx - t.get_width() // 2, 20 + row * cell_h + 105))
    pygame.image.save(screen, "preview/sheet_monsters.png")

def sheet_items():
    quals = [Q_WHITE, Q_SILVER, Q_PURPLE, Q_GOLD, Q_RED]
    kinds = [("武器·剑", "weapon", WEAPON_SWORD), ("武器·弓", "weapon", WEAPON_BOW),
             ("武器·杖", "weapon", WEAPON_STAFF), ("衣服", "armor", None),
             ("头盔", "helmet", None), ("钥匙", "key", None), ("宝箱", "chest", None)]
    cell = 90
    W, H = cell * len(kinds) + 40, cell * len(quals) + 50
    screen = pygame.display.set_mode((W, H))
    screen.fill((24, 22, 32))
    for ci, (label, kind, wt) in enumerate(kinds):
        t = font.render(label, True, (230, 230, 230))
        screen.blit(t, (20 + ci * cell + cell // 2 - t.get_width() // 2, 8))
    for ri, q in enumerate(quals):
        for ci, (label, kind, wt) in enumerate(kinds):
            surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            art.draw_item_icon(surf, 2, 2, kind, q, wt, 0.7)
            big = pygame.transform.scale(surf, (120, 120))
            screen.blit(big, (20 + ci * cell - 15, 30 + ri * cell - 15))
        t = font.render(q, True, Q_COLOR[q])
        screen.blit(t, (W - 60, 30 + ri * cell + 35))
    pygame.image.save(screen, "preview/sheet_items.png")

def sheet_tiles():
    for lvl in (0, 1):
        rows = []
        for r in range(8):
            row = []
            for c in range(14):
                wall = r in (0, 7) or c in (0, 13) or (r, c) in ((2, 4), (2, 5), (3, 8), (5, 6), (5, 7), (5, 8))
                row.append("1" if wall else "0")
            rows.append(row)
        surf = pygame.Surface((TILE_SIZE * 14, TILE_SIZE * 8))
        art.paint_map(surf, rows, lvl)
        big = pygame.transform.scale(surf, (surf.get_width() * 2, surf.get_height() * 2))
        pygame.image.save(big, f"preview/tiles_{lvl}.png")

sheet_monsters(); sheet_items(); sheet_tiles()
print("ok")
