# Evaluation records and inference settings

The saved answers, prompts, and scoring code suffice to reproduce the reported
scores without calling a model. Fresh inference is a different operation: it
requires access to the relevant service, may incur charges, and need not return
the historical answers. No new inference was performed while assembling this
submission.

`settings.json` indexes the six original response sets, seven additional
60-episode runs, and Astra's separate 20-episode direct/target-wise comparison.
All paths in its inventory and in each run's `prompt_calls` are relative to the
submission archive root. See the root README for offline verification commands.
The read-only `python3 evaluation/verify_evaluation.py` check also validates
the 13-set inventory, all 92 follow-up prompt/response associations against
`MANIFEST.json`, harness hashes, and the recorded Fable SDK/context settings.
It can be invoked by its absolute path from any working directory.

## What is included

- Original responses: `original_release/responses/direct_transcription.json`,
  the two source response PDFs and their extracted text. The original Pro and
  Sol target-wise responses are in `support_transcription.json` in that directory.
- Released inputs: twelve five-episode direct prompts and four target-wise
  prompts under `original_release/prompts/`, with a SHA-256 manifest.
- Additional responses: `followups/2026-09-05/<run>/responses/`. Each
  `evaluation/runs/<run>.json` records its prompt mapping, source metadata,
  call receipts, completion record, and the available capture-audit summary.
- Execution plan and changes: `protocol.json`; Fable's available small refusal
  checks: `fable_refusal_diagnostics.json`; actual Fable calling code: `harnesses/`.

The original six sets are saved web-chat responses, not six runs made by the
newer CLI/API harnesses. Their display labels are retained in `settings.json`.
Pro has five missing answers and Qwen 3.8 has five malformed answers in D12;
these receive zero, with all 60 episodes retained. All other direct rows have
60 valid answers. The frozen manual-chat protocol and its README distinguish
the original intended controls from what can be checked in the saved records.
In particular, the historical target-wise responses cover D04, D05, D06, and
D12, not the different optional subset named in that frozen protocol.

## Astra and Sol

The supplied records report Codex CLI 0.153.0, a fresh process and blank working
directory per prompt, bundled CLI instructions, and no tools or prior
conversation. The requested model and effort are listed for every run.
Temperature and a numeric reasoning budget were not exposed. Each call had a
2400-second timeout, with no automatic retry or repair of mathematical answers.
The saved audits report fresh sessions and zero tool events.

The exact follow-up runner source and command-line invocation files were not
included in the supplied export. Their reported hashes are retained, but this
archive does not substitute a different runner or claim to reproduce the full
historical runtime. The event-log hashes and audit summaries are execution
records, not independent authentication of hidden serving settings.

Astra's target-wise comparison uses eight separate calls: direct then support
for D04, support then direct for D05, direct then support for D06, and support
then direct for D12. The primary procedure keeps the first two predicted
candidates for each target, then maximizes predicted coverage over all 560
triples with candidate-ID lexicographic tie-breaking. Actual proof-use labels
are used only for scoring. These direct answers are not substituted into the
full 60-episode runs.

The first Astra xhigh run preceded the protocol freeze. The remaining CLI plan
was frozen at 01:46:26 UTC on 5 September 2026. At 07:49:33 UTC, after core
scores were known, the queue was shortened to finish the second Sol/Astra
xhigh runs and cancel the unstarted third pair. The original plan and later
amendment are both retained in `protocol.json`; all started scored runs remain
included. These are post-release evaluations: labels were known to the
experimenter but were not supplied to the evaluated models.

## Fable

Both completed Fable runs used the streaming Anthropic Messages API with
`anthropic==1.4.0`, `output_config.effort="xhigh"`, and `max_tokens=128000`.
The recorded Python version is 3.14.6. Each request contained one unchanged
released user prompt, with no tools or previous conversation. No temperature,
top-p, or separate thinking parameter was sent. Fable 5 had no system prompt;
Fable 5.1 used the exact additional benchmark-context text preserved at
`followups/2026-09-05/claude_fable_5_1_xhigh_ctx_r1/harness/system_context.txt`.

The three scripts below are byte-preserved source copies, renamed only to make
their historical roles clear. Full hashes and source paths are in `settings.json`.

| Script | Historical use |
| --- | --- |
| `fable5_initial_979e3864.py` | Fable 5 calls 01–09 and the first, failed call 10. |
| `fable5_resume_46aca1c4.py` | Fable 5 resumed calls 10–12, without a system prompt. |
| `fable51_context_76bdf78d.py` | All twelve Fable 5.1 calls with the context system prompt. |

Fable 5 call 10 encountered a stream overload reported with HTTP status 200.
The resume version added handling for such stream errors and retained the
already completed answers. It also changed retry defaults from four to six
attempts. The receipts contain the failed call and the subsequent completion;
all completed calls are recorded as succeeding on their first attempt within
their respective invocation. Source defaults are not evidence that no command-
line overrides were used. The exact historical invocation strings are not
available. The context-capable scripts retain an older introductory comment
about no system prompt; the actual argument handling and recorded request
parameters establish which runs used the additional context.

The supplied export reports that twelve earlier bare-prompt Fable 5.1 requests
were refused before answer generation and were withdrawn from the scored
export. Those twelve original records are not available here. The retained
classifier diagnostics document smaller checks, with a 16-token output limit,
including refusals without context and acceptance with context. They are not
the missing twelve records and are not scored benchmark answers.

## Running new inference

For a new manual-chat evaluation, follow
`original_release/docs/RERUN_MODELS.md`. Its commands assume `original_release/`
as the working directory and instruct readers to keep new output paths outside
the archive so the submitted files remain unchanged. For Fable, the preserved scripts can
make new calls, subject to service and model availability. Supply credentials
through your own environment; no credentials are included. Keep new outputs
outside the submission tree.

The following is an example for a **new** Fable 5.1 run, not a recovered
historical command. Run it from the submission archive root after installing
the recorded SDK in your own environment, and replace the output path:

```sh
python3 evaluation/harnesses/fable51_context_76bdf78d.py \
  --release-root original_release \
  --run-dir /absolute/path/to/new-fable51-run \
  --model claude-fable-5-1 --effort xhigh --max-tokens 128000 \
  --system-file followups/2026-09-05/claude_fable_5_1_xhigh_ctx_r1/harness/system_context.txt \
  --system-id new_fable51_run
```

Pass `--release-root` explicitly: the scripts' original default assumes their
old directory layout. For a new Fable 5 run, use the initial script with
`--model claude-fable-5` and no `--system-file`. Do not reproduce the historical
transport failure deliberately. The scripts save outputs and then invoke the
released scorer; they are not offline verification commands. Even `--dry-run`
creates a run directory and copies its harness, while `--probe` makes a real
model call.

## Source projections and privacy

The JSON evidence files are projections of the supplied records. Each wrapper
retains the original source member and its pre-projection SHA-256 hash, plus a
list of omitted fields. Repository identity commits, local paths, local-time
timezone fields, provider request/message IDs, and classifier text prefixes
are omitted; embedded local paths and provider IDs are replaced with explicit
placeholders. Scientific settings, UTC times, usage, prompt/response hashes,
and protocol decisions are retained. Source-relative `prompts/...` paths inside
wrapped records refer to `original_release/prompts/...` in this package.

The source hashes identify the supplied originals; they are not hashes of the
cleaned JSON projections. Raw API payloads and long CLI event/thought streams
are not included, so their retained hashes cannot be independently checked
against a file in this compact archive. Final answers and released prompts
are preserved separately and can be hash-checked here. These packaging
projections do not revise the scientific provenance or the project's
assistance disclosures.
