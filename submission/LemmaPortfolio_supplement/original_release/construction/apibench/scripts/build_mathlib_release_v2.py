#!/usr/bin/env python3
"""Materialize and verify the prospective Mathlib-30 v2 holdout.

V2 is not a relabeling of v1. It mines the first 30 successful modules under a
new fixed seed and the strict-current construction profile after excluding the
exact 30 v1 development modules. Public rows use one canonical exact-two task.
The label bytes are evaluator-held until all v2 responses are frozen; only
their SHA-256 commitment belongs in the pre-inference public manifest.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

try:
    from . import mine_mathlib_portfolios as miner
    from .audit_mathlib_generation_v1 import verify_input_files
except ImportError:  # Direct script execution.
    import mine_mathlib_portfolios as miner
    from audit_mathlib_generation_v1 import verify_input_files


APIBENCH_ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = APIBENCH_ROOT / "releases/lemma_portfolio_mathlib_30_v2"
PUBLIC_PATH = RELEASE_ROOT / "public.jsonl"
MANIFEST_PATH = RELEASE_ROOT / "manifest.json"
RECEIPT_PATH = RELEASE_ROOT / "generation_receipt.json"
EXCLUSIONS_PATH = RELEASE_ROOT / "v1_module_exclusions.json"
HARD_NEGATIVE_PROFILE_PATH = RELEASE_ROOT / "hard_negative_profile_v2.json"
LEAN_QUALITY_EXCLUSIONS_PATH = RELEASE_ROOT / "lean_quality_exclusions_v2.json"
DIRECT_VALUE_AUDIT_RECEIPT_PATH = RELEASE_ROOT / "direct_value_audit_receipt.json"
V1_LABELS_PATH = APIBENCH_ROOT / "pilot/mathlib_labels.jsonl"
V1_RECEIPT_PATH = APIBENCH_ROOT / "pilot/mathlib_generation_receipt_v1.json"
GENERATOR_PATH = APIBENCH_ROOT / "scripts/mine_mathlib_portfolios.py"
HARD_NEGATIVE_AUDIT_PATH = APIBENCH_ROOT / "scripts/audit_mathlib_hard_negatives_v1.py"
DIRECT_VALUE_AUDIT_PATH = APIBENCH_ROOT / "scripts/audit_mathlib_release_v2_direct_values.py"
BUILDER_PATH = Path(__file__).resolve()

BENCHMARK_ID = "lemma-portfolio.mathlib-30.v2"
PUBLIC_SCHEMA = "lemma-portfolio.static.v2"
LABEL_SCHEMA = "lemma-portfolio.static-labels.v2"
V2_SEED = "lemma-portfolio-mathlib-30-v2-2026-08-28"
HARD_NEGATIVE_PROFILE = "public-type-band-v1"
V1_LABELS_SHA256 = "aa80f0ecafb3fda1d56b96707d12e1a21fd5570c9632a444f3344d8296e290ad"
V1_RECEIPT_SHA256 = "fc4057647751c09dd141f876dfc88873685fb5fbbfbbf4a306e13db39498c4e7"
CANONICAL_TASK = (
    "Select exactly two distinct candidate IDs. They are the only candidate "
    "declarations used directly in the original elaborated bodies of the listed "
    "targets. Every target uses at least one of them, and each is used by at least "
    "two targets."
)

PUBLIC_TYPE_TOKEN = re.compile(
    r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*"
)
PUBLIC_STATEMENT_TOKEN = re.compile(
    r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*|:=|=>|[^\s]"
)
PUBLIC_TYPE_STOP = frozenset(
    {"Type", "inst", "fun", "forall", "Prop", "Sort", "true", "false"}
)


class ReleaseError(RuntimeError):
    """A v2 generation, commitment, or release invariant failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path}: expected an object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    _require(all(isinstance(row, dict) for row in rows), f"{path}: non-object row")
    return rows


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def canonical_public_type(type_text: str) -> str:
    """Remove pretty-printer line wrapping without changing Lean token order."""

    return " ".join(type_text.split())


def public_type_tokens(type_text: str) -> frozenset[str]:
    """Tokenize only the public declaration type, without names or docstrings."""

    values: set[str] = set()
    for token in PUBLIC_TYPE_TOKEN.findall(type_text):
        token = token.strip(".'")
        if not token:
            continue
        values.update(
            piece.lower()
            for piece in token.split(".")
            if piece and piece not in PUBLIC_TYPE_STOP
        )
    return frozenset(values)


def normalized_statement_signature(type_text: str) -> tuple[str, ...]:
    """Whitespace-insensitive exact token signature for a public type."""

    return tuple(PUBLIC_STATEMENT_TOKEN.findall(type_text))


def _top_level_colon(text: str) -> int | None:
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    for index, character in enumerate(text):
        if character in pairs:
            depth += 1
        elif character in closers:
            depth -= 1
        elif character == ":" and depth == 0:
            return index
    return None


def _leading_binder_names(type_text: str) -> list[str]:
    """Extract binder identifiers from leading pretty-printed `forall` groups."""

    text = " ".join(type_text.split())
    names: list[str] = []
    while text.startswith("∀ "):
        prefix = text[2:]
        depth = 0
        comma = None
        for index, character in enumerate(prefix):
            if character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character == "," and depth == 0:
                comma = index
                break
        if comma is None:
            break
        binders = prefix[:comma].strip()
        top_level_text: list[str] = []
        index = 0
        while index < len(binders):
            if binders[index] not in "([{":
                top_level_text.append(binders[index])
                index += 1
                continue
            opening = binders[index]
            closing = {"(": ")", "[": "]", "{": "}"}[opening]
            depth = 1
            end = index + 1
            while end < len(binders) and depth:
                if binders[end] == opening:
                    depth += 1
                elif binders[end] == closing:
                    depth -= 1
                end += 1
            if depth:
                break
            content = binders[index + 1 : end - 1]
            colon = _top_level_colon(content)
            if colon is not None:
                names.extend(PUBLIC_TYPE_TOKEN.findall(content[:colon]))
            index = end
        ungrouped = "".join(top_level_text).strip()
        colon = _top_level_colon(ungrouped)
        if ungrouped:
            names.extend(
                PUBLIC_TYPE_TOKEN.findall(
                    ungrouped[:colon] if colon is not None else ungrouped
                )
            )
        text = prefix[comma + 1 :].strip()
    # Pretty-printed universe parameters are implicit rather than ordinary
    # binders.  Canonicalize their conventional unqualified identifiers too.
    for universe in re.findall(r"\bType\s+([A-Za-z_][A-Za-z0-9_]*)", type_text):
        if universe not in names:
            names.append(universe)
    return names


def alpha_normalized_statement_signature(type_text: str) -> tuple[str, ...]:
    """Normalize whitespace and names of leading displayed binders."""

    renaming = {
        name: f"__BOUND_{index}__"
        for index, name in enumerate(dict.fromkeys(_leading_binder_names(type_text)))
    }
    return tuple(
        renaming.get(token, token) for token in PUBLIC_STATEMENT_TOKEN.findall(type_text)
    )


def statements_are_identifiable(
    candidate_types: Sequence[str],
    target_types: Sequence[str],
) -> bool:
    """Reject exact/whitespace or leading-binder-alpha statement collisions."""

    candidate_exact = [normalized_statement_signature(value) for value in candidate_types]
    target_exact_rows = [normalized_statement_signature(value) for value in target_types]
    target_exact = set(target_exact_rows)
    if len(candidate_exact) != len(set(candidate_exact)):
        return False
    if len(target_exact_rows) != len(target_exact):
        return False
    if set(candidate_exact) & target_exact:
        return False
    candidate_alpha = [
        alpha_normalized_statement_signature(value) for value in candidate_types
    ]
    target_alpha_rows = [
        alpha_normalized_statement_signature(value) for value in target_types
    ]
    target_alpha = set(target_alpha_rows)
    return (
        len(candidate_alpha) == len(set(candidate_alpha))
        and len(target_alpha_rows) == len(target_alpha)
        and not set(candidate_alpha) & target_alpha
    )


def _jaccard(left: frozenset[str], right: frozenset[str]) -> Fraction:
    union = left | right
    return Fraction(len(left & right), len(union)) if union else Fraction()


def public_type_portfolio_similarity(
    candidate_type: str,
    target_types: Sequence[str],
) -> Fraction:
    """Exact, frozen public-text score used only to match negative difficulty.

    The first term is the mean of the two largest token-set Jaccard scores; the
    second is half the mean over the complete target portfolio.  Fractions avoid
    platform-dependent floating-point ties.
    """

    _require(len(target_types) >= 2, "hard-negative similarity needs two targets")
    candidate = public_type_tokens(candidate_type)
    similarities = sorted(
        (_jaccard(candidate, public_type_tokens(target)) for target in target_types),
        reverse=True,
    )
    return (
        sum(similarities[:2], Fraction()) / 2
        + sum(similarities, Fraction()) / (2 * len(similarities))
    )


def _distance_to_band(score: Fraction, low: Fraction, high: Fraction) -> Fraction:
    if score < low:
        return low - score
    if score > high:
        return score - high
    return Fraction()


def select_hard_negatives(
    *,
    declarations: dict[str, miner.Declaration],
    eligible_pool: Sequence[str],
    helper_names: Sequence[str],
    target_names: Sequence[str],
    module: str,
    seed: str,
    count: int = 10,
) -> list[str] | None:
    """Select public-type-matched negatives with two anti-signal anchors.

    One selected negative must score strictly above the lower-scoring helper and
    a different selected negative strictly below the higher-scoring helper.  The
    rest minimize exact distance to the closed helper-similarity band.  This
    prevents the two reference declarations from being the score's top two or
    bottom two.  Every tie is resolved by a domain-separated seed hash.
    """

    _require(len(helper_names) == 2, "hard-negative profile requires two helpers")
    _require(count >= 2, "hard-negative profile requires two anchors")
    target_types = [declarations[name].type for name in target_names]
    helper_scores = [
        public_type_portfolio_similarity(declarations[name].type, target_types)
        for name in helper_names
    ]
    low, high = min(helper_scores), max(helper_scores)
    scored = [
        (
            public_type_portfolio_similarity(declarations[name].type, target_types),
            name,
        )
        for name in eligible_pool
    ]
    above_low = [item for item in scored if item[0] > low]
    below_high = [item for item in scored if item[0] < high]
    if not above_low or not below_high:
        return None
    above_low.sort(
        key=lambda item: (
            item[0] - low,
            miner.stable_token(seed, module, "hard-negative-above-low", item[1]),
        )
    )
    below_high.sort(
        key=lambda item: (
            high - item[0],
            miner.stable_token(seed, module, "hard-negative-below-high", item[1]),
        )
    )
    chosen: list[tuple[Fraction, str]] = [above_low[0]]
    lower_anchor = next(
        (item for item in below_high if item[1] != chosen[0][1]),
        None,
    )
    if lower_anchor is None:
        return None
    chosen.append(lower_anchor)
    chosen_names = {name for _score, name in chosen}
    remainder = [item for item in scored if item[1] not in chosen_names]
    midpoint = (low + high) / 2
    remainder.sort(
        key=lambda item: (
            _distance_to_band(item[0], low, high),
            abs(item[0] - midpoint),
            miner.stable_token(seed, module, "hard-negative-band", item[1]),
        )
    )
    chosen.extend(remainder[: count - len(chosen)])
    if len(chosen) != count:
        return None
    negative_scores = [score for score, _name in chosen]
    _require(any(score > low for score in negative_scores), "missing upper anchor")
    _require(any(score < high for score in negative_scores), "missing lower anchor")
    return [name for _score, name in chosen]


def load_excluded_modules() -> list[str]:
    value = load_json(EXCLUSIONS_PATH)
    _require(
        value.get("schema_version") == "lemma-portfolio.module-exclusions.v2",
        "exclusion schema mismatch",
    )
    _require(value.get("derived_from_labels_sha256") == V1_LABELS_SHA256, "v1 label binding")
    modules = value.get("modules")
    _require(
        isinstance(modules, list)
        and len(modules) == len(set(modules)) == 30
        and all(isinstance(module, str) and module for module in modules),
        "exclusion list must contain 30 distinct module names",
    )
    v1_labels = load_jsonl(V1_LABELS_PATH)
    _require(
        set(modules) == {row["source_module"] for row in v1_labels},
        "exclusion list is not exactly the v1 module set",
    )
    _require(modules == sorted(modules), "exclusion list must be lexically sorted")
    return modules


def validate_hard_negative_profile() -> dict[str, Any]:
    value = load_json(HARD_NEGATIVE_PROFILE_PATH)
    _require(
        value.get("schema_version") == "lemma-portfolio.hard-negative-profile.v2",
        "hard-negative profile schema mismatch",
    )
    _require(value.get("profile") == HARD_NEGATIVE_PROFILE, "hard-negative profile mismatch")
    _require(
        value.get("status")
        == "frozen_from_v1_development_evidence_before_v2_hard-negative_materialization",
        "hard-negative profile was not frozen prospectively",
    )
    design_data = value.get("design_data")
    diagnostic = value.get("v1_design_diagnostic")
    _require(isinstance(design_data, dict), "hard-negative design data missing")
    _require(isinstance(diagnostic, dict), "hard-negative diagnostic missing")
    _require(design_data.get("v1_labels_sha256") == V1_LABELS_SHA256, "profile v1 labels")
    _require(design_data.get("v2_model_outputs_read") == 0, "profile used v2 outputs")
    _require(
        diagnostic.get("episodes_accepted") == 28
        and diagnostic.get("episodes_rejected_fail_closed") == 2,
        "hard-negative v1 acceptance diagnostic changed",
    )
    return value


def load_lean_quality_exclusions() -> set[str]:
    value = load_json(LEAN_QUALITY_EXCLUSIONS_PATH)
    _require(
        value.get("schema_version") == "lemma-portfolio.lean-quality-exclusions.v2",
        "Lean quality-exclusion schema mismatch",
    )
    _require(value.get("benchmark_id") == BENCHMARK_ID, "quality-exclusion benchmark")
    _require(value.get("v2_model_outputs_read") == 0, "quality exclusion used model output")
    hashes = value.get("excluded_module_sha256")
    _require(
        isinstance(hashes, list)
        and len(hashes) == len(set(hashes)) == 1
        and all(
            isinstance(item, str)
            and len(item) == 64
            and set(item) <= set("0123456789abcdef")
            for item in hashes
        ),
        "quality-exclusion hashes are invalid",
    )
    return set(hashes)


def _canonicalize_episode(
    public: dict[str, Any],
    labels: dict[str, Any],
    index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    episode_id = f"MLP2_{index:04d}"
    public = dict(public)
    labels = dict(labels)
    public.pop("source_module_hash", None)
    public.pop("budget", None)
    public["benchmark_id"] = BENCHMARK_ID
    public["episode_id"] = episode_id
    public["schema_version"] = PUBLIC_SCHEMA
    public["task"] = CANONICAL_TASK
    public["candidates"] = [
        {
            "id": candidate["id"],
            "statement": canonical_public_type(candidate["statement"]),
        }
        for candidate in public["candidates"]
    ]
    public["targets"] = [
        {**target, "statement": canonical_public_type(target["statement"])}
        for target in public["targets"]
    ]
    labels["benchmark_id"] = BENCHMARK_ID
    labels["episode_id"] = episode_id
    labels["schema_version"] = LABEL_SCHEMA
    return public, labels


def _apply_hard_negative_profile(
    *,
    public: dict[str, Any],
    labels: dict[str, Any],
    declarations: dict[str, miner.Declaration],
    edges: dict[str, frozenset[str]],
    module: str,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Replace seed-random negatives while preserving helpers and target order."""

    candidate_sources = labels["candidate_sources"]
    target_sources = labels["target_sources"]
    helper_names = [candidate_sources[item] for item in labels["oracle_helpers"]]
    target_names = [target_sources[target["id"]] for target in public["targets"]]
    target_set = set(target_names)
    helper_set = set(helper_names)
    target_types = [canonical_public_type(declarations[name].type) for name in target_names]
    if any(
        miner.name_visible_in_type(helper, statement)
        for helper in helper_names
        for statement in target_types
    ) or any(
        miner.name_visible_in_type(helper, declarations[helper].type)
        for helper in helper_names
    ):
        return None
    used_by_targets = set().union(*(edges[target] for target in target_names))
    module_names = sorted(
        name
        for name, declaration in declarations.items()
        if declaration.module == module and name in edges
    )
    eligible_pool = [
        name
        for name in module_names
        if name not in target_set
        and name not in helper_set
        and name not in used_by_targets
        and not any(
            miner.name_visible_in_type(name, statement) for statement in target_types
        )
        and not miner.name_visible_in_type(name, declarations[name].type)
    ]
    negative_names = select_hard_negatives(
        declarations=declarations,
        eligible_pool=eligible_pool,
        helper_names=helper_names,
        target_names=target_names,
        module=module,
        seed=V2_SEED,
    )
    if negative_names is None:
        return None
    _require(
        not set(negative_names) & used_by_targets,
        "hard-negative profile selected a direct target dependency",
    )
    candidate_names = helper_names + negative_names
    candidate_names.sort(
        key=lambda name: miner.stable_token(V2_SEED, module, "candidate-order", name)
    )
    if not statements_are_identifiable(
        [declarations[name].type for name in candidate_names],
        target_types,
    ):
        return None
    public_types = [declarations[name].type for name in candidate_names] + target_types
    if any(
        miner.name_visible_in_type(source_name, statement)
        for source_name in candidate_names + target_names
        for statement in public_types
    ):
        return None
    candidate_id = {
        name: f"C{index + 1:02d}" for index, name in enumerate(candidate_names)
    }
    target_id = {name: row["id"] for name, row in zip(target_names, public["targets"], strict=True)}
    hardened_public = dict(public)
    hardened_public["candidates"] = [
        {
            "id": candidate_id[name],
            "statement": canonical_public_type(declarations[name].type),
        }
        for name in candidate_names
    ]
    hardened_labels = dict(labels)
    hardened_labels["candidate_sources"] = {
        candidate_id[name]: name for name in candidate_names
    }
    hardened_labels["oracle_helpers"] = sorted(
        candidate_id[name] for name in helper_names
    )
    hardened_labels["targets"] = [
        {
            "id": target_id[name],
            "required_candidates": sorted(
                candidate_id[helper]
                for helper in helper_names
                if helper in edges[name]
            ),
        }
        for name in target_names
    ]
    return hardened_public, hardened_labels


def mine_v2(
    declarations: dict[str, miner.Declaration],
    excluded_modules: Sequence[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validate_hard_negative_profile()
    quality_exclusions = load_lean_quality_exclusions()
    edges = miner.proof_only_edges(
        declarations,
        generation_profile=miner.STRICT_GENERATION_PROFILE,
    )
    modules = sorted(
        {declaration.module for declaration in declarations.values()},
        key=lambda module: miner.stable_token(V2_SEED, module),
    )
    excluded = set(excluded_modules)
    public_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for module in modules:
        if module in excluded:
            continue
        if hashlib.sha256(module.encode("utf-8")).hexdigest() in quality_exclusions:
            continue
        result = miner.choose_episode(
            module,
            declarations,
            edges,
            seed=V2_SEED,
            episode_index=len(public_rows),
            candidate_count=12,
            target_count=6,
            budget=2,
        )
        if result is None:
            continue
        hardened = _apply_hard_negative_profile(
            public=result[0],
            labels=result[1],
            declarations=declarations,
            edges=edges,
            module=module,
        )
        if hardened is None:
            continue
        public, labels = _canonicalize_episode(*hardened, len(public_rows))
        public_rows.append(public)
        label_rows.append(labels)
        if len(public_rows) == 30:
            break
    _require(len(public_rows) == 30, "fewer than 30 v2 episodes were generated")
    validate_release(public_rows, label_rows, excluded)
    return public_rows, label_rows


def _portfolio_objective(
    pair: tuple[str, str],
    requirements: Sequence[set[str]],
) -> tuple[int, int]:
    selected = set(pair)
    covered = [
        index
        for index, required in enumerate(requirements)
        if required and required <= selected
    ]
    reused = {
        candidate
        for candidate in selected
        if sum(candidate in requirements[index] for index in covered) >= 2
    }
    return (
        sum(bool(requirements[index] & reused) for index in covered),
        len(covered),
    )


def validate_release(
    public_rows: Sequence[dict[str, Any]],
    label_rows: Sequence[dict[str, Any]],
    excluded_modules: set[str],
) -> dict[str, Any]:
    expected_episode_ids = [f"MLP2_{index:04d}" for index in range(30)]
    _require([row["episode_id"] for row in public_rows] == expected_episode_ids, "public ID order")
    _require([row["episode_id"] for row in label_rows] == expected_episode_ids, "label ID order")
    modules: list[str] = []
    target_distribution: dict[str, int] = {"4": 0, "5": 0, "6": 0}
    total_targets = 0
    anti_signal_passes = 0
    visible_source_name_statement_pairs = 0
    statement_identity_passes = 0
    for public, labels in zip(public_rows, label_rows, strict=True):
        episode_id = public["episode_id"]
        _require(public.get("benchmark_id") == BENCHMARK_ID, f"{episode_id}: benchmark ID")
        _require(public.get("schema_version") == PUBLIC_SCHEMA, f"{episode_id}: public schema")
        _require(public.get("task") == CANONICAL_TASK, f"{episode_id}: task text")
        _require("at most" not in public["task"].lower(), f"{episode_id}: legacy wording")
        _require("most useful" not in public["task"].lower(), f"{episode_id}: subjective wording")
        _require("return" not in public["task"].lower(), f"{episode_id}: output-envelope wording")
        _require("json" not in public["task"].lower(), f"{episode_id}: row-local JSON wording")
        _require(labels.get("benchmark_id") == BENCHMARK_ID, f"{episode_id}: label benchmark")
        _require(labels.get("schema_version") == LABEL_SCHEMA, f"{episode_id}: label schema")
        _require("budget" not in public, f"{episode_id}: legacy budget field")
        candidates = public.get("candidates")
        targets = public.get("targets")
        _require(isinstance(candidates, list) and len(candidates) == 12, f"{episode_id}: candidates")
        _require(isinstance(targets, list) and len(targets) in {4, 5, 6}, f"{episode_id}: targets")
        candidate_ids = [f"C{index:02d}" for index in range(1, 13)]
        target_ids = [f"T{index:02d}" for index in range(1, len(targets) + 1)]
        _require([row.get("id") for row in candidates] == candidate_ids, f"{episode_id}: candidate IDs")
        _require([row.get("id") for row in targets] == target_ids, f"{episode_id}: target IDs")
        _require(
            all(
                set(row) == {"id", "statement"}
                and isinstance(row.get("statement"), str)
                for row in candidates
            ),
            f"{episode_id}: candidate payload",
        )
        _require(
            all(
                set(row) == {"id", "statement"}
                and isinstance(row.get("statement"), str)
                and row["statement"]
                for row in targets
            ),
            f"{episode_id}: target payload",
        )
        _require(
            all(
                row["statement"] == canonical_public_type(row["statement"])
                for row in list(candidates) + list(targets)
            ),
            f"{episode_id}: public statement whitespace is not canonical",
        )
        _require(
            statements_are_identifiable(
                [row["statement"] for row in candidates],
                [row["statement"] for row in targets],
            ),
            f"{episode_id}: normalized or alpha-equivalent statement collision",
        )
        statement_identity_passes += 1
        _require(
            not any(miner.obviously_reflexive(row["statement"]) for row in candidates + targets),
            f"{episode_id}: strict reflexivity rejection failed",
        )
        _require(set(public) == {
            "benchmark_id", "candidates", "episode_id", "schema_version",
            "source_project", "targets", "task",
        }, f"{episode_id}: public field leakage")
        _require(public["source_project"] == "mathlib", f"{episode_id}: source project")
        _require(set(labels) == {
            "benchmark_id", "candidate_sources", "episode_id", "oracle_helpers",
            "schema_version", "source_module", "target_sources", "targets",
        }, f"{episode_id}: label fields")
        module = labels["source_module"]
        _require(module not in excluded_modules, f"{episode_id}: v1 module overlap")
        modules.append(module)
        oracle = labels["oracle_helpers"]
        _require(
            isinstance(oracle, list)
            and len(oracle) == len(set(oracle)) == 2
            and set(oracle) <= set(candidate_ids),
            f"{episode_id}: reference pair",
        )
        target_types = [target["statement"] for target in targets]
        candidate_similarity = {
            candidate["id"]: public_type_portfolio_similarity(
                candidate["statement"], target_types
            )
            for candidate in candidates
        }
        helper_scores = [candidate_similarity[item] for item in oracle]
        negative_scores = [
            score
            for candidate, score in candidate_similarity.items()
            if candidate not in set(oracle)
        ]
        low, high = min(helper_scores), max(helper_scores)
        _require(
            any(score > low for score in negative_scores),
            f"{episode_id}: gold pair is a high-similarity lexical signal",
        )
        _require(
            any(score < high for score in negative_scores),
            f"{episode_id}: gold pair is a low-similarity lexical signal",
        )
        anti_signal_passes += 1
        all_source_names = list(labels["candidate_sources"].values()) + list(
            labels["target_sources"].values()
        )
        public_statements = [
            row["statement"] for row in list(candidates) + list(targets)
        ]
        episode_visible_pairs = sum(
            miner.name_visible_in_type(source_name, statement)
            for source_name in all_source_names
            for statement in public_statements
        )
        visible_source_name_statement_pairs += episode_visible_pairs
        _require(
            episode_visible_pairs == 0,
            f"{episode_id}: a private source name is visible in public types",
        )
        label_targets = labels["targets"]
        _require([row["id"] for row in label_targets] == target_ids, f"{episode_id}: label target order")
        requirements = [set(row["required_candidates"]) for row in label_targets]
        _require(all(requirements), f"{episode_id}: a target has no reference use")
        active = {candidate for required in requirements for candidate in required}
        _require(active == set(oracle), f"{episode_id}: active candidates differ from reference")
        _require(
            all(sum(candidate in required for required in requirements) >= 2 for candidate in oracle),
            f"{episode_id}: reference candidate is not reused",
        )
        scores = [
            (_portfolio_objective(pair, requirements), frozenset(pair))
            for pair in itertools.combinations(candidate_ids, 2)
        ]
        best = max(score for score, _pair in scores)
        _require(
            [pair for score, pair in scores if score == best] == [frozenset(oracle)],
            f"{episode_id}: reference pair is not the unique optimum",
        )
        target_distribution[str(len(targets))] += 1
        total_targets += len(targets)
    _require(len(modules) == len(set(modules)) == 30, "v2 modules must be distinct")
    _require(visible_source_name_statement_pairs == 0, "source-name leakage")
    return {
        "episodes": 30,
        "distinct_modules": 30,
        "candidates_per_episode": 12,
        "target_count_distribution": target_distribution,
        "total_targets": total_targets,
        "strict_reflexive_declarations": 0,
        "hard_negative_profile": HARD_NEGATIVE_PROFILE,
        "hard_negative_anti_signal_passes": anti_signal_passes,
        "distractors_per_episode": 10,
        "source_name_public_statement_matrix_visible_pairs": 0,
        "statement_identifiability_passes": statement_identity_passes,
        "normalized_or_alpha_statement_collisions": 0,
        "lean_quality_excluded_draft_modules": len(load_lean_quality_exclusions()),
        "unique_reference_pairs": 30,
        "v1_module_overlap": 0,
    }


def declarations_from_parquets(parquet_dir: Path) -> dict[str, miner.Declaration]:
    v1_receipt = load_json(V1_RECEIPT_PATH)
    dependencies, types = verify_input_files(parquet_dir, v1_receipt)
    return miner.load_declarations(dependencies, types)


def materialize(parquet_dir: Path, public_out: Path, labels_out: Path) -> dict[str, Any]:
    _require(not public_out.exists(), "refusing to overwrite public output")
    _require(not labels_out.exists(), "refusing to overwrite sealed labels")
    declarations = declarations_from_parquets(parquet_dir)
    excluded = load_excluded_modules()
    public, labels = mine_v2(declarations, excluded)
    public_bytes = jsonl_bytes(public)
    label_bytes = jsonl_bytes(labels)
    public_out.parent.mkdir(parents=True, exist_ok=True)
    labels_out.parent.mkdir(parents=True, exist_ok=True)
    public_out.write_bytes(public_bytes)
    labels_out.write_bytes(label_bytes)
    summary = validate_release(public, labels, set(excluded))
    return {
        "status": "materialized",
        "declarations": len(declarations),
        "public_path": str(public_out),
        "public_sha256": sha256_bytes(public_bytes),
        "labels_path": str(labels_out),
        "labels_sha256": sha256_bytes(label_bytes),
        "summary": summary,
    }


def check_release(parquet_dir: Path | None, labels_path: Path | None) -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH)
    receipt = load_json(RECEIPT_PATH)
    direct_value_receipt = load_json(DIRECT_VALUE_AUDIT_RECEIPT_PATH)
    excluded = load_excluded_modules()
    _require(manifest.get("schema_version") == "lemma-portfolio.release-manifest.v2", "manifest schema")
    _require(receipt.get("schema_version") == "lemma-portfolio.generation-receipt.v2", "receipt schema")
    _require(manifest.get("benchmark_id") == BENCHMARK_ID, "manifest benchmark ID")
    _require(receipt.get("benchmark_id") == BENCHMARK_ID, "receipt benchmark ID")
    _require(
        manifest.get("release_status") == "FINAL_FROZEN_PREINFERENCE",
        "manifest is not a final pre-inference freeze",
    )
    _require(
        receipt.get("release_status") == "FINAL_FROZEN_PREINFERENCE",
        "receipt is not a final pre-inference freeze",
    )
    _require(manifest.get("model_results") == [], "pre-inference release cannot carry results")
    _require(receipt["prospective_status"]["v2_model_inference_started"] is False, "receipt is not pre-inference")
    hashes = receipt["hashes"]
    _require(hashes["builder_sha256"] == sha256_path(BUILDER_PATH), "builder hash")
    _require(hashes["generator_sha256"] == sha256_path(GENERATOR_PATH), "generator hash")
    _require(
        hashes["hard_negative_design_audit_script_sha256"]
        == sha256_path(HARD_NEGATIVE_AUDIT_PATH),
        "hard-negative design audit script hash",
    )
    _require(
        hashes["direct_value_audit_script_sha256"]
        == sha256_path(DIRECT_VALUE_AUDIT_PATH),
        "direct-value audit script hash",
    )
    _require(hashes["v1_receipt_sha256"] == V1_RECEIPT_SHA256, "v1 receipt binding")
    _require(hashes["v1_labels_sha256"] == V1_LABELS_SHA256, "v1 labels binding")
    _require(hashes["exclusions_sha256"] == sha256_path(EXCLUSIONS_PATH), "exclusion hash")
    _require(
        hashes["lean_quality_exclusions_sha256"]
        == sha256_path(LEAN_QUALITY_EXCLUSIONS_PATH),
        "Lean quality-exclusion hash",
    )
    _require(
        hashes["hard_negative_profile_sha256"]
        == sha256_path(HARD_NEGATIVE_PROFILE_PATH),
        "hard-negative profile hash",
    )
    _require(
        hashes["direct_value_audit_receipt_sha256"]
        == sha256_path(DIRECT_VALUE_AUDIT_RECEIPT_PATH),
        "direct-value audit receipt hash",
    )
    _require(hashes["public_sha256"] == sha256_path(PUBLIC_PATH), "public receipt hash")
    _require(manifest["hashes"]["public_sha256"] == sha256_path(PUBLIC_PATH), "public manifest hash")
    _require(manifest["hashes"]["label_commitment_sha256"] == hashes["labels_sha256"], "label commitment")
    _require(manifest["hashes"]["generation_receipt_sha256"] == sha256_path(RECEIPT_PATH), "receipt hash")
    _require(
        manifest["hashes"]["direct_value_audit_receipt_sha256"]
        == sha256_path(DIRECT_VALUE_AUDIT_RECEIPT_PATH),
        "manifest direct-value receipt hash",
    )
    _require(manifest.get("canonical_task") == CANONICAL_TASK, "manifest canonical task")
    _require(manifest.get("official_metric") == "exact_pair_accuracy", "manifest metric")
    _require(
        direct_value_receipt.get("status") == "pass"
        and direct_value_receipt.get("benchmark_id") == BENCHMARK_ID,
        "direct-value audit did not pass",
    )
    _require(
        direct_value_receipt["inputs"]["public_sha256"] == hashes["public_sha256"]
        and direct_value_receipt["inputs"]["labels_sha256"] == hashes["labels_sha256"],
        "direct-value audit input binding",
    )
    construction_audits = receipt["construction_audits"]
    _require(
        construction_audits["candidate_candidate_normalized_or_alpha_duplicates"] == 0,
        "candidate statement collision audit",
    )
    _require(
        construction_audits["candidate_target_normalized_or_alpha_identities"] == 0,
        "candidate-target statement collision audit",
    )
    _require(
        construction_audits["source_name_public_statement_matrix_visible_pairs"] == 0,
        "source-name leakage audit",
    )
    public = load_jsonl(PUBLIC_PATH)
    label_rows: list[dict[str, Any]] | None = None
    if labels_path is not None:
        _require(sha256_path(labels_path) == hashes["labels_sha256"], "sealed label hash")
        label_rows = load_jsonl(labels_path)
        summary = validate_release(public, label_rows, set(excluded))
        _require(summary == receipt["construction_summary"], "receipt construction summary")
    else:
        _require(len(public) == 30, "public episode count")
        _require(all(row.get("task") == CANONICAL_TASK for row in public), "public task text")
        _require(
            all("source_module_hash" not in row and "source_module" not in row for row in public),
            "public module provenance leakage",
        )
        _require(
            all(
                statements_are_identifiable(
                    [item["statement"] for item in row["candidates"]],
                    [item["statement"] for item in row["targets"]],
                )
                for row in public
            ),
            "public statement collision",
        )
        summary = receipt["construction_summary"]
    if parquet_dir is not None:
        _require(label_rows is not None, "full Parquet replay requires --labels")
        replay_public, replay_labels = mine_v2(
            declarations_from_parquets(parquet_dir),
            excluded,
        )
        _require(jsonl_bytes(replay_public) == PUBLIC_PATH.read_bytes(), "public replay mismatch")
        _require(jsonl_bytes(replay_labels) == labels_path.read_bytes(), "label replay mismatch")
    return {
        "status": "ok",
        "benchmark_id": BENCHMARK_ID,
        "public_sha256": hashes["public_sha256"],
        "label_commitment_sha256": hashes["labels_sha256"],
        "labels_opened": labels_path is not None,
        "full_parquet_replay": parquet_dir is not None,
        "model_results": 0,
        "construction_summary": summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet-dir", type=Path)
    parser.add_argument("--labels", type=Path, help="evaluator-held labels for private/full checks")
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--public-out", type=Path)
    parser.add_argument("--labels-out", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.materialize:
            _require(args.parquet_dir is not None, "--materialize requires --parquet-dir")
            _require(args.public_out is not None, "--materialize requires --public-out")
            _require(args.labels_out is not None, "--materialize requires --labels-out")
            result = materialize(args.parquet_dir, args.public_out, args.labels_out)
        else:
            result = check_release(args.parquet_dir, args.labels)
    except (KeyError, OSError, RuntimeError, UnicodeError, ValueError) as error:
        raise SystemExit(f"v2 release check failed: {error}") from error
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
