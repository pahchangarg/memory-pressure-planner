"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    MEMORY_PRESSURE = "memory_pressure"
    KILL_ORDER = "kill_order"
    CLOSE_APPS = "close_apps"


class Task(Enum):
    MEMORY_PRESSURE = "memory-pressure"
    KILL_ORDER = "kill-order"
    CLOSE_APPS = "close-apps"
    FREE_MEMORY = "free-memory"


class AppClass(Enum):
    FOREGROUND = "foreground"
    VISIBLE = "visible"
    SERVICE = "service"
    BACKGROUND = "background"
    CACHED = "cached"


class Pressure(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


APPS = "The open apps, 0 to 40, each name once"
TOTAL = "The machine's RAM in MB, 512 to 1048576"
OS = "The MB the operating system itself uses, 0 to total_mb"
LEVEL = "normal when used_mb is at most 80% of total_mb; warning above 80% up to 95%; critical above 95%"


@dataclass
class App(Output):
    name: Annotated[str, "The app's name, unique among the apps"]
    memory_mb: Annotated[int, "The RAM it uses, in MB, 1 to 65536"]
    app_class: Annotated[
        AppClass,
        "foreground (the app in use), visible (on screen), service (working in the background, e.g. playing music),"
        " background (open but unused) or cached (kept only to reopen fast)",
    ]
    idle_s: Annotated[int, "Seconds since it was last used, 0 or more"]
    unsaved: Annotated[bool, "Whether it holds unsaved work"]
    reopen_s: Annotated[int, "Seconds it takes to reopen once closed, 1 to 600: the cost of closing it"]


@dataclass
class PressureInput(Output):
    total_mb: Annotated[int, TOTAL]
    os_mb: Annotated[int, OS]
    apps: Annotated[list[App], APPS]


@dataclass
class PressureOutput(Output):
    used_mb: Annotated[int, "os_mb plus every app's memory_mb"]
    free_mb: Annotated[int, "total_mb minus used_mb; negative when the machine is swapping"]
    level: Annotated[Pressure, LEVEL]


@dataclass
class KillOrderInput(Output):
    apps: Annotated[list[App], APPS]


@dataclass
class KillOrderOutput(Output):
    order: Annotated[
        list[str],
        "Every app that is not protected, in the order a low-memory killer closes them: cached, then background, then"
        " service, then visible; within a class the most memory first, then the longest idle, then by name",
    ]
    protected: Annotated[list[str], "The protected apps (the foreground app and apps with unsaved work), in the apps order"]


@dataclass
class CloseInput(Output):
    total_mb: Annotated[int, TOTAL]
    os_mb: Annotated[int, OS]
    apps: Annotated[list[App], APPS]
    close: Annotated[list[str], "Names of apps to close, each once; none may be protected"]


@dataclass
class CloseOutput(Output):
    freed_mb: Annotated[int, "The memory the closed apps used"]
    used_mb: Annotated[int, "used_mb after closing them"]
    free_mb: Annotated[int, "total_mb minus the new used_mb"]
    level: Annotated[Pressure, LEVEL]
    reopen_s: Annotated[int, "The closed apps' reopen_s added up: the time lost reopening them"]
    kept: Annotated[list[str], "The apps still open, in the apps' order"]


@dataclass
class FreeInput(Output):
    total_mb: Annotated[int, TOTAL]
    os_mb: Annotated[int, OS]
    apps: Annotated[list[App], APPS]
    target_mb: Annotated[int, "used_mb must end at or below this many MB, 0 to total_mb"]


@dataclass
class FreeOutput(Output):
    possible: Annotated[bool, "Whether closing apps that are not protected can bring used_mb to target_mb or below"]
    close: Annotated[
        list[str],
        "Apps to close, each once and none protected, that bring used_mb to target_mb or below with the smallest total"
        " reopen_s; empty when nothing needs closing or it is not possible",
    ]
    reopen_s: Annotated[int, "The closed apps' reopen_s added up; 0 when none are closed"]


TOOLS = {
    Tool.MEMORY_PRESSURE: (PressureInput, PressureOutput),
    Tool.KILL_ORDER: (KillOrderInput, KillOrderOutput),
    Tool.CLOSE_APPS: (CloseInput, CloseOutput),
}
TASKS = {
    Task.MEMORY_PRESSURE: (PressureInput, PressureOutput),
    Task.KILL_ORDER: (KillOrderInput, KillOrderOutput),
    Task.CLOSE_APPS: (CloseInput, CloseOutput),
    Task.FREE_MEMORY: (FreeInput, FreeOutput),
}
