"""校验：每张地图用玩家真实碰撞盒(32x48)都能从出生点走到宝箱和传送门。"""
import os, sys, random
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from settings import TILE_SIZE, WEAPON_SWORD, WEAPON_BOW
from level import (generate_map, MAP_ROWS, MAP_COLS, START_TILE, CHEST_TILE,
                   DOOR_TILE, _reachable_cells, _tile_touchable, Level)

STEP = 4  # 细网格精度(px)


def _blocked_grid(map_rows):
    W, H = MAP_COLS * TILE_SIZE, MAP_ROWS * TILE_SIZE
    gw, gh = W // STEP, H // STEP
    blocked = [[0] * gw for _ in range(gh)]
    for r, row in enumerate(map_rows):
        for c, ch in enumerate(row):
            if ch == "1":
                for y in range(r * TILE_SIZE // STEP, (r + 1) * TILE_SIZE // STEP):
                    for x in range(c * TILE_SIZE // STEP, (c + 1) * TILE_SIZE // STEP):
                        blocked[y][x] = 1
    return blocked


def fine_reach(map_rows, start_px, target_rect, box=(32, 48)):
    """4px 精度 BFS：玩家矩形能否从 start_px 移动并碰到 target_rect。"""
    blocked = _blocked_grid(map_rows)
    gh, gw = len(blocked), len(blocked[0])
    # 前缀和，O(1) 判断矩形区域是否全空
    pref = [[0] * (gw + 1) for _ in range(gh + 1)]
    for y in range(gh):
        row_sum = 0
        for x in range(gw):
            row_sum += blocked[y][x]
            pref[y + 1][x + 1] = pref[y][x + 1] + row_sum

    bw, bh = box[0] // STEP, box[1] // STEP

    def free(x, y):
        if x < 0 or y < 0 or x + box[0] > gw * STEP or y + box[1] > gh * STEP:
            return False
        x0, y0 = x // STEP, y // STEP
        x1, y1 = x0 + bw, y0 + bh
        total = (pref[y1][x1] - pref[y0][x1] - pref[y1][x0] + pref[y0][x0])
        return total == 0

    sx, sy = start_px
    # 对齐到网格
    sx -= sx % STEP
    sy -= sy % STEP
    start = (sx, sy)
    if not free(sx, sy):
        return False, 0

    seen = {start}
    q = deque([start])
    hit = False
    while q:
        x, y = q.popleft()
        rect = pygame.Rect(x, y, box[0], box[1])
        if rect.colliderect(target_rect):
            hit = True
            break
        for dx, dy in ((STEP, 0), (-STEP, 0), (0, STEP), (0, -STEP)):
            nxt = (x + dx, y + dy)
            if nxt not in seen and free(*nxt):
                seen.add(nxt)
                q.append(nxt)
    return hit, len(seen)


def physics_walk(level, max_frames=6000):
    """用真实的 Player.move()/update() 沿 BFS 路线走到门口，验证手感上没有卡点。"""
    map_rows = level.map_data
    cells = _reachable_cells(map_rows, START_TILE)
    dr, dc = DOOR_TILE
    goals = [c for c in cells if c in ((dr, dc), (dr - 1, dc))]
    if not goals:
        return False, "门口没有可站立格"
    goal = min(goals, key=lambda c: abs(c[0] - START_TILE[0]) + abs(c[1] - START_TILE[1]))

    # 格子级 BFS 求路径
    start = None
    for cand in ((START_TILE[0], START_TILE[1]), (START_TILE[0] + 1, START_TILE[1])):
        if cand in cells:
            start = cand
            break
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        r, c = cur
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if (nr, nc) in cells and (nr, nc) not in prev:
                prev[(nr, nc)] = cur
                q.append((nr, nc))
    if goal not in prev:
        return False, "格子 BFS 走不到门口"

    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    player = level.player
    walls = level.walls
    frames = 0
    for (r, c) in path[1:]:
        tx = c * TILE_SIZE + 4
        ty = r * TILE_SIZE + 16
        stall = 0
        while frames < max_frames:
            frames += 1
            dx = 0 if abs(tx - player.rect.x) <= STEP else (1 if tx > player.rect.x else -1)
            dy = 0 if abs(ty - player.rect.y) <= STEP else (1 if ty > player.rect.y else -1)
            if dx == 0 and dy == 0:
                break
            before = player.rect.topleft
            player.move(dx, dy, walls)
            player.update(walls)
            if player.rect.topleft == before:
                stall += 1
                if stall > 120:      # 卡住 2 秒就算失败
                    return False, f"在格子 {(r, c)} 卡住"
            else:
                stall = 0
            if player.rect.colliderect(level.door_rect):
                return True, frames
    return player.rect.colliderect(level.door_rect), frames


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


random.seed(2024)
for seed in range(6):
    random.seed(seed)
    for lvl in (0, 1, 2):
        m = generate_map(lvl)
        walls = [pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                 for r, row in enumerate(m) for c, ch in enumerate(row) if ch == "1"]

        # 关键点位不能被墙占据
        assert m[START_TILE[0]][START_TILE[1]] == "2"
        assert m[DOOR_TILE[0]][DOOR_TILE[1]] == "5"
        assert m[CHEST_TILE[0]][CHEST_TILE[1]] == "4"

        start_px = (START_TILE[1] * TILE_SIZE, START_TILE[0] * TILE_SIZE)
        chest_rect = pygame.Rect(CHEST_TILE[1] * TILE_SIZE, CHEST_TILE[0] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        door_rect = pygame.Rect(DOOR_TILE[1] * TILE_SIZE, DOOR_TILE[0] * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        ok_chest, n1 = fine_reach(m, start_px, chest_rect)
        ok_door, n2 = fine_reach(m, start_px, door_rect)
        check(f"seed={seed} 关卡{lvl}: 32x48 碰撞盒能走到宝箱", ok_chest, f"可达格{n1}")
        check(f"seed={seed} 关卡{lvl}: 32x48 碰撞盒能走到传送门", ok_door, f"可达格{n2}")

        # 没有“玩家钻不进去的死缝”：每一块空地都必须能被站立的玩家覆盖
        cells = _reachable_cells(m, START_TILE)
        covered = set()
        for rr, cc in cells:
            covered.add((rr, cc))
            covered.add((rr + 1, cc))
        dead = [(r, c) for r in range(MAP_ROWS) for c in range(MAP_COLS)
                if m[r][c] in "02345" and (r, c) not in covered]
        check(f"seed={seed} 关卡{lvl}: 没有玩家钻不进去的死缝", not dead,
              f"{dead[:5]} 共{len(dead)}格")

for seed in range(3):
    random.seed(seed)
    for lvl in (0, 1, 2):
        level = Level(lvl, WEAPON_SWORD)
        walked, info = physics_walk(level)
        check(f"seed={seed} 关卡{lvl}: 用真实移动代码从出生点走到门口", walked, f"{info}")

print("\nALL MAP CHECKS PASSED")
