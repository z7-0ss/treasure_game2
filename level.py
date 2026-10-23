# level.py
import math
import random
from collections import deque

import pygame

import art
import audio
from settings import *
from entities import (Player, Enemy, Boss, Item, Pet, Bolt, Beam, Projectile, FloatText, Shockwave,
                      MeteorStrike, SparkBurst, SlashArc, CastCircle,
                      LightningFX, GroundCracks, ArrowStormFX, BossSkillFX,
                      SpinBlades, FrostShards, Q_WHITE, Q_SILVER, Q_PURPLE, Q_GOLD,
                      Q_RED, Q_RANK)

# ---- 地图尺寸（单位：格）----
MAP_ROWS, MAP_COLS = 30, 60

# 迷宫按“房间”排布：房间内部 2 格宽，房间之间隔 1 格墙。
# 这样所有通道至少 2 格 = 80px 宽；玩家碰撞盒只有 32x48，进得去也转得开。
MAZE_PITCH = 3
MAZE_COLS = 19
MAZE_ROWS = 9

# 关键点位（行, 列）。出生点、钥匙、宝箱、传送门在生成时都会被保护起来。
START_TILE = (7, 7)
KEY_TILE = (13, 28)
CHEST_TILE = (25, 55)
DOOR_TILE = (26, 56)


def _blank_grid(fill):
    return [[fill] * MAP_COLS for _ in range(MAP_ROWS)]


def _carve_room(grid, cx, cy):
    """把第 (cx, cy) 个房间内部挖成 2x2 的空地。"""
    ox, oy = 1 + cx * MAZE_PITCH, 1 + cy * MAZE_PITCH
    for y in range(oy, oy + 2):
        for x in range(ox, ox + 2):
            grid[y][x] = "0"


def _carve_doorway(grid, a, b):
    """打通相邻两个房间之间的墙，门洞宽 2 格。"""
    (ax, ay), (bx, by) = a, b
    if ax == bx:  # 上下相邻
        wall_y = 1 + max(ay, by) * MAZE_PITCH - 1
        for x in range(1 + ax * MAZE_PITCH, 3 + ax * MAZE_PITCH):
            grid[wall_y][x] = "0"
    else:  # 左右相邻
        wall_x = 1 + max(ax, bx) * MAZE_PITCH - 1
        for y in range(1 + ay * MAZE_PITCH, 3 + ay * MAZE_PITCH):
            grid[y][wall_x] = "0"


def _carve_maze(grid):
    """深度优先挖一个完美迷宫（任意房间互通，通道恒为 2 格宽）。"""
    visited = [[False] * MAZE_COLS for _ in range(MAZE_ROWS)]
    _carve_room(grid, 0, 0)
    visited[0][0] = True
    stack = [(0, 0)]
    while stack:
        cx, cy = stack[-1]
        options = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < MAZE_COLS and 0 <= ny < MAZE_ROWS and not visited[ny][nx]:
                options.append((nx, ny))
        if not options:
            stack.pop()
            continue
        nx, ny = random.choice(options)
        _carve_doorway(grid, (cx, cy), (nx, ny))
        _carve_room(grid, nx, ny)
        visited[ny][nx] = True
        stack.append((nx, ny))


def _reserved_tiles(*spots):
    """关键点位及其周围 3x3 区块，避免随机落石把出生点/门堵死。"""
    reserved = set()
    for r, c in spots:
        for rr in range(r - 1, r + 3):   # 含下一行：玩家高 48，要占 2 行
            for cc in range(c - 1, c + 2):
                reserved.add((rr, cc))
    return reserved


def _fits(grid, r, c):
    """玩家碰撞盒 32x48：宽占 1 格，高占 2 格。矮墙走路过不去也算障碍。"""
    blocked = ("1", "6", "7", "9")
    return (0 <= r < MAP_ROWS - 1 and 0 <= c < MAP_COLS
            and grid[r][c] not in blocked and grid[r + 1][c] not in blocked)


def _reachable_cells(grid, start_tile):
    """从出生点出发，玩家（32x48 碰撞盒）实际站得住的格子集合。"""
    r0, c0 = start_tile
    start = None
    for cand in ((r0, c0), (r0 + 1, c0), (r0, c0 + 1), (r0 - 1, c0)):
        if _fits(grid, *cand):
            start = cand
            break
    if start is None:
        return set()

    seen = {start}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if (nr, nc) not in seen and _fits(grid, nr, nc):
                seen.add((nr, nc))
                queue.append((nr, nc))
    return seen


def _tile_touchable(cells, tile):
    """站在某个可站立格时，玩家是否会和该格（宝箱/门）重叠。"""
    r, c = tile
    return any((rr, cc) in cells
               for rr in (r - 1, r)
               for cc in (c - 1, c))


def _carve_path(grid, a, b):
    """兜底：强行挖一条 2 格宽的 L 形通道，保证玩家一定走得通。"""
    (ar, ac), (br, bc) = a, b
    cells = [(ar, ac), (ar + 1, ac), (ar, ac + 1), (ar + 1, ac + 1)]
    step = 1 if bc >= ac else -1
    for cc in range(ac, bc + step, step):
        cells += [(ar, cc), (ar + 1, cc), (ar, cc + 1), (ar + 1, cc + 1)]
    step = 1 if br >= ar else -1
    for rr in range(ar, br + step, step):
        cells += [(rr, bc), (rr + 1, bc), (rr, bc + 1), (rr + 1, bc + 1)]
    for rr, cc in cells:
        if 0 < rr < MAP_ROWS - 1 and 0 < cc < MAP_COLS - 1 and grid[rr][cc] == "1":
            grid[rr][cc] = "0"


def _scatter_special(grid, char, count, reserved, targets):
    """放置矮墙/平台/木箱/尖刺：每次放置都保证关键点位仍连通。"""
    candidates = [(r, c) for r in range(2, MAP_ROWS - 2) for c in range(2, MAP_COLS - 2)
                  if grid[r][c] == "0" and (r, c) not in reserved
                  and (r + 1, c) not in reserved]
    random.shuffle(candidates)
    candidates = candidates[:max(60, count * 8)]
    placed = []
    for r, c in candidates:
        if len(placed) >= count:
            break
        grid[r][c] = char
        cells = _reachable_cells(grid, START_TILE)
        if all(_tile_touchable(cells, t) for t in targets) and _all_floor_reachable(grid):
            placed.append((r, c))
        else:
            grid[r][c] = "0"
    return placed


def _all_floor_reachable(grid):
    """整张地图的空地是否都还能走到（特殊地块不能把地图切碎）。"""
    rows, cols = MAP_ROWS, MAP_COLS
    blocked_chars = ("1", "6", "7", "9")
    stand = [[False] * cols for _ in range(rows)]
    for r in range(rows - 1):
        row0 = grid[r]
        row1 = grid[r + 1]
        srow = stand[r]
        for c in range(cols):
            if row0[c] not in blocked_chars and row1[c] not in blocked_chars:
                srow[c] = True

    start = None
    for r in range(rows - 1):
        for c in range(cols):
            if grid[r][c] == "2":
                start = (r, c)
                break
        if start is not None:
            break
    if start is None or not stand[start[0]][start[1]]:
        return False

    visited = [[False] * cols for _ in range(rows)]
    queue = [start]
    visited[start[0]][start[1]] = True
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < rows - 1 and 0 <= nc < cols and stand[nr][nc] and not visited[nr][nc]:
                visited[nr][nc] = True
                queue.append((nr, nc))

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] in blocked_chars:
                continue
            if visited[r][c] or (r > 0 and visited[r - 1][c]):
                continue
            return False
    return True


def _scatter_low_walls(grid, count, reserved, targets):
    """在空地上撒矮墙（跳得过去，走着过不去）。

    每放一块都检查关键点位是否仍然可达；如果会把路堵死就换一块，
    保证不靠跳跃也能正常通关（跳跃是战术选择，不是必需品）。
    """
    candidates = [(r, c) for r in range(2, MAP_ROWS - 2) for c in range(2, MAP_COLS - 2)
                  if grid[r][c] == "0" and (r, c) not in reserved
                  and (r + 1, c) not in reserved]
    random.shuffle(candidates)
    placed = []
    for r, c in candidates:
        if len(placed) >= count:
            break
        grid[r][c] = "6"
        cells = _reachable_cells(grid, START_TILE)
        if all(_tile_touchable(cells, t) for t in targets) and _all_floor_reachable(grid):
            placed.append((r, c))
        else:
            grid[r][c] = "0"
    return placed


def _scatter_rocks(grid, reserved, count, spacing=3, tries=6000):
    """随机撒石头，但任意两块石头至少隔 spacing 格，保证通道永远 2 格宽。"""
    placed = []
    for _ in range(tries):
        if len(placed) >= count:
            break
        r = random.randint(3, MAP_ROWS - 4)
        c = random.randint(3, MAP_COLS - 4)
        if (r, c) in reserved:
            continue
        if any(abs(r - pr) < spacing and abs(c - pc) < spacing for pr, pc in placed):
            continue
        placed.append((r, c))
        grid[r][c] = "1"
    return placed


def _framed_open_grid():
    grid = _blank_grid("0")
    for r in range(MAP_ROWS):
        grid[r][0] = "1"
        grid[r][MAP_COLS - 1] = "1"
    for c in range(MAP_COLS):
        grid[0][c] = "1"
        grid[MAP_ROWS - 1][c] = "1"
    return grid


def _fill_rect(grid, top, left, height, width, char="1"):
    bottom = min(MAP_ROWS - 1, top + height)
    right = min(MAP_COLS - 1, left + width)
    for r in range(max(1, top), bottom):
        for c in range(max(1, left), right):
            grid[r][c] = char


def _clear_rect(grid, top, left, height, width):
    _fill_rect(grid, top, left, height, width, "0")


def _clear_disk(grid, row, col, radius):
    for r in range(max(1, row - radius), min(MAP_ROWS - 1, row + radius + 1)):
        for c in range(max(1, col - radius), min(MAP_COLS - 1, col + radius + 1)):
            if ((r - row) * (r - row) + (c - col) * (c - col)) <= radius * radius + radius:
                grid[r][c] = "0"


def _carve_hall(grid, a, b, width=2):
    ar, ac = a
    br, bc = b
    if random.random() < 0.5:
        row = ar
        step = 1 if bc >= ac else -1
        for c in range(ac, bc + step, step):
            _clear_rect(grid, row - width // 2, c - width // 2, width + 1, width + 1)
        col = bc
        step = 1 if br >= row else -1
        for r in range(row, br + step, step):
            _clear_rect(grid, r - width // 2, col - width // 2, width + 1, width + 1)
    else:
        col = ac
        step = 1 if br >= ar else -1
        for r in range(ar, br + step, step):
            _clear_rect(grid, r - width // 2, col - width // 2, width + 1, width + 1)
        row = br
        step = 1 if bc >= col else -1
        for c in range(col, bc + step, step):
            _clear_rect(grid, row - width // 2, c - width // 2, width + 1, width + 1)


def _ensure_story_points_clear(grid):
    for spot in (START_TILE, KEY_TILE, CHEST_TILE, DOOR_TILE):
        _clear_rect(grid, spot[0] - 1, spot[1] - 1, 4, 4)


def _generate_forest_layout(sub):
    grid = _blank_grid("1")
    groves = [START_TILE, KEY_TILE, CHEST_TILE, DOOR_TILE]
    extras = [(6, 16), (9, 40), (18, 18), (20, 46), (24, 30)]
    random.shuffle(extras)
    groves.extend(extras)
    for row, col in groves:
        _clear_disk(grid, row, col, 2 + (1 if sub >= 2 and random.random() < 0.45 else 0))
    for a, b in zip(groves, groves[1:]):
        _carve_hall(grid, a, b, width=2 + (1 if sub >= 1 else 0))
    for _ in range(3 + sub):
        a, b = random.sample(groves, 2)
        _carve_hall(grid, a, b, width=2)
    for _ in range(8 + sub * 3):
        _clear_disk(grid, random.randint(4, MAP_ROWS - 5), random.randint(4, MAP_COLS - 5), 1)
    _ensure_story_points_clear(grid)
    return grid


def _generate_ocean_layout(sub):
    grid = _framed_open_grid()
    lane_rows = [5, 13, 21]
    for row in lane_rows:
        _clear_rect(grid, row, 1, 4, MAP_COLS - 2)
    reserved = _reserved_tiles(START_TILE, KEY_TILE, CHEST_TILE, DOOR_TILE)
    for _ in range(11 + sub * 2):
        h = random.randint(3, 6)
        w = random.randint(4, 9)
        r = random.randint(2, MAP_ROWS - h - 2)
        c = random.randint(3, MAP_COLS - w - 3)
        if any((rr, cc) in reserved for rr in range(r - 1, r + h + 1) for cc in range(c - 1, c + w + 1)):
            continue
        _fill_rect(grid, r, c, h, w)
        if h >= 5 and w >= 6 and random.random() < 0.55:
            _clear_rect(grid, r + 1, c + 1, h - 2, w - 2)
    for col in range(8, MAP_COLS - 8, 12):
        gap = random.choice(lane_rows) + random.randint(-1, 1)
        for r in range(2, MAP_ROWS - 2):
            if abs(r - gap) <= 2:
                continue
            if random.random() < 0.85:
                grid[r][col] = "1"
    _ensure_story_points_clear(grid)
    return grid


def _generate_sky_layout(sub):
    grid = _framed_open_grid()
    column_step = 8
    for i, col in enumerate(range(8, MAP_COLS - 6, column_step)):
        gap = 4 + ((i * 5 + sub * 3) % 16)
        thickness = 2 if i % 2 == 0 else 1
        for r in range(2, MAP_ROWS - 2):
            if gap <= r <= gap + 4:
                continue
            for off in range(thickness):
                if col + off < MAP_COLS - 1:
                    grid[r][col + off] = "1"
    for row in (7, 15, 23):
        for c in range(5, MAP_COLS - 5):
            if (c // 6 + row + sub) % 3 == 0:
                _clear_rect(grid, row, c, 2, 3)
    _ensure_story_points_clear(grid)
    return grid


def _generate_volcano_layout(sub):
    grid = _framed_open_grid()
    _fill_rect(grid, 7, 18, 16, 24)
    _clear_rect(grid, 10, 21, 10, 18)
    _clear_rect(grid, 13, 18, 4, 3)
    _clear_rect(grid, 13, 39, 4, 3)
    _clear_rect(grid, 7, 28, 3, 4)
    _clear_rect(grid, 20, 28, 3, 4)
    for col in range(8, MAP_COLS - 8, 10):
        if 18 <= col <= 40:
            continue
        gap = random.choice((5, 13, 22))
        for r in range(2, MAP_ROWS - 2):
            if abs(r - gap) <= 1:
                continue
            grid[r][col] = "1"
            if sub >= 2 and col + 1 < MAP_COLS - 1 and random.random() < 0.65:
                grid[r][col + 1] = "1"
    for row in (6, 23):
        for c in range(6, MAP_COLS - 6, 7):
            _fill_rect(grid, row, c, 2, 2)
    _ensure_story_points_clear(grid)
    return grid


# 生成一个 60列 x 30行 的超大地图（960x540 屏幕需要滚动）
def generate_map(level_idx):
    theme = level_theme(level_idx)
    chapter = chapter_of(level_idx)
    sub = level_idx % LEVELS_PER_CHAPTER
    if theme == "forest" and sub == 0:
        grid = _blank_grid("1")
        _carve_maze(grid)
        _ensure_story_points_clear(grid)
    elif theme == "forest":
        grid = _generate_forest_layout(sub)
    elif theme == "ocean":
        grid = _generate_ocean_layout(sub)
    elif theme == "sky":
        grid = _generate_sky_layout(sub)
    else:
        grid = _generate_volcano_layout(sub)

    for (r, c), char in ((START_TILE, "2"), (KEY_TILE, "3"),
                         (CHEST_TILE, "4"), (DOOR_TILE, "5")):
        grid[r][c] = char

    # 矮墙：跳起来可以越过，走路过不去
    reserved = _reserved_tiles(START_TILE, KEY_TILE, CHEST_TILE, DOOR_TILE)
    targets = (KEY_TILE, CHEST_TILE, DOOR_TILE)
    low_count = {
        "forest": [12, 16, 20, 24],
        "ocean": [10, 12, 14, 16],
        "sky": [6, 8, 10, 12],
        "volcano": [14, 18, 22, 26],
    }[theme][sub]
    _scatter_special(grid, LOW_WALL_CHAR, low_count, reserved, targets)
    platform_count = {
        "forest": [10, 12, 14, 16],
        "ocean": [16, 18, 20, 22],
        "sky": [24, 28, 32, 36],
        "volcano": [10, 12, 14, 16],
    }[theme][sub]
    _scatter_special(grid, PLATFORM_CHAR, platform_count, reserved, targets)
    crate_count = {
        "forest": [6, 8, 10, 12],
        "ocean": [4, 6, 8, 10],
        "sky": [3, 4, 5, 6],
        "volcano": [5, 7, 9, 11],
    }[theme][sub] + chapter
    _scatter_special(grid, CRATE_CHAR, crate_count, reserved, targets)
    hazard = {
        "forest": [4, 6, 8, 10],
        "ocean": [8, 10, 12, 14],
        "sky": [5, 6, 7, 8],
        "volcano": [14, 18, 22, 26],
    }[theme][sub]
    _scatter_special(grid, SPIKE_CHAR, hazard, reserved, targets)

    # 保底校验：玩家必须真的能从出生点走到宝箱和传送门，否则强行开路
    cells = _reachable_cells(grid, START_TILE)
    if not all(_tile_touchable(cells, t) for t in (KEY_TILE, CHEST_TILE, DOOR_TILE)):
        _carve_path(grid, START_TILE, CHEST_TILE)
        _carve_path(grid, START_TILE, DOOR_TILE)
        cells = _reachable_cells(grid, START_TILE)

    # 还是不通，说明矮墙挡路：逐块移除直到连通
    while not all(_tile_touchable(cells, t) for t in (KEY_TILE, CHEST_TILE, DOOR_TILE)):
        lows = [(r, c) for r in range(MAP_ROWS) for c in range(MAP_COLS) if grid[r][c] == "6"]
        if not lows:
            break
        r, c = lows[len(lows) // 2]
        grid[r][c] = "0"
        cells = _reachable_cells(grid, START_TILE)

    return ["".join(row) for row in grid]


class Weather:
    """轻量天气：0 萤火 / 1 花瓣 / 2 雨 / 3 雪。"""

    KIND = {"forest": "petals", "ocean": "bubbles", "sky": "feathers", "volcano": "embers"}
    COUNT = {"petals": 46, "bubbles": 54, "feathers": 44, "embers": 60,
             "motes": 34, "rain": 80, "snow": 62}

    def __init__(self, level_index):
        self.kind = self.KIND.get(level_theme(level_index), "petals")
        self.particles = [[random.uniform(-20, WIDTH + 20),
                           random.uniform(-HEIGHT, HEIGHT),
                           random.uniform(0.5, 1.6),
                           random.uniform(0, math.tau)]
                          for _ in range(self.COUNT[self.kind])]

    def update(self):
        for p in self.particles:
            x, y, sp, ph = p
            if self.kind == "bubbles":
                p[1] -= 1.2 * sp
                p[0] += math.sin(ph + y * 0.03) * 0.6
            elif self.kind == "feathers":
                p[1] += 0.7 * sp
                p[0] += math.sin(ph + y * 0.02) * 1.2 + 0.5
            elif self.kind == "embers":
                p[1] -= 1.5 * sp
                p[0] += math.sin(ph + y * 0.04) * 0.9
            elif self.kind == "rain":
                p[0] -= 1.8 * sp
                p[1] += 9.5 * sp + 2
            elif self.kind == "snow":
                p[1] += 1.15 * sp
                p[0] += math.sin(ph + y * 0.02) * 0.8
            elif self.kind == "petals":
                p[1] += 0.85 * sp
                p[0] += math.sin(ph + y * 0.03) * 1.5 + 0.35
            else:
                p[1] -= 0.45 * sp
                p[0] += math.cos(ph + y * 0.02) * 0.6
            if p[1] > HEIGHT + 24:
                p[1], p[0] = -24, random.uniform(-20, WIDTH + 20)
            elif p[1] < -24:
                p[1], p[0] = HEIGHT + 24, random.uniform(-20, WIDTH + 20)
            if p[0] < -30:
                p[0] = WIDTH + 24
            elif p[0] > WIDTH + 30:
                p[0] = -24

    def draw(self, screen):
        if self.kind == "bubbles":
            for x, y, sp, _ in self.particles:
                pygame.draw.circle(screen, (170, 230, 255), (int(x), int(y)), max(1, int(sp + 1)), 1)
        elif self.kind == "feathers":
            for x, y, sp, _ in self.particles:
                pygame.draw.ellipse(screen, (250, 250, 255), (int(x), int(y), 5, 2))
        elif self.kind == "embers":
            for x, y, sp, _ in self.particles:
                art.blit_glow(screen, int(x), int(y), 8, (255, 140, 60), 60)
        elif self.kind == "rain":
            for x, y, sp, _ in self.particles:
                pygame.draw.line(screen, (150, 192, 236), (x, y), (x - 2 * sp, y + 11 * sp), 1)
        elif self.kind == "snow":
            for x, y, sp, _ in self.particles:
                pygame.draw.circle(screen, (240, 248, 255), (int(x), int(y)), max(1, int(sp + 0.5)))
        elif self.kind == "petals":
            for x, y, sp, ph in self.particles:
                pygame.draw.ellipse(screen, (255, 188, 212), (int(x), int(y), 6, 3))
        else:
            for x, y, sp, ph in self.particles:
                art.blit_glow(screen, int(x), int(y), 10, (255, 238, 150), 34)


class Level:
    # 每关的怪物池：越往后越多样、越危险
    MONSTER_POOL = {
        0: ["slime", "mushroom", "butterfly"],
        1: ["slime", "butterfly", "bat", "mushroom"],
        2: ["mushroom", "skeleton", "bat", "tree", "butterfly"],
        3: ["skeleton", "bat", "tree", "mushroom"],
    }
    CHAPTER_POOL = {
        "forest": ["slime", "mushroom", "butterfly", "bat"],
        "ocean": ["mushroom", "butterfly", "bat", "skeleton", "tree"],
        "sky": ["butterfly", "bat", "skeleton", "slime", "tree"],
        "volcano": ["slime", "skeleton", "tree", "mushroom", "bat"],
    }
    ELITE_CHANCE = {0: 0.06, 1: 0.14, 2: 0.22, 3: 0.3}

    def __init__(self, level_index, weapon_type, existing_player=None):
        self.level_index = level_index
        self.set_key = level_theme(level_index)
        self.theme = self.set_key
        self.map_data = generate_map(level_index)
        self.weapon_type = weapon_type

        self.walls = []
        self.low_walls = []
        self.platform_rects = []
        self.spike_rects = []
        self.crates = []
        self.crate_rects = []
        self.spike_damage_cd = 0
        self.enemies = []
        self.items = []
        self.door_rect = None
        self.empty_tiles = []

        self.effects = []
        self.float_texts = []
        self.shake = 0

        # 过关条件：拿到钥匙 + 击杀本关 BOSS
        self.has_key = False
        self.boss_defeated = False
        self.boss = None
        self.door_open = False

        self.enemy_shots = []
        self.spawn_timer = 0
        self.spawn_base_interval = 9 * 60
        self.spawn_interval = self.spawn_base_interval

        start_pos = (TILE_SIZE * 3, TILE_SIZE * 3)

        for r, row in enumerate(self.map_data):
            for c, char in enumerate(row):
                x, y = c * TILE_SIZE, r * TILE_SIZE
                if char == "1":
                    self.walls.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                elif char == "6":
                    self.low_walls.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                elif char == "7":
                    self.platform_rects.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                elif char == "8":
                    self.spike_rects.append(pygame.Rect(x, y, TILE_SIZE, TILE_SIZE))
                elif char == "9":
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    self.crates.append({"rect": rect, "hp": CRATE_HP, "max_hp": CRATE_HP})
                    self.crate_rects.append(rect)
                elif char == "2":
                    start_pos = (x, y)
                elif char == "3":
                    pass          # 钥匙改为只由 BOSS 掉落
                elif char == "4":
                    self.items.append(Item(x, y, "chest"))
                elif char == "5":
                    self.door_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                elif char == "0":
                    self.empty_tiles.append((x, y))

        if existing_player:
            self.player = existing_player
            self.player.rect.x = start_pos[0]
            self.player.rect.y = start_pos[1]
            self.player.hp = self.player.max_hp
            self.player.invincible_timer = 120
            self.player.projectiles.clear()
            self.player.z = 0
            self.player.vz = 0
        else:
            self.player = Player(start_pos[0], start_pos[1], self.weapon_type)

        # 先选好 BOSS 位置并挖出竞技场（要在渲染地图之前完成）
        self.boss_center = self._pick_boss_spot(start_pos)
        self._carve_arena(self.boss_center)
        self.bosses = []
        count = boss_count(self.level_index)
        plan = chapter_boss_plan(self.level_index)
        if count <= 1:
            bt, nm, tier = plan[0]
            b = Boss(self.boss_center[0] - 44, self.boss_center[1] - 38,
                     level_idx=self.level_index, boss_type=bt)
            b.name = nm
            b.variant = tier
            self._apply_boss_variant(b, tier)
            self.bosses.append(b)
        else:
            ring = 60 if count <= 2 else (96 if count <= 4 else 128)
            for i in range(count):
                bt, nm, tier = plan[i]
                ang = math.tau * i / count - math.pi / 2
                cx = self.boss_center[0] + math.cos(ang) * ring
                cy = self.boss_center[1] + math.sin(ang) * ring
                b = Boss(cx - 44, cy - 38, level_idx=self.level_index, boss_type=bt)
                b.name = nm
                b.variant = tier
                b.hp = int(b.max_hp * (0.78 if count >= 3 else 0.9))
                b.max_hp = b.hp
                self._apply_boss_variant(b, tier)
                self.bosses.append(b)

        # 最后一关：45 级最终大魔王
        if self.level_index == FINAL_LEVEL_INDEX:
            fb = Boss(self.boss_center[0] - 55, self.boss_center[1] + 60,
                      level_idx=self.level_index, boss_type="skeleton")
            fb.name = f"深渊魔王 Lv.{FINAL_BOSS_LEVEL}"
            fb.rect = pygame.Rect(fb.rect.x, fb.rect.y, 116, 100)
            fb.hp = fb.max_hp = 26000
            fb.attack_damage = 72
            fb.speed = 2.3
            fb.is_final = True
            self.bosses.append(fb)

        self.boss = self.bosses[0]

        # 整张地图一次性渲染并缓存，之后每帧只 blit 可见区域
        size = (len(self.map_data[0]) * TILE_SIZE, len(self.map_data) * TILE_SIZE)
        self.map_surface = art.paint_map(pygame.Surface(size), self.map_data, level_index)

        for _ in range(6 + chapter_of(level_index) * 2):
            self.spawn_enemy()

        # BOSS 出生在专门挖出来的竞技场里（体力型 BOSS 需要空间，也不会卡墙）
        for b in self.bosses:
            self.enemies.append(b)

        # 跟宠：按职业分工
        self.pet = Pet(self.player)

        # 小地图 / 雷达
        self.minimap = pygame.transform.smoothscale(self.map_surface, (MAP_COLS * 4, MAP_ROWS * 4))
        self.radar_surface = pygame.transform.smoothscale(self.minimap, (200, 100))
        self.weather = Weather(self.level_index)

    # ---------------- BOSS 竞技场 ----------------
    def _apply_boss_variant(self, boss, tier):
        """变体 BOSS：更强、配色不同。"""
        if not tier:
            return
        mult = 1 + tier * 0.22
        boss.max_hp = int(boss.max_hp * mult)
        boss.hp = boss.max_hp
        boss.attack_damage *= 1 + tier * 0.15

    def _arena_radius(self):
        n = boss_count(self.level_index)
        if self.level_index == FINAL_LEVEL_INDEX:
            n += 1
        return 2 if n <= 2 else (3 if n <= 4 else 4)

    def _pick_boss_spot(self, start_pos):
        """在离出生点较远、又不压住关键点位的地方选一个 BOSS 场地中心。"""
        safe = [(KEY_TILE[1] * TILE_SIZE, KEY_TILE[0] * TILE_SIZE),
                (CHEST_TILE[1] * TILE_SIZE, CHEST_TILE[0] * TILE_SIZE),
                (DOOR_TILE[1] * TILE_SIZE, DOOR_TILE[0] * TILE_SIZE)]

        def ok(tile):
            return all(abs(tile[0] - s[0]) + abs(tile[1] - s[1]) > 6 * TILE_SIZE for s in safe)

        # 离地图边缘至少 3 格，保证 5x5 竞技场能完整挖出来
        margin = self._arena_radius() + 1
        interior = [t for t in self.empty_tiles
                    if margin <= t[0] // TILE_SIZE <= MAP_COLS - 1 - margin
                    and margin <= t[1] // TILE_SIZE <= MAP_ROWS - 1 - margin]
        candidates = [t for t in interior if ok(t)]
        far = [t for t in candidates
               if abs(t[0] - start_pos[0]) + abs(t[1] - start_pos[1]) > 700]
        pool = far or candidates or self.empty_tiles
        spot = random.choice(pool)
        return (spot[0] + TILE_SIZE // 2, spot[1] + TILE_SIZE // 2)

    def _carve_arena(self, center):
        """以 center 为中心挖出 5x5 的空地，作为 BOSS 战场。"""
        cr, cc = center[1] // TILE_SIZE, center[0] // TILE_SIZE
        radius = self._arena_radius()
        r0, r1 = max(1, cr - radius), min(MAP_ROWS - 2, cr + radius)
        c0, c1 = max(1, cc - radius), min(MAP_COLS - 2, cc + radius)
        for r in range(r0, r1 + 1):
            row = self.map_data[r]
            self.map_data[r] = row[:c0] + "0" * (c1 - c0 + 1) + row[c1 + 1:]

        self.walls = [w for w in self.walls
                      if not (r0 <= w.y // TILE_SIZE <= r1 and c0 <= w.x // TILE_SIZE <= c1)]
        self.low_walls = [w for w in self.low_walls
                          if not (r0 <= w.y // TILE_SIZE <= r1 and c0 <= w.x // TILE_SIZE <= c1)]
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (c * TILE_SIZE, r * TILE_SIZE) not in self.empty_tiles:
                    self.empty_tiles.append((c * TILE_SIZE, r * TILE_SIZE))
    # ---------------- 掉落 ----------------
    # 品质顺序：白 / 绿 / 紫 / 金 / 红
    LOOT_WEIGHTS = {
        0: [78, 20, 2, 0, 0],          # 第 1 关：最多紫，且只有 2%
        1: [40, 38, 20, 2, 0],         # 第 2 关：金装刚出现
        2: [12, 30, 40, 16, 2],        # 第 3 关
        3: [4, 20, 40, 28, 8],         # 第 4 关：红装才有机会
    }
    BOSS_WEIGHTS = {
        0: [45, 45, 10, 0, 0],         # 第 1 关 BOSS 也不会掉金/红
        1: [10, 40, 42, 8, 0],
        2: [0, 14, 44, 34, 8],
        3: [0, 4, 26, 44, 26],
    }

    def get_drop_quality(self, is_boss=False):
        table = self.BOSS_WEIGHTS if is_boss else self.LOOT_WEIGHTS
        chapter = chapter_of(self.level_index)
        weights = table.get(chapter, table[3])
        qualities = [Q_WHITE, Q_SILVER, Q_PURPLE, Q_GOLD, Q_RED]
        return random.choices(qualities, weights=weights, k=1)[0]

    def handle_drops(self, enemy, drop_key=True):
        if enemy.is_boss:
            cx, cy = enemy.rect.centerx, enemy.rect.centery
            # BOSS 只随机掉 3 件装备，不再铺满一地
            kinds = random.sample(["weapon", "armor", "helmet", "boots", "pants", "bracelet"],
                                  BOSS_DROP_COUNT)
            for i, kind in enumerate(kinds):
                q = self.get_drop_quality(is_boss=True)
                hidden = None
                if q == Q_RED and random.random() < MYTHIC_HIDDEN_CHANCE:
                    hidden = random.choice(list(HIDDEN_EFFECTS))
                ang = math.tau * i / BOSS_DROP_COUNT - math.pi / 2
                px = cx + math.cos(ang) * 52 - 14
                py = cy + math.sin(ang) * 40 - 6
                self.spawn_item(px, py, kind, quality=q,
                                weapon_type=self.weapon_type if kind == "weapon" else None,
                                label_dy=i * 4, set_key=self.set_key, hidden=hidden)
            if drop_key:
                self.spawn_item(cx - 5, cy + 55, "key", label_dy=0)
            self.spawn_item(cx + 40, cy + 40, "potion_hp", label_dy=8)
            return

        drop_chance = GEAR_DROP_ELITE if enemy.is_elite else GEAR_DROP_NORMAL
        if random.random() < drop_chance:
            q = self.get_drop_quality()
            if enemy.is_elite and q == Q_WHITE:
                q = Q_SILVER
            drop_type = random.choice(["weapon", "armor", "helmet", "boots", "pants", "bracelet"])
            hidden = None
            if q == Q_RED and random.random() < MYTHIC_HIDDEN_CHANCE:
                hidden = random.choice(list(HIDDEN_EFFECTS))
            self.spawn_item(
                enemy.rect.x, enemy.rect.y, drop_type, quality=q,
                weapon_type=self.weapon_type if drop_type == "weapon" else None,
                set_key=self.set_key, hidden=hidden)

        if random.random() < (0.5 if enemy.is_elite else POTION_DROP_NORMAL):
            pool = ["potion_hp", "potion_hp", "potion_energy", "potion_energy",
                    "potion_speed", "bomb"]
            self.spawn_item(enemy.rect.x + 22, enemy.rect.y, random.choice(pool))

        # 钥匙只由 BOSS 掉落

    # ---------------- 战斗 ----------------
    def _hit_feedback(self, enemy, damage, crit=False, magic=False):
        """命中火花 / 音效 / 震屏。"""
        if crit:
            color = (255, 232, 130)
            self.effects.append(SparkBurst(enemy.rect.centerx, enemy.rect.centery,
                                           color, 14, 4.6, 22, 4))
            self.float_texts.append(FloatText(
                enemy.rect.centerx, enemy.rect.top - 16, f"暴击 {int(damage)}",
                (255, 220, 120), 19, 46))
            self.shake = max(self.shake, 6)
            audio.play("crit", 0.75)
        else:
            color = (190, 160, 255) if magic else (255, 206, 140)
            self.effects.append(SparkBurst(enemy.rect.centerx, enemy.rect.centery,
                                           color, 7, 2.9, 15, 3))
            self.shake = max(self.shake, 2)
            audio.play("hit_magic" if magic else "hit_phys", 0.65)
        enemy.hit_timer = max(getattr(enemy, "hit_timer", 0), 6 if crit else 4)
        if self.player.has_hidden("lifesteal"):
            heal = max(1, int(damage * 0.08))
            if self.player.heal(heal) > 0:
                self.float_texts.append(FloatText(
                    self.player.rect.centerx, self.player.rect.top - 18,
                    f"+{heal}", (150, 255, 170), 13, 30))

    def pop_damage(self, enemy, damage, color=None):
        self.float_texts.append(FloatText(
            enemy.rect.centerx, enemy.rect.top - 4, str(int(damage)),
            color or (255, 236, 140), 16, 40))

    def pop_player_damage(self, amount, dmg_type=DMG_PHYS):
        if self.theme == "volcano" and self.player.hp > 0 and random.random() < 0.42:
            resist = self.player.status_resist("volcano")
            self.player.burn_timer = max(self.player.burn_timer,
                                         max(24, int(140 * (1 - resist))))
        color = (255, 110, 110) if dmg_type == DMG_PHYS else (185, 150, 255)
        self.float_texts.append(FloatText(
            self.player.rect.centerx, self.player.rect.top - 6,
            f"-{int(amount)}", color, 17, 46))

    def use_item(self, kind):
        """从背包使用道具（道具栏按钮 / 数字键）。"""
        player = self.player
        if player.bag.get(kind, 0) <= 0:
            return False

        if kind == "bomb":
            player.bag[kind] -= 1
            ghost = Item(player.rect.centerx - 14, player.rect.centery - 14, "bomb")
            self.explode(ghost)
            return True

        if kind == "potion_hp":
            if player.hp >= player.max_hp:
                return False
            player.bag[kind] -= 1
            healed = player.heal(POTION_HEAL)
            self.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 8,
                                              f"+{healed} 生命", (130, 255, 170), 16, 60))
            return True

        if kind == "potion_energy":
            if player.energy >= MAX_ENERGY:
                return False
            player.bag[kind] -= 1
            player.energy = min(MAX_ENERGY, player.energy + POTION_ENERGY)
            self.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 8,
                                              f"+{POTION_ENERGY} 能量", (150, 200, 255), 16, 60))
            return True

        if kind == "potion_speed":
            player.bag[kind] -= 1
            player.speed_bonus_timer = SPEED_POTION_FRAMES
            audio.play("pickup")
            self.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 8,
                                              "疾风！移速 +65%", (255, 226, 120), 17, 70))
            return True

        return False

    def spawn_enemy_bolt(self, x, y, vx, vy, damage, dmg_type, kind):
        self.enemy_shots.append(Bolt(x, y, vx, vy, damage, dmg_type, True, kind))

    def _refresh_door(self):
        was_open = getattr(self, "door_open", False)
        self.door_open = self.has_key and self.boss_defeated
        if self.door_open and not was_open:
            audio.play("door", 0.9)
            self.float_texts.append(FloatText(
                self.door_rect.centerx, self.door_rect.top - 20,
                "传送门开启了！", (150, 255, 200), 17, 80))

    # ---------------- 矮墙 / 炸弹 ----------------
    @property
    def solid(self):
        return self.walls + self.low_walls + self.platform_rects + self.crate_rects

    def _drop_blockers(self):
        blockers = self.solid[:]
        if self.door_rect:
            blockers.append(self.door_rect)
        return blockers

    def _settle_item(self, item):
        blockers = self._drop_blockers()
        if not any(item.rect.colliderect(w) for w in blockers):
            return item
        origin = item.rect.copy()
        best = None
        best_cost = None
        for radius in range(0, 7):
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    cand = origin.move(ox * 10, oy * 10)
                    if cand.left < 4 or cand.top < 4:
                        continue
                    if cand.right > MAP_COLS * TILE_SIZE - 4 or cand.bottom > MAP_ROWS * TILE_SIZE - 4:
                        continue
                    if any(cand.colliderect(w) for w in blockers):
                        continue
                    cost = abs(ox) + abs(oy)
                    if best is None or cost < best_cost:
                        best = cand
                        best_cost = cost
            if best is not None:
                break
        if best is not None:
            item.rect.topleft = best.topleft
        item.update_physics(blockers)
        return item

    def spawn_item(self, x, y, type_name, quality="none", weapon_type=None, label_dy=0,
                   set_key=None, hidden=None):
        item = Item(x, y, type_name, quality=quality, weapon_type=weapon_type,
                    label_dy=label_dy, set_key=set_key or self.set_key, hidden=hidden)
        self._settle_item(item)
        self.items.append(item)
        return item

    def _live_bosses(self):
        return [b for b in getattr(self, "bosses", []) if b in self.enemies]

    def _spawn_cap(self):
        return [6, 8, 10, 12][chapter_of(self.level_index)]

    def _nearby_spawn_cap(self):
        return [4, 5, 6, 7][chapter_of(self.level_index)]

    def _living_mobs(self):
        return [e for e in self.enemies if not e.is_boss]

    def _nearby_mob_count(self, radius=560):
        px, py = self.player.rect.center
        return sum(1 for e in self._living_mobs()
                   if math.hypot(e.rect.centerx - px, e.rect.centery - py) <= radius)

    def _can_spawn_enemy(self):
        if self.boss_defeated:
            return False
        live_mobs = self._living_mobs()
        if len(live_mobs) >= self._spawn_cap():
            return False
        if self._nearby_mob_count() >= self._nearby_spawn_cap():
            return False
        live_bosses = self._live_bosses()
        if live_bosses:
            nearest_boss = min(math.hypot(b.rect.centerx - self.player.rect.centerx,
                                          b.rect.centery - self.player.rect.centery)
                               for b in live_bosses)
            if nearest_boss < 760:
                return False
        return True

    def _update_spawn_interval(self):
        cap = max(1, self._spawn_cap())
        pressure = len(self._living_mobs()) / cap
        self.spawn_interval = int(self.spawn_base_interval * (1.0 + pressure * 0.7))

    def collision_walls(self):
        """跳跃高度足够时，矮墙/平台不再挡路。"""
        blocked = self.walls + self.crate_rects
        if self.player.z < LOW_WALL_Z:
            blocked = blocked + self.low_walls
        if self.player.z < PLATFORM_H - 4:
            blocked = blocked + self.platform_rects
        return blocked

    def _landing_fix(self):
        """落地时如果正好卡在矮墙里，把角色推到最近的一侧。"""
        if self.player.z >= LOW_WALL_Z:
            return
        pr = self.player.rect
        for lw in self.low_walls:
            if not pr.colliderect(lw):
                continue
            ox = min(pr.right - lw.left, lw.right - pr.left)
            oy = min(pr.bottom - lw.top, lw.bottom - pr.top)
            if ox < oy:
                if pr.centerx < lw.centerx:
                    pr.right = lw.left
                else:
                    pr.left = lw.right
            else:
                if pr.centery < lw.centery:
                    pr.bottom = lw.top
                else:
                    pr.top = lw.bottom

    def _explode_at(self, x, y, radius, damage):
        """爆裂箭的爆炸伤害。"""
        self.effects.append(Shockwave(x, y, radius, (255, 170, 90), 22, 6, 0.25))
        self.effects.append(Shockwave(x, y, radius * 0.6, (255, 232, 160), 14, 4, 0.35))
        self.shake = max(self.shake, 7)
        audio.play("boom", 0.6)
        for enemy in self.enemies[:]:
            if math.hypot(enemy.rect.centerx - x, enemy.rect.centery - y) <= radius + enemy.rect.width * 0.4:
                splash = max(1, int(damage * 0.6))
                enemy.take_hit(splash, enemy.rect.centerx >= x)
                self.pop_damage(enemy, splash, (255, 200, 140))
                if enemy.dead:
                    self.kill_enemy(enemy)

    def _hit_crate(self, crate, damage):
        crate["hp"] -= damage
        rect = crate["rect"]
        self.effects.append(Shockwave(rect.centerx, rect.centery, 22, (226, 176, 96), 12, 3, 0.4))
        if crate["hp"] <= 0:
            self._break_crate(crate)

    def _break_crate(self, crate):
        rect = crate["rect"]
        if crate in self.crates:
            self.crates.remove(crate)
        if rect in self.crate_rects:
            self.crate_rects.remove(rect)
        self._clear_tile(rect.x, rect.y)
        kind = random.choice(["potion_hp", "potion_energy", "potion_speed", "bomb"])
        self.spawn_item(rect.centerx - 14, rect.centery - 14, kind)
        self.effects.append(Shockwave(rect.centerx, rect.centery, 64, (255, 206, 130), 20, 6, 0.3))
        self.shake = max(self.shake, 4)
        audio.play("boom", 0.55)
        self.float_texts.append(FloatText(rect.centerx, rect.top, "木箱碎了！", (255, 214, 150), 14, 50))

    def _clear_tile(self, x, y):
        c, r = x // TILE_SIZE, y // TILE_SIZE
        if 0 <= r < len(self.map_data) and 0 <= c < len(self.map_data[0]):
            self.map_data[r] = self.map_data[r][:c] + "0" + self.map_data[r][c + 1:]
            art.paint_floor(self.map_surface, x, y, r, c, self.level_index)
            if (x, y) not in self.empty_tiles:
                self.empty_tiles.append((x, y))

    def explode(self, item):
        cx, cy = item.rect.center
        destroyed = 0
        for wall in self.walls[:]:
            c, r = wall.x // TILE_SIZE, wall.y // TILE_SIZE
            if r in (0, MAP_ROWS - 1) or c in (0, MAP_COLS - 1):
                continue                       # 地图最外层围墙炸不开
            if math.hypot(wall.centerx - cx, wall.centery - cy) <= BOMB_RADIUS:
                self.walls.remove(wall)
                self._clear_tile(wall.x, wall.y)
                destroyed += 1
        for lw in self.low_walls[:]:
            if math.hypot(lw.centerx - cx, lw.centery - cy) <= BOMB_RADIUS:
                self.low_walls.remove(lw)
                self._clear_tile(lw.x, lw.y)
                destroyed += 1
        self.effects.append(Shockwave(cx, cy, BOMB_RADIUS + 26, (255, 176, 90), 26, 12, 0.15))
        self.effects.append(Shockwave(cx, cy, BOMB_RADIUS * 0.6, (255, 232, 160), 16, 8, 0.3))
        self.shake = 14
        audio.play("boom")
        self.float_texts.append(FloatText(cx, cy - 18, f"炸开 {destroyed} 块墙",
                                          (255, 200, 120), 15, 64))

    # ---------------- 雷达 / 地图 ----------------
    def _map_point(self, rect, wx, wy):
        return (rect.x + wx / (MAP_COLS * TILE_SIZE) * rect.w,
                rect.y + wy / (MAP_ROWS * TILE_SIZE) * rect.h)

    def _radar_marks(self, screen, rect, dot=2):
        def put(pos, color, r):
            x, y = self._map_point(rect, pos[0], pos[1])
            pygame.draw.circle(screen, (8, 8, 12), (int(x), int(y)), r + 1)
            pygame.draw.circle(screen, color, (int(x), int(y)), r)

        for e in self.enemies:
            if e.is_summon:
                put(e.rect.center, (198, 142, 255), dot)
            elif not e.is_boss:
                put(e.rect.center, (255, 122, 122), dot)
        for b in getattr(self, "bosses", []):
            if b in self.enemies:
                put(b.rect.center, (255, 110, 182), dot + 1)
        if not self.has_key:
            key_item = next((i for i in self.items if i.type == "key" and not i.collected), None)
            if key_item is not None:
                put(key_item.rect.center, (255, 214, 80), dot)
        if self.door_rect:
            put(self.door_rect.center, (110, 255, 160) if self.door_open else (228, 96, 96), dot)
        put(self.player.rect.center, (255, 255, 255), dot + 1)

    def draw_radar(self, screen, rect):
        pygame.draw.rect(screen, (12, 10, 18), rect.inflate(10, 10), border_radius=8)
        pygame.draw.rect(screen, (150, 160, 190), rect.inflate(10, 10), 1, border_radius=8)
        screen.blit(self.radar_surface, rect.topleft)
        self._radar_marks(screen, rect, dot=2)

    def draw_map_overlay(self, screen):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 6, 12, 200))
        screen.blit(shade, (0, 0))

        panel = pygame.Rect(WIDTH // 2 - 300, 66, 600, 392)
        pygame.draw.rect(screen, (20, 17, 28), panel, border_radius=14)
        pygame.draw.rect(screen, (255, 160, 210), panel, 2, border_radius=14)
        title = art.label("地图", (255, 206, 232), 22, True)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 10))
        hint = art.label("按 M 关闭", (190, 190, 205), 13)
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 36))

        map_rect = pygame.Rect(panel.x + 20, panel.y + 58, 560, 280)
        big = pygame.transform.scale(self.radar_surface, map_rect.size)
        screen.blit(big, map_rect)
        pygame.draw.rect(screen, (100, 100, 130), map_rect, 1)
        self._radar_marks(screen, map_rect, dot=3)

        legend = [("你", (255, 255, 255)), ("BOSS", (255, 110, 182)),
                  ("怪物", (255, 122, 122)), ("召唤物", (198, 142, 255)),
                  ("钥匙", (255, 214, 80)), ("传送门", (110, 255, 160))]
        x = panel.x + 24
        y = panel.bottom - 34
        for text, color in legend:
            pygame.draw.circle(screen, color, (x + 5, y + 6), 5)
            t = art.label(text, (225, 225, 235), 13)
            screen.blit(t, (x + 14, y - 2))
            x += 14 + t.get_width() + 20

    def kill_enemy(self, enemy):
        if enemy not in self.enemies:
            return
        if enemy.is_summon and getattr(enemy, "summoner", None) is not None:
            enemy.summoner.summon_count = max(0, getattr(enemy.summoner, "summon_count", 0) - 1)
        self.enemies.remove(enemy)
        # 后面的大关卡经验更高，保证 16 关下来能练到 45 级
        self.effects.append(SparkBurst(enemy.rect.centerx, enemy.rect.centery,
                                       (255, 220, 160), 10, 3.6, 20, 3))
        self.effects.append(Shockwave(enemy.rect.centerx, enemy.rect.centery, 30,
                                      (255, 200, 140), 14, 3, 0.35))
        exp_scale = 1 + self.level_index * 0.35
        exp = int(EXP_PER_KILL * exp_scale
                  * (5 if enemy.is_boss else (2 if enemy.is_elite else enemy.xp)))
        before_level = self.player.level
        self.player.gain_exp(exp)
        if self.player.level > before_level:
            px, py = self.player.rect.center
            audio.play("levelup", 0.85)
            self.effects.append(Shockwave(px, py - 10, 130, (255, 230, 150), 26, 7, 0.18))
            self.effects.append(SparkBurst(px, py - 20, (255, 232, 140), 14, 3.2, 26, 3, -0.12))
            self.float_texts.append(FloatText(px, py - 56, f"升级！Lv.{self.player.level}",
                                              (255, 232, 150), 20, 90))
        if getattr(self, "pet", None) is not None:
            self.pet.gain_exp(max(1, int(enemy.xp)), level=self)
        self.float_texts.append(FloatText(enemy.rect.centerx, enemy.rect.centery - 10,
                                          f"+{int(exp)} EXP", (150, 240, 255), 13, 46))
        self.effects.append(Shockwave(enemy.rect.centerx, enemy.rect.centery,
                                      max(enemy.rect.width, enemy.rect.height),
                                      (255, 220, 160), 18, 3, 0.5))
        drop_key = True
        if enemy.is_boss:
            for minion in [e for e in self.enemies if e.summoner is enemy]:
                self.enemies.remove(minion)
                self.effects.append(Shockwave(minion.rect.centerx, minion.rect.centery,
                                              36, (200, 140, 255), 16, 4, 0.4))
            self.shake = 14
            self.effects.append(Shockwave(enemy.rect.centerx, enemy.rect.centery, 220,
                                          (255, 210, 120), 32, 10, 0.2))
            self.float_texts.append(FloatText(
                enemy.rect.centerx, enemy.rect.top - 30,
                f"{enemy.name} 被击败！", (255, 226, 140), 20, 90))

            alive_bosses = [b for b in self.bosses if b in self.enemies]
            drop_key = not alive_bosses
            if drop_key:
                self.boss_defeated = True
                self.float_texts.append(FloatText(
                    self.player.rect.centerx, self.player.rect.top - 30,
                    "全部 BOSS 已击败！", (255, 226, 140), 18, 90))
            else:
                self.float_texts.append(FloatText(
                    enemy.rect.centerx, enemy.rect.top - 52,
                    f"还剩 {len(alive_bosses)} 个 BOSS", (255, 190, 150), 15, 70))
            self._refresh_door()
        self.handle_drops(enemy, drop_key=drop_key)

    def cast_skill(self, slot=0):
        """释放技能（slot 0 = K 键，slot 1 = L 键）。"""
        skill = self.player.try_skill(slot)
        if skill is None:
            return False
        audio.play("skill")

        px, py = self.player.rect.center
        kind = skill["type"]
        base = self.player.get_damage()
        if kind in (SKILL_VOLLEY, "wave", "blast", "meteor"):
            self.player.auto_aim(self, 620)

        if kind == SKILL_SPIN:
            damage = max(1, int(base * skill["mult"]))
            radius = skill["radius"]
            self.effects.append(SpinBlades(px, py, radius))
            self.effects.append(Shockwave(px, py, radius, skill["color"], 22, 6, 0.55))
            for enemy in list(self.enemies):
                reach = radius + max(enemy.rect.width, enemy.rect.height) * 0.5
                if math.hypot(enemy.rect.centerx - px, enemy.rect.centery - py) <= reach:
                    enemy.take_hit(damage, enemy.rect.centerx >= px)
                    enemy.knockback_x = 11 if enemy.rect.centerx >= px else -11
                    enemy.knockback_y = random.uniform(-4, 4)
                    self.pop_damage(enemy, damage, skill["color"])
                    if enemy.dead:
                        self.kill_enemy(enemy)
            self.shake = 7

        elif kind == SKILL_VOLLEY:
            damage = max(1, int(base * skill["mult"]))
            self.player.spawn_volley(skill["count"], damage)
            self.effects.append(Shockwave(px, py, 48, skill["color"], 16, 4, 0.5))
            self.shake = 3

        elif kind == "wave":
            damage = max(1, int(base * skill["mult"]))
            target = self.player.pick_target(self, 760)
            shot_x, shot_y = self.player._shot_unit(0.08)
            if target is not None:
                self.player.set_aim_towards(target.rect.centerx, target.rect.centery, lock=30)
                dist = math.hypot(target.rect.centerx - self.player.rect.centerx,
                                  target.rect.centery - self.player.rect.centery)
                if dist > 1.0:
                    shot_x = (target.rect.centerx - self.player.rect.centerx) / dist
                    shot_y = (target.rect.centery - self.player.rect.centery) / dist
            direction = 1 if shot_x >= 0 else -1
            px = self.player.rect.right if direction > 0 else self.player.rect.left - 40
            wave = Projectile(px, self.player.rect.centery - 20, direction, damage, "wave",
                              max_dist=460, pierce=99, tint=skill["color"],
                              vy=shot_y * 11, vx=shot_x * 11, target=target,
                              homing=0.1 if target is not None else 0.0, hit_pad=16)
            wave.rect.height = 44
            self.player.projectiles.append(wave)
            self.shake = 4

        elif kind == "blast":
            damage = max(1, int(base * skill["mult"]))
            target = self.player.pick_target(self, 760)
            shot_x, shot_y = self.player._shot_unit(0.12)
            if target is not None:
                self.player.set_aim_towards(target.rect.centerx, target.rect.centery, lock=30)
                dist = math.hypot(target.rect.centerx - self.player.rect.centerx,
                                  target.rect.centery - self.player.rect.centery)
                if dist > 1.0:
                    shot_x = (target.rect.centerx - self.player.rect.centerx) / dist
                    shot_y = (target.rect.centery - self.player.rect.centery) / dist
            direction = 1 if shot_x >= 0 else -1
            px = self.player.rect.right if direction > 0 else self.player.rect.left - 18
            arrow = Projectile(px, self.player.rect.centery - 6, direction, damage, "arrow",
                               max_dist=420, pierce=1, tint=(255, 190, 140),
                               vy=shot_y * 12, vx=shot_x * 12, target=target,
                               homing=0.14 if target is not None else 0.0, hit_pad=10)
            arrow.explode_radius = skill["radius"]
            self.player.projectiles.append(arrow)
            self.shake = 3

        elif kind == "chain":
            damage = max(1, int(base * skill["mult"]))
            targets = []
            for enemy in self.enemies:
                dist = math.hypot(enemy.rect.centerx - self.player.rect.centerx,
                                  enemy.rect.centery - self.player.rect.centery)
                if dist < 420:
                    targets.append((dist, enemy))
            targets.sort(key=lambda t: t[0])
            last = (self.player.rect.centerx, self.player.rect.centery)
            for _, enemy in targets[:skill["targets"]]:
                self.effects.append(LightningFX(last[0], last[1], enemy.rect.centerx,
                                                enemy.rect.centery, skill["color"], 13, 9))
                self.effects.append(Beam(last[0], last[1], enemy.rect.centerx, enemy.rect.centery,
                                         skill["color"], 8, 3))
                last = (enemy.rect.centerx, enemy.rect.centery)
                enemy.take_hit(damage, enemy.rect.centerx >= self.player.rect.centerx)
                enemy.freeze(skill["freeze"])
                self.pop_damage(enemy, damage, skill["color"])
                if enemy.dead:
                    self.kill_enemy(enemy)
            self.effects.append(Shockwave(self.player.rect.centerx, self.player.rect.centery,
                                          90, skill["color"], 20, 4, 0.3))
            self.shake = 5

        elif kind == "quake":
            damage = max(1, int(base * skill["mult"]))
            radius = skill["radius"]
            px, py = self.player.rect.center
            self.effects.append(GroundCracks(px, py + 18, radius, (255, 170, 110), 30))
            self.effects.append(Shockwave(px, py, radius, (255, 170, 110), 30, 12, 0.15))
            self.effects.append(Shockwave(px, py, radius * 0.6, (255, 220, 160), 20, 8, 0.3))
            self.shake = 9
            audio.play("boom", 0.7)
            for enemy in list(self.enemies):
                if math.hypot(enemy.rect.centerx - px, enemy.rect.centery - py) <= radius:
                    enemy.take_hit(damage, enemy.rect.centerx >= px)
                    enemy.freeze(skill["freeze"])
                    self.pop_damage(enemy, damage, skill["color"])
                    if enemy.dead:
                        self.kill_enemy(enemy)

        elif kind == "arrow_rain":
            damage = max(1, int(base * skill["mult"]))
            radius = skill["radius"]
            px, py = self.player.rect.center
            self.effects.append(ArrowStormFX(px, py, radius, (200, 255, 210), 34, 22))
            self.effects.append(Shockwave(px, py, radius, (190, 255, 200), 28, 6, 0.2))
            self.shake = 5
            for enemy in list(self.enemies):
                if math.hypot(enemy.rect.centerx - px, enemy.rect.centery - py) > radius:
                    continue
                for k in range(2):
                    self.effects.append(Beam(enemy.rect.centerx + random.randint(-20, 20),
                                             enemy.rect.centery - 160,
                                             enemy.rect.centerx, enemy.rect.centery,
                                             (200, 255, 210), 12 + k * 4, 3))
                enemy.take_hit(damage, enemy.rect.centerx >= px)
                self.pop_damage(enemy, damage, skill["color"])
                if enemy.dead:
                    self.kill_enemy(enemy)

        elif kind == "meteor":
            damage = max(1, int(base * skill["mult"]))
            radius = skill["radius"]
            px, py = self.player.rect.center
            target = None
            best = 520
            for enemy in self.enemies:
                d = math.hypot(enemy.rect.centerx - px, enemy.rect.centery - py)
                if d < best:
                    best, target = d, enemy
            tx = target.rect.centerx if target else px + int(self.player.aim_dx * 90)
            ty = target.rect.centery if target else py + int(self.player.aim_dy * 70)
            self.effects.append(MeteorStrike(tx, ty, radius, skill["color"]))
            self.shake = 11
            audio.play("boom", 0.8)
            for enemy in list(self.enemies):
                if math.hypot(enemy.rect.centerx - tx, enemy.rect.centery - ty) <= radius:
                    enemy.take_hit(damage, enemy.rect.centerx >= tx)
                    self.pop_damage(enemy, damage, skill["color"])
                    if enemy.dead:
                        self.kill_enemy(enemy)

        elif kind == SKILL_NOVA:
            damage = max(1, int(base * skill["mult"]))
            radius = skill["radius"]
            self.effects.append(Shockwave(px, py, radius, skill["color"], 30, 9, 0.25))
            self.effects.append(FrostShards(px, py, radius))
            for enemy in list(self.enemies):
                reach = radius + max(enemy.rect.width, enemy.rect.height) * 0.5
                if math.hypot(enemy.rect.centerx - px, enemy.rect.centery - py) <= reach:
                    enemy.take_hit(damage, enemy.rect.centerx >= px)
                    enemy.freeze(skill["freeze"])
                    self.pop_damage(enemy, damage, skill["color"])
                    if enemy.dead:
                        self.kill_enemy(enemy)
            self.shake = 9

        return True

    # ---------------- 物品拾取 ----------------
    def _pickup(self, item):
        player = self.player
        item.collected = True

        if item.type == "key":
            self.has_key = True
            audio.play("key", 0.95)
            self.float_texts.append(FloatText(item.rect.centerx, item.rect.top,
                                              "获得钥匙！", GOLD_COLOR, 17, 70))
            self._refresh_door()
            return

        if item.type in ("potion_hp", "potion_energy", "potion_speed", "bomb"):
            player.add_item(item.type)
            audio.play("pickup")
            self.float_texts.append(FloatText(
                item.rect.centerx, item.rect.top,
                f"获得 {ITEM_NAME[item.type]} ×1", (255, 214, 170), 14, 60))
            return

        if item.type in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
            inv = {
                "weapon": player.inventory_weapons,
                "armor": player.inventory_armors,
                "helmet": player.inventory_helmets,
                "boots": player.inventory_boots,
                "pants": player.inventory_pants,
                "bracelet": player.inventory_bracelets,
            }[item.type]
            if len(inv) >= INVENTORY_MAX:
                self.float_texts.append(FloatText(
                    item.rect.centerx, item.rect.top - 10, "背包已满！",
                    (255, 150, 150), 15, 60))
                item.collected = False
                return
            inv.append((item.quality, item.set_key, item.hidden))
            self.float_texts.append(FloatText(item.rect.centerx, item.rect.top,
                                              f"获得 {item.display_name()}",
                                              Q_COLOR[item.quality], 14, 60))
            audio.play("pickup")
            return

        if item.type == "chest":
            audio.play("pickup")
            self.effects.append(Shockwave(item.rect.centerx, item.rect.centery, 120,
                                          (255, 210, 110), 26, 6, 0.3))
            self.float_texts.append(FloatText(item.rect.centerx, item.rect.top,
                                              "宝箱开启！", (255, 226, 150), 16, 70))
            for _ in range(2):
                q = self.get_drop_quality()
                kind = random.choice(["weapon", "armor", "helmet"])
                hidden = None
                if q == Q_RED and random.random() < MYTHIC_HIDDEN_CHANCE:
                    hidden = random.choice(list(HIDDEN_EFFECTS))
                self.spawn_item(
                    item.rect.centerx + random.randint(-36, 36),
                    item.rect.centery + random.randint(-20, 26),
                    kind, q, self.weapon_type if kind == "weapon" else None,
                    set_key=self.set_key, hidden=hidden)


    # ---------------- 主循环 ----------------
    def update(self):
        # 环境：海水阻力 / 火山灼烧
        if self.theme == "ocean":
            resist = self.player.status_resist("ocean")
            self.player.env_speed_mult = 1.0 - 0.18 * (1 - resist)
        else:
            self.player.env_speed_mult = 1.0
        if self.theme == "volcano":
            tile = self.map_data[self.player.rect.centery // TILE_SIZE][
                self.player.rect.centerx // TILE_SIZE]
            if tile == SPIKE_CHAR and self.player.burn_timer <= 0:
                self.player.burn_timer = max(30, int(120 * (1 - self.player.status_resist("volcano"))))
                self.float_texts.append(FloatText(
                    self.player.rect.centerx, self.player.rect.top - 22,
                    "灼烧！", (255, 150, 80), 16, 60))
        if self.player.burn_timer > 0:
            self.player.burn_timer -= 1
            if self.player.burn_timer % 30 == 0:
                burn_resist = self.player.status_resist("volcano")
                dmg = self.player.take_damage(max(1, int((4 + chapter_of(self.level_index))
                                                        * (1 - burn_resist))), DMG_MAGIC)
                if dmg:
                    self.pop_player_damage(dmg, DMG_MAGIC)
                    self.effects.append(SparkBurst(self.player.rect.centerx,
                                                   self.player.rect.centery,
                                                   (255, 140, 60), 6, 2.0, 12, 2, -0.2))

        # 玩家攻击特效（刀光 / 火花 / 魔法阵）
        for fx in self.player.fx_queue:
            kind, fx_x, fx_y, fx_d = fx
            if kind == "slash":
                self.effects.append(SlashArc(fx_x, fx_y, fx_d, (255, 236, 190), 58))
            elif kind == "shot":
                self.effects.append(SparkBurst(fx_x, fx_y, (210, 255, 210), 5, 2.2, 9, 2, 0.1))
            elif kind == "cast":
                self.effects.append(CastCircle(fx_x, fx_y, (150, 200, 255)))
                self.effects.append(SparkBurst(fx_x, fx_y - 22, (160, 210, 255),
                                               8, 1.8, 16, 3, -0.1))
            elif kind == "cast_magic":
                self.effects.append(CastCircle(fx_x, fx_y, (136, 208, 255), life=24))
                self.effects.append(Shockwave(fx_x, fx_y - 10, 42, (122, 200, 255), 18, 4, 0.45))
                self.effects.append(SparkBurst(fx_x, fx_y - 24, (188, 236, 255),
                                               12, 2.1, 18, 3, -0.14))
        self.player.fx_queue.clear()

        # BOSS 战音乐：带迟滞，避免在范围边缘来回切换
        px, py = self.player.rect.center
        nearest = 10 ** 9
        for b in self.bosses:
            if b in self.enemies:
                nearest = min(nearest, math.hypot(b.rect.centerx - px, b.rect.centery - py))
        if getattr(self, "_boss_music", False):
            if self.boss_defeated or nearest > 820:
                self._boss_music = False
        elif not self.boss_defeated and nearest < 620:
            self._boss_music = True
        want = "boss" if getattr(self, "_boss_music", False) else level_theme(self.level_index)
        if audio.music_name() != want:
            audio.play_music(want)

        self._update_spawn_interval()
        if self._can_spawn_enemy():
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0
                self.spawn_enemy()
        else:
            self.spawn_timer = min(self.spawn_timer, max(0, self.spawn_interval - 90))

        for enemy in self.enemies[:]:
            enemy.update(self.solid, self.player, self)

            # 剑士近战判定
            if (self.player.weapon_type == WEAPON_SWORD and self.player.is_attacking
                    and self.player.attack_timer == 11
                    and self.player.attack_rect.colliderect(enemy.rect)):
                crit = random.random() < self.player.crit_chance
                dmg = self.player.get_damage() * (self.player.CRIT_MULT if crit else 1)
                enemy.take_hit(dmg, self.player.facing_right)
                self._hit_feedback(enemy, dmg, crit=crit)
                self.pop_damage(enemy, dmg, (255, 220, 120) if crit else None)
                if enemy.dead:
                    self.kill_enemy(enemy)

        # 平台：站在上面时脚下高度抬高
        p = self.player
        p.floor_z = 0
        if p.z >= PLATFORM_H - 10:
            for pr_rect in self.platform_rects:
                if p.rect.colliderect(pr_rect):
                    p.floor_z = PLATFORM_H
                    break

        self.player.update(self.walls)
        self._landing_fix()

        # 尖刺陷阱
        if self.spike_damage_cd > 0:
            self.spike_damage_cd -= 1
        if self.spike_rects and self.player.z <= 4 and self.spike_damage_cd == 0:
            feet = pygame.Rect(self.player.rect.centerx - 9, self.player.rect.bottom - 10, 18, 10)
            if any(feet.colliderect(sr) for sr in self.spike_rects):
                dmg = self.player.take_damage(SPIKE_DAMAGE, DMG_PHYS)
                if dmg > 0:
                    self.pop_player_damage(dmg, DMG_PHYS)
                    self.spike_damage_cd = 45
                    self.effects.append(Shockwave(self.player.rect.centerx,
                                                  self.player.rect.bottom, 34,
                                                  (255, 120, 120), 14, 3, 0.4))
        self.pet.update(self)

        # 剑士砍木箱
        if (self.player.weapon_type == WEAPON_SWORD and self.player.is_attacking
                and self.player.attack_timer == 11):
            for crate in self.crates[:]:
                if self.player.attack_rect.colliderect(crate["rect"]):
                    self._hit_crate(crate, self.player.get_damage())
                    audio.play("hit", 0.5)

        # 敌方弹幕（弓箭手/法师/BOSS 技能）
        for bolt in self.enemy_shots[:]:
            bolt.update(self.walls)
            if bolt.dead:
                self.enemy_shots.remove(bolt)
                continue
            if bolt.rect.colliderect(self.player.rect) and self.player.z < JUMP_DODGE_Z:
                dmg = self.player.take_damage(bolt.damage, bolt.dmg_type)
                if dmg > 0:
                    self.pop_player_damage(dmg, bolt.dmg_type)
                    self.shake = max(self.shake, 2)
                self.enemy_shots.remove(bolt)

        # 玩家弹幕命中木箱
        for p in self.player.projectiles:
            if p.dead:
                continue
            hit_rect = p.hit_rect()
            for crate in self.crates[:]:
                if hit_rect.colliderect(crate["rect"]):
                    self._hit_crate(crate, p.damage)
                    p.dead = True
                    break

        # 玩家弹幕命中（支持穿透）
        for p in self.player.projectiles:
            if p.dead:
                continue
            hit_rect = p.hit_rect()
            for enemy in self.enemies[:]:
                if p.dead:
                    break
                if id(enemy) in p.hits:
                    continue
                if hit_rect.colliderect(enemy.rect):
                    p.hits.add(id(enemy))
                    crit = random.random() < self.player.crit_chance
                    dmg = p.damage * (self.player.CRIT_MULT if crit else 1)
                    magic = getattr(p, "p_type", "arrow") == "magic"
                    enemy.take_hit(dmg, p.direction > 0)
                    self._hit_feedback(enemy, dmg, crit=crit, magic=magic)
                    self.pop_damage(enemy, dmg, (255, 220, 120) if crit else None)
                    p.pierce -= 1
                    if p.pierce <= 0:
                        p.dead = True
                    if getattr(p, "explode_radius", 0):
                        self._explode_at(p.rect.centerx, p.rect.centery,
                                         p.explode_radius, p.damage)
                        p.dead = True
                    if enemy.dead:
                        self.kill_enemy(enemy)

        for item in self.items[:]:
            item.update_physics(self._drop_blockers())
            if not item.collected and self.player.rect.colliderect(item.rect):
                self._pickup(item)

        for effect in self.effects[:]:
            effect.update()
            if effect.dead:
                self.effects.remove(effect)

        for text in self.float_texts[:]:
            text.update()
            if text.dead:
                self.float_texts.remove(text)

        if self.shake > 0:
            self.shake -= 1

        self.weather.update()
        self._refresh_door()

    def spawn_enemy(self):
        if not self.empty_tiles:
            return
        px, py = self.player.rect.center
        valid = []
        for ex, ey in self.empty_tiles:
            cx, cy = ex + TILE_SIZE // 2, ey + TILE_SIZE // 2
            dist = math.hypot(cx - px, cy - py)
            if dist < 320 or dist > 920:
                continue
            if math.hypot(cx - self.boss_center[0], cy - self.boss_center[1]) < 220:
                continue
            if any(math.hypot(cx - enemy.rect.centerx, cy - enemy.rect.centery) < 120
                   for enemy in self.enemies if not enemy.is_boss):
                continue
            valid.append((ex, ey))
        if not valid:
            valid = [(ex, ey) for ex, ey in self.empty_tiles
                     if 320 < math.hypot(ex - px, ey - py) < 920]
        if not valid:
            return
        sx, sy = random.choice(valid)
        pool = self.CHAPTER_POOL[level_theme(self.level_index)]
        e_type = random.choice(pool)
        elite_chance = self.ELITE_CHANCE.get(self.level_index, 0.3)
        is_elite = random.random() < elite_chance
        self.enemies.append(Enemy(sx, sy, enemy_type=e_type,
                                  is_elite=is_elite, level_idx=self.level_index))

    # ---------------- 绘制 ----------------
    def _draw_door(self, screen, cam_x, cam_y):
        if not self.door_rect:
            return
        dx = self.door_rect.x - cam_x
        dy = self.door_rect.y - cam_y
        if not (-TILE_SIZE < dx < WIDTH and -TILE_SIZE < dy < HEIGHT):
            return

        t = pygame.time.get_ticks() / 1000.0
        if self.door_open:
            color = (90, 255, 150)
            art.blit_glow(screen, dx + TILE_SIZE // 2, dy + TILE_SIZE // 2,
                          int(TILE_SIZE * 1.2 + 6 * math.sin(t * 4)), color, 90)
            pygame.draw.rect(screen, (20, 70, 40), (dx + 4, dy + 4, TILE_SIZE - 8, TILE_SIZE - 8))
            pygame.draw.rect(screen, color, (dx + 7, dy + 7, TILE_SIZE - 14, TILE_SIZE - 14), 2)
            for i in range(3):
                r = int(6 + i * 5 + 3 * math.sin(t * 3 + i))
                pygame.draw.circle(screen, color, (dx + TILE_SIZE // 2, dy + TILE_SIZE // 2), r, 2)
        else:
            color = (190, 60, 70)
            art.blit_glow(screen, dx + TILE_SIZE // 2, dy + TILE_SIZE // 2, 36, color, 50)
            pygame.draw.rect(screen, (44, 20, 26), (dx + 3, dy + 2, TILE_SIZE - 6, TILE_SIZE - 4))
            for i in range(0, TILE_SIZE - 8, 8):
                pygame.draw.line(screen, (110, 44, 52), (dx + 4 + i, dy + 3),
                                 (dx + 4 + i, dy + TILE_SIZE - 4), 3)
            pygame.draw.rect(screen, color, (dx + 3, dy + 2, TILE_SIZE - 6, TILE_SIZE - 4), 2)
            pygame.draw.circle(screen, (255, 200, 120), (dx + TILE_SIZE // 2, dy + TILE_SIZE // 2), 3)

            if self.has_key:
                need = "需击败 BOSS"
            elif self.boss_defeated:
                need = "需找到钥匙"
            else:
                need = "需钥匙+BOSS"
            tip = art.label(need, (255, 190, 150), 11)
            screen.blit(tip, (dx + TILE_SIZE // 2 - tip.get_width() // 2, dy - 16))

    def _offscreen_marker(self, screen, cam_x, cam_y, world_pos, color, icon_char):
        """目标在屏幕外时，在屏幕边缘画一个指向箭头，方便找钥匙/BOSS。"""
        x = world_pos[0] - cam_x
        y = world_pos[1] - cam_y
        margin = 34
        if margin < x < WIDTH - margin and margin < y < HEIGHT - margin:
            return
        # 指示器只在“安全区”内移动，避开顶部 HUD 和右下角按钮
        left, top = 44, 150
        right, bottom = WIDTH - 44, HEIGHT - 182
        cx, cy = (left + right) / 2, (top + bottom) / 2
        dx, dy = x - cx, y - cy
        scale = min((right - left) / 2 / max(1e-6, abs(dx)),
                    (bottom - top) / 2 / max(1e-6, abs(dy)))
        px, py = cx + dx * scale, cy + dy * scale
        ang = math.atan2(dy, dx)
        tip = (px + math.cos(ang) * 14, py + math.sin(ang) * 14)
        left = (px + math.cos(ang + 2.5) * 12, py + math.sin(ang + 2.5) * 12)
        right = (px + math.cos(ang - 2.5) * 12, py + math.sin(ang - 2.5) * 12)
        pygame.draw.polygon(screen, color, [tip, left, right])
        pygame.draw.circle(screen, (18, 16, 24), (int(px), int(py)), 12)
        pygame.draw.circle(screen, color, (int(px), int(py)), 12, 2)
        surf = art.label(icon_char, color, 13, True)
        screen.blit(surf, (int(px) - surf.get_width() // 2, int(py) - surf.get_height() // 2))

    def draw(self, screen, cam_x, cam_y):
        src = pygame.Rect(cam_x, cam_y, WIDTH, HEIGHT)
        screen.blit(self.map_surface, (0, 0), src)

        self._draw_door(screen, cam_x, cam_y)

        for item in self.items:
            if -60 < item.rect.x - cam_x < WIDTH + 60 and -60 < item.rect.y - cam_y < HEIGHT + 60:
                item.draw(screen, cam_x, cam_y)

        for enemy in self.enemies:
            if -120 < enemy.rect.x - cam_x < WIDTH + 120 and -120 < enemy.rect.y - cam_y < HEIGHT + 120:
                enemy.draw(screen, cam_x, cam_y)

        self.pet.draw(screen, cam_x, cam_y)
        self.player.draw(screen, cam_x, cam_y)

        for bolt in self.enemy_shots:
            if -60 < bolt.x - cam_x < WIDTH + 60 and -60 < bolt.y - cam_y < HEIGHT + 60:
                bolt.draw(screen, cam_x, cam_y)

        live_bosses = [b for b in getattr(self, "bosses", []) if b in self.enemies]
        if live_bosses:
            nearest = min(live_bosses, key=lambda b: math.hypot(
                b.rect.centerx - self.player.rect.centerx,
                b.rect.centery - self.player.rect.centery))
            self._offscreen_marker(screen, cam_x, cam_y,
                                   nearest.rect.center, (255, 120, 170), "王")
        if not self.has_key:
            key_item = next((i for i in self.items if i.type == "key" and not i.collected), None)
            if key_item is not None:
                self._offscreen_marker(screen, cam_x, cam_y,
                                       key_item.rect.center, (255, 214, 80), "钥")

        for effect in self.effects:
            effect.draw(screen, cam_x, cam_y)

        for text in self.float_texts:
            text.draw(screen, cam_x, cam_y)

        self.weather.draw(screen)
        _draw_vignette(screen, self.level_index)


_vignette_cache = {}


def _draw_vignette(screen, level_index):
    """画面四周压暗，洞穴氛围更足。"""
    theme = level_theme(level_index)
    if theme == "sky":
        return
    tint_color = {"ocean": (10, 30, 60), "volcano": (50, 10, 6)}.get(theme, (0, 0, 0))
    surf = _vignette_cache.get((theme, tint_color))
    if surf is None:
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        depth = 90
        for i in range(depth):
            alpha = int(120 * (1 - i / depth) ** 2)
            if alpha <= 0:
                continue
            col = (*tint_color, alpha)
            pygame.draw.rect(surf, col, (0, i, WIDTH, 1))
            pygame.draw.rect(surf, col, (0, HEIGHT - 1 - i, WIDTH, 1))
            pygame.draw.rect(surf, col, (i, 0, 1, HEIGHT))
            pygame.draw.rect(surf, col, (WIDTH - 1 - i, 0, 1, HEIGHT))
        _vignette_cache[(theme, tint_color)] = surf
    screen.blit(surf, (0, 0))
