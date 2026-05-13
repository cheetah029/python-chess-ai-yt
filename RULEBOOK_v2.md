# **Draft Rulebook — Version 2**

This is **Version 2** of the rulebook. It differs from Version 1 (`RULEBOOK.md`) in:

- The **Queen Manipulation Action** restriction (1) is changed: instead of "may not return to its previous square," the manipulated piece **may not make any spatial move** on its immediate next turn (it is held in place — actions such as the queen's transformation are still allowed).
- The **Queen** section has been reworded to make explicit that promoted queens have all the same abilities as the royal queen, differing only in not being royal. The manipulation Restriction 3 has been corrected to forbid manipulation of any base-form queen (royal or promoted), not only the royal queen.
- A new **No Legal Moves** loss condition is documented in the Additional Clarifications. Because the manipulation freeze can deny the manipulated player all spatial moves, the player to move with no legal turn (move or action) available loses.
- The **Knight** has been redesigned. The previous always-on adjacent-capture rule (capture any enemy adjacent to the landing square after a jump) is replaced by two simpler mechanics:
  - **Jump-capture:** when an enemy piece moves to a square the knight can jump over, on the knight's next turn the knight may capture that piece by jumping over it. Only the jumped piece may be captured.
  - **Invulnerability after jumping:** when the knight makes a **non-capture** spatial move that jumps over a piece (friendly, enemy, or boulder) AND lands adjacent (chebyshev distance 1) to an enemy piece other than the jumped piece, the knight is invulnerable to capture for the immediately following opponent turn. Captures of any kind — standard or jump-capture — do not grant invulnerability. The adjacent-enemy condition ties invulnerability to active engagement at close range, formalizing the "cavalry charge into enemy lines" thematic and preventing perpetual invulnerability cycles via stationary friendly-piece bouncing.
- The **Repetition Rule** board-state list now includes invulnerable pieces and last-moved-piece tracking, since both gate which moves are legal on the resulting turn.

The original RULEBOOK.md is preserved as Version 1 for reference. The tiny endgame rule changes proposed in `docs/potential-rule-changes.md` Section 4 are NOT included in Version 2.

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

A pawn promotes into a **non-royal queen**.

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

2. The queen may not move a piece that moved on the immediately preceding turn.

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

The player may always decline an offered jump-capture, in which case the jumped piece survives.

The knight may not capture more than one piece on a single turn. Only the jumped piece may be captured by jump-capture; other pieces adjacent to the landing square are not affected.

### **Invulnerability After Jumping**

When the knight makes a **non-capture** spatial move that jumps over a piece AND lands adjacent (chebyshev distance 1) to at least one enemy piece other than the jumped piece, the knight is **invulnerable to capture during the immediately following opponent turn**. While invulnerable, no other piece may capture the knight via any move or action — this includes the king (friendly or enemy), whose special capture power does NOT override invulnerability. Invulnerability expires automatically when that opponent turn ends.

The jumped piece itself may be of any affiliation — friendly, enemy, or the boulder — but it does **not** count as "the adjacent enemy" for purposes of the trigger condition. Even though the jumped piece is geometrically adjacent to the landing square (it sits between the knight's start and end), it is excluded from the adjacent-enemy check. A separate, distinct enemy must be present in one of the other 7 chebyshev-1 neighbors of the landing square.

The adjacent-enemy condition is the rule's way of tying invulnerability to **active engagement at close range**:

* A knight that charges into enemy lines (jumping over a front-rank piece to land beside another enemy) earns protection during its commitment.

* A knight that leaps in empty space — over a stationary friendly piece into territory with no enemies nearby — does **not** earn protection. Such moves are repositioning, not engagement, and the rule does not reward them.

Invulnerability does **not** trigger when the knight's move captures anything:

* not when the knight makes a standard capture at the landing square (even if the move also jumps over a surviving piece in transit),

* not when the knight makes a jump-capture of the jumped piece.

Declining an offered jump-capture is a non-capture move and therefore can trigger invulnerability — provided the same adjacent-enemy condition is met at the landing square. The jumped piece survives, and if a different enemy is adjacent to the knight's landing square, the knight gains invulnerability for the next opponent turn.

**Knight movements caused by queen manipulation do not grant functional invulnerability.** When the queen manipulates an enemy knight and the knight jumps over a piece during the forced move, the knight's invulnerability is cleared at the start of the knight player's own next turn — before any opportunity to use it — because invulnerability expiration runs on the player whose turn is beginning. In effect, manipulated knights skip the protection: it isn't a reward the manipulator can hand to the opponent.

#### Thematic Note (non-normative)

The adjacent-enemy condition models a **cavalry charge into engagement**: the knight leaps past one obstacle (friendly, enemy, or boulder) and arrives at close quarters with a target enemy. The momentum and commitment of that charge make the knight briefly hard to capture. A leap into empty territory, by contrast, is a tactical reposition without engagement, and confers no protective momentum.

---

# **Repetition Rule**

A player may not make a turn that causes a board state to appear **for the third time** during the game.

A board state includes:

* piece positions

* boulder markers

* queen markers

* whose turn it is

* which pieces (if any) are currently invulnerable

* which piece (if any) made a spatial move on the immediately preceding turn (this gates knight jump-capture eligibility)

If every legal turn would result in a player creating a third repetition, the player loses.

---

# **Tiny Endgame Rule**

## **Tiny Endgame Rule**

This rule applies only when:

* no pawns remain on the board, and

* either

  * there are **4 or fewer non-neutral pieces** on the board, or

  * there are **6 or fewer non-neutral pieces** on the board and, after ignoring kings, both sides have at least **2 pieces**, and their piece counts differ by at most 1.

The boulder is neutral and does not count toward these totals.

For this rule, when comparing remaining piece types:

* **kings are ignored**

* a **royal queen** counts as a **queen** even while transformed

* a **promoted queen** also counts as a **queen**

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

* **No Legal Moves Loss.** If, at the start of a player's turn, that player has **no legal turn available** — meaning no piece they control can make a legal spatial move and no legal action is available — that player **loses**. This can occur, for example, when the manipulated player's last manipulable piece is held in place by the queen's manipulation freeze (Restriction 1) and they have no other piece able to move or act. (The Repetition Rule and Tiny Endgame Rule may also produce no-legal-move situations under their own constraints.)

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

