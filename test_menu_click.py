"""Headless regression test: menu clicks must start the game, and level transition must not crash."""
import os, sys, asyncio

os.environ["TREASURE_SAVE"] = "/tmp/treasure_test_save.json"
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
import main as game_main

RealLevel = game_main.Level
instances = []


def LevelSpy(*args, **kwargs):
    lv = RealLevel(*args, **kwargs)
    instances.append(lv)
    return lv


game_main.Level = LevelSpy


def run(clicks, frames=25, open_door=False, label=""):
    """clicks: list of (frame_index, pos). A final QUIT ends the loop."""
    instances.clear()
    script = {}
    for f, pos in clicks:
        script.setdefault(f, []).append(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})
        )
    script.setdefault(frames, []).append(pygame.event.Event(pygame.QUIT))

    counter = {"n": 0}
    errors = []

    def fake_get():
        i = counter["n"]
        counter["n"] += 1
        if open_door and instances and i in (5, 6):
            lv = instances[-1]
            # 新规则：必须拿到钥匙并击杀本关 BOSS 才能过门
            lv.has_key = True
            lv.boss_defeated = True
            lv._refresh_door()
            lv.player.rect.center = lv.door_rect.center
        return script.get(i, [])

    game_main.pygame.event.get = fake_get
    try:
        asyncio.run(game_main.main())
    except Exception as exc:  # noqa: BLE001
        errors.append(exc)
    return list(instances), errors


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail else ""))
    if not cond:
        raise SystemExit(1)


# 1) Clicking each profession card starts a level with the right weapon type
for pos, expected in [((220, 320), 1), ((470, 320), 2), ((720, 320), 3)]:
    lv, errs = run([(0, pos)], label=str(pos))
    check(f"click {pos} starts game, no exception", not errs, repr(errs))
    check(f"click {pos} -> weapon_type {expected}",
          lv and lv[0].player.weapon_type == expected,
          f"levels={len(lv)}")

# 2) Clicking empty background must NOT start the game
lv, errs = run([(0, (40, 40))])
check("click on empty area does not start game", not errs and len(lv) == 0, f"levels={len(lv)}")

# 3) Walking through the portal (uses random.randint) must advance levels without crashing
lv, errs = run([(0, (220, 320))], frames=12, open_door=True)
check("key+BOSS 达成后可以过门进下一关", not errs and len(lv) >= 2, f"levels={len(lv)} errors={errs!r}")

# 4) Keyboard shortcut still works
pygame.event.get = lambda: []
instances.clear()
script = {0: [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_2, "mod": 0, "unicode": "2"})],
          6: [pygame.event.Event(pygame.QUIT)]}
counter = {"n": 0}


def kb_get():
    i = counter["n"]
    counter["n"] += 1
    return script.get(i, [])


game_main.pygame.event.get = kb_get
errs = []
try:
    asyncio.run(game_main.main())
except Exception as exc:  # noqa: BLE001
    errs.append(exc)
check("key 2 starts game as archer", not errs and instances and instances[0].player.weapon_type == 2,
      f"levels={len(instances)} errors={errs!r}")

print("\nALL CHECKS PASSED")
