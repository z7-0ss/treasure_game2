"""audio.py —— 代码合成的背景音乐与音效（无外部素材）。

- 背景音乐：菜单 / 森林 / 海底 / 天空 / 火山 / BOSS 战 / 通关，共 7 段循环，按场景切换
- 音效：挥砍、射箭、施法、物理/法术命中、暴击、受伤、拾取、升级、爆炸、治疗、开门、BOSS 咆哮…
全部用 numpy 即时合成；没有声卡或 numpy 时静默降级，不影响游戏。
"""
import math
import os
import sys
from array import array

import pygame

from settings import *

try:
    import numpy as np
except Exception:            # pragma: no cover
    np = None

SR = 22050
_ready = False
_music = {}                  # 已合成的 BGM 缓存 {"menu": Sound, ...}
_music_current = None
_music_playing = None
_sfx = {}
_sfx_volume = 0.9
_music_volume = 0.55
_music_channel = None
_music_switch_at = 0.0
_music_on = False
_sfx_on = True
_sfx_last_played = {}
_SFX_COOLDOWN_MS = {
    "boss_roar": 180,
    "boss_skill": 90,
    "boom": 45,
    "hit_magic": 35,
    "hit_phys": 25,
    "hit": 25,
}

_NOTE_BASE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
              "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _freq(name):
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + _NOTE_BASE[pitch]
    return 440.0 * 2 ** ((midi - 69) / 12)


# --------------------------------------------------------------------------
# 合成工具
# --------------------------------------------------------------------------
def _env(t, attack=0.01, decay=2.0):
    a = np.clip(t / max(1e-4, attack), 0, 1)
    return a * np.exp(-t * decay)


def _pure_env(i, n, attack, decay):
    t = i / SR
    a = min(1.0, t / max(1e-4, attack))
    return a * math.exp(-t * decay)


def _sine(freq, dur, amp=0.2, attack=0.01, decay=2.0, vibrato=0.0):
    n = int(SR * dur)
    if np is None:                       # 没有 numpy 也能发声
        out = []
        for i in range(n):
            t = i / SR
            ph = 2 * math.pi * freq * t + (math.sin(2 * math.pi * 5.0 * t) * vibrato if vibrato else 0)
            out.append(amp * math.sin(ph) * _pure_env(i, n, attack, decay))
        return out
    t = np.linspace(0, dur, n, endpoint=False)
    phase = 2 * np.pi * freq * t
    if vibrato:
        phase += np.sin(2 * np.pi * 5.0 * t) * vibrato
    return amp * np.sin(phase) * _env(t, attack, decay)


def _tri(freq, dur, amp=0.2, attack=0.01, decay=2.0):
    n = int(SR * dur)
    if np is None:
        out = []
        for i in range(n):
            t = i / SR
            w = 2 * abs(2 * (t * freq - math.floor(t * freq + 0.5))) - 1
            out.append(amp * w * _pure_env(i, n, attack, decay))
        return out
    t = np.linspace(0, dur, n, endpoint=False)
    w = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
    return amp * w * _env(t, attack, decay)


def _saw(freq, dur, amp=0.15, attack=0.01, decay=2.0):
    n = int(SR * dur)
    if np is None:
        out = []
        for i in range(n):
            t = i / SR
            w = 2 * (t * freq - math.floor(t * freq + 0.5))
            out.append(amp * w * _pure_env(i, n, attack, decay))
        return out
    t = np.linspace(0, dur, n, endpoint=False)
    w = 2 * (t * freq - np.floor(t * freq + 0.5))
    return amp * w * _env(t, attack, decay)


def _noise(dur, amp=0.2, decay=5.0, seed=7):
    n = int(SR * dur)
    if np is None:
        import random as _random
        rng = _random.Random(seed)
        out = []
        for i in range(n):
            out.append(amp * rng.uniform(-1, 1) * _pure_env(i, n, 0.005, decay))
        return out
    t = np.linspace(0, dur, n, endpoint=False)
    rng = np.random.default_rng(seed)
    return amp * rng.uniform(-1, 1, len(t)) * _env(t, 0.005, decay)


def _mix(length, tracks):
    if np is None:
        buf = [0.0] * length
        for start, data in tracks:
            end = min(length, start + len(data))
            for i in range(max(0, end - start)):
                buf[start + i] += data[i]
        return buf
    buf = np.zeros(length)
    for start, data in tracks:
        end = min(length, start + len(data))
        if end > start:
            buf[start:end] += data[:end - start]
    return buf


def _to_sound(buf, volume=1.0, fade=True):
    # 归一化到 0.9 峰值，保证能听见（volume 只作为相对响度）
    if np is not None:
        peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
        if peak > 1e-6:
            buf = buf / peak * 0.95 * volume
    else:
        peak = max((abs(v) for v in buf), default=0.0)
        if peak > 1e-6:
            k = 0.95 * volume / peak
            buf = [v * k for v in buf]
    if np is None:
        n = len(buf)
        k = int(SR * 0.012) if fade and n > 400 else 0
        samples = array("h")
        for i, v in enumerate(buf):
            if k and i < k:
                v *= i / k
            elif k and i >= n - k:
                v *= (n - 1 - i) / k
            s = int(max(-1.0, min(1.0, v * volume)) * 32767)
            samples.append(s)
            samples.append(s)
        return pygame.mixer.Sound(buffer=samples.tobytes())
    buf = np.clip(buf, -1.0, 1.0) * volume
    if fade and len(buf) > 400:
        k = int(SR * 0.012)
        buf[:k] *= np.linspace(0, 1, k)
        buf[-k:] *= np.linspace(1, 0, k)
    # 关键：浮点 [-1,1] 必须放大到 16bit 整数范围，否则就是静音
    pcm = np.clip(buf * 32767.0, -32768, 32767).astype(np.int16)
    stereo = np.repeat(pcm.reshape(-1, 1), 2, axis=1)
    return pygame.mixer.Sound(buffer=stereo.tobytes())


# --------------------------------------------------------------------------
# 七段背景音乐
# --------------------------------------------------------------------------
# 每段：bar 秒数、和弦（低音 + 分解音）、琶音间隔、音色、是否加鼓
_MUSIC_SPECS = {
    "menu": dict(bar=4.8, kind="sine", arp=0.6, pad=0.055, arp_amp=0.075,
                 perc=False, sparkle=True,
                 chords=[("A2 C3 E3 G3", "E4 A4 C5 E5"),
                         ("F2 A3 C4 E4", "C4 E4 A4 C5"),
                         ("C3 E3 G3 B3", "G4 B4 E5 G5"),
                         ("G2 B3 D4 F3", "D4 G4 B4 D5")]),
    "forest": dict(bar=4.4, kind="tri", arp=0.55, pad=0.05, arp_amp=0.07,
                   perc=False, sparkle=True,
                   chords=[("D3 F#3 A3 C#4", "A4 C#5 E5 F#5"),
                           ("B2 D3 F#3 A3", "F#4 A4 D5 F#5"),
                           ("G2 B2 D3 F#3", "D4 G4 B4 D5"),
                           ("A2 C#3 E3 G3", "E4 A4 C#5 E5")]),
    "ocean": dict(bar=5.2, kind="sine", arp=0.8, pad=0.065, arp_amp=0.055,
                  perc=False, sparkle=True,
                  chords=[("A2 E3 G3 B3", "E4 A4 B4 E5"),
                          ("F2 C4 E4 A4", "C4 F4 A4 C5"),
                          ("C3 G3 B3 E4", "G4 B4 E5 G5"),
                          ("E2 B3 D4 G4", "B3 E4 G4 B4")]),
    "sky": dict(bar=4.0, kind="sine", arp=0.5, pad=0.05, arp_amp=0.08,
                perc=False, sparkle=True,
                chords=[("C3 E3 G3 B3", "G4 B4 E5 G5"),
                        ("A2 C3 E3 G3", "E4 G4 C5 E5"),
                        ("F2 A3 C4 E4", "C5 E5 A5 C6"),
                        ("G2 B3 D4 F3", "D5 F5 B5 D6")]),
    "volcano": dict(bar=3.6, kind="saw", arp=0.45, pad=0.045, arp_amp=0.06,
                    perc=True, sparkle=False,
                    chords=[("D2 D3 F3 A3", "D4 F4 A4 D5"),
                            ("A#1 A#2 D3 F3", "D4 F4 A#4 D5"),
                            ("G1 G2 A#2 D3", "A#3 D4 G4 A#4"),
                            ("A1 A2 C#3 E3", "C#4 E4 A4 C#5")]),
    "boss": dict(bar=3.2, kind="saw", arp=0.4, pad=0.05, arp_amp=0.075,
                 perc=True, sparkle=False,
                 chords=[("D2 D3 F3 A3", "D4 F4 A4 D5"),
                         ("D#2 D#3 F#3 A#3", "D#4 F#4 A#4 D#5"),
                         ("D2 D3 F3 A3", "D4 F4 A4 D5"),
                         ("A1 A2 C#3 E3", "A3 C#4 E4 A4")]),
    "victory": dict(bar=3.2, kind="tri", arp=0.4, pad=0.06, arp_amp=0.09,
                    perc=False, sparkle=True,
                    chords=[("C3 E3 G3 C4", "E4 G4 C5 E5"),
                            ("F2 A3 C4 F4", "A4 C5 F5 A5"),
                            ("G2 B3 D4 G4", "B4 D5 G5 B5"),
                            ("C3 E3 G3 C4", "G5 C6 E6 G5")]),
}


def _build_track(name):
    spec = _MUSIC_SPECS[name]
    if np is None:                      # 纯 Python：缩短循环，减少音符
        spec = dict(spec)
        spec["bar"] = min(2.6, spec["bar"])
        spec["arp"] = 0.8
        spec["chords"] = spec["chords"][:2]
    bar = spec["bar"]
    chords = spec["chords"]
    length = int(SR * bar * len(chords))
    tracks = []
    perc = spec["perc"]

    for i, (bass_s, arp_s) in enumerate(chords):
        start = int(SR * bar * i)
        bass = bass_s.split()
        arp = arp_s.split()
        for note in bass:
            f = _freq(note)
            if spec["kind"] == "saw":
                data = _saw(f, bar * 1.02, amp=spec["pad"], attack=0.5, decay=0.9)
            elif spec["kind"] == "tri":
                data = _tri(f, bar * 1.02, amp=spec["pad"], attack=0.7, decay=0.8)
            else:
                data = _sine(f, bar * 1.02, amp=spec["pad"], attack=0.9,
                             decay=0.55, vibrato=0.6)
            tracks.append((start, data))

        step = spec["arp"]
        count = int(bar / step)
        for k in range(count):
            note = arp[k % len(arp)]
            t0 = start + int(SR * step * k)
            amp = spec["arp_amp"] if k % 2 == 0 else spec["arp_amp"] * 0.65
            fn = _sine if spec["kind"] != "saw" else _saw
            tracks.append((t0, fn(_freq(note), 1.3, amp=amp, attack=0.01, decay=2.4)))

        if spec["sparkle"]:
            note = arp[0]
            tracks.append((start + int(SR * 2.4),
                           _sine(_freq(note) * 2, 1.8, amp=0.026, attack=0.05, decay=1.6)))

        if perc:
            beat = 0.4
            beats = int(bar / beat)
            for k in range(beats):
                t0 = start + int(SR * beat * k)
                if k % 4 == 0:
                    tracks.append((t0, _sine(58, 0.22, 0.16, 0.004, 16)))
                if k % 2 == 1:
                    tracks.append((t0, _noise(0.05, 0.045, 60, seed=11 + k)))

    buf = _mix(length, tracks)
    fade = int(SR * 0.15)
    if len(buf) > 2 * fade:
        if np is None:
            for i in range(fade):
                g = i / fade
                buf[i] *= g
                buf[-1 - i] *= g
        else:
            buf[:fade] *= np.linspace(0, 1, fade)
            buf[-fade:] *= np.linspace(1, 0, fade)
    return _to_sound(buf, 1.0, fade=False)


# --------------------------------------------------------------------------
# 音效
# --------------------------------------------------------------------------
def _build_sfx():
    sfx = {}

    # 挥砍：风声 + 金属泛音
    sfx["slash"] = _to_sound(_mix(int(SR * 0.2), [
        (0, _noise(0.18, 0.24, 22, seed=3)),
        (0, _sine(1100, 0.12, 0.1, 0.003, 24)),
        (int(SR * 0.03), _sine(1560, 0.1, 0.06, 0.003, 28)),
    ]), 0.55)
    sfx["swing"] = sfx["slash"]

    # 射箭：弓弦 + 破空
    sfx["shot"] = _to_sound(_mix(int(SR * 0.18), [
        (0, _tri(220, 0.1, 0.16, 0.002, 22)),
        (0, _noise(0.16, 0.16, 28, seed=5)),
        (int(SR * 0.02), _sine(1400, 0.1, 0.07, 0.003, 30)),
    ]), 0.5)
    sfx["arrow"] = sfx["shot"]

    # 施法：上扬泛音
    cast_len = int(SR * 0.5)
    cast = []
    for i, f in enumerate((392, 523, 659, 880)):
        cast.append((int(SR * 0.06 * i), _sine(f, 0.36, 0.1, 0.008, 5)))
    cast.append((int(SR * 0.1), _noise(0.28, 0.05, 9, seed=9)))
    sfx["spell"] = _to_sound(_mix(cast_len, cast), 0.5)
    sfx["skill"] = _to_sound(_mix(cast_len, cast), 0.6)

    # 命中：物理闷响
    sfx["hit_phys"] = _to_sound(_mix(int(SR * 0.12), [
        (0, _tri(180, 0.1, 0.28, 0.003, 26)),
        (0, _noise(0.08, 0.12, 34, seed=13)),
    ]), 0.6)
    sfx["hit"] = sfx["hit_phys"]

    # 命中：法术碎裂
    sfx["hit_magic"] = _to_sound(_mix(int(SR * 0.22), [
        (0, _noise(0.18, 0.14, 18, seed=17)),
        (0, _sine(880, 0.16, 0.12, 0.003, 18)),
        (int(SR * 0.04), _sine(1320, 0.12, 0.08, 0.003, 20)),
    ]), 0.55)

    # 暴击：明亮双音 + 碎响
    sfx["crit"] = _to_sound(_mix(int(SR * 0.3), [
        (0, _sine(1568, 0.16, 0.16, 0.002, 12)),
        (int(SR * 0.05), _sine(2093, 0.2, 0.13, 0.002, 10)),
        (0, _noise(0.14, 0.12, 20, seed=23)),
    ]), 0.6)

    # 受伤
    sfx["hurt"] = _to_sound(_mix(int(SR * 0.24), [
        (0, _tri(170, 0.22, 0.24, 0.004, 14)),
        (0, _noise(0.12, 0.1, 18, seed=29)),
    ]), 0.6)

    # 拾取 / 钥匙 / 升级
    sfx["pickup"] = _to_sound(_mix(int(SR * 0.3), [
        (0, _sine(1046, 0.14, 0.14, 0.005, 12)),
        (int(SR * 0.09), _sine(1318, 0.18, 0.12, 0.005, 10)),
    ]), 0.45)
    sfx["key"] = _to_sound(_mix(int(SR * 0.5), [
        (0, _sine(1318, 0.18, 0.13, 0.004, 8)),
        (int(SR * 0.08), _sine(1760, 0.2, 0.12, 0.004, 7)),
        (int(SR * 0.16), _sine(2093, 0.24, 0.1, 0.004, 6)),
    ]), 0.45)
    lvl = []
    for i, f in enumerate((523, 659, 784, 1046, 1318)):
        lvl.append((int(SR * 0.07 * i), _sine(f, 0.35, 0.13, 0.005, 6)))
    sfx["levelup"] = _to_sound(_mix(int(SR * 0.8), lvl), 0.55)

    # 爆炸
    sfx["boom"] = _to_sound(_mix(int(SR * 0.6), [
        (0, _noise(0.6, 0.34, 6, seed=31)),
        (0, _sine(70, 0.5, 0.22, 0.005, 6)),
    ]), 0.65)

    # 治疗
    sfx["heal"] = _to_sound(_mix(int(SR * 0.45), [
        (0, _sine(659, 0.3, 0.12, 0.01, 6)),
        (int(SR * 0.1), _sine(880, 0.32, 0.1, 0.01, 5)),
    ]), 0.42)

    # BOSS 咆哮 / 蓄力 / 开门
    sfx["boss_roar"] = _to_sound(_mix(int(SR * 0.9), [
        (0, _saw(72, 0.8, 0.26, 0.05, 3.2)),
        (0, _saw(96, 0.8, 0.16, 0.08, 3.0)),
        (0, _noise(0.7, 0.14, 4, seed=37)),
    ]), 0.6)
    sfx["boss_skill"] = _to_sound(_mix(int(SR * 0.9), [
        (0, _sine(120, 0.7, 0.2, 0.15, 2.2)),
        (0, _sine(181, 0.7, 0.12, 0.2, 2.4)),
        (int(SR * 0.3), _noise(0.4, 0.1, 6, seed=41)),
    ]), 0.55)
    sfx["door"] = _to_sound(_mix(int(SR * 0.8), [
        (0, _noise(0.7, 0.16, 4, seed=43)),
        (0, _sine(90, 0.6, 0.18, 0.05, 4)),
    ]), 0.5)
    sfx["jump"] = _to_sound(_mix(int(SR * 0.16), [
        (0, _sine(520, 0.12, 0.1, 0.004, 20)),
        (0, _noise(0.08, 0.05, 30, seed=47)),
    ]), 0.35)

    # 通关
    win = []
    for i, f in enumerate((523, 659, 784, 1046)):
        win.append((int(SR * 0.18 * i), _sine(f, 0.6, 0.16, 0.01, 2.6)))
    sfx["win"] = _to_sound(_mix(int(SR * 1.6), win), 0.55)
    return sfx


# --------------------------------------------------------------------------
# 对外接口
# --------------------------------------------------------------------------
_error = ""
_driver = ""


def _force_real_driver():
    """如果环境里残留 SDL_AUDIODRIVER=dummy（测试常用），强制换回真实驱动。"""
    env = os.environ.get("SDL_AUDIODRIVER", "")
    if env.lower() in ("dummy", "disk"):
        os.environ.pop("SDL_AUDIODRIVER", None)
        try:
            pygame.mixer.quit()
        except pygame.error:
            pass
        return f"已忽略环境变量 SDL_AUDIODRIVER={env}"
    return ""


def init():
    """初始化混音器；采样率跟随实际设备，避免音高不对或没声音。"""
    global _ready, _sfx, SR, _error
    if _ready:
        return True
    global _driver
    note = _force_real_driver()
    if pygame.mixer.get_init() is None:
        for kwargs in (dict(frequency=SR, size=-16, channels=2, buffer=1024),
                       dict(frequency=44100, size=-16, channels=2, buffer=1024),
                       dict()):
            try:
                pygame.mixer.init(**kwargs)
                break
            except pygame.error as exc:
                _error = str(exc)
                try:
                    pygame.mixer.quit()
                except pygame.error:
                    pass
        if pygame.mixer.get_init() is None:
            return False

    got = pygame.mixer.get_init()
    if got and got[0] and got[0] != SR:
        SR = got[0]          # 用设备真实采样率重建，音高才正常

    try:
        _sfx = _build_sfx()
        pygame.mixer.set_num_channels(32)
        pygame.mixer.set_reserved(2)      # 0/1 号声道留给音乐，音效抢不走
        global _music_channel
        _music_channel = pygame.mixer.Channel(0)
        _ready = True
        _error = ""
        _driver = note
    except Exception as exc:      # pragma: no cover
        _error = str(exc)
        _ready = False
    return _ready


def diagnostics():
    """返回一段可直接贴出来的音频诊断信息。"""
    lines = []
    try:
        import numpy as _np
        lines.append(f"numpy: {_np.__version__}")
    except Exception:
        lines.append("numpy: 未安装（已启用纯 Python 合成）")
    lines.append(f"SDL_AUDIODRIVER: {os.environ.get('SDL_AUDIODRIVER', '(未设置)')}")
    lines.append(f"mixer.get_init(): {pygame.mixer.get_init()}")
    try:
        lines.append(f"mixer channels: {pygame.mixer.get_num_channels()}")
    except Exception:
        pass
    lines.append(f"platform: {sys.platform}")
    lines.append(f"ready: {_ready}")
    lines.append(f"status: {status()}")
    if _driver:
        lines.append(f"note: {_driver}")
    if not _ready and _error:
        lines.append(f"error: {_error}")
    return "\n".join(lines)


def test_tone():
    """播放一个测试音（菜单里的“测试声音”按钮用）。"""
    if not _ready:
        return False
    play("key", 1.0)
    return True


def status():
    """给 UI 显示的音频状态。"""
    if _ready:
        got = pygame.mixer.get_init()
        rate = got[0] if got else SR
        return f"音效 {rate // 1000}kHz · 背景音乐已关闭"
    return f"音频不可用：{_error or '未知原因'}"


def available():
    return _ready


def play_music(name="menu", force=False):
    """背景音乐默认关闭，只记录状态并确保不会残留播放。"""
    global _music_playing, _music_current, _music_switch_at
    _music_current = name
    _music_playing = None
    if not _ready:
        return
    try:
        if _music_channel is not None:
            _music_channel.stop()
    except pygame.error:
        pass
    _music_switch_at = pygame.time.get_ticks() / 1000.0


def stop_music():
    global _music_playing, _music_current
    try:
        if _music_channel is not None:
            _music_channel.fadeout(300)
        elif _music_playing is not None:
            _music_playing.fadeout(300)
    except pygame.error:
        pass
    _music_playing = None
    _music_current = None


def play(name, volume=1.0):
    if not _ready or not _sfx_on:
        return
    sound = _sfx.get(name)
    if sound is None:
        return
    cooldown = _SFX_COOLDOWN_MS.get(name, 0)
    if cooldown > 0:
        now = pygame.time.get_ticks()
        last = _sfx_last_played.get(name, -10 ** 9)
        if now - last < cooldown:
            return
        _sfx_last_played[name] = now
    try:
        sound.set_volume(min(1.0, _sfx_volume * volume))
        if sound.play() is None:
            ch = pygame.mixer.find_channel(True)   # 抢一个最老的声道
            if ch is not None:
                ch.set_volume(sound.get_volume())
                ch.play(sound)
    except pygame.error:
        pass


def set_sfx_volume(value):
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, value))


def sfx_volume():
    return _sfx_volume


def music_volume():
    return _music_volume


def set_music_volume(value):
    global _music_volume
    _music_volume = max(0.0, min(1.0, value))
    try:
        if _music_channel is not None:
            _music_channel.set_volume(_music_volume)
        if _music_playing is not None:
            _music_playing.set_volume(_music_volume)
    except pygame.error:
        pass


def music_name():
    return _music_current


def music_enabled():
    return False


def sfx_enabled():
    return _sfx_on


def set_music_enabled(_on):
    global _music_on
    _music_on = False
    try:
        if _music_channel is not None:
            _music_channel.fadeout(120)
    except pygame.error:
        pass


def set_sfx_enabled(on):
    global _sfx_on
    _sfx_on = bool(on)


def ensure_music():
    return


def prewarm_music(*_names):
    return
