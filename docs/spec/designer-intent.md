# What each rule is for — the designer's own words

The designer supplied these in response to a direct request during
development, with the caveat that they are **not authoritative and not
complete**: "there are many different functions for each rule … a
reference for what the big picture looks like."

They are recorded here and in `lgref/reference/seed_labels.yaml`, which
is the machine-readable copy Phase 5 reads.

## Why the prose is kept, not just the mapping

The framework needs function NAMES from its own 40-function ontology.
The designer wrote prose. Somebody has to translate, and that somebody
was the framework.

Translating silently would make the system the author of the intent it
judges itself against — the exact circularity `lgref/reference/` exists
to prevent. So both layers are stored, and every mapping is marked
`mapped_by: framework` until the designer confirms it. The Phase 5
report prints `[framework]` beside any verdict resting on one.

## The statements, and what they were mapped to

| rule | designer's words | mapped to |
|---|---|---|
| boulder | both players influence; pawn restriction and space control | `shared_object_influence`, `mobility_restriction`, `space_control` |
| repetition rule | prevents cycles; ensures finite game termination | `cycle_prevention`, `termination_guarantee` |
| tiny endgame | draw prevention under optimal play; termination in practical time | `draw_suppression`, `termination_acceleration` |
| queen manipulation | tactical flexibility; unique ability of control | `tactical_flexibility` |
| queen transformation | mobility and escape; prevents overcrowding of a single piece type | `mobility_expansion`, `escape_facilitation`, `piece_type_balancing` |
| king captures friendly | escape and freedom of movement; more options for queen transformation | `escape_facilitation`, `mobility_expansion`, `sacrificial_clearance` |
| win needs both royals | longer and more dynamic games; raises importance of queen | `delayed_victory`, `objective_salience` |
| knight invulnerability | easier to attack; more escape options | `temporary_protection`, `escape_facilitation` |
| knight jump capture | controls larger area; reduces threat density | `threat_projection`, `space_control` |
| rook two-step | greater threat density; reduces mobile flexibility | `threat_concentration`, `mobility_restriction` |
| bishop teleport | positional flexibility; unique stealth theme restriction | `repositioning`, `escape_facilitation` |
| bishop reactive capture | pin opposing pieces; exposes bishop to capture | `pinning_immobilization`, `retaliation` |
| pawn movement | slower advancement, easier to pursue; forward multidirectional capture | `mobility_expansion`, `capture_enablement` |
| pawn promotion | increases flexibility, preserves total power; non-royal | `tactical_flexibility`, `power_preservation`, `resource_conversion` |

Three mappings are exact to the point of being verbatim —
"greater threat density" is `threat_concentration`'s definition,
"preserves total power" is `power_preservation`'s, and "prevents
overcrowding of a single piece type" is `piece_type_balancing`'s.
Those three are the strongest evidence in the project that the
ontology describes something real, because the designer reached for
them independently.

## What the ontology had no name for — and now mostly does

Five phrases could not be mapped when this file was first written. The
designer's response was that **costs matter and should be in the
ontology**, so four functions were added (#230), closing three of the
five.

| was unmappable | now | why it needed a new function |
|---|---|---|
| "exposes bishop to capture" | `self_exposure` (category I) | every one of the outline's forty functions is phrased as something a rule **provides**; none as something it **costs** |
| "reduces threat density during attacking" | `threat_dispersion` | the ontology had concentration and no name for its inverse |
| "slower advancement" | `advance_regulation` | the tempo functions are about a **game's** duration, not how fast material crosses the board |
| — | `tempo_cost` | a turn spent on an action is a turn not spent developing; the same missing idea as `self_exposure`, at the level of the turn rather than the piece |

**Category I, "Cost and trade-off", is an extension beyond the
outline**, made at the designer's request. `OUTLINE_SIZE` and
`EXTENSIONS` keep the two apart, and a test asserts all forty of the
outline's functions are still present rather than merely counting to
forty-four — so an outline function cannot be quietly swapped for an
extension.

`threat_dispersion` is worth noting for how it is kept distinct from
`threat_concentration`: they name **the same two metrics** and predict
**opposite movements**. Nothing would have separated them before
direction became data (#220).

### Two that are still unmapped, for different reasons

- **"unique stealth theme restriction"** — theme, and it should stay
  unmapped. A strategic-function ontology describes what a rule does to
  the decision system; what a rule *expresses* is a different layer,
  closer to the design characteristics. Adding a theme function would
  make the ontology a container for anything a designer might say, which
  is how a vocabulary stops meaning anything.
- **"unique ability of control"** for queen manipulation — ambiguous,
  and **waiting on the designer**. It could be `threat_redistribution`
  ("you move their piece, nothing is captured") or
  `forced_choice_creation` ("you take away their good replies"). The
  structural inference already predicts the first, so mapping the
  designer's phrase onto it would make the held-out label a copy of the
  prediction it exists to test.

## Where the designer and the structure disagree

Worth recording rather than reconciling. For **queen transformation**
the designer said mobility, escape and type balancing. The structural
inference predicts `tactical_reconfiguration` and `power_preservation`
with high confidence and does not predict escape at all.

A designer describing what a rule ACHIEVES and a structure describing
what it DOES are allowed to differ. The difference is a result.

## What is still missing

Only five of the fourteen rules have an ablation variant that measures
them. The other nine are recorded and unmeasurable: the behavioural
sweep plays engine variants, and no variant isolates the rook's
two-step move or the bishop's teleport. Building those variants is
what would let the other nine statements be tested.
