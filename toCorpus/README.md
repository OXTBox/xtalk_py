# toCorpus: scripts waiting to join the corpus

Drop loose LiveCode scripts here (any name, `.livecodescript` or `.txt`).

1. **Spark's first look** (optional, needs LM Studio running with Spark loaded):
   `python3 tools/spark_catalogue.py` writes a draft catalogue of each script to
   `_spark/<file>.md`: what it is (form follows function), every handler, reusable
   handlers, workarounds, possible `LIB_` libraries. Prompt: `prompts/spark_catalogue_prompt.md`.
2. **Claude's review:** Claude reads each script and Spark's draft, corrects the draft,
   may add comments to the script, writes the script's entry in `corpus/sources.json`,
   and moves the script into its corpus folder. The corrected catalogue goes to
   `corpus/notes/<file>.md`, with Spark's draft beside it as `<file>.spark.md`
   (draft + correction pairs: material for training Spark or another model later).
3. Claude runs `tools/corpus_sync.py` and `tools/glossary_census.py`, and **removes the
   script from this folder**.

A script that belongs to a project is kept in its project; the corpus gets a copy.
