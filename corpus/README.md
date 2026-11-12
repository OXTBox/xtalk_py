# LiveCode script corpus

All of the owner's LiveCode scripts in one place: his original stacks, his libraries,
games, demos and tools. It's a knowledge base and a test bench for xtalk_py, and it's
where Claude and Spark (the local model in LM Studio) look when they need real examples
of how the owner writes LiveCode.

**Start with `INDEX.md`** (a table, for reading) or **`index.json`** (the same, for
programs and local models): every script's title, description, size and handler names.

## Folders

| Folder | What goes in it |
|---|---|
| `originals/` | The owner's stack scripts that live **only here** (GridDraw, the Bitmap Vector Tracer). Add new ones here. |
| `engines/` | Vibecode3D's engine stack script |
| `libraries/` | LIB_BIT, LIB_TRACE, LIB_MAP, LIB_MCP, LIB_XTJSON and their ancestors |
| `tools/` | Harvester, rebuild launcher, error capture, standalone launcher |
| `games/vibecode3d/` | Game card scripts (from LIB_GAMES) |
| `xt3d/` | The xt3d benches, demos and launchers |
| `reference/` | Test cases and captured scripts |
| `inbox/` | Drop new scripts here; Claude files and describes them |

## Copies and originals

- A script that belongs to a project (a library, a game, the engine) stays in its project,
  where it's developed. The corpus holds a **copy**, refreshed by
  `python3 tools/corpus_sync.py` (run it from `xtalk_py`). `sources.json` records where
  each copy comes from.
- A script with no project lives **only here** (`"source": null` in `sources.json`).
- Older versions and duplicates are left out: each script appears once, newest version.
- Not included: the per-control scripts inside XTJSON harvests (they stay in their
  harvest folders, which have their own manifests) and generated files such as
  `vibe_engine_xt3d.livecodescript` (a copy of the engine plus overrides).

## Adding scripts

1. Drop the file into `inbox/` (any name; `.livecodescript` or `.txt`).
2. Ask Claude to catalogue it. Claude reads it, moves it to the right folder, writes its
   entry in `sources.json` (title, description, kind, tags, where it came from) and runs
   `tools/corpus_sync.py`, which rebuilds `INDEX.md` and `index.json`.

`python3 tools/corpus_sync.py --check` lists copies whose project file has changed,
anything missing, and files waiting in `inbox/`.

## Used by

- `tools/glossary_census.py`: counts the LiveCode vocabulary the corpus uses
  (`docs/GLOSSARY.md`, the interpreter's to-do list).
- Later: the interpreter's test bench (run a corpus script in xtalk_py and in LiveCode
  9.6.3 through LIB_MCP, compare).
