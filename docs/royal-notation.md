# Royal Chess Notation & the V3 Save Format

Royal chess notation is this variant's counterpart to standard chess
notation: a short, readable token per turn, recording only the
difference between consecutive board states. The V3 save format is a
PGN-style text — a small stats header plus a numbered movetext —
that reconstructs the ENTIRE game (undo history, redo states,
repetition tracking, winner) by replaying the movetext from the
standard initial position.

Implementation: `src/notation.py` (grammar, inference, replay) and
`Game.serialize_to_text` / `Game._load_v3` in `src/game.py`.

## Token grammar

```
Spatial turn:      [>] L ['] FROM (-|x) TO [=F] [j]
Transformation:        L ['] SQ = F
```

| Element | Meaning |
|---|---|
| `>` | Queen **manipulation** — the mover moved an ENEMY piece. |
| `L` | Piece letter as it stood before the turn: `K` `Q` `R` `B` `N` `P`, and `O` for the neutral boulder. |
| `'` | The piece is a **transformed queen** (e.g. `R'` = queen-as-rook). |
| `FROM`/`TO`/`SQ` | Algebraic squares `a1`..`h8`. The boulder's first move uses `**` (the central intersection): `O**-d4`. |
| `-` / `x` | Move to an empty square / landing capture. `x` covers every capture-by-landing: normal captures, the king taking a friendly piece or the boulder, the boulder taking a pawn, and a bishop's **reactive capture** (which is just a bishop move onto the victim's square). |
| `=F` | On a pawn move to the last rank: the promotion form (`=Q` base queen, `=R`/`=B`/`=N` transformed). On a transformation token: the form the queen becomes (`=Q` returns to base). |
| `j` | Accepted **jump-capture**: the knight captures the piece on its jumped square. The jumped square is never written — the rulebook derives it uniquely from FROM and TO. A token *without* `j` whose move happens to offer a jump-capture is a **decline**. |

Examples:

```
Pe2-e3        pawn move                  Qd4=B      queen -> bishop form
Nb1-b3j       accepted jump-capture      B'f5=Q     back to base form
>Pd7-d6       manipulated enemy pawn     O**-d4     boulder leaves intersection
R'a4xa7       queen-as-rook captures     Pe7-e8=N   promotion to queen-as-knight
Ka2xb2        king takes (any piece)     >Pe2-e1=Q  manipulated promotion
```

Everything not written in a token is reproduced by the replay going
through the live game's own turn-application code: manipulation
freeze, knight invulnerability (including declined-jump grants),
boulder cooldown and no-return memory, repetition-state recording,
tiny-endgame counts, and winner checks (both royals captured or
no-legal-moves loss).

## V3 save layout

```
=== Chess Variant Save (v3 royal notation) ===
Mode: human_vs_human
White: human   Black: human
CurrentTurn: 24
Timeline: 30
Perspective: black          (only when the HvH human side is black)
Winner: white               (only when the game is over at CurrentTurn)

___VARIANT_SAVE_V3_BEGIN___
1. Bh1-c4 O**-d4
2. Ne1-e3 Ne8-c6
...
___VARIANT_SAVE_V3_END___
```

- **`CurrentTurn`** (in the stats block near the top) is the position
  shown on load. The full timeline is always replayed; turns after
  CurrentTurn land on the redo stack, so loading resumes exactly
  where the game was saved, with the rest reachable via undo/redo.
- **`Winner`** records the live winner at CurrentTurn. It is normally
  re-derived by the replay; the header stays authoritative so winner
  states always round-trip.
- Move numbers count full move pairs (white then black), like a
  standard PGN.

## Correctness & compatibility

- **Self-verifying saves.** The serializer infers each token by
  diffing consecutive undo-history snapshots, then REPLAYS the whole
  movetext on a scratch game and compares every state hash against
  the live timeline. Any divergence — or a game whose timeline does
  not start at the standard initial position (e.g. loaded from a
  FEN) — falls back to the V2 compressed container. A V3 save is
  therefore correct by construction.
- **Back-compatibility.** Loading accepts V3, V2 (zlib+base64
  pickle), and legacy V1 (plain base64 pickle) saves. Only the
  writer changed.
- **Size.** A mid-length game: ~0.4 KB as V3 vs ~16 KB as V2 vs
  ~600 KB as V1.
