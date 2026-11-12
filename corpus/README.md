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
| `notes/` | Reviewed catalogues (`<file>.md`) beside Spark's drafts (`<file>.spark.md`) |

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

Drop scripts into `xtalk_py/toCorpus/` (see its README): Spark writes a first-look
catalogue, Claude reviews it, files the script here with its `sources.json` entry, and
removes it from `toCorpus`. Whole stacks to take apart go to `xtalk_py/fromXJSON/` as
XTJSON harvests.

`python3 tools/corpus_sync.py --check` lists copies whose project file has changed,
anything missing, and scripts waiting in `toCorpus/`.

## Used by

- `tools/glossary_census.py`: counts the LiveCode vocabulary the corpus uses
  (`docs/GLOSSARY.md`, the interpreter's to-do list).
- Later: the interpreter's test bench (run a corpus script in xtalk_py and in LiveCode
  9.6.3 through LIB_MCP, compare).
