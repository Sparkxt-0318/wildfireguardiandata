"""firewitness core: shared building blocks for all tracks. Standard library only."""
from .config import load_region
from .evidence import Verdict, Witness, combine, fit_witnesses, fit_witnesses_grouped
from .hashing import canonical_json, hash_inputs, hash_obj, sha256_bytes, sha256_file
from .keys import MissingKey, get_key, load_keys, redact, require_key
from .patch import (Patch, PatchConflict, PatchSet, apply_patches, missing, revert_file, revert_patches,
                    snapshot_input, verify_input_unchanged)
from .placebo import (cluster_bootstrap, interval_excludes_zero, paired_cluster_bootstrap, placebo_test,
                      shuffle_column)

__all__ = [n for n in dir() if not n.startswith("_")]
