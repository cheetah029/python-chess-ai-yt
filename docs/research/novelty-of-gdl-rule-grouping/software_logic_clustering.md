# Methodological analogues for clustering the rules of a logic specification into functional modules

Method being assessed: a typed, weighted dependency graph over the clauses of a GDL description (edge types: predicate call, same head predicate, shared fluent reads, temporal write-to-read across steps, legal/next linked by a shared action), with hub and negated-guard filtering, generic infrastructure held out, Louvain with a calibrated resolution, overlapping membership for shared helpers, and validation against hand-labelled modules.

Verification legend: **[V]** means bibliographic details were confirmed against a real source in this session (link given). **[NV]** means the reference is cited from background knowledge and was NOT re-verified this session. The report writer should check NV items or drop them.

## Software architecture recovery and module clustering

### Takeaway
Almost every step of the pipeline has a direct precedent in software clustering. Bunch did graph clustering of a module dependency graph with a modularity-style fitness function. Weighted dependency types and their effect on accuracy have been studied (Lutellier et al.). Omnipresent or hub removal followed by reattachment is FICABOO (Wen and Tzerpos), and Müller et al. described omnipresent modules earlier. Louvain on call and dependency graphs is now routine. What is new is the *substrate*: clauses of a logic program, with GDL-specific edge types (temporal next-to-true flow, legal/next pairing through a shared action, negated-guard filtering). The clustering machinery itself is not new.

### Cited Findings
- **Mitchell, B. S. & Mancoridis, S. (2006). "On the automatic modularization of software systems using the Bunch tool." IEEE TSE 32(3):193–208, doi:10.1109/TSE.2006.31 [V].** Bunch clusters a graph of system entities and relations. It scores partitions with a fitness function (MQ, which rewards intra-cluster edges and penalises inter-cluster edges) and searches for a good partition with hill-climbing or genetic search. — [dblp](https://dblp.org/rec/journals/tse/MitchellM06); [IEEE metadata](https://manuscript.isc.ac/Inventory/49/880163.htm)
  - Comparison: MQ is a modularity-like objective, so this is the closest ancestor of "Louvain on a dependency graph". Bunch also supported manual handling of "omnipresent" modules and user-specified clusters [NV for these feature details], which is analogous to the method's hub filtering and its held-out infrastructure.
- Earlier Bunch papers [NV]: Mancoridis, Mitchell, Rorres, Chen & Gansner (1998), "Using automatic clustering to produce high-level system organizations of source code," IWPC 1998. Mancoridis, Mitchell, Chen & Gansner (1999), "Bunch: A clustering tool for the recovery and maintenance of software system structures," ICSM 1999.
- **Wen, Z. & Tzerpos, V. (2005). "Software clustering based on omnipresent object detection." IWPC 2005 [V].** FICABOO pipeline: (1) cluster, (2) detect omnipresent objects, (3) remove them from the dependency graph, (4) recluster, (5) reattach them by Orphan Adoption. — [bibtex record](https://bibtex.github.io/IWPC-2005-WenT.html); [summary](https://www.bohrium.com/paper-details/software-clustering-based-on-omnipresent-object-detection/812278215555940352-104696)
  - Comparison: this is nearly the same as "filter hub nodes, hold out generic shared infrastructure, then assign it afterwards". The method's overlap for shared helpers is a soft version of orphan adoption, which assigns to exactly one cluster.
- Müller, Orgun, Tilley & Uhl (1993), "A reverse-engineering approach to subsystem structure identification," J. Software Maintenance: Research and Practice 5(4) [NV]. Commonly credited with the notion of "omnipresent" modules, meaning heavily used utilities that should be set aside before subsystem identification.
- Tzerpos, V. & Holt, R. C. (2000), "ACDC: An algorithm for comprehension-driven clustering," WCRE 2000 [NV]. Pattern-based rather than objective-based. It uses subgraph-dominator and "support library" patterns, and the support-library pattern explicitly segregates widely used utilities, which parallels the held-out infrastructure.
- Andritsos, P. & Tzerpos, V. (2005), "Information-theoretic software clustering," IEEE TSE 31(2) (LIMBO) [NV]. Uses the information bottleneck over entity features and can combine structural and non-structural attributes, which parallels mixing edge types.
- **Garcia, J., Ivkovic, I. & Medvidovic, N. (2013). "A comparative analysis of software architecture recovery techniques." ASE 2013, pp. 486–496, doi:10.1109/ASE.2013.6693106 [V].** Compared six techniques against eight carefully verified ground-truth architectures, and reported that even the best technique had surprisingly low accuracy. — [researchr](https://researchr.org/publication/GarciaIM13); [IEEE metadata](https://manuscript.isc.ac/Inventory/49/660580.htm)
- **Lutellier, T., Chollak, D., Garcia, J., Tan, L., Rayside, D., Medvidovic, N. & Kroeger, R. (2018). "Measuring the impact of code dependencies on software architecture recovery techniques." IEEE TSE 44(2):159–181, doi:10.1109/TSE.2017.2671865 [V].** Evaluated nine variants of six techniques on 8 dependency types. Symbol dependencies beat include dependencies, and direct dependencies and module-level granularity also help, but overall accuracy is low. The Chromium ground truth took two years of collaboration with its developers. The ICSE 2015 conference version is "Comparing software architecture recovery techniques using accurate dependencies." — [Purdue PDF](https://www.cs.purdue.edu/homes/lintan/publications/archrec-tse17.pdf); [UWSpace](https://uwspace.uwaterloo.ca/handle/10012/9554); [search record for ICSE'15 version](https://vufind-test.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-c285t-d1ec05c5ca17c555875fbb7ba0041d3a47b40a35356f399c8cc4f79ec959f0d13)
  - Comparison: this is the closest empirical analogue to the method's choice of *which edge types to include and how to weight them*. The finding that dependency type materially changes recovery accuracy supports running ablations over edge types (call, same-head, fluent-read, temporal, legal-next).
- **Louvain on software graphs** is well established. Uses include Debian package dependency networks, class-level Java dependencies (Louvain against Greedy Modularity, k-clique and Girvan–Newman), and Arcan-extracted class dependencies weighted by number of uses (Louvain against Leiden). One study found Louvain the most reasonable community-detection choice for the software module clustering problem. Another cautioned that Louvain communities can be driven partly by network heterogeneity and size rather than by function. — [arXiv 1111.5251](https://arxiv.org/pdf/1111.5251); [J. Web Eng. paper](https://journals.riverpublishers.com/index.php/JWE/article/download/26395/22469?inline=1); [core.ac.uk](https://core.ac.uk/download/518780754.pdf)
- Open-source code-intelligence tools now run Louvain on call graphs to find "functional modules", with resolution fixed at 1.0. That confirms the commodity status of the base step, and that calibrating resolution is a step beyond the default. — [codebase-memory-mcp note](https://instagit.com/DeusData/codebase-memory-mcp/louvain-community-detection-algorithm-functional-modules.md); [infigraph-core docs](https://docs.rs/infigraph-core/1.5.5/infigraph_core/cluster/)
- **Overlapping clustering** in software is rarer. Some work notes Infomap yields "slightly overlapping" cohesive clusters when combining structural and semantic information. Cluster ensembles have been proposed instead of a single algorithm. — [arXiv 2102.04710](https://ar5iv.arxiv.org/html/2102.04710); [IEEE Access 2019 cluster ensembles](https://scholarworks.bwise.kr/cau/bitstream/2019.sw.cau/32805/1/Software%20Architecture%20Module-View%20Recovery%20Using%20Cluster%20Ensembles.pdf)
- Information-fusion recovery (2023) combines multiple dependency and semantic sources, much like a typed and weighted multi-edge graph. — [arXiv 2311.04643](https://arxiv.org/pdf/2311.04643)
- Background for Louvain and resolution [NV]: Blondel, Guillaume, Lambiotte & Lefebvre (2008), "Fast unfolding of communities in large networks," J. Stat. Mech. P10008. Reichardt & Bornholdt (2006), "Statistical mechanics of community detection," Phys. Rev. E 74:016110 (resolution parameter γ). Fortunato & Barthélemy (2007), "Resolution limit in community detection," PNAS 104(1). Traag, Waltman & van Eck (2019), "From Louvain to Leiden," Sci. Rep. 9:5233.

### Inferences
- Generic hub filtering, Louvain or modularity, and the weighting of dependency types are all prior art. A novelty claim cannot rest on them.
- Plausibly novel: (a) the edge *ontology*, especially temporal write-to-read edges and legal-next edges through a shared action, which have no direct analogue in call-graph clustering; (b) treating negated guards as a separate filtered edge class; (c) applying all of this at clause granularity rather than file or class granularity.
- Calibrating resolution against labelled data is common practice in network science but uncommon in SAR papers, which mostly use the default γ=1 or Bunch's MQ.

### Gaps
- No full-text check of Bunch's omnipresent-module handling or ACDC's support-library pattern in this session.
- No dedicated software overlapping-clustering paper was verified, for example fuzzy or soft clustering of modules.

## Evaluation of software clustering against ground truth

### Takeaway
There is a mature metric toolkit for comparing a recovered partition with a hand-labelled one: MoJo, MoJoFM, a2a, c2c and cvg, and ARI. Garcia et al. and Lutellier et al. establish the protocol of building expert-verified ground truth. Most of these metrics assume *non-overlapping* partitions, so overlapping membership needs an adapted metric such as overlapping NMI or omega index, or a rule for collapsing overlaps.

### Cited Findings
- **Wen, Z. & Tzerpos, V. (2004). "An effectiveness measure for software clustering algorithms." IWPC 2004 [V]** (MoJoFM). — [bibtex record](https://bibtex.github.io/IWPC-2004-WenT.html)
- Tzerpos, V. & Holt, R. C. (1999), "MoJo: A distance metric for software clusterings," WCRE 1999 [NV]. Counts the minimum Move and Join operations needed to turn one partition into another.
- a2a is an architecture-to-architecture similarity on a 0–100 scale, computed from add, remove and move operations on entities and normalised against an empty architecture. c2c measures entity overlap between two clusters, and cvg builds on it. — [arXiv 1901.07700](https://arxiv.org/pdf/1901.07700)
- A 2023 study found a2a poorly discriminating, because it stays high even when clusters merge. cvg depends heavily on its threshold. The study recommends ARI and an adjusted a2a. — [arXiv 2311.04643](https://arxiv.org/pdf/2311.04643)
- Behnamghader et al. used these metrics in an empirical study of architectural change in open-source systems. — [typeset](https://typeset.io/pdf/an-empirical-study-of-architectural-change-in-open-source-3rhwlqcn2a.pdf). The exact original paper introducing a2a was not confirmed (likely Behnamghader et al. 2017, Empirical Software Engineering, "A large-scale study of architectural evolution in open-source software systems" [NV]).
- Ground-truth construction: Garcia, Krka, Mattmann & Medvidovic (2013), "Obtaining ground-truth software architectures," ICSE 2013 (SEIP) [record found, details NV]. — [typeset](https://typeset.io/papers/obtaining-ground-truth-software-architectures-4920kws7cd)

### Inferences
- Validating against hand-labelled modules matches SAR practice. Reporting MoJoFM and ARI, alongside an overlap-aware measure, would make results comparable with that literature.
- Hand-labelled ground truth for small game descriptions is cheap compared with the two-year Chromium effort. But there is a single labeller and the labels are built with knowledge of the method, which is a circularity risk SAR papers handle with independent experts.

### Gaps
- No verified source for overlap-aware metrics applied in SAR.

## Logic programs: modularisation, dependency graphs, splitting, slicing, rule-base clustering

### Takeaway
Logic programming offers *semantic* decomposition (splitting sets, module theorems, predicate-dependency SCCs) and *query-driven* extraction (slicing), but not unsupervised functional clustering of clauses. The closest analogue is the 1980s–90s expert-system literature, which clustered production rules by data flow: Jacob and Froscher (1990), the knowledge-base partitioning problem (DKE 1992), and graph-partitioning approaches. That literature essentially is "group rules by shared facts and minimise inter-group connections", without modern community detection or typed temporal edges.

### Cited Findings
- **Jacob, R. J. K. & Froscher, J. N. (1990). "A software engineering methodology for rule-based systems." IEEE TKDE 2(2) [V for title, authors, venue and year; volume and issue NV].** Divides rules into groups based on data flow, focuses on the facts that carry information between groups, and gives an algorithm for grouping rules automatically by cluster analysis over a rule "relatedness" measure. It also separates control variables and control rules from domain knowledge. — [record](https://www.bohrium.com/paper-details/a-software-engineering-methodology-for-rule-based-systems/812458443427282946-2486)
  - Comparison: the strongest single precedent. It clusters rules by shared facts, which corresponds to the method's shared-fluent-read edges, and it segregates control rules, which parallels holding out generic infrastructure. The method adds typed and temporal edges, modularity optimisation with calibrated resolution, and overlap.
- "The knowledge base partitioning problem: Mathematical formulation and heuristic clustering," Data & Knowledge Engineering, DOI 10.1016/0169-023X(92)90045-D (likely 1992; authors not confirmed) [partially V]. Formulates rule allocation as a 0–1 quadratic program that minimises inter-partition connections under size limits (NP-complete), and solves it with a nearest-neighbour clustering heuristic. — [record](https://datalearner.com/academic/journal-papers/0169-023X/volumes-and-issues/35/paper-detail/32344) (later returned 404, so the record was seen only in a search snippet)
- "A graph theory-based approach for partitioning knowledge bases," INFORMS J. Computing 7(3):286 (authors NV). Models the KB as a graph and adapts minimum-cost graph partitioning. — [INFORMS](https://pubsonline.informs.org/doi/pdf/10.1287/ijoc.7.3.286)
- A CLIPS study semi-automatically structured a rule base into groups of rules that carry related information (NASA NTRS). — [NTRS](https://ntrs.nasa.gov/citations/19960001820)
- Prolog work: a 1991 paper clusters Prolog KBs for distributed computation using rule–fact dependency relations. There is also a modularisation approach for Prolog KBs (Information Systems) that localises inference to subsets of the KB. Full citations were not verified. — [academia.edu](https://www.academia.edu/97166161/Clustering_PROLOG_programs_for_distributed_computations); [record](https://datalearner.com:8443/academic/journal-papers/0306-4379/volumes-and-issues/88/paper-detail/108659) (fetch failed)
- Prolog refactoring includes a "Split Module" refactoring but no automatic clustering. — [arXiv cs/0406026](https://arxiv.org/pdf/cs/0406026). SWI-Prolog's prolog_xref and prolog_codewalk produce predicate dependency graphs, and practitioners find predicate-level graphs unreadable without aggregation. — [SWI Discourse](https://swi-prolog.discourse.group/t/swi-dependency-graph/5978)
- **Oikarinen, E. & Janhunen, T. (2008). "Achieving compositionality of the stable model semantics for smodels programs." TPLP 8(5–6) [V for title and venue; volume NV].** A module theorem that extends Lifschitz and Turner's splitting and allows negative recursion between modules. Modular equivalence is a congruence. It builds on ECAI 2006 ("Modular equivalence for normal logic programs") and LPNMR 2007. — [arXiv 0809.4582](https://arxiv.org/pdf/0809.4582.pdf); [Cambridge](https://www.cambridge.org/core/journals/theory-and-practice-of-logic-programming/article/achieving-compositionality-of-the-stable-model-semantics-forsmodels-programs1/812468C015AFB09A9233ADCA33C34B6B)
- **Janhunen, T., Oikarinen, E., Tompits, H. & Woltran, S. (2009). "Modularity aspects of disjunctive stable models." JAIR [V].** DLP-functions with input/output interfaces. Modules are built from SCCs of positive dependencies, and positively interdependent atoms must be in the same module. — [JAIR](https://jair.org/index.php/jair/article/view/10622)
  - Comparison: these define *which* modular decompositions are semantically sound, based on SCCs and interfaces. They do not search for the *functionally meaningful* decomposition. A useful constraint the method could adopt is never splitting a positive SCC across non-overlapping modules.
- Lifschitz, V. & Turner, H. (1994), "Splitting a logic program," ICLP 1994, MIT Press, pp. 23–37 [NV; referenced as the base by Oikarinen and Janhunen above].
- **Szilágyi, G., Gyimóthy, T. & Małuszyński, J. (2002). "Static and dynamic slicing of constraint logic programs." Automated Software Engineering 9(1):41–65, doi:10.1023/A:1013280119003 [V].** Notes that data flow in CLP is implicit, so imperative slicing does not transfer directly. — [dblp](https://dblp.uni-trier.de/rec/journals/ase/SzilagyiGM02.html); [arXiv cs/0012014](https://arxiv.org/abs/cs/0012014)
- Vasconcelos, W. W. (1999), "A flexible framework for dynamic and static slicing of logic programs," PADL 1999, LNCS 1551 [NV].
  - Comparison: slicing extracts the clauses relevant to a criterion such as one predicate. Seeding slices from each legal/next head would give a supervised, overlapping decomposition, which is a natural baseline for the method's overlapping clusters.

### Inferences
- In logic programming, decomposition research is about soundness (splitting, modules) and relevance (slicing). The "functional module discovery" goal of the method is closer to the rule-base partitioning literature of 1989–1997 than to modern ASP or Datalog work.
- No work was found that applies modern community detection to a Prolog, ASP or Datalog clause graph. This absence is meaningful but not proof, since search coverage was limited.

### Gaps
- Could not retrieve authors for the DKE 1992 and INFORMS JOC knowledge-base partitioning papers.
- No Datalog-specific clustering work was found.

## Ontology and knowledge-base modularisation

### Takeaway
Ontology modularisation splits into logic-based extraction, where locality guarantees a conservative extension, and structure-based partitioning, which is graph clustering of the concept hierarchy. The second is a close methodological sibling: graph-based partitioning of a declarative KB into topic modules, validated by inspection.

### Cited Findings
- **Cuenca Grau, B., Horrocks, I., Kazakov, Y. & Sattler, U. (2008). "Modular reuse of ontologies: theory and practice." JAIR 31:273–318, doi:10.1613/jair.2375 [V].** Locality-based modules give logically sound, signature-driven extraction. — [JAIR](https://jair.org/index.php/jair/article/view/10534); [Oxford](https://www.cs.ox.ac.uk/publications/publication898-abstract.html)
- **Stuckenschmidt, H. & Klein, M. (2004). "Structure-based partitioning of large concept hierarchies." ISWC 2004, LNCS 3298:289–303, doi:10.1007/978-3-540-30475-3_21 [V].** Automatic partitioning based only on the structure of the class hierarchy, which performed "surprisingly well" on real ontologies. — [VU research portal](https://research.vu.nl/en/publications/structure-based-partitioning-of-large-concept-hierarchies/); [Springer](https://link.springer.com/doi/10.1007/978-3-540-30475-3_21)
- Stuckenschmidt, H. & Schlicht, A. (2009), "Structure-based partitioning of large ontologies," in *Modular Ontologies*, LNCS 5445 [V for existence]. — [Springer chapter](https://link.springer.com/chapter/10.1007/978-3-642-01907-4_9); [Mannheim](https://madoc.bib.uni-mannheim.de/26491/). Schlicht & Stuckenschmidt (2006), "Towards structural criteria for ontology modularization," WoMO 2006 [NV].

### Inferences
- The method sits on the structure-based side, with no logical guarantee. Pairing it with a semantic check, as locality does for ontologies or splitting sets do for ASP, would be a differentiator.

### Gaps
- No business-rule or policy-rule grouping literature was searched within the tool budget.

## Planning domains and game description languages

### Takeaway
GDL decomposition work exists but targets *independent subgames* for search speedup, judged by exactness of separation. It does not target functional modules of one game's rules. No work was found that clusters GDL or PDDL clauses into functional modules with community detection.

### Cited Findings
- Günther, M., Schiffel, S. & Thielscher, M. (2009), "Factoring general games," IJCAI-09 Workshop on General Game Playing (GIGA'09) [V via citing reference list]. — [Springer citing chapter](https://link.springer.com/chapter/10.1007%252F978-3-319-57969-6_12)
- Cox, E., Schkufza, E., Madsen, R. & Genesereth, M. (2009), "Factoring general games using propositional automata," GIGA'09 [V via citing reference list; same source].
- **Hufschmitt, A., Vittaut, J.-N. & Méhat, J. (2016). "A general approach of game description decomposition for general game playing." CGW/GIGA 2016 at IJCAI, Springer CCIS, doi:10.1007/978-3-319-57969-6_12 [V].** Identifies perfectly separable subgames, serial games and compound moves, avoids reliance on syntactic features that rewriting can remove, and decomposed 32 of 40 games in under 5 s. A 2018 follow-up notes that earlier approaches relied on syntax or on costly DNF computation. — [author page](https://jnv.up8.site/publication/hufschmitt-2016/); [core.ac.uk](https://core.ac.uk/download/226919612.pdf)
- Zhao, Schiffel & Thielscher (2009), "Decomposition of multi-player games," AI 2009 (Australasian), LNAI 5866 [NV].
- Planning [NV]: Knoblock, C. A. (1994), "Automatically generating abstractions for planning," Artificial Intelligence 68(2). Groups literals into abstraction levels using dependencies between operators. Helmert, M. (2006), "The Fast Downward planning system," JAIR 26. Its causal graph over state variables comes from operator pre/effect relations, which is analogous to the temporal write-to-read edges.

### Inferences
- Subgame factoring asks "can the game be split without loss?" and has a binary, exact criterion. The method asks "which rules implement which mechanic?", allows overlap and is approximate. They are complementary, and the distinction should be stated clearly in any novelty claim.
- The causal graph (precondition to effect) is the closest planning analogue to the temporal write-to-read and legal-next edges, but it is used for heuristics or abstraction, not functional clustering.

### Gaps
- No PDDL action-schema clustering paper was found or searched in depth.
- The full text of Hufschmitt et al. was not read, so the graph construction details are not reported.
