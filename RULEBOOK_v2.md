# **Rulebook (v2)**

A concise definition of the game's rules. Long-form rationale, design history, and thematic notes are preserved in `docs/RULEBOOK_v2_elaborated.md`.

## **Terminology**

- **Turn:** one player's choice of either a move or an action.
- **Move:** a spatial change; a piece changes squares (including captures).
- **Action:** non-spatial ability; the acting piece remains on its square.
- **Capture:** removing an opponent piece by moving onto its square, except where piece-specific rules state otherwise.
- **Royal piece:** a king or a royal queen.
- **Royal distance:** the Manhattan distance between the closest pair of opposing royal pieces.

## **Objective**

A player **wins** immediately when they capture **both** of the opponent's royal pieces — the **king** and the **royal queen**. Order does not matter. Promoted (non-royal) queens do not count toward victory.

A player **loses** when any of the following occurs:

- Both of their royal pieces are captured.
- They have no legal turn available at the start of their turn (see "No Legal Moves").
- They would cause a board state to appear a third time (Repetition Rule).
- Under the Tiny Endgame Rule, every legal non-capture turn would push the resulting royal-distance count above 3.

## **Board and Setup**

An **8×8 chessboard**. The setup is **rotationally symmetric** (not mirror).

Each player's back rank (left to right): **Bishop – Queen – Rook – Knight – Knight – Rook – King – Bishop**. Pawns are placed on the second rank.

A neutral **boulder** (two stacked markers) starts on the intersection of the four central squares.

## **Turn Structure**

Players alternate turns. On a turn a player performs **one move OR one action**. Players must make a legal turn whenever possible; otherwise they lose ("No Legal Moves Loss").

A turn includes legal boulder moves (either player may move the boulder).

---

## **The Boulder**

- **First move:** the boulder's first move must be to one of the four central squares (d4, d5, e4, e5). White may not move the boulder on their first turn.
- **Subsequent moves:** like a king (one square in any direction).
- **Capture rules:** the boulder may capture only pawns (of either colour). Only a king may capture the boulder.
- **Neutral status:** the boulder is treated as a friendly piece by both sides for most purposes.
- **Central intersection:** when on the central intersection, the boulder blocks diagonal lines only — not files or ranks.
- **Cooldown:** after the boulder moves, both players must make one turn before the boulder may move again.
- **No-return memory:** the boulder may not return (by non-capturing move) to the immediately last square it occupied. It **may** return to that square to capture a pawn there.

---

## **Pieces**

### **Pawn**

- **Movement:** one square forward, left, or right. Pawns may not move backward.
- **Capture:** one square forward, diagonally forward-left, or diagonally forward-right.
- **Promotion:** upon reaching the last rank, a pawn must promote to a **non-royal queen**. The promoting player chooses the queen's starting form: base, rook, bishop, or knight. A transformed starting form is available only if a friendly piece of that type was captured earlier; base form is always available. A promoted queen has all queen abilities; it differs from the royal queen only in not being royal. Promoted queens are marked to distinguish them from the royal queen.

### **King**

- **Movement:** one square in any direction.
- **Capture:** the king may capture enemy pieces, friendly pieces, and the boulder. It is the only piece that may capture friendly pieces or the boulder.
- The king's capture ability does **not** override invulnerability (a piece marked invulnerable cannot be captured by any piece, including the king).

### **Queen** (royal or promoted)

A queen has two modes: **base form** and a **transformed form** (rook, bishop, or knight). Royal and promoted queens follow identical rules except that promoted queens do not count toward victory.

**Base form:**

- **Movement:** one square in any direction.
- **Capture:** any adjacent enemy piece (except the boulder).
- **Actions:** Manipulation or Transformation (below).

**Manipulation Action.** The queen moves an enemy piece located within the queen's line-of-sight (rank, file, or diagonal). The piece is moved exactly as if its owner had moved it, and captures are allowed. The queen may only manipulate while in base form. Restrictions:

1. The manipulated piece **may not make a spatial move on its immediately next turn** (non-spatial actions, such as transformation, remain available).
2. The queen may not manipulate a piece that made a **spatial move** on the immediately preceding turn. Non-spatial actions on the preceding turn do not count toward this restriction; if the target's most recent spatial move was earlier, the restriction does not apply.
3. The queen may not manipulate the enemy king, the boulder, or any enemy base-form queen.

**Transformation Action.** The queen may transform into a rook, bishop, or knight — provided a friendly piece of that type has been captured earlier. The queen may return to base form on a later turn. Transformation does not move the queen. A marker indicates which piece is the queen.

### **Rook**

The rook moves in two steps within a single turn:

1. One square orthogonally (up, down, left, or right).
2. Then a 90° turn and any number of squares in the new direction (including zero).

The rook may stop on or capture the first enemy piece it encounters during the sweep; it may not jump over pieces.

### **Bishop**

- **Movement:** teleport to any empty square that is not currently moveable to or capturable by any enemy piece. Enemy bishops, queens-as-bishop, and the boulder are **excluded** from this safety check (the bishop may teleport into their range). Capturable squares include squares reachable by the knight's jump capture.
- **Reactive capture:** if an enemy piece begins its move on a square within the bishop's diagonal line-of-sight and moves to a new square, the bishop may capture it on its **immediate next turn** by teleporting onto the destination square. The teleport-safety check does not apply to this capture.

**Manipulation and reactive capture.** A manipulation-induced move counts as "the piece moved" for reactive-capture eligibility. A **single** manipulation cannot produce a valid reactive capture, for either of two reasons:

- If the bishop's own side manipulates an enemy piece off the bishop's line-of-sight, the opponent's turn intervenes and the bishop's "immediate next turn" window expires.
- If the opponent manipulates the bishop's own piece, the timing is valid but the bishop would be capturing its own piece (forbidden; only the king captures same-color pieces).

A **double manipulation** can produce a reactive capture: on turn N, player A manipulates B's piece P off A's bishop's line-of-sight; on turn N+1, B manipulates A's bishop to reactive-capture P at its new square. The capturing bishop belongs to A and the captured piece to B, so this is not a same-color capture. The capture choice is offered to the manipulator (B), who may accept or decline.

### **Knight**

- **Movement (radius-2):** to any of the 16 squares within a chebyshev-2 pattern:
  - Two squares orthogonally,
  - Two squares diagonally, or
  - L-shape: two squares orthogonally then one square perpendicular.

  The knight may jump over other pieces.

- **Jumped square:** every knight move passes over one specific square, the **jumped square**:
  - 2-orthogonal move: one square in that direction from the start.
  - 2-diagonal move: one square diagonally from the start.
  - L-shape move: one square along the 2-square (orthogonal) direction from the start.

- **Standard capture:** the knight captures any enemy piece on its landing square.

- **Jump capture:** if an enemy piece moved (spatially) onto a square that a knight can jump over, the knight may capture that piece on its **immediate next turn** by making a normal radius-2 move to an empty landing square, with the moved enemy as the jumped square. Only the jumped piece is captured; other pieces near the landing square are unaffected. The knight may not capture more than one piece per turn. The player may always decline the offered jump-capture (the jumped piece survives).

  "Moved on the immediately preceding turn" means a spatial relocation directly before the knight's move. It includes captures and queen-manipulated moves; it does not include non-spatial actions or turns where the piece in question did not move.

- **Manipulation and jump-capture.** A manipulation-induced move counts as "the piece moved" for jump-capture eligibility. A **single** manipulation cannot produce a valid jump-capture:
  - If the knight's own side manipulates an enemy piece adjacent to the knight, the opponent's turn intervenes (the manipulated piece is frozen by Restriction 1 on that intervening turn, so it does not move on the turn directly before the knight's move).
  - If the opponent manipulates the knight's own piece adjacent to the knight, the timing is valid but the knight would be capturing its own piece (forbidden).

  A **double manipulation** can produce a jump-capture: on turn N, player A manipulates B's piece P next to A's knight K; on turn N+1, B manipulates K to jump over P. The capture is offered to the manipulator (B), who may accept or decline.

- **Invulnerability after jumping.** If a knight makes a **non-capture spatial move** that jumps over a **friendly piece or the boulder** (not over an enemy) AND lands at chebyshev-1 of at least one enemy piece other than the jumped piece, the knight is **invulnerable to capture for the immediately following opponent turn**. No piece — including the king (friendly or enemy) — may capture the knight while it is invulnerable. The adjacent enemy may itself be invulnerable; the check is for the presence of an opposing piece, not for current capturability.

  Invulnerability is NOT triggered if:
  - The knight captures anything during the move (standard or jump-capture).
  - The jumped piece is an enemy (jumping over an enemy never grants invulnerability).
  - Declining a jump-capture (the jumped piece is by definition an enemy in that scenario).
  - The knight was moved by queen manipulation (the invulnerability flag is cleared at the start of the knight player's own next turn).

---

## **Repetition Rule**

A player may not make a turn that would cause a board state to appear **for the third time** during the game. If every legal turn would do so, that player loses.

A **board state** captures all information that determines the legal-move set at the current position, EXCEPT for the state-history counts of the repetition rule itself and the distance counts of the tiny endgame rule (both are game-level tracking, not properties of the current position).

The state includes:

- Piece positions, types, and colors.
- **Per-piece status flags** that affect this turn's legal moves:
  - **Royal flag** and **transformed flag** (queen markers — form and identity).
  - **Manipulation freeze** — a piece frozen by Restriction 1 may not make a spatial move on its next turn.
  - **Invulnerability** — an invulnerable piece cannot be captured this turn.
  - **Moved-last-turn** — true for a piece IF it moved on the immediately preceding turn AND some rule consults this fact at the current position (an enemy base-form queen has queen line-of-sight to the piece, blocking manipulation under Restriction 2; OR an enemy knight is at chebyshev-1 of the piece, making jump-capture eligible).
  - **Reactive-armed** (bishops and queens-as-bishop only) — true for a bishop IF it is enemy of the piece that moved on the immediately preceding turn AND has unblocked diagonal line-of-sight to that move's INITIAL square.
- **Boulder state:** position, cooldown, and no-return memory. The no-return memory is part of the state ONLY when it would restrict the boulder's legal moves — i.e., the boulder is not on cooldown, the memory square is adjacent to the boulder, and that square is empty.
- **Whose turn it is.**

Two positions with identical fields above produce identical legal-move sets and are considered the same state, regardless of the move history that led to them.

---

## **Tiny Endgame Rule**

### **Activation**

The rule applies when ALL of the following hold:

- No pawns remain on the board.
- There are **6 or fewer** non-king non-neutral pieces on the board (boulder excluded, kings ignored).
- The position **balances** under the cancel-queens + 1-to-2 valuation defined below.

### **Queen Counting**

For this rule, a royal queen and a promoted queen each count as a **queen** regardless of transformation form.

### **Cancel-Queens + 1-to-2 Valuation**

Let:

- Q_W, Q_B = queen count on white and black,
- N_W, N_B = non-king non-queen count on white and black.

1. **Cancel queens.** Let q = min(Q_W, Q_B). Subtract q from both queen counts. After cancellation, one side M has r = |Q_W − Q_B| queens; the other side L has 0 queens.
2. **Valuation.** Each of M's r remaining queens is independently assigned a value in {1, 2}; each non-king non-queen piece counts as 1. The position **balances** iff there exists an assignment such that:

   `Σ (queen values) + N_M = N_L`

Equivalent numerical condition:

- If r ≥ 1: balanced iff `r ≤ N_L − N_M ≤ 2r`.
- If r = 0: balanced iff `N_M = N_L`.

### **Distance Counts**

For each possible royal distance from **1 to 14**, keep a count of how many times that distance has occurred while the rule is active (measured in the resulting position after each turn).

- When the rule first activates, set the count for the current royal distance to **1**.
- After every non-capture turn, increase the count for the resulting royal distance by **1**.
- After every capture, reset all distance counts to **0**. If the rule still applies after the capture, set the count for the resulting royal distance to **1**.

### **Limit**

A player may not make a **non-capture turn** that would cause the count for the resulting royal distance to become greater than **3**. If every legal turn would do so, that player loses.

---

## **Additional Rules**

- **No Legal Moves Loss.** If, at the start of a player's turn, the player has no legal move, no legal action, AND no legal boulder move, the player loses. The boulder counts toward "a legal turn exists" only when it is actually movable (not on cooldown, with a destination satisfying the first-move and no-return restrictions).
- Players may not make a move or action on the opponent's turn.
- Captures remove the captured piece immediately.
- If only one of a player's royal pieces is captured, the game continues; the player has not lost yet.
