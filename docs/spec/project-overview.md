# LGREF Project Overview

## A Logic-Based Game Rule Evaluation Framework

LGREF is a proposed research framework for supporting game designers by identifying game rules from computer-readable statements, determining their gameplay roles, and measuring their effects. It combines relationships among statements, gameplay traces, and controlled rule-removal experiments. This overview describes the current terminology and experimental plan; numerical examples illustrate the intended output and are not reported research results.

## 1. Current research title

**LGREF: A Logic-Based Game Rule Evaluation Framework to Support Game Designers in Balancing Games by Automatically Analyzing a Computer-Readable Rule Set**

“Logic-based” describes the framework’s foundation in formal logical statements and their dependencies. The framework also uses gameplay traces and controlled experiments; formal logic is not its only evidence source.

A “computer-readable rule set” is the complete description of one game supplied to an analysis. The singular wording describes one input per run and does not restrict LGREF to one game.

---

## 2. Central research question

> Can a hybrid AI system identify which computer-readable statements implement each game rule, determine each rule’s roles and measured gameplay effects, and outperform single-source methods on unseen games?

The research question concerns three primary capabilities:

1. **Rule identification:** Which statements work together to implement a recognizable game rule, including statements shared by multiple rules?
2. **Role determination:** What does each identified rule do in gameplay?
3. **Effect measurement:** How much and in what direction does gameplay change when that rule is disabled or replaced?

Performance is measured against hidden benchmark mappings, predefined function criteria, and independent exact-search references where available. Comparison with single-source methods takes place on games withheld from development.

**Design recommendations** are an optional extension. They require a stated design objective: a small competitive effect alone does not justify removing a rule that may serve thematic, aesthetic, accessibility, or educational purposes.

---

# 3. Core terminology

The framework separates computer-readable statements, identified game rules, gameplay roles, and measured gameplay effects.

## 3.1 Computer-readable statement

A **statement** is an individual formal clause in the input description. Statements define legal actions, state transitions, persistent information, termination conditions, and outcomes.

One statement may implement only part of a game rule. For example, a knight-protection rule may require separate statements authorizing a jump, recording temporary protection, preventing capture, and ending protection. These are plain-language descriptions of possible clauses, not literal Game Description Language (GDL) syntax.

The phrase **rule set** still refers to the complete game description; its individual implementation units are called **statements** throughout this overview.

## 3.2 Identified game rule

An **identified game rule** is a group of statements that together implements a recognizable gameplay operation, restriction, condition, or outcome requirement. Examples include knight invulnerability, queen transformation, and a repetition restriction.

A rule can exist even when its measured strategic effect is small, redundant, or undesirable. An unused teleport ability remains a game rule even if the tested agents never select it.

### Proposed formal representation

Let the input statement set be:

\[
\mathcal S = \{s_1,s_2,\ldots,s_n\}.
\]

A candidate rule group \(R_j\subseteq\mathcal S\) is evaluated using four kinds of evidence:

**Structural cohesion.** Its statements share predicates, state variables, action types, or transition dependencies.

**Dynamic cohesion.** Its statements activate together or participate in related transitions during gameplay.

**Operational completeness.** The group accounts for the relevant legality, transition, persistence, or outcome behavior, including explicitly recorded dependencies on shared statements.

**Intervention coherence.** The group can be disabled or replaced through a defined intervention that preserves the supporting logic needed by unrelated rules.

These are evidence sources, not a requirement that every rule activate frequently in ordinary simulations. Shared infrastructure and rarely activated rules must remain representable. A statement may belong to multiple rule groups, and a rule may depend on another rule.

## 3.3 Gameplay role or strategic function

A **gameplay role** describes what an identified rule does. **Strategic function** is the technical term for a role involving the game’s choices, threats, resources, history, or outcomes.

Examples include space control, mobility restriction, cycle prevention, escape facilitation, termination acceleration, and tactical flexibility. One rule can perform several roles.

For the boulder, space control and pawn mobility restriction are candidate functions. Being neutral and shared describes its design characteristics and is recorded separately.

## 3.4 Measured gameplay effect

A **measured gameplay effect** is the direction and magnitude of a change in a predefined statistic under a specified rule intervention. **Contribution** may describe this effect, but it is not a universal score for how valuable a rule is.

A role answers “What does the rule do?” An effect answers “How much difference does it make under this evaluation?”

Illustrative examples include a cycle-prevention rule reducing repeated-state frequency, or a flexibility rule increasing the number of near-optimal actions. Report the statistic, comparison, units, agent conditions, and uncertainty with every estimate.

---

# 4. Five-layer representation

The system uses five representational layers:

| Layer | Representation | Purpose |
| --- | --- | --- |
| 0 | Formal statements | Describe legality, transitions, persistent state, termination, and outcomes. |
| 1 | Statement dependency graph | Represent relationships among implementation statements. |
| 2 | Identified rule graph | Represent groups of statements and dependencies among the resulting game rules. |
| 3 | Gameplay function classification | Describe reusable roles through project-defined operational criteria. |
| 4 | Gameplay effect profile | Report measured changes produced by controlled interventions. |

Each identified rule’s output includes its constituent statement IDs, dependencies, operational behavior, candidate and supported roles, design characteristics, measured effects, and supporting evidence. An objective-dependent recommendation may be added as an optional extension.

---

# 5. Statement dependency graph

## 5.1 Nodes

Each node represents one normalized formal statement.

A node contains:

```text
statement_id
statement_type
head_predicate
input_predicates
state_variables_read
state_variables_written
action_types
piece_types
spatial_scope
temporal_scope
terminal_dependency
execution_frequency
```

## 5.2 Edge types

The graph should not contain only one generic dependency edge. It should distinguish:

### Predicate dependency

The output of one statement is used by another statement.

### State dependency

Two statements read or modify the same state variable.

### Legality–transition dependency

One statement authorizes an action that another statement executes.

### Temporal dependency

One statement creates a temporary state later consumed by another.

### Terminal dependency

A statement influences a termination or outcome condition.

### Dynamic co-activation

Two statements repeatedly execute during the same move or transition.

The statement graph is a typed, weighted graph:

\[
\mathcal G_S=(V_S,E_S,\tau,w).
\]

Here, \(V_S\) contains statements, \(E_S\) contains relationships, \(\tau\) records relationship type, and \(w\) records its weight. Dependencies have a direction; shared-variable and co-activation relationships can be represented by symmetric links.

---

# 6. Automatic rule discovery

Rule discovery should combine three kinds of evidence.

## 6.1 Static structural evidence

Derived without playing the game:

- shared predicates;
- shared state variables;
- common action types;
- common piece types where the game has pieces;
- call or dependency paths;
- communities in the statement graph.

## 6.2 Dynamic operational evidence

Derived from execution traces:

- statements activated in the same move;
- statements affecting the same state transition;
- temporal activation sequences;
- shared game phases;
- conditional co-occurrence;
- activation frequency.

## 6.3 Interventional evidence

Derived by disabling or altering statement groups:

- whether the game still compiles;
- whether a coherent behavior disappears;
- which actions become unavailable;
- which state variables become irrelevant;
- whether the effect is localized or scattered.

The discovery model may assign soft membership:

\[P(R_j\mid s_i)\]

rather than forcing every statement into exactly one rule. This is necessary because shared statements may support multiple rules.

---

## 6.4 Candidate rule score

A candidate statement group \(C\) can be scored using an exploratory combination:

\[
Q(C)=\lambda_s S(C)+\lambda_d D(C)+\lambda_i I(C)-\lambda_x X(C).
\]

where:

- \(S(C)\): static cohesion;
- \(D(C)\): dynamic co-activation;
- \(I(C)\): intervention coherence;
- \(X(C)\): coupling to unrelated statements.

The coefficients should initially be treated as hyperparameters, not as scientifically objective constants.

Select coefficients using development and validation games with known statement-to-rule mappings, then freeze them before held-out testing.

---

# 7. Strategic-function ontology

The project-defined function classification should support multiple labels per rule and may use a hierarchy. “Ontology” here means the project’s organized vocabulary, not an existing standardized expert classification. Freeze definitions and measurable criteria before formal testing.

It should not attempt to list every possible named rule. Instead, it should describe reusable strategic functions that appear across different games.

## Category A: Mobility and access

### Mobility expansion

Increases reachable destinations or legal movement options.

### Mobility restriction

Reduces reachable destinations or constrains movement paths.

### Repositioning

Allows a piece to change strategic location without ordinary movement.

### Escape facilitation

Increases the ability to leave threatened, blocked, or losing positions.

### Penetration

Allows movement through or beyond conventional defensive structures.

---

## Category B: Threat and capture

### Threat projection

Expands the set of locations or pieces that can be attacked.

### Threat concentration

Concentrates attack power in a region or direction.

### Threat redistribution

Changes where threats occur without necessarily changing total attack capacity.

### Capture enablement

Creates new ways to remove opposing resources.

### Retaliation

Allows a response conditioned on an opponent’s preceding action.

### Pinning or immobilization

Restricts an opponent because movement would trigger a penalty or capture.

---

## Category C: Space and control

### Space control

Changes which regions can be safely occupied or traversed.

### Area denial

Prevents or discourages occupation of a region.

### Path obstruction

Changes routes through persistent or temporary blocking.

Shared or neutral control is recorded as a design characteristic. Any associated strategic role, such as space control or mobility restriction, needs its own measurable evidence.

---

## Category D: Survival and protection

### Survivability

Reduces the probability of immediate or forced capture.

### Temporary protection

Provides protection for a limited duration or condition.

### Royal preservation

Protects a piece whose loss contributes directly to termination.

### Sacrificial clearance

Removes friendly material to create mobility, transformation, or tactical opportunity.

---

## Category E: Transformation and resource configuration

### Piece transformation

Changes a piece’s legal abilities or identity.

### Tactical reconfiguration

Changes the available tactical role of an existing piece.

### Power preservation

Maintains aggregate capability while changing its form.

### Piece-type balancing

Prevents excessive accumulation or disappearance of one type.

### Resource conversion

Exchanges one form of game resource for another.

---

## Category F: Time, history, and persistence

### Cycle prevention

Prevents repeated-state loops.

### Historical dependency

Makes legality or effects depend on previous states or actions.

### Cooldown regulation

Temporarily prevents immediate reuse or reversal.

### State persistence

Creates a condition that remains active across turns.

### Anti-drift control

Limits prolonged play without strategically irreversible progress.

---

## Category G: Termination and outcome structure

### Termination guarantee

Ensures that all legal play sequences eventually terminate under defined assumptions. This label requires a proof or exhaustive state-graph verification; finite simulations alone cannot establish it.

### Termination acceleration

Reduces expected or tail game duration.

### Draw suppression

Reduces the occurrence of draw outcomes.

### Outcome balancing

Reduces first-player, side, or role advantage.

### Delayed victory

Requires additional objectives before a win is awarded.

### Objective salience

Raises the strategic importance of a particular piece, region, or resource.

---

## Category H: Choice structure

### Tactical flexibility

Increases the number of meaningfully different short-term choices.

### Strategic diversity

Expands distinct long-horizon plans.

### Forced-choice creation

Reduces the number of viable responses.

### Decision compression

Removes ineffective or dominated alternatives.

### Complexity without depth

Increases legal actions without increasing meaningful strategic alternatives.

This final category is important because the system must distinguish raw branching from strategic value.

---

# 8. Rule design characteristics

Design characteristics must be stored separately from strategic functions.

Recommended characteristics include:

| Dimension  | Possible values                                |
| ---------- | ---------------------------------------------- |
| Ownership  | player-owned, opponent-owned, neutral, shared  |
| Symmetry   | symmetric, asymmetric                          |
| Duration   | instantaneous, temporary, persistent           |
| Activation | passive, proactive, reactive, conditional      |
| Scope      | local, regional, global                        |
| Phase      | opening, midgame, endgame, universal           |
| Visibility | explicit, hidden, partially observable         |
| Direction  | enabling, constraining, mixed                  |
| Target     | self, opponent, both, environment              |
| Frequency  | common, periodic, rare, one-time               |
| Dependency | independent, enabling, dependent, compensatory |

For example:

```text
Boulder
Functions:
- Space control
- Pawn mobility restriction

Characteristics:
- Neutral
- Shared
- Persistent
- Local-to-regional
- Symmetric access
```

---

# 9. Function inference

Function inference should combine three channels.

## 9.1 Structural inference

The system examines statements and dependencies to propose candidate roles. Structural clues alone do not establish the magnitude of a gameplay effect.

Examples:

- modifying legal destination predicates suggests a mobility function;
- reading historical-state counters suggests a history function;
- writing terminal conditions suggests a termination function;
- creating temporary immunity suggests a survival function.

## 9.2 Behavioral inference

The system observes how the rule is used.

Examples:

- which game phases activate it;
- whether it is associated with attacks or escapes;
- which pieces use it;
- how frequently evaluated agents select it, using exact-optimal agents only where the game is solved;
- whether it changes opponent replies.

## 9.3 Controlled intervention through ablation

Compare the full game \(G_{\mathrm{full}}\) with a valid variant \(G_{-R_j}\) in which rule \(R_j\) is disabled or replaced. Ablation means this controlled removal of the rule’s behavior.

Define the effect of having the rule present as:

\[
\Delta_j=\mathbf z(G_{\mathrm{full}})-\mathbf z(G_{-R_j}),
\]

where \(\mathbf z\) is the vector of predefined gameplay measurements. Report whether a table uses this presence effect or the opposite removal effect so signs remain interpretable.

Use the same evaluation conditions for both versions and record dependencies that the intervention must preserve. If single-rule comparisons cannot distinguish interacting effects, add experiments removing each rule alone and both together.

For agent-dependent statistics, evaluate a predefined range of strategies and skill levels. Report overall effects using declared aggregation weights and retain the variation across agents. The combined result represents the tested range of play styles; it is not automatically a distribution of real human players.

---

# 10. Operational definitions of major functions

A reported function must satisfy its predefined operational criteria and be supported by the relevant evidence. For a claimed nonzero effect estimated from simulations, require the relevant 95% confidence interval to exclude zero. Exact results may instead provide deterministic evidence. Classify inconclusive evidence as uncertain rather than assuming the function is absent.

## Mobility expansion

Possible evidence:

- increased reachable squares;
- increased legal destinations;
- increased escape paths;
- increased effective branching factor.

## Mobility restriction

Possible evidence:

- reduced opponent legal moves;
- reduced reachable-state volume;
- increased blocked-piece rate;
- increased pursuit success.

## Space control

Possible evidence:

- reduced safe occupancy for the opponent;
- increased controlled-region coverage;
- altered path centrality;
- increased spatial bottlenecks.

## Threat projection

Possible evidence:

- increased attack-map coverage;
- increased number of capturable targets;
- increased probability of forcing a defensive reply.

## Tactical flexibility

Possible evidence:

- increased number of near-optimal actions;
- increased policy-effective branching;
- increased tactical line diversity.

## Cycle prevention

Possible evidence:

- fewer repeated states;
- fewer strongly connected recurrent regions;
- lower probability of indefinite or maximum-turn play.

## Termination acceleration

Possible evidence:

- reduced median game length;
- reduced upper-tail game length;
- fewer non-progress intervals.

## Outcome balancing

Possible evidence:

- lower side-specific win disparity;
- reduced role advantage;
- increased robustness across starting conditions.

## Survivability

Possible evidence:

- reduced capture probability;
- increased expected survival time;
- increased escape-route count;
- lower forced-loss probability.

## Complexity without depth

Possible evidence:

- raw legal-action count increases;
- effective branching changes little;
- optimal-action set changes little;
- minimax values remain unchanged.

---

# 11. Gameplay effect profile

Every identified rule receives a multidimensional effect profile rather than a single importance score. Include the measurement, direction, magnitude, uncertainty, and evaluation conditions.

| Dimension | Example measurement | Required reporting |
| --- | --- | --- |
| Mobility | Legal destinations or reachable positions | Full and modified game values; difference and interval |
| Space control | Opponent safe occupancy or blocked routes | Operational definition and effect estimate |
| Tactical flexibility | Number of near-optimal actions | Exact or approximate action values and tolerance |
| Outcome balance | Side-specific win disparity | Starting conditions, agents, and uncertainty |
| Duration | Median and upper-tail game length | Treatment of capped or unfinished games |
| Cycle prevention | Repeated-state frequency | State definition and intervention effect |

Human decision time and learnability are not measured in the current computational study. Avoid claiming that an agent statistic directly measures human experience.

## 11.1 Optional objective-dependent summary

A scalar summary can be added for a stated design objective:

\[
C_w(R_j)=\sum_k w_k d_k(R_j),
\]

where \(d_k\) is a declared effect measure and \(w_k\) expresses that objective’s priorities. There is no universal contribution index.

For example, a competitive-balance objective may emphasize side advantage and counterplay; an anti-stagnation objective may emphasize repetitions and game duration. Keep raw measurements and uncertainty available alongside any summary. Do not include human accessibility or learnability in a score without corresponding evidence.

---

# 12. Rule graph

After rule discovery, construct a higher-level graph:

\[\mathcal G_R=(V_R,E_R)\]

Each node is a discovered rule.

Edges include:

## Dependency

Rule \(R_2\) cannot operate without \(R_1\).

## Enablement

\(R_1\) increases the opportunity to use \(R_2\).

## Inhibition

\(R_1\) reduces the activation or effectiveness of \(R_2\).

## Compensation

\(R_1\) corrects a negative effect produced by \(R_2\).

## Redundancy

\(R_1\) and \(R_2\) perform substantially overlapping functions.

## Synergy

Their combined effect exceeds the sum of their separate effects.

## Conflict

Their combined effect is weaker or less stable than expected.

This graph records how a rule’s effects depend on other rules. Dependencies may come from statement structure; claims of synergy, redundancy, or compensation require appropriate comparison experiments.

---

# 13. Evidence-constrained explanation

An optional explanation module converts structured results into readable descriptions. It uses measured evidence and the predefined function vocabulary; it does not freely invent a rule’s intended purpose.

## Step 1. Generate structured evidence

Illustrative example only:

```text
Identified rule group: R7
Supported function: cycle prevention
Repeated-state frequency:
    full game: 2.4%
    rule-disabled game: 11.8%
Removal effect: +9.4 percentage points
95% confidence interval for removal effect:
    +7.1 to +11.7 percentage points
Other measurements: report separately with uncertainty
```

## Step 2. Generate a controlled explanation

Example:

> Rule R7 supports cycle prevention under the tested conditions. Removing it increased repeated-state frequency by 9.4 percentage points, with a 95% confidence interval from 7.1 to 11.7 percentage points.

Every numerical and functional claim must map to a structured evidence field. Explanations can be evaluated for unsupported claims and contradictions against these fields without expert usefulness ratings. Template-based text is sufficient; an LLM is optional.

---

# 14. Optional recommendation engine

Recommendations are outside the core accuracy claim. If implemented, they use measured evidence and a designer-specified objective to produce one of five recommendations:

## Retain

Evidence supports an important intended function with manageable trade-offs.

## Revise

The function is useful, but the rule produces undesirable secondary effects.

## Simplify

The rule provides value, but tested alternative implementations obtain similar effects with fewer statements. Lower human cognitive cost requires separate evidence.

## Merge

Two rules have highly overlapping functions and may be redundant.

## Investigate

Evidence is uncertain, unstable, or strongly dependent on another rule.

“Remove” should be used only when:

- the design objective is specified;
- contribution is consistently low or harmful;
- uncertainty is low;
- thematic value is not part of the evaluation;
- interaction effects have been tested.

---

# 15. Royal Chess seed ontology

Aaron’s Royal Chess descriptions supply the following candidate functions for development. They require operational definitions and empirical or exact evidence before being reported as supported functions.

| Rule                      | Strategic functions                                                   | Design characteristics                           |
| ----------------------------- | --------------------------------------------------------------------- | ------------------------------------------------ |
| Boulder                       | Space control; pawn mobility restriction; path regulation             | Neutral; shared; persistent; symmetric influence |
| Repetition Rule               | Cycle prevention; termination support to be verified                          | Global; history-dependent; constraining          |
| Tiny Endgame                  | Draw suppression; termination acceleration; anti-drift control        | Endgame-specific; state-dependent                |
| Queen Manipulation            | Tactical flexibility; tactical reconfiguration; control extension     | Active; conditional; distinctive control mode    |
| Queen Transformation          | Mobility recovery; escape facilitation; piece-type balancing          | Transformative; state-dependent                  |
| King Capturing Own Pieces     | Sacrificial clearance; escape facilitation; transformation enablement | Self-targeting; irreversible                     |
| Capture King and Queen to Win | Delayed victory; queen salience; royal redundancy                     | Global terminal rule                             |
| Knight Invulnerability        | Temporary protection; penetration; escape facilitation                | Temporary; conditional                           |
| Knight Jump Capture           | Area reach; threat redistribution; attack-path expansion              | Conditional follow-up action                     |
| Rook Hash Pattern             | Threat projection; threat concentration; mobility restriction         | Geometric; piece-specific                        |
| Bishop Teleport               | Repositioning; access expansion; escape facilitation                  | Nonlocal; piece-specific                         |
| Bishop Reactive Capture       | Pinning; retaliation; counterplay; risk exposure                      | Reactive; conditional                            |
| Pawn Movement and Capture     | Controlled advancement; forward pressure; pursuit vulnerability       | Directional; asymmetric movement/capture         |
| Promotion to Any Queen Form   | Tactical reconfiguration; immediate adaptability; power preservation  | Transformative; non-royal outcome                |

These labels are **development annotations**, not final ground truth.

Convert candidate functions into explicit measurable criteria during development. These Royal Chess descriptions are hypotheses, not independent test labels. Hiding them at evaluation time does not make Royal Chess unseen after it has guided framework development.

---

# 16. Proposed AI architecture

| Stage | Operation | Output |
| --- | --- | --- |
| 1 | Parse and normalize the computer-readable rule set | Formal statements with stable IDs |
| 2 | Analyze predicates, variables, and dependencies | Typed statement dependency graph |
| 3 | Form candidate rule groups | Initial statement-to-rule memberships |
| 4 | Incorporate gameplay traces | Activation and transition evidence |
| 5 | Test coherent rule interventions | Revised groups and recorded dependencies |
| 6 | Infer candidate functions | Roles proposed from structure and behavior |
| 7 | Compare full and modified games | Gameplay effect estimates and interaction evidence |
| 8 | Apply predefined function criteria | Supported, unsupported, or uncertain functions |
| 9 | Assemble the LGREF report | Identified rules, roles, effects, evidence, and resource use |

Optional explanation and objective-dependent recommendation modules consume the report. Benchmark mappings and held-out function references remain outside the analysis pipeline and are used only for evaluation.

---

# 17. Model comparison

Compare LGREF with simpler methods using the same held-out games and compatible output formats.

## Baseline 1. Predicate-name similarity

Groups statements using names and tokens. This tests how much apparent understanding comes from meaningful identifiers.

## Baseline 2. Static-only analysis

Uses statement dependencies and structural features without gameplay traces or intervention evidence.

## Baseline 3. Dynamic-only analysis

Uses execution traces and co-activation evidence without the hybrid structural and intervention components.

## Hybrid LGREF

Combines static dependencies, dynamic traces, intervention coherence, and function-specific effect measurements. The comparison should separate gains in rule grouping from gains in function identification.

Known benchmark mappings are scoring references, not a competing automatic method. An optional experiment may supply the correct groups to isolate function-classification performance; label it clearly as a reference condition.

Fix each method’s information access and computing budget before testing. Single-source methods receive their declared evidence source; hidden benchmark answers are unavailable to every tested method. Record resource use as well as accuracy.

A graph neural network is optional. A transparent grouping model is sufficient if it supports the required experiments.

---

# 18. Experimental program and current proceedings

The project currently has a revised terminology and flowchart-based experimental plan. The stages below describe intended work; completed results are not implied.

## Phase A. Develop the framework using Royal Chess

Use Royal Chess to develop the statement graph, logging, candidate grouping method, preliminary function classification, and intervention procedure. Its rule descriptions provide development hypotheses. This stage is exploratory.

## Phase B. Construct independent capability benchmarks

Build small, completely solvable games with recorded statement-to-rule mappings, including shared statements, redundant rules, and interacting rules. Retain these mappings outside the model input.

Define each tested function using a statistic, direction, effect criterion, and evaluation conditions. Generate reference effects using an independent exact solver where applicable. Do not assign a reference label by accepting LGREF’s own prediction. Exact search establishes game values and optimal actions; behavioral measurements also require a specified policy and treatment of ties between equally optimal actions.

Create development, validation, and held-out test sets. Keep related game variants in the same split. The small games validate the method’s capabilities; they do not establish every possible role in every game.

## Phase C. Develop and validate the MCTS evaluator

Monte Carlo Tree Search (MCTS) is the approximate gameplay search method evaluated against exact solutions in this stage.

Use development positions to select the MCTS search budget, rollout settings, and other parameters. Freeze them before evaluating separate held-out positions.

Compare chosen actions with exact-optimal action sets: any equally optimal action counts as correct. Also record exact value loss when the selected action is suboptimal. Agreement on actions alone does not validate every gameplay statistic, so separately compare relevant effect estimates with exact references.

Document which games and positions the evaluator can handle reliably before using it as the measurement instrument for larger games.

## Phase D. Freeze LGREF before formal testing

Freeze the statement representation, grouping algorithm, function definitions, features, intervention procedure, agents, search budgets, aggregation rules, metrics, and success criteria. Record this version as **LGREF v1.0**.

Predefine sample counts or stopping rules, random seeds, confidence-interval methods, and treatment of unfinished games. Generate reference results separately from LGREF’s predictions and retain them as hidden scoring data.

## Phase E. Test on held-out games

Run the frozen framework and baselines on games absent from development. Measure statement grouping, function identification, and effect estimation separately. Use independent references where available and report unsupported or uncertain outputs.

Use more than one held-out game when feasible and include distinct game families. A single unseen game supports only a narrow demonstration of generalization.

## Phase F. Analyze Royal Chess as a case study

Apply the frozen framework to Royal Chess and compare its output with operationalized development hypotheses and measured intervention effects. Report it as a case study, not independent unseen-game validation. For unsolved positions, describe MCTS-based results as estimates rather than exact ground truth.

## Phase G. Measure resources and report potential impact

Record runtime, computation cost, peak memory, and rules evaluated per hour. State the hardware and cost calculation. These measurements describe practical resource requirements and potential accessibility; they do not establish correctness or prove savings over human playtesting.

The current procedure does not require expert judgment, expert review time, human playtesting, or physiological sensing.

## Procedure redesign if underlying assumptions fail

If rule groupings overlap, allow statements in multiple rule groups. If rule effects cannot be separated, test rules alone and together. If new functions do not fit existing categories, revise the classification system. If results depend strongly on the agent used, test agents with varied strategies and skill levels, then calculate the overall effects and variation across agents.

These changes revise the grouping representation, experimental comparisons, function classification, or evaluation stage. If redesign occurs after formal testing has begun, record a new framework version and validate it on fresh held-out data; do not present retesting on already examined games as untouched validation.

---

# 19. Evaluation metrics

## Primary measures

| Output | Independent reference | Primary metric |
| --- | --- | --- |
| Statements grouped into game rules | Hidden known statement-to-rule mappings | Grouping F1 using a predefined overlap-aware scoring method |
| Gameplay functions | Labels generated from predefined criteria and independent benchmark evidence | Multi-label function macro-F1 |
| Gameplay effects | Independent exact calculations on solvable benchmarks | Effect-direction agreement and effect-size error |
| MCTS action selection | Exact-optimal action sets on held-out positions | Optimal-action rate and exact value loss |

For grouping, specify how predicted groups are matched to reference groups and how shared statements are scored. Pairwise membership precision, recall, and F1 can supplement the group-level score. Ordinary partition metrics are not the primary choice when overlapping groups are allowed.

For function macro-F1, define the evaluated categories and average per-category F1. Distinguish an absent function from an unevaluable or uncertain case using a frozen scoring policy. Keep the number of evaluated cases visible.

## Effect evidence

Report full-game and modified-game values, effect estimates, and 95% confidence intervals where results are sampled. Each reported nonzero function effect needs the relevant interval to exclude zero; exact results can provide direct evidence. A statistically detectable effect is not automatically a large or desirable effect.

Compare both direction and magnitude against independent references. Preserve agent-specific variation alongside overall effects. If many effects are tested, state the predefined treatment of multiple comparisons.

## Optional secondary measures

- Dependency inference: edge precision, recall, and F1 against known benchmark relationships.
- Interaction detection: agreement with known interacting-rule benchmarks.
- Explanation faithfulness: unsupported numerical or functional claims and contradictions against structured evidence.
- Robustness: performance after identifier renaming, statement-order permutation, and changes in random seeds.

## Resource measurements

Report runtime per game, computation cost per game, peak memory, and rules evaluated per hour. For local hardware, distinguish directly measured usage from cost estimated using a declared rate. Compare resource requirements across games, rule-set sizes, and methods. These are potential-impact indicators rather than accuracy criteria.

---

# 20. Primary hypotheses and success criteria

## H1. Rule identification

The hybrid model will achieve grouping F1 at least **five percentage points higher** than the best evaluated single-source method on held-out games.

## H2. Gameplay function identification

The hybrid model will achieve function macro-F1 at least **five percentage points higher** than the best evaluated single-source method on held-out games.

Five percentage points means an absolute increase of 0.05 on a score scaled from 0 to 1, not a five-percent relative increase. Report uncertainty for the between-method differences and predefine how per-game results are aggregated.

## H3. Evidence for reported functions

Each reported function will satisfy its predefined operational criterion and have the relevant gameplay-change evidence. For a claimed nonzero simulated effect, its 95% confidence interval must exclude zero; independent exact evidence may establish an effect directly on solvable games.

## Secondary research questions

Test how accuracy changes after identifier obfuscation, whether MCTS reproduces exact-optimal decisions and reference effects, and how resource requirements scale. If an explanation module is implemented, test its claims against the structured evidence.

These are proposed criteria, not achieved results. Runtime, cost, memory, and throughput support the discussion of potential accessibility but are not substitutes for the correctness tests.

---

# 21. Minimum viable ISEF scope

The core study should focus on:

1. Distinguishing statements, identified game rules, gameplay roles, and measured effects.
2. Automatically identifying statement groups using structural, dynamic, and intervention evidence.
3. Inferring functions using predefined criteria and measured effects.
4. Validating grouping, functions, and effects with independent small-game benchmarks.
5. Validating the MCTS evaluator against exact search before interpreting larger-game results.
6. Comparing the frozen method with single-source baselines on unseen games.
7. Measuring runtime, computation cost, peak memory, and evaluation throughput.

Royal Chess is a development example and case study. Evidence-constrained explanations, designer-objective summaries, recommendations, and graph neural networks remain optional. Human playtesting and expert semantic ratings are not part of the current required procedure.

---

# 22. Proposed scientific claim and societal relevance

The proposed framework claim is:

> LGREF combines statement dependency analysis, gameplay traces, and controlled rule interventions to identify groups of computer-readable statements that implement game rules, determine their gameplay roles, and measure their effects. Its correctness is evaluated using hidden benchmark mappings, predefined function criteria, and independent exact-search references, with comparisons against single-source methods on held-out games.

The five-percentage-point performance claims remain hypotheses until formal tests support them. Report achieved results, uncertainty, and tested scope in the final claim.

LGREF could make systematic rule evaluation more accessible to game designers by producing repeatable analyses with documented computing requirements. The study measures these requirements directly. It does not establish actual human time savings, player enjoyment, or improved balance after a designer applies its findings; those would require additional studies.

---

# 23. Conceptual contribution

The central distinction is:

| Object | Meaning |
| --- | --- |
| Statement | A formal implementation clause in the input rule set |
| Identified game rule | A group of statements implementing a recognizable gameplay behavior or condition |
| Gameplay role or strategic function | What that rule does, defined through measurable criteria |
| Measured gameplay effect | How much a predefined statistic changes under a specified intervention |

This representation allows a statement to support multiple rules, a rule to perform multiple functions, and different rules to perform the same function. A rule can exist with little measured effect, and its effects can depend on other rules or on the strategies used.

Reusable function definitions provide a basis for evaluating unseen games even when their pieces, terminology, and rule structures differ from those used in development.

---

# 24. Final system output example

The following invented example illustrates the report structure; it is not a result from Royal Chess or a benchmark experiment.

```text
Identified game rule: R7
Constituent statements: S17, S21, S24, S31, S33
Operational description: history-dependent repetition restriction

Supported gameplay role:
Cycle prevention

Design characteristics:
Global; history-dependent; constraining

Measured effect under the tested agent range:
Repeated-state frequency:
    full game: 2.4%
    rule-disabled game: 11.8%
Removal effect: +9.4 percentage points
95% confidence interval: +7.1 to +11.7 percentage points

Other roles:
Not established by the evidence shown here

Dependencies:
Requires history-state tracking

Evaluation conditions:
List strategies, skill levels, budgets, seeds, sample counts,
aggregation weights, and variation across agents in the report.

Resources:
Record runtime, computation cost, peak memory, and throughput.

Explanation:
The identified rule supports cycle prevention. Removing it increased
repeated-state frequency under the declared evaluation conditions.
The observed change supports this role; it does not by itself establish
a termination guarantee or a universal improvement in game balance.
```

This is the intended core output of **LGREF**: identified game rules, their supported roles, and measured gameplay effects with traceable evidence.
