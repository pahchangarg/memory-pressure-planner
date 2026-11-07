"""Checks shared by the verifiers: the rules worked out apart from the tools' code."""

from fractions import Fraction

from contract import AppClass, Pressure

MAX_APPS = 40
# Classes in the order a low-memory killer closes them; the foreground app is never closed.
RANK = {AppClass.CACHED: 0, AppClass.BACKGROUND: 1, AppClass.SERVICE: 2, AppClass.VISIBLE: 3}


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def first_problem(*problems):
    return next((problem for problem in problems if problem), None)


def apps_problem(apps):
    if len(apps) > MAX_APPS:
        return f"apps must be at most {MAX_APPS}"
    names = [app.name for app in apps]
    if len(set(names)) != len(names) or any(not name.strip() for name in names):
        return "app names must be unique and not blank"
    for app in apps:
        if not 1 <= app.memory_mb <= 65_536:
            return f"{app.name}: memory_mb must be 1 to 65536"
        if app.idle_s < 0:
            return f"{app.name}: idle_s must be 0 or more"
        if not 1 <= app.reopen_s <= 600:
            return f"{app.name}: reopen_s must be 1 to 600"
    if len([app for app in apps if app.app_class == AppClass.FOREGROUND]) > 1:
        return "at most one app can be in the foreground"
    return None


def machine_problem(total_mb, os_mb, apps):
    if not 512 <= total_mb <= 1_048_576:
        return "total_mb must be 512 to 1048576"
    if not 0 <= os_mb <= total_mb:
        return "os_mb must be 0 to total_mb"
    return apps_problem(apps)


def used(os_mb, apps):
    total = os_mb
    for app in apps:
        total += app.memory_mb
    return total


def level(used_mb, total_mb):
    share = Fraction(used_mb, total_mb)
    if share <= Fraction(4, 5):
        return Pressure.NORMAL
    if share <= Fraction(19, 20):
        return Pressure.WARNING
    return Pressure.CRITICAL


def protected(app):
    return app.app_class == AppClass.FOREGROUND or app.unsaved


def closes_before(one, other):
    """Whether a low-memory killer closes ``one`` before ``other``."""
    if RANK[one.app_class] != RANK[other.app_class]:
        return RANK[one.app_class] < RANK[other.app_class]
    if one.memory_mb != other.memory_mb:
        return one.memory_mb > other.memory_mb
    if one.idle_s != other.idle_s:
        return one.idle_s > other.idle_s
    return one.name < other.name


def kill_order(apps):
    """The closable apps' names, by picking the next to close one at a time."""
    left = [app for app in apps if not protected(app)]
    order = []
    while left:
        pick = left[0]
        for app in left[1:]:
            if closes_before(app, pick):
                pick = app
        order.append(pick.name)
        left = [app for app in left if app.name != pick.name]
    return order


def close_problem(apps, close):
    names = {app.name: app for app in apps}
    if len(set(close)) != len(close):
        return "close must name each app once"
    for name in close:
        if name not in names:
            return f"no open app is named {name!r}"
        if protected(names[name]):
            return f"{name} is protected: it is in the foreground or has unsaved work"
    return None


def cheapest(apps, need_mb):
    """The smallest total reopen_s of closable apps freeing at least need_mb, or None if none do.

    most[c] is the most memory a set of apps with total reopen_s exactly c frees (-1: no such set).
    """
    if need_mb <= 0:
        return 0
    closable = [app for app in apps if not protected(app)]
    budget = sum(app.reopen_s for app in closable)
    most = [-1] * (budget + 1)
    most[0] = 0
    for app in closable:
        for cost in range(budget, app.reopen_s - 1, -1):
            before = most[cost - app.reopen_s]
            if before >= 0 and before + app.memory_mb > most[cost]:
                most[cost] = before + app.memory_mb
    return next((cost for cost in range(budget + 1) if most[cost] >= need_mb), None)
