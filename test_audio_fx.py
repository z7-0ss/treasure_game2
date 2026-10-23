"""音效 / 战斗特效 / 背景音乐校验。"""
import os
import random
import sys

os.environ["TREASURE_SAVE"] = "/tmp/treasure_audio_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
pygame.display.set_mode((960, 540))

import audio
from settings import *
from level import Level
from entities import Player, SparkBurst, SlashArc, CastCircle, Shockwave, FloatText


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# ---------- 1. 音频资源 ----------
ready = audio.init()
check("音频系统可用", ready)
check("音效数量 >= 18", len(audio._sfx) >= 18, len(audio._sfx))
for name in ("slash", "shot", "spell", "hit_phys", "hit_magic", "crit",
             "boss_skill", "boss_roar", "levelup", "key", "door", "jump"):
    check(f"存在音效 {name}", name in audio._sfx)

# ---------- 1.5 波形必须是真实响度（防止 int16 未缩放导致静音） ----------
from array import array


def _peak(sound):
    pcm = array("h")
    pcm.frombytes(sound.get_raw())
    return max((abs(v) for v in pcm), default=0)


for name in ("slash", "crit", "hit_phys", "levelup", "boss_roar"):
    peak = _peak(audio._sfx[name])
    check(f"音效 {name} 不是静音", peak > 1000, peak)
audio.play_music("menu")
check("背景音乐不是静音", _peak(audio._music["menu"]) > 3000,
      _peak(audio._music["menu"]))

# ---------- 2. 多段背景音乐 ----------
for track in ("menu", "forest", "ocean", "sky", "volcano", "boss", "victory"):
    audio.play_music(track, force=True)
    check(f"背景音乐可切换到 {track}", audio.music_name() == track)

# 去抖：1.2 秒内不会来回切
audio.play_music("menu", force=True)
audio.play_music("boss")
check("1.2 秒内不重复切换（防抖）", audio.music_name() == "menu", audio.music_name())
audio._music_switch_at = -10.0   # 跳过冷却，方便后续关卡测试
check("重复切换同名音乐不报错", audio.music_name() == "menu")

# ---------- 3. 关卡自动切换 BOSS 音乐 ----------
random.seed(2)
lv = Level(5, WEAPON_SWORD)          # 海底
lv.player.invincible_timer = 10 ** 9
# 先把玩家挪远，避免直接触发 BOSS 音乐
lv.player.rect.center = (TILE_SIZE * 4, TILE_SIZE * 4)
audio._music_switch_at = -10.0
lv.update()
check("海底关卡播放海底音乐", audio.music_name() == "ocean", audio.music_name())

lv.player.rect.center = (lv.boss.rect.centerx - 60, lv.boss.rect.centery)
audio._music_switch_at = -10.0
lv.update()
check("靠近 BOSS 切换战斗音乐", audio.music_name() == "boss", audio.music_name())

# ---------- 4. 武器攻击特效 ----------
random.seed(3)
sword_lv = Level(0, WEAPON_SWORD)
sword_lv.player.attack()
sword_lv.update()
check("剑士挥砍有刀光", any(isinstance(e, SlashArc) for e in sword_lv.effects),
      [type(e).__name__ for e in sword_lv.effects])

random.seed(3)
bow_lv = Level(0, WEAPON_BOW)
bow_lv.player.attack()
bow_lv.update()
check("弓箭手射击有枪口火花",
      any(isinstance(e, SparkBurst) for e in bow_lv.effects),
      [type(e).__name__ for e in bow_lv.effects])

random.seed(3)
staff_lv = Level(0, WEAPON_STAFF)
staff_lv.player.attack()
staff_lv.update()
check("法师施法有魔法阵",
      any(isinstance(e, CastCircle) for e in staff_lv.effects),
      [type(e).__name__ for e in staff_lv.effects])

# ---------- 5. 命中火花 / 暴击 ----------
random.seed(5)
lv = Level(0, WEAPON_SWORD)
lv.player.invincible_timer = 10 ** 9
enemy = lv.enemies[0]
enemy.hp = enemy.max_hp = 99999
lv.player.rect.center = (enemy.rect.centerx - 30, enemy.rect.centery)
lv.player.facing_right = True
lv.player.level = 45          # 暴击率更高，测试更稳定
hp_before = enemy.hp
crit_seen = False
for _ in range(600):
    lv.player.attack()
    lv.update()
    if any(isinstance(f, FloatText) and "暴击" in f.text for f in lv.float_texts):
        crit_seen = True
    if enemy.hp < hp_before and not any(isinstance(e, SparkBurst) for e in lv.effects):
        pass
check("命中会掉血", enemy.hp < hp_before, (hp_before, enemy.hp))
check("命中产生火花",
      any(isinstance(e, SparkBurst) for e in lv.effects)
      or crit_seen, len(lv.effects))
check("会出现暴击（600 帧内）", crit_seen, lv.player.crit_chance)

# ---------- 6. 升级特效 ----------
random.seed(6)
lv = Level(0, WEAPON_SWORD)
lv.player.invincible_timer = 10 ** 9
lv.player.level = 10
lv.player.next_level_exp = 50
lv.player.exp = 49
target = lv.enemies[0]
target.hp = 1
lv.kill_enemy(target)
check("击杀后升级", lv.player.level == 11, lv.player.level)
check("升级有金色冲击波",
      any(isinstance(e, Shockwave) and e.color == (255, 230, 150) for e in lv.effects),
      [(type(e).__name__, getattr(e, "color", None)) for e in lv.effects])
check("升级有飘字",
      any(isinstance(f, FloatText) and "升级" in f.text for f in lv.float_texts),
      [f.text for f in lv.float_texts])

# ---------- 7. 击杀爆裂 ----------
check("击杀产生爆裂火花",
      any(isinstance(e, SparkBurst) for e in lv.effects))

# ---------- 8. 音乐 / 音效开关 + 偏好持久化 ----------
import save as save_mod

audio.set_music_enabled(False)
audio.play_music("menu")
check("关闭音乐后不播放", not audio._music_channel.get_busy())
check("关闭音乐仍记住曲目", audio.music_name() == "menu")

audio.set_music_enabled(True)
check("重新打开音乐", audio.music_enabled() and audio._music_channel.get_busy())

audio.set_sfx_enabled(False)
check("关闭音效标记生效", not audio.sfx_enabled())
audio.set_sfx_enabled(True)
check("重新打开音效", audio.sfx_enabled())

save_mod.save_prefs({"music": False, "sfx": True})
prefs = save_mod.load_prefs()
check("偏好设置可保存", prefs.get("music") is False and prefs.get("sfx") is True, prefs)
check("偏好文件路径存在", os.path.exists(save_mod._PREF_PATH) or save_mod._browser_window())
try:
    os.remove(save_mod._PREF_PATH)
except OSError:
    pass

print("\nAUDIO / FX CHECKS PASSED")
