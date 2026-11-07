from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output

from contract import CloseInput, KillOrderInput, Pressure, PressureInput
from plugin import close_apps, kill_order, memory_pressure


def app(name: str, memory: int, kind: str, idle: int = 0, unsaved: bool = False, reopen: int = 5) -> dict:
    return {"name": name, "memory_mb": memory, "app_class": kind, "idle_s": idle, "unsaved": unsaved, "reopen_s": reopen}


# A 16 GB laptop at 98% use.
APPS = [
    app("Chrome", 4200, "foreground", 0, False, 8),
    app("Slack", 900, "background", 600, False, 6),
    app("Spotify", 700, "service", 30, False, 5),
    app("VSCode", 2500, "visible", 120, True, 10),
    app("Photoshop", 3100, "background", 1800, False, 25),
    app("Zoom", 1200, "cached", 3600, False, 7),
    app("Notes", 300, "cached", 7200, False, 2),
    app("Docker", 2000, "service", 900, False, 30),
]
LAPTOP = {"total_mb": 16384, "os_mb": 1200, "apps": APPS}


def pressure(total: int, os_mb: int, apps: list[dict]) -> tuple:
    made = memory_pressure(build_output({"total_mb": total, "os_mb": os_mb, "apps": apps}, PressureInput), Path("."))
    return made.used_mb, made.free_mb, made.level


def test_pressure_levels_and_their_edges() -> None:
    assert pressure(16384, 1200, APPS) == (16100, 284, Pressure.CRITICAL)
    assert pressure(10000, 8000, []) == (8000, 2000, Pressure.NORMAL)  # exactly 80%
    assert pressure(10000, 8001, []) == (8001, 1999, Pressure.WARNING)
    assert pressure(10000, 9500, []) == (9500, 500, Pressure.WARNING)  # exactly 95%
    assert pressure(10000, 9501, []) == (9501, 499, Pressure.CRITICAL)
    assert pressure(1000, 900, [app("Big", 300, "cached")]) == (1200, -200, Pressure.CRITICAL)  # swapping


def order(apps: list[dict]) -> tuple:
    made = kill_order(build_output({"apps": apps}, KillOrderInput), Path("."))
    return made.order, made.protected


def test_kill_order_and_protected_apps() -> None:
    assert order(APPS) == (["Zoom", "Notes", "Photoshop", "Slack", "Docker", "Spotify"], ["Chrome", "VSCode"])
    tied = [app("B", 500, "cached", 10), app("A", 500, "cached", 20), app("D", 500, "cached", 20), app("C", 500, "cached", 20)]
    assert order(tied) == (["A", "C", "D", "B"], [])  # longest idle first, then by name
    assert order([app("Doc", 100, "cached", 0, True)]) == ([], ["Doc"])  # unsaved work is protected in any class


def test_close_apps_reports_what_it_frees() -> None:
    made = close_apps(build_output({**LAPTOP, "close": ["Zoom", "Notes"]}, CloseInput), Path("."))
    assert (made.freed_mb, made.used_mb, made.free_mb, made.level, made.reopen_s) == (1500, 14600, 1784, Pressure.WARNING, 9)
    assert made.kept == ["Chrome", "Slack", "Spotify", "VSCode", "Photoshop", "Docker"]
    made = close_apps(build_output({**LAPTOP, "close": []}, CloseInput), Path("."))
    assert (made.freed_mb, made.used_mb, made.reopen_s) == (0, 16100, 0)


@pytest.mark.parametrize(
    ("close", "message"),
    [(["Chrome"], "protected"), (["VSCode"], "protected"), (["Zoom", "Zoom"], "once"), (["Excel"], "no open app")],
)
def test_close_apps_refuses_what_it_may_not_close(close: list[str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        close_apps(build_output({**LAPTOP, "close": close}, CloseInput), Path("."))


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ({"apps": [APPS[1], APPS[1]]}, "unique"),
        ({"apps": [app("X", 0, "cached")]}, "memory_mb"),
        ({"apps": [app("X", 10, "cached", reopen=0)]}, "reopen_s"),
        ({"apps": [app("X", 10, "cached", idle=-1)]}, "idle_s"),
        ({"apps": [app("X", 10, "foreground"), app("Y", 10, "foreground")]}, "foreground"),
        ({"os_mb": 20000}, "os_mb"),
        ({"total_mb": 100}, "total_mb"),
    ],
)
def test_refuses_a_malformed_machine(bad: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        memory_pressure(build_output({**LAPTOP, **bad}, PressureInput), Path("."))
