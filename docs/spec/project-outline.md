# The Rule–Mechanic–Function Framework

> **On ISEF:** this outline was written with an ISEF submission in mind.
> **That is not a concern for this work.** The target is a full paper for
> IEEE CoG, and nothing in the implementation is shaped by competition
> categories or judging criteria. Read past those references.
>
> **On terminology:** the outline says *mechanic*; this project renamed
> that to **rule**, and MCI to **RCI**. The substance is unchanged.
>
> **This document is authoritative for the ontologies.** Section 7's
> strategic functions and Section 8's design characteristics are
> implemented in `lgref/functions/strategic_ontology.py` and
> `lgref/functions/characteristics.py` respectively, and are kept as
> separate layers on purpose.

## A Computational Framework for Machine Understanding of Formal Game Rules

## 1. Proposed research title

**From Rules to Functions: Machine Discovery and Strategic Evaluation of Game Mechanics from Formal Rule Descriptions**

## 2. Central research question

> Can an artificial intelligence system autonomously infer higher-level game mechanics and their strategic functions directly from formal game rules, without receiving manually specified mechanic boundaries?

Four capabilities:

1. **Mechanic discovery:** Which rules jointly form one mechanic?
2. **Function inference:** What strategic role does that mechanic perform?
3. **Contribution evaluation:** How strongly does it affect the game?
4. **Design reasoning:** Should the mechanic be retained, revised, merged, or investigated further?

The fourth must remain conditional on a specified design objective. A system cannot objectively recommend deleting a mechanic merely because its competitive effect is small; the mechanic may serve aesthetic, thematic, accessibility, or educational purposes.

## 3. Core distinction

### 3.1 Rule

A formal clause determining at least one of: whether an action is legal; how a state changes; what information persists; when a game terminates; how an outcome is assigned. An implementation-level object.

### 3.2 Mechanic

An intervention-coherent group of formal rules that jointly implements a recognizable gameplay operation or state process. A mechanic is not required to be strategically valuable:

> Existence as a mechanic ≠ positive strategic contribution

Four criteria: **structural cohesion**, **dynamic cohesion**, **interface completeness**, **intervention coherence**. Perfect independence is not required.

### 3.3 Strategic function

The role a mechanic performs in the game's decision system — space control, mobility expansion, cycle prevention, threat projection, escape facilitation, termination acceleration, tactical flexibility, outcome balancing. A mechanic can perform several simultaneously.

### 3.4 Strategic contribution

The magnitude and direction of measurable change attributable to a mechanic. Function answers *what does it do*; contribution answers *how much difference does it make in this game*.

## 4. Five-layer representation

- **Layer 0:** formal rules
- **Layer 1:** rule graph
- **Layer 2:** mechanic graph
- **Layer 3:** strategic-function ontology
- **Layer 4:** contribution profile

Output is a structured representation: constituent rules, dependencies, operational behaviour, strategic functions, design characteristics, contribution profile, evidence, recommendation.

## 5. Rule graph

Node fields: `rule_id`, `rule_type`, `head_predicate`, `input_predicates`, `state_variables_read`, `state_variables_written`, `action_types`, `piece_types`, `spatial_scope`, `temporal_scope`, `terminal_dependency`, `execution_frequency`.

Edge types, kept distinct rather than collapsed into one generic dependency: **predicate dependency**, **state dependency**, **legality–transition**, **temporal**, **terminal**, **dynamic co-activation**. A typed, directed, weighted graph.

## 6. Automatic mechanic discovery

Three kinds of evidence: **static structural** (shared predicates, state variables, action types, graph communities), **dynamic operational** (co-activation in traces, phases, frequency), **interventional** (does it still compile, what disappears, is the effect localised).

Soft membership `P(M_j | r_i)` rather than forcing every rule into one mechanic, because shared rules support multiple mechanics.

Candidate score combines static cohesion, dynamic co-activation, intervention coherence, and coupling to unrelated rules. Coefficients are hyperparameters, not objective constants.

## 7. Strategic-function ontology

Hierarchical and multi-label. Describes reusable strategic functions that appear across games rather than enumerating named mechanics.

### Category A: Mobility and access
**Mobility expansion** — increases reachable destinations or legal movement options.
**Mobility restriction** — reduces reachable destinations or constrains movement paths.
**Repositioning** — allows a piece to change strategic location without ordinary movement.
**Escape facilitation** — increases the ability to leave threatened, blocked, or losing positions.
**Penetration** — allows movement through or beyond conventional defensive structures.

### Category B: Threat and capture
**Threat projection** — expands the set of locations or pieces that can be attacked.
**Threat concentration** — concentrates attack power in a region or direction.
**Threat redistribution** — changes where threats occur without necessarily changing total attack capacity.
**Capture enablement** — creates new ways to remove opposing resources.
**Retaliation** — allows a response conditioned on an opponent's preceding action.
**Pinning or immobilization** — restricts an opponent because movement would trigger a penalty or capture.

### Category C: Space and control
**Space control** — changes which regions can be safely occupied or traversed.
**Area denial** — prevents or discourages occupation of a region.
**Path obstruction** — changes routes through persistent or temporary blocking.
**Shared-object influence** — allows multiple players to control or alter the same neutral game element. (An interaction function rather than a direct strategic effect.)

### Category D: Survival and protection
**Survivability** — reduces the probability of immediate or forced capture.
**Temporary protection** — provides protection for a limited duration or condition.
**Royal preservation** — protects a piece whose loss contributes directly to termination.
**Sacrificial clearance** — removes friendly material to create mobility, transformation, or tactical opportunity.

### Category E: Transformation and resource configuration
**Piece transformation** — changes a piece's legal abilities or identity.
**Tactical reconfiguration** — changes the available tactical role of an existing piece.
**Power preservation** — maintains aggregate capability while changing its form.
**Piece-type balancing** — prevents excessive accumulation or disappearance of one type.
**Resource conversion** — exchanges one form of game resource for another.

### Category F: Time, history, and persistence
**Cycle prevention** — prevents repeated-state loops.
**Historical dependency** — makes legality or effects depend on previous states or actions.
**Cooldown regulation** — temporarily prevents immediate reuse or reversal.
**State persistence** — creates a condition that remains active across turns.
**Anti-drift control** — limits prolonged play without strategically irreversible progress.

### Category G: Termination and outcome structure
**Termination guarantee** — ensures that all legal play sequences eventually terminate under defined assumptions.
**Termination acceleration** — reduces expected or tail game duration.
**Draw suppression** — reduces the occurrence of draw outcomes.
**Outcome balancing** — reduces first-player, side, or role advantage.
**Delayed victory** — requires additional objectives before a win is awarded.
**Objective salience** — raises the strategic importance of a particular piece, region, or resource.

### Category H: Choice structure
**Tactical flexibility** — increases the number of meaningfully different short-term choices.
**Strategic diversity** — expands distinct long-horizon plans.
**Forced-choice creation** — reduces the number of viable responses.
**Decision compression** — removes ineffective or dominated alternatives.
**Complexity without depth** — increases legal actions without increasing meaningful strategic alternatives.

This last category matters because the system must distinguish raw branching from strategic value.

## 8. Mechanic design characteristics

Stored **separately** from strategic functions.

| Dimension | Possible values |
|---|---|
| Ownership | player-owned, opponent-owned, neutral, shared |
| Symmetry | symmetric, asymmetric |
| Duration | instantaneous, temporary, persistent |
| Activation | passive, proactive, reactive, conditional |
| Scope | local, regional, global |
| Phase | opening, midgame, endgame, universal |
| Visibility | explicit, hidden, partially observable |
| Direction | enabling, constraining, mixed |
| Target | self, opponent, both, environment |
| Frequency | common, periodic, rare, one-time |
| Dependency | independent, enabling, dependent, compensatory |

Example — Boulder: functions are *space control* and *pawn mobility restriction*; characteristics are neutral, shared, persistent, local-to-regional, symmetric access.

## 9. Function inference

Three channels: **structural** (modifying legal destination predicates suggests mobility; reading history counters suggests history; writing terminal conditions suggests termination; creating temporary immunity suggests survival), **behavioral** (which phases activate it, which pieces use it, how often optimal agents select it), and **causal through ablation** (compare the full game against an interface-preserving variant with the mechanic disabled).

## 10. Operational definitions of major functions

A strategic function should only be used when it has measurable evidence.

- **Mobility expansion** — increased reachable squares, legal destinations, escape paths, effective branching.
- **Mobility restriction** — reduced opponent legal moves, reduced reachable-state volume, increased blocked-piece rate, increased pursuit success.
- **Space control** — reduced safe occupancy for the opponent, increased controlled-region coverage, altered path centrality, increased spatial bottlenecks.
- **Threat projection** — increased attack-map coverage, capturable targets, probability of forcing a defensive reply.
- **Tactical flexibility** — increased near-optimal actions, policy-effective branching, tactical line diversity.
- **Cycle prevention** — fewer repeated states, fewer recurrent regions, lower probability of indefinite play.
- **Termination acceleration** — reduced median and upper-tail game length, fewer non-progress intervals.
- **Outcome balancing** — lower side-specific win disparity, reduced role advantage, robustness across starting conditions.
- **Survivability** — reduced capture probability, increased expected survival time and escape routes, lower forced-loss probability.
- **Complexity without depth** — raw legal-action count increases while effective branching, the optimal-action set, and minimax values barely move.

## 11. Mechanic Contribution Profile

Every mechanic receives a multidimensional profile rather than one score, as standardized effect estimates with uncertainty intervals. It answers: *in which dimensions is the mechanic influential?* It remains the primary output.

### 11.1 Optional Contribution Index

A scalar summary `Σ w_k d_k(M)` where `w_k` represents a stated design objective. **There should not be one universal index.** Different objectives — competitive balance, accessibility, anti-stagnation, tactical richness — produce different summaries, so a recommendation is objective-dependent.

## 12. Mechanic graph

Nodes are discovered mechanics. Edges: **dependency**, **enablement**, **inhibition**, **compensation**, **redundancy**, **synergy**, **conflict**. Necessary because contribution is context-dependent.

## 13. Evidence-constrained explanation engine

Two steps: structured evidence generation from stored results, then a template or tightly constrained model call that turns *only* that record into prose. Every sentence traceable to an evidence field.

## 14. Recommendation engine

Five cautious outputs: **retain**, **revise**, **simplify**, **merge**, **investigate**. "Remove" only when the design objective is specified, contribution is consistently low or harmful, uncertainty is low, thematic value is out of scope, and interaction effects have been tested.

## 15. Royal Chess seed ontology

**Development annotations, not ground truth.** Held out from discovery and inference; used only as reference labels at evaluation.

| Mechanic | Strategic functions | Design characteristics |
|---|---|---|
| Boulder | Space control; pawn mobility restriction; path regulation | Neutral; shared; persistent; symmetric influence |
| Repetition Rule | Cycle prevention; finite-termination support | Global; history-dependent; constraining |
| Tiny Endgame | Draw suppression; termination acceleration; anti-drift control | Endgame-specific; state-dependent |
| Queen Manipulation | Tactical flexibility; tactical reconfiguration; control extension | Active; conditional |
| Queen Transformation | Mobility recovery; escape facilitation; piece-type balancing | Transformative; state-dependent |
| King Capturing Own Pieces | Sacrificial clearance; escape facilitation; transformation enablement | Self-targeting; irreversible |
| Capture King and Queen to Win | Delayed victory; queen salience; royal redundancy | Global terminal rule |
| Knight Invulnerability | Temporary protection; penetration; escape facilitation | Temporary; conditional |
| Knight Jump Capture | Area reach; threat redistribution; attack-path expansion | Conditional follow-up action |
| Rook Hash Pattern | Threat projection; threat concentration; mobility restriction | Geometric; piece-specific |
| Bishop Teleport | Repositioning; access expansion; escape facilitation | Nonlocal; piece-specific |
| Bishop Reactive Capture | Pinning; retaliation; counterplay; risk exposure | Reactive; conditional |
| Pawn Movement and Capture | Controlled advancement; forward pressure; pursuit vulnerability | Directional; asymmetric |
| Promotion to Any Queen Form | Tactical reconfiguration; immediate adaptability; power preservation | Transformative; non-royal outcome |

## 16. Proposed architecture

Formal rule input → parser and normalizer → typed rule dependency graph → static candidate discovery → dynamic trace enrichment → intervention-coherence testing → mechanic graph → strategic function classifier → ablation evaluator → evidence-constrained explanation → objective-conditioned recommendation.

## 17. Model comparison

Baselines: predicate-name similarity; static dependency clustering; dynamic co-activation clustering; human-authored mechanic modules (upper reference, not an automatic system). The proposed hybrid uses static structure, dynamic traces, intervention coherence, and function-specific causal signatures. A GNN may later be added but should not be assumed necessary — a transparent graph-clustering model may be scientifically stronger if it performs similarly.

## 18. Experimental program

- **Phase A** — Royal Chess–driven framework development (exploratory).
- **Phase B** — framework freeze: ontology version, rule representation, clustering method, function labels, feature set, ablation procedure, evaluation metrics.
- **Phase C** — exact capability validation on small solvable games.
- **Phase D** — formal Royal Chess analysis with labels withheld.
- **Phase E** — external-game generalization.
- **Phase F** — expert semantic validation.
- **Phase G** — player behavioral validation.

## 19. Evaluation metrics

**Discovery:** pairwise precision, recall, F1, ARI, NMI, overlapping-cluster F1.
**Function inference:** macro-F1, micro-F1, hierarchical F1, top-k accuracy, calibration error.
**Dependency inference:** edge precision, recall, F1, graph edit distance.
**Strategic reasoning:** effect-direction accuracy, effect-size prediction error, rank correlation with exact contribution, interaction-detection accuracy.
**Explanation:** factual grounding, completeness, contradiction rate, expert usefulness.
**Robustness:** performance after predicate-name obfuscation, rule-order permutation, across seeds, on an unseen game.

## 20. Primary hypotheses

- **H1** — a hybrid model combining static dependencies, dynamic traces and intervention evidence recovers mechanic boundaries more accurately than lexical or single-source baselines.
- **H2** — ablation-derived causal signatures improve strategic-function classification beyond static analysis alone.
- **H3** — the system retains substantially more accuracy than lexical baselines under predicate-name obfuscation.
- **H4** — the system infers meaningful functions in an unseen game without game-specific retraining.
- **H5** — evidence-constrained explanations receive higher grounding scores and lower contradiction rates than unconstrained model explanations.

## 21. Minimum viable version

**Required:** the formal distinction among rules, mechanics, functions and contribution; automatic discovery from rule graphs; strategic-function inference using ablation evidence.
**Strongly recommended:** exact capability benchmarks; Royal Chess case study; unseen-game validation; evidence-constrained explanation.
**Optional:** recommendation engine; player behavioral validation; GNN; physiological sensing.

## 22. Proposed scientific claim

> This work introduces a computational framework that separates formal rules, mechanic structures, strategic functions, and measurable contribution. The system combines typed rule-graph analysis, dynamic execution traces, and controlled ablation to discover candidate mechanics and infer their strategic roles from formal game descriptions.

A stronger claim should only be made if supported by held-out benchmark and cross-game results.

## 23. Conceptual contribution

The central theoretical contribution is the separation:

```
Rule         = formal implementation
Mechanic     = coherent operational module
Function     = strategic semantic role
Contribution = measured causal effect
```

This resolves several ambiguities: a mechanic can perform multiple functions; different mechanics can perform the same function; a mechanic can exist but contribute little; contribution can depend on other mechanics; and a function can generalize across games even when mechanic names do not. That final point is the basis for machine understanding across games.

## 24. Final system output example

```text
Discovered Mechanic: M4
Rules: R17, R21, R24, R31, R33
Structural interpretation: History-dependent endgame transition module

Primary function:   Cycle prevention — confidence 0.91
Secondary:          Termination acceleration — 0.84; Draw suppression — 0.67
Characteristics:    Global; persistent; endgame-specific; constraining

Ablation evidence:
  Repeated-state frequency: +38%
  95th-percentile game length: +27 moves
  Midgame effective branching: no meaningful change
  Side advantage: no meaningful change

Recommendation under anti-stagnation objective: Retain
```
