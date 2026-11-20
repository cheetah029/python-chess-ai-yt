# Benchmarks with ground-truth rule/module boundaries, and evaluation metrics/baselines for overlapping clustering against a hand-labelled reference

Verification legend used below:
- **[V]** = bibliographic details (authors, year, title, venue) confirmed in this session against a primary or catalogue source (journal page, arXiv, dblp, PMC, publisher, institutional repository). Linked.
- **[U]** = NOT verified in this session (comes from prior knowledge only). The report writer should either verify or drop these. They are listed in Gaps, not cited as findings.

---

## (A1) Do datasets exist that label rule units / ludemes / modules inside formal game descriptions (GDL repositories, Ludii, VGDL, PDDL)? Can Ludii ludeme trees serve as ground truth for GDL?

### Takeaway
No dataset was found that labels "rule units" inside GDL descriptions; GGP repositories (ggp-base / Tiltyard) ship flat clause files with no rule-boundary annotation. Ludii is the closest thing to structured ground truth (games are trees of named ludemes, plus a formal "concepts" catalogue), but no published GDL-to-Ludii (or Ludii-to-GDL) clause-aligned translation corpus was found, so Ludii ludeme trees cannot be used as off-the-shelf ground truth for GDL clause grouping; hand-labelling (as planned) remains necessary and is defensible.

### Cited Findings
- [V] Piette, Soemers, Stephenson, Sironi, Winands, Browne, "Ludii – The Ludemic General Game System," ECAI 2020 (arXiv 1905.05013). Ludii defines games as structures of *ludemes*, "high-level, easily understandable game concepts", contrasted with GDL whose clauses are criticised as verbose and not encapsulating the concepts designers use. — [arXiv 1905.05013](https://arxiv.org/pdf/1905.05013); [UCLouvain record](https://research.dial.uclouvain.be/handle/2078.5/253707)
- The same paper compares Ludii against a GGP-Base propositional-network GDL reasoner "in all games available in the Tiltyard GGP repository" and reports Tic-Tac-Toe at 24 tokens in Ludii vs 381 in GDL (101 in RBG). This shows the Tiltyard games were re-implemented in Ludii for benchmarking, but the comparison is of speed and description size, not of clause-to-ludeme alignment. — [arXiv 1905.05013](https://arxiv.org/pdf/1905.05013)
- An independent re-evaluation of the Ludii vs GDL/RBG efficiency claims noted that the GDL numbers were obtained on different hardware, and that a GGP-Prover rather than a propnet was used for chess. — [ar5iv 1907.00244](https://ar5iv.labs.arxiv.org/html/1907.00244) (title/authors of 1907.00244 not fully confirmed here; believed to be Kowalski & Szykuła's empirical evaluation of Ludii and RBG — see Gaps)
- [V] Soemers, Piette, Stephenson, Browne, "The Ludii Game Description Language is Universal," IEEE Conference on Games (CoG) 2024, DOI 10.1109/CoG60054.2024.10645550 (arXiv 2205.00451). It proves that Ludii can represent any finite extensive-form game, including non-deterministic and imperfect-information games, building on Thielscher's earlier GDL result. This is an expressiveness result, not a translation corpus. — [arXiv 2205.00451v3](https://arxiv.org/abs/2205.00451v3); [Flinders record](https://researchnow.flinders.edu.au/en/publications/the-ludii-game-description-language-is-universal/)
- [V, arXiv only] Piette, Stephenson, Soemers, Browne, "General Board Game Concepts," arXiv 2107.01078 (July 2021). It formalises "game concepts" inspired by player and designer vocabulary, at several levels of abstraction (the game, the moves, the states reached). It is the basis of Ludii's concepts database. These concepts label *whole games* (which concepts a game exhibits); they do not segment a description into rule units. — [arXiv 2107.01078 summary](https://fugumt.com/fugumt/paper_check/2107.01078v1_enmode)
- A Ludii-related thesis on translating Ludii rule sets into plain English (substitution vs contextual approaches) was found. It is Ludii to English, not GDL to Ludii. — [Ludii citations, Thesis2021-6](https://ludii.games/citations/Thesis2021-6.pdf)
- Searches for a GDL-to-Ludii or Ludii-to-GDL translator, or a list of ggp-base games translated clause by clause into Ludii, returned nothing. — (negative result; searches recorded in this note)

### Inferences
- Ludii ludeme subtrees (for example `(play ...)`, `(end ...)`, `(equipment ...)`) are a plausible *external, author-independent* source of rule boundaries for games that exist in both Ludii and GDL (tic-tac-toe certainly does). A paper could map each GDL clause to the Ludii ludeme(s) it implements and treat that mapping as a second, independent reference labelling. That would partly answer the reviewer objection "the authors labelled their own ground truth". Doing this would itself be a contribution, because no such alignment corpus appears to exist.
- Ludii's concepts are game-level binary features, so at most they give weak supervision (for example, a game flagged with a concept should contain a rule that realises it). They do not give clause-level boundaries.
- The lack of an existing benchmark is both a novelty argument and a weakness. Reviewers will want the labelling protocol written down: who labelled, the labelling guide, and inter-annotator agreement (see A2 for the software-engineering precedent).

### Gaps
- VGDL/GVGAI and PDDL: no targeted search was run within the call budget. I am not aware of any VGDL or PDDL corpus annotated with rule or module boundaries, but this was **not verified**. Note that VGDL is already syntactically segmented (SpriteSet, InteractionSet, TerminationSet), so its "rules" are given by the syntax rather than labelled.
- [U] "Ludii as a Competition Platform" (believed to be Stephenson, Piette, Soemers, Browne, IEEE CoG 2019) was not verified. A Maastricht-hosted `cog19_5.pdf` appeared in results ([link](https://cris.maastrichtuniversity.nl/ws/files/37362640/cog19_5.pdf)) but was not opened.
- arXiv 1907.00244: the authors and title were not confirmed from the page itself.
- The venue of "General Board Game Concepts" (believed to be IEEE CoG 2021) was not confirmed.
- I did not check whether the ggp.org base repository or the Dresden GGP server has any clause comments or sectioning that could act as weak labels.

---

## (A2) Software clustering benchmarks with ground-truth architectures, as an analogy for building and validating ground truth

### Takeaway
Software architecture recovery is the closest methodological analogue. There, ground truth is built manually, is expensive, and is validated by the system's own developers. Benchmarks are tiny (4 to 8 systems), and even the best techniques score low, so a small hand-labelled reference set is an accepted practice when the labelling protocol is rigorous and documented.

### Cited Findings
- [V] Garcia, Ivkovic, Medvidovic, "A Comparative Analysis of Software Architecture Recovery Techniques," IEEE/ACM ASE 2013, pp. 486–496, DOI 10.1109/ASE.2013.6693106. The paper notes that rigorous assessment had been hampered by the lack of architectural "ground truths". It compares six recovery techniques against eight architectures recovered from open-source systems and independently verified. Two techniques routinely outperform the others, but even the best has surprisingly low accuracy. — [researchr](https://researchr.org/publication/GarciaIM13)
- [V] Garcia, Krka, Mattmann, Medvidović, "Obtaining Ground-Truth Software Architectures," ICSE 2013 (SEIP). It describes the procedure for recovering the ground-truth architectures of four open-source systems. — [ICSE 2013 page](https://2013.icse-conferences.org/content/obtaining-ground-truth-software-architectures.html)
- [V] Lutellier, Chollak, Garcia, Tan, Rayside, Medvidović, Kroeger, "Comparing Software Architecture Recovery Techniques Using Accurate Dependencies," ICSE 2015 (vol. 2, SEIP), pp. 69–78. It compares nine variants of six techniques on five projects. More accurate (symbol-level) dependencies improve accuracy, yet overall accuracy stays low. Conclusion: input-dependency accuracy is itself a factor. — [PDF](https://www.cs.purdue.edu/homes/lintan/publications/archrec-icse15.pdf); [bibtex](https://bibtex.github.io/ICSE-v2-2015-LutellierCGTRMK.html)
- The journal extension, "Measuring the Impact of Code Dependencies on Software Architecture Recovery Techniques" (IEEE TSE vol. 44 no. 2, pp. 159–181), adds granularity, virtual-call resolution and global-variable factors. Sources disagree on the year (2018 in the library record, 2017 in the thesis). — [library record](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_ieee_primary_7859416)

### Inferences
- Direct analogy: GDL clause dependencies (shared predicates, shared variables, body/head references) play the role of code dependencies. Lutellier et al.'s finding implies that **the choice of edge definition** (name tokens vs semantic or dataflow dependency) should be reported as a factor and ablated. This fits the planned comparison against a name-token-similarity baseline.
- Garcia et al. 2013 validated ground truth with system experts. The GDL analogue is a labelling guide plus a second labeller, or an external source such as a Ludii ludeme alignment.
- These papers report architecture-level metrics, chiefly MoJoFM and a2a (from memory, [U]), not ARI. A paper aimed at both communities might report one software-clustering metric for continuity. This is optional.

### Gaps
- The exact metrics used by Garcia 2013 and Lutellier 2015 (MoJoFM, c2c_cvg) were not confirmed from full text.

---

## (B1) Is ARI defined/standard for overlapping clusterings? What overlapping extensions exist, and which do reviewers expect?

### Takeaway
Standard ARI (Hubert & Arabie) is defined only for hard partitions. "ARI by pair counting over overlapping or soft membership" is not a standard named measure, and reviewers will ask which generalisation it is. The established pair-counting generalisations are the **Omega index** (Collins & Dent 1988), for overlapping covers, and the **fuzzy Rand/ARI family** (Hüllermeier et al. 2012), for soft memberships. In overlapping community detection, the de facto expected trio is **overlapping NMI (preferably the McDaid–Greene–Hurley "max" variant), Omega index, and best-match F1** (Xie et al. 2013 used NMI, Omega and F-score). BCubed (extended) and element-centric similarity are the theoretically best-motivated additions.

### Cited Findings
- [V, catalogue only] Collins, L. M. & Dent, C. W. (1988). "Omega: A general formulation of the Rand index of cluster recovery suitable for non-disjoint solutions." *Multivariate Behavioral Research* 23(2): 231–242. The only confirmation came from a third-party reference listing; the DOI page was not opened. — [reference listing](https://data.zhenzhi.com/details/1/1008654963)
- [V] Hüllermeier, Rifqi, Henzgen, Senge (2012). "Comparing Fuzzy Partitions: A Generalization of the Rand Index and Related Measures." *IEEE Transactions on Fuzzy Systems* 20(3): 546–556, DOI 10.1109/TFUZZ.2011.2179303. The class of measures includes the Rand index and the Jaccard measure. It compares two fuzzy partitions directly; Campello's earlier extension only compared a fuzzy partition with a crisp reference. The authors claim desirable metric properties over earlier fuzzy extensions. — [dblp](https://dblp.uni-trier.de/rec/journals/tfs/HullermeierRHS12.html); [HAL preprint](https://hal.archives-ouvertes.fr/hal-00734389/file/tfuzz-hullermeier-2179303-proof.pdf)
- [V] Lancichinetti, Fortunato, Kertész (2009). "Detecting the overlapping and hierarchical community structure in complex networks." *New Journal of Physics* 11: 033015 (arXiv 0802.1218). This is the LFK algorithm, and it is also the source of the original overlapping NMI ("LFK NMI"). — [CEU record](https://research.ceu.edu/en/publications/detecting-the-overlapping-and-hierarchical-community-structure-in/)
- [V, arXiv] McDaid, Greene, Hurley (2011). "Normalized Mutual Information to evaluate overlapping community finding algorithms," arXiv:1110.2515. It shows that the LFK normalisation can over-score unrelated covers (for example ≥0.5 where ~0 is expected) and proposes normalising by max(H(X), H(Y)). It is implemented in cdlib as `overlapping_normalized_mutual_information_MGH` (default "max"; "LFK" also available). — [ar5iv 1110.2515](https://ar5iv.arxiv.org/html/1110.2515); [cdlib docs](https://cdlib.readthedocs.io/en/v0.2.5/reference/eval/cdlib.evaluation.overlapping_normalized_mutual_information_MGH.html)
- [V] Amigó, Gonzalo, Artiles, Verdejo (2009). "A comparison of extrinsic clustering evaluation metrics based on formal constraints." *Information Retrieval* 12(4): 461–486. Of the metrics studied, only BCubed satisfies all of the proposed formal constraints (homogeneity, completeness, rag bag, cluster size vs quantity), validated against human assessments. It also proposes an **extended BCubed for overlapping clustering**. An erratum (July 2009) corrects some precision values in figures. — [Springer PDF](https://link.springer.com/content/pdf/10.1007/s10791-009-9106-z.pdf); [UNED record](https://portalcientifico.uned.es/documentos/5fa07b08299952440aae188b?lang=en)
- [V] Gates, Wood, Hetrick, Ahn (2019). "Element-centric clustering comparison unifies overlaps and hierarchy." *Scientific Reports* (arXiv 1706.06136). The authors argue that existing comparison measures have critical biases and that no prior measure handles both overlapping and hierarchical clusterings. Their framework compares elements via the cluster-induced relationships, with a scaling parameter r that weights levels of a hierarchy. — [PMC6561975](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6561975/); [arXiv](https://arxiv.org/pdf/1706.06136)
- [V] Yang & Leskovec (2013). "Overlapping community detection at scale: a nonnegative matrix factorization approach" (BigCLAM). WSDM 2013, pp. 587–596, DOI 10.1145/2433396.2433471. Evaluated on 6 networks with ground-truth communities. It is the standard citation for best-match (average) F1 between detected and ground-truth communities, but the F1 definition was **not** confirmed from full text in this session. — [dblp](https://dblp.org/rec/conf/wsdm/YangL13)
- [V] Xie, Kelley, Szymanski (2013). "Overlapping community detection in networks: The state-of-the-art and comparative study." *ACM Computing Surveys* 45(4), Article 43 (arXiv 1110.5813). It reviews algorithms, quality measures and benchmarks; compares 14 algorithms using **NMI, Omega index and F-score**; and adds an evaluation of overlapping-*node* detection (over- and under-detection). — [arXiv 1110.5813](https://www.arxiv.org/pdf/1110.5813); [bibbase](https://bibbase.org/network/publication/xie-kelley-szymanski-overlappingcommunitydetectioninnetworksthestateoftheartandcomparativestudy-2013)

### Inferences
- **Naming the metric:** the planned "pairwise precision/recall/F1 and ARI by pair counting over soft/overlapping membership" should be (a) defined explicitly with a formula, and (b) identified with its closest established relative. If pair agreement is "same number of shared clusters", it is essentially the Omega index. If pair co-membership is a real-valued product or min of memberships, it is in the Hüllermeier et al. fuzzy Rand/Jaccard family. Otherwise the paper should say it is a new variant and show that it reduces to ARI on hard partitions. Pairwise P/R/F1 by pair counting is the "pair-counting F-measure" that Amigó et al. analyse and show fails some constraints (for example rag bag and cluster size vs quantity). Reporting extended BCubed alongside it pre-empts that critique.
- **Suggested reporting set** for a community-detection reviewer: Omega index, overlapping NMI (MGH "max"), best-match F1 (Yang & Leskovec style), and extended BCubed P/R/F; optionally element-centric similarity, which handles overlap natively and avoids pair-counting biases. cdlib implements most of these (Omega, NMI-MGH, F1/NF1), which helps reproducibility.
- On tiny games (tens of clauses), report all metrics with their **chance baseline** (see B2) and the raw contingency, because single numbers are unstable at small n.

### Gaps
- [U] Hubert & Arabie (1985), "Comparing partitions," *Journal of Classification* 2: 193–218, is the standard ARI citation. It was not verified here.
- [U] Lancichinetti & Fortunato (2009), "Benchmarks for testing community detection algorithms on directed and weighted graphs with overlapping communities," *Phys. Rev. E* 80: 016118 (the overlapping LFR benchmark), was not verified.
- The exact formula of the Omega index was not confirmed from the original paper (the full text was not accessed).
- I found no source that surveys reviewer *expectations* directly. The "expected trio" is inferred from Xie et al. 2013's choice of metrics and cdlib's coverage.

---

## (B2) Known pitfalls of ARI/NMI

### Takeaway
Chance correction matters most exactly in this setting (few elements relative to the number of clusters). The choice of random model behind "adjusted" indices changes results. Unadjusted NMI is biased toward many small clusters, and the LFK overlapping NMI over-scores unrelated covers.

### Cited Findings
- [V] Vinh, Epps, Bailey (2010). "Information Theoretic Measures for Clusterings Comparison: Variants, Properties, Normalization and Correction for Chance." *JMLR* 11: 2837–2854. It stresses correcting information-theoretic measures for chance, "especially when the data size is small compared to the number of clusters". It recommends normalized information distance (a true metric, with an exact adjusted-for-chance form) and introduces AMI. A preliminary version appeared at ICML 2009 ("Is a correction for chance necessary?"). — [JMLR](https://www.jmlr.org/papers/v11/vinh10a.html)
- [V] Romano, Vinh, Bailey, Verspoor (2016). "Adjusting for Chance Clustering Comparison Measures," *JMLR* 17. It recommends ARI when the reference has large, equal-sized clusters, and AMI when the reference is unbalanced with small clusters. — [JMLR v17 15-627](https://www.jmlr.org/papers/v17/15-627.html)
- [V] Gates & Ahn (2017). "The Impact of Random Models on Clustering Similarity." *JMLR* 18(87): 1–28. The standard permutation model (fixed number and sizes of clusters) underlies ARI and AMI. They derive corrections under random models where cluster counts and sizes vary, and for one-sided comparison against a fixed reference. The choice of random model can significantly change rankings, so it "should be justified carefully". — [JMLR](https://www.jmlr.org/papers/v18/17-039.html)
- [V] McDaid et al. 2011: LFK overlapping NMI can give ≥0.5 for unrelated covers. — [ar5iv](https://ar5iv.arxiv.org/html/1110.2515)
- [V] Gates et al. 2019: existing comparison measures carry critical biases (motivating element-centric similarity). — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6561975/)

### Inferences
- For the paper: since the reference labelling is fixed, the **one-sided** random model of Gates & Ahn 2017 is arguably the correct chance baseline. Saying so explicitly is a cheap way to show rigor.
- A tiny-game reference with a few rules of unequal size (for example one large "board/legal" rule and several singleton rules) is the unbalanced case where Romano et al. favour AMI over ARI. Report both, or justify the choice.
- Report a permutation null empirically: shuffle cluster labels, or sample random covers with the same size and overlap distribution, to get an empirical expected score and p-value. This is easy at n ≈ tens of clauses.

### Gaps
- No source specifically on chance-corrected *overlapping* indices was examined. The Omega index includes a chance correction by design ([U], not confirmed from full text).

---

## (B3) Overlapping community detection algorithms that would be natural baselines (instead of Louvain + post-hoc overlap)

### Takeaway
Reviewers will expect at least one native-overlap method (link communities, OSLOM, clique percolation, BigCLAM, or LFK), and will flag Louvain for possibly disconnected communities (use Leiden) and for modularity's resolution limit. All of these run trivially on graphs of tens of clauses.

### Cited Findings
- [V] Ahn, Bagrow, Lehmann (2010). "Link communities reveal multiscale complexity in networks." *Nature* 466: 761–764. It partitions *links*, not nodes, so node overlap arises naturally and hierarchy comes from a link dendrogram. — [IDEAS/RePEc](https://ideas.repec.org/a/nat/nature/v466y2010i7307d10.1038_nature09182.html); [Nature PDF](https://www.nature.com/articles/nature09182.pdf)
  - Relevance: clause-to-clause edges (shared predicates) are natural "links". A link-community method gives overlapping clause membership without post-hoc heuristics.
- [V] Lancichinetti, Radicchi, Ramasco, Fortunato (2011). "Finding Statistically Significant Communities in Networks" (OSLOM). *PLoS ONE* 6(4): e18961. It handles weights, direction, overlap and hierarchy, and scores clusters by their statistical significance against a configuration-model null. It can also refine another method's partition. — [PMC3084717](https://pmc.ncbi.nlm.nih.gov/articles/PMC3084717); [arXiv 1012.2363](https://arxiv.org/pdf/1012.2363)
  - Relevance: its significance-based clusters directly answer "is this rule grouping more than chance?" on tiny graphs.
- [V] Lancichinetti, Fortunato, Kertész (2009), NJP 11: 033015. Local fitness optimisation gives overlapping and hierarchical communities, with a resolution parameter α. — [CEU record](https://research.ceu.edu/en/publications/detecting-the-overlapping-and-hierarchical-community-structure-in/)
- [V] Yang & Leskovec (2013), BigCLAM, WSDM. A model-based overlapping method that assumes community overlaps are densely connected. — [dblp](https://dblp.org/rec/conf/wsdm/YangL13)
- [V] Traag, Waltman, van Eck (2019). "From Louvain to Leiden: guaranteeing well-connected communities." *Scientific Reports* 9: 5233. In their experiments Louvain gives up to 25% badly connected and up to 16% disconnected communities. Leiden guarantees connected communities and, iterated, converges to a partition where all subsets are locally optimally assigned. — [arXiv 1810.08473](https://arxiv.org/pdf/1810.08473); [PMC6435756](https://pmc.ncbi.nlm.nih.gov/articles/PMC6435756)
- [V] Fortunato & Barthélemy (2007). "Resolution limit in community detection." *PNAS* 104(1): 36–41, DOI 10.1073/pnas.0605965104. Modularity optimisation can miss modules below a scale that depends on the total number of links (roughly when internal links ≲ √(2L)), even for unambiguous modules. — [arXiv physics/0607100](https://arxiv.org/pdf/physics/0607100); [PMC1765466](https://pmc.ncbi.nlm.nih.gov/articles/PMC1765466)
- [V] Xie et al. (2013) compared 14 overlapping algorithms. In networks with high overlap density and diversity, SLPA and GAME were relatively stable, and they judged detection in such networks to be not yet resolved. — [arXiv 1110.5813](https://www.arxiv.org/pdf/1110.5813)

### Inferences
- Minimum credible baseline set for the paper: (1) the name-token-similarity baseline (already planned); (2) Leiden (replacing Louvain, or at least alongside it, citing Traag 2019) plus the same post-hoc overlap step, which isolates the contribution of the overlap step; (3) one native-overlap method, with link communities (Ahn 2010) as the most natural fit for clause graphs; (4) OSLOM or clique percolation as a second native-overlap baseline; (5) trivial baselines: all-singletons, one-cluster, and random covers with matched size and overlap distribution.
- Resolution limit: on tiny graphs the resolution limit cuts the other way. Modularity at γ=1 may *merge* small rules (for example singleton "terminal" or "goal" clauses) when it should not. A resolution sweep (γ, or α in LFK) is expected, and the paper should report results across it, not at one tuned value.

### Gaps
- [U] Palla, Derényi, Farkas, Vicsek (2005). "Uncovering the overlapping community structure of complex networks in nature and society." *Nature* 435: 814–818 (clique percolation). Not verified in this session.
- [U] Rosvall & Bergstrom (2008). "Maps of random walks on complex networks reveal community structure." *PNAS* 105(4): 1118–1123 (Infomap). Not verified.
- [U] Blondel, Guillaume, Lambiotte, Lefebvre (2008). "Fast unfolding of communities in large networks." *J. Stat. Mech.* P10008 (Louvain). Not verified.
- [U] Fortunato (2010). "Community detection in graphs." *Physics Reports* 486: 75–174 (arXiv 0906.0612 appeared in results but was not opened). Fortunato & Hric (2016), "Community detection in networks: A user guide," *Physics Reports* 659: 1–44. Not verified.

---

## (B4) Sensitivity/robustness analysis expectations and statistical significance with tiny ground-truth sets

### Takeaway
No source was found that sets a field standard for robustness reporting on tiny reference sets. The literature found does support three concrete expectations: chance-corrected scores whose random model is stated, results across a resolution sweep rather than one tuned value, and significance testing against a null (OSLOM's configuration-model null, or permutation nulls).

### Cited Findings
- Correction for chance matters most when n is small relative to the number of clusters. — [Vinh et al. 2010, JMLR](https://www.jmlr.org/papers/v11/vinh10a.html)
- The choice of random model can change rankings and must be justified. One-sided (fixed-reference) models exist. — [Gates & Ahn 2017, JMLR](https://www.jmlr.org/papers/v18/17-039.html)
- Modularity's detectable module size depends on the size of the whole network, so results at a single resolution are not intrinsic. — [Fortunato & Barthélemy 2007, PNAS](https://pmc.ncbi.nlm.nih.gov/articles/PMC1765466)
- Louvain's output can include disconnected communities; Leiden fixes this. Louvain and Leiden are randomised (node order), which motivates multiple seeds. — [Traag et al. 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6435756)
- OSLOM frames community validity as statistical significance against a null model. — [Lancichinetti et al. 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3084717)
- Software architecture recovery papers evaluate on only 4 to 8 hand-verified systems, so tiny reference sets are an accepted practice in a neighbouring field. — [Garcia et al. 2013](https://researchr.org/publication/GarciaIM13); [Lutellier et al. 2015](https://www.cs.purdue.edu/homes/lintan/publications/archrec-icse15.pdf)

### Inferences
Recommended protocol (inferred, not sourced as a standard):
- **Seeds:** run ≥30 seeds per configuration and report the mean ± SD (or median and IQR) of every metric, plus the consensus clustering.
- **Weights/resolution:** sweep each edge-weight component and the resolution parameter. Report the score as a curve or heatmap, and the width of the parameter region where the method beats the baseline. Avoid tuning on the same tiny games used for testing; use leave-one-game-out if anything is tuned.
- **Significance:** with 3 games, between-game statistics are meaningless. Test within each game against (a) a permutation null of the method's own clusters (same sizes and overlaps, shuffled members), and (b) the name-token baseline, using a paired test over seeds and parameter settings, or bootstrap over clauses. Report effect sizes and exact p-values, and say plainly that the results show feasibility, not generalisation.
- **Reference reliability:** if possible, have a second person label the clauses independently and report agreement *using the same overlapping metric* (for example Omega between the two labellers). This gives a human ceiling for interpreting the method's scores.
- **Ablation of the redundant and interacting-rules game:** the purpose-built game can carry targeted, falsifiable predictions (for example, the method must place the two redundant clauses together and the token baseline must not). That kind of evaluation is more convincing at tiny n than an aggregate ARI.

### Gaps
- I found no published guideline specific to statistical testing of clustering against tiny hand-labelled references. The protocol above is an inference.
- I did not search for consensus-clustering citations (for example Lancichinetti & Fortunato 2012, "Consensus clustering in complex networks", *Sci. Rep.* [U]).
