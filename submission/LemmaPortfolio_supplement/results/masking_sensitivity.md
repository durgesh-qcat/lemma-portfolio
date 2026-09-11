# Masking-exclusion sensitivity: all thirteen direct-response sets

Post-hoc exclusion sensitivity on saved responses; not corrected prompts, new inference, or evidence of no training exposure.

The preserved name-prefix scan identifies six test episodes. Exclusion is
based on prompt content, not the outcomes of any model. Missing or malformed
answers still receive zero and remain in the retained denominator of 54.

Excluded IDs: `MLP4B_0012`, `MLP4B_0033`, `MLP4B_0037`, `MLP4B_0042`, `MLP4B_0046`, `MLP4B_0059`.

| Model / baseline | Exact /54 | Coverage /8 | Valid /54 |
|---|---:|---:|---:|
| Oracle (hidden annotations) | 54 | 6.26 | 54 |
| Uniform random (expectation) | 0.12 | 2.34 | 54 |
| Character TF-IDF | 0 | 3.70 | 54 |
| GPT SOL 5.6 Pro | 22 | 5.07 | 50 |
| GPT SOL 5.6 xhigh | 15 | 5.13 | 54 |
| DeepSeek Instant + DeepThink | 1 | 4.26 | 54 |
| DeepSeek Expert + DeepThink | 7 | 4.67 | 54 |
| Qwen 3.8 Max-Thinking | 10 | 4.41 | 50 |
| Qwen 3.7 Plus-Thinking | 3 | 3.98 | 54 |
| GPT-6 Astra / xhigh / 1 | 23 | 5.44 | 54 |
| GPT-6 Astra / xhigh / 2 | 27 | 5.54 | 54 |
| GPT-5.6 Sol / xhigh / 1 | 17 | 5.06 | 54 |
| GPT-5.6 Sol / xhigh / 2 | 13 | 5.07 | 54 |
| GPT-6 Astra / max / 1 | 27 | 5.59 | 54 |
| Claude Fable 5 / xhigh | 22 | 5.52 | 54 |
| Claude Fable 5.1 / xhigh / context | 23 | 5.61 | 54 |

The original six model rows reproduce the previously archived sensitivity
check. The seven follow-up rows extend that same exclusion to saved answers.
The main 60-episode results are unchanged. No causal masking effect is
estimated: this subset also differs in episode composition.

Reproduce with `python3 -B verify_masking_sensitivity.py`.
