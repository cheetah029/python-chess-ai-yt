# Candidates, including the ones that lost

Every weight set produced during the agent-strength work, shipped or
not. Kept because a failed candidate is evidence: it says what was
tried and what it cost, and more than one idea here was rejected only
after a race that a weight table had made look good.

These are NOT shipped. The shipped history is one directory up.

A candidate that does not load either predates the `extractor` field or
was written by a trainer that did not record one -- see
`record.audit`, which now refuses such a payload.

| file | weights | extractor | ablated | loads |
|---|---|---|---|---|
| `att_10.json` | 13 | legacy | RoyalForm:,PromotedQueenForm: | yes |
| `att_30.json` | 13 | legacy | RoyalForm:,PromotedQueenForm: | yes |
| `att_60.json` | 13 | legacy | RoyalForm:,PromotedQueenForm: | yes |
| `blend_all8.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `blend_leaf3.json` | 23 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `cand_formablated.json` | 13 | legacy | RoyalForm:,PromotedQueenForm: | yes |
| `fix_401.json` | 67 | with_threshold(royal_chess) | - | yes |
| `fix_401_zeroed.json` | 67 | with_threshold(royal_chess) | - | yes |
| `fix_402.json` | 67 | with_threshold(royal_chess) | - | yes |
| `fix_seed11.json` | 17 | (not recorded) | - | no |
| `fix_seed22.json` | 17 | (not recorded) | - | no |
| `hang2_811.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang2_812.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang2_813.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang_801.json` | 26 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang_802.json` | 24 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang_803.json` | 24 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hang_best.json` | 24 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hb_811812.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hb_811813.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hb_812813.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `hb_all.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `kq_seed52.json` | 17 | (not recorded) | - | no |
| `lean_501.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_502.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_503.json` | 23 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_504.json` | 23 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_505.json` | 23 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_avg.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `lean_avg5.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `legacyA.json` | 19 | legacy | - | yes |
| `legacyB.json` | 18 | legacy | - | yes |
| `legacy_avg3.json` | 19 | legacy | - | yes |
| `legacy_best.json` | 19 | legacy | - | yes |
| `nocov2.json` | 12 | legacy | RoyalForm:,PromotedQueenForm:,Covers | yes |
| `noforms.json` | 13 | legacy | RoyalForm:,PromotedQueenForm: | yes |
| `pin_971.json` | 20 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag:,RoyalForm:,PromotedQueenForm:,Pinned: | yes |
| `pin_972.json` | 20 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag:,RoyalForm:,PromotedQueenForm:,Pinned: | yes |
| `pin_973.json` | 20 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag:,RoyalForm:,PromotedQueenForm:,Pinned: | yes |
| `pin_blend.json` | 20 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag:,RoyalForm:,PromotedQueenForm:,Pinned: | yes |
| `sup_950.json` | 65 | with_threshold(royal_chess) | - | yes |
| `superseded_5seed.json` | 25 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `td_seed11.json` | 16 | (not recorded) | - | no |
| `td_seed22.json` | 17 | (not recorded) | - | no |
| `tdleaf_711.json` | 63 | with_threshold(royal_chess) | - | yes |
| `tdleaf_712.json` | 23 | with_threshold(royal_chess) | - | yes |
| `tdleaf_713.json` | 20 | with_threshold(royal_chess) | - | yes |
| `tdleaf_714.json` | 23 | with_threshold(royal_chess) | - | yes |
| `tdq_921.json` | 27 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `tdq_922.json` | 27 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `tdq_923.json` | 27 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `tdq_probe.json` | 21 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `tdq_probe2.json` | 18 | with_threshold(royal_chess) | Attacked:,Hanging:,Threatens:,Flag: | yes |
| `tdroot_new_201.json` | 82 | (not recorded) | - | no |
| `tdroot_new_202.json` | 82 | (not recorded) | - | no |
| `weights_backup.json` | 18 | (not recorded) | - | no |
| `weights_prev_tdroot.json` | 18 | (not recorded) | - | no |
| `z_matonly.json` | 19 | legacy | - | yes |
| `z_nobishop.json` | 19 | legacy | - | yes |
| `z_nocov.json` | 19 | legacy | - | yes |
| `z_noforms.json` | 19 | legacy | - | yes |
| `z_noformsatall.json` | 19 | legacy | - | yes |
| `z_nomob.json` | 19 | legacy | - | yes |
| `z_noroyalform.json` | 19 | legacy | - | yes |
