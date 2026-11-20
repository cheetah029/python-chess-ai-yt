# Prior work on automatically analysing the internal structure of formal game descriptions (GDL, Ludii, VGDL)

Scope: does any existing work automatically group the clauses of a game description into "rules" (sets of clauses that together implement one gameplay provision) via a typed clause dependency graph plus overlapping community detection? Searched: GGP structure detection, GGP decomposition and factoring, GDL graph analysis and game recognition, Ludii ludemes and concepts, VGDL/GVGAI rule analysis. Read in full or in part: Hufschmitt et al. 2016 (full text), Kuhlmann & Stone 2007 ECML (full text), Kuhlmann, Dresner & Stone 2006 (full text). Everything else comes from abstracts, publisher and dblp listings, or how later papers describe it.

## GGP structure detection (Kuhlmann/Dresner/Stone, Clune, Fluxplayer)

### Takeaway
Early GGP players find *structures* (successor relations, step counters, boards, markers, pieces, quantities) by matching clauses against hand-written syntactic templates, or by simulation. They do this to build heuristic evaluation functions. They label a few clause patterns. They do not split the whole description into rule units.

### Cited Findings
- Kuhlmann, G., Dresner, K., Stone, P. (2006). "Automatic Heuristic Construction in a Complete General Game Player." *Proc. 21st National Conference on Artificial Intelligence (AAAI-06)*, pp. 1457–1462. It is a complete GGP agent built for the first AAAI GGP competition. — [Stone publications page](https://cs.utexas.edu/~pstone/Papers/bib2html/b2hd-AAAI06-ggp.html); [mlanthology](https://mlanthology.org/aaai/2006/kuhlmann2006aaai-automatic)
- Method (from the full text): "Our agent identifies these structures by syntactically matching game description clauses to a set of template patterns." The structures are successor relations, counters, boards, markers, pieces and quantities. A counter is found by matching a `next(counter(V1)) :- true(counter(V2)) & successor(V2,V1)` template. Successor relations are recognised by their structure, not their names, so scrambled tokens still work. The purpose is to build heuristic evaluation features for minimax search. — [AAAI06 PDF](https://www.cs.utexas.edu/~pstone/Papers/bib2html-links/AAAI06-ggp.pdf)
- A short companion paper also exists: Kuhlmann & Stone, "Automatic Heuristic Construction for General Game Playing," AAAI-06, pp. 1883–1884. — [researchr](https://researchr.org/publication/KuhlmannS06a)
- Clune, J. E. (2007). "Heuristic Evaluation Functions for General Game Playing." *AAAI-07*, pp. 1134–1139. Journal version in *KI – Künstliche Intelligenz* 25(1), 2011 (DOI 10.1007/s13218-010-0074-7). UCLA PhD dissertation, 2008. It builds evaluation functions automatically from GDL descriptions. — [mlanthology](https://mlanthology.org/aaai/2007/clune2007aaai-heuristic); [GI dl](https://dl.gi.de/items/1b35639c-0097-403d-9fd8-140bea628735/full); [ProQuest](https://www.proquest.com/docview/304657114)
- Schiffel, S., Thielscher, M. (2007). "Fluxplayer: A Successful General Game Player." *AAAI-07*. The PDF is hosted on the second author's UNSW page. Fluxplayer won the 2006 competition. — [PDF](https://cgi.cse.unsw.edu.au/~mit/Papers/AAAI07a.pdf); [Schiffel thesis (academia.edu)](https://www.academia.edu/1625467/Knowledge_Based_General_Game_Playing)
- Schiffel, S. (2010). "Symmetry Detection in General Game Playing." *AAAI-10*, pp. 980–985. — [dblp](https://dblp.org/rec/conf/aaai/Schiffel10.html)

### Inferences
- The units these systems find are *semantic roles of individual predicates or functions* (for example, "this is a step counter"). They are not clause groups covering the whole description. Each structure type has its own hand-written template, and there is no graph clustering.
- Their purpose is play strength (search heuristics), not analysing or ablating rules.

### Gaps
- I did not read the full Fluxplayer 2007 or Clune 2007 texts. Some details are from memory and should be checked before quoting: Fluxplayer finds structures such as successor relations, boards and quantities partly by syntax and partly by simulation and argument-type analysis, and it scores goal conditions with fuzzy logic. Clune finds candidate features (piece counts, distances) by analysing which arguments vary and how stable they are under simulation.

## Game factoring and decomposition (Günther/Schiffel/Thielscher, Cox et al., Zhao et al., Cerexhe et al., Hufschmitt et al.)

### Takeaway
This is the closest technical line of work. It builds a dependency graph from a GDL description and splits it into parts automatically. But the graph's nodes are **ground fluents and actions, not clauses**, and the split is into **connected components (independent subgames)**, not modularity communities. Each node belongs to exactly one part (except special handling for serial pivots and steppers). The only goal is faster search and solving, and "rules" as gameplay provisions are never the unit of output.

### Cited Findings
- Günther, M. (2007). "Decomposition of Single Player Games." Master's thesis, TU Dresden. — cited as ref. 6 in [Hufschmitt et al. 2016](https://jnv.up8.site/publication/hufschmitt-2016/hufschmitt-2016.pdf)
- Günther, M., Schiffel, S., Thielscher, M. (2009). "Factoring General Games." *Proc. IJCAI-09 Workshop on General Game Playing (GIGA'09)*, pp. 27–33. It builds "a dependency graph between fluents and actions: the connected parts of the graph represent the different subgames." Potential preconditions, positive effects and negative effects define the edges. Fluents that no action affects are put into a separate subgame. Single-player games only. — [Hufschmitt et al. 2016 (full text read)](https://jnv.up8.site/publication/hufschmitt-2016/hufschmitt-2016.pdf); [bibsonomy](https://www.bibsonomy.org/bibtex/26dbc8cdb6348419bf4e82b69a8e883d)
- Cox, E., Schkufza, E., Madsen, R., Genesereth, M. (2009). "Factoring General Games using Propositional Automata." *GIGA'09*, pp. 13–20. It proves conditions under which a global game is made of several independent simultaneous subgames, using the propositional-automata (propnet) encoding. — [Hufschmitt et al. 2016](https://jnv.up8.site/publication/hufschmitt-2016/hufschmitt-2016.pdf); [Cerexhe et al. 2014 PDF](https://cgi.cse.unsw.edu.au/~mit/Papers/ECAI14.pdf)
- That formalism comes from Schkufza, E., Love, N., Genesereth, M. (2008). "Propositional Automata and Cell Automata: Representational Frameworks for Discrete Dynamic Systems." *AI 2008*, LNCS, pp. 56–66. — [Springer](https://link.springer.com/doi/10.1007/978-3-540-89378-3_6)
- Zhao, D., Schiffel, S., Thielscher, M. (2009). "Decomposition of Multi-player Games." *AI 2009: Advances in Artificial Intelligence*, LNCS 5866, pp. 475–484, Springer (DOI 10.1007/978-3-642-10439-8_48). It extends decomposition to multi-player games using partly instantiated fluents and actions. Connected components of the dependency graph are the independent subgames. The control (turn) fluent has to be ignored, or every action gets linked together. Serial games and compound moves are handled as separate cases. It also shows how to use the decomposition in game-tree search. There is a companion Master's thesis (TU Dresden, 2009). — [Springer](https://link.springer.com/doi/10.1007/978-3-642-10439-8_48); [PDF](https://cgi.cse.unsw.edu.au/~mit/Papers/AI09b.pdf)
- Cerexhe, T., Rajaratnam, D., Saffidine, A., Thielscher, M. (2014). "A Systematic Solution to the (De-)Composition Problem in General Game Playing." *Proc. ECAI 2014*, IOS Press (DOI 10.3233/978-1-61499-419-0-195). It studies composition operators on transition systems, that is, how to combine solutions to subgames. Detecting the decomposition is explicitly out of scope. — [PDF](https://cgi.cse.unsw.edu.au/~mit/Papers/ECAI14.pdf); [IOS Press](https://ebooks.iospress.nl/doi/10.3233/978-1-61499-419-0-195); scope statement per [Hufschmitt et al. 2016](https://jnv.up8.site/publication/hufschmitt-2016/hufschmitt-2016.pdf)
- Hufschmitt, A., Vittaut, J.-N., Méhat, J. (2016). "A General Approach of Game Description Decomposition for General Game Playing." *Computer Games Workshop / GIGA at IJCAI 2016*. Later revised in Springer CCIS 705, pp. 165–177 (DOI 10.1007/978-3-319-57969-6_12). Method, from the full text:
  - Ground the rules (Prolog with tabling).
  - Build a propnet-like logic circuit, factorise it greedily, and recover auxiliary predicates as internal gates.
  - Build a graph whose vertices are "the fully instantiated actions and fluents", with edges for potential preconditions and positive or negative effects. Connected components are the subgames.
  - Handle joint moves, compound moves, serial games (via "pivot" auxiliary predicates), "multiple" games (with useless subgames), and steppers.
  - The authors state the method avoids depending on syntax that a rewrite of the GDL rules could remove.
  - On 40 games, 32 decomposed in under 5 seconds. The stated motivation is speeding up search.
  — [full text](https://jnv.up8.site/publication/hufschmitt-2016/hufschmitt-2016.pdf); [Springer chapter](https://link.springer.com/chapter/10.1007%252F978-3-319-57969-6_12)
- Hufschmitt, A., Vittaut, J.-N., Jouandeau, N. (2018). "Statistical GGP Game Decomposition." *Computer Games Workshop (CGW) 2018*, published in Springer CCIS (DOI 10.1007/978-3-030-24337-1_4). It decomposes games statistically, from simulations rather than from the syntax. — [author page](https://vittaut.perso.lip6.fr/publication/hufschmitt-2018-a); [HAL](https://hal.archives-ouvertes.fr/hal-02182460v1); [unpaywall/DOI](https://unpaywall.org/10.1007%2F978-3-030-24337-1_4)

### Inferences
- How this line differs from the target method:
  - **Nodes:** ground fluents and actions, not clauses.
  - **Unit:** an independent or serial *subgame*, not a gameplay provision such as "knight movement" or "turn alternation".
  - **Partition:** connected components with hard, non-overlapping membership, not Louvain with overlap.
  - **Edges:** action precondition and effect edges only. There are no "same head predicate", "shared fluent read" or terminal-dependence edge types.
  - **Purpose:** search and solving speedup, not rule analysis or ablation.
- In a single, non-compound game like chess, these methods return one component, so they yield no rule-level structure at all. This is the gap the target method fills.
- The turn-control fluent is the one hub every decomposition paper has to remove by hand (Zhao et al.). The target method has the same problem, and its typed, weighted edges could be framed as a principled answer to it.
- Hufschmitt et al.'s point about robustness to syntax (using a ground circuit rather than predicate names) is a known criticism that the target method has to face: a grouping over clauses can change when the description is rewritten. Kuhlmann & Stone's robustness to scrambling (below) is a related benchmark.

### Gaps
- I could not get the Günther et al. 2009 and Cox et al. 2009 full texts. Their descriptions above come from the Hufschmitt and Cerexhe papers.
- I did not check the 2018 statistical paper's abstract in detail (the author page redirected and I did not fetch it).
- I found no decomposition paper after 2018 in GGP (searched "GDL decomposition / dependency graph / community detection 2023–2025"; nothing relevant came up).

## GDL rules analysed as logic programs: rule graphs, recognition, dependency graphs, propnets

### Takeaway
Kuhlmann & Stone's rule graphs (2007) turn a whole GDL description into a coloured graph over the syntax tree, then match it to known games by graph isomorphism for transfer learning. Later work (Jung & Hoey) adds approximate graph edit distance. Atom dependency graphs are standard in GDL theory for checking well-formedness (stratification, acyclicity). None of this work groups clauses into rule units.

### Cited Findings
- Kuhlmann, G., Stone, P. (2007). "Graph-Based Domain Mapping for Transfer Learning in General Games." *Proc. ECML 2007*, LNCS 4701, pp. 188–200 (DOI 10.1007/978-3-540-74958-5_20). From the full text: "Rule graphs are colored, directed graph representations of game rules." Construction:
  - one node per logical sentence, relational sentence, constant and variable;
  - argument edges from each term to its arguments;
  - order edges between consecutive arguments, and from the rule head to each body literal;
  - label nodes linking all instances of the same variable or non-keyword constant.
  Game recognition is done with off-the-shelf graph isomorphism (VF). The authors prove that isomorphic rule graphs mean scramble-equivalent descriptions. Game variants are found by applying transformations to the rule graph. The purpose is domain mapping for value-function transfer in RL. — [PDF](https://cs.utexas.edu/~ai-lab/pubs/ECML07-rulegraphs.pdf); [Springer](https://link.springer.com/content/pdf/10.1007/978-3-540-74958-5_20.pdf)
- Jung, J., Hoey, J. "Distance-Based Mapping for General Game Playing" (IEEE CoG 2021, per the Ludii citations hosting). It estimates edit distances between rule graphs of different games. — [PDF](https://ludii.games/citations/COG2021-1.pdf)
- Jung, J. (2024). "Graph-Based Mapping for Knowledge Transfer in General Game Playing." PhD thesis, University of Waterloo. — [UWSpace](https://uwspace.uwaterloo.ca/items/131c72da-bcc6-49d8-945a-943d8f471d63)
- Gunawan, A., et al. (2022). "A Graph Neural Network Reasoner for Game Description Language." *Proc. KR 2022*. It uses a GNN to reason over GDL. — [KR proceedings](https://proceedings.kr.org/2022/46/kr2022-0046-gunawan-et-al.pdf)
- He et al. (2024). "Verification of General Games with Imperfect Information using Strategy Logic." *Proc. KR 2024*. It defines the atom dependency graph of a ground GDL-II description, used for acyclicity checks. — [KR proceedings](https://proceedings.kr.org/2024/40/kr2024-0040-he-et-al.pdf)
- Standard GDL validity conditions are stated over a dependency graph: no cycles through a negative edge (stratification), and restrictions on where `init`, `does` and `next` may appear. — [Ruan & Thielscher, Model Checking Games in GDL-II (CGW 2012)](https://cgi.cse.unsw.edu.au/~mit/Papers/CGW12.pdf)

### Inferences
- The rule graph covers the *whole* description for matching against other games. It does not segment one description internally. Its "rule" is a single GDL clause in the logic-programming sense, not a gameplay provision.
- The predicate dependency graphs used in GDL theory are untyped (only positive or negative edges) and serve well-formedness checks. The target method adds typed edges (legal→next via `does`, temporal write→read, terminal dependence) and community detection. That pairing does not appear in any of the GDL literature I found.

### Gaps
- Jung & Hoey: I did not open the venue page to confirm the exact venue and year. "CoG 2021" is inferred from the hosted file name COG2021-1.pdf. Treat it as partly unverified.
- Gunawan et al. 2022 and He et al. 2024: the full author lists were not checked.
- I did not survey propnet latch and invariant detection in depth (for example, work on finding latches, inhibitors and invariants in propnets in later GGP players). I found no source in this session to cite for it.

## Ludii: ludemes, concepts, distances, and whether rule units are discovered automatically

### Takeaway
In Ludii, rule units are **written by humans by design**: each game is a ludeme expression (a tree of predefined keywords). Analysis runs on ludeme counts or on more than 600 hand-defined "concepts", and is used for game distance, clustering, heuristic prediction, recommendation and reconstruction. I found no Ludii work that automatically *discovers* rule groupings from a lower-level description.

### Cited Findings
- Piette, É., Stephenson, M., Soemers, D. J. N. J., Browne, C. (2021). "General Board Game Concepts." *Proc. IEEE Conference on Games (CoG) 2021* (DOI 10.1109/CoG52621.2021.9618990); arXiv:2107.01078. It formalises "game concepts" at the level of the game, a trial, a state or a move. Listed uses include rule reconstruction for ancient games, recommender systems, transfer learning and explainable AI. — [arXiv](https://arxiv.org/abs/2107.01078v1); [UCLouvain](https://research.dial.uclouvain.be/handle/2078.5/253792)
- Piette, É., Soemers, D. J. N. J., Stephenson, M., Sironi, C. F., Winands, M. H. M., Browne, C. "Ludii – The Ludemic General Game System." (arXiv 2019; ECAI 2020). Games are single symbolic expressions of predefined ludemes, from a few dozen for Tic-Tac-Toe to several hundred for Chess. — [arXiv 1905.05013](https://arxiv.org/pdf/1905.05013); [ResearchGate](https://www.researchgate.net/publication/333077653_Ludii_-_The_ludemic_General_Game_System)
- Stephenson, M., Soemers, D. J. N. J., Piette, É., Browne, C. (2023). "Measuring Board Game Distance." *Computers and Games (CG 2022)*, LNCS 13865, pp. 121–130. It argues that ludeme lists alone miss how ludemes interact (for example, "hop" does not say what can be jumped), so it measures distance over concepts (cosine and Euclidean). — [arXiv 2301.03913](https://arxiv.org/abs/2301.03913)
- Stephenson et al. (2021). "General Game Heuristic Prediction Based on Ludeme Descriptions." It clusters games by their ludemes with t-SNE (three groups) and uses a decision tree to find which ludemes define the clusters. Note that this clusters *games*, not the rules inside one game. — [arXiv 2105.12846](https://arxiv.org/pdf/2105.12846)
- Stephenson et al. (2021). "Automatic Generation of Board Game Manuals." It produces rule explanations from Ludii descriptions. — [arXiv 2109.09507](https://arxiv.org/pdf/2109.09507)
- Soemers, D. J. N. J., et al. (2022). "Spatial State-Action Features for General Games." It cites the GGP factoring literature. — [arXiv 2201.06401](https://arxiv.org/pdf/2201.06401)
- Browne, C. (2008). "Automatic Generation and Evaluation of Recombination Games." PhD thesis, QUT. This is where ludemes and the Ludi system originate, with "a ludeme is an element of play" taken from Parlett. — [QUT eprints](https://eprints.qut.edu.au/17025/1/Cameron_Browne_Thesis.pdf)

### Inferences
- A ludeme is the closest existing idea to the target method's "rule". But in Ludii, ludemes are given by the language and grouped by its authors. The target method instead infers rule groups from a flat logic program (GDL), where no such grouping exists. That inversion is the main novelty claim against Ludii.
- Ludii concept analysis (correlations, importance, distance) works *across* games. It is not an ablation of single rules within one game.

### Gaps
- I found no source showing that the Digital Ludeme Project studies ludeme or concept importance for gameplay outcomes in a way that ablates rules inside a game. Searches returned only the concepts and distance papers. Reconstruction papers (for example, Browne et al. on reconstructing ancient games) were not opened.
- Recent LLM work on generating Ludii games (2024–2025) was not checked in this session.

## VGDL / GVGAI rule analysis and rule generation

### Takeaway
VGDL descriptions are already split into explicit sections (sprite set, interaction set, termination set, level mapping), so a "rule" is a ready-made line of the interaction or termination set. Work in this area generates or selects rules (GVG-RG), or finds *critical mechanics* from description parsing plus playtraces. Rule segmentation is never needed.

### Cited Findings
- Khalifa, A., et al. (2019). "General Video Game Rule Generation." The GVG-RG framework produces interaction and termination sets for a given level, with random, constructive and search-based generators. — [arXiv 1906.05160](https://arxiv.org/pdf/1906.05160); [ar5iv](https://ar5iv.org/html/1906.05160)
- The GVGAI framework overview defines the interaction set (effects of two sprites colliding) and the termination set. — [ar5iv 1802.10363](https://ar5iv.labs.arxiv.org/html/1802.10363)
- Green, M. C., Khalifa, A., Barros, G. A. B., Machado, T., Togelius, J. (2019–2020). "Automatic Critical Mechanic Discovery Using Playtraces in Video Games." arXiv:1909.03094 (v3, 2020). It combines "game description parsing and playtrace information" to find the critical mechanics. A user study shows these match human judgements, and MCTS agents using them do better on four GVGAI games. — [arXiv](https://arxiv.org/abs/1909.03094)
- "AtDelfi: Automatically Designing Legible, Full Instructions For Games" (arXiv 2018) is the earlier tutorial and mechanic-explanation system in the same line. — [arXiv 1807.04375](https://arxiv.org/pdf/1807.04375)
- More recent work: GVGAI-LLM (2025) translates VGDL rules into natural language. — [arXiv 2508.08501](https://arxiv.org/pdf/2508.08501). A 2026 preprint treats VGDL as a domain-specific structural causal model and evaluates recovering the rule set from gameplay. — [arXiv 2602.00190](https://arxiv.org/pdf/2602.00190)

### Inferences
- Critical mechanic discovery is the closest match in *purpose*: it decides which rules matter for winning. But in VGDL the rule units are given by the syntax, so the target method's clustering step has no equivalent there. Its "importance" is decided by playtraces, which compares with the target method's measured gameplay effects.

### Gaps
- I did not check the venue of the critical-mechanics paper (arXiv lists none). The authors and venue of AtDelfi, and the authors of the 2026 SCM preprint, were not checked.

## Work that explicitly identifies a game's "rules" from its formal description in order to evaluate or ablate them

### Takeaway
I found no prior work that (a) automatically groups GDL clauses into gameplay-provision rules, (b) uses a typed clause dependency graph, or (c) uses community detection, let alone overlapping Louvain. The nearest work falls into three groups:
- GGP decomposition: fluent/action graphs, connected components into subgames, for search.
- Kuhlmann & Stone rule graphs: whole-description isomorphism, for transfer.
- Rule-importance work in VGDL and Ludii, which starts from rule units that are given by the language rather than discovered.

### Cited Findings
- A targeted search for GDL dependency graphs combined with community detection (2023–2025) found only decomposition and verification papers. — [Zhao et al. PDF](https://cgi.cse.unsw.edu.au/~mit/Papers/AI09b.pdf); [He et al. KR 2024](https://proceedings.kr.org/2024/40/kr2024-0040-he-et-al.pdf)
- A search for automatic segmentation of rules from formal descriptions or ludemes found only clustering of games by ludemes, not of rules inside a game. — [arXiv 2105.12846](https://arxiv.org/pdf/2105.12846)
- Possibly relevant, not opened: a 2025 arXiv paper "Repairing General Game Descriptions" (arXiv 2508.10438) came up in the factoring search. It works on GDL descriptions, and its link to rule segmentation was not checked. — [arXiv](https://arxiv.org/pdf/2508.10438)

### Inferences
- Positioning: the target method can be described as moving the dependency graph from GGP decomposition (Günther et al. 2009; Zhao et al. 2009; Hufschmitt et al. 2016) to a different level. Three things change:
  - nodes become clauses instead of ground fluents and actions, with typed edges;
  - the partition becomes modularity-based communities with overlap, instead of connected components;
  - the goal becomes identifying and ablating rules, instead of speeding up search.
- Its output resembles Ludii ludemes, but here the units are inferred rather than authored.
- Expected reviewer objections, taken from this literature:
  - Grouping clauses depends on syntax (Hufschmitt et al.'s criticism).
  - Results should hold up under scrambling and rewriting (Kuhlmann & Stone's criterion).
  - The turn-control hub (Zhao et al.).

### Gaps
- Coverage of 2019–2026 GGP-specific venues (GIGA workshop proceedings, IEEE ToG) is thin. A dblp sweep of GIGA 2019–2024 tables of contents was not done.
- arXiv 2508.10438 ("Repairing General Game Descriptions") is unread and should be checked for any rule-unit notion.
