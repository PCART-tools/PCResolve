## @package pcresolve.flow.index.generation
#  Determine whether a previously built flow index may be reused.

from typing import Optional, Sequence
from pcresolve.frontend.source_snapshot import SourceSnapshot


## Compare the complete source generation and ordered module naming roots.
#  @param previous Previously indexed snapshot, if any.
#  @param current Newly captured source snapshot.
#  @param previous_roots Roots used for the prior index.
#  @param current_roots Roots requested by the current analysis.
#  @return True only when every selected document is the same cached version.
def same_generation(previous: Optional[SourceSnapshot], current: SourceSnapshot,
                    previous_roots: Sequence[str], current_roots: Sequence[str]) -> bool:
    return (previous is not None and previous.files == current.files
            and previous.policy == current.policy
            and tuple(previous_roots) == tuple(current_roots)
            and all(previous.documents[path] is current.documents[path]
                    for path in previous.files))
