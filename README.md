# xtalk_py

Carrying LiveCode forward: a Python runtime for xTalk (LiveCode Script) and harvested
LiveCode stacks, drawn with raylib + Dear ImGui. Working name.

Status: planning. Nothing runs yet. See `docs/ROADMAP.md`.

| Path | What it is |
|---|---|
| `docs/ROADMAP.md` | decisions, phases, next step |
| `docs/GLOSSARY.md` | the LiveCode vocabulary the owner's scripts use, most used first (generated) |
| `docs/glossary.json` | the same, as data (generated) |
| `tools/glossary_census.py` | makes the two above: `python3 tools/glossary_census.py [paths...]` |
| `CLAUDE.md` | working notes for Claude Code |

## Licence

GPL-3.0 (see `LICENSE`), because the xTalk work here is built on the GPL-licensed LiveCode Community 9 engine. Copyright (c) 2026 xAction.

The Python files (`.py`) and other material that is not xTalk are also offered under the MIT licence, Copyright (c) 2026 xAction: you may use them under either licence.
