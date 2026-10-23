# entities.py
import math
import random

import pygame

import art
import audio
from settings import *


WEAPON_ITEM_NAME = {WEAPON_SWORD: "长剑", WEAPON_BOW: "长弓", WEAPON_STAFF: "法杖"}

# 怪物图鉴：血量/速度/体型/飞行/追击/经验 + 战斗定位（战士/弓箭手/法师）
ENEMY_STATS = {
    "slime":     dict(hp=1.0,  speed=1.0,  size=(30, 30), fly=False, chase=False, xp=1,
                      role="warrior", dmg=6),
    "mushroom":  dict(hp=1.4,  speed=0.8,  size=(32, 32), fly=False, chase=False, xp=1,
                      role="warrior", dmg=7),
    "skeleton":  dict(hp=1.9,  speed=1.1,  size=(30, 40), fly=False, chase=True,  xp=2,
                      role="archer",  dmg=5, shot=8),
    "bat":       dict(hp=0.65, speed=1.7,  size=(30, 24), fly=True,  chase=True,  xp=1,
                      role="mage",    dmg=4, shot=9),
    "butterfly": dict(hp=0.55, speed=1.5,  size=(32, 32), fly=True,  chase=False, xp=1,
                      role="mage",    dmg=3, shot=6),
    "tree":      dict(hp=3.2,  speed=0.4,  size=(40, 48), fly=False, chase=False, xp=3,
                      role="warrior", dmg=14),
    "golem":     dict(hp=3.6,  speed=0.6,  size=(38, 44), fly=False, chase=True,  xp=4,
                      role="warrior", dmg=15),
}

ROLE_NAME = {"warrior": "战士", "archer": "弓箭手", "mage": "法师", "boss": "首领"}
ROLE_DMG_TYPE = {"warrior": DMG_PHYS, "archer": DMG_PHYS, "mage": DMG_MAGIC, "boss": DMG_PHYS}
ROLE_COLOR = {"warrior": (255, 150, 120), "archer": (160, 230, 160),
              "mage": (170, 150, 255), "boss": (255, 120, 200)}
_BOSS_WARN_CACHE = {}


def _shade(color, factor=0.6):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def _light(color, amount=0.35):
    return tuple(min(255, int(c + (255 - c) * amount)) for c in color[:3])


def _boss_warn_surface(radius):
    surf = _BOSS_WARN_CACHE.get(radius)
    if surf is not None:
        return surf
    surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 90, 60, 120), (radius + 4, radius + 4), radius, 4)
    pygame.draw.circle(surf, (255, 220, 120, 60), (radius + 4, radius + 4),
                       max(1, int(radius * 0.6)), 3)
    _BOSS_WARN_CACHE[radius] = surf
    return surf


# --------------------------------------------------------------------------
# 玩家的箭矢/法术弹
# --------------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, direction, damage, type_name, max_dist=300,
                 vy=0.0, pierce=1, tint=None, vx=None, target=None,
                 homing=0.0, hit_pad=0):
        self.type = type_name
        self.p_type = type_name
        self.direction = 1 if direction >= 0 else -1
        self.damage = damage
        self.max_dist = max_dist
        self.pierce = pierce
        self.tint = tint
        self.explode_radius = 0
        self.hits = set()
        base_speed = 11 if type_name != "magic" else 9
        self.vx = float(vx) if vx is not None else self.direction * base_speed
        self.vy = float(vy)
        self.target = target
        self.homing = homing
        self.hit_pad = hit_pad
        if abs(self.vx) < 0.01:
            self.vx = self.direction * max(1.0, base_speed * 0.35)
        self.direction = 1 if self.vx >= 0 else -1
        self.speed = max(0.01, math.hypot(self.vx, self.vy))
        self.x = float(x)
        self.y = float(y)
        self.start_x, self.start_y = self.x, self.y
        self.dead = False
        if type_name == "magic":
            self.rect = pygame.Rect(int(self.x), int(self.y), 22, 22)
            self.hit_pad = max(self.hit_pad, 10)
        elif type_name == "wave":
            self.rect = pygame.Rect(int(self.x), int(self.y), 34, 44)
            self.hit_pad = max(self.hit_pad, 16)
        else:
            self.rect = pygame.Rect(int(self.x), int(self.y), 22, 12)
            self.hit_pad = max(self.hit_pad, 6)

    def hit_rect(self):
        return self.rect.inflate(self.hit_pad * 2, self.hit_pad * 2)

    def _home_towards_target(self):
        if self.homing <= 0 or self.target is None or getattr(self.target, "dead", False):
            return
        tx = self.target.rect.centerx - self.rect.centerx
        ty = self.target.rect.centery - self.rect.centery
        dist = math.hypot(tx, ty)
        if dist <= 1.0:
            return
        desired_vx = tx / dist * self.speed
        desired_vy = ty / dist * self.speed
        blend = max(0.0, min(0.45, self.homing))
        self.vx = self.vx * (1.0 - blend) + desired_vx * blend
        self.vy = self.vy * (1.0 - blend) + desired_vy * blend
        self.direction = 1 if self.vx >= 0 else -1

    def update(self, walls):
        self._home_towards_target()
        self.x += self.vx
        self.y += self.vy
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)
        if math.hypot(self.x - self.start_x, self.y - self.start_y) > self.max_dist:
            self.dead = True
        for wall in walls:
            if self.rect.colliderect(wall):
                self.dead = True
                break

    def _nearby(self, level, radius):
        out = []
        for enemy in level.enemies:
            d = math.hypot(enemy.rect.centerx - self.rect.centerx,
                           enemy.rect.centery - self.rect.centery)
            if d <= radius:
                out.append((d, enemy))
        out.sort(key=lambda t: t[0])
        return out

    def _cast_skill(self, index, level):
        """返回 True 表示成功释放。"""
        player = self.player
        base = (PET_ATTACK_DMG + player.level * 3 + self.level * 3) * (1 + self.stage * 0.25)

        if self.kind == WEAPON_SWORD:
            if index == 0:
                targets = self._nearby(level, 340)
                if not targets:
                    return False
                enemy = targets[0][1]
                level.effects.append(Beam(self.rect.centerx, self.rect.centery,
                                          enemy.rect.centerx, enemy.rect.centery,
                                          (255, 160, 80), 14, 6))
                dmg = int(base * 2.2)
                enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                level.pop_damage(enemy, dmg, (255, 180, 100))
                level.effects.append(Shockwave(enemy.rect.centerx, enemy.rect.centery, 40,
                                               (255, 170, 90), 16, 4, 0.3))
                if enemy.dead:
                    level.kill_enemy(enemy)
                return True
            ring = self._nearby(level, 150)
            if not ring:
                return False
            level.effects.append(Shockwave(self.rect.centerx, self.rect.centery, 150,
                                           (255, 140, 70), 26, 8, 0.2))
            for _, enemy in ring:
                dmg = int(base * 1.6)
                enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                level.pop_damage(enemy, dmg, (255, 170, 100))
                if enemy.dead:
                    level.kill_enemy(enemy)
            return True

        if self.kind == WEAPON_BOW:
            if index == 0:
                targets = self._nearby(level, 360)[:3]
                if not targets:
                    return False
                for _, enemy in targets:
                    level.effects.append(Beam(self.rect.centerx, self.rect.centery,
                                              enemy.rect.centerx, enemy.rect.centery,
                                              (190, 255, 200), 10, 4))
                    dmg = int(base * 1.5)
                    enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                    level.pop_damage(enemy, dmg, (200, 255, 210))
                    if enemy.dead:
                        level.kill_enemy(enemy)
                return True
            player.speed_bonus_timer = max(player.speed_bonus_timer, 240)
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                               "风之祝福！", (190, 255, 210), 16, 60))
            level.effects.append(Shockwave(player.rect.centerx, player.rect.centery, 70,
                                           (190, 255, 200), 20, 4, 0.3))
            return True

        # 法师跟宠
        if index == 0:
            healed = player.heal(24 + self.level * 2)
            before = player.energy
            player.energy = min(MAX_ENERGY, player.energy + 12)
            if healed <= 0 and player.energy == before:
                return False
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                               f"治疗波 +{healed}", (150, 255, 200), 15, 52))
            return True
        healed = player.heal(46 + self.level * 3)
        player.energy = min(MAX_ENERGY, player.energy + 40)
        level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                           f"魔力涌泉 +{healed}", (150, 220, 255), 15, 60))
        level.effects.append(Shockwave(player.rect.centerx, player.rect.centery, 90,
                                       (140, 210, 255), 24, 6, 0.25))
        return True

    def draw(self, screen, cam_x, cam_y):
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery - cam_y
        if self.type == "magic":
            tail_dx = -self.direction * 12
            for i, alpha in enumerate((44, 28, 16)):
                px = int(cx + tail_dx * (0.35 + i * 0.28))
                py = int(cy - self.vy * (1.5 + i * 0.5))
                art.blit_glow(screen, px, py, 12 - i * 2, (120, 220, 255), alpha)
            art.blit_glow(screen, cx, cy, 24, (90, 220, 255), 110)
            pygame.draw.circle(screen, (60, 170, 220), (cx, cy), 9)
            pygame.draw.circle(screen, (150, 235, 255), (cx, cy), 6)
            pygame.draw.circle(screen, (245, 255, 255), (cx - 1, cy - 1), 2)
            for ang in (0, math.pi / 2, math.pi, math.pi * 1.5):
                rx = int(cx + math.cos(ang) * 6)
                ry = int(cy + math.sin(ang) * 6)
                pygame.draw.line(screen, (210, 248, 255), (cx, cy), (rx, ry), 1)
            return

        color = self.tint or (238, 226, 190)
        if self.type == "wave":
            r = 26
            surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            start = -1.1 if self.direction > 0 else 2.0
            pygame.draw.arc(surf, (*color, 230), (4, 4, r * 2, r * 2), start, start + 1.3, 9)
            pygame.draw.arc(surf, (255, 255, 255, 170), (10, 10, r * 2 - 12, r * 2 - 12),
                            start, start + 1.3, 3)
            screen.blit(surf, (cx - r - 4, cy - r - 4))
            return
        ang = math.atan2(self.vy, self.direction * self.speed)
        dx, dy = math.cos(ang), math.sin(ang)
        tail = (cx - dx * 16, cy - dy * 16)
        head = (cx + dx * 9, cy + dy * 9)
        pygame.draw.line(screen, _shade(color), tail, head, 3)
        pygame.draw.line(screen, color, (tail[0] + dx * 2, tail[1] + dy * 2), head, 1)
        pygame.draw.polygon(screen, (255, 250, 235), [
            head,
            (head[0] - dx * 7 + dy * 4, head[1] - dy * 7 - dx * 4),
            (head[0] - dx * 7 - dy * 4, head[1] - dy * 7 + dx * 4),
        ])
        pygame.draw.line(screen, (226, 120, 120),
                         tail, (tail[0] - dx * 5 + dy * 4, tail[1] - dy * 5 - dx * 4), 2)
        pygame.draw.line(screen, (226, 120, 120),
                         tail, (tail[0] - dx * 5 - dy * 4, tail[1] - dy * 5 + dx * 4), 2)


# --------------------------------------------------------------------------
# 怪物/宠物共用的飞行弹
# --------------------------------------------------------------------------
class Bolt:
    def __init__(self, x, y, vx, vy, damage, dmg_type=DMG_PHYS,
                 hostile=True, kind="arrow", life=180):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.dmg_type = dmg_type
        self.hostile = hostile
        self.kind = kind
        self.life = life
        self.dead = False
        self.rect = pygame.Rect(0, 0, 10, 10)
        self.rect.center = (int(x), int(y))
        self.angle = math.atan2(vy, vx)

    def update(self, walls):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        self.life -= 1
        if self.life <= 0:
            self.dead = True
        for wall in walls:
            if self.rect.colliderect(wall):
                self.dead = True
                break

    def draw(self, screen, cam_x, cam_y):
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        if self.kind in ("orb", "bolt"):
            color = (170, 120, 255) if self.kind == "orb" else (255, 200, 120)
            art.blit_glow(screen, cx, cy, 16, color, 110)
            pygame.draw.circle(screen, _shade(color), (cx, cy), 7)
            pygame.draw.circle(screen, _light(color, 0.5), (cx, cy), 4)
            pygame.draw.circle(screen, (255, 255, 255), (cx - 1, cy - 1), 1)
            return

        if self.kind == "thorn":
            color = (120, 200, 90)
            for dx, dy in ((0, -6), (6, 0), (0, 6), (-6, 0)):
                pygame.draw.line(screen, color, (cx, cy), (cx + dx, cy + dy), 2)
            pygame.draw.circle(screen, _light(color, 0.4), (cx, cy), 3)
            return

        dx, dy = math.cos(self.angle), math.sin(self.angle)
        color = (255, 226, 190) if self.kind != "bone" else (236, 234, 224)
        pygame.draw.line(screen, color, (cx - dx * 12, cy - dy * 12), (cx, cy), 3)
        pygame.draw.polygon(screen, (255, 255, 255), [
            (cx + dx * 5, cy + dy * 5),
            (cx - dx * 4 + dy * 4, cy - dy * 4 - dx * 4),
            (cx - dx * 4 - dy * 4, cy - dy * 4 + dx * 4),
        ])


# --------------------------------------------------------------------------
# 特效
# --------------------------------------------------------------------------
class FloatText:
    def __init__(self, x, y, text, color=(255, 236, 140), size=16, life=44):
        self.x, self.y = float(x), float(y)
        self.text = text
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        self.y -= 0.85

    def draw(self, screen, cam_x, cam_y):
        alpha = 255 if self.life > 12 else int(255 * self.life / 12)
        surf = art.label(self.text, self.color, self.size, True)
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        screen.blit(surf, (int(self.x - cam_x) - surf.get_width() // 2, int(self.y - cam_y)))


class Shockwave:
    def __init__(self, x, y, radius, color, life=26, width=7, start=0.3):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.life = life
        self.max_life = life
        self.width = width
        self.start = start

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        t = 1 - self.life / self.max_life
        r = int(self.radius * (self.start + (1 - self.start) * t))
        alpha = int(220 * (1 - t) ** 1.4)
        if r <= 0:
            return
        surf = pygame.Surface((r * 2 + 16, r * 2 + 16), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha // 6), (r + 8, r + 8), r)
        pygame.draw.circle(surf, (*self.color, alpha), (r + 8, r + 8), r,
                           max(2, int(self.width * (1 - t))))
        inner = max(4, int(r * 0.58))
        pygame.draw.circle(surf, (255, 248, 220, alpha // 3), (r + 8, r + 8), inner, 2)
        for i in range(6):
            ang = math.tau * i / 6 + t * 2.4
            px = r + 8 + math.cos(ang) * inner
            py = r + 8 + math.sin(ang) * inner
            pygame.draw.circle(surf, (255, 255, 255, alpha // 2), (int(px), int(py)), 2)
        screen.blit(surf, (self.x - cam_x - r - 8, self.y - cam_y - r - 8))


class SpinBlades:
    def __init__(self, x, y, radius, life=26, color=(255, 226, 150)):
        self.x, self.y = x, y
        self.radius = radius
        self.life = life
        self.max_life = life
        self.color = color

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        t = 1 - self.life / self.max_life
        r = int(self.radius * (0.55 + 0.45 * t))
        alpha = int(210 * (1 - t) ** 0.8)
        cx, cy = self.x - cam_x, self.y - cam_y
        surf = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, max(0, alpha // 6)), (r + 6, r + 6), r)
        base = math.tau * t * 1.6
        for i in range(3):
            a0 = base + i * math.tau / 3
            pygame.draw.arc(surf, (*self.color, alpha), (6, 6, r * 2, r * 2), a0, a0 + 1.35, 10)
            pygame.draw.arc(surf, (255, 255, 240, alpha // 2), (12, 12, r * 2 - 12, r * 2 - 12),
                            a0, a0 + 1.35, 3)
        screen.blit(surf, (cx - r - 6, cy - r - 6))


class FrostShards:
    def __init__(self, x, y, radius, life=34, count=18):
        self.x, self.y = x, y
        self.life = life
        self.max_life = life
        self.particles = []
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            dist = random.uniform(radius * 0.35, radius)
            self.particles.append([self.x + math.cos(ang) * dist * 0.3,
                                   self.y + math.sin(ang) * dist * 0.3,
                                   math.cos(ang) * random.uniform(1.5, 4.5),
                                   math.sin(ang) * random.uniform(1.5, 4.5)])

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.94
            p[3] *= 0.94

    def draw(self, screen, cam_x, cam_y):
        t = self.life / self.max_life
        color = (170, 230, 255) if t > 0.5 else (225, 248, 255)
        for px, py, _, _ in self.particles:
            size = 5 if t > 0.45 else 4
            sx, sy = int(px - cam_x), int(py - cam_y)
            art.blit_glow(screen, sx, sy, 10, color, 28)
            pygame.draw.polygon(screen, color,
                                [(sx, sy - size), (sx - size // 2, sy),
                                 (sx, sy + size), (sx + size // 2, sy)])
            pygame.draw.line(screen, (255, 255, 255), (sx, sy - size), (sx, sy + size), 1)


class Beam:
    """跟宠攻击用的光束。"""

    def __init__(self, x1, y1, x2, y2, color=(160, 255, 210), life=9, width=4):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.color = color
        self.life = life
        self.max_life = life
        self.width = width

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        alpha = int(255 * self.life / self.max_life)
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(surf, (*self.color, alpha), (self.x1 - cam_x, self.y1 - cam_y),
                         (self.x2 - cam_x, self.y2 - cam_y), self.width)
        pygame.draw.circle(surf, (255, 255, 255, alpha), (int(self.x1 - cam_x), int(self.y1 - cam_y)), 4)
        screen.blit(surf, (0, 0))


class BossCast:
    """BOSS 施法动态效果：粒子向中心收束 + 能量环。"""

    def __init__(self, x, y, size, duration=34, color=(255, 120, 196)):
        self.x, self.y = x, y
        self.size = size
        self.life = duration
        self.max_life = duration
        self.color = color
        self.particles = []
        for _ in range(24):
            ang = random.uniform(0, math.tau)
            dist = random.uniform(size * 0.8, size * 2.0)
            self.particles.append([ang, dist])

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for p in self.particles:
            p[1] = max(8, p[1] - 4.6)

    def draw(self, screen, cam_x, cam_y):
        t = 1 - self.life / self.max_life
        cx, cy = self.x - cam_x, self.y - cam_y
        for ang, dist in self.particles:
            px = cx + math.cos(ang) * dist
            py = cy + math.sin(ang) * dist
            r = max(1, int(4 * (1 - t * 0.7)))
            pygame.draw.circle(screen, self.color, (int(px), int(py)), r)
        radius = int(self.size * (1.7 - 0.9 * t))
        surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
        alpha = int(230 * (1 - t))
        pygame.draw.circle(surf, (*self.color, alpha), (radius + 5, radius + 5), radius, 5)
        pygame.draw.circle(surf, (255, 255, 255, alpha // 2), (radius + 5, radius + 5),
                           max(4, radius - 14), 2)
        screen.blit(surf, (cx - radius - 5, cy - radius - 5))


class SparkBurst:
    """命中火花：四散的小光点。"""

    def __init__(self, x, y, color=(255, 220, 140), count=9, speed=3.4,
                 life=18, size=3, gravity=0.22):
        self.parts = []
        for i in range(count):
            ang = math.tau * i / count + random.uniform(-0.3, 0.3)
            sp = speed * random.uniform(0.55, 1.25)
            self.parts.append([x, y, math.cos(ang) * sp, math.sin(ang) * sp,
                               random.uniform(0.6, 1.3)])
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for pt in self.parts:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += self.gravity
            pt[2] *= 0.94

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        col = self.color
        for x, y, _vx, _vy, s in self.parts:
            r = max(1, int(self.size * s * k))
            surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*col, int(230 * k)), (r + 1, r + 1), r)
            pygame.draw.circle(surf, (255, 255, 255, int(120 * k)), (r + 1, r + 1), max(1, r - 1))
            screen.blit(surf, (int(x - cam_x) - r, int(y - cam_y) - r))
        if self.life > self.max_life * 0.55:
            r = int(16 * (1 - k) + 6)
            surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 255, int(150 * k)), (r + 2, r + 2), r, 2)
            screen.blit(surf, (int(self.parts[0][0] - cam_x) - r, int(self.parts[0][1] - cam_y) - r))


class SlashArc:
    """剑士挥砍：一道月牙形刀光。"""

    def __init__(self, x, y, direction=1, color=(255, 226, 180), radius=52, life=12):
        self.x, self.y = x, y
        self.direction = direction
        self.color = color
        self.radius = radius
        self.life = life
        self.max_life = life

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        r = int(self.radius * (1.25 - 0.35 * k))
        surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        cx = cy = r + 4
        start = -1.15 if self.direction > 0 else math.pi - 1.15
        end = 1.15 if self.direction > 0 else math.pi + 1.15
        alpha = int(230 * k)
        for w, a in ((12, alpha // 4), (8, alpha // 2), (4, alpha)):
            pygame.draw.arc(surf, (*self.color, a), (cx - r, cy - r, r * 2, r * 2),
                            start, end, w)
        for i in range(4):
            trail_r = max(8, r - 10 - i * 8)
            pygame.draw.arc(surf, (255, 255, 255, max(24, alpha // (5 + i))),
                            (cx - trail_r, cy - trail_r, trail_r * 2, trail_r * 2),
                            start, end, 2)
        # 刀尖亮光
        tip_ang = end if self.direction > 0 else start
        tx = cx + math.cos(tip_ang) * r
        ty = cy + math.sin(tip_ang) * r
        pygame.draw.circle(surf, (255, 255, 255, int(220 * k)), (int(tx), int(ty)), 4)
        screen.blit(surf, (int(self.x - cam_x) - cx, int(self.y - cam_y) - cy))


class CastCircle:
    """施法：脚下展开的魔法阵。"""

    def __init__(self, x, y, color=(150, 200, 255), life=20):
        self.x, self.y = x, y
        self.color = color
        self.life = life
        self.max_life = life

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        t = 1 - k
        r = int(18 + 40 * t)
        surf = pygame.Surface((r * 2 + 10, (r + 8) * 2 + 10), pygame.SRCALPHA)
        cx, cy = r + 5, r + 13
        alpha = int(220 * k)
        pygame.draw.ellipse(surf, (*self.color, alpha), (cx - r, cy - r // 3, r * 2, r // 2), 2)
        pygame.draw.ellipse(surf, (*self.color, alpha // 2), (cx - r // 2, cy - r // 5, r, r // 3), 2)
        pygame.draw.ellipse(surf, (255, 255, 255, alpha // 4),
                            (cx - r + 10, cy - r // 3 + 4, r * 2 - 20, max(8, r // 2 - 8)), 1)
        for i in range(6):
            ang = math.tau * i / 6 + t * 2.2
            px = cx + math.cos(ang) * r * 0.8
            py = cy + math.sin(ang) * r * 0.28
            pygame.draw.circle(surf, (255, 255, 255, alpha), (int(px), int(py)), 2)
        for i in range(4):
            ang = math.tau * i / 4 - t * 2.5
            px = cx + math.cos(ang) * r * 0.45
            py = cy + math.sin(ang) * r * 0.16
            pygame.draw.rect(surf, (*self.color, alpha // 2), (int(px) - 2, int(py) - 2, 4, 4), 1)
        pygame.draw.circle(surf, (*self.color, alpha), (cx, int(cy - r * 0.35)), 3)
        screen.blit(surf, (int(self.x - cam_x) - cx, int(self.y - cam_y) - cy))


class LightningFX:
    """连锁闪电：折线 + 分叉。"""

    def __init__(self, x1, y1, x2, y2, color=(180, 220, 255), life=12, segments=8):
        self.pts = [(x1, y1)]
        dx, dy = (x2 - x1) / segments, (y2 - y1) / segments
        for i in range(1, segments):
            self.pts.append((x1 + dx * i + random.uniform(-9, 9),
                             y1 + dy * i + random.uniform(-9, 9)))
        self.pts.append((x2, y2))
        self.branches = []
        for i in range(1, len(self.pts) - 1, 2):
            bx, by = self.pts[i]
            ang = random.uniform(0, math.tau)
            self.branches.append(((bx, by),
                                  (bx + math.cos(ang) * 16, by + math.sin(ang) * 16)))
        self.color = color
        self.life = life
        self.max_life = life

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        width = 1 + int(3 * k)
        pts = [(x - cam_x, y - cam_y) for x, y in self.pts]
        for p in pts[1:-1]:
            art.blit_glow(screen, int(p[0]), int(p[1]), 10, self.color, int(24 * k))
        pygame.draw.lines(screen, (255, 255, 255), False, pts, width + 1)
        pygame.draw.lines(screen, self.color, False, pts, width)
        for (ax, ay), (bx, by) in self.branches:
            pygame.draw.line(screen, self.color, (ax - cam_x, ay - cam_y),
                             (bx - cam_x, by - cam_y), 1)
        end = pts[-1]
        art.blit_glow(screen, int(end[0]), int(end[1]), 18, self.color, 70)


class GroundCracks:
    """裂地斩：地面放射状裂缝 + 扬尘。"""

    def __init__(self, x, y, radius, color=(255, 190, 120), life=28, count=10):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.life = life
        self.max_life = life
        self.cracks = []
        for i in range(count):
            ang = math.tau * i / count + random.uniform(-0.18, 0.18)
            seg = []
            r = 16
            px, py = x + math.cos(ang) * r, y + math.sin(ang) * r * 0.45
            seg.append((px, py))
            steps = random.randint(3, 5)
            for _ in range(steps):
                r += random.uniform(14, 30)
                wob = random.uniform(-0.2, 0.2)
                px = x + math.cos(ang + wob) * r
                py = y + math.sin(ang + wob) * r * 0.45
                seg.append((px, py))
            self.cracks.append(seg)
        self.dust = [[x + random.uniform(-radius, radius),
                      y + random.uniform(-radius * 0.4, radius * 0.4),
                      random.uniform(-0.6, 0.6), random.uniform(-1.6, -0.4),
                      random.uniform(2, 4)] for _ in range(14)]

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for d in self.dust:
            d[0] += d[2]
            d[1] += d[3]
            d[3] += 0.05

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        for seg in self.cracks:
            pts = [(px - cam_x, py - cam_y) for px, py in seg]
            pygame.draw.lines(screen, (60, 30, 20), False, pts, 4)
            pygame.draw.lines(screen, (*self.color, ), False, pts, 2)
            if k > 0.6:
                pygame.draw.lines(screen, (255, 240, 200), False, pts, 1)
            elif k > 0.25:
                pygame.draw.lines(screen, (255, 180, 100), False, pts, 1)
        for dx, dy, _vx, _vy, r in self.dust:
            a = int(150 * k)
            surf = pygame.Surface((int(r * 2) + 4, int(r * 2) + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 170, 140, a), (int(r) + 2, int(r) + 2), int(r))
            screen.blit(surf, (int(dx - cam_x) - r, int(dy - cam_y) - r))


class ArrowStormFX:
    """箭幕：从天而降的箭雨。"""

    def __init__(self, x, y, radius, color=(200, 255, 210), life=30, count=18):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.life = life
        self.max_life = life
        self.arrows = []
        for _ in range(count):
            ax = x + random.uniform(-radius, radius)
            ay = y + random.uniform(-radius * 0.6, radius * 0.6)
            self.arrows.append([ax, ay, random.randint(0, 18)])

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for a in self.arrows:
            if a[2] > 0:
                a[2] -= 1

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        for ax, ay, delay in self.arrows:
            if delay > 0:
                continue
            sx, sy = ax - cam_x, ay - cam_y
            art.blit_glow(screen, int(sx), int(sy - 12), 12, self.color, int(28 * k))
            pygame.draw.line(screen, self.color, (sx, sy - 46), (sx, sy - 10), 2)
            pygame.draw.polygon(screen, (255, 255, 255),
                                [(sx, sy), (sx - 4, sy - 10), (sx + 4, sy - 10)])
        # 地面圈
        surf = pygame.Surface((self.radius * 2 + 8, self.radius + 8), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (*self.color, int(90 * k)),
                            (4, 4, self.radius * 2, self.radius), 2)
        screen.blit(surf, (self.x - cam_x - self.radius - 4, self.y - cam_y - self.radius // 2 - 4))


class BossSkillFX:
    """BOSS 技能专属特效（不同技能不同表现）。"""

    def __init__(self, kind, x, y, radius, color=(255, 170, 90), life=34):
        self.kind = kind
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.life = life
        self.max_life = life
        self.parts = []
        if kind == "slam":
            for i in range(26):
                ang = random.uniform(0, math.tau)
                self.parts.append([math.cos(ang) * random.uniform(20, radius),
                                   math.sin(ang) * random.uniform(10, radius * 0.5),
                                   random.uniform(1.5, 4.5), random.randint(10, 30)])
        elif kind in ("thorn_ring", "spore_ring", "ice_nova"):
            n = 14 if kind != "spore_ring" else 10
            for i in range(n):
                ang = math.tau * i / n
                self.parts.append([math.cos(ang), math.sin(ang), 0, i])
        elif kind == "bone_volley":
            for i in range(10):
                ang = math.tau * i / 10
                self.parts.append([math.cos(ang), math.sin(ang), 0, i])
        elif kind == "charge":
            for i in range(10):
                self.parts.append([random.uniform(-radius, radius),
                                   random.uniform(-radius * 0.4, radius * 0.4), 0, i])
        else:  # summon
            for i in range(18):
                ang = random.uniform(0, math.tau)
                self.parts.append([math.cos(ang) * random.uniform(20, radius),
                                   -random.uniform(10, 120), random.uniform(1, 3), i])

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1
        for p in self.parts:
            if self.kind == "slam":
                p[0] += p[2] * 0.6
                p[1] += p[2] * 0.3
            elif self.kind == "summon":
                p[1] -= p[2]

    def draw(self, screen, cam_x, cam_y):
        k = max(0.0, self.life / self.max_life)
        t = 1 - k
        cx, cy = self.x - cam_x, self.y - cam_y
        if self.kind == "slam":
            r = int(self.radius * min(1.0, t * 2))
            surf = pygame.Surface((r * 2 + 8, r + 8), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (*self.color, int(220 * k)), (4, 4, r * 2, r), 5)
            pygame.draw.ellipse(surf, (255, 240, 200, int(140 * k)), (4 + r // 3, 4 + r // 4,
                                                                     r, r // 2), 2)
            screen.blit(surf, (cx - r - 4, cy - r // 2 - 4))
            for px, py, _v, _d in self.parts:
                pygame.draw.rect(screen, (150, 120, 100), (cx + px, cy + py, 4, 4))
        elif self.kind == "thorn_ring":
            for dx, dy, _a, _d in self.parts:
                r = 120 * min(1.0, t * 2.2)
                tx, ty = cx + dx * r, cy + dy * r * 0.55
                pygame.draw.polygon(screen, (210, 170, 90),
                                    [(tx, ty - 16), (tx - 5, ty + 4), (tx + 5, ty + 4)])
        elif self.kind == "spore_ring":
            for dx, dy, _a, _d in self.parts:
                r = 30 + 100 * t
                px, py = cx + dx * r, cy + dy * r * 0.5
                art.blit_glow(screen, int(px), int(py), 26, (150, 230, 150), int(70 * k))
        elif self.kind == "ice_nova":
            for dx, dy, _a, _d in self.parts:
                r = 40 + 130 * t
                px, py = cx + dx * r, cy + dy * r * 0.5
                pygame.draw.polygon(screen, (150, 220, 255),
                                    [(px, py - 12), (px - 5, py + 5), (px + 5, py + 5)])
            surf = pygame.Surface((260, 130), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (120, 200, 255, int(160 * k)), (10, 10, 240, 110), 4)
            screen.blit(surf, (cx - 130, cy - 65))
        elif self.kind == "bone_volley":
            for dx, dy, _a, _d in self.parts:
                r = 30 + 160 * t
                px, py = cx + dx * r, cy + dy * r
                pygame.draw.line(screen, (230, 226, 210), (px, py),
                                 (px + dx * 16, py + dy * 16), 3)
        elif self.kind == "charge":
            for px, py, _a, _d in self.parts:
                x1 = cx + px - 50 * t
                pygame.draw.line(screen, (*self.color, ), (x1, cy + py),
                                 (x1 + 34, cy + py), 2)
        else:  # summon
            surf = pygame.Surface((140, 240), pygame.SRCALPHA)
            pygame.draw.rect(surf, (190, 130, 255, int(120 * k)), (40, 20, 60, 200))
            pygame.draw.rect(surf, (230, 180, 255, int(180 * k)), (56, 20, 28, 200))
            screen.blit(surf, (cx - 70, cy - 200))
            pygame.draw.ellipse(screen, (200, 140, 255), (cx - 60, cy - 20, 120, 44), 3)
            for px, py, _v, _d in self.parts:
                pygame.draw.circle(screen, (230, 190, 255), (int(cx + px), int(cy + py)), 2)


class MeteorStrike:
    """陨石术：从天而降的陨石 + 落地爆炸。"""

    def __init__(self, x, y, radius, color=(255, 140, 90), life=36):
        self.x, self.y = x, y
        self.radius = radius
        self.color = color
        self.life = life
        self.max_life = life

    @property
    def dead(self):
        return self.life <= 0

    def update(self):
        self.life -= 1

    def draw(self, screen, cam_x, cam_y):
        t = 1 - self.life / self.max_life
        cx, cy = self.x - cam_x, self.y - cam_y
        fall = min(1.0, t * 1.8)
        my = cy - 320 * (1 - fall)
        r = 16
        art.blit_glow(screen, int(cx), int(my), 46, self.color, 90)
        pygame.draw.circle(screen, _shade(self.color, 0.5), (int(cx), int(my)), r)
        pygame.draw.circle(screen, self.color, (int(cx), int(my)), r - 4)
        pygame.draw.circle(screen, (255, 240, 200), (int(cx - 3), int(my - 3)), 4)
        # 尾迹
        for i in range(4):
            ty = my - 14 - i * 10
            pygame.draw.circle(screen, (*self.color, 120), (int(cx), int(ty)), max(1, 7 - i))
        if fall >= 1:
            k = (t - 0.55) / 0.45
            rr = int(self.radius * min(1.0, k * 1.4))
            surf = pygame.Surface((rr * 2 + 12, rr * 2 + 12), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, int(200 * (1 - k))), (rr + 6, rr + 6), rr, 8)
            pygame.draw.circle(surf, (255, 240, 180, int(160 * (1 - k))), (rr + 6, rr + 6),
                               max(2, rr // 2), 3)
            screen.blit(surf, (cx - rr - 6, cy - rr - 6))


# --------------------------------------------------------------------------
# 玩家
# --------------------------------------------------------------------------
class Player:
    CRIT_MULT = 1.8

    def __init__(self, x, y, weapon_type):
        self.rect = pygame.Rect(x, y, 32, 48)
        self.base_max_hp = MAX_HP
        self.invincible_timer = 0

        self.level = 1
        self.exp = 0
        self.next_level_exp = 50
        self.energy = 0

        self.weapon_type = weapon_type

        self.weapon_quality = Q_WHITE
        self.armor_quality = "none"
        self.helmet_quality = "none"
        self.boots_quality = "none"
        self.pants_quality = "none"
        self.bracelet_quality = "none"
        self.weapon_set = "forest"
        self.armor_set = "forest"
        self.helmet_set = "forest"
        self.boots_set = "forest"
        self.pants_set = "forest"
        self.bracelet_set = "forest"
        self.weapon_hidden = None
        self.armor_hidden = None
        self.helmet_hidden = None
        self.boots_hidden = None
        self.pants_hidden = None
        self.bracelet_hidden = None

        self.inventory_weapons = []
        self.inventory_armors = []
        self.inventory_helmets = []
        self.inventory_boots = []
        self.inventory_pants = []
        self.inventory_bracelets = []
        self.pet_state = {"level": 1, "exp": 0}
        self.hp = self.max_hp

        self.facing_right = True
        self.aim_dx = 1.0
        self.aim_dy = 0.0
        self.aim_lock_timer = 0
        self.z = 0
        self.vz = 0
        self.jump_count = 0

        self.speed = PLAYER_SPEED + (1.5 if weapon_type == WEAPON_BOW else 0)

        self.is_attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_rect = pygame.Rect(0, 0, 0, 0)
        self.projectiles = []

        self.fx_queue = []
        self.chill_timer = 0
        self.freeze_timer = 0
        self.burn_timer = 0
        self.env_speed_mult = 1.0
        self.skill_cds = [0, 0, 0]
        self.skill_cd_maxs = [SKILL_BY_WEAPON[weapon_type]["cd"],
                              SKILL2_BY_WEAPON[weapon_type]["cd"],
                              SKILL3_BY_WEAPON[weapon_type]["cd"]]
        self.skill_cast_timer = 0
        self.anim = 0
        self.speed_bonus_timer = 0
        self.pet_haste = False
        self.floor_z = 0                 # 当前脚下平台高度
        self.bag = {k: 0 for k in ITEM_SLOTS}

    # ---------------- 属性 ----------------
    @property
    def max_hp(self):
        return self.base_max_hp + PANTS_HP.get(self.pants_quality, 0)

    @property
    def defense(self):
        return (ARMOR_DEF.get(self.armor_quality, 0) + HELMET_DEF.get(self.helmet_quality, 0)
                + PANTS_DEF.get(self.pants_quality, 0) + BOOTS_DEF.get(self.boots_quality, 0))

    @property
    def magic_resist(self):
        return (ARMOR_MRES.get(self.armor_quality, 0) + HELMET_MRES.get(self.helmet_quality, 0)
                + BRACELET_MRES.get(self.bracelet_quality, 0))

    @property
    def move_speed(self):
        return self.speed * (1 + BOOTS_SPEED.get(self.boots_quality, 0))

    @property
    def pet_stage_name(self):
        level = self.pet_state.get("level", 1)
        return PET_STAGE_NAMES[min(PET_MAX_STAGE, (level - 1) // 3)]

    @property
    def hp_ratio(self):
        return max(0.0, self.hp / self.max_hp)

    @property
    def skill_info(self):
        return SKILL_BY_WEAPON[self.weapon_type]

    @property
    def skill_info2(self):
        return SKILL2_BY_WEAPON[self.weapon_type]

    def skill_at(self, slot):
        if slot == 0:
            return self.skill_info
        if slot == 1:
            return self.skill_info2
        return SKILL3_BY_WEAPON[self.weapon_type]

    def skill_cost(self, slot):
        return (SKILL_COST_PRIMARY, SKILL_COST_SECONDARY, SKILL_COST_TERTIARY)[slot]

    def skill_ready_at(self, slot):
        return self.skill_cds[slot] <= 0 and self.energy >= self.skill_cost(slot)

    @property
    def skill_ready(self):
        return self.skill_ready_at(0)

    @property
    def skill_cd(self):
        return self.skill_cds[0]

    @property
    def skill_cd_max(self):
        return self.skill_cd_maxs[0]

    # ---------------- 动作 ----------------
    def jump(self):
        if self.jump_count < 2:
            self.vz = JUMP_VELOCITY
            self.jump_count += 1
            audio.play("jump", 0.5)

    def move(self, dx, dy, walls):
        if self.freeze_timer > 0:
            self._acc_x = getattr(self, "_acc_x", 0.0) * 0.35
            self._acc_y = getattr(self, "_acc_y", 0.0) * 0.35
            return
        if self.aim_lock_timer <= 0:
            if dx > 0:
                self.set_aim_vector(1, 0, lock=0)
            if dx < 0:
                self.set_aim_vector(-1, 0, lock=0)

        speed = self.move_speed * (SPEED_POTION_MULT if self.speed_bonus_timer > 0 else 1.0)
        speed *= self.env_speed_mult
        if self.chill_timer > 0:
            speed *= 0.55
        if self.has_hidden("swift"):
            speed *= 1.08
        assist = 6

        def move_axis(axis, amount):
            if amount == 0:
                return False
            if axis == "x":
                self.rect.x += amount
            else:
                self.rect.y += amount
            for wall in walls:
                if self.rect.colliderect(wall):
                    if axis == "x":
                        if amount > 0:
                            self.rect.right = wall.left
                        else:
                            self.rect.left = wall.right
                    else:
                        if amount > 0:
                            self.rect.bottom = wall.top
                        else:
                            self.rect.top = wall.bottom
                    return True
            return False

        def try_corner_slide(primary_axis, primary_amount, secondary_axis, secondary_dir):
            if primary_amount == 0 or secondary_dir == 0:
                return False
            start = self.rect.topleft
            for offset in range(1, assist + 1):
                if secondary_axis == "y":
                    self.rect.y += secondary_dir * offset
                else:
                    self.rect.x += secondary_dir * offset
                blocked = any(self.rect.colliderect(w) for w in walls)
                if blocked:
                    self.rect.topleft = start
                    continue
                if not move_axis(primary_axis, primary_amount):
                    return True
                self.rect.topleft = start
            self.rect.topleft = start
            return False

        # 用小数累积，避免每帧取整把 8% 之类的加成抹掉
        self._acc_x = getattr(self, "_acc_x", 0.0) + dx * speed
        step_x = int(self._acc_x)
        self._acc_x -= step_x
        blocked_x = move_axis("x", step_x)
        if blocked_x:
            try_corner_slide("x", step_x, "y", -1 if dy < 0 else (1 if dy > 0 else 0))

        self._acc_y = getattr(self, "_acc_y", 0.0) + dy * speed
        step_y = int(self._acc_y)
        self._acc_y -= step_y
        blocked_y = move_axis("y", step_y)
        if blocked_y:
            try_corner_slide("y", step_y, "x", -1 if dx < 0 else (1 if dx > 0 else 0))

    def set_aim_vector(self, dx, dy, lock=18):
        dist = math.hypot(dx, dy)
        if dist <= 0.001:
            return
        self.aim_dx = dx / dist
        self.aim_dy = dy / dist
        if abs(self.aim_dx) > 0.08:
            self.facing_right = self.aim_dx >= 0
        self.aim_lock_timer = max(self.aim_lock_timer, lock)

    def set_aim_towards(self, x, y, lock=18):
        self.set_aim_vector(x - self.rect.centerx, y - self.rect.centery, lock)

    def aim_sign(self):
        return 1 if self.aim_dx >= 0 else -1

    def pick_target(self, level, radius=520):
        if level is None:
            return None
        best = None
        best_score = 10 ** 9
        px, py = self.rect.center
        aim_bias = self.aim_lock_timer > 0 or abs(self.aim_dy) > 0.18
        for enemy in level.enemies:
            if enemy.dead:
                continue
            dx = enemy.rect.centerx - px
            dy = enemy.rect.centery - py
            dist = math.hypot(dx, dy)
            if dist > radius:
                continue
            if not aim_bias:
                score = dist
            else:
                ndx, ndy = dx / max(1.0, dist), dy / max(1.0, dist)
                align = ndx * self.aim_dx + ndy * self.aim_dy
                front_bonus = max(0.0, align) * 110.0
                rear_penalty = 90.0 if align < -0.2 else 0.0
                vertical_penalty = abs(dy) * 0.08
                score = dist + vertical_penalty + rear_penalty - front_bonus
            if score < best_score:
                best_score = score
                best = enemy
        return best

    def auto_aim(self, level, radius=520):
        target = self.pick_target(level, radius)
        if target is not None:
            self.set_aim_towards(target.rect.centerx, target.rect.centery, lock=26)
        return target

    def _shot_unit(self, min_horizontal=0.45):
        ax, ay = self.aim_dx, self.aim_dy
        sign = 1 if ax >= 0 else -1
        ax = abs(ax)
        if ax < min_horizontal:
            ax = min_horizontal
        norm = math.hypot(ax, ay)
        if norm <= 0.001:
            return float(sign), 0.0
        return sign * ax / norm, ay / norm

    QUALITY_WEIGHT = {Q_WHITE: 0.2, Q_SILVER: 0.4, Q_PURPLE: 0.6,
                      Q_GOLD: 0.8, Q_RED: 1.0}

    def hidden_effects(self):
        out = []
        for kind in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
            eff = getattr(self, kind + "_hidden", None)
            if eff:
                out.append(eff)
        return out

    def has_hidden(self, key):
        return key in self.hidden_effects()

    def status_resist(self, set_key):
        """穿该大关专属套装越多、品质越高，负面效果越短。"""
        total = 0.0
        for kind in ("weapon", "armor", "helmet", "boots", "pants", "bracelet"):
            q = getattr(self, kind + "_quality", "none")
            sk = getattr(self, kind + "_set", "forest")
            if sk == set_key and q in self.QUALITY_WEIGHT:
                total += self.QUALITY_WEIGHT[q] * 0.12
        return min(0.72, total)

    def freeze(self, frames):
        self.freeze_timer = max(self.freeze_timer, frames)

    @property
    def crit_chance(self):
        bonus = {Q_SILVER: 0.01, Q_PURPLE: 0.02, Q_GOLD: 0.035, Q_RED: 0.05}
        extra = 0.08 if self.has_hidden("crit") else 0.0
        return min(0.7, 0.06 + self.level * 0.005 + bonus.get(self.bracelet_quality, 0.0) + extra)

    def attack(self, level=None):
        if self.attack_cooldown > 0:
            return
        if self.weapon_type == WEAPON_SWORD:
            self.auto_aim(level, 120)
        else:
            self.auto_aim(level, 560)
        self.is_attacking = True
        haste = (1 - PET_HASTE) if self.pet_haste else 1.0

        if self.weapon_type == WEAPON_SWORD:
            direction = self.aim_sign()
            self.attack_timer = 12
            self.attack_cooldown = int(22 * haste)
            audio.play("slash")
            self.fx_queue.append(("slash", self.rect.centerx + 26 * direction,
                                  self.rect.centery, direction))
            bonus_range = (self.level // 2) * 5
            if direction > 0:
                self.attack_rect = pygame.Rect(self.rect.right, self.rect.y, 40 + bonus_range, 48)
            else:
                self.attack_rect = pygame.Rect(self.rect.left - 40 - bonus_range, self.rect.y, 40 + bonus_range, 48)
        elif self.weapon_type == WEAPON_BOW:
            direction = self.aim_sign()
            self.attack_timer = 10
            self.attack_cooldown = int(18 * haste)
            self.spawn_projectile("arrow", self.pick_target(level, 640))
            audio.play("shot")
            self.fx_queue.append(("shot", self.rect.centerx + 18 * direction,
                                  self.rect.centery - 2, direction))
        elif self.weapon_type == WEAPON_STAFF:
            self.auto_aim(level, 620)
            self.attack_timer = 15
            self.attack_cooldown = int(28 * haste)
            self.spawn_projectile("magic", self.pick_target(level, 700))
            audio.play("spell")
            self.fx_queue.append(("cast_magic", self.rect.centerx, self.rect.bottom - 2,
                                  self.aim_sign()))

        self.energy = min(MAX_ENERGY, self.energy + 15 + (8 if self.has_hidden("mana") else 0))

    def spawn_projectile(self, p_type, target=None):
        speed = 13 if p_type == "arrow" else (10 if p_type == "magic" else 11)
        shot_x, shot_y = self._shot_unit(0.1 if p_type == "magic" else 0.14)
        if target is not None:
            tx = target.rect.centerx - self.rect.centerx
            ty = target.rect.centery - self.rect.centery
            dist = math.hypot(tx, ty)
            if dist > 1.0:
                shot_x = tx / dist
                shot_y = ty / dist
                self.set_aim_vector(shot_x, shot_y, lock=28)
        direction = 1 if shot_x >= 0 else -1
        proj_x = self.rect.right if direction > 0 else self.rect.left - 16
        proj_y = self.rect.centery - 4 + int(shot_y * 8)
        max_dist = (300 if p_type == "arrow" else 250) + (self.level - 1) * 40
        homing = 0.12 if (p_type == "arrow" and target is not None) else 0.0
        if p_type == "magic":
            homing = 0.24 if target is not None else 0.14
        self.projectiles.append(Projectile(
            proj_x, proj_y, direction, self.get_damage(), p_type, max_dist,
            vy=shot_y * speed, vx=shot_x * speed, target=target,
            homing=homing, hit_pad=10 if p_type == "magic" else 6))

    def try_skill(self, slot=0):
        cost = self.skill_cost(slot)
        if self.skill_cds[slot] > 0 or self.energy < cost:
            return None
        skill = self.skill_at(slot)
        self.energy -= cost
        self.skill_cds[slot] = skill["cd"]
        self.skill_cd_maxs[slot] = skill["cd"]
        self.skill_cast_timer = 16
        self.is_attacking = False
        return skill

    def spawn_volley(self, count, damage, spread=0.34):
        speed = 11
        base_x_dir, base_y_dir = self._shot_unit(0.14)
        perp_x, perp_y = -base_y_dir, base_x_dir
        for i in range(count):
            offset = i - (count - 1) / 2
            vx = base_x_dir + perp_x * offset * spread
            vy = base_y_dir + perp_y * offset * spread
            norm = math.hypot(vx, vy)
            if norm <= 0.001:
                vx, vy = base_x_dir, base_y_dir
                norm = 1.0
            vx /= norm
            vy /= norm
            direction = 1 if vx >= 0 else -1
            base_x = self.rect.right if direction > 0 else self.rect.left - 16
            base_y = self.rect.centery - 4 + int(vy * 8)
            self.projectiles.append(Projectile(
                base_x, base_y, direction, damage, "arrow",
                max_dist=430, vy=vy * speed, pierce=3, tint=(190, 255, 190), vx=vx * speed))

    def get_damage(self):
        base = INIT_SWORD_DMG if self.weapon_type == WEAPON_SWORD else (
            INIT_BOW_DMG if self.weapon_type == WEAPON_BOW else INIT_STAFF_DMG)
        base += (self.level - 1) * DMG_PER_LEVEL[self.weapon_type]

        base += BRACELET_ATK.get(self.bracelet_quality, 0)

        if self.weapon_quality == Q_SILVER:
            base += DMG_BONUS_SILVER
        elif self.weapon_quality == Q_PURPLE:
            base += DMG_BONUS_PURPLE
        elif self.weapon_quality == Q_GOLD:
            base += DMG_BONUS_GOLD
        elif self.weapon_quality == Q_RED:
            base += DMG_BONUS_RED

        # 剑士：血越少伤害越高（最多 +30%）
        if self.weapon_type == WEAPON_SWORD:
            missing_ratio = 1 - self.hp_ratio
            base = int(base * (1 + missing_ratio * 0.3))

        return max(1, int(base))

    def take_damage(self, raw_dmg, dmg_type=DMG_PHYS):
        """返回实际掉血量（0 表示无敌帧内没打中）。"""
        if self.invincible_timer > 0:
            return 0
        if self.has_hidden("guard"):
            raw_dmg *= 0.92
        resist = self.defense if dmg_type == DMG_PHYS else self.magic_resist
        mult = 1 - resist / (resist + DEF_K)
        final = max(1, int(round(raw_dmg * mult)))
        self.hp -= final
        if self.hp < 0:
            self.hp = 0
        self.invincible_timer = INVINCIBLE_FRAMES
        audio.play("hurt", 0.8)
        return final

    def to_dict(self):
        return {
            "level": self.level, "exp": self.exp, "next_level_exp": self.next_level_exp,
            "base_max_hp": self.base_max_hp, "hp": self.hp, "energy": self.energy,
            "weapon_type": self.weapon_type,
            "weapon_quality": self.weapon_quality, "armor_quality": self.armor_quality,
            "helmet_quality": self.helmet_quality, "boots_quality": self.boots_quality,
            "pants_quality": self.pants_quality, "bracelet_quality": self.bracelet_quality,
            "weapon_set": self.weapon_set, "armor_set": self.armor_set,
            "helmet_set": self.helmet_set, "boots_set": self.boots_set,
            "pants_set": self.pants_set, "bracelet_set": self.bracelet_set,
            "weapon_hidden": self.weapon_hidden, "armor_hidden": self.armor_hidden,
            "helmet_hidden": self.helmet_hidden, "boots_hidden": self.boots_hidden,
            "pants_hidden": self.pants_hidden, "bracelet_hidden": self.bracelet_hidden,
            "inventory_weapons": list(self.inventory_weapons),
            "inventory_armors": list(self.inventory_armors),
            "inventory_helmets": list(self.inventory_helmets),
            "inventory_boots": list(self.inventory_boots),
            "inventory_pants": list(self.inventory_pants),
            "inventory_bracelets": list(self.inventory_bracelets),
            "bag": dict(self.bag),
            "pet_state": dict(self.pet_state),
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        p = cls(0, 0, data.get("weapon_type", WEAPON_SWORD))
        for key in ("level", "exp", "next_level_exp", "base_max_hp", "energy",
                    "weapon_quality", "armor_quality", "helmet_quality",
                    "boots_quality", "pants_quality", "bracelet_quality",
                    "weapon_set", "armor_set", "helmet_set",
                    "boots_set", "pants_set", "bracelet_set",
                    "weapon_hidden", "armor_hidden", "helmet_hidden",
                    "boots_hidden", "pants_hidden", "bracelet_hidden"):
            if key in data:
                setattr(p, key, data[key])
        for key in ("inventory_weapons", "inventory_armors", "inventory_helmets",
                    "inventory_boots", "inventory_pants", "inventory_bracelets"):
            if key in data:
                entries = []
                for entry in data[key]:
                    if isinstance(entry, (list, tuple)) and len(entry) == 3:
                        entries.append((entry[0], entry[1], entry[2]))
                    elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                        entries.append((entry[0], entry[1], None))
                    else:
                        entries.append((entry, "forest", None))
                setattr(p, key, entries)
        if isinstance(data.get("bag"), dict):
            for k in p.bag:
                p.bag[k] = int(data["bag"].get(k, 0))
        if isinstance(data.get("pet_state"), dict):
            p.pet_state = {"level": int(data["pet_state"].get("level", 1)),
                           "exp": int(data["pet_state"].get("exp", 0))}
        p.hp = min(int(data.get("hp", p.max_hp)), p.max_hp)
        return p

    def add_item(self, kind, count=1):
        if kind in self.bag:
            self.bag[kind] += count
            return True
        return False

    def heal(self, amount):
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        gained = int(round(self.hp - before))
        if gained > 0:
            audio.play("heal", 0.5)
        return gained

    def gain_exp(self, amount):
        if self.level >= MAX_PLAYER_LEVEL:
            self.exp = 0
            return
        self.exp += amount
        while self.exp >= self.next_level_exp and self.level < MAX_PLAYER_LEVEL:
            self.exp -= self.next_level_exp
            self.level += 1
            self.next_level_exp = 50 + (self.level - 1) * 25
            self.base_max_hp += HP_PER_LEVEL
            self.hp = self.max_hp
        if self.level >= MAX_PLAYER_LEVEL:
            self.level = MAX_PLAYER_LEVEL
            self.exp = 0
            self.next_level_exp = 1

    def update(self, walls):
        self.anim += 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.aim_lock_timer > 0:
            self.aim_lock_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        for i in range(3):
            if self.skill_cds[i] > 0:
                self.skill_cds[i] -= 1
        if self.skill_cast_timer > 0:
            self.skill_cast_timer -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        else:
            self.is_attacking = False
        if self.speed_bonus_timer > 0:
            self.speed_bonus_timer -= 1
        if self.chill_timer > 0:
            self.chill_timer -= 1
        if self.freeze_timer > 0:
            self.freeze_timer -= 1

        if self.z > self.floor_z or self.vz > 0:
            self.z += self.vz
            self.vz -= GRAVITY
            if self.z <= self.floor_z:
                self.z = self.floor_z
                self.vz = 0
                self.jump_count = 0

        for p in self.projectiles[:]:
            p.update(walls)
            if p.dead:
                self.projectiles.remove(p)

    # ---------------- 绘制 ----------------
    def draw(self, screen, cam_x, cam_y):
        x = self.rect.x - cam_x
        y = self.rect.y - cam_y - self.z

        art.shadow(screen, x + 1, self.rect.y - cam_y + 40 + min(self.z, 18), 30, 10, 90)

        if self.speed_bonus_timer > 0:
            art.blit_glow(screen, x + 16, y + 34, 34, (255, 214, 110), 55)

        if self.skill_ready:
            art.blit_glow(screen, x + 16, y + 30, 30, self.skill_info["color"], 46)
        if self.skill_cast_timer > 0:
            art.blit_glow(screen, x + 16, y + 26, 46, self.skill_info["color"], 80)

        if self.invincible_timer > 0 and (self.invincible_timer // 4) % 2 == 0:
            return

        armor_color = (72, 132, 204) if self.armor_quality == "none" else Q_COLOR[self.armor_quality]
        head_color = HAIR_COLOR if self.helmet_quality == "none" else Q_COLOR[self.helmet_quality]
        dominant_set = self.armor_set if self.armor_quality != "none" else self.weapon_set
        spr = art.player_sprite(armor_color, head_color, self.weapon_type, dominant_set)
        if self.freeze_timer > 0:
            spr = art.tint(spr, (170, 226, 255, 150))

        bob = 0 if (self.z > 0 or not self.is_attacking) else int(math.sin(self.anim * 0.35) * 1)
        sx = self.rect.centerx - cam_x - spr.get_width() // 2
        sy = y + 48 - spr.get_height() + 1 + bob
        screen.blit(spr, (sx, sy))
        art.draw_player_hat(screen, sx, sy, self.weapon_type, head_color)
        self._draw_weapon(screen, sx, sy)

        for p in self.projectiles:
            p.draw(screen, cam_x, cam_y)

    def _draw_weapon(self, screen, sx, sy):
        c_w = Q_COLOR.get(self.weapon_quality, (150, 150, 150))
        style = art.gear_style(self.weapon_set)
        trim = _light(style["trim"], 0.1)
        rune = style["rune"]
        right = self.facing_right
        hx = sx + (31 if right else 1)
        hy = sy + 12

        if self.weapon_type == WEAPON_SWORD:
            if self.is_attacking:
                progress = (12 - self.attack_timer) / 12.0
                surf = pygame.Surface((120, 120), pygame.SRCALPHA)
                start = -1.57 + progress * 2.0
                pygame.draw.arc(surf, (*trim, 180), (12, 12, 96, 96), start, start + 1.7, 11)
                pygame.draw.arc(surf, (*c_w, 220), (16, 16, 88, 88), start, start + 1.7, 8)
                pygame.draw.arc(surf, (255, 232, 246, 150), (22, 22, 76, 76), start, start + 1.7, 3)
                screen.blit(surf, (sx - 14, sy - 20))
            else:
                pygame.draw.rect(screen, _shade(c_w), (hx - 1, hy - 4, 7, 28))
                pygame.draw.rect(screen, c_w, (hx, hy - 5, 5, 26))
                pygame.draw.rect(screen, _light(c_w, 0.55), (hx + 1, hy - 4, 2, 21))
                pygame.draw.polygon(screen, trim, [(hx - 5, hy + 18), (hx + 10, hy + 18),
                                                   (hx + 7, hy + 22), (hx - 2, hy + 22)])
                if self.weapon_set == "forest":
                    pygame.draw.polygon(screen, style["trim"], [(hx + 2, hy - 12), (hx + 6, hy - 6), (hx - 1, hy - 5)])
                elif self.weapon_set == "ocean":
                    pygame.draw.circle(screen, style["rune"], (hx + 2, hy - 8), 3)
                elif self.weapon_set == "sky":
                    pygame.draw.line(screen, style["rune"], (hx - 2, hy + 1), (hx + 7, hy - 7), 2)
                else:
                    pygame.draw.rect(screen, style["trim"], (hx - 1, hy + 3, 7, 2))
                pygame.draw.rect(screen, (120, 72, 32), (hx, hy + 22, 5, 8))
                pygame.draw.rect(screen, rune, (hx + 1, hy + 24, 2, 2))
        elif self.weapon_type == WEAPON_BOW:
            bow_col = _light(trim, 0.08)
            if right:
                pygame.draw.lines(screen, _shade(bow_col), False,
                                  [(hx + 1, hy - 12), (hx + 10, hy - 4), (hx + 10, hy + 10),
                                   (hx + 1, hy + 20)], 4)
                pygame.draw.line(screen, (238, 238, 244), (hx + 1, hy - 11), (hx + 1, hy + 19), 1)
                pygame.draw.rect(screen, rune, (hx + 3, hy + 1, 10, 2))
            else:
                pygame.draw.lines(screen, _shade(bow_col), False,
                                  [(hx - 1, hy - 12), (hx - 10, hy - 4), (hx - 10, hy + 10),
                                   (hx - 1, hy + 20)], 4)
                pygame.draw.line(screen, (238, 238, 244), (hx - 1, hy - 11), (hx - 1, hy + 19), 1)
                pygame.draw.rect(screen, rune, (hx - 9, hy + 1, 10, 2))
            if self.weapon_set == "forest":
                pygame.draw.polygon(screen, style["trim"], [(hx + (6 if right else -6), hy - 9),
                                                            (hx + (12 if right else -12), hy - 4),
                                                            (hx + (6 if right else -6), hy)])
            elif self.weapon_set == "sky":
                pygame.draw.line(screen, style["rune"], (hx + (7 if right else -7), hy - 6),
                                 (hx + (13 if right else -13), hy - 10), 2)
        elif self.weapon_type == WEAPON_STAFF:
            pygame.draw.rect(screen, (120, 76, 40), (hx, hy - 8, 5, 30))
            art.blit_glow(screen, hx + 2, hy - 12, 18, trim, 95)
            pygame.draw.circle(screen, _shade(trim), (hx + 2, hy - 12), 8)
            pygame.draw.circle(screen, trim, (hx + 2, hy - 12), 5)
            pygame.draw.circle(screen, rune, (hx + 2, hy - 12), 2)
            pygame.draw.circle(screen, _light(c_w, 0.7), (hx + 1, hy - 14), 2)
            if self.weapon_set in ("sky", "ocean"):
                pygame.draw.line(screen, style["metal"], (hx - 3, hy - 12), (hx + 7, hy - 12), 2)
            elif self.weapon_set == "volcano":
                pygame.draw.polygon(screen, style["trim"], [(hx + 2, hy - 20), (hx + 6, hy - 12), (hx - 2, hy - 12)])


# --------------------------------------------------------------------------
# 跟宠：自动治疗 + 协助攻击
# --------------------------------------------------------------------------
class Pet:
    """跟宠：按职业分工 —— 战士远程输出 / 弓箭手加攻速 / 法师回蓝回血。"""

    COLOR = {
        WEAPON_SWORD: (255, 186, 120),   # 战士：暖橙
        WEAPON_BOW: (255, 226, 120),     # 弓箭手：金黄
        WEAPON_STAFF: (150, 196, 255),   # 法师：淡蓝
    }
    ROLE_TEXT = {
        WEAPON_SWORD: "远程助战",
        WEAPON_BOW: "攻速加成",
        WEAPON_STAFF: "回血回蓝",
    }

    def __init__(self, player):
        self.player = player
        self.kind = player.weapon_type
        self.color = self.COLOR.get(self.kind, (120, 240, 200))
        state = getattr(player, "pet_state", {"level": 1, "exp": 0})
        self.level = state.get("level", 1)
        self.exp = state.get("exp", 0)
        self.rect = pygame.Rect(player.rect.centerx - 30, player.rect.top - 30, 30, 30)
        self.anim = random.randint(0, 60)
        self.attack_cd = 50
        self.heal_cd = 120
        self.energy_cd = 60
        self.heal_flash = 0
        self.facing_right = True
        self.hp_given = 0
        self.energy_given = 0
        self.damage_done = 0
        self.skill_cds = [80, 200]

    @property
    def stage(self):
        return min(PET_MAX_STAGE, (self.level - 1) // 3)

    @property
    def stage_name(self):
        return PET_STAGE_NAMES[self.stage]

    @property
    def role_text(self):
        return f"{self.ROLE_TEXT.get(self.kind, '')}·{self.stage_name} Lv.{self.level}"

    def exp_need(self):
        return 3 + self.level * 2

    def gain_exp(self, amount, level=None):
        """击杀获得经验，进化很快（每 3 级一个阶段）。"""
        self.exp += amount
        evolved = False
        while self.exp >= self.exp_need():
            self.exp -= self.exp_need()
            self.level += 1
            evolved = True
        self.player.pet_state = {"level": self.level, "exp": self.exp}
        if evolved and level is not None:
            level.effects.append(Shockwave(self.rect.centerx, self.rect.centery, 70,
                                           (150, 255, 210), 24, 6, 0.25))
            level.float_texts.append(FloatText(
                self.rect.centerx, self.rect.top - 6,
                f"跟宠进化！Lv.{self.level} {self.stage_name}", (150, 255, 220), 16, 80))
            audio.play("win", 0.5)
        return evolved

    def update(self, level):
        self.anim += 1
        player = self.player

        side = -1 if player.facing_right else 1
        target_x = player.rect.centerx + side * 36
        target_y = player.rect.top - 26 + math.sin(self.anim * 0.07) * 7
        self.rect.x += (target_x - self.rect.x) * 0.14
        self.rect.y += (target_y - self.rect.y) * 0.14
        self.facing_right = player.facing_right

        if self.heal_cd > 0:
            self.heal_cd -= 1
        if self.attack_cd > 0:
            self.attack_cd -= 1
        if self.energy_cd > 0:
            self.energy_cd -= 1
        if self.heal_flash > 0:
            self.heal_flash -= 1

        player.pet_haste = (self.kind == WEAPON_BOW)

        if self.kind == WEAPON_SWORD:
            self._ranged_attack(level)
        elif self.kind == WEAPON_STAFF:
            self._support(level)
        # 弓箭手跟宠：只提供攻速加成（player.pet_haste）

        # 跟宠技能：阶段解锁，自动释放
        for i in range(2):
            if self.skill_cds[i] > 0:
                self.skill_cds[i] -= 1
        if self.stage >= 1 and self.skill_cds[0] == 0:
            if self._cast_skill(0, level):
                self.skill_cds[0] = PET_SKILLS[self.kind][0][2]
        if self.stage >= 2 and self.skill_cds[1] == 0:
            if self._cast_skill(1, level):
                self.skill_cds[1] = PET_SKILLS[self.kind][1][2]

    # 战士跟宠：远程点射
    def _ranged_attack(self, level):
        if self.attack_cd > 0:
            return
        target = None
        best = 320
        for enemy in level.enemies:
            dist = math.hypot(enemy.rect.centerx - self.rect.centerx,
                              enemy.rect.centery - self.rect.centery)
            if dist < best:
                best = dist
                target = enemy
        if target is None:
            return
        self.attack_cd = max(28, PET_ATTACK_CD - self.stage * 10)
        damage = int((PET_ATTACK_DMG + self.player.level * 3 + self.level * 3)
                     * (1 + self.stage * 0.25))
        self.damage_done += damage
        level.effects.append(Beam(self.rect.centerx, self.rect.centery,
                                  target.rect.centerx, target.rect.centery,
                                  self.color, 10, 4))
        target.take_hit(damage, target.rect.centerx >= self.rect.centerx)
        level.pop_damage(target, damage, self.color)
        if target.dead:
            level.kill_enemy(target)

    # 法师跟宠：回血 + 回蓝
    def _support(self, level):
        player = self.player
        if self.heal_cd <= 0 and 0 < player.hp < player.max_hp * 0.8:
            healed = player.heal(PET_HEAL + player.level * 2 + self.level * 2 + self.stage * 4)
            if healed > 0:
                self.hp_given += healed
                self.heal_cd = PET_HEAL_CD
                self.heal_flash = 26
                level.float_texts.append(FloatText(
                    player.rect.centerx, player.rect.top - 8, f"+{healed}",
                    (130, 255, 170), 16, 52))
                level.effects.append(Shockwave(player.rect.centerx, player.rect.centery,
                                               52, (130, 255, 170), 22, 4, 0.4))
        if self.energy_cd <= 0 and player.energy < MAX_ENERGY:
            before = player.energy
            player.energy = min(MAX_ENERGY, player.energy + PET_ENERGY_AMOUNT + self.stage * 5)
            gained = int(player.energy - before)
            if gained > 0:
                self.energy_given += gained
                self.energy_cd = PET_ENERGY_CD
                level.float_texts.append(FloatText(
                    player.rect.centerx + 14, player.rect.top - 26, f"+{gained} 能量",
                    (150, 200, 255), 13, 44))

    def _nearby(self, level, radius):
        out = []
        for enemy in level.enemies:
            d = math.hypot(enemy.rect.centerx - self.rect.centerx,
                           enemy.rect.centery - self.rect.centery)
            if d <= radius:
                out.append((d, enemy))
        out.sort(key=lambda t: t[0])
        return out

    def _cast_skill(self, index, level):
        """返回 True 表示成功释放。"""
        player = self.player
        base = (PET_ATTACK_DMG + player.level * 3 + self.level * 3) * (1 + self.stage * 0.25)

        if self.kind == WEAPON_SWORD:
            if index == 0:
                targets = self._nearby(level, 340)
                if not targets:
                    return False
                enemy = targets[0][1]
                level.effects.append(Beam(self.rect.centerx, self.rect.centery,
                                          enemy.rect.centerx, enemy.rect.centery,
                                          (255, 160, 80), 14, 6))
                dmg = int(base * 2.2)
                enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                level.pop_damage(enemy, dmg, (255, 180, 100))
                level.effects.append(Shockwave(enemy.rect.centerx, enemy.rect.centery, 40,
                                               (255, 170, 90), 16, 4, 0.3))
                if enemy.dead:
                    level.kill_enemy(enemy)
                return True
            ring = self._nearby(level, 150)
            if not ring:
                return False
            level.effects.append(Shockwave(self.rect.centerx, self.rect.centery, 150,
                                           (255, 140, 70), 26, 8, 0.2))
            for _, enemy in ring:
                dmg = int(base * 1.6)
                enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                level.pop_damage(enemy, dmg, (255, 170, 100))
                if enemy.dead:
                    level.kill_enemy(enemy)
            return True

        if self.kind == WEAPON_BOW:
            if index == 0:
                targets = self._nearby(level, 360)[:3]
                if not targets:
                    return False
                for _, enemy in targets:
                    level.effects.append(Beam(self.rect.centerx, self.rect.centery,
                                              enemy.rect.centerx, enemy.rect.centery,
                                              (190, 255, 200), 10, 4))
                    dmg = int(base * 1.5)
                    enemy.take_hit(dmg, enemy.rect.centerx >= self.rect.centerx)
                    level.pop_damage(enemy, dmg, (200, 255, 210))
                    if enemy.dead:
                        level.kill_enemy(enemy)
                return True
            player.speed_bonus_timer = max(player.speed_bonus_timer, 240)
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                               "风之祝福！", (190, 255, 210), 16, 60))
            level.effects.append(Shockwave(player.rect.centerx, player.rect.centery, 70,
                                           (190, 255, 200), 20, 4, 0.3))
            return True

        # 法师跟宠
        if index == 0:
            healed = player.heal(24 + self.level * 2)
            before = player.energy
            player.energy = min(MAX_ENERGY, player.energy + 12)
            if healed <= 0 and player.energy == before:
                return False
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                               f"治疗波 +{healed}", (150, 255, 200), 15, 52))
            return True
        healed = player.heal(46 + self.level * 3)
        player.energy = min(MAX_ENERGY, player.energy + 40)
        level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 26,
                                           f"魔力涌泉 +{healed}", (150, 220, 255), 15, 60))
        level.effects.append(Shockwave(player.rect.centerx, player.rect.centery, 90,
                                       (140, 210, 255), 24, 6, 0.25))
        return True

    def draw(self, screen, cam_x, cam_y):
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery - cam_y
        radius = 26 + self.stage * 8
        pulse = 0.75 + math.sin(self.anim * 0.12) * 0.12
        art.blit_glow(screen, cx, cy, int(radius * pulse), self.color, 56 + self.stage * 8)
        orbit_count = 3 + self.stage
        for i in range(orbit_count):
            ang = self.anim * 0.06 + i * math.tau / orbit_count
            orb_x = int(cx + math.cos(ang) * (12 + self.stage * 4))
            orb_y = int(cy + math.sin(ang * 1.2) * (7 + self.stage * 2) - 5)
            orb_r = 2 + (1 if i % 2 == 0 else 0)
            art.blit_glow(screen, orb_x, orb_y, 8 + self.stage * 2, self.color, 34)
            pygame.draw.circle(screen, art._light(self.color, 0.45), (orb_x, orb_y), orb_r)
        if self.stage >= 2:
            ring = int(radius + 6 + 3 * math.sin(self.anim * 0.12))
            pygame.draw.circle(screen, self.color, (cx, cy), ring, 1)
        spr = art.pet_sprite(3 + self.stage, not self.facing_right, self.color)
        screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() // 2))
        if self.stage >= 1:
            tail_y = cy + spr.get_height() // 4
            for i in range(3):
                px = int(cx - (8 + i * 5) * (-1 if self.facing_right else 1))
                py = int(tail_y + math.sin(self.anim * 0.1 + i) * 3)
                pygame.draw.line(screen, art._light(self.color, 0.35), (cx, cy + 1), (px, py), 1)
        if self.stage >= 3:
            art.draw_crown(screen, cx, cy - spr.get_height() // 2 - 6, self.anim * 0.05)
        if self.heal_flash > 0:
            art.blit_glow(screen, cx, cy, 34, (150, 255, 180), 90)

# --------------------------------------------------------------------------
# 怪物
# --------------------------------------------------------------------------
class Enemy:
    def __init__(self, x, y, enemy_type="slime", is_elite=False, level_idx=0):
        self.enemy_type = enemy_type if enemy_type in ENEMY_STATS else "slime"
        stats = ENEMY_STATS[self.enemy_type]

        self.is_elite = is_elite
        self.is_boss = False
        self.level_idx = level_idx

        hp_multiplier = 1 + level_idx * 0.55
        hp_val = int(ENEMY_MAX_HP * stats["hp"] * hp_multiplier)
        if is_elite:
            hp_val = int(hp_val * 1.8)

        w, h = stats["size"]
        if is_elite:
            w += 6
            h += 6
        self.rect = pygame.Rect(x, y, w, h)
        self.start_x, self.start_y = x, y

        self.hp = hp_val
        self.max_hp = hp_val
        self.fly = stats["fly"]
        self.chase = stats["chase"]
        self.xp = stats["xp"]

        # 战斗定位：战士近战 / 弓箭手射箭 / 法师法弹
        self.role = stats["role"]
        self.dmg_type = ROLE_DMG_TYPE[self.role]
        dmg_scale = 1 + level_idx * 0.25
        self.attack_damage = stats["dmg"] * dmg_scale * (1.35 if is_elite else 1.0)
        self.shot_damage = stats.get("shot", 0) * dmg_scale * (1.3 if is_elite else 1.0)

        self.range = random.randint(90, 230)
        self.aggro = 260 if self.chase else 0
        self.speed = ENEMY_SPEED * stats["speed"] * (1 + level_idx * 0.15)
        if is_elite:
            self.speed *= 0.9

        self.direction = random.choice([-1, 1])
        self.axis = random.choice(["x", "y"])
        self.hit_timer = 0
        self.freeze_timer = 0
        self.knockback_x, self.knockback_y = 0, 0
        self.time_passed = random.random() * 10
        self.anim = random.randint(0, 20)

        self.attack_cd = 0
        self.melee_interval = 55
        self.shoot_cd = random.randint(50, 110)
        self.cast_timer = 0
        self.pending_skill = None
        self.elite_skill_cd = random.randint(180, 300)
        self.dash_timer = 0
        self.dash_vx = self.dash_vy = 0
        self.is_summon = False
        self.summoner = None
        self.support_kind = None
        self.support_cd = random.randint(20, 80)

    # ---------------- 战斗 ----------------
    def _deal_melee(self, level, player):
        if self.attack_cd > 0:
            return
        if player.z >= 20:
            return
        self.attack_cd = self.melee_interval
        dmg = player.take_damage(self.attack_damage, self.dmg_type)
        if dmg > 0:
            level.pop_player_damage(dmg, self.dmg_type)
            level.shake = max(level.shake, 4)
            if self.is_summon and self.support_kind == "chill":
                resist = player.status_resist("ocean")
                player.chill_timer = max(player.chill_timer, int(80 * (1 - resist)))
            elif self.is_summon and self.support_kind == "freeze":
                resist = player.status_resist("ocean")
                player.freeze(max(10, int(22 * (1 - resist))))
                player.chill_timer = max(player.chill_timer, int(110 * (1 - resist)))

    def heal(self, amount):
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def _fire_bolts(self, level, player, count=1, spread=0.16, speed=7.0, kind=None):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        base = math.atan2(dy, dx)
        if kind is None:
            kind = "arrow" if self.role == "archer" else "orb"
        for i in range(count):
            ang = base + (i - (count - 1) / 2) * spread
            level.spawn_enemy_bolt(self.rect.centerx, self.rect.centery,
                                   math.cos(ang) * speed, math.sin(ang) * speed,
                                   self.shot_damage, self.dmg_type, kind)

    def _update_skill_timers(self, level, player):
        """精英怪蓄力放技能；返回 True 表示本帧在蓄力，不移动。"""
        if self.is_elite and not self.is_boss and level is not None and player is not None:
            self.elite_skill_cd -= 1
            if self.elite_skill_cd <= 0:
                self.elite_skill_cd = 320
                self.cast_timer = 26
                return True
        return False

    def _update_summon_support(self, level, player):
        if not self.is_summon or self.summoner is None or player is None or level is None:
            return
        if self.summoner.dead or self.summoner not in level.enemies:
            return
        self.support_cd = max(0, self.support_cd - 1)
        boss = self.summoner
        dist_boss = math.hypot(boss.rect.centerx - self.rect.centerx, boss.rect.centery - self.rect.centery)
        dist_player = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
        if self.support_kind == "regen" and self.support_cd == 0 and dist_boss < 210:
            healed = boss.heal(max(10, int(boss.max_hp * 0.018)))
            if healed > 0:
                level.effects.append(SparkBurst(boss.rect.centerx, boss.rect.top + 10,
                                                (140, 255, 180), 10, 2.2, 16, 3, -0.12))
                level.float_texts.append(FloatText(boss.rect.centerx, boss.rect.top - 14,
                                                   f"+{healed}", (150, 255, 190), 16, 40))
            self.support_cd = 52
        elif self.support_kind == "rage" and dist_boss < 220:
            boss.summon_attack_buff_timer = max(getattr(boss, "summon_attack_buff_timer", 0), 18)
            if self.support_cd == 0:
                level.effects.append(SparkBurst(boss.rect.centerx, boss.rect.centery - 8,
                                                (255, 150, 120), 8, 2.0, 14, 3, -0.1))
                self.support_cd = 42
        elif self.support_kind == "chill" and self.support_cd == 0 and dist_player < 150 and player.z < 18:
            resist = player.status_resist("ocean")
            player.chill_timer = max(player.chill_timer, int(125 * (1 - resist)))
            level.effects.append(FrostShards(player.rect.centerx, player.rect.centery, 46, life=20, count=10))
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 20,
                                               "迟缓！", (150, 220, 255), 15, 40))
            self.support_cd = 78
        elif self.support_kind == "freeze" and self.support_cd == 0 and dist_player < 120 and player.z < 18:
            resist = player.status_resist("ocean")
            boss.summon_frost_buff_timer = max(getattr(boss, "summon_frost_buff_timer", 0), 24)
            player.freeze(max(14, int(28 * (1 - resist))))
            player.chill_timer = max(player.chill_timer, int(150 * (1 - resist)))
            level.effects.append(BossSkillFX("ice_nova", self.rect.centerx, self.rect.centery,
                                             70, (150, 220, 255), 18))
            level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 22,
                                               "冻结！", (170, 230, 255), 16, 44))
            self.support_cd = 110

    def _release_skill(self, level, player):
        if player is None:
            return
        if self.role == "warrior":
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            dist = max(1.0, math.hypot(dx, dy))
            self.dash_timer = 28
            self.dash_vx = dx / dist * self.speed * 3.2
            self.dash_vy = dy / dist * self.speed * 3.2
            level.effects.append(Shockwave(self.rect.centerx, self.rect.centery, 46,
                                           ROLE_COLOR["warrior"], 16, 4, 0.4))
        elif self.role == "archer":
            self._fire_bolts(level, player, count=3, spread=0.18, speed=8.0)
        else:
            for i in range(8):
                ang = math.tau * i / 8
                level.spawn_enemy_bolt(self.rect.centerx, self.rect.centery,
                                       math.cos(ang) * 5.5, math.sin(ang) * 5.5,
                                       self.shot_damage, DMG_MAGIC, "orb")
            level.effects.append(Shockwave(self.rect.centerx, self.rect.centery, 60,
                                           ROLE_COLOR["mage"], 20, 5, 0.3))

    # ---------------- 行为 ----------------
    def update(self, walls, player=None, level=None):
        self.anim += 1
        if self.hit_timer > 0:
            self.hit_timer -= 1
        if self.attack_cd > 0:
            self.attack_cd -= 1

        if self.freeze_timer > 0:
            self.freeze_timer -= 1
            return

        if self.cast_timer > 0:
            self.cast_timer -= 1
            if self.cast_timer == 0 and level is not None:
                self._release_skill(level, player)
            return

        if self._update_skill_timers(level, player):
            return

        if self.is_summon:
            self._update_summon_support(level, player)

        is_knockback = abs(self.knockback_x) > 1 or abs(self.knockback_y) > 1
        move_x = move_y = 0

        if self.dash_timer > 0:
            self.dash_timer -= 1
            move_x, move_y = self.dash_vx, self.dash_vy
        elif is_knockback:
            move_x, move_y = self.knockback_x, self.knockback_y
            self.knockback_x *= 0.8
            self.knockback_y *= 0.8
            if abs(self.knockback_x) < 1:
                self.knockback_x = 0
            if abs(self.knockback_y) < 1:
                self.knockback_y = 0
        else:
            self.knockback_x = self.knockback_y = 0
            self.time_passed += 0.1

            target = None
            if self.chase and player is not None:
                dx = player.rect.centerx - self.rect.centerx
                dy = player.rect.centery - self.rect.centery
                if math.hypot(dx, dy) < self.aggro:
                    target = (dx, dy)

            if self.fly:
                if target:
                    dist = max(1.0, math.hypot(*target))
                    move_x = self.speed * 1.1 * target[0] / dist
                    move_y = self.speed * 1.1 * target[1] / dist
                else:
                    move_x = self.direction * self.speed
                    move_y = math.sin(self.time_passed) * 2.6
                    if abs(self.rect.x - self.start_x) > self.range:
                        self.direction *= -1
            elif target:
                if abs(target[0]) > abs(target[1]):
                    move_x = self.speed * (1 if target[0] > 0 else -1)
                else:
                    move_y = self.speed * (1 if target[1] > 0 else -1)
            else:
                if self.axis == "x":
                    move_x = self.direction * self.speed
                    if abs(self.rect.x + move_x - self.start_x) > self.range:
                        self.direction *= -1
                        move_x = self.direction * self.speed
                else:
                    move_y = self.direction * self.speed
                    if abs(self.rect.y + move_y - self.start_y) > self.range:
                        self.direction *= -1
                        move_y = self.direction * self.speed

        if move_x:
            self.rect.x += move_x
            if not self.fly:
                for wall in walls:
                    if self.rect.colliderect(wall):
                        if move_x > 0:
                            self.rect.right = wall.left
                        if move_x < 0:
                            self.rect.left = wall.right
                        if is_knockback:
                            self.knockback_x = 0
                        elif self.dash_timer <= 0:
                            self.direction *= -1

        if move_y:
            self.rect.y += move_y
            if not self.fly:
                for wall in walls:
                    if self.rect.colliderect(wall):
                        if move_y > 0:
                            self.rect.bottom = wall.top
                        if move_y < 0:
                            self.rect.top = wall.bottom
                        if is_knockback:
                            self.knockback_y = 0
                        elif self.dash_timer <= 0:
                            self.direction *= -1

        if player is None or level is None:
            return

        # 近战接触伤害
        if self.rect.colliderect(player.rect):
            self._deal_melee(level, player)

        # 远程：弓箭手射箭 / 法师法弹
        if self.role in ("archer", "mage"):
            if self.shoot_cd > 0:
                self.shoot_cd -= 1
            else:
                dist = math.hypot(player.rect.centerx - self.rect.centerx,
                                  player.rect.centery - self.rect.centery)
                if 70 < dist < 400:
                    self._fire_bolts(level, player)
                    self.shoot_cd = 105 if self.role == "archer" else 120

    def take_hit(self, damage, from_right):
        self.hp -= damage
        self.hit_timer = 10
        self.knockback_x = -7 if from_right else 7
        self.knockback_y = random.uniform(-2.5, 2.5)

    def freeze(self, frames):
        self.freeze_timer = max(self.freeze_timer, frames)

    @property
    def dead(self):
        return self.hp <= 0

    # ---------------- 绘制 ----------------
    def draw(self, screen, cam_x, cam_y):
        dx = self.rect.x - cam_x
        dy = self.rect.y - cam_y
        bob = math.sin(self.anim * 0.12 + self.time_passed) * (2.5 if self.fly else 1.2)

        sw = max(16, self.rect.width - 6)
        art.shadow(screen, dx + 3, dy + self.rect.height - 6, sw, 8, 80)
        if self.is_summon:
            art.blit_glow(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                          int(self.rect.width * 0.8), (190, 130, 255), 45)
            pygame.draw.ellipse(screen, (196, 140, 255),
                                (dx + 2, dy + self.rect.height - 8, self.rect.width - 4, 8), 2)
            tags = {"regen": ("愈", (150, 255, 180)), "rage": ("怒", (255, 164, 128)),
                    "chill": ("缓", (150, 220, 255)), "freeze": ("冻", (188, 235, 255))}
            glyph, gcol = tags.get(self.support_kind, ("召", (220, 180, 255)))
            tag = art.label(glyph, gcol, 10, True)
            screen.blit(tag, (dx + self.rect.width // 2 - tag.get_width() // 2,
                              dy - 20))

        frame = (self.anim // 12) % 2 if self.fly else 0
        spr = art.monster_sprite(self.enemy_type, self.is_elite, frame, not self.direction > 0)

        if self.hit_timer > 0:
            spr = art.silhouette(spr)
        elif self.freeze_timer > 0:
            spr = art.tint(spr)
        elif self.is_summon:
            spr = art.tint(spr, (200, 140, 255, 85))

        sx = dx + self.rect.width // 2 - spr.get_width() // 2
        sy = dy + self.rect.height - spr.get_height() + 4 + bob
        screen.blit(spr, (sx, sy))

        if self.is_elite:
            art.draw_crown(screen, dx + self.rect.width // 2, sy - 10, self.anim * 0.05)

        if self.cast_timer > 0:
            art.blit_glow(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                          int(self.rect.width * 0.9), ROLE_COLOR.get(self.role, (255, 200, 120)), 80)

        if 0 < self.hp < self.max_hp:
            bar_w = max(22, self.rect.width)
            by = dy - 9
            pygame.draw.rect(screen, (40, 16, 20), (dx, by, bar_w, 6))
            ratio = max(0.0, self.hp / self.max_hp)
            color = (250, 90, 90) if ratio < 0.35 else (110, 226, 120)
            pygame.draw.rect(screen, color, (dx + 1, by + 1, int((bar_w - 2) * ratio), 4))
            if self.is_elite:
                txt = art.label(f"{max(0, int(self.hp))}/{int(self.max_hp)}", (255, 240, 200), 11)
                screen.blit(txt, (dx + bar_w // 2 - txt.get_width() // 2, by - 14))


class Boss(Enemy):
    """每关不同的 BOSS，各自带一套技能。"""

    TYPES = {0: "slime", 1: "mushroom", 2: "tree", 3: "skeleton"}
    NAMES = {"slime": "史莱姆王", "mushroom": "蘑菇大王",
             "tree": "树妖王", "skeleton": "骷髅王", "golem": "远古石魔"}
    SKILLS = {
        "slime": ["slam", "summon"],
        "mushroom": ["spore_ring", "summon"],
        "tree": ["thorn_ring", "slam"],
        "skeleton": ["bone_volley", "summon", "charge"],
        "golem": ["slam", "summon", "charge"],
    }
    MINIONS = {"slime": "slime", "mushroom": "mushroom",
               "tree": "mushroom", "skeleton": "skeleton", "golem": "golem"}

    def __init__(self, x, y, level_idx=1, boss_type=None):
        boss_type = boss_type or self.TYPES.get(level_idx, "slime")
        super().__init__(x, y, boss_type, True, level_idx)
        self.is_boss = True
        self.role = "boss"
        self.dmg_type = DMG_PHYS
        self.rect = pygame.Rect(x, y, 88, 76)
        self.hp = int(BOSS_MAX_HP * (1 + level_idx * 1.15))
        self.max_hp = self.hp
        self.speed = 1.5 + level_idx * 0.2
        self.range = 380
        self.aggro = 720
        self.chase = True
        self.attack_damage = 20 + level_idx * 5.5
        self.base_attack_damage = self.attack_damage
        self.melee_interval = 60
        self.skill_cd = 90
        self.pending_skill = None
        self.elite_skill_cd = 10 ** 9
        self.name = self.NAMES.get(boss_type, "首领")
        self.weapon_kind = {"skeleton": "sword", "tree": "club",
                            "golem": "hammer", "mushroom": "staff"}.get(boss_type)
        self.summon_count = 0
        self.summon_attack_buff_timer = 0
        self.summon_frost_buff_timer = 0
        self.support_index = 0

    def freeze(self, frames):
        super().freeze(max(20, frames // 2))     # BOSS 抗冻

    def update(self, walls, player=None, level=None):
        if self.summon_attack_buff_timer > 0:
            self.summon_attack_buff_timer -= 1
        if self.summon_frost_buff_timer > 0:
            self.summon_frost_buff_timer -= 1
        self.attack_damage = self.base_attack_damage * (1.28 if self.summon_attack_buff_timer > 0 else 1.0)
        super().update(walls, player, level)

    def _update_skill_timers(self, level, player):
        if player is None or level is None:
            return False
        # 离得太远就不放技能，避免隔着半张地图空放
        if math.hypot(player.rect.centerx - self.rect.centerx,
                      player.rect.centery - self.rect.centery) > 700:
            return False
        self.skill_cd -= 1
        if self.skill_cd <= 0:
            self.skill_cd = 165
            pool = list(self.SKILLS[self.enemy_type])
            if getattr(level, "theme", "") == "ocean" and "ice_nova" not in pool:
                pool.append("ice_nova")
                if random.random() < 0.55:
                    self.pending_skill = "ice_nova"
                    pool = None
            if pool:
                self.pending_skill = random.choice(pool)
            self.cast_timer = 30
            level.effects.append(BossCast(self.rect.centerx, self.rect.centery,
                                          self.rect.width, duration=34,
                                          color=SKILL_BY_WEAPON[WEAPON_SWORD]["color"]))
            level.shake = max(level.shake, 5)
            audio.play("boss_skill", 0.9)
            if self.pending_skill == "summon":
                audio.play("boss_roar", 0.7)
            names = {"slam": "砸地！", "summon": "召唤！", "thorn_ring": "荆棘环射！",
                     "bone_volley": "骨矛齐射！", "charge": "冲锋！",
                     "spore_ring": "孢子环射！", "ice_nova": "冰冻！"}
            level.float_texts.append(FloatText(
                self.rect.centerx, self.rect.top - 20,
                names.get(self.pending_skill, "技能！"),
                (255, 220, 160), 20, 70))
            return True
        return False

    def _release_skill(self, level, player):
        skill = self.pending_skill
        self.pending_skill = None
        if skill is None or player is None:
            return
        cx, cy = self.rect.center

        if skill == "slam":
            radius = 190
            level.effects.append(BossSkillFX("slam", cx, cy + self.rect.height // 2,
                                            radius, (255, 170, 90), 30))
            level.effects.append(Shockwave(cx, cy, radius, (255, 170, 90), 26, 10, 0.2))
            level.shake = 12
            audio.play("boom", 0.6)
            if math.hypot(player.rect.centerx - cx, player.rect.centery - cy) <= radius:
                dmg = player.take_damage(self.attack_damage * 1.9, DMG_PHYS)
                if dmg:
                    level.pop_player_damage(dmg, DMG_PHYS)

        elif skill == "summon":
            if self.summon_count >= 6:
                return
            minion = self.MINIONS.get(self.enemy_type, "slime")
            level.float_texts.append(FloatText(cx, cy - self.rect.height, "召唤！",
                                               (210, 160, 255), 22, 70))
            level.shake = max(level.shake, 6)
            level.effects.append(BossSkillFX("summon", cx, cy, 90, (200, 140, 255), 34))
            audio.play("boss_roar", 0.7)
            support_cycle = ("regen", "rage", "chill", "freeze")
            for _ in range(3):
                ang = random.uniform(0, math.tau)
                mx = cx + math.cos(ang) * random.randint(60, 110)
                my = cy + math.sin(ang) * random.randint(60, 110)
                spawned = Enemy(mx, my, minion, False, self.level_idx)
                spawned.is_summon = True
                spawned.summoner = self
                spawned.support_kind = support_cycle[self.support_index % len(support_cycle)]
                spawned.support_cd = 24
                self.support_index += 1
                spawned.hp = int(spawned.max_hp * 0.7)
                spawned.max_hp = spawned.hp
                level.enemies.append(spawned)
                self.summon_count += 1
                level.effects.append(Shockwave(mx, my, 44, (200, 140, 255), 18, 4, 0.4))

        elif skill == "spore_ring":
            level.effects.append(BossSkillFX("spore_ring", cx, cy, 120, (150, 255, 170), 30))
            for i in range(10):
                ang = math.tau * i / 10
                level.spawn_enemy_bolt(cx, cy, math.cos(ang) * 4.6, math.sin(ang) * 4.6,
                                       self.attack_damage * 1.0, DMG_MAGIC, "orb")
            level.effects.append(Shockwave(cx, cy, 120, (150, 255, 170), 24, 6, 0.25))
            level.shake = 8

        elif skill == "thorn_ring":
            level.effects.append(BossSkillFX("thorn_ring", cx, cy, 120, (220, 180, 90), 26))
            for i in range(12):
                ang = math.tau * i / 12
                level.spawn_enemy_bolt(cx, cy, math.cos(ang) * 5.0, math.sin(ang) * 5.0,
                                       self.attack_damage * 0.9, DMG_PHYS, "thorn")
            level.shake = 8

        elif skill == "bone_volley":
            level.effects.append(BossSkillFX("bone_volley", cx, cy, 110, (235, 230, 210), 24))
            self._fire_bolts(level, player, count=5, spread=0.18, speed=8.5, kind="bone")
            level.shake = 6
            self.shoot_cd = 90

        elif skill == "ice_nova":
            level.effects.append(BossSkillFX("ice_nova", cx, cy, 150, (140, 210, 255), 34))
            radius = 170
            level.shake = 7
            audio.play("hit_magic", 0.8)
            if math.hypot(player.rect.centerx - cx, player.rect.centery - cy) <= radius:
                dmg = player.take_damage(self.attack_damage * 1.15, DMG_MAGIC)
                if dmg:
                    level.pop_player_damage(dmg, DMG_MAGIC)
                resist = player.status_resist("ocean")
                player.chill_timer = max(player.chill_timer, int(150 * (1 - resist)))
                level.float_texts.append(FloatText(player.rect.centerx, player.rect.top - 24,
                                                   "冰冻！", (150, 220, 255), 17, 70))

        elif skill == "charge":
            dx = player.rect.centerx - cx
            dy = player.rect.centery - cy
            dist = max(1.0, math.hypot(dx, dy))
            self.dash_timer = 34
            self.dash_vx = dx / dist * self.speed * 4.0
            self.dash_vy = dy / dist * self.speed * 4.0
            level.effects.append(BossSkillFX("charge", cx, cy, 100, (255, 120, 90), 22))
            level.shake = 7

    def draw(self, screen, cam_x, cam_y):
        dx = self.rect.x - cam_x
        dy = self.rect.y - cam_y
        bob = math.sin(self.anim * 0.08) * 3

        art.shadow(screen, dx, dy + self.rect.height - 10, self.rect.width, 14, 90)
        variant = getattr(self, "variant", 0)
        aura = {0: (220, 60, 200), 1: (230, 80, 70), 2: (150, 90, 240),
                3: (90, 70, 140)}.get(variant, (220, 60, 200))
        art.blit_glow(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                      self.rect.width if not variant else int(self.rect.width * 1.2),
                      aura, 40)
        if self.summon_attack_buff_timer > 0:
            art.blit_glow(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                          64, (255, 150, 120), 36)
        if self.summon_frost_buff_timer > 0:
            art.blit_glow(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                          56, (150, 220, 255), 32)

        facing_right = self.direction >= 0
        chapter = chapter_of(self.level_idx)
        wing_color = {
            0: (188, 240, 198),
            1: (150, 224, 255),
            2: (232, 236, 255),
            3: (255, 170, 118),
        }.get(chapter, (225, 235, 255))
        weapon_color = {
            0: (196, 236, 164),
            1: (166, 226, 255),
            2: (236, 236, 255),
            3: (255, 188, 132),
        }.get(chapter, (214, 218, 230))
        if variant == 1:
            weapon_color = (255, 150, 130)
        elif variant == 2:
            weapon_color = (190, 150, 255)
        elif variant >= 3:
            weapon_color = (132, 118, 196)
        # 天空大关的 BOSS 有翅膀
        if chapter == 2:
            art.draw_wings(screen, dx + self.rect.width // 2, dy + self.rect.height // 2,
                           wing_color, self.anim * 0.12)

        spr = art.boss_sprite(self.enemy_type, self.level_idx, not facing_right,
                              getattr(self, "variant", 0))
        if self.hit_timer > 0:
            spr = art.silhouette(spr)
        elif self.freeze_timer > 0:
            spr = art.tint(spr)
        elif self.is_summon:
            spr = art.tint(spr, (200, 140, 255, 85))

        sx = dx + self.rect.width // 2 - spr.get_width() // 2
        sy = dy + self.rect.height - spr.get_height() + 8 + bob
        screen.blit(spr, (sx, sy))
        art.draw_crown(screen, dx + self.rect.width // 2, sy - 16, self.anim * 0.04)
        if variant:
            mark = art.label(["", "狂", "古", "渊"][variant], (255, 226, 150), 12, True)
            screen.blit(mark, (dx + self.rect.width // 2 - mark.get_width() // 2, dy - 30))

        # 部分 BOSS 手持武器（蓄力时举起挥动）
        if self.weapon_kind:
            swing = 0.0
            if self.cast_timer > 0:
                swing = 1.0 - self.cast_timer / 34.0
            hx = dx + (self.rect.width - 10 if facing_right else 10)
            hy = dy + self.rect.height * 0.52
            art.draw_boss_weapon(screen, hx, hy, self.weapon_kind, facing_right, swing, weapon_color)

        if self.cast_timer > 0:
            # 技能蓄力预警圈
            t = 1 - self.cast_timer / 34
            r = int(90 + 60 * t)
            surf = _boss_warn_surface(r)
            screen.blit(surf, (dx + self.rect.width // 2 - r - 4,
                               dy + self.rect.height // 2 - r - 4))


# --------------------------------------------------------------------------
# 掉落物
# --------------------------------------------------------------------------
class Item:
    def __init__(self, x, y, type_name, quality="none", weapon_type=None, label_dy=0,
                 set_key="forest", hidden=None):
        self.type = type_name
        self.quality = quality
        self.weapon_type = weapon_type
        self.label_dy = label_dy
        self.set_key = set_key
        self.hidden = hidden
        self.rect = pygame.Rect(x + 6, y + 6, 28, 28)
        self.collected = False
        self.age = random.randint(0, 40)
        self.phase = random.random() * math.tau
        self.vx = random.uniform(-1.8, 1.8)
        self.vy = random.uniform(-2.4, -0.8)
        self.air_timer = 20

    def _nudge_from_blockers(self, blockers):
        if not blockers:
            return
        for _ in range(4):
            pushed = False
            for wall in blockers:
                if not self.rect.colliderect(wall):
                    continue
                ox = min(self.rect.right - wall.left, wall.right - self.rect.left)
                oy = min(self.rect.bottom - wall.top, wall.bottom - self.rect.top)
                if ox < oy:
                    if self.rect.centerx < wall.centerx:
                        self.rect.right = wall.left
                    else:
                        self.rect.left = wall.right
                    self.vx *= -0.22
                else:
                    if self.rect.centery < wall.centery:
                        self.rect.bottom = wall.top
                    else:
                        self.rect.top = wall.bottom
                    self.vy *= -0.18
                pushed = True
            if not pushed:
                break

    def update_physics(self, blockers=None):
        self.age += 1
        if self.air_timer > 0 or abs(self.vx) > 0.08 or abs(self.vy) > 0.08:
            self.air_timer = max(0, self.air_timer - 1)
            self.vy = min(2.6, self.vy + 0.18)
            self.rect.x += int(round(self.vx))
            self._nudge_from_blockers(blockers)
            self.rect.y += int(round(self.vy))
            self._nudge_from_blockers(blockers)
            self.vx *= 0.82
            self.vy *= 0.72
        else:
            self._nudge_from_blockers(blockers)

    def display_name(self):
        gear = GEAR_SETS.get(self.set_key, GEAR_SETS["forest"])
        qn = Q_NAME.get(self.quality, "")
        if self.type == "weapon":
            base = gear["weapon"].get(self.weapon_type, "武器")
            return f"{qn}·{base}"
        if self.type in ("armor", "helmet", "boots", "pants", "bracelet"):
            base = f"{qn}·{gear[self.type]}"
        else:
            return ITEM_NAME.get(self.type, "")
        if self.hidden:
            base += "（隐藏）"
        return base

    def draw(self, screen, cam_x, cam_y):
        if self.collected:
            return
        bob = math.sin(self.age * 0.12 + self.phase) * 3
        box = art.ITEM_BOX
        x = self.rect.centerx - cam_x - box // 2
        y = self.rect.centery - cam_y - box // 2 + bob
        set_color = GEAR_SETS.get(self.set_key, {}).get("color")
        if self.hidden:
            art.blit_glow(screen, x + box // 2, y + box // 2, box, (255, 190, 90), 80)
        art.draw_item_icon(screen, x, y, self.type, self.quality, self.weapon_type,
                           self.age * 0.08, set_color=set_color, set_key=self.set_key)

        name = self.display_name()
        if name:
            color = Q_COLOR.get(self.quality, (230, 230, 230))
            if self.type == "potion_hp":
                color = (255, 140, 150)
            elif self.type == "potion_energy":
                color = (140, 190, 255)
            surf = art.label(name, color, 12)
            screen.blit(surf, (x + box // 2 - surf.get_width() // 2, y - 13 + self.label_dy))
