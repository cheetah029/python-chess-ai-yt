# Why material matters — and what that means for a general agent

Written for two audiences: the author, who wants the root reason rather
than a restatement, and the paper, which needs the claim to be
measurable.

---

## Note on variant differences

Per `CLAUDE.md`, the rules this document depends on, stated up front
because every one of them is a false friend from standard chess:

- **Queen, base form** moves **one square, king-like** — not unlimited
  range. It captures only adjacent enemies.
- **Queen transformation** into rook, bishop or knight is available
  **only if a friendly piece of that type was captured earlier.** This
  single clause does most of the work below.
- **Queen manipulation** moves an *enemy* piece within the queen's line
  of sight, exactly as its owner would, captures allowed. Base form
  only.
- **Bishop** has **no direct attack.** It moves by **global teleport**
  to any safe square and captures only *reactively* — a piece that
  begins its move on the bishop's diagonal and moves may be captured on
  the bishop's immediate next turn.
- **Knight** moves **radius-2 (16 squares)**, not L-only, and may gain
  one turn of **invulnerability** after a non-capturing jump.
- **Rook** moves one square orthogonally, then turns 90° and sweeps.
- **Pawn** moves one square forward *or sideways*, and promotes to a
  **non-royal queen** — which does not count toward victory.
- **Win condition:** capture **both** the king and the royal queen.
  **There is no check and no checkmate.**
- A turn is **one move OR one action**; actions are non-spatial.

---

## 1. The root reason, in four links

Material is not valuable in itself. Nothing in any rulebook says a rook
is worth keeping. Its value is entirely derived, through a chain of four
links. Naming them separately matters, because in this variant they do
not all hold.

**Link 1 — the turn is the only strictly rationed resource.** Both
players get exactly one per round, forever, symmetrically. Pieces,
squares and threats are all unbounded in principle; turns are not. So
*every* advantage in *every* turn-based game must ultimately cash out in
the same currency: being able to do more per turn than the opponent can
answer.

**Link 2 — a piece is an annuity, not a payment.** A move is spent once.
A piece on the board generates legal turns every turn, for the rest of
the game, at no recurring cost. This is the asymmetry that makes
material a *stock* rather than a *flow*, and it is why capturing is
qualitatively different from merely gaining tempo.

**Link 3 — attack is parallel, defence is serial.** This is the
load-bearing link, and it is the actual answer to "why does material
matter".

> The number of threats you can hold *simultaneously* grows with your
> piece count. The number you can *answer* is one per turn, no matter
> how many pieces you have.

So material superiority is not "more stuff". It is precisely **the
ability to create more simultaneous threats than the opponent has tempo
to answer.** Threats are parallel; responses are serial. That mismatch
is the entire mechanism, and everything else is a corollary of it.

This also explains why material is not linear. An extra piece is worth a
great deal when it lets you open a second front, and worth almost
nothing when the position admits only one — which is why "up a piece" is
a statement about the position, not about the arithmetic.

**Link 4 — the advantage ratchets.** Captures are irreversible. So each
conversion of a material edge into another capture is permanent, and
compounds: more material means more parallel threats, which means more
captures. Material is the *integral of everything that has already gone
well.*

Material, therefore, is **instrumental, not terminal.** It appears
nowhere in the win condition. It is a proxy that correlates with winning
*through these four links* — and a proxy is only as good as its weakest
link.

---

## 2. A separate question: why material is a good *feature*

Why material *matters* and why it is *easy to learn* are different
questions, and conflating them is what makes agent design go wrong.
Material is the first thing any learner discovers in any capture game
because of three properties of the **measurement**, not of the game:

1. **It is a ratchet, so credit assignment is nearly free.** Material
   changes only on captures, and never reverses. A feature that is a
   monotone integral of past successes correlates with a distant outcome
   *without the learner having to model the intervening play.* Almost
   nothing else about a position has this property.
2. **It is dense.** Nonzero almost everywhere, and cheap — O(board).
   Compare the *declared* objective, royal count, which this project
   measured as flat in **100% of sampled opening positions**: a
   perfectly valid objective that gives a search no gradient at all.
3. **It is low-variance.** It does not flicker ply to ply, so it
   survives the coarse sampling a learner can actually afford.

**The design lesson, stated generally:** a game whose decisive quantity
is a cheap monotone irreversible scalar will yield its evaluation to
outcome-regression from weak play. Pile size in nim is such a quantity.
Corridor progress in the Phase B race game is such a quantity. A game
whose decisive quantity oscillates — mutual zugzwang, tempo games — is
not, and no amount of data will make it one. **This is a screening
criterion that can be applied to a new game before training anything,**
which is more useful than a material prior and is game-independent.

---

## 3. Where Royal Chess breaks the chain

Six breaks. Each is tied to a specific rule, and several are
*measurable*, which is what makes this more than commentary.

**Break 1 — Link 3 is weakened: most pieces cannot make an
unconditional threat.** The bishop has no direct attack; it captures
only a piece that *chooses to move* off its diagonal. So a bishop
generates no threat against a static piece — its threat is conditional
on the opponent's cooperation. The base-form queen threatens only its
eight adjacent squares. Material therefore converts into *simultaneous
unconditional threats* far less efficiently than in standard chess, and
Link 3 — the whole mechanism — is correspondingly weaker.

**Break 2 — Link 4 is inverted: losing a piece unlocks a capability.**
This is the deepest break, and the measurement found it before the rule
explanation did.

Transformation is available *only if a friendly piece of that type was
captured earlier*. So **while both your bishops are alive, your queen
cannot take bishop form** — and queen-as-bishop is the strongest
defensive resource in the game, because its teleport can only be trapped
by covering all 64 squares at once. Holding your bishops denies your own
queen its escape hatch.

So a capture is still irreversible, but its *consequence is not purely
negative*. **Material is not monotone in this variant.** The ratchet —
the property that made material a good feature in §2 — is partly
reversed for exactly the piece whose loss opens the best defence.

**Break 3 — Link 2 is shared: enemy material is partly your own
resource.** Manipulation lets a base-form queen actuate an *enemy* piece
as though it were the owner's. An opposing piece is therefore not purely
a liability to you; it is also an object you can sometimes move, and
capturing it destroys one of your own manipulation targets along with the
opponent's asset.

**Break 4 — the objective is a conjunction, so its signal is strong but
SPARSE.** The win requires capturing **both** royals, and there is **no
check and no checkmate.** In standard chess a material edge cashes out
quickly because it converts into a *mating attack* — a dense, nearby
tactical target. Here there is no such target: you must physically take
two specific pieces.

Two measurements that look contradictory and are not:

- Exact one-ply search over 56 midgame moves found **0 wins and 0
  losses** — no single move can end the game while both royals live (the
  search does find the win when a side is down to one royal). Royal
  count is equal in **100% of sampled opening positions.** So the
  objective gives a search *no gradient whatever* for choosing between
  opening or midgame moves.
- Across whole games, `Royal` is nevertheless the **strongest** predictor
  of winning measured anywhere in this project: d = +0.719 at **z =
  5.4** (§4).

Both are true because the objective is **sparse, not weak**: flat almost
everywhere, and decisive in the minority of states where it moves at
all. This is a sharper statement than "the objective is uninformative",
which is what the under-powered run appeared to show, and it is the
precise reason a search needs an *instrumental* feature for the midgame
even though the declared objective is an excellent long-run predictor.

**Break 5 — pawn count is a claim, not small material.** A pawn promotes
to a *non-royal* queen: it does not count toward victory, but it has
every queen ability. A pawn is therefore a **claim on a future queen**,
and a high pawn count means those claims are *unexercised*.

**This reasoning predicted a negative weight on pawns, and the
measurement does not support it.** Earlier runs reported `Pawn` at d =
−0.23 to −0.63 and this document's first draft treated that as partly
real. At 240 games with cluster aggregation the sign **reverses and the
effect vanishes**: d = +0.154 at z = 1.2, indistinguishable from zero.
The negative readings were a phase confound compounded by
pseudo-replication (§5), not a property of the game. Recorded as a
refuted prediction rather than quietly dropped, because it is a clean
example of a plausible mechanism story surviving three runs before the
statistics caught it.

**Break 6 — stalling refuses the cash-out.** Link 3 assumed a defender
must spend a turn answering. But a queen has *actions* — transformation
and manipulation — and an action-only turn is non-spatial, so it neither
moves the piece nor triggers a reactive capture. The project's own
rule-analysis notes are explicit that **"an extra piece automatically
wins under optimal play" is false** in this variant: positions are held
by queen-as-bishop teleport escape, by mutual bishop pins that cancel
both queens, by action stalling, and by symmetric defensive setups. The
final step of Link 3 can be declined outright.

---

## 4. What was actually measured

240 random games, 22,818 sampled states, cluster-aggregated with a
standard error on every effect (§5 explains why earlier numbers were not
trustworthy). Rows reaching z >= 2 in bold:

| feature | games | Cohen's d | SE | z |
|---|---|---|---|---|
| **`Royal`** | 240 | **+0.719** | 0.134 | **5.4** |
| **`RoyalQueenForm:Bishop`** | 140 | **+0.655** | 0.175 | **3.7** |
| **`Bishop`** | 240 | **−0.485** | 0.132 | **3.7** |
| **`RoyalQueen`** | 240 | **+0.378** | 0.131 | **2.9** |
| **`King*royal`** | 240 | **+0.300** | 0.131 | **2.3** |
| `RoyalQueenForm:Rook` | 184 | +0.292 | 0.149 | 2.0 |
| `Knight` | 240 | +0.178 | 0.130 | 1.4 |
| `RoyalQueenForm:Queen` | 240 | +0.165 | 0.130 | 1.3 |
| `Pawn` | 240 | +0.154 | 0.130 | 1.2 |
| `Rook` | 240 | +0.090 | 0.130 | 0.7 |
| `RoyalQueenForm:Knight` | 187 | −0.035 | 0.148 | 0.2 |

### The result

**Two significant findings, one rule, opposite signs — and the rule is
one no general player could be told.**

- **`RoyalQueenForm:Bishop` = +0.655 (z = 3.7).** Holding your royal
  queen *in bishop form* strongly predicts winning. This is the
  queen-as-bishop teleport escape, measured directly from outcomes.
- **`Bishop` = −0.485 (z = 3.7).** Holding *bishops* strongly predicts
  **losing**.

These point in opposite directions and are explained by the same single
clause: **transformation into a form requires that a friendly piece of
that type was captured earlier.** While your bishops live, your queen
*cannot* enter the form that is the game's best defensive resource.
Keeping bishops denies your own queen its escape hatch — so the agent
should want its bishops traded off.

A standard-chess prior would assign bishops a solidly positive value and
would be **wrong, with high confidence, for a reason no amount of chess
experience would suggest.** This is the clearest evidence the project has
that inferring beats supplying.

- **`Royal` = +0.719 (z = 5.4)** is the strongest effect measured
  anywhere in this project — but it is also **close to tautological, and
  must not be read as a discovery.** `Royal` *is* the win condition's
  own quantity, so "a side that has already lost a royal tends to lose"
  is most of what this row says. Its value is as a **positive control**:
  a procedure that failed to find this would be broken. See Break 4 for
  why it coexists with the objective being flat in 100% of opening
  positions.
- The **genuinely inferred** findings are therefore `Bishop` and
  `RoyalQueenForm:Bishop`. Neither appears in the win condition, neither
  is stated anywhere in the rules as something to want or avoid, and
  both are significant at z = 3.7. Those two rows are the result; the
  royal rows are the control.
- **Ordinary material is not what matters here.** `Rook` (z = 0.7),
  `Knight` (z = 1.4) and `Pawn` (z = 1.2) are all indistinguishable from
  zero. Under random play the signal in this game is carried almost
  entirely by *royalty and queen form*, not by piece count.

### The 40-game run was wrong, in an instructive way

An earlier pass over 40 games (identical code, fewer games) reported
`Rook` at d = +0.688, **z = 2.1** — its only ordinary-material finding,
and the one this document's first draft led with. At 240 games `Rook`
falls to d = +0.090, **z = 0.7**. It was a **false positive**, which is
what a z of 2.1 means: a 1-in-20 threshold crossed once.

`Royal` moved the other way, from z = 1.1 to **z = 5.4** — a false
negative at 40 games. So the under-powered run got the two most
important rows **both wrong, in opposite directions.**

The lesson is not "use a significance gate" — the gate was already
there, and it passed the false positive and blocked the true effect. It
is that **a gate cannot substitute for power.** The SE column is what
makes this diagnosable: at 40 games SE ≈ 0.32, so only a d > 0.64 effect
could ever clear the gate, and the real effects are 0.30–0.72.

### Sample size, derived and then confirmed

Clearing z >= 2 on a d ≈ 0.35 effect needs SE <= 0.175, and SE ≈
sqrt(4/g), so **g ≈ 130 games**. Confirmed: at 240 games the measured SE
is 0.130–0.134 for the dense features, and the d ≈ 0.30 effects
(`King*royal`, `RoyalQueen`) resolve at z = 2.3–2.9 as predicted. The
iteration loop's 20 games per round was roughly **6x short** of the
minimum, and its 8-game matches (SE 0.177) could not resolve any
plausible strength difference at all.

## 5. Four estimator defects, and why they matter here

The first version of this measurement reported nine confident weights.
All four of these defects inflated or distorted them, and all four were
found by reading the module's own output rather than by a test failing:

1. **Form counted as material.** A royal queen in knight form was
   counted as `Knight*royal` rather than as the royal queen, so a
   Transformation — which captures nothing and moves nothing — swung the
   feature vector by two units, and **no feature measured whether the
   royal queen was alive at all.** Queen-kind pieces are now counted by
   identity with form carried separately.
2. **The neutral boulder was scored as an enemy of both sides.**
   `Board` spells its colour as the *string* `'none'`, so an `is None`
   guard missed it and it contributed −1 to whoever was to move — the
   same sign for both players, which is not a differential.
3. **The sample was counted in the wrong unit.** States are sampled
   every few plies and every state in a game carries that game's single
   outcome: 880 traces came from **14 games**. Cohen's d on the traces
   divided by a spread estimated from pseudo-replicates. Correcting it
   moved effects in **both** directions — `RoyalQueenForm:Knight` shrank
   6.5× (−0.481 → −0.073), `King*royal` *grew* 4.5× (+0.048 → +0.215),
   and `RoyalQueenForm:Rook` **flipped sign**. It was not an inflation;
   it was an arbitrary distortion.
4. **Perfect separation read as zero.** The guard
   `diff / spread if spread else 0.0` reported a feature that separated
   the two groups *perfectly* as carrying no information, because with
   no within-group variance the denominator vanishes — while its AUC
   read 1.000. This is the opposite failure from the other three.

The first iteration run is void as a result: its round-0 weights were
fitted on the distorted estimator, and its match scores — 37.5% and
62.5% over **8 games**, standard error 0.177 — were within one standard
error of a coin flip in both directions.

---

## 6. Consequences for the agent's design

1. **Discoverability is a property of the policy, not of the game.**
   Random games do end in royal captures — that is how they end — so the
   win condition itself is measurable from random play (`Royal`, z =
   5.4). What random play does *not* produce is the systematic
   **conversion** of a material edge into those captures, which is Links
   3 and 4. That is the most likely reason ordinary material measures
   ~0 here (`Rook` z = 0.7, `Knight` z = 1.4) while royalty and queen
   form measure strongly: the mechanism by which rooks would matter is
   absent from the traces, not absent from the game. A mechanism the
   data-generating policy never exercises cannot be measured, however
   much data is collected — so the feature set you can discover is a
   function of the strength of the policy you discover it from. That is
   circular, and iteration is the only known way out.

   This is a **hypothesis with a decisive test**: re-run the identical
   measurement under a stronger policy. If `Rook` and `Knight` rise, the
   conversion mechanism was the missing ingredient. If they stay at
   zero, then ordinary material genuinely does not matter much in Royal
   Chess, and the four-link chain is broken here more severely than §3
   argues. Either outcome is publishable; the measurement is the same
   either way.
2. **The budget is now a number, not a guess.** ~130 games per round for
   feature significance; ~400 match games to resolve a 5-point strength
   difference at two standard errors. The first run had 20 and 8.
3. **Screen new games with the ratchet test, not with a material
   prior.** Ask whether the game has a cheap, monotone, irreversible
   quantity. That question is game-independent, answerable before
   training, and *predicts in advance* where this method will work — a
   far stronger contribution than a transplanted piece-value table.
4. **The sign-blindness is the result, not a limitation.** The
   procedure put a **negative** weight on bishops (z = 3.7) and a
   **positive** one on the royal queen being in bishop form (z = 3.7). A
   chess prior would have got the first backwards with high confidence,
   and has no vocabulary at all for the second. Both follow from one
   clause — transformation requires a prior friendly capture of that
   type — that no general player could be told and that no amount of
   chess experience would suggest. **That is the case for inferring
   rather than supplying, and it is the strongest claim this line of
   work supports.**

5. **Report power, not just significance.** The 40-game run passed a
   false positive (`Rook`, z = 2.1) and blocked a true effect (`Royal`,
   z = 1.1) through the same correctly-implemented gate. A gate controls
   the false-positive *rate*; it cannot manufacture the power to detect
   an effect that is smaller than the noise. Every effect this project
   reports should carry its SE, so that "not significant" can be
   distinguished from "not measurable at this budget" — they call for
   opposite responses.

---

## See also

- `lgref/experiments/discover.py` — the inference, and the four defects
  documented at the point of fix.
- `lgref/experiments/iterate.py` — the loop, its two failure modes, and
  the significance gate.
- `lgref/experiments/objective.py` — the declared objective, and the
  measurement that it is flat.
- `RULEBOOK.md`, `docs/key-rule-differences.md` — the rules every break
  in §3 rests on.
