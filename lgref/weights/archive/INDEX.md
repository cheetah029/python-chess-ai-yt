# Every shipped weight set, kept

Recovered from git history, so this is COMPLETE rather than whatever
happened to be lying around. To put one back:

```bash
cp lgref/weights/archive/<file> lgref/weights/td_royal_chess.json
```

**Five of these cannot be loaded today, and the reason is worth
knowing.** They predate the `extractor` field, and the feature
extractor they were fitted on was never frozen -- `legacy.py` is one
snapshot (at `d60adbb`) and it is not the one they used. Identified
rather than guessed: each known extractor was built, run on real
positions, and its feature names compared with the payload's weight
names. The best overlap was 0.30 to 0.67, so none of them is it.

That cannot happen again: `record.audit` refuses a payload with no
extractor named, and the loader calls it on every load.

The extractor SOURCE for any version is still recoverable, because git
already keeps code:

```bash
git show <commit>:lgref/experiments/features.py
```

| file | commit | date | features | extractor | ablated | loadable | what changed |
|---|---|---|---|---|---|---|---|
| `2026-10-14_76634da6.json` | 76634da6 | 2026-10-14 | 18 | (never recorded) | - | **no** | Two defects behind the TD agent's bad trades, and a valuation that is not yet stable (#276) |
| `2026-10-14_7a55bc24.json` | 7a55bc24 | 2026-10-14 | 19 | (never recorded) | - | **no** | TD bootstrapping: learn the gradients instead of assuming them (#276) |
| `2026-10-16_b4854305.json` | b4854305 | 2026-10-16 | 17 | (never recorded) | - | **no** | Make/unmake, depth 4, and a sign bug that made depth 3 worse than useless (#277) |
| `2026-10-17_2efb26fb.json` | 2efb26fb | 2026-10-17 | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | **yes** | Ship the five-seed average: it won its race (#278) |
| `2026-10-17_35e7b13b.json` | 35e7b13b | 2026-10-17 | 82 | with_threshold(royal_chess) | - | **yes** | Ship gated weights, and report the regression they caused (#278) |
| `2026-10-17_8dccbf03.json` | 8dccbf03 | 2026-10-17 | 18 | (never recorded) | - | **no** | The king does not outrank the queen: the ordering was never replicated (#277) |
| `2026-10-17_8e5bf4ee.json` | 8e5bf4ee | 2026-10-17 | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | **yes** | Shipped: better than it was, replicated across two seeds (#278) |
| `2026-10-17_8f924b26.json` | 8f924b26 | 2026-10-17 | 84 | (never recorded) | - | **no** | Two defects in my own new features, found by my own dependence check (#278) |
| `2026-10-17_cae36048.json` | cae36048 | 2026-10-17 | 67 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | **yes** | The features I added to fix the misses were causing them (#278) |
| `2026-10-18_09cb8872.json` | 09cb8872 | 2026-10-18 | 19 | legacy | - | **yes** | Fix the bishop without losing the knight (#278) |
| `2026-10-18_c112d16a.json` | c112d16a | 2026-10-18 | 18 | legacy | - | **yes** | Restore the agent the reviewer measured as competent (#278) |
| `2026-10-19_ccdb27cb.json` | ccdb27cb | 2026-10-19 | 13 | legacy | RoyalForm:,PromotedQueenForm: | **yes** | Ship the form-ablation: 18-5 against the previous blend (#278) |
