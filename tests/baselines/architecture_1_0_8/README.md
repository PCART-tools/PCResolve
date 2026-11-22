# Architecture 1.0.8 compatibility baselines

These are comparison inputs, not generated reports. The source reference is
commit `b79a58fead5790aed50d01119e108cfff8bdae3f`, after the value-flow
precision changes. Its `src/pcresolve` Python files have SHA-256
`5bb448605ab3606ee0fb9c114c091ff611c31f948672fbb932a775d40aeb61c2`,
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
baseline. On Windows, CI compares with the checked-in `analysis.json`. On
Ubuntu 24.04, CI runs `scripts/capture_platform_baseline.py` to capture the
same reference revision on Linux, then compares the current checkout with that
platform-specific result. The capture checks the Git object IDs of the three
corpus inputs in both revisions before running. It uses the current fingerprint
and flow path normalization on both revisions; ownership output is compared
on the same operating system rather than against Windows-specific fingerprints.
Generated reports belong in build artifacts rather than this directory.

The API comparison checks the recorded exports and legacy module mappings.
An unchanged fingerprint means the captured output agrees with its reference;
neither check alone proves that the shared semantic result is correct. The
reviewed ownership corpus and strict value-flow matrix provide separate
behavioral checks, with the limits described in `docs/validation.md`.
