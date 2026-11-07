# Memory Pressure Planner

A `nanoagent.plugin/v0001` plugin, made from the structure of NanoAgent's
reference plugin, [arxiv-source](https://github.com/zeyuyang8/arxiv-source).
When too many apps are open, the system runs short of RAM. This plugin takes a
snapshot of a machine (its RAM, the operating system's share and each open
app) and works out how hard memory is pressed, which apps a low-memory killer
would close first, and the cheapest set of apps to close to get back under a
target. It never touches a real machine: every answer is a function of the
snapshot given, so it can be checked exactly.

## Tools

| Tool | Does | Code |
|---|---|---|
| `memory_pressure` | Adds up the RAM used, the RAM free and the pressure level: normal up to 80% of total, warning up to 95%, critical above | `src/plugin/pressure.py` |
| `kill_order` | Orders the closable apps as a low-memory killer closes them (cached, background, service, visible; most memory, then longest idle, then name) and lists the protected ones | `src/plugin/order.py` |
| `close_apps` | Closes the named apps, refusing protected ones, and reports the memory freed, the new level and the seconds lost reopening them | `src/plugin/close.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `memory-pressure` | Shows how hard the machine's memory is pressed | `tool`, with `memory_pressure` |
| `kill-order` | Shows which apps would be closed first | `tool`, with `kill_order` |
| `close-apps` | Closes some apps and shows what it frees | `tool`, with `close_apps` |
| `free-memory` | Chooses the apps to close to get under a target with the least total reopen time | `agent`, with `memory_pressure`, `kill_order` and `close_apps` |

The rules:

- Memory is whole MB. Used memory is the operating system's share plus every
  open app's. A level is compared exactly: exactly 80% is still normal and
  exactly 95% is still warning.
- The foreground app and every app with unsaved work are protected and never
  closed.
- In `free-memory` any set of closable apps that gets to the target with the
  smallest total `reopen_s` passes. Closing the biggest apps first, or
  following the kill order, is not always the cheapest; when even closing every
  closable app is not enough, the answer is `possible: false`.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and one module per tool
├── tests/           # the tools' tests and the verifier's
├── ui/              # outputs are drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

`verifier/` works every answer out again with its own code
(`verifier/checks.py`): levels as exact fractions, the kill order by picking
the next app to close one at a time, and, for `free-memory`, the smallest
possible reopen time by dynamic programming over reopen seconds (the most
memory each total reopen time can free). It then checks that the submitted
apps may be closed, free enough, and cost no more than that minimum.

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

The plugin needs no network and no environment variables.
