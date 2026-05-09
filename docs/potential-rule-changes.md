# Potential Rule Changes

This document tracks proposed rule modifications discovered through AI training data analysis and game design discussions. Changes listed here are candidates for implementation after initial data collection with the original rules is complete.

---

## 1. Tiny Endgame Rule: Bishop Deadlock Fix

### Problem

All observed draws (4 total across random and trained AI data, original 300-turn-cap model) follow the same "bishop deadlock" pattern: 5-6 non-neutral pieces remain with asymmetric compositions, and the only non-royal attackers are bishops. The tiny endgame rule never activates because the symmetry condition (both sides must have the same piece types, ignoring kings) is not met.

| Draw | White Remaining | Black Remaining | Activates? |
|------|----------------|-----------------|------------|
| 1 | queen x2, bishop | queen, bishop | No - asymmetric |
| 2 | king, bishop | queen x2, bishop | No - asymmetric |
| 3 | queen x2, king, bishop | queen, bishop | No - asymmetric |
| 4 | queen, king | bishop x2, queen | No - asymmetric |

These positions stall because bishops can only capture reactively (pieces that move from their diagonal), not proactively. They cannot chase down a queen or king. Without rooks or knights to create active threats, no captures occur, and the game drifts until the turn cap.

**Update (fine-tuned model):** After fine-tuning the AI with a 1000-turn cap (20 additional iterations from the 50-iteration base model), draws dropped to **0 in 1000 games** (from 2 in 1002 with the original model). The original 2 draws involved positions with 6+ pieces and ongoing captures — they were not structural deadlocks but rather cases where the AI lacked endgame training beyond 300 turns. The fine-tuned model resolved all such positions decisively, with 19 games exceeding 300 turns (max 483) that would have been draws under the old training cap. This suggests the bishop deadlock problem may be less severe than initially thought, and better-trained AI can resolve most positions that appear stalled.

### Why the current rule misses this

The current activation condition for 5-6 pieces requires both sides to have identical piece types (ignoring kings). This was designed to keep the rule "fair" by only applying to symmetric material. But the stalling problem happens precisely in asymmetric endgames where the remaining pieces structurally cannot capture each other.

### Ideas considered

1. **Remove the symmetry requirement entirely for 5-6 pieces.** Too broad - would activate in positions like king+queen+rook+bishop vs king+bishop where the stronger side has a clear winning plan. The distance count limit of 3 would rush them artificially and could turn won positions into losses.

2. **Scale the distance count limit based on piece mobility.** Complex to implement and hard for players to track.

3. **Add a "free reset" of distance counts.** Delays the problem but doesn't fix the structural inability of bishops to capture.

### Proposed change

Add a third activation clause to the tiny endgame rule:

**Current rule:** No pawns AND (4 or fewer non-neutral pieces OR 6 or fewer non-neutral pieces with same piece types ignoring kings)

**New clause:** OR 6 or fewer non-neutral pieces AND no knights or rooks remain on either side.

This specifically targets endgames where the only non-royal attackers are bishops, which are structurally incapable of resolving the game. If even one knight or rook exists, the position has a piece that can actively hunt royals, so the symmetry check still gates activation.

A royal queen counts as "queen" even while transformed (using the same logic as the existing comparison function). This prevents an exploit where repeatedly transforming the queen into a knight toggles the rule on and off, resetting distance counts and enabling infinite stalling.

---

## 2. Queen Manipulation: Strengthening Base Form

### Problem

Data from 50 trained AI games shows the base-form queen is severely undervalued:

- The queen has the fewest moves of any piece (286 total, 5.7/game) and second-worst capture rate (4.9%)
- 524 manipulations occurred (10.5/game), but 98.1% were pure repositioning with no direct impact — only 10 resulted in captures (1.9%)
- Only 13.9% of manipulations set up a capture on the player's very next turn
- Average manipulation distance: 2.6 squares (43% move the piece just 1 square)
- The AI transforms away from base form 5.2x more often than reverting (140 vs 27)
- Only 15 of 50 games ever see a reversion to base form

The core issue: manipulation costs a full turn, but the effect evaporates immediately because the target moves freely on its next turn (only restriction: can't return to its previous square). The opponent simply adapts, making manipulation a tempo-neutral action at best.

Meanwhile, transforming into a knight (43% of transformations) or bishop (22%) provides dramatically better mobility and attack power. The immunity to manipulation that base form provides is not enough to offset this — being manipulated as a transformed queen is barely punishing.

### Ideas considered

1. **Increase manipulation range or allow multi-step manipulation.** Doesn't fix the core problem — the target still moves freely afterward regardless of how far it was moved.

2. **Allow manipulation to move the base-form enemy queen.** Makes the immunity problem worse — removes the one remaining incentive to stay in base form. The AI would transform even more aggressively.

3. **Make manipulation a "free action" (half-turn).** Large mechanical change that could make manipulation dominant rather than just viable.

4. **Let manipulation explicitly choose the destination (not limited by piece's own movement).** Combined with the free-movement-afterward problem, this just makes the nudge bigger without making it stickier.

5. **Give the base-form queen a passive aura ability.** Adds a new mechanic entirely, increasing game complexity.

6. **Extend restriction #1 — piece can't return to its previous square for N turns instead of 1.** Simple but limited impact — a displaced piece that can move anywhere else isn't meaningfully disrupted.

7. **Manipulated piece can only move one square on its next turn.** Good effect but mechanically awkward — pieces suddenly gain movement they don't normally have (e.g., a knight moving 1 square instead of radius-2). Feels visually and strategically strange.

8. **Queen can only manipulate to adjacent square, piece frozen afterward.** Too weak — 1 square of displacement is barely meaningful even with a freeze.

9. **Bishop-parallel pin: if the manipulated piece moves, the queen can capture it at its destination.** Has the same timing issue as the freeze (see analysis below). Whether the piece is frozen or pinned, the effect only lasts one opponent turn, and by the time the manipulating player can act, the effect has expired.

10. **Freeze + safe-square constraint: piece can't move next turn, queen can't place it on a threatened square.** The freeze provides real disruption, but the safe-square check is hard to compute mentally — especially with knight jump captures threatening non-obvious squares. Creates unintuitive restrictions (e.g., can't manipulate a pawn to a square your own knight could jump-capture, even if the pawn is defended). Making exceptions for specific pieces adds more rules.

11. **Bundle manipulation with queen's normal move (free action).** The queen barely moves in base form anyway (5.7 moves/game), so the bonus movement adds no real value — you'd rather spend the move on a knight or rook. The turn cost of manipulation isn't the core problem; the effect's weakness is.

12. **Freeze without safe-square restriction.** The manipulated piece cannot move on its next turn, and the queen can place it on any legal destination (including threatened squares). This achieves displacement but creates a dominant zero-thinking strategy: place the piece next to your attacker, it's frozen, free capture next turn. This changes manipulation's purpose from positional disruption to a capture-setup mechanic, removing the need for any strategic thought — manipulation is only used when you want a free kill. This is the opposite of adding strategic depth.

13. **Exclusion zone: piece can't return to origin or adjacent squares for one turn.** AI-tested: manipulation surged to 15.5/game (2.4x original), transform ratio dropped to 2.8:1 (best result). Statistically effective but thematically unintuitive — there's no spatial logic for why a piece can't go to a square adjacent to where it was. Feels like a mechanical balance lever, not a natural game rule. Also easy to forget during physical play.

14. **Forced response: opponent must move the manipulated piece on their next turn.** The opponent is forced to move the manipulated piece, but since pieces have high mobility, the second move likely brings it back close to where it originally was, effectively undoing the displacement. Two moves allow the second to undo the first.

### AI Playtesting Results (Initial — 50 games each)

Three variants were implemented, trained (5 iterations, 64-channel network), and tested (50 decisive games each):

| Metric | Original | Freeze | Exclusion Zone |
|---|---|---|---|
| White wins | 17 (34%) | 17 (34%) | 25 (50%) |
| Black wins | 33 (66%) | 33 (66%) | 25 (50%) |
| Avg game length | 133.5 | 115.3 | 165.5 |
| Manipulations/game | 6.5 | 3.5 | 15.5 |
| Transforms away from base | 166 | 89 | 79 |
| Reverts to base form | 41 | 16 | 28 |
| Transform ratio (out:in) | 4.0:1 | 5.6:1 | 2.8:1 |

Key findings:
- **Freeze** made manipulation stronger per use but the AI used it less (3.5/game), transforming even more aggressively (5.6:1 ratio). Each freeze was powerful enough that few were needed — the queen transformed into a knight for most of the game and only reverted for occasional surgical freezes.
- **Exclusion zone** made manipulation weaker per use but the AI used it constantly (15.5/game), staying in base form more (2.8:1 ratio). The weakness of each use encouraged frequent use, and cumulative small disruptions shaped the game more than rare powerful ones. Also neutralized black's boulder-first advantage (50/50 win rate).
- A weaker-per-use ability used constantly can shape the game more than a strong-per-use ability used rarely.

Note: 50 games with 5 training iterations is too small for statistical confidence. These results indicate trends but could be influenced by random variance.

### Analysis of the Core Design Tension

The problem has two dimensions:
1. **Displacement persistence** — the manipulated piece should stay where it was moved, not immediately return
2. **Exploitation prevention** — the freeze shouldn't become a capture-setup tool

Every attempt to solve #1 without creating #2 introduced complexity:
- Safe-square restrictions are hard to compute mentally (especially with knight jump captures)
- Exclusion zones work statistically but feel arbitrary and unintuitive
- Forced responses undo the displacement through the second move

### Sub-variants tested

Building on the freeze mechanic, four additional sub-variants were tested to explore invulnerability (protecting the frozen piece from enemy capture) and manipulation restrictions (no-repeat, cooldown):

1. **Freeze+NoRepeat** — frozen piece can be captured; queen cannot re-manipulate the same piece on consecutive turns
2. **Freeze+Invulnerable** — frozen piece is immune to enemy capture on the manipulator's next turn; repeat manipulation allowed
3. **Freeze+Invulnerable+NoRepeat** — invulnerability + no-repeat restriction
4. **Freeze+Invulnerable+Cooldown** — invulnerability + queen cannot manipulate any piece for one turn after manipulating

**Timing (corrected):** If manipulation occurs on turn N:
- **Turn N+1 (owner's turn):** piece is frozen (cannot make spatial moves, can still perform actions like transformation)
- **Turn N+2 (manipulator's turn):** freeze expires; for invulnerable variants, piece becomes invulnerable (cannot be captured by enemies); no-repeat and cooldown restrictions are active
- **Turn N+3 (owner's turn):** invulnerability expires; all flags cleared

Note: an earlier implementation incorrectly set both frozen and invulnerable simultaneously at manipulation time and cleared both at N+2 before move generation, making invulnerability functionally inert. All invulnerable variant data was recollected after fixing the timing.

### AI Playtesting Results (Full — 100 games each)

All variants: 5 iterations, 64-channel network, 100 decisive games each.

| Metric | Original | Freeze | Freeze+NR | Freeze+Invuln | Freeze+Invuln+NR | Freeze+Invuln+CD |
|---|---|---|---|---|---|---|
| Games | 100 | 100 | 100 | 100 | 100 | 100 |
| White wins | 31 (31%) | 31 (31%) | 46 (46%) | 64 (64%) | 61 (61%) | 83 (83%) |
| Black wins | 69 (69%) | 69 (69%) | 54 (54%) | 36 (36%) | 39 (39%) | 17 (17%) |
| Avg game length | 130.5 | 108.3 | 137.7 | 122.4 | 166.7 | 125.7 |
| Median game length | 122 | 89 | 122 | 106 | 144 | 106 |
| Std dev game length | 60.4 | 66.5 | 96.4 | 60.4 | 80.8 | 71.6 |
| Avg captures/game | 20.6 | 20.1 | 20.5 | 21.6 | 24.5 | 21.5 |
| Avg manipulations/game | 6.6 | 3.0 | 11.9 | 3.5 | 8.6 | 7.9 |
| Manipulation CV | 0.90 | 1.73 | 1.21 | 1.44 | 0.81 | 0.98 |
| Avg transforms away/game | 2.99 | 2.33 | 2.80 | 2.24 | 7.18 | 3.22 |
| Avg reverts to base/game | 0.79 | 0.35 | 1.11 | 0.59 | 2.59 | 0.74 |
| Avg total transforms/game | 3.78 | 2.68 | 3.91 | 2.83 | 9.77 | 3.96 |
| Enemy capture at N+2 (% of manips) | 0.2% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| Avg pieces remaining | 11.4 | 11.8 | 11.5 | 10.4 | 7.5 | 10.5 |

Metric notes:
- **Manipulation CV** = coefficient of variation of manipulations per game (higher = more varied strategic use across games)
- **Transforms away** = queen transforms from base form to rook/bishop/knight (avg per game)
- **Reverts to base** = queen transforms back to base form (avg per game)
- **Enemy capture at N+2** = % of all manipulations where the manipulator captures the displaced piece on their next turn; blocked to 0.0% in all invulnerable variants, confirming invulnerability works correctly

### Analysis

**Invulnerability creates a strong white advantage.** All invulnerable variants shift the win rate heavily toward white: Freeze+Invuln (64%), Freeze+Invuln+NR (61%), Freeze+Invuln+CD (83%). Without invulnerability, Original and Freeze both show 31% white / 69% black. The invulnerability mechanic disproportionately benefits the first mover.

**Invulnerability protects against a near-zero threat.** Enemy capture of the displaced piece at N+2 occurs in only 0.2% of manipulations even in the Original variant (no protection). In Freeze+NR (no invulnerability), the rate is also 0.0%. Invulnerability blocks an event that almost never happens, yet it produces large behavioral differences in the AI — likely because the AI over-indexes on the rule's existence during training rather than its practical impact. With only 5 training iterations, the behavioral differences between invulnerable and non-invulnerable variants are likely dominated by training noise rather than genuine strategic consequences of the rule.

**Freeze+NR is the most balanced variant.** At 46/54, it has the closest win rate to 50/50. It also has the highest manipulation usage (11.9/game) and highest manipulation CV (1.21), indicating the AI uses manipulation frequently and with high variation across games — a sign of genuine strategic decision-making rather than rote patterns.

**Freeze alone doesn't change the game.** Freeze and Original share identical 31/69 win rates. Freeze has even lower manipulation usage (3.0/game vs 6.6/game), suggesting the AI finds freeze too powerful per use and simply transforms away from base form, using manipulation rarely.

**Freeze+Invuln+CD is severely unbalanced.** 83/17 white win rate makes it unsuitable without fundamental rebalancing.

### Proposed change: Freeze + No-Repeat

The original manipulation restrictions are:

- The piece moved may not return to its previous square on the immediate next turn.
- The queen may not move a piece that moved on the immediately preceding turn.
- The queen may not manipulate the enemy king, boulder, or base-form royal queen.

The proposed modified restrictions are:

- The piece moved may not make a spatial move on the immediate next turn.
- The queen may not move a piece that moved on the immediately preceding turn.
- The queen may not move a piece that was manipulated on the previous turn.
- The queen may not manipulate the enemy king, boulder, or base-form royal queen.

The first restriction replaces "may not return to its previous square" with "may not make a spatial move" — the manipulated piece stays where it was placed for one turn, though it may still perform actions (such as transformation). The third restriction is new: it prevents the queen from repeatedly manipulating the same piece on consecutive turns, clearing after any non-manipulation turn.

#### Arguments for Freeze+NR

1. **Most balanced win rate (46/54)** — closest to fair of any variant tested, correcting the 31/69 black advantage in the original rules
2. **Highest manipulation usage (11.9/game)** — the AI uses the queen's power frequently, meaning it's strategically valuable without being overpowered
3. **Highest manipulation variation (CV=1.21)** — games vary in how much manipulation is used, indicating real strategic decisions about when to manipulate vs. move
4. **Moderate game length (137.7 turns)** — close to Original (130.5), not excessively long
5. **Rich transformation play (3.91/game)** — on par with Original (3.78), showing the full move system is engaged
6. **Simple rules** — two small modifications to the existing restriction list; easy to explain and track during physical play; no delayed timing mechanics
7. **No spatial calculations** — no safe-square checks, exclusion zones, or adjacent-square restrictions

#### Arguments against (for including invulnerability)

1. **Invulnerability solves the exploitation problem in principle** — even though enemy capture of manipulated pieces is rare (~0.2%), invulnerability guarantees it can never happen, closing a potential abuse vector that could emerge with stronger AI training or human play
2. **Thematic coherence** — making a manipulated piece both immobile and invulnerable is a clean concept ("the piece is suspended"); without invulnerability, the manipulator can still set up captures by placing pieces in danger, even if the AI rarely does so
3. **Human players may exploit differently** — AI data shows near-zero exploitation, but human players who spot the manipulate-then-capture pattern could abuse it; invulnerability prevents this by design rather than relying on it being suboptimal
4. **Deeper strategic play** — Freeze+Invuln+NR produces the most complex games (9.77 transforms, 24.5 captures, 166.7 turns), which could appeal to experienced players seeking depth

#### Decision

**Freeze + No-Repeat is the recommended variant.** The invulnerability mechanic adds rule complexity (delayed timing across 3 turns) for protection against an event that occurs in <0.2% of manipulations. The behavioral differences observed in invulnerable variants are likely training artifacts given the light training (5 iterations). Freeze+NR achieves the design goals — balanced win rate, frequent and varied manipulation usage, moderate game length — with simpler rules.

If future testing with stronger AI or human playtesting reveals that freeze-then-capture exploitation is a real problem, invulnerability can be added as a targeted fix at that point.

Note: All data collected with 5 training iterations and 100 games per variant. Results indicate trends but may be influenced by random variance or undertrained networks. Further validation with deeper training is recommended before finalizing rule changes.

---

## 3. Freeze Variant: Removing the No-Repeat Restriction

### Background

The original Freeze+NR proposal (Section 2) included a "no-repeat" restriction: the queen cannot manipulate the same piece on consecutive turns. This was added to prevent the queen from "pin-and-shuffle" — repeatedly displacing the same enemy piece via manipulation chains.

### Reconsideration

Without no-repeat, the queen's manipulation gains a "reeling-in" pattern: with the freeze rule, a manipulated piece is frozen for one turn (cannot make spatial moves), and the queen can manipulate it again on the next queen turn (since the manipulated piece didn't make a spatial move). This lets the queen drag a piece across the board, freezing it between manipulations, and eventually pull it adjacent for capture.

### Arguments for removing no-repeat

1. **The queen's base form gains genuine "presence."** Pieces in the queen's line of sight become real targets, not just transient annoyances. Mirrors how a chess queen's threat radius works without copying chess movement.
2. **Endgame strategy emerges:** "queen + line of sight to enemy piece = I will reel you in." The queen becomes a controller of its line of sight rather than a wind-pusher.
3. **Solves the queen-base-form-undervaluation problem** (the AI transforms the queen 5x more often than reverting). Without no-repeat, base form becomes strategically distinct and worth keeping.
4. **Game-warping risk is bounded by structural limits:**
   - Manipulation cannot target king, boulder, or base-form royal queen (cannot directly win the game).
   - The queen is a slow 1-square mover and vulnerable while manipulating.
   - Manipulation costs the queen's full turn (opportunity cost).
   - Both sides typically have queens, so the power is symmetric.
   - Restriction 1 ("piece can't return to previous square next turn") still applies, preventing trivial 2-square oscillations.

### Arguments against (for keeping no-repeat)

1. **The "drag and capture" tactic could be too dominant** in some positions, especially when the queen has a long line of sight to an undefended enemy piece.
2. **AI data shows manipulation usage drops without no-repeat** (3.5/game vs. 11.9/game with NR), suggesting the AI doesn't find the freedom strategically valuable. Possibly because:
   - The current AI is undertrained and doesn't see the "reeling-in" tactic.
   - Or the freedom is genuinely not worth the loss of variety.
3. **Removing no-repeat could create dominant single-piece tactics** — once the queen establishes line of sight, the targeted enemy piece is effectively dead.

### Decision

**Lean toward removing no-repeat.** The endgame "reeling-in" tactic gives the queen's base form a unique identity and presence. The structural bounds on manipulation (line-of-sight requirement, exemptions for king/boulder/RQ-base, opportunity cost) prevent the mechanic from being game-breaking. The AI's reluctance to use repeated manipulation likely reflects training limitations rather than the tactic's true value.

**Test under curriculum-trained AI before finalizing.** If deeper training reveals the freeze-without-no-repeat variant produces dominant tactics that warp the game, no-repeat can be re-added. Alternatively, a softer constraint (e.g., "cannot manipulate the same piece on three consecutive queen turns") could be considered.

### Final proposed manipulation restrictions (Freeze without NR)

The original manipulation restrictions are:

- The piece moved may not return to its previous square on the immediate next turn.
- The queen may not move a piece that moved on the immediately preceding turn.
- The queen may not manipulate the enemy king, boulder, or base-form royal queen.

The proposed modified restrictions (Freeze without NR) are:

- The piece moved may not make a spatial move on the immediate next turn.
- The queen may not move a piece that moved on the immediately preceding turn.
- The queen may not manipulate the enemy king, boulder, or base-form royal queen.

Just one substantive modification: replace "may not return to its previous square" with "may not make a spatial move" (the freeze). Restriction 2 is unchanged (this is what allows queens to manipulate frozen pieces again on subsequent turns, enabling the reeling-in tactic).

---

## 4. Tiny Endgame Rule: Final Redesign

### Background

Sections 1 (bishop-deadlock fix) and the original tiny endgame rule (in `RULEBOOK.md`) target small-piece-count endgames where pieces cannot resolve the game on their own. Through extensive structural analysis of borderline cases, a cleaner final formulation has been developed.

### Motivation

The original rule (no pawns AND (≤4 pieces OR ≤6 pieces with same piece types ignoring kings)) had several gaps:

1. **5-6 piece asymmetric multisets were not covered**, even when balanced (e.g., K+B+B vs K+N+N).
2. **Bishop deadlock cases** (Section 1) were not caught because the symmetry condition failed for the affected positions.
3. **Mixed-king cases** (one side has only a royal queen, no king) were not handled symmetrically.
4. **Lone-queen-defender cases** (e.g., K+Q vs K+B+B) were uncovered, even though the queen's manipulation/transformation toolkit lets a single queen hold off two opposing pieces.
5. **The K+N+2R vs Q case** is borderline because two rooks plus a knight cannot fully cover all 64 squares (one square always remains uncovered for Q-as-bishop to teleport to).

### Structural insights from the analysis

- **Kings are barely useful** under optimal play. They cannot be aggressive, cannot pin or actively threaten, and primarily serve as a "buffer" for victory conditions. The "+1 royal king" advantage is minimal in practice.
- **Bishops are powerful defenders** via teleportation + reactive capture along diagonals. They neutralize active attackers (knights, transformed queens) by pinning them to their diagonal sight.
- **Queens are uniquely versatile** because manipulation + transformation provide a complete defensive toolkit in a single piece. A lone queen can hold off two attackers.
- **Manipulation neutralizes itself.** When both sides have queens, manipulation power cancels out via mutual disruption.
- **Piece-count constraints** in this variant (max 2 of each type per side) eliminate certain hypothetical configurations (e.g., 3 bishops on one side).

### Final proposed rule

**Tiny Endgame Rule activates when all of the following hold:**

1. No pawns are on the board.
2. At most 6 non-neutral pieces remain.
3. The position matches one of three patterns:

**Pattern A — Small endgame:** At most 4 non-neutral pieces remain.

**Pattern B — Balanced endgame:** Both sides have at least 2 non-king pieces, and the two sides' non-king piece counts differ by at most 1.

**Pattern C — Lone-queen defender:** One side's only non-king piece is a queen, and the other side either:
- has 2 non-king pieces, with at most 1 of them being a queen, OR
- has 3 non-king pieces, none of which are queens or bishops.

### Counting conventions

- A **queen** is the royal queen (in any form, including transformed) or any promoted queen.
- A **non-king piece** is any piece that is not a king. (Queens count as non-king pieces.)
- The **boulder** is neutral and is excluded from all counts.

### Persistence

The rule activates as soon as the conditions are met and deactivates if the conditions stop being met. Distance counts pause when the rule is inactive, resume when it reactivates, and reset to 0 only on captures.

### What each pattern catches

- **Pattern A** is a universal catch-all for very small endgames; the original ≤4 rule.
- **Pattern B** covers balanced 5-6 piece positions where both sides have meaningful coordination resources (bishop pinning, knight forking, rook sweeping). Subsumes the original "same multiset" clause and extends it to handle different piece-type compositions with similar counts (the bishop-deadlock fix from Section 1 plus all minor-piece-mismatch cases like K+B+B vs K+N+N).
- **Pattern C** covers the lone-queen exception:
  - Bullet 1: queen alone holding off 2 attackers (works because queen toolkit compensates for piece count). The "at most 1 queen" restriction prevents the K+Q+PQ vs K+Q forced case where the larger side's extra queen overwhelms.
  - Bullet 2: queen alone against 3 non-bishop non-queen attackers (specifically catches K+N+2R vs Q where rooks fail to fully cover the board). Slightly over-covers K+2N+R vs Q (which is forced for the larger side, but harmlessly — the rule activates and the larger side still wins under distance count).

### Why no piece-list conditions are needed

The rule uses only:
- Piece-count thresholds (≤4, ≤6, "at most 1 queen," "at least 2 non-king")
- Piece-class exclusions (no queens, no bishops)

It avoids specific compositions like "exactly 2 rooks and 1 knight." The "no queens or bishops" condition in Pattern C bullet 2 is structural — it identifies the class of compositions where the larger side relies entirely on direct-attack pieces (knights and rooks) without the manipulation/pinning toolkit that bishops or queens provide.

### Cases excluded (correctly forced)

- All compositions with the lone-queen side having only a non-queen piece (e.g., K+B+B vs K+B): forced because the bishop alone has no defensive toolkit.
- All compositions where the lone-queen side faces an opponent with a bishop (e.g., K+Q vs K+B+B+B): bishops' reactive captures + queen's third-piece advance overwhelm the queen.
- Heavy material asymmetry (non-king diff ≥ 2 for non-Pattern-C cases): forced by piece count.

### Implementation notes

- **Replaces** the original rule's activation conditions in `RULEBOOK.md` (the distance count mechanism and the ≤4 cap remain unchanged).
- **Subsumes Section 1's bishop-deadlock fix** — Pattern B's "non-king count differs by at most 1" already catches the bishop-deadlock cases that Section 1 targeted, without needing the explicit "no knights or rooks" clause.
- The royal queen counts as a queen even while transformed (matches the existing rulebook's convention for the same-multiset rule).
- Promoted queens count as queens (matches the existing convention).
