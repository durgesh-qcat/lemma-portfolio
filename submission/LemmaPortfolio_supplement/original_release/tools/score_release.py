#!/usr/bin/env python3
"""Reconstruct LemmaPortfolio V4 optima and score the released responses.

The script uses only the Python standard library.  It parses text extracted
from the two archived response PDFs, aligns blocks by episode ID, regenerates both
deterministic baselines, and writes canonical machine-readable results.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


BENCHMARK_ID = "lemma-portfolio.mathlib-compression-blind-60.v4"
PUBLIC_SHA256 = "b54293b08bc7ddbb7110a50908049922f7cfd86f14cb49a4de4e28353aecc6d8"
LABELS_SHA256 = "d17c1fd5c6d87635daf8035fe4a0918d1eaa29708eae37cb797cae08c19ef887"
SOURCE_PDF_SHA256 = "2f20fbc4b3eb3b87c4b693058fc5744a947de04e19a2eca70f0ea5c0d54dde3f"
SOURCE_TEXT_SHA256 = "3cd354ccb7f8533e3709a11a785748c7d09735b41f6f97930a4247d17a8f3c40"
XHIGH_SOURCE_PDF_SHA256 = "02abb92d1e3fd6d59dca5faa191a7fec214dffae7c4f023ce5cbb5d02b517afa"
XHIGH_SOURCE_TEXT_SHA256 = "ac3bfc8cac5db47000f5d42b29fb798fcbb4dd8184a4f6bf2b3e6190f7555ca3"
DEVELOPMENT_PUBLIC_SHA256 = "404452daa5017793d9f7b10f4d92716d2bb267dca034094b0f41f8c8d9219ffc"
DEVELOPMENT_LABELS_SHA256 = "bee487259392de4d36b2140a715c7b4196ce7cc2027c3b13c90e1874a19149d0"
DEVELOPMENT_PROTOCOL_SHA256 = "7b5a05678166e2595f465ccfd562afbda281b9523b29bd1cddb86e1d02241c1c"
DEVELOPMENT_PROMPTS_SHA256 = "58a31aa21f8cd1d5f34fc3e3f6aa367f4f02ea909be695db0531b8cc534b2284"
DEVELOPMENT_PANEL_SHA256 = "bc598103d7cd0ec4caa5f930032fc44f1531bb5154bb2c6e0409348331e39f39"
DEVELOPMENT_RUN_SHA256 = "1298df0885ff96179e86885e2ceaadabf0bc43998567dcfed29574954ec7c018"
SELECTION_BUDGET = 3
TARGET_COUNT = 8
SHA_BASELINE_SEED = "lemma-portfolio-v4-manual-core-sha256-random-v1"

MODELS = [
    ("gpt_sol_5_6_pro", "GPT SOL 5.6 Pro", "GPT SOL 5.6 Pro"),
    (
        "deepseek_instant_deepthink",
        "DeepSeek Instant + DeepThink",
        "DeepSeek Instant (with DeepThink mode)",
    ),
    (
        "deepseek_expert_deepthink",
        "DeepSeek Expert + DeepThink",
        "DeepSeek Expert (with DeepThink mode)",
    ),
    ("qwen_3_8_max_thinking", "Qwen 3.8 Max - Thinking", "Qwen 3.8 Max- Thinking"),
    ("qwen_3_7_plus_thinking", "Qwen 3.7 Plus - Thinking", "QWEN 3.7 PLUS- THINKING"),
]
XHIGH_MODEL = ("gpt_sol_5_6_xhigh", "GPT SOL 5.6 (xhigh)", "Gpt sol 5.6 xhigh")


class ReleaseError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def coverage(selected: frozenset[str], dependencies: dict[str, frozenset[str]]) -> int:
    return sum(bool(selected & direct) for direct in dependencies.values())


def load_benchmark(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    public_path = root / "data/test.public.jsonl"
    labels_path = root / "data/test.labels.jsonl"
    if sha256(public_path) != PUBLIC_SHA256 or sha256(labels_path) != LABELS_SHA256:
        raise ReleaseError("public data or labels differ from the committed SHA-256")
    public_rows = jsonl(public_path)
    label_rows = jsonl(labels_path)
    if len(public_rows) != 60 or len(label_rows) != 60:
        raise ReleaseError("V4 must contain exactly 60 public and label rows")
    public: dict[str, dict[str, Any]] = {}
    for row in public_rows:
        episode_id = row["episode_id"]
        candidate_ids = [candidate["id"] for candidate in row["candidates"]]
        target_ids = [target["id"] for target in row["targets"]]
        if (
            episode_id in public
            or len(candidate_ids) != 16
            or len(set(candidate_ids)) != 16
            or len(target_ids) != TARGET_COUNT
            or row.get("selection_budget") != SELECTION_BUDGET
        ):
            raise ReleaseError(f"invalid public row: {episode_id}")
        public[episode_id] = {
            "row": row,
            "candidate_ids": candidate_ids,
            "target_ids": target_ids,
        }
    labels: dict[str, dict[str, Any]] = {}
    for row in label_rows:
        episode_id = row["episode_id"]
        if episode_id not in public or episode_id in labels:
            raise ReleaseError(f"invalid label ID: {episode_id}")
        dependencies = {
            target["id"]: frozenset(target["direct_candidates"])
            for target in row["targets"]
        }
        allowed = set(public[episode_id]["candidate_ids"])
        if list(dependencies) != public[episode_id]["target_ids"] or any(
            not direct.issubset(allowed) for direct in dependencies.values()
        ):
            raise ReleaseError(f"invalid incidence row: {episode_id}")
        scored = [
            (coverage(frozenset(portfolio), dependencies), portfolio)
            for portfolio in combinations(sorted(allowed), SELECTION_BUDGET)
        ]
        optimum = max(score for score, _ in scored)
        optima = [list(portfolio) for score, portfolio in scored if score == optimum]
        if optimum != row["optimal_coverage"] or optima != row["optimal_portfolios"]:
            raise ReleaseError(f"stored optimum does not replay: {episode_id}")
        labels[episode_id] = {
            "dependencies": dependencies,
            "optimal_coverage": optimum,
            "optimal_portfolios": {tuple(value) for value in optima},
            "edge_count": sum(len(value) for value in dependencies.values()),
        }
    if list(public) != list(labels):
        raise ReleaseError("public and label order differs")
    return public, labels


def load_development_batch(
    root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load and independently reconstruct the first 15 development episodes."""

    public_path = root / "data/development.public.jsonl"
    labels_path = root / "data/development.labels.jsonl"
    if (
        sha256(public_path) != DEVELOPMENT_PUBLIC_SHA256
        or sha256(labels_path) != DEVELOPMENT_LABELS_SHA256
    ):
        raise ReleaseError("development data or labels differ from the released V4 files")
    public_rows = jsonl(public_path)[:15]
    label_rows = jsonl(labels_path)[:15]
    public: dict[str, dict[str, Any]] = {}
    labels: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(public_rows):
        episode_id = f"MLP4C_{index:04d}"
        candidate_ids = [candidate["id"] for candidate in row["candidates"]]
        target_ids = [target["id"] for target in row["targets"]]
        if (
            row.get("episode_id") != episode_id
            or len(candidate_ids) != 16
            or len(set(candidate_ids)) != 16
            or len(target_ids) != TARGET_COUNT
            or row.get("selection_budget") != SELECTION_BUDGET
        ):
            raise ReleaseError(f"invalid development public row: {episode_id}")
        public[episode_id] = {
            "row": row,
            "candidate_ids": candidate_ids,
            "target_ids": target_ids,
        }
    for index, row in enumerate(label_rows):
        episode_id = f"MLP4C_{index:04d}"
        if row.get("episode_id") != episode_id:
            raise ReleaseError(f"invalid development label row: {episode_id}")
        dependencies = {
            target["id"]: frozenset(target["direct_candidates"])
            for target in row["targets"]
        }
        allowed = set(public[episode_id]["candidate_ids"])
        scored = [
            (coverage(frozenset(portfolio), dependencies), portfolio)
            for portfolio in combinations(sorted(allowed), SELECTION_BUDGET)
        ]
        optimum = max(score for score, _ in scored)
        optima = [list(portfolio) for score, portfolio in scored if score == optimum]
        if optimum != row["optimal_coverage"] or optima != row["optimal_portfolios"]:
            raise ReleaseError(f"development optimum does not replay: {episode_id}")
        labels[episode_id] = {
            "dependencies": dependencies,
            "optimal_coverage": optimum,
            "optimal_portfolios": {tuple(value) for value in optima},
            "edge_count": sum(len(value) for value in dependencies.values()),
        }
    return public, labels


def development_evidence(
    root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify the frozen capture inventory and independently score its 15 selections."""

    frozen = root / "development_evidence/frozen"
    run_root = (
        frozen
        / "frozen_runs/codex_gpt56_sol_max_calibration_direct"
    )
    core = {
        frozen / "PANEL_PROTOCOL.frozen.json": DEVELOPMENT_PROTOCOL_SHA256,
        frozen / "prompts/manifest.json": DEVELOPMENT_PROMPTS_SHA256,
        frozen / "frozen_runs/OUTPUTS_FROZEN.json": DEVELOPMENT_PANEL_SHA256,
        run_root / "RUN_FROZEN.json": DEVELOPMENT_RUN_SHA256,
    }
    for path, expected in core.items():
        if not path.is_file() or sha256(path) != expected:
            raise ReleaseError(f"development evidence differs: {path.name}")
    panel = json.loads((frozen / "frozen_runs/OUTPUTS_FROZEN.json").read_text(encoding="utf-8"))
    run = json.loads((run_root / "RUN_FROZEN.json").read_text(encoding="utf-8"))
    if (
        panel.get("status") != "FROZEN_BEFORE_LABEL_UNSEAL"
        or panel.get("labels_opened") is not False
        or panel.get("labels_sha256_commitment")
        != "9fec3602da660e4a293c7a5a8c9f74e7f4eddafab87d3bf84f4cea84a899d9f5"
        or run.get("status") != "FROZEN_BEFORE_LABEL_UNSEAL"
        or run.get("labels_unopened_during_run") is not True
        or run.get("episode_count") != 15
    ):
        raise ReleaseError("development freeze metadata is inconsistent")
    for artifact in run.get("artifacts", []):
        path = run_root / artifact["path"]
        if (
            not path.is_file()
            or path.stat().st_size != artifact["bytes"]
            or sha256(path) != artifact["sha256"]
        ):
            raise ReleaseError(f"development capture artifact differs: {artifact['path']}")
    public, labels = load_development_batch(root)
    predictions: dict[str, Any] = {}
    for episode_id in public:
        response = json.loads(
            (run_root / f"responses/{episode_id}.txt").read_text(encoding="utf-8")
        )
        if response.get("episode_id") != episode_id:
            raise ReleaseError(f"development response ID differs: {episode_id}")
        predictions[episode_id] = response.get("selected")
    summary, details = score_predictions(
        "codex_gpt56_sol_max_calibration_direct",
        "Controlled Codex CLI Sol development check",
        predictions,
        public,
        labels,
    )
    if (
        summary["exact_optimal"] != 6
        or summary["valid"] != 15
        or summary["achieved_target_coverage"] != 80
    ):
        raise ReleaseError("development 6/15 check does not reproduce")
    report = {
        "schema_version": "lemma-portfolio.development-score.v4.replay-v1",
        "batch": "first 15 released development episodes",
        "source_hashes": {
            "development_public_sha256": DEVELOPMENT_PUBLIC_SHA256,
            "development_labels_sha256": DEVELOPMENT_LABELS_SHA256,
            "protocol_sha256": DEVELOPMENT_PROTOCOL_SHA256,
            "prompts_manifest_sha256": DEVELOPMENT_PROMPTS_SHA256,
            "panel_freeze_sha256": DEVELOPMENT_PANEL_SHA256,
            "run_manifest_sha256": DEVELOPMENT_RUN_SHA256,
        },
        "row": summary,
    }
    return report, details


def decoded_envelopes(segment: str) -> list[dict[str, Any]]:
    """Decode balanced JSON objects after undoing PDF layout whitespace."""

    compact = "".join(segment.split())
    output: list[dict[str, Any]] = []
    cursor = 0
    while True:
        start = compact.find("{", cursor)
        if start < 0:
            return output
        depth = 0
        in_string = False
        escaped = False
        end = None
        for position in range(start, len(compact)):
            character = compact[position]
            if in_string:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    in_string = False
            else:
                if character == '"':
                    in_string = True
                elif character == "{":
                    depth += 1
                elif character == "}":
                    depth -= 1
                    if depth == 0:
                        end = position + 1
                        break
        if end is None:
            return output
        try:
            value = json.loads(compact[start:end])
        except json.JSONDecodeError:
            value = None
        if isinstance(value, dict) and ({"predictions", "predicted_support"} & set(value)):
            output.append(value)
        cursor = end


def block_id(episode_ids: list[str]) -> str:
    numbers = sorted(int(episode_id.rsplit("_", 1)[1]) for episode_id in episode_ids)
    if len(numbers) != 5 or numbers != list(range(numbers[0], numbers[0] + 5)) or numbers[0] % 5:
        raise ReleaseError(f"not a complete five-item block: {episode_ids}")
    return f"D{numbers[0] // 5 + 1:02d}"


def parse_xhigh_responses(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Parse the separately supplied four-page GPT SOL xhigh capture."""

    pdf_path = root / "responses/sol_xhigh_source_responses.pdf"
    text_path = root / "responses/sol_xhigh_source_extracted.txt"
    if (
        sha256(pdf_path) != XHIGH_SOURCE_PDF_SHA256
        or sha256(text_path) != XHIGH_SOURCE_TEXT_SHA256
    ):
        raise ReleaseError("xhigh response source PDF or extracted text hash differs")
    raw = text_path.read_text(encoding="utf-8")
    predictions: dict[str, list[str]] = {}
    support: dict[str, Any] = {}
    order: list[str] = []
    support_order: list[str] = []
    for envelope in decoded_envelopes(raw):
        if "predictions" in envelope:
            values = envelope["predictions"]
            if not isinstance(values, dict):
                raise ReleaseError("xhigh: predictions is not an object")
            current = block_id(list(values))
            order.append(current)
            for episode_id, selected in values.items():
                if episode_id in predictions:
                    raise ReleaseError(f"xhigh: duplicate prediction {episode_id}")
                predictions[episode_id] = selected
        elif "predicted_support" in envelope:
            values = envelope["predicted_support"]
            if not isinstance(values, dict):
                raise ReleaseError("xhigh: predicted_support is not an object")
            support_order.append(block_id(list(values)))
            for episode_id, value in values.items():
                if episode_id in support:
                    raise ReleaseError(f"xhigh: duplicate support row {episode_id}")
                support[episode_id] = value
    expected_direct = [f"D{number:02d}" for number in range(1, 13)]
    expected_support = ["D04", "D05", "D06", "D12"]
    if (
        sorted(order) != expected_direct
        or len(order) != len(expected_direct)
        or len(predictions) != 60
    ):
        raise ReleaseError("xhigh: direct block set is incomplete or duplicated")
    if (
        sorted(support_order) != expected_support
        or len(support_order) != len(expected_support)
        or len(support) != 20
    ):
        raise ReleaseError("xhigh: support block set is incomplete or duplicated")
    direct = {
        "display_label": XHIGH_MODEL[1],
        "predictions": dict(sorted(predictions.items())),
    }
    alignment = {
        "decoded_block_order": order,
        "duplicate_blocks": [],
        "missing_blocks": [],
        "support_block_order": support_order,
    }
    return direct, dict(sorted(support.items())), alignment


def parse_responses(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    pdf_path = root / "responses/source_responses.pdf"
    text_path = root / "responses/source_extracted.txt"
    if sha256(pdf_path) != SOURCE_PDF_SHA256 or sha256(text_path) != SOURCE_TEXT_SHA256:
        raise ReleaseError("response source PDF or extracted text hash differs")
    raw = text_path.read_text(encoding="utf-8")
    direct: dict[str, Any] = {}
    alignment: dict[str, Any] = {}
    support: dict[str, Any] = {}
    for index, (system_id, display, heading) in enumerate(MODELS):
        start = raw.index(heading)
        stop = raw.index(MODELS[index + 1][2]) if index + 1 < len(MODELS) else len(raw)
        segment = raw[start:stop]
        envelopes = decoded_envelopes(segment)
        predictions: dict[str, list[str]] = {}
        order: list[str] = []
        duplicate_blocks: list[str] = []
        for envelope in envelopes:
            if "predictions" in envelope:
                values = envelope["predictions"]
                if not isinstance(values, dict):
                    raise ReleaseError(f"{system_id}: predictions is not an object")
                current = block_id(list(values))
                if current in order:
                    duplicate_blocks.append(current)
                order.append(current)
                for episode_id, selected in values.items():
                    predictions.setdefault(episode_id, selected)
            elif system_id == "gpt_sol_5_6_pro":
                values = envelope["predicted_support"]
                if not isinstance(values, dict):
                    raise ReleaseError("GPT structured support is not an object")
                support.update(values)
        direct[system_id] = {
            "display_label": display,
            "predictions": dict(sorted(predictions.items())),
        }
        alignment[system_id] = {
            "decoded_block_order": order,
            "duplicate_blocks": duplicate_blocks,
            "missing_blocks": [f"D{number:02d}" for number in range(1, 13) if f"D{number:02d}" not in order],
        }
    xhigh_direct, xhigh_support, xhigh_alignment = parse_xhigh_responses(root)
    direct[XHIGH_MODEL[0]] = xhigh_direct
    alignment[XHIGH_MODEL[0]] = xhigh_alignment
    expected_counts = {
        "gpt_sol_5_6_pro": 55,
        "gpt_sol_5_6_xhigh": 60,
        "deepseek_instant_deepthink": 60,
        "deepseek_expert_deepthink": 60,
        "qwen_3_8_max_thinking": 55,
        "qwen_3_7_plus_thinking": 60,
    }
    if {key: len(value["predictions"]) for key, value in direct.items()} != expected_counts:
        raise ReleaseError("decoded response counts differ from the audited alignment")
    if len(support) != 20 or len(xhigh_support) != 20:
        raise ReleaseError("each GPT structured-support capture must contain 20 episodes")
    alignment["policy"] = {
        "alignment_key": "explicit episode_id",
        "gpt_duplicate_rule": "retain first D11 occurrence; both variants score identically",
        "invalid_whole_blocks": {
            "gpt_sol_5_6_pro": ["D12: absent direct-response envelope"],
            "qwen_3_8_max_thinking": ["D12: outer opening brace absent"],
        },
        "source_files": {
            "combined_five_rows": "responses/source_responses.pdf",
            "gpt_sol_5_6_xhigh": "responses/sol_xhigh_source_responses.pdf",
        },
        "repairs_applied": False,
    }
    return direct, {
        "gpt_sol_5_6_pro": dict(sorted(support.items())),
        "gpt_sol_5_6_xhigh": xhigh_support,
    }, alignment


def valid_prediction(value: Any, allowed: set[str]) -> tuple[str, ...] | None:
    if (
        not isinstance(value, list)
        or len(value) != SELECTION_BUDGET
        or len(set(value)) != SELECTION_BUDGET
        or not all(isinstance(item, str) for item in value)
        or not set(value).issubset(allowed)
    ):
        return None
    return tuple(sorted(value))


def item_metrics(
    selected: tuple[str, ...] | None, label: dict[str, Any]
) -> dict[str, Any]:
    if selected is None:
        return {"coverage": 0, "normalized": 0.0, "selected_edges": 0, "optimal": False}
    chosen = frozenset(selected)
    achieved = coverage(chosen, label["dependencies"])
    return {
        "coverage": achieved,
        "normalized": achieved / label["optimal_coverage"],
        "selected_edges": sum(len(chosen & direct) for direct in label["dependencies"].values()),
        "optimal": tuple(sorted(selected)) in label["optimal_portfolios"],
    }


def wilson(correct: int, total: int) -> list[float]:
    z = 1.959963984540054
    proportion = correct / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [centre - margin, centre + margin]


def cluster_interval(outcomes: list[list[int]]) -> list[float]:
    """Exact percentile interval for the empirical whole-block bootstrap."""

    block_scores = [sum(block) for block in outcomes]
    distribution: Counter[int] = Counter({0: 1})
    for _ in block_scores:
        updated: Counter[int] = Counter()
        for subtotal, count in distribution.items():
            for score in block_scores:
                updated[subtotal + score] += count
        distribution = updated
    denominator = len(block_scores) ** len(block_scores)

    def quantile(probability: float) -> float:
        cumulative = 0
        for score in sorted(distribution):
            cumulative += distribution[score]
            if cumulative / denominator >= probability:
                return score / sum(map(len, outcomes))
        raise AssertionError("unreachable bootstrap quantile")

    return [quantile(0.025), quantile(0.975)]


def score_predictions(
    system_id: str,
    display_label: str,
    predictions: dict[str, Any],
    public: dict[str, dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    episode_ids: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ids = list(public) if episode_ids is None else episode_ids
    details: list[dict[str, Any]] = []
    blocks: dict[str, list[int]] = {}
    for episode_id in ids:
        selected = valid_prediction(predictions.get(episode_id), set(public[episode_id]["candidate_ids"]))
        metrics = item_metrics(selected, labels[episode_id])
        block = f"D{int(episode_id.rsplit('_', 1)[1]) // 5 + 1:02d}"
        blocks.setdefault(block, []).append(int(metrics["optimal"]))
        details.append(
            {
                "system_id": system_id,
                "episode_id": episode_id,
                "block_id": block,
                "selected": list(selected) if selected else None,
                "valid": selected is not None,
                "optimal": metrics["optimal"],
                "coverage": metrics["coverage"],
                "optimal_coverage": labels[episode_id]["optimal_coverage"],
                "normalized_coverage": metrics["normalized"],
                "selected_edges": metrics["selected_edges"],
                "hidden_edges": labels[episode_id]["edge_count"],
            }
        )
    total = len(ids)
    exact = sum(int(row["optimal"]) for row in details)
    valid = sum(int(row["valid"]) for row in details)
    achieved = sum(row["coverage"] for row in details)
    selected_edges = sum(row["selected_edges"] for row in details)
    hidden_edges = sum(row["hidden_edges"] for row in details)
    summary = {
        "system_id": system_id,
        "display_label": display_label,
        "exact_optimal": exact,
        "total": total,
        "exact_optimal_percentage": 100 * exact / total,
        "valid": valid,
        "valid_percentage": 100 * valid / total,
        "achieved_target_coverage": achieved,
        "target_count": TARGET_COUNT * total,
        "target_coverage_percentage": 100 * achieved / (TARGET_COUNT * total),
        "mean_oracle_normalized_coverage_percentage": 100 * sum(row["normalized_coverage"] for row in details) / total,
        "selected_edge_recall_percentage": 100 * selected_edges / hidden_edges,
        "wilson_95_interval_fraction": wilson(exact, total),
        "block_bootstrap_95_interval_fraction": cluster_interval(
            [blocks[key] for key in sorted(blocks)]
        ),
        "exact_by_block": {key: sum(value) for key, value in sorted(blocks.items())},
    }
    return summary, details


def ngrams(statement: str) -> Counter[str]:
    return Counter(
        statement[start : start + width]
        for width in (3, 4, 5)
        for start in range(max(0, len(statement) - width + 1))
    )


def tfidf_vectors(statements: list[str]) -> list[dict[str, float]]:
    counts = [ngrams(statement) for statement in statements]
    document_frequency: Counter[str] = Counter()
    for row in counts:
        document_frequency.update(row.keys())
    vectors = []
    for row in counts:
        weighted = {
            term: (1 + math.log(count))
            * (math.log((1 + len(counts)) / (1 + document_frequency[term])) + 1)
            for term, count in row.items()
        }
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        vectors.append({term: value / norm for term, value in weighted.items()} if norm else {})
    return vectors


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


def deterministic_baselines(public: dict[str, dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    sha_predictions: dict[str, list[str]] = {}
    tfidf_predictions: dict[str, list[str]] = {}
    for episode_id, item in public.items():
        candidate_ids = item["candidate_ids"]
        sha_ranked = sorted(
            candidate_ids,
            key=lambda candidate_id: hashlib.sha256(
                f"{SHA_BASELINE_SEED}\0{episode_id}\0{candidate_id}".encode()
            ).digest(),
        )
        sha_predictions[episode_id] = sorted(sha_ranked[:SELECTION_BUDGET])
        row = item["row"]
        statements = [candidate["statement"] for candidate in row["candidates"]] + [
            target["statement"] for target in row["targets"]
        ]
        vectors = tfidf_vectors(statements)
        candidate_vectors = vectors[:16]
        target_vectors = vectors[16:]
        similarities = [
            [cosine(target, candidate) for candidate in candidate_vectors]
            for target in target_vectors
        ]
        candidate_index = {candidate_id: index for index, candidate_id in enumerate(candidate_ids)}
        scored = []
        for portfolio in combinations(sorted(candidate_ids), SELECTION_BUDGET):
            value = sum(
                max(target[candidate_index[candidate_id]] for candidate_id in portfolio)
                for target in similarities
            )
            scored.append((value, portfolio))
        optimum = max(value for value, _ in scored)
        tfidf_predictions[episode_id] = list(
            next(portfolio for value, portfolio in scored if value == optimum)
        )
    return {
        "sha256_random_portfolio": sha_predictions,
        "public_text_char_tfidf_facility": tfidf_predictions,
    }


def random_expectation(labels: dict[str, dict[str, Any]]) -> dict[str, float]:
    expected_exact = 0.0
    expected_coverage = 0.0
    expected_normalized = 0.0
    portfolio_count = math.comb(16, SELECTION_BUDGET)
    for label in labels.values():
        expected_exact += len(label["optimal_portfolios"]) / portfolio_count
        item_coverage = 0.0
        for direct in label["dependencies"].values():
            misses = math.comb(16 - len(direct), SELECTION_BUDGET)
            item_coverage += 1 - misses / portfolio_count
        expected_coverage += item_coverage
        expected_normalized += item_coverage / label["optimal_coverage"]
    return {
        "expected_exact_episodes": expected_exact,
        "expected_exact_percentage": 100 * expected_exact / len(labels),
        "mean_expected_coverage_out_of_8": expected_coverage / len(labels),
        "mean_target_coverage_percentage": 100 * expected_coverage / (TARGET_COUNT * len(labels)),
        "mean_oracle_normalized_coverage_percentage": 100 * expected_normalized / len(labels),
        "expected_edge_recall_percentage": 100 * SELECTION_BUDGET / 16,
    }


def solve_support(candidate_ids: list[str], support: dict[str, list[str]], prefix: int) -> list[str]:
    retained = {target: frozenset(values[:prefix]) for target, values in support.items()}
    scored = [
        (sum(bool(frozenset(portfolio) & values) for values in retained.values()), portfolio)
        for portfolio in combinations(sorted(candidate_ids), SELECTION_BUDGET)
    ]
    optimum = max(value for value, _ in scored)
    return list(next(portfolio for value, portfolio in scored if value == optimum))


def incidence_counts(
    predicted: dict[str, list[str]], actual: dict[str, frozenset[str]], prefix: int | None
) -> tuple[int, int, int]:
    true_positive = false_positive = false_negative = 0
    for target, direct in actual.items():
        values = predicted[target] if prefix is None else predicted[target][:prefix]
        guess = set(values)
        true_positive += len(guess & direct)
        false_positive += len(guess - direct)
        false_negative += len(direct - guess)
    return true_positive, false_positive, false_negative


def structured_diagnostic(
    system_id: str,
    display_label: str,
    support_bundle: dict[str, Any],
    direct: dict[str, Any],
    public: dict[str, dict[str, Any]],
    labels: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    support = support_bundle[system_id]
    predictions: dict[str, list[str]] = {}
    full_counts = [0, 0, 0]
    q2_counts = [0, 0, 0]
    for episode_id, value in support.items():
        expected_targets = public[episode_id]["target_ids"]
        if set(value) != set(expected_targets):
            raise ReleaseError(f"support target keys differ: {episode_id}")
        allowed = set(public[episode_id]["candidate_ids"])
        for target in expected_targets:
            ranked = value[target]
            if (
                not isinstance(ranked, list)
                or len(ranked) > 4
                or len(ranked) != len(set(ranked))
                or not set(ranked).issubset(allowed)
            ):
                raise ReleaseError(f"invalid support list: {episode_id}/{target}")
        predictions[episode_id] = solve_support(public[episode_id]["candidate_ids"], value, 2)
        for index, count in enumerate(incidence_counts(value, labels[episode_id]["dependencies"], None)):
            full_counts[index] += count
        for index, count in enumerate(incidence_counts(value, labels[episode_id]["dependencies"], 2)):
            q2_counts[index] += count
    ids = sorted(support)
    structured_summary, details = score_predictions(
        f"{system_id}_support_q2",
        f"{display_label} support q=2",
        predictions,
        public,
        labels,
        ids,
    )
    direct_summary, direct_details = score_predictions(
        f"{system_id}_matched_direct",
        f"{display_label} matched direct",
        direct[system_id]["predictions"],
        public,
        labels,
        ids,
    )

    def edge_summary(counts: list[int]) -> dict[str, float | int]:
        tp, fp, fn = counts
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        return {
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "micro_precision": precision,
            "micro_recall": recall,
            "micro_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        }

    comparison = {
        "source_system_id": system_id,
        "source_display_label": display_label,
        "episode_ids": ids,
        "direct_summary": direct_summary,
        "structured_summary": structured_summary,
        "exact_accuracy_delta_percentage_points":
            structured_summary["exact_optimal_percentage"] - direct_summary["exact_optimal_percentage"],
        "support_full": edge_summary(full_counts),
        "support_q2": edge_summary(q2_counts),
        "per_block": [],
    }
    for block in ("D04", "D05", "D06", "D12"):
        direct_count = direct_summary["exact_by_block"][block]
        structured_count = structured_summary["exact_by_block"][block]
        comparison["per_block"].append(
            {
                "block_id": block,
                "direct_exact": direct_count,
                "structured_exact": structured_count,
                "delta_percentage_points": 20 * (structured_count - direct_count),
            }
        )
    return structured_summary, details, comparison, direct_details


def run(root: Path, output_root: Path) -> None:
    public, labels = load_benchmark(root)
    direct, support, alignment = parse_responses(root)
    baselines = deterministic_baselines(public)
    summaries: list[dict[str, Any]] = []
    per_item: list[dict[str, Any]] = []
    for system_id, predictions in baselines.items():
        display = {
            "sha256_random_portfolio": "SHA-256 deterministic draw",
            "public_text_char_tfidf_facility": "Character TF-IDF",
        }[system_id]
        summary, details = score_predictions(system_id, display, predictions, public, labels)
        summaries.append(summary)
        per_item.extend(details)
    for system_id, display, _ in [MODELS[0], XHIGH_MODEL, *MODELS[1:]]:
        summary, details = score_predictions(
            system_id, display, direct[system_id]["predictions"], public, labels
        )
        summaries.append(summary)
        per_item.extend(details)
    structured_summary, structured_details, comparison, matched_direct_details = structured_diagnostic(
        "gpt_sol_5_6_pro", "GPT SOL 5.6 Pro", support, direct, public, labels
    )
    per_item.extend(matched_direct_details)
    per_item.extend(structured_details)
    xhigh_structured, xhigh_structured_details, xhigh_comparison, xhigh_matched_details = structured_diagnostic(
        "gpt_sol_5_6_xhigh", "GPT SOL 5.6 (xhigh)", support, direct, public, labels
    )
    per_item.extend(xhigh_matched_details)
    per_item.extend(xhigh_structured_details)
    development_report, development_details = development_evidence(root)
    report = {
        "schema_version": "lemma-portfolio.score-report.v4.two-pdf-capture-v2",
        "benchmark_id": BENCHMARK_ID,
        "episode_count": len(public),
        "selection_budget": SELECTION_BUDGET,
        "source_hashes": {
            "public_sha256": PUBLIC_SHA256,
            "labels_sha256": LABELS_SHA256,
            "response_pdf_sha256": SOURCE_PDF_SHA256,
            "response_text_sha256": SOURCE_TEXT_SHA256,
            "xhigh_response_pdf_sha256": XHIGH_SOURCE_PDF_SHA256,
            "xhigh_response_text_sha256": XHIGH_SOURCE_TEXT_SHA256,
        },
        "uniform_random_analytic": random_expectation(labels),
        "rows": summaries,
        "structured_row": structured_summary,
        "structured_rows": [structured_summary, xhigh_structured],
    }
    dump_json(output_root / "responses/direct_transcription.json", direct)
    dump_json(output_root / "responses/support_transcription.json", support)
    dump_json(output_root / "responses/alignment_audit.json", alignment)
    dump_json(output_root / "results/baseline_predictions.json", baselines)
    dump_json(output_root / "results/scores.json", report)
    dump_json(output_root / "results/structured_comparison.json", comparison)
    dump_json(output_root / "results/xhigh_structured_comparison.json", xhigh_comparison)
    dump_jsonl(output_root / "results/per_item.jsonl", per_item)
    dump_json(output_root / "results/development_score.json", development_report)
    dump_jsonl(output_root / "results/development_per_item.jsonl", development_details)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    output = (args.output_root or root).resolve()
    run(root, output)
    print(f"Reconstructed and scored LemmaPortfolio V4 into {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
