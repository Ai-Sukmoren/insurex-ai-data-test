# Chunk size comparison

Run on 2026-10-05 against the 5 real PDFs in `knowledge_base/` (qwen3:14b + bge-m3, top 4, title-labelled chunks).

## Stage 1: retrieval only (no LLM)

For the 85 answerable questions: does one of the top-k chunks come from the right PDF **and** contain the expected answer?

| Chunk / overlap | Chunks | Avg chars | Answer in top 1 | Answer in top 4 | …and above the 0.45 floor |
|---|---|---|---|---|---|
| 300/50 | 144 | 275 | 57/85 | 76/85 | 75/85 |
| 400/60 | 105 | 367 | 62/85 | 76/85 | 75/85 |
| 400/80 | 111 | 363 | 62/85 | 77/85 | 77/85 |
| 500/80 | 86 | 446 | 65/85 | 77/85 | 76/85 |
| 500/100 | 91 | 450 | 62/85 | 78/85 | 77/85 |
| 600/100 | 76 | 520 | 68/85 | 80/85 | 79/85 |
| 700/120 | 66 | 597 | 64/85 | 80/85 | 79/85 |
| 700/0 | 61 | 579 | 63/85 | 79/85 | 79/85 |
| 800/120 | 57 | 672 | 64/85 | 78/85 | 78/85 |
| 900/150 | 54 | 722 | 68/85 | 78/85 | 77/85 |
| 1000/150 | 47 | 805 | 68/85 | 82/85 | 81/85 |
| 1200/200 | 41 | 933 | 65/85 | 83/85 | 81/85 |
| page/0 | 20 | 1706 | 72/85 | 85/85 | 83/85 |

Bigger chunks look better here, but this measure flatters them: with 20 page-sized chunks the top 4 covers a fifth of
all text, and short expected values ("3", "50") match by coincidence. So the candidates went to a full test.

## Stage 2: full 100-question test (85 answerable + 15 out of scope)

| Chunk / overlap | Chunks | Overall | Answers right | Out-of-scope refused | Run time |
|---|---|---|---|---|---|
| 700 / 120 (previous) | 66 | 91/100 | 76/85 | 15/15 | – |
| **1000 / 150 (chosen)** | 47 | 96/100 | 81/85 | 15/15 | 11.2 min |
| 1200 / 200 | 41 | 94/100 | 80/85 | 14/15 | 14.4 min |
| one chunk per page | 20 | 54/100 | 46/85 | 8/15 | 10.3 min |

**Why 1000 / 150:** the best overall and answer scores, and all off-topic questions still refused. Chunks hold a
whole table block or product section, so a premium stays with its column headers and conditions with their product.
Going larger stopped helping, and one chunk per page broke the refusal path: almost every page contains something
loosely related, so the grader kept passages, the model was distracted, and 7 off-topic questions got answers.
Overlap stays at 15% so a fact on a chunk boundary is whole in at least one chunk.
