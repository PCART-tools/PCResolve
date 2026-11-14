# Architecture 1.0.8 compatibility baselines

These are comparison inputs, not generated reports. The source reference is
commit `7444cc9d4e75f0e71575f4d38e95423c45f60a3f`, before the package
reorganization. Its `src/pcresolve` Python files have SHA-256
`e77ca58d9d175e0ef06d177f523d0ecb697694211faf229f5becbe0f27dc510f`,
computed from Git archive bytes in sorted relative-path order, hashing each
relative path followed by its file bytes.

`analysis.json` was captured on Python 3.13.9 with `PYTHONHASHSEED=0` by the
reference commit's analysis and matrix runners, using the 42-project ownership
manifest and 83 flow entries. Its `corpus_git_objects` records the Git object
IDs for the manifest and fixture trees. The runner applied the current
`flow-checkout-root-v2` fingerprint normalization before hashing: it replaces
only checkout-root paths in flow path, call identifier, heap identifier and
source-hash fields, including path keys. Order, evidence, boundaries and other
semantic values are retained. Runtime timings are intentionally excluded.

`api.json` records signatures and defining modules directly inspected from the
reference commit's 19 exports. Its `legacy_original_modules` records successful
imports of the 56 legacy paths in that reference checkout. `legacy_modules`
records the relocation mapping introduced by the 1.0.8 reorganization, so the
comparison checks both the recorded mapping and actual imported module identity.
The relocation mapping is an approved compatibility target, not a claim that
the new paths existed in the reference commit.

The analysis comparison requires the same Python version and hash seed as the
baseline. CI compares from a separate checkout; generated comparison results
belong in build artifacts rather than this directory.
