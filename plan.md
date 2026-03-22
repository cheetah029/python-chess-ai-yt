# Implementation Plan: New Piece Features

## Phase 1: Piece Class Refactoring

### 1.1 Add general attributes to the Piece base class
**File: `src/piece.py`**
- Add `is_royal` attribute (default `False`) — `True` for all Kings and promoted Royal Queens
- Add `is_transformed` attribute (default `False`) — `True` for any piece that has been transformed by a queen's power
- These attributes live on the base `Piece` class so all subclasses inherit them

### 1.2 Update King subclass
- Set `is_royal = True` in King's `__init__`

### 1.3 Add Boulder subclass
**File: `src/piece.py`**
- New subclass `Boulder(Piece)` with name `'boulder'`, no color (neutral), value `0`
- Boulders are immovable, non-capturable obstacles
- They block movement and line-of-sight for all pieces

---

## Phase 2: Boulder Mechanics

### 2.1 Board placement
**File: `src/board.py`**
- Place boulders at the 4 center squares: (3,3), (3,4), (4,3), (4,4)
- Boulders occupy squares but belong to neither player

### 2.2 Movement blocking
**File: `src/board.py`**
- Update `straightline_squares()` (line ~195): when a boulder is encountered, stop — do not add that square, just break
- Update `straightline_of_sight_squares()` (line ~230): boulders block line-of-sight the same way
- Boulders also block diagonal movement at the center intersection
- Knights (Hippogriffs) can jump over boulders but cannot land on them
- No piece can capture or move onto a boulder square

### 2.3 Boulder rendering
**File: `assets/`**
- Add boulder texture image (a neutral-colored rock/stone)
- Render boulders on the board like any other piece

---

## Phase 3: Pawn Promotion Menu

### 3.1 Promotion selection UI
**Files: `src/main.py`, `src/board.py`**
- When a pawn reaches the last rank, show a selection menu asking which type of queen to promote to:
  - **Royal Queen** (`is_royal = True`) — moves like current queen (1 square any direction), has queen powers (move enemy pieces, transform), and is a check/checkmate target like the king
  - **Regular Queen** (`is_royal = False`) — moves like current queen but without royal status
- After selection, replace the pawn with a Queen instance, setting `is_royal` accordingly
- Mark promoted queens visually (e.g., a small crown icon or border glow) to distinguish them from the original queen

---

## Phase 4: Queen Transformation Power

### 4.1 Transformation selection UI
**Files: `src/main.py`, `src/board.py`**
- When a queen uses its transformation power on a friendly piece, show a selection menu asking which piece type to transform into (e.g., Knight/Hippogriff, Bishop/Assassin, Rook/Chariot)
- The transformed piece keeps its color but changes its type, movement rules, and texture
- Set `is_transformed = True` on the transformed piece
- Mark transformed pieces visually (e.g., a small indicator) to distinguish them from original pieces of that type

### 4.2 Transformation logic
**File: `src/board.py`**
- Queen must be adjacent to the friendly piece (within line of sight)
- Transformation replaces the piece object on the board with a new instance of the chosen subclass
- Carry over: color, `is_transformed = True`, position
- A piece can only be transformed once (check `is_transformed` before allowing)

---

## Phase 5: Knight (Hippogriff) Jump Capture

### 5.1 Simplified interaction
**Files: `src/main.py`, `src/board.py`**
- When a knight lands on a square, if there are adjacent enemy pieces that could be captured:
  - Highlight the adjacent capturable enemy pieces AND the landing square itself
  - User clicks an adjacent enemy piece to capture it, OR clicks the landing square to decline capturing
- No secondary selection step or action menu needed — just one click after landing

---

## Phase 6: Queen Enemy Piece Manipulation (Already Partially Implemented)

### 6.1 Simplified interaction (already works this way)
- The current flow already lets the user select an enemy piece and move it directly (no queen selection needed)
- The queen's line-of-sight determines which enemy pieces can be manipulated
- No additional action menu needed — the existing click-to-select, drag-to-move flow handles this

---

## Summary of Class Structure

```
Piece (base class)
  - name, color, value, is_royal (default False), is_transformed (default False)
  - moves, line_of_sight, moved, moved_by_queen, texture, texture_rect
  ├── Pawn (value: 1.0)
  ├── Knight / Hippogriff (value: 3.0)
  ├── Bishop / Assassin (value: 3.001)
  ├── Rook / Chariot (value: 5.0)
  ├── Queen (value: 9.0) — is_royal set based on promotion choice
  ├── King (value: 10000.0) — is_royal = True always
  └── Boulder (value: 0, no color) — immovable, blocks movement/sight
```

## UI Additions Summary
1. **Boulder rendering** — neutral stone graphic on center squares
2. **Pawn promotion menu** — choose Royal Queen vs Regular Queen
3. **Queen transformation menu** — choose which piece type to transform a friendly piece into
4. **Visual markers** — promoted queens get a marker; transformed pieces get a marker
5. **Knight jump capture** — highlight capturable adjacent pieces + landing square after landing
