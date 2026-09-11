#!/usr/bin/env python3
"""Fresh-session LemmaPortfolio V4 direct-prompt capture harness for the Claude API.

Mirrors the Codex CLI follow-up captures in ``followups/2026-09-04``:

* one stateless API request per released prompt file, in numerical order;
* the released prompt bytes are the *only* user message (no system prompt,
  no tools, no files, no prior context);
* prompt bytes are verified against ``prompts/PROMPT_SHA256SUMS.txt`` first;
* every raw final answer is saved unchanged (``NN.json`` only when the whole
  text is one JSON object, otherwise ``NN.txt``), never repaired or regenerated;
* provider errors before any output are retried explicitly and every attempt
  is written to ``CALL_RECEIPTS.json``;
* the complete API response object, usage, stop reason, request id and
  timings are preserved for audit; then the released scorer is run.

Credentials: ``ANTHROPIC_API_KEY`` in the environment, or a gitignored
``.env`` file at the repository root containing ``ANTHROPIC_API_KEY=...``.
The key is never printed or written to the run directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HARNESS_PATH = Path(__file__).resolve()
DEFAULT_ROOT = HARNESS_PATH.parents[2]
DIRECT_CALLS = [f"{i:02d}" for i in range(1, 13)]
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
BACKOFF_SECONDS = [30, 60, 120]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def local_now() -> str:
    return dt.datetime.now().astimezone().isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_dotenv_key(root: Path) -> None:
    """Populate ANTHROPIC_API_KEY from a gitignored repo-root .env if unset."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key in {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"} and value:
            os.environ.setdefault(key, value)


def released_prompt_hashes(root: Path) -> dict[str, str]:
    sums = root / "prompts" / "PROMPT_SHA256SUMS.txt"
    table: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        table[name.strip().lstrip("*")] = digest.strip()
    return table


def episode_ids_from_prompt(text: str) -> list[str]:
    header = text.split("<episodes>", 1)[0]
    seen: list[str] = []
    for match in re.findall(r"MLP4B_\d{4}", header):
        if match not in seen:
            seen.append(match)
    return seen


def prepare_calls(root: Path, names: list[str]) -> list[dict[str, Any]]:
    table = released_prompt_hashes(root)
    calls = []
    for name in names:
        rel = f"DIRECT_PROMPTS/{name}.txt"
        path = root / "prompts" / rel
        data = path.read_bytes()
        digest = sha256_bytes(data)
        expected = table.get(rel)
        if expected is None:
            raise SystemExit(f"{rel} is not listed in PROMPT_SHA256SUMS.txt")
        if digest != expected:
            raise SystemExit(f"{rel} hash mismatch: {digest} != released {expected}")
        text = data.decode("utf-8")
        calls.append(
            {
                "name": name,
                "kind": "direct",
                "prompt": f"prompts/{rel}",
                "prompt_sha256": digest,
                "prompt_bytes": len(data),
                "episode_ids": episode_ids_from_prompt(text),
                "_text": text,
            }
        )
    return calls


def public_call(call: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in call.items() if not k.startswith("_")}


def response_text(message: Any) -> tuple[str, list[str], int]:
    """Concatenate text blocks exactly as returned; report block types."""
    types: list[str] = []
    parts: list[str] = []
    tool_uses = 0
    for block in message.content:
        types.append(block.type)
        if block.type == "text":
            parts.append(block.text)
        elif block.type in {"tool_use", "server_tool_use"}:
            tool_uses += 1
    return "".join(parts), types, tool_uses


def is_json_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except (json.JSONDecodeError, RecursionError):
        return False


def usage_dict(message: Any) -> dict[str, Any]:
    usage = message.usage
    out = {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", None),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
    }
    return out


def error_summary(exc: BaseException) -> dict[str, Any]:
    info: dict[str, Any] = {"type": type(exc).__name__, "message": str(exc)[:2000]}
    status = getattr(exc, "status_code", None)
    if status is not None:
        info["status_code"] = status
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        rid = headers.get("request-id")
        if rid:
            info["request_id"] = rid
        retry_after = headers.get("retry-after")
        if retry_after:
            info["retry_after"] = retry_after
    return info


def make_client(anthropic_mod: Any) -> Any:
    # Own retry loop so every attempt lands in the receipts; long read timeout
    # because a single xhigh request can run for many minutes.
    return anthropic_mod.Anthropic(
        max_retries=0,
        timeout=anthropic_mod.Timeout(3600.0, connect=60.0),
    )


def request_params(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model": args.model,
        "max_tokens": args.max_tokens,
        "output_config": {"effort": args.effort},
        # thinking is always on for claude-fable-5-1; the parameter is omitted.
        # No system prompt, no tools, no temperature/top_p, no fallbacks.
    }


def run_one(
    client: Any,
    anthropic_mod: Any,
    params: dict[str, Any],
    prompt_text: str,
    max_attempts: int,
    log,
) -> tuple[Any | None, list[dict[str, Any]], dict[str, Any] | None]:
    """Return (message, attempts, fatal_error)."""
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        record: dict[str, Any] = {"attempt": attempt, "started_utc": utc_now()}
        try:
            with client.messages.stream(
                **params,
                messages=[{"role": "user", "content": prompt_text}],
            ) as stream:
                message = stream.get_final_message()
            record["ended_utc"] = utc_now()
            record["outcome"] = "response"
            attempts.append(record)
            return message, attempts, None
        except anthropic_mod.APIConnectionError as exc:  # includes timeouts
            record.update(ended_utc=utc_now(), outcome="connection_error", error=error_summary(exc))
            retryable = True
        except anthropic_mod.APIStatusError as exc:
            record.update(ended_utc=utc_now(), outcome="api_error", error=error_summary(exc))
            retryable = exc.status_code in RETRYABLE_STATUS
        attempts.append(record)
        log(f"    attempt {attempt} failed: {record['error']['type']} "
            f"{record['error'].get('status_code', '')} {record['error']['message'][:200]}")
        if not retryable:
            return None, attempts, record["error"]
        if attempt < max_attempts:
            delay = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
            log(f"    retrying in {delay}s")
            time.sleep(delay)
    return None, attempts, attempts[-1].get("error")


def sha256_manifest(run_dir: Path) -> None:
    lines = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def score(root: Path, run_dir: Path, system_id: str, display_label: str, log) -> None:
    responses = sorted((run_dir / "responses").glob("*"))
    if not responses:
        log("no response files to score")
        return
    cmd = [
        sys.executable,
        str(root / "tools" / "score_predictions.py"),
        "--predictions",
        *[str(p) for p in responses],
        "--invalid-as-missing",
        "--system-id",
        system_id,
        "--display-label",
        display_label,
        "--output",
        str(run_dir / "score.json"),
    ]
    log("scoring: " + " ".join(cmd[:3]) + " ...")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    log(proc.stdout.strip())
    if proc.returncode != 0:
        log("scorer stderr: " + proc.stderr.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--release-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--model", default="claude-fable-5-1")
    parser.add_argument("--effort", default="xhigh",
                        choices=["low", "medium", "high", "xhigh", "max"])
    parser.add_argument("--max-tokens", type=int, default=128000)
    parser.add_argument("--calls", nargs="+", default=DIRECT_CALLS,
                        help="subset of 01..12 (default: all twelve, in order)")
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--system-id", default=None)
    parser.add_argument("--display-label", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="verify prompts and write metadata; make no API calls")
    parser.add_argument("--probe", action="store_true",
                        help="one tiny readiness request with the same model/effort, "
                             "saved under probes/ and excluded from the benchmark calls")
    args = parser.parse_args()

    root = args.release_root.resolve()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (root / args.run_dir)
    run_dir = run_dir.resolve()
    system_id = args.system_id or f"{args.model.replace('-', '_')}_{args.effort}_r1"
    pretty = {"claude-fable-5-1": "Claude Fable 5.1", "claude-opus-5": "Claude Opus 5",
              "claude-sonnet-5": "Claude Sonnet 5"}.get(args.model, args.model)
    display_label = args.display_label or f"{pretty} (Claude API, {args.effort})"

    log_path = run_dir / "harness_log.txt"

    def log(msg: str) -> None:
        line = f"[{utc_now()}] {msg}"
        print(line, flush=True)
        if not args.dry_run:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    for name in args.calls:
        if name not in DIRECT_CALLS:
            raise SystemExit(f"unknown call {name}; expected one of {DIRECT_CALLS}")

    calls = prepare_calls(root, args.calls)
    print(f"verified {len(calls)} released prompt file(s) against PROMPT_SHA256SUMS.txt", flush=True)

    (run_dir / "responses").mkdir(parents=True, exist_ok=True)
    (run_dir / "raw_api").mkdir(exist_ok=True)
    (run_dir / "harness").mkdir(exist_ok=True)
    shutil.copy2(HARNESS_PATH, run_dir / "harness" / HARNESS_PATH.name)

    load_dotenv_key(root)
    if not args.dry_run and not (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or (Path.home() / ".config" / "anthropic").is_dir()
    ):
        raise SystemExit(
            "No Claude API credential found. Export ANTHROPIC_API_KEY, or put "
            "ANTHROPIC_API_KEY=... in the gitignored .env at the repository root."
        )
    try:
        import anthropic  # noqa: WPS433 (runtime import so --dry-run works without it)
    except ImportError:
        anthropic = None
        if not args.dry_run:
            raise SystemExit("anthropic SDK not importable in this interpreter")

    params = request_params(args)
    metadata_path = run_dir / "run_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        known = {c["name"] for c in metadata["calls"]}
        for call in calls:
            if call["name"] not in known:
                metadata["calls"].append(public_call(call))
    else:
        metadata = {
            "started_utc": utc_now(),
            "started_local": local_now(),
            "provider": "Anthropic Claude API (api.anthropic.com), Messages API",
            "model_requested": args.model,
            "visible_mode": f"output_config.effort={args.effort}; thinking always on (parameter omitted)",
            "tier": "unknown (organization rate-limit tier not queried)",
            "session_isolation": "one stateless request per prompt; no prior context",
            "system_prompt": None,
            "tools": "none declared",
            "web_search_browsing_files_memory_connectors": "not available to the model (bare Messages API)",
            "fallbacks": "disabled (refusals preserved as-is)",
            "request_params": params,
            "sdk": {
                "package": "anthropic",
                "version": getattr(anthropic, "__version__", None),
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "harness": {
                "path": str(HARNESS_PATH.relative_to(root)) if HARNESS_PATH.is_relative_to(root) else str(HARNESS_PATH),
                "sha256": sha256_file(HARNESS_PATH),
            },
            "released_prompt_manifest_sha256": sha256_file(root / "prompts" / "PROMPT_SHA256SUMS.txt"),
            "system_id": system_id,
            "display_label": display_label,
            "calls": [public_call(c) for c in calls],
        }
    if not args.dry_run:
        write_json(metadata_path, metadata)

    if args.dry_run:
        print(json.dumps({k: v for k, v in metadata.items() if k != "calls"}, indent=2))
        for call in calls:
            print(f"  {call['name']}  {call['prompt_sha256'][:16]}  {call['prompt_bytes']:>7} B  {call['episode_ids']}")
        print("dry run complete; no API calls made")
        return 0

    client = make_client(anthropic)

    if args.probe:
        (run_dir / "probes").mkdir(exist_ok=True)
        probe_params = dict(params, max_tokens=2048)
        log(f"readiness probe: {args.model} effort={args.effort}")
        t0 = time.monotonic()
        message, attempts, fatal = run_one(
            client, anthropic, probe_params,
            "Reply with exactly the single word OK and nothing else.",
            1, log,
        )
        record = {
            "started_utc": attempts[0]["started_utc"],
            "wall_seconds": round(time.monotonic() - t0, 3),
            "attempts": attempts,
            "note": "readiness probe; not one of the twelve benchmark calls",
        }
        if message is not None:
            text, types, _ = response_text(message)
            record.update(
                model_returned=message.model, message_id=message.id,
                request_id=getattr(message, "_request_id", None),
                stop_reason=message.stop_reason, content_block_types=types,
                text=text, usage=usage_dict(message),
            )
            log(f"probe ok: model={message.model} stop={message.stop_reason} text={text!r}")
        else:
            log(f"probe FAILED: {fatal}")
        write_json(run_dir / "probes" / f"probe_{int(time.time())}.json", record)
        if message is None:
            return 2

    receipts_path = run_dir / "CALL_RECEIPTS.json"
    receipts: list[dict[str, Any]] = (
        json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.exists() else []
    )
    completed = {r["call"] for r in receipts if r.get("completed")}

    run_t0 = time.monotonic()
    for call in calls:
        name = call["name"]
        if name in completed:
            log(f"call {name}: already completed, skipping")
            continue
        log(f"call {name}: {call['prompt']} ({call['prompt_bytes']} bytes) -> {args.model} effort={args.effort}")
        t0 = time.monotonic()
        started = utc_now()
        message, attempts, fatal = run_one(
            client, anthropic, params, call["_text"], args.max_attempts, log
        )
        wall = round(time.monotonic() - t0, 3)
        receipt: dict[str, Any] = {
            "call": name,
            "kind": "direct",
            "model_requested": args.model,
            "effort": args.effort,
            "prompt": call["prompt"],
            "prompt_sha256": call["prompt_sha256"],
            "episode_ids": call["episode_ids"],
            "started_utc": started,
            "ended_utc": utc_now(),
            "wall_seconds": wall,
            "attempts": attempts,
            "attempt_count": len(attempts),
        }
        if message is None:
            receipt.update(completed=False, fatal_error=fatal)
            receipts.append(receipt)
            write_json(receipts_path, receipts)
            log(f"call {name}: FATAL provider error, aborting run (no response file written)")
            return 3

        text, types, tool_uses = response_text(message)
        valid = is_json_object(text)
        ext = "json" if valid else "txt"
        out_path = run_dir / "responses" / f"{name}.{ext}"
        out_path.write_text(text, encoding="utf-8")
        write_json(run_dir / "raw_api" / f"{name}.json", message.to_dict())

        receipt.update(
            completed=True,
            model_returned=message.model,
            message_id=message.id,
            request_id=getattr(message, "_request_id", None),
            stop_reason=message.stop_reason,
            stop_details=(message.stop_details.to_dict()
                          if getattr(message, "stop_details", None) is not None else None),
            content_block_types=types,
            tool_use_block_count=tool_uses,
            usage=usage_dict(message),
            response_file=out_path.relative_to(run_dir).as_posix(),
            response_chars=len(text),
            response_sha256=sha256_bytes(text.encode("utf-8")),
            valid_json_object=valid,
            raw_api_sha256=sha256_file(run_dir / "raw_api" / f"{name}.json"),
        )
        receipts.append(receipt)
        write_json(receipts_path, receipts)
        u = receipt["usage"]
        log(f"call {name}: done in {wall/60:.1f} min; stop={message.stop_reason} "
            f"json={valid} in={u['input_tokens']} out={u['output_tokens']} "
            f"cache_read={u['cache_read_input_tokens']} blocks={types}")

    done = [r for r in receipts if r.get("completed")]
    totals = {k: sum((r["usage"].get(k) or 0) for r in done) for k in
              ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
    completed_json = {
        "ended_utc": utc_now(),
        "ended_local": local_now(),
        "call_count": len(done),
        "all_twelve_completed": {r["call"] for r in done} == set(DIRECT_CALLS),
        "wall_seconds_this_invocation": round(time.monotonic() - run_t0, 3),
        "sum_call_wall_seconds": round(sum(r["wall_seconds"] for r in done), 3),
        "usage_totals": totals,
        "stop_reasons": {r["call"]: r["stop_reason"] for r in done},
        "valid_json_count": sum(1 for r in done if r["valid_json_object"]),
        "tool_use_blocks_total": sum(r["tool_use_block_count"] for r in done),
    }
    write_json(run_dir / "RUN_COMPLETED.json", completed_json)
    log(f"run complete: {len(done)} call(s); sum wall {completed_json['sum_call_wall_seconds']/60:.1f} min; usage {totals}")

    score(root, run_dir, system_id, display_label, log)
    sha256_manifest(run_dir)
    log(f"wrote SHA256SUMS.txt for {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
