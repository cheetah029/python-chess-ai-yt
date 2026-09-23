# Provenance note — the recorded git SHA is unreachable

The manifest records `git_sha: c642ce5...`, the HEAD of the feature
branch this run was launched from. That branch was squash-merged into
`main` and the original commit is no longer reachable from any ref, so
resolving the SHA in a fresh clone will fail.

**The equivalent commit is `259a78d`** ("Make infix GDL the official
dialect; LGREF now takes infix input (#190) (#191)") on `main`. The
content is identical; the squash changed the parentage, not the code.

This is not specific to this run. Every experiment launched from a
feature branch ends up with an unreachable SHA once that branch is
squash-merged, so the guarantee the field exists to provide is not
currently being provided for any run in this project. Tracked as
issue #195, which proposes recording a content hash over the files that
determine a run rather than depending on history.
