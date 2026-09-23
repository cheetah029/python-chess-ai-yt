# Aborted run — not a result

Killed at cluster 3/21. The manifest still reads `status: running`
because the process was terminated before it could seal itself; that
field is written by the run, and rewriting it afterwards would forge a
machine-written record.

**Why it was killed.** This run used the clustering code from before the
determinism fix. Its partition was one sample from a hash-order
dependent distribution, so its cluster list would not have reproduced.
See the commit "Clustering was not reproducible, and shared helpers were
misattached".

Kept rather than deleted: results accumulate, and an abandoned run is
part of the record of how the measurement was arrived at.
