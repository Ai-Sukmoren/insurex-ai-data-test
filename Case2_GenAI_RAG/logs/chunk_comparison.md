# Chunk size comparison

Run on 2026-10-05 against the 5 InsureX category PDFs in `knowledge_base/` (qwen3:14b + bge-m3, top 4, chunks labelled
"document title › section").

## Stage 1: retrieval only (no LLM)

For the 85 answerable questions: does one of the top-k chunks come from the right PDF **and** contain the expected answer?

| Chunk / overlap | Chunks | Avg chars | Answer in top 1 | Answer in top 4 | …and above the 0.45 floor |
|---|---|---|---|---|---|
| 300/50 | 536 | 292 | 70/85 | 81/85 | 81/85 |
| 400/60 | 373 | 388 | 63/85 | 83/85 | 83/85 |
| 400/80 | 377 | 391 | 58/85 | 81/85 | 81/85 |
| 500/80 | 304 | 468 | 62/85 | 83/85 | 83/85 |
| 500/100 | 304 | 476 | 64/85 | 85/85 | 85/85 |
| 600/100 | 253 | 553 | 63/85 | 84/85 | 84/85 |
| 700/120 | 220 | 634 | 64/85 | 81/85 | 81/85 |
| 700/0 | 208 | 624 | 64/85 | 83/85 | 83/85 |
| 800/120 | 190 | 712 | 61/85 | 84/85 | 84/85 |
| 900/150 | 170 | 803 | 66/85 | 84/85 | 84/85 |
| 1000/150 | 152 | 875 | 64/85 | 85/85 | 85/85 |
| 1200/200 | 138 | 990 | 67/85 | 84/85 | 84/85 |
| page/0 | 61 | 1932 | 64/85 | 82/85 | 82/85 |

Every setting finds the answer for 81–85 questions, so retrieval alone can't pick a winner. ("page" uses the
document title only.) Four candidates went to the full test.

## Stage 2: full 100-question test (85 answerable + 15 out of scope)

| Chunk / overlap | Chunks | Overall | Answers right | Out-of-scope refused | Run time |
|---|---|---|---|---|---|
| 500/100 | 304 | 85/100 | 71/85 | 14/15 | 7.2 min |
| 700/120 | 220 | 82/100 | 69/85 | 13/15 | 9.9 min |
| **1000/150 (chosen)** | 152 | 91/100 | 77/85 | 14/15 | 12.3 min |
| 1200/200 | 138 | 89/100 | 76/85 | 13/15 | 11.2 min |

**Why 1000 / 150:** 1000/150 scored best (91/100, 77/85 answers, 14/15 refusals). Smaller chunks scored lower (85 and 82) and 1200/200 scored 89 with one fewer correct refusal. The likely reason is that at about 1000 characters a benefit-table block stays in one chunk with its plan-name headings; this is an explanation, not something the test measured. Overlap stays at 15% so a fact on a chunk boundary is whole in at least one chunk.

The comparison used the question set before two ambiguous wordings were fixed (questions 15 and 16); the final eval
in `eval_report.md` uses the fixed set.
