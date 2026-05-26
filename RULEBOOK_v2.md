# **Draft Rulebook — Version 2**

This is **Version 2** of the rulebook. It differs from Version 1 (`RULEBOOK.md`) in:

- The **Queen Manipulation Action** restriction (1) is changed: instead of "may not return to its previous square," the manipulated piece **may not make any spatial move** on its immediate next turn (it is held in place — actions such as the queen's transformation are still allowed).
- The **Queen** section has been reworded to make explicit that promoted queens have all the same abilities as the royal queen, differing only in not being royal. The manipulation Restriction 3 has been corrected to forbid manipulation of any base-form queen (royal or promoted), not only the royal queen.
- A new **No Legal Moves** loss condition is documented in the Additional Clarifications. Because the manipulation freeze can deny the manipulated player all spatial moves, the player to move with no legal turn (move or action) available loses.
- The **Knight** has been redesigned. The previous always-on adjacent-capture rule (capture any enemy adjacent to the landing square after a jump) is replaced by two simpler mechanics:
  - **Jump-capture:** when an enemy piece moves to a square the knight can jump over, on the knight's next turn the knight may capture that piece by jumping over it. Only the jumped piece may be captured.
  - **Invulnerability after jumping:** when the knight makes a **non-capture** spatial move that jumps over a **friendly piece or the boulder** (NOT an enemy) AND lands adjacent (chebyshev distance 1) to an enemy piece other than the jumped piece, the knight is invulnerable to capture for the immediately following opponent turn. Captures of any kind — standard or jump-capture — do not grant invulnerability. Jumping over an enemy never grants invulnerability — this closes the perpetual-invulnerability loophole that would otherwise let a knight chain non-capture leaps through enemy territory. The combined "friendly/boulder jump + adjacent enemy at landing" condition ties invulnerability to a supported cavalry charge launching from friendly lines.
- The **Repetition Rule** board-state list now includes which pieces are currently invulnerable, since invulnerability gates which captures are legal on the resulting turn. The state hash deliberately does NOT include the most recent move or any move history — repetition is a positional rule, so identical positions with identical per-piece statuses count as the same state regardless of the move sequence that produced them.
- The **Tiny Endgame Rule** activation condition has been redesigned. The previous "≤4 total OR ≤6 with same multiset ignoring kings" rule is replaced by a single condition: ≤6 **non-king** pieces AND the cancel-queens + 1-to-3 valuation balances. The catch-all ≤4 total clause has been removed (analysis showed all ≤4 positions are forceable for the +material side under optimal play). The new condition adds coverage of stall-prone 7–8-piece positions with extra kings without over-covering.

The original RULEBOOK.md is preserved as Version 1 for reference.

## **Terminology**

* **Turn:** one player’s choice of either a **move** or an **action**.

* **Move:** a spatial change; a piece changes squares (including captures).

* **Action:** non-spatial ability; the acting piece remains on the same square.

* **Capture:** removing an opponent piece by moving onto its square (unless a piece has special capture rules).

---

# **The Game (Working Title)**

## **Objective**

The goal is to capture **both** of the opponent’s royal pieces:

* the **King**

* the **Royal Queen**

A player loses immediately when both are captured, in any order.

Pawn-promoted queens are **not royal** and do not count toward the win condition.

---

# **Board and Setup**

The game is played on a standard **8×8 chessboard**.

The setup is **rotationally symmetric**, not mirror symmetric.

Each player’s back rank is arranged (from left to right):

Bishop – Queen – Rook – Knight – Knight – Rook – King – Bishop

White and Black have identical orientation relative to their own side.

Pawns are placed normally on the second rank.

---

# **The Boulder**

A neutral piece called the **Boulder** begins on the intersection of the four central squares.

It is represented by two stacked markers.

Either player may move the boulder on their turn, and moving the boulder counts as a turn.

### **First Move**

The first time the boulder moves, it must move to one of the four central squares.

White may not move the boulder on their first turn.

### **Later Movement**

Afterward it moves like a **king**.

### **Capture Rules**

* The boulder may capture **pawns only**.

* Only a **king** may capture the boulder.

### **Neutral Status**

For most purposes the boulder is treated as a **friendly piece by both sides**.

When the boulder’s position is on the central intersection, it blocks diagonals only but not files or ranks.

### **Boulder Cooldown**

After the boulder moves, **both players must make one turn** before the boulder can move again.

### **Boulder Memory**

The boulder may not move to the immediate last square it occupied. It may potentially move there again on future turns.

**Exception — captures:** the no-return restriction applies only to non-capturing moves. If a pawn occupies the boulder's immediate last square, the boulder **may** return to that square to **capture** the pawn. The no-return rule exists to prevent pointless back-and-forth oscillation; a capture is irreversible progress (it removes a piece), not oscillation, so it is permitted even back onto the last square.

---

# **Turn Structure**

Players alternate turns.

On a turn a player may perform either:

* **one move** (a spatial movement), or

* **one action** (a non-spatial ability).

Players must make a legal turn whenever possible.

---

# **Piece Movement**

## **Pawn**

### **Movement**

A pawn may move **one square**:

* forward

* left

* right

A pawn may **not move backward**.

### **Capture**

A pawn captures one square:

* forward

* diagonally forward-left

* diagonally forward-right

### **Promotion**

When a pawn reaches the last rank, it must promote.

A pawn promotes into a **non-royal queen**. The promoting player chooses which **form** the queen begins in: base form, or any transformed form (rook, bishop, or knight). The piece's identity is always a queen — it retains queen abilities (manipulation, transformation) regardless of which form it starts in.

Form-specific constraints at promotion follow the standard queen-transformation rule: a transformed form (rook, bishop, or knight) is only available if a friendly piece of that type has been captured earlier. The base-form queen is always available.

Promoted queens have **all the same properties and abilities as the royal queen** (same movement, capture, manipulation, and transformation). The only difference is that they are **not royal** — they do not count toward the win condition.

Promoted queens are marked (for example with a checker) to distinguish them from the royal queen.

---

## **King**

### **Movement**

The king moves one square in any direction.

### **Special Capture Ability**

The king may capture:

* enemy pieces

* friendly pieces

* the boulder

The king is the only piece that may capture friendly pieces or the boulder.

The king's special capture ability does **not** override invulnerability. A piece marked invulnerable (e.g., a knight that just gained one-turn invulnerability after a non-capture jump) cannot be captured by any piece — including the king, whether friendly or enemy.

---

## **Queen**

A queen (royal or promoted) has two modes: **base form** and **transformed form**. The rules in this section apply equally to the royal queen and to any promoted queen — promoted queens differ from the royal queen only in that they are not royal and do not count toward the win condition.

### **Base Form**

Movement: one square in any direction (like a king).

Capture: any adjacent enemy piece (except the boulder).

Action: Manipulation (see below).

### **Manipulation Action**

Instead of moving, the queen may **move an enemy piece** within normal queen line-of-sight (rank, file, or diagonal).

The piece is moved exactly as if the opponent had moved it. Captures are allowed.

Restrictions:

1. The piece moved **may not make a spatial move** on its immediate next turn. (It is held in place for one turn. Non-spatial actions, such as a queen's transformation or another manipulation, remain available — the restriction only prohibits spatial movement.)

2. The queen may not move a piece that moved on the immediately preceding turn. "Moved" here means a spatial move (a change of square). Non-spatial actions on the immediately preceding turn — for example, the target piece's owner transforming the target piece on their frozen turn, or transforming any other piece — do not count, since no spatial relocation occurred. If the target's most recent spatial move was on an earlier turn (with one or more intervening action turns or moves by other pieces), the restriction does not apply.

3. The queen may not manipulate the enemy **king**, the **boulder**, or any enemy **base-form queen** (royal or promoted).

The manipulation action counts as a turn and a player may only perform the action on their turn.

The queen may only perform the manipulation action when in base form.

---

### **Transformation Action**

The queen may transform into any friendly non-royal piece type that has been captured earlier.

The queen may transform into:

* rook

* bishop

* knight

The queen may return to base form on a later turn.

Transformation does not change the queen’s square.

A marker under the piece indicates that it is the queen.

---

## **Rook**

The rook moves in a two-step pattern:

1. Move **one square orthogonally** (up, down, left, or right).

2. Then turn **90°** and move any number of squares in that direction (including zero).

The rook may stop or capture the first enemy piece encountered if blocked during any step.

---

## **Bishop**

The bishop moves by **teleportation**.

It may teleport to any square that:

* cannot currently be moved to by an enemy piece

* cannot currently be captured by an enemy piece

* not including the enemy bishops, queen transformed as a bishop, or the boulder

Capturable squares include squares that can be captured by the knight’s jump capture.

### **Bishop Capture Mechanic**

If a piece begins its move on a square within the bishop’s **diagonal line of sight**, then:

* after that piece moves to a new square,

* the bishop may capture it on its next turn

* by teleporting to the destination square. (Teleporting restrictions do not apply to this capture.)

This capture is only available on the bishop’s **immediate next turn**.

### **Reactive Capture and Manipulation (double-manipulation nuance)**

A manipulation-induced move counts as "the piece moved" for reactive-capture eligibility, exactly as it does for the knight's jump-capture. Because the bishop captures only on its **immediate next turn**, a *single* manipulation can never produce a valid reactive capture:

* If the bishop's own side manipulates an enemy piece off that side's bishop's line of sight, the manipulation happens on that side's turn, so the opponent's turn intervenes before the bishop could act and the window expires.
* If the opponent manipulates the bishop owner's own piece off the line of sight, the timing is valid but the bishop capturing its own piece would be a same-color capture, which is forbidden (only the king captures same-color pieces).

The valid case is a **double manipulation**: on turn N, player A manipulates B's piece off A's bishop's line of sight; on turn N+1, player B manipulates A's bishop to reactive-capture that B piece (which moved on the immediately preceding turn). The capturing bishop belongs to A (an enemy of the current player B), and the captured piece belongs to B — so this is **not** a same-color capture; it is a "self-capture" only in the sense that the player whose turn it is (B) removes their own piece. The capture is offered to B (who will almost always decline). This mirrors the knight's double-manipulation jump-capture nuance.

---

## **Knight**

### **Movement**

The knight may move to any square within a radius-2 pattern:

1. **Two squares orthogonally** (up, down, left, right)

2. **Two squares diagonally**

3. **Two squares in an orthogonal direction and one square perpendicular** (L-shape)

The knight may jump over other pieces.

### **Jumped Square**

Every knight move passes over **one specific square**, called the **jumped square**.

This square is determined as follows. If the knight moves:

* **Two squares orthogonally:** the jumped square is exactly one square in that direction.

* **Two squares diagonally:** the jumped square is exactly one square diagonally from the starting square.

* **L-shape (2 \+ 1):** the jumped square is one square along the two-square direction.

If any piece occupies the jumped square, the knight is considered to have **jumped over that piece**.

### **Standard Capture**

The knight may capture any enemy piece on a square it can move to.

### **Jump Capture**

When an enemy piece moves to a square the knight can jump over, the knight may, on its next turn, capture that piece by jumping over it. A jump-capture move:

* moves the knight from its current square to an **empty** landing square in its normal 2-square pattern,

* passes over the moved enemy piece (the jumped square), and

* removes that enemy piece from the board.

"Moved on the immediately preceding turn" is interpreted strictly: the turn directly before the knight's move. This includes captures and queen-manipulated movements (any spatial relocation of the piece in question), but does not include non-spatial actions (e.g., a queen's transformation) or turns on which the piece in question did not move.

This eligibility rule applies symmetrically: it does not matter whether the jumped piece moved by its owner's own initiative or because it was manipulated by the opposing queen. Either way the jump-capture is offered. In the "double-manipulation" case — where player A manipulates B's piece P next to A's knight K on one turn, and B then manipulates K to jump over P on the next turn — the jump-capture target is still eligible. The capture / decline decision is made by the player whose turn it currently is (i.e., the manipulator of the knight). Even if the jumped piece is the manipulator's own, the choice is presented and the manipulator may decline; in most situations declining is the rational outcome, but the rule does not prohibit the manipulator from clearing their own piece off the square (e.g. to free up a key square) by accepting the capture.

The player may always decline an offered jump-capture, in which case the jumped piece survives.

The knight may not capture more than one piece on a single turn. Only the jumped piece may be captured by jump-capture; other pieces adjacent to the landing square are not affected.

### **Invulnerability After Jumping**

When the knight makes a **non-capture** spatial move that jumps over a **friendly piece or the boulder** (NOT an enemy) AND lands adjacent (chebyshev distance 1) to at least one enemy piece other than the jumped piece, the knight is **invulnerable to capture during the immediately following opponent turn**. While invulnerable, no other piece may capture the knight via any move or action — this includes the king (friendly or enemy), whose special capture power does NOT override invulnerability. Invulnerability expires automatically when that opponent turn ends.

The jumped piece must be either **a friendly piece** or **the boulder**. Jumping over an **enemy** piece does NOT grant invulnerability — even if a different enemy is adjacent to the landing square. This restriction closes the perpetual-invulnerability loophole that would otherwise let a knight chain non-capture leaps through enemy territory and remain protected each turn. The jumped piece also does **not** count as "the adjacent enemy" for the trigger condition: a separate, distinct enemy must be present in one of the 7 chebyshev-1 neighbors of the landing square (the jumped square excluded).

The adjacent enemy may itself be **invulnerable** (e.g., an enemy knight that gained invulnerability on a previous turn, or a piece marked invulnerable by the manipulation variants). The adjacent-enemy check is about *engagement* — the presence of an opposing piece — not about whether that piece can currently be captured. An invulnerable enemy still occupies its square and still represents a target the knight has charged into close range with, so it satisfies the condition.

The adjacent-enemy condition is the rule's way of tying invulnerability to **active engagement at close range**:

* A knight that charges into enemy lines (jumping over a front-rank piece to land beside another enemy) earns protection during its commitment.

* A knight that leaps in empty space — over a stationary friendly piece into territory with no enemies nearby — does **not** earn protection. Such moves are repositioning, not engagement, and the rule does not reward them.

* A knight that leaps over an **enemy** piece — even into close engagement with another enemy — does **not** earn protection. This is the loophole-closure case: a lone knight infiltrating enemy territory should be at risk, not protected by the very enemies it's surrounded by. The cavalry-charge thematic models a charge that *launches from friendly lines*, leaping past your own troops to engage the enemy — not weaving through the enemy itself.

Invulnerability does **not** trigger when the knight's move captures anything:

* not when the knight makes a standard capture at the landing square (even if the move also jumps over a surviving piece in transit),

* not when the knight makes a jump-capture of the jumped piece.

Declining an offered jump-capture is a non-capture move. However, the friendly/boulder-only rule for the jumped piece still applies — and a jump-capture is only ever offered when the jumped piece is an enemy. As a result, declining a jump-capture **never** grants invulnerability under this rule (the jumped piece is, by definition, an enemy in that scenario). The jumped piece survives, but the knight is exposed on the opponent's next turn.

**Knight movements caused by queen manipulation do not grant functional invulnerability.** When the queen manipulates an enemy knight and the knight jumps over a piece during the forced move, the knight's invulnerability is cleared at the start of the knight player's own next turn — before any opportunity to use it — because invulnerability expiration runs on the player whose turn is beginning. In effect, manipulated knights skip the protection: it isn't a reward the manipulator can hand to the opponent.

#### Thematic Note (non-normative)

The rule models a **cavalry charge launching from friendly lines**: the knight leaps past one of *its own* troops (or past the boulder) into close quarters with a target enemy. The momentum and commitment of that supported charge make the knight briefly hard to capture. A leap through *the enemy itself* — weaving past enemy pieces to land beside more enemies — is not a charge; it's lone-rider infiltration, and the rule does not reward it with protection. A leap into empty territory, similarly, is repositioning without engagement, and confers no protective momentum either.

---

# **Repetition Rule**

A player may not make a turn that causes a board state to appear **for the third time** during the game.

**Governing principle:** a board state captures all information that determines the set of legal moves at this position, EXCEPT for the restrictions enforced by the repetition rule itself (the state-history counts) and the tiny endgame rule (the distance-count history). Those two rules track game-state history that accumulates over time; they are not properties of the current position. Everything else that affects which moves are legal right now is part of the state.

Concretely, a board state includes:

* piece positions, types, colors

* per-piece status flags that gate this turn's legal moves:
  * **royal flag** (`is_royal`) and **transformed flag** (`is_transformed`) — together, the "queen markers" (form + identity)
  * **manipulation freeze** (`moved_by_queen`, Restriction 1) — a frozen piece cannot make a spatial move on its next turn
  * **invulnerability** — a piece marked invulnerable cannot be captured this turn; this filters opposing captures and so materially changes the legal-move set

* boulder state: its position, **cooldown**, and **no-return memory** (the last square it occupied) — a boulder on cooldown or barred from returning has different legal moves than one without those constraints

* whose turn it is

* **last-move information IF AND ONLY IF it affects some rule's eligibility at this position.** Three rules consult the immediately preceding move: (a) manipulation Restriction 2 (queen may not manipulate a piece that moved on the immediately preceding turn) — consults `last_move.final`; (b) knight reactive jump-capture (jumped piece must have moved on the immediately preceding turn) — also consults `last_move.final`; (c) bishop reactive capture (eligible only if the captured piece began its move on the bishop's diagonal LoS) — consults `last_move.initial`. The state hash includes the relevant square(s) IF some enemy queen/knight/bishop is positioned to actually consult them, and OMITS them otherwise. So two positions identical in all per-piece statuses but differing only in `last_move.final` (or `.initial`) hash to the SAME state when no rule actually consults the change. This avoids over-differentiation: same legal-move set ⇒ same state.

What is NOT part of the board state for repetition purposes: the state-history counts of the repetition rule itself, and the distance counts of the tiny endgame rule. These are game-level tracking that the rules use to determine when their respective limits fire; they accumulate across the game but are not properties of the current position.

(Implementation note: the code's `get_state_hash` also includes two per-piece flags — `forbidden_square` and `forbidden_zone` — that belong to ALTERNATE manipulation-mode variants (not part of the active rule, which uses `moved_by_queen` freeze). They're hashed for variant correctness but are always `None` under the active rule and so have no effect here.)

If every legal turn would result in a player creating a third repetition, the player loses.

---

# **Tiny Endgame Rule**

## **Tiny Endgame Rule**

This rule applies only when ALL of the following hold:

* no pawns remain on the board, and

* there are **6 or fewer non-king non-neutral pieces** on the board, and

* the position **balances** under the cancel-queens + 1-to-2 valuation defined below.

The boulder is neutral and does not count toward the piece total. Kings are ignored from the count (so the count is of queens and non-queen non-king pieces only).

### **Queen counting**

For this rule:

* a **royal queen** counts as a **queen** regardless of transformation form (a royal queen transformed as a knight still counts as a queen)

* a **promoted queen** also counts as a **queen** regardless of form

### **Cancel-queens + 1-to-2 valuation**

For each side, count:

* **Q** = number of queens (royal + promoted, counted per above).

* **N** = number of non-king non-queen pieces (rooks, bishops, knights).

**Step 1 — Cancel queens.** Let `q = min(Q_W, Q_B)`. Subtract `q` from both `Q_W` and `Q_B`. After cancellation, one side (call it M) has `r = |Q_W − Q_B|` remaining queens; the other side (call it L) has zero queens.

**Step 2 — Valuation.** Each of M's `r` remaining queens is independently assigned a value from `{1, 2}`. Each non-king non-queen piece counts as `1`. The position **balances** iff there exists an assignment of queen values such that the two sides' totals are equal:

```
Σ (queen values) + N_M  =  N_L
```

If `r = 0` (both sides had the same number of queens before Step 1), the condition reduces to `N_M = N_L`.

### **Equivalent numerical condition**

Since each queen value lies in `{1, 2}` and there are `r` queens, the sum ranges over the integer interval `[r, 2r]`. The balance condition is:

```
r ≤ N_L − N_M ≤ 2r           (when r ≥ 1)
N_M = N_L                    (when r = 0)
```

### **Rationale**

The cancel-queens framing encodes that two opposing queens largely neutralize each other in tiny endgames via mutual bishop-form pinning. The 1-to-2 valuation reflects that a queen's effective material worth ranges from ~1 (when constrained) to ~2 (when its transformation/manipulation toolkit and bishop-form escape apply). The combined check activates the rule precisely on positions where neither side has enough material to force a win in practical turn counts.

**Why 1-to-2, not 1-to-3 (2026-05-26 update):** the previous 1-to-3 cap allowed positions like `K + Q vs K + 3 non-queen pieces` (e.g., K+Q vs K+2R+N) to count as balanced. Closer analysis showed all such positions are forceable for the +material side under optimal play. The hardest case is K+Q vs K+2R+N, which is the only 3-non-queen composition with 0 bishops — and even there, W can construct a square-coverage trap (Kf2, Rb7, Rc2, Nf6 covers all squares except h2 when K is at f2, forcing B's Q-as-B into oscillation between h2 and e2, terminating via repetition). With 1 or 2 bishops in the 3-non-queen mix, the bishops continuously pin B's queen, making the trap easier. The 1-to-2 cap removes over-coverage of these positions; they win on material rather than via rule-driven termination.

## **Royal Pieces**

A **royal piece** is a **king** or a **royal queen**.

## **Royal Distance**

The **royal distance** is the Manhattan distance between the closest pair of opposing royal pieces.

## **Distance Counts**

For each possible royal distance from **1 to 14**, keep a count of how many times that distance has occurred while this rule is active, measured in the **resulting position after each turn**.

* When this rule first becomes active, set the count for the current royal distance to **1**.

* After every **non-capture turn**, increase the count for the resulting royal distance by **1**.

* After every **capture**, reset all distance counts to **0**.  
   If this rule still applies after that capture, set the count for the resulting royal distance to **1**.

## **Limit**

A player may not make a **non-capture turn** if it would cause the count for the resulting royal distance to become greater than **3**.

If every legal turn would do so, that player loses.

## **Notes**

To help players understand the rule, an intuitive explanation is provided below. This provided explanation is not part of the game rules.

In these small pawnless endgames, the same few royal spacings cannot be used forever. Each spacing can only be used a limited number of times before someone must change the geometry or force the game forward.

---

# **Additional Clarifications**

* Players must make a turn if any legal turn exists.

* **No Legal Moves Loss.** If, at the start of a player's turn, that player has **no legal turn available** — meaning no piece they control can make a legal spatial move, no legal action is available, **and the player cannot make a legal boulder move** — that player **loses**. Because either player may move the boulder and moving the boulder counts as a turn, a player whose only available legal turn is a boulder move is **not** stuck — they must make it. The boulder counts toward "a legal turn exists" only when it is actually movable (it is not on cooldown, and a destination exists that satisfies the first-move and no-return restrictions). This loss can occur, for example, when the manipulated player's last manipulable piece is held in place by the queen's manipulation freeze (Restriction 1), they have no other piece able to move or act, and no legal boulder move is available. (The Repetition Rule and Tiny Endgame Rule use the same "is any legal turn available" test — boulder moves included — for their own no-legal-move loss conditions.)

* Players may not make a move or action on the opponent’s turn.

* Captures remove the piece immediately.

* If a royal piece is captured, the game continues unless the player has lost both royal pieces.

---

# **Victory**

A player wins immediately when they capture both:

* the opponent’s **king**, and

* the opponent’s **royal queen**.

The order of capture does not matter.

Promoted queens do not count toward victory.

