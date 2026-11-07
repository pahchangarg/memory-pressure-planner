"""What the tools share: input checks, memory used, the pressure level and which apps may be closed."""

from __future__ import annotations

from contract import App, AppClass, Pressure

MAX_APPS = 40
# A low-memory killer closes cached apps first and visible ones last; it never closes the foreground app.
CLOSE_FIRST = [AppClass.CACHED, AppClass.BACKGROUND, AppClass.SERVICE, AppClass.VISIBLE]


def check_apps(apps: list[App]) -> None:
    if len(apps) > MAX_APPS:
        raise ValueError(f"apps must be at most {MAX_APPS}")
    names = [app.name for app in apps]
    if any(not name.strip() for name in names) or len(set(names)) != len(names):
        raise ValueError("app names must be unique and not blank")
    for app in apps:
        if not 1 <= app.memory_mb <= 65_536:
            raise ValueError(f"{app.name}: memory_mb must be 1 to 65536")
        if app.idle_s < 0:
            raise ValueError(f"{app.name}: idle_s must be 0 or more")
        if not 1 <= app.reopen_s <= 600:
            raise ValueError(f"{app.name}: reopen_s must be 1 to 600")
    if sum(app.app_class is AppClass.FOREGROUND for app in apps) > 1:
        raise ValueError("at most one app can be in the foreground")


def check_machine(total_mb: int, os_mb: int, apps: list[App]) -> None:
    if not 512 <= total_mb <= 1_048_576:
        raise ValueError("total_mb must be 512 to 1048576")
    if not 0 <= os_mb <= total_mb:
        raise ValueError("os_mb must be 0 to total_mb")
    check_apps(apps)


def used(os_mb: int, apps: list[App]) -> int:
    return os_mb + sum(app.memory_mb for app in apps)


def level(used_mb: int, total_mb: int) -> Pressure:
    # Compared in whole numbers: used / total <= 80 / 100 is used * 100 <= 80 * total.
    if used_mb * 100 <= 80 * total_mb:
        return Pressure.NORMAL
    if used_mb * 100 <= 95 * total_mb:
        return Pressure.WARNING
    return Pressure.CRITICAL


def is_protected(app: App) -> bool:
    return app.app_class is AppClass.FOREGROUND or app.unsaved


def check_close(apps: list[App], close: list[str]) -> list[App]:
    """The apps named in ``close``, after checking each is known, named once and not protected."""
    by_name = {app.name: app for app in apps}
    if len(set(close)) != len(close):
        raise ValueError("close must name each app once")
    for name in close:
        if name not in by_name:
            raise ValueError(f"no open app is named {name!r}")
        if is_protected(by_name[name]):
            raise ValueError(f"{name} is protected: it is in the foreground or has unsaved work")
    return [by_name[name] for name in close]
