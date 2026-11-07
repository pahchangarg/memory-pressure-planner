"""close_apps and the close-apps task."""

from .checks import close_problem, first_problem, level, machine_problem, result, used


def input_problem(value):
    return first_problem(machine_problem(value.total_mb, value.os_mb, value.apps), close_problem(value.apps, value.close))


def verify_input(value):
    problem = input_problem(value)
    return result(problem is None, problem or "a valid set of apps to close")


def verify_output(given, made, workspace):
    problem = input_problem(given)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    kept = [app for app in given.apps if app.name not in given.close]
    gone = [app for app in given.apps if app.name in given.close]
    used_mb = used(given.os_mb, kept)
    want = (
        sum(app.memory_mb for app in gone),
        used_mb,
        given.total_mb - used_mb,
        level(used_mb, given.total_mb),
        sum(app.reopen_s for app in gone),
        [app.name for app in kept],
    )
    got = (made.freed_mb, made.used_mb, made.free_mb, made.level, made.reopen_s, made.kept)
    if got != want:
        return result(False, f"closing them frees {want[0]} MB, leaving {want[1]} MB used ({want[3].value}), "
                             f"{want[4]} s to reopen")
    return result(True, f"freed {want[0]} MB: {want[3].value}", freed_mb=want[0])
