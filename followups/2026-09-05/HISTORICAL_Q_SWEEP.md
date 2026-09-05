# Historical support-prefix sensitivity

Exploratory post-hoc analysis; no new inference. Original q=2 scores and edge counts reproduce exactly.

| Historical row | q | Exact /20 | Coverage /160 | Edge F1 | Mean tied optima | True optimum among ties /20 |
|---|---:|---:|---:|---:|---:|---:|
| gpt_sol_5_6_pro | 1 | 1 | 86 | 59.3% | 7.2 | 8 |
| gpt_sol_5_6_pro | 2 | 1 | 92 | 72.6% | 5.3 | 9 |
| gpt_sol_5_6_pro | 3 | 1 | 91 | 74.2% | 5.0 | 10 |
| gpt_sol_5_6_pro | 4 | 0 | 86 | 74.0% | 5.9 | 11 |
| gpt_sol_5_6_xhigh | 1 | 0 | 78 | 56.6% | 8.3 | 8 |
| gpt_sol_5_6_xhigh | 2 | 0 | 78 | 69.1% | 9.7 | 9 |
| gpt_sol_5_6_xhigh | 3 | 0 | 81 | 71.9% | 9.8 | 9 |
| gpt_sol_5_6_xhigh | 4 | 0 | 80 | 72.7% | 10.1 | 11 |

The tie diagnostics use labels only to measure ambiguity after selection. They are not an alternative deployable optimizer. The actual pipeline always uses the original lexicographic tie break.
