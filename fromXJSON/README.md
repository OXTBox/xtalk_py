# fromXJSON: stacks to take apart

Put XTJSON harvests here (the folder LCHarvest2 writes for a stack: `manifest.json`,
`stack_*.json`, `scripts/`, `blobs/`). Some stacks hide most of their code in their
cards, groups and controls, so the stack script alone doesn't show what they do.

Claude strips the scripts out of each harvest into the corpus, **one file per stack**:
every object's script in message-path order (stack, cards, groups, controls), each under
a banner naming the object (type, name, id, its card), so the scripts can be read, tested
and catalogued together, with the context the harvest gives (object names, custom
properties). Then the file goes through the usual `toCorpus` review.

`xtRedeemer` (the XTJSON rebuild launcher) is the test for the harvest itself: it rebuilds
a stack from its harvest so the result can be compared with the original, to find what
XTJSON lost or changed and needs clarification ("redemption").
