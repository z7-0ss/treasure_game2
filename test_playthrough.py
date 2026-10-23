"""端到端：出生点 → 捡钥匙 → 找到并击杀 BOSS → 传送门过关。"""
import os, sys, random
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import TILE_SIZE, WEAPON_SWORD
from level import (Level, _reachable_cells, START_TILE, CHEST_TILE, DOOR_TILE,
                   KEY_TILE, MAP_ROWS, MAP_COLS)


def bfs_cells(cells, start, goal):
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        r, c = cur
        for nxt in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if nxt in cells and nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    if goal not in prev:
        return None
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def drive(level, path, max_frames=9000):
    player, walls = level.player, level.walls
    frames = 0
    for (r, c) in path[1:]:
        tx, ty = c * TILE_SIZE + 4, r * TILE_SIZE + 16
        stall = 0
        while frames < max_frames:
            frames += 1
            dx = 0 if abs(tx - player.rect.x) <= 4 else (1 if tx > player.rect.x else -1)
            dy = 0 if abs(ty - player.rect.y) <= 4 else (1 if ty > player.rect.y else -1)
            if dx == 0 and dy == 0:
                break
            before = player.rect.topleft
            player.move(dx, dy, walls)
            player.update(walls)
            level.enemies.clear()          # 只测走位
            level.update()
            if player.rect.topleft == before:
                stall += 1
                if stall > 180:
                    return False, frames, f"在 {(r, c)} 卡住"
            else:
                stall = 0
    return True, frames, ""


def nearest_cell(cells, tile, limit=3):
    r, c = tile
    best, best_d = None, 10 ** 9
    for (rr, cc) in cells:
        d = abs(rr - r) + abs(cc - c)
        if d < best_d and d <= limit:
            best, best_d = (rr, cc), d
    return best


def playthrough(level_idx, weapon_type, seed):
    random.seed(seed)
    level = Level(level_idx, weapon_type)
    player = level.player
    player.invincible_timer = 10 ** 9

    cells = _reachable_cells(level.map_data, START_TILE)
    cur = START_TILE if START_TILE in cells else (START_TILE[0] + 1, START_TILE[1])

    # 1) 找到 BOSS 并击杀
    boss = level.boss
    boss.freeze(10 ** 9)
    bcell = (boss.rect.centery // TILE_SIZE, boss.rect.centerx // TILE_SIZE)
    goal = nearest_cell(cells, bcell, 4)
    if goal is None:
        return False, "BOSS 周围没有可站立点"
    path = bfs_cells(cells, cur, goal)
    if path is None:
        return False, "走不到 BOSS"
    ok, frames, why = drive(level, path)
    if not ok:
        return False, why
    cur = goal

    boss.hp = 4
    level.enemies = [boss]
    for _ in range(400):
        player.attack()
        level.update()
        if level.boss_defeated:
            break
    if not level.boss_defeated:
        return False, f"没能击杀 BOSS（剩余 {int(boss.hp)}）"

    # 2) 钥匙只能由 BOSS 掉落：掉落可能直接落在脚下，需要时才走过去
    if not level.has_key:
        key_item = next((i for i in level.items if i.type == "key" and not i.collected), None)
        if key_item is None:
            return False, "BOSS 没有掉落钥匙"
        kcell = (key_item.rect.centery // TILE_SIZE, key_item.rect.centerx // TILE_SIZE)
        goal = nearest_cell(cells, kcell, 4)
        if goal is None:
            return False, "钥匙周围没有可站立点"
        path = bfs_cells(cells, cur, goal)
        if path is None:
            return False, "走不到钥匙"
        ok, frames, why = drive(level, path)
        if not ok:
            return False, why
        cur = goal
    if not level.has_key:
        return False, "走到钥匙旁边却没捡到"

    # 3) 门必须开着，然后走上去过关
    if not level.door_open:
        return False, "钥匙+BOSS 都齐了但门没开"
    goal = nearest_cell(cells, DOOR_TILE, 1)
    path = bfs_cells(cells, cur, goal)
    if path is None:
        return False, "走不到传送门"
    ok, frames, why = drive(level, path)
    if not ok:
        return False, why
    if not player.rect.colliderect(level.door_rect):
        return False, "没能站到传送门上"
    return True, "BOSS→钥匙→传送门 通过"


if __name__ == "__main__":
    ok_all = True
    for seed in range(2):
        for lvl in (0, 5, 10, 15):
            ok, info = playthrough(lvl, WEAPON_SWORD, seed)
            ok_all &= ok
            print(("PASS " if ok else "FAIL ") + f"seed={seed} 关卡{lvl}: {info}")
    if not ok_all:
        raise SystemExit(1)
    print("\nPLAYTHROUGH OK")
