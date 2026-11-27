---
name: feedback-offline-accuracy-over-speed
description: One-time data collection favours accuracy over speed (no turn caps in Royal Chess strength data); LGREF's own running time favours speed.
metadata:
  type: feedback
---

There are two budgets, and they are traded off differently.

- **LGREF's own running time** (the program's pipeline) should be made as
  short as possible, up to the point where cutting further would hurt
  its effectiveness or integrity.
- **One-time offline data collection** (version tables, depth races,
  strength measurements) is not part of LGREF's running time. Here
  accuracy matters more than speed, so let it run as long as it needs.

The concrete case: **no turn cap in Royal Chess strength data.** Royal
Chess has no draw outcome. Its rules end every game in a win or a loss,
and the repetition rule makes every game finite. A capped game is
therefore an artefact of the measurement. Scoring it as ½ is wrong,
because one side may have been winning. Excluding it is also wrong,
because it drops the long games. Run every game to its real end; a
watchdog may alert, but it must never stop a game. Genuine draws in
games that have them (m,n,k, Krieg, the card games) still count as ½.

**Why:** the user said this on 2026-11-27, after the depth race had 6 of
40 games capped at 150 plies.

**How to apply:** remove ply caps from Royal Chess measurement runs.
Re-play capped games uncapped from the same seed. Prefer longer runs to
truncated data. Related: [[feedback-measurement-discipline]].
