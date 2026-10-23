"""渲染最终通关画面（16 关全通、45 级、红装）。"""
import os, sys, random
os.environ["TREASURE_SAVE"] = "/tmp/final_shot.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, ".")
import pygame
pygame.init()
from settings import *
from level import Level
from entities import Player
import audio, art
import main as gm

audio.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font, big_font, small_font = art.font(24), art.font(42), art.font(16)

random.seed(9)
lv = Level(15, WEAPON_SWORD)
pl = lv.player
pl.level = MAX_PLAYER_LEVEL
pl.base_max_hp = 1200
pl.hp = pl.max_hp
pl.weapon_quality, pl.weapon_set = Q_RED, "volcano"
pl.armor_quality, pl.armor_set = Q_RED, "volcano"
pl.helmet_quality, pl.helmet_set = Q_GOLD, "sky"
pl.boots_quality, pl.boots_set = Q_RED, "sky"
pl.pants_quality, pl.pants_set = Q_GOLD, "ocean"
pl.bracelet_quality, pl.bracelet_set = Q_RED, "forest"
lv.pet.level = 22
lv.pet_state = {"level": 22, "exp": 5}

gm.draw_win_screen(screen, lv, font, big_font, small_font)
pygame.image.save(screen, "preview/scene_win_final.png")
print("ok", pl.level, pl.get_damage())
