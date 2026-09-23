# Aborted run — not a result, and killed for a bad reason

Killed at cluster 4/21. The manifest still reads `status: running`
because the process was terminated before it could seal itself.

**Why it was killed, and why that was wrong.** Cluster 3 took 178.3s. I
extrapolated 18 remaining clusters x 178s = 53 min, concluded it would
overrun the 50-minute timeout set on the process, and stopped it.
Cluster 4 then landed at 20.7s. Per-cluster cost ranges from ~0s to
~250s, because the termination probe's cost tracks how many legal moves
the ABLATED game has per ply -- which is exactly the thing each ablation
changes. The mean was nearer 100s and the run would have finished
comfortably.

The stopping decision needed a spread, not a point. This is the second
time in this project that extrapolating from one timing sample produced
a wrong call, which is why it is written down here rather than only in a
commit message.

The successor run is `infix522-det-165443`, restarted with a two-hour
bound so a timeout could not force the decision again.
