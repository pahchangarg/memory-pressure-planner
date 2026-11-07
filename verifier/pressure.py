"""memory_pressure and the memory-pressure task."""

from .checks import level, machine_problem, result, used


def input_problem(value):
    return machine_problem(value.total_mb, value.os_mb, value.apps)


def verify_input(value):
    problem = input_problem(value)
    return result(problem is None, problem or "a valid machine")


def verify_output(given, made, workspace):
    problem = input_problem(given)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    used_mb = used(given.os_mb, given.apps)
    want = (used_mb, given.total_mb - used_mb, level(used_mb, given.total_mb))
    if (made.used_mb, made.free_mb, made.level) != want:
        return result(False, f"the machine uses {want[0]} MB, {want[1]} MB free: {want[2].value}")
    return result(True, f"{used_mb} MB used of {given.total_mb}: {want[2].value}", level=want[2].value)
