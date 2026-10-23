"""save.py —— 存档：3 个角色存档槽，支持不同职业分别保存。

桌面端写 JSON 文件；网页/手机（pygbag）自动改用浏览器 localStorage。
所有失败都静默降级，不会影响游戏运行。
"""
import json
import os
import time

_KEY = "treasure_save"
_PREF_KEY = "treasure_prefs"
SLOT_COUNT = 3
_PATH = os.environ.get("TREASURE_SAVE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "savegame.json")
_PREF_PATH = os.path.join(os.path.dirname(_PATH), "prefs.json")


def _browser_window():
    try:
        import platform as _platform
        return getattr(_platform, "window", None)
    except Exception:
        return None


def _read_raw():
    win = _browser_window()
    if win is not None:
        try:
            raw = win.localStorage.getItem(_KEY)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_raw(data):
    text = json.dumps(data, ensure_ascii=False)
    win = _browser_window()
    if win is not None:
        try:
            win.localStorage.setItem(_KEY, text)
            return True
        except Exception:
            pass
    try:
        tmp = _PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, _PATH)
        return True
    except Exception:
        return False


def load_all():
    """读取全部存档槽：{"version":2, "active":0, "slots":[slot|None]*3}。"""
    raw = _read_raw()
    if not raw:
        return {"version": 2, "active": 0, "slots": [None] * SLOT_COUNT}

    if "slots" in raw and isinstance(raw["slots"], list):
        slots = list(raw["slots"])[:SLOT_COUNT]
        while len(slots) < SLOT_COUNT:
            slots.append(None)
        active = int(raw.get("active", 0)) if str(raw.get("active", 0)).isdigit() else 0
        return {"version": 2, "active": max(0, min(SLOT_COUNT - 1, active)), "slots": slots}

    # 兼容旧版单存档：放进 1 号槽
    slot = {k: raw.get(k) for k in ("weapon", "cleared", "player")}
    if raw.get("saved_at"):
        slot["saved_at"] = raw["saved_at"]
    slots = [slot] + [None] * (SLOT_COUNT - 1)
    return {"version": 2, "active": 0, "slots": slots}


def write_all(data):
    data = dict(data)
    data["version"] = 2
    data["slots"] = (list(data.get("slots", [])) + [None] * SLOT_COUNT)[:SLOT_COUNT]
    return _write_raw(data)


def write_slot(index, slot):
    data = load_all()
    index = max(0, min(SLOT_COUNT - 1, int(index)))
    slot = dict(slot or {})
    slot["saved_at"] = int(time.time())
    data["slots"][index] = slot
    data["active"] = index
    return write_all(data)


def delete_slot(index):
    data = load_all()
    index = max(0, min(SLOT_COUNT - 1, int(index)))
    data["slots"][index] = None
    return write_all(data)


def set_active(index):
    data = load_all()
    data["active"] = max(0, min(SLOT_COUNT - 1, int(index)))
    return write_all(data)


def slot_info(slot):
    """给 UI 用的摘要。"""
    if not slot or not isinstance(slot, dict):
        return {"empty": True, "title": "空存档", "sub": "点击选择职业开始", "level": 0,
                "cleared": 0, "weapon": None, "time": ""}
    player = slot.get("player") or {}
    ts = slot.get("saved_at") or 0
    when = time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else ""
    return {
        "empty": False,
        "level": int(player.get("level", 1)),
        "weapon": player.get("weapon_type", slot.get("weapon")),
        "cleared": len(slot.get("cleared") or []),
        "time": when,
        "title": f"Lv.{int(player.get('level', 1))}",
        "sub": f"已通关 {len(slot.get('cleared') or [])}/16",
    }


# ---------- 兼容旧接口（单槽 = 当前激活槽） ----------
def load():
    data = load_all()
    return data["slots"][data["active"]]


def save(data):
    info = load_all()
    return write_slot(info["active"], data)


def exists():
    info = load_all()
    return any(info["slots"])


def remove():
    for i in range(SLOT_COUNT):
        delete_slot(i)


# ---------------- 偏好设置（音乐/音效开关等） ----------------
def load_prefs():
    win = _browser_window()
    if win is not None:
        try:
            raw = win.localStorage.getItem(_PREF_KEY)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    try:
        with open(_PREF_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_prefs(data):
    text = json.dumps(data or {}, ensure_ascii=False)
    win = _browser_window()
    if win is not None:
        try:
            win.localStorage.setItem(_PREF_KEY, text)
            return True
        except Exception:
            pass
    try:
        with open(_PREF_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception:
        return False
