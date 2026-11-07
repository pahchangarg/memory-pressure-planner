from __future__ import annotations

import itertools
import random
from pathlib import Path

import pytest
from slimconfig import build_output, plain_output
from test_tools import APPS, LAPTOP, app

import verifier
from contract import TASKS, TOOLS, CloseInput, KillOrderInput, PressureInput, Task, Tool
from plugin import close_apps, kill_order, memory_pressure
from verifier.checks import cheapest, protected


def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_task(task: str, arguments: dict, output: dict, workspace: Path) -> dict:
    given, made = TASKS[Task(task)]
    return verifier.verify_task(task, build_output(arguments, given), build_output(output, made), None, str(workspace))


def test_approves_the_tools_own_outputs(tmp_path: Path) -> None:
    for machine in (LAPTOP, {"total_mb": 10000, "os_mb": 8000, "apps": []}, {"total_mb": 10000, "os_mb": 9500, "apps": []}):
        made = plain_output(memory_pressure(build_output(machine, PressureInput), tmp_path))
        assert verify_task("memory-pressure", machine, made, tmp_path)["valid"] is True
    made = plain_output(kill_order(build_output({"apps": APPS}, KillOrderInput), tmp_path))
    assert verify_task("kill-order", {"apps": APPS}, made, tmp_path)["valid"] is True
    for close in ([], ["Zoom", "Notes"], ["Photoshop", "Docker", "Slack"]):
        request = {**LAPTOP, "close": close}
        made = plain_output(close_apps(build_output(request, CloseInput), tmp_path))
        assert verify_task("close-apps", request, made, tmp_path)["valid"] is True


def test_refuses_wrong_tool_outputs(tmp_path: Path) -> None:
    at_80 = {"total_mb": 10000, "os_mb": 8000, "apps": []}
    assert "normal" in verify_task("memory-pressure", at_80, {"used_mb": 8000, "free_mb": 2000, "level": "warning"}, tmp_path)["message"]
    made = plain_output(kill_order(build_output({"apps": APPS}, KillOrderInput), tmp_path))
    smallest_first = {**made, "order": ["Notes", "Zoom", *made["order"][2:]]}
    assert "kill order is" in verify_task("kill-order", {"apps": APPS}, smallest_first, tmp_path)["message"]
    unsafe = {"order": [*made["order"], "VSCode"], "protected": ["Chrome"]}
    assert "protected apps are" in verify_task("kill-order", {"apps": APPS}, unsafe, tmp_path)["message"]
    request = {**LAPTOP, "close": ["Zoom", "Notes"]}
    made = plain_output(close_apps(build_output(request, CloseInput), tmp_path))
    assert verify_task("close-apps", request, {**made, "level": "normal"}, tmp_path)["valid"] is False
    assert verify_task("close-apps", request, {**made, "reopen_s": 7}, tmp_path)["valid"] is False


NORMAL = {**LAPTOP, "target_mb": 13107}  # 80% of 16384 MB, rounded down: 2993 MB must go


def free(close: list[str], arguments: dict = NORMAL, possible: bool = True) -> dict:
    cost = sum(a["reopen_s"] for a in arguments["apps"] if a["name"] in close)
    return {"possible": possible, "close": close, "reopen_s": cost}


def test_approves_the_cheapest_set_to_close(tmp_path: Path) -> None:
    # Four small apps (20 s) beat Photoshop alone (25 s) and the kill order's Zoom, Notes, Photoshop (34 s).
    assert verify_task("free-memory", NORMAL, free(["Zoom", "Slack", "Spotify", "Notes"]), tmp_path)["valid"] is True
    assert verify_task("free-memory", NORMAL, free(["Notes", "Spotify", "Slack", "Zoom"]), tmp_path)["valid"] is True
    exact = {**LAPTOP, "target_mb": 13000}  # those four free exactly the 3100 MB needed
    assert verify_task("free-memory", exact, free(["Zoom", "Slack", "Spotify", "Notes"], exact), tmp_path)["valid"] is True
    under = {**LAPTOP, "target_mb": 16384}
    assert verify_task("free-memory", under, free([], under), tmp_path)["valid"] is True
    hopeless = {**LAPTOP, "target_mb": 5000}  # 11100 MB must go; closable apps hold 8200
    assert verify_task("free-memory", hopeless, free([], hopeless, False), tmp_path)["valid"] is True


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (free(["Photoshop"]), "25 s to reopen, but 20 s is enough"),
        (free(["Zoom", "Notes", "Photoshop"]), "34 s to reopen, but 20 s is enough"),
        (free(["Zoom", "Slack", "Spotify"]), "frees 2800 MB, but 2993 MB must go"),
        (free(["Chrome"]), "protected"),
        (free(["VSCode", "Notes"]), "protected"),
        (free(["Zoom", "Zoom"]), "once"),
        ({**free(["Zoom", "Slack", "Spotify", "Notes"]), "reopen_s": 19}, "take 20 s to reopen"),
        (free([], NORMAL, False), "can be reached for 20 s"),
    ],
)
def test_refuses_a_wrong_choice(tmp_path: Path, output: dict, message: str) -> None:
    verdict = verify_task("free-memory", NORMAL, output, tmp_path)
    assert verdict["valid"] is False and message in verdict["message"]


def test_refuses_closing_when_nothing_must_go_or_claiming_the_impossible(tmp_path: Path) -> None:
    under = {**LAPTOP, "target_mb": 16384}
    assert "0 s is enough" in verify_task("free-memory", under, free(["Notes"], under), tmp_path)["message"]
    hopeless = {**LAPTOP, "target_mb": 5000}
    claimed = free(["Zoom", "Notes", "Photoshop", "Slack", "Docker", "Spotify"], hopeless)
    assert "frees too little" in verify_task("free-memory", hopeless, claimed, tmp_path)["message"]
    bad_target = {**LAPTOP, "target_mb": 20000}
    assert "target_mb" in verify_task("free-memory", bad_target, free([]), tmp_path)["message"]


def test_the_cheapest_by_cost_per_mb_is_not_always_cheapest(tmp_path: Path) -> None:
    # A and B cost less per MB than C, but C alone covers the 1500 MB for 9 s against their 10 s.
    small = {"total_mb": 4096, "os_mb": 1000, "target_mb": 3000,
             "apps": [app("A", 1000, "cached", reopen=5), app("B", 1000, "cached", reopen=5), app("C", 1500, "background", reopen=9)]}
    assert verify_task("free-memory", small, free(["C"], small), tmp_path)["valid"] is True
    assert "10 s to reopen, but 9 s" in verify_task("free-memory", small, free(["A", "B"], small), tmp_path)["message"]


def test_cheapest_matches_brute_force_on_random_machines() -> None:
    generator = random.Random(480)
    for _ in range(200):
        kinds = ["cached", "background", "service", "visible"]
        listed = [app(f"app{i}", generator.randint(1, 3000), generator.choice(kinds), unsaved=generator.random() < 0.15,
                      reopen=generator.randint(1, 40)) for i in range(generator.randint(0, 9))]
        apps = build_output({"apps": listed}, KillOrderInput).apps
        need = generator.randint(-500, 12000)
        closable = [a for a in apps if not protected(a)]
        costs = [
            sum(a.reopen_s for a in chosen)
            for size in range(len(closable) + 1)
            for chosen in itertools.combinations(closable, size)
            if sum(a.memory_mb for a in chosen) >= need
        ]
        assert cheapest(apps, need) == (min(costs) if costs else None)


def test_checks_what_the_types_cannot_say() -> None:
    assert verify_input("memory_pressure", LAPTOP)["valid"]
    assert not verify_input("memory_pressure", {**LAPTOP, "os_mb": -1})["valid"]
    assert not verify_input("kill_order", {"apps": [APPS[0], APPS[0]]})["valid"]
    assert not verify_input("kill_order", {"apps": [app("X", 70000, "cached")]})["valid"]
    assert verify_input("close_apps", {**LAPTOP, "close": ["Zoom"]})["valid"]
    assert not verify_input("close_apps", {**LAPTOP, "close": ["Chrome"]})["valid"]
    assert not verify_input("close_apps", {**LAPTOP, "close": ["Excel"]})["valid"]
