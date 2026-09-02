#!/usr/bin/env python3
"""Mine and freeze LemmaPortfolio v4 as dependency-portfolio compression.

Each episode displays K=16 candidate theorem statements and eight target
statements. The hidden incidence set D(t) is the intersection of a target's
direct elaborated proof-body constants with those sixteen candidates. A model
selects B=3 candidates and is evaluated by

    F(S) = |{t : D(t) intersects S}|.

All size-three maximizers are accepted. This is a historical dependency-
coverage surrogate; it is not a causal claim that inserting a declaration
would improve a prover.

The builder reads no model output. It excludes all v1--v3 source modules and
statement signatures, requires a genuinely combinatorial active incidence
graph, applies fixed construction diagnostics, and produces a disjoint
calibration split plus a larger blind split. Private labels are
written with mode 0600 and public files expose only their SHA-256 commitments.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

try:
    from apibench.hard_blind_v4 import construction_diagnostics
    from apibench.scripts import build_mathlib_release_v2 as common
    from apibench.scripts import mine_mathlib_portfolios as miner
except ImportError:  # Direct execution from this directory.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from apibench.hard_blind_v4 import construction_diagnostics
    from apibench.scripts import build_mathlib_release_v2 as common
    from apibench.scripts import mine_mathlib_portfolios as miner


APIBENCH_ROOT = Path(__file__).resolve().parents[1]
V1_PUBLIC = APIBENCH_ROOT / "pilot/mathlib_public.jsonl"
V1_LABELS = APIBENCH_ROOT / "pilot/mathlib_labels.jsonl"
V2_PUBLIC = APIBENCH_ROOT / "releases/lemma_portfolio_mathlib_30_v2/public.jsonl"
V2_MODULE_HASHES = (
    APIBENCH_ROOT
    / "releases/lemma_portfolio_mathlib_30_v3/v2_module_exclusions.json"
)
V3_PUBLIC = APIBENCH_ROOT / "releases/lemma_portfolio_mathlib_30_v3/public.jsonl"
V3_LABELS = APIBENCH_ROOT / "releases/lemma_portfolio_mathlib_30_v3/labels.jsonl"

SEED = "lemma-portfolio-dependency-compression-v4-2026-09-01"
PUBLIC_SCHEMA = "lemma-portfolio.dependency-compression.v4"
LABEL_SCHEMA = "lemma-portfolio.dependency-compression-labels.v4"
CALIBRATION_ID = "lemma-portfolio.mathlib-compression-calibration-30.v4"
BLIND_ID = "lemma-portfolio.mathlib-compression-blind-60.v4"
CALIBRATION_COUNT = 30
BLIND_COUNT = 60
K = 16
B = 3
TARGET_COUNT = 8
MIN_RECURRENT_USES = 2
MIN_ACTIVE_CANDIDATES = 7
MIN_NONOPTIMAL_ACTIVE = 4
MIN_NEAR_OPTIMAL = 2
MIN_MULTI_EDGE_TARGETS = 2
MAX_SINGLETON_COVERAGE = 4
MIN_OPTIMAL_COVERAGE = 6
MAX_OPTIMAL_PORTFOLIOS = 32
MAX_DOMAIN_CALIBRATION = 5
MAX_DOMAIN_BLIND = 10
CALIBRATION_TRIAL_LIMIT = 28
COHORT_TRIALS = 32
TARGET_SEED_TRIALS = 32
PINNED_LEAN_EXCLUDED_MODULE_HASHES = frozenset(
    {"f22caa542e02fac9b7c2bc447b23a9fa32f7f9d60c907904c99917c6873b5684"}
)
FROZEN_CALIBRATION_PUBLIC_SHA256 = (
    "404452daa5017793d9f7b10f4d92716d2bb267dca034094b0f41f8c8d9219ffc"
)
FROZEN_CALIBRATION_LABELS_SHA256 = (
    "bee487259392de4d36b2140a715c7b4196ce7cc2027c3b13c90e1874a19149d0"
)
PINNED_LEAN_PREFLIGHT_BLIND_PUBLIC_SHA256 = (
    "b54293b08bc7ddbb7110a50908049922f7cfd86f14cb49a4de4e28353aecc6d8"
)
PINNED_LEAN_PREFLIGHT_BLIND_LABELS_SHA256 = (
    "d17c1fd5c6d87635daf8035fe4a0918d1eaa29708eae37cb797cae08c19ef887"
)

CANONICAL_TASK = (
    "Among the displayed candidates, select exactly three distinct candidate IDs "
    "to cover as many targets as possible. The displayed candidates are exactly "
    "the in-pool candidate declarations; a target may have other nondisplayed "
    "dependencies. A target is covered when at least one selected candidate was "
    "used directly in that target's original elaborated proof body. Return only "
    "the three selected IDs."
)

TOKEN = re.compile(
    r"[A-Za-z_\u0080-\uffff][A-Za-z0-9_\u0080-\uffff'.]*|:=|=>|[^\s]"
)
CONNECTIVES = ("=", "≠", "→", "↔", "∧", "∨", "¬", "≤", "≥", "<", ">")
DRAFT_REJECTIONS: Counter[str] = Counter()
DRAFT_FUNNEL: Counter[str] = Counter()
MINING_COUNTS: Counter[str] = Counter()


class HardBlindError(RuntimeError):
    """A fail-closed v4 construction or validation invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HardBlindError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verified_parquet_inventory(parquet_dir: Path) -> list[dict[str, Any]]:
    """Re-hash every current shard and fail unless it matches the v1 receipt."""

    receipt = json.loads(common.V1_RECEIPT_PATH.read_text(encoding="utf-8"))
    expected = receipt.get("parquet_inputs")
    require(isinstance(expected, list) and len(expected) == 256, "Parquet receipt count")
    expected_names = [row.get("name") for row in expected if isinstance(row, dict)]
    require(len(expected_names) == 256, "invalid Parquet receipt rows")
    actual_names = sorted(path.name for path in parquet_dir.glob("*.parquet"))
    require(actual_names == sorted(expected_names), "Parquet directory file set mismatch")
    actual: list[dict[str, Any]] = []
    for expected_row in expected:
        name = expected_row["name"]
        path = parquet_dir / name
        row = {
            "name": name,
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        }
        require(row == expected_row, f"Parquet receipt mismatch: {name}")
        actual.append(row)
    require(
        sum(row["bytes"] for row in actual) == receipt.get("parquet_total_bytes"),
        "Parquet byte total mismatch",
    )
    return actual


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    ).encode("utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def module_hash(module: str) -> str:
    return hashlib.sha256(module.encode("utf-8")).hexdigest()


def top_level_domain(module: str) -> str:
    pieces = module.split(".")
    return pieces[1] if len(pieces) > 1 else pieces[0]


def construction_config() -> dict[str, Any]:
    """All admission and selection knobs, serialized into the freeze receipt."""

    return {
        "seed": SEED,
        "public_schema": PUBLIC_SCHEMA,
        "label_schema": LABEL_SCHEMA,
        "canonical_task": CANONICAL_TASK,
        "calibration_count": CALIBRATION_COUNT,
        "blind_count": BLIND_COUNT,
        "candidates_per_episode": K,
        "selection_budget": B,
        "targets_per_episode": TARGET_COUNT,
        "minimum_recurrent_corpus_uses": MIN_RECURRENT_USES,
        "minimum_active_candidates": MIN_ACTIVE_CANDIDATES,
        "minimum_nonoptimal_active_candidates": MIN_NONOPTIMAL_ACTIVE,
        "minimum_near_optimal_portfolios": MIN_NEAR_OPTIMAL,
        "minimum_multi_edge_targets": MIN_MULTI_EDGE_TARGETS,
        "maximum_single_candidate_coverage": MAX_SINGLETON_COVERAGE,
        "minimum_optimal_coverage": MIN_OPTIMAL_COVERAGE,
        "maximum_optimal_portfolios": MAX_OPTIMAL_PORTFOLIOS,
        "maximum_calibration_rows_per_top_level_domain": MAX_DOMAIN_CALIBRATION,
        "maximum_blind_rows_per_top_level_domain": MAX_DOMAIN_BLIND,
        "candidate_cohort_trials": COHORT_TRIALS,
        "target_seed_trials_per_cohort": TARGET_SEED_TRIALS,
        "calibration_trial_limit": CALIBRATION_TRIAL_LIMIT,
        "pinned_lean_excluded_module_hashes": sorted(
            PINNED_LEAN_EXCLUDED_MODULE_HASHES
        ),
        "frozen_calibration_public_sha256": FROZEN_CALIBRATION_PUBLIC_SHA256,
        "frozen_calibration_labels_sha256": FROZEN_CALIBRATION_LABELS_SHA256,
        "pinned_lean_preflight_blind_public_sha256": (
            PINNED_LEAN_PREFLIGHT_BLIND_PUBLIC_SHA256
        ),
        "pinned_lean_preflight_blind_labels_sha256": (
            PINNED_LEAN_PREFLIGHT_BLIND_LABELS_SHA256
        ),
        "calibration_selection_salt": "calibration-hash-rank",
        "blind_selection_salt": "blind-hash-rank",
        "objective": "target coverage under direct-value displayed-candidate incidence",
        "construction_gate_method_names": sorted(
            [
                f"{feature}_{direction}"
                for feature in (
                    "characters", "tokens", "binders", "connectives", "target_similarity"
                )
                for direction in ("largest", "smallest", "central")
            ]
            + [
                "lexical_greedy_top1",
                "lexical_greedy_top2",
                "lexical_greedy_top3",
                "true_frequency_top3",
                "true_greedy_set_cover",
            ]
        ),
    }


@dataclass(frozen=True)
class PriorExclusions:
    module_hashes: frozenset[str]
    exact_signatures: frozenset[tuple[str, ...]]
    alpha_signatures: frozenset[tuple[str, ...]]
    source_names: frozenset[str]


def load_prior_exclusions() -> PriorExclusions:
    module_hashes: set[str] = set()
    source_names: set[str] = set()
    for path in (V1_LABELS, V3_LABELS):
        for row in load_jsonl(path):
            module_hashes.add(module_hash(row["source_module"]))
            source_names.update(row["candidate_sources"].values())
            source_names.update(row["target_sources"].values())
    rejected_v2 = json.loads(V2_MODULE_HASHES.read_text(encoding="utf-8"))
    module_hashes.update(rejected_v2["module_sha256"])

    exact: set[tuple[str, ...]] = set()
    alpha: set[tuple[str, ...]] = set()
    for path in (V1_PUBLIC, V2_PUBLIC, V3_PUBLIC):
        for episode in load_jsonl(path):
            for item in episode["candidates"] + episode["targets"]:
                statement = common.canonical_public_type(item["statement"])
                exact.add(common.normalized_statement_signature(statement))
                alpha.add(common.alpha_normalized_statement_signature(statement))
    return PriorExclusions(
        module_hashes=frozenset(module_hashes),
        exact_signatures=frozenset(exact),
        alpha_signatures=frozenset(alpha),
        source_names=frozenset(source_names),
    )


def is_prior_statement(statement: str, prior: PriorExclusions) -> bool:
    statement = common.canonical_public_type(statement)
    return (
        common.normalized_statement_signature(statement) in prior.exact_signatures
        or common.alpha_normalized_statement_signature(statement)
        in prior.alpha_signatures
    )


@lru_cache(maxsize=None)
def statement_tokens(statement: str) -> frozenset[str]:
    return common.public_type_tokens(statement)


def jaccard(left: frozenset[str], right: frozenset[str]) -> Fraction:
    union = left | right
    return Fraction(len(left & right), len(union)) if union else Fraction()


def jaccard_float(left: frozenset[str], right: frozenset[str]) -> float:
    """Fast ranking-only Jaccard; no serialized value depends on this float."""

    union = left | right
    return len(left & right) / len(union) if union else 0.0


def eligible_statement(statement: str, prior: PriorExclusions) -> bool:
    canonical = common.canonical_public_type(statement)
    token_count = len(TOKEN.findall(canonical))
    return (
        16 <= token_count <= 240
        and len(canonical) <= 1400
        and not miner.obviously_reflexive(canonical)
        and not is_prior_statement(canonical, prior)
    )


def incidence_coverage(
    selected: frozenset[str], incidence: Sequence[frozenset[str]]
) -> int:
    return sum(bool(selected & direct) for direct in incidence)


def exhaustive_optima(
    candidates: Sequence[str], incidence: Sequence[frozenset[str]]
) -> tuple[int, tuple[tuple[str, ...], ...], Counter[int]]:
    histogram: Counter[int] = Counter()
    scored: list[tuple[int, tuple[str, ...]]] = []
    for portfolio in itertools.combinations(candidates, B):
        score = incidence_coverage(frozenset(portfolio), incidence)
        histogram[score] += 1
        scored.append((score, portfolio))
    optimum = max(score for score, _portfolio in scored)
    optimal = tuple(portfolio for score, portfolio in scored if score == optimum)
    return optimum, optimal, histogram


def _surface_features(
    candidate: str,
    target_statements: Sequence[str],
    declarations: dict[str, miner.Declaration],
) -> tuple[Fraction, ...]:
    statement = common.canonical_public_type(declarations[candidate].type)
    return (
        Fraction(len(statement)),
        Fraction(len(TOKEN.findall(statement))),
        Fraction(statement.count("∀") + statement.count("fun") + statement.count(":")),
        Fraction(sum(statement.count(marker) for marker in CONNECTIVES)),
        common.public_type_portfolio_similarity(statement, target_statements),
    )


def _rank_pick(
    candidates: Sequence[str],
    values: dict[str, Fraction],
    *,
    largest: bool,
) -> tuple[str, ...]:
    index = {name: position for position, name in enumerate(candidates)}
    return tuple(
        sorted(
            candidates,
            key=lambda name: (
                -values[name] if largest else values[name], index[name]
            ),
        )[:B]
    )


def _central_pick(
    candidates: Sequence[str], values: dict[str, Fraction]
) -> tuple[str, ...]:
    ordered_values = sorted(values.values())
    median = (ordered_values[K // 2 - 1] + ordered_values[K // 2]) / 2
    index = {name: position for position, name in enumerate(candidates)}
    return tuple(
        sorted(
            candidates,
            key=lambda name: (abs(values[name] - median), index[name]),
        )[:B]
    )


def _lexical_predicted_incidence(
    candidates: Sequence[str],
    target_statements: Sequence[str],
    declarations: dict[str, miner.Declaration],
    *,
    width: int,
) -> list[frozenset[str]]:
    index = {name: position for position, name in enumerate(candidates)}
    result: list[frozenset[str]] = []
    for target in target_statements:
        target_tokens = statement_tokens(target)
        ranked = sorted(
            candidates,
            key=lambda name: (
                -jaccard(statement_tokens(declarations[name].type), target_tokens),
                index[name],
            ),
        )
        result.append(frozenset(ranked[:width]))
    return result


def _greedy_cover(
    candidates: Sequence[str], incidence: Sequence[frozenset[str]]
) -> tuple[str, ...]:
    index = {name: position for position, name in enumerate(candidates)}
    selected: list[str] = []
    covered: set[int] = set()
    while len(selected) < B:
        choice = max(
            (name for name in candidates if name not in selected),
            key=lambda name: (
                sum(
                    target_index not in covered and name in direct
                    for target_index, direct in enumerate(incidence)
                ),
                -index[name],
            ),
        )
        selected.append(choice)
        covered.update(
            target_index
            for target_index, direct in enumerate(incidence)
            if choice in direct
        )
    return tuple(sorted(selected, key=index.__getitem__))


def construction_diagnostic_predictions(
    candidates: Sequence[str],
    target_statements: Sequence[str],
    incidence: Sequence[frozenset[str]],
    declarations: dict[str, miner.Declaration],
) -> dict[str, tuple[str, ...]]:
    features = {
        name: _surface_features(name, target_statements, declarations)
        for name in candidates
    }
    result: dict[str, tuple[str, ...]] = {}
    labels = ("characters", "tokens", "binders", "connectives", "target_similarity")
    for feature_index, label in enumerate(labels):
        values = {name: row[feature_index] for name, row in features.items()}
        result[f"{label}_largest"] = _rank_pick(candidates, values, largest=True)
        result[f"{label}_smallest"] = _rank_pick(candidates, values, largest=False)
        result[f"{label}_central"] = _central_pick(candidates, values)

    # These two incidence-aware heuristics are private construction gates.
    # Requiring them to miss ensures a real portfolio interaction. They are not
    # independent evaluation baselines because admission conditions on them.
    use_counts = {
        name: Fraction(sum(name in direct for direct in incidence))
        for name in candidates
    }
    result["true_frequency_top3"] = _rank_pick(candidates, use_counts, largest=True)
    result["true_greedy_set_cover"] = _greedy_cover(candidates, incidence)

    # Public lexical set-cover proxies infer up to three edges per target from
    # token overlap, then use the same deterministic greedy rule.
    for width in (1, 2, 3):
        predicted = _lexical_predicted_incidence(
            candidates, target_statements, declarations, width=width
        )
        result[f"lexical_greedy_top{width}"] = _greedy_cover(candidates, predicted)
    return result


def _target_conflicts(
    candidate: str,
    selected: Sequence[str],
    edges: dict[str, frozenset[str]],
) -> bool:
    return any(
        other in edges.get(candidate, frozenset())
        or candidate in edges.get(other, frozenset())
        for other in selected
    )


def _mean_target_similarity(
    target_names: Sequence[str], declarations: dict[str, miner.Declaration]
) -> float:
    token_sets = [statement_tokens(declarations[name].type) for name in target_names]
    values = [
        jaccard_float(left, right)
        for left, right in itertools.combinations(token_sets, 2)
    ]
    return sum(values) / len(values) if values else 0.0


def choose_target_set(
    *,
    module: str,
    trial: str,
    seed_target: str,
    target_pool: Sequence[str],
    direct: dict[str, frozenset[str]],
    declarations: dict[str, miner.Declaration],
    edges: dict[str, frozenset[str]],
) -> tuple[str, ...] | None:
    MINING_COUNTS["target_seed_attempts"] += 1
    ordered = sorted(
        target_pool,
        key=lambda name: miner.stable_token(
            SEED, module, f"target-trial-{trial}", name
        ),
    )
    ordered.remove(seed_target)
    ordered.insert(0, seed_target)
    selected: list[str] = []
    use_counts: Counter[str] = Counter()
    for name in ordered:
        if _target_conflicts(name, selected, edges):
            continue
        if any(use_counts[item] >= MAX_SINGLETON_COVERAGE for item in direct[name]):
            continue
        selected.append(name)
        use_counts.update(direct[name])
        if len(selected) == TARGET_COUNT:
            break
    if len(selected) != TARGET_COUNT:
        MINING_COUNTS["target_seed_reject_incomplete_conflict_or_cap_fill"] += 1
        return None
    MINING_COUNTS["target_sets_pass_complete_fill"] += 1
    if len(use_counts) < MIN_ACTIVE_CANDIDATES:
        MINING_COUNTS["target_seed_reject_too_few_active"] += 1
        return None
    MINING_COUNTS["target_sets_pass_minimum_active"] += 1
    if max(use_counts.values()) > MAX_SINGLETON_COVERAGE:
        MINING_COUNTS["target_seed_reject_singleton_cap"] += 1
        return None
    MINING_COUNTS["target_sets_pass_singleton_cap"] += 1
    if sum(len(direct[name]) >= 2 for name in selected) < MIN_MULTI_EDGE_TARGETS:
        MINING_COUNTS["target_seed_reject_too_few_multi_edge"] += 1
        return None
    MINING_COUNTS["target_sets_pass_multi_edge"] += 1
    if _mean_target_similarity(selected, declarations) > 0.6:
        MINING_COUNTS["target_seed_reject_target_similarity"] += 1
        return None
    MINING_COUNTS["target_sets_pass_similarity"] += 1
    return tuple(
        sorted(
            selected,
            key=lambda name: miner.stable_token(SEED, module, "target-order", name),
        )
    )


@dataclass(frozen=True)
class DraftEpisode:
    module: str
    candidates: tuple[str, ...]
    targets: tuple[str, ...]
    incidence: tuple[frozenset[str], ...]
    optimal_coverage: int
    optimal_portfolios: tuple[tuple[str, ...], ...]
    coverage_histogram: tuple[tuple[int, int], ...]
    recurrent_use_counts: tuple[tuple[str, int], ...]
    construction_diagnostics: tuple[tuple[str, tuple[str, ...]], ...]
    cohort_trial: int
    target_seed_trial: int


def evaluate_draft(
    *,
    module: str,
    candidates: Sequence[str],
    targets: Sequence[str],
    reverse: dict[str, set[str]],
    declarations: dict[str, miner.Declaration],
    edges: dict[str, frozenset[str]],
    cohort_trial: int,
    target_seed_trial: int,
) -> DraftEpisode | None:
    DRAFT_FUNNEL["drafts_evaluated"] += 1
    candidate_set = set(candidates)
    incidence = tuple(frozenset(edges[target] & candidate_set) for target in targets)
    if any(not direct for direct in incidence):
        DRAFT_REJECTIONS["empty_incidence"] += 1
        return None
    DRAFT_FUNNEL["pass_nonempty_incidence"] += 1
    active = set().union(*incidence)
    if len(active) < MIN_ACTIVE_CANDIDATES:
        DRAFT_REJECTIONS["too_few_active"] += 1
        return None
    DRAFT_FUNNEL["pass_minimum_active_candidates"] += 1
    use_counts = {
        name: sum(name in direct for direct in incidence) for name in candidates
    }
    if max(use_counts.values()) > MAX_SINGLETON_COVERAGE:
        DRAFT_REJECTIONS["singleton_cap"] += 1
        return None
    DRAFT_FUNNEL["pass_single_candidate_coverage_cap"] += 1
    if sum(len(direct) >= 2 for direct in incidence) < MIN_MULTI_EDGE_TARGETS:
        DRAFT_REJECTIONS["too_few_multi_edge"] += 1
        return None
    DRAFT_FUNNEL["pass_minimum_multi_edge_targets"] += 1

    optimum, optimal, histogram = exhaustive_optima(candidates, incidence)
    if optimum < MIN_OPTIMAL_COVERAGE:
        DRAFT_REJECTIONS["optimal_coverage_below_minimum"] += 1
        return None
    DRAFT_FUNNEL["pass_minimum_optimal_coverage"] += 1
    if len(optimal) > MAX_OPTIMAL_PORTFOLIOS:
        DRAFT_REJECTIONS["too_many_optimal_portfolios"] += 1
        return None
    DRAFT_FUNNEL["pass_maximum_optimal_portfolios"] += 1
    optimal_sets = {frozenset(portfolio) for portfolio in optimal}
    optimal_union = set().union(*optimal_sets)
    if len(active - optimal_union) < MIN_NONOPTIMAL_ACTIVE:
        DRAFT_REJECTIONS["too_few_nonoptimal_active"] += 1
        return None
    DRAFT_FUNNEL["pass_minimum_nonoptimal_active"] += 1
    if any(use_counts[name] < 2 for name in optimal_union):
        DRAFT_REJECTIONS["optimal_member_not_reused"] += 1
        return None
    DRAFT_FUNNEL["pass_optimal_member_reuse"] += 1
    if any(
        incidence_coverage(portfolio - {name}, incidence) >= optimum
        for portfolio in optimal_sets
        for name in portfolio
    ):
        DRAFT_REJECTIONS["nonessential_optimal_member"] += 1
        return None
    DRAFT_FUNNEL["pass_optimal_member_essentiality"] += 1
    if histogram.get(optimum - 1, 0) < MIN_NEAR_OPTIMAL:
        DRAFT_REJECTIONS["too_few_near_optimal"] += 1
        return None
    DRAFT_FUNNEL["pass_minimum_near_optimal_portfolios"] += 1

    target_statements = [declarations[name].type for name in targets]
    predictions = construction_diagnostic_predictions(
        candidates, target_statements, incidence, declarations
    )
    if any(frozenset(prediction) in optimal_sets for prediction in predictions.values()):
        DRAFT_REJECTIONS["construction_gate_optimal"] += 1
        return None
    DRAFT_FUNNEL["pass_all_construction_gates_miss"] += 1
    displayed_statements = [declarations[name].type for name in candidates] + target_statements
    source_names = list(candidates) + list(targets)
    if any(
        miner.name_visible_in_type(source, statement)
        for source in source_names
        for statement in displayed_statements
    ):
        DRAFT_REJECTIONS["source_name_visible"] += 1
        return None
    DRAFT_FUNNEL["pass_source_name_masking"] += 1
    if not common.statements_are_identifiable(
        [declarations[name].type for name in candidates], target_statements
    ):
        DRAFT_REJECTIONS["statement_collision"] += 1
        return None
    DRAFT_FUNNEL["pass_within_episode_statement_identifiability"] += 1
    DRAFT_FUNNEL["accepted_drafts"] += 1
    return DraftEpisode(
        module=module,
        candidates=tuple(candidates),
        targets=tuple(targets),
        incidence=incidence,
        optimal_coverage=optimum,
        optimal_portfolios=optimal,
        coverage_histogram=tuple(sorted(histogram.items())),
        recurrent_use_counts=tuple((name, len(reverse[name])) for name in candidates),
        construction_diagnostics=tuple(sorted(predictions.items())),
        cohort_trial=cohort_trial,
        target_seed_trial=target_seed_trial,
    )


def draft_module_episode(
    module: str,
    names: Sequence[str],
    declarations: dict[str, miner.Declaration],
    edges: dict[str, frozenset[str]],
) -> DraftEpisode | None:
    name_set = set(names)
    reverse: dict[str, set[str]] = defaultdict(set)
    for target in names:
        for dependency in edges[target] & name_set:
            reverse[dependency].add(target)
    hubs = [name for name, consumers in reverse.items() if len(consumers) >= MIN_RECURRENT_USES]
    if len(hubs) < K:
        return None
    MINING_COUNTS["modules_with_at_least_k_recurrent_hubs"] += 1

    seen_cohorts: set[frozenset[str]] = set()
    for cohort_trial in range(COHORT_TRIALS):
        cohort = tuple(
            sorted(
                hubs,
                key=lambda name: miner.stable_token(
                    SEED, module, f"cohort-{cohort_trial}", name
                ),
            )[:K]
        )
        cohort_set = frozenset(cohort)
        if cohort_set in seen_cohorts:
            continue
        seen_cohorts.add(cohort_set)
        MINING_COUNTS["unique_candidate_cohorts_evaluated"] += 1
        candidates = tuple(
            sorted(
                cohort,
                key=lambda name: miner.stable_token(SEED, module, "candidate-order", name),
            )
        )
        direct = {
            target: frozenset(edges[target] & cohort_set)
            for target in names
            if target not in cohort_set
        }
        target_pool = [
            target for target, values in direct.items() if 1 <= len(values) <= 5
        ]
        if len(target_pool) < TARGET_COUNT:
            MINING_COUNTS["candidate_cohorts_reject_small_target_pool"] += 1
            continue
        MINING_COUNTS["candidate_cohorts_pass_target_pool"] += 1
        target_pool.sort(
            key=lambda name: miner.stable_token(
                SEED, module, f"target-pool-{cohort_trial}", name
            )
        )
        for seed_trial, seed_target in enumerate(target_pool[:TARGET_SEED_TRIALS]):
            targets = choose_target_set(
                module=module,
                trial=f"{cohort_trial}-{seed_trial}",
                seed_target=seed_target,
                target_pool=target_pool,
                direct=direct,
                declarations=declarations,
                edges=edges,
            )
            if targets is None:
                continue
            draft = evaluate_draft(
                module=module,
                candidates=candidates,
                targets=targets,
                reverse=reverse,
                declarations=declarations,
                edges=edges,
                cohort_trial=cohort_trial,
                target_seed_trial=seed_trial,
            )
            if draft is not None:
                return draft
    return None


def mine_drafts(
    declarations: dict[str, miner.Declaration], prior: PriorExclusions
) -> tuple[list[DraftEpisode], dict[str, Any], dict[str, frozenset[str]]]:
    DRAFT_REJECTIONS.clear()
    DRAFT_FUNNEL.clear()
    MINING_COUNTS.clear()
    edges = miner.proof_only_edges(
        declarations, generation_profile=miner.STRICT_GENERATION_PROFILE
    )
    eligible_names = {
        name
        for name, declaration in declarations.items()
        if name in edges
        and name not in prior.source_names
        and eligible_statement(declaration.type, prior)
        and module_hash(declaration.module) not in prior.module_hashes
        and module_hash(declaration.module) not in PINNED_LEAN_EXCLUDED_MODULE_HASHES
    }
    by_module: dict[str, list[str]] = defaultdict(list)
    for name in eligible_names:
        by_module[declarations[name].module].append(name)
    modules = sorted(
        by_module,
        key=lambda module: miner.stable_token(SEED, "module-mining-order", module),
    )
    MINING_COUNTS["eligible_module_centers"] = len(modules)
    drafts: list[DraftEpisode] = []
    for module_index, module in enumerate(modules, start=1):
        draft = draft_module_episode(module, by_module[module], declarations, edges)
        if draft is not None:
            drafts.append(draft)
        if module_index % 500 == 0:
            print(
                f"v4 construction: scanned {module_index}/{len(modules)} modules; "
                f"eligible drafts {len(drafts)}",
                file=sys.stderr,
                flush=True,
            )
    return drafts, {
        "eligible_declarations": len(eligible_names),
        "eligible_modules": len(modules),
        "accepted_module_drafts": len(drafts),
        "rejected_modules": len(modules) - len(drafts),
        "pinned_lean_excluded_module_hashes": sorted(
            PINNED_LEAN_EXCLUDED_MODULE_HASHES
        ),
        "construction_center_counts": dict(sorted(MINING_COUNTS.items())),
        "sequential_evaluated_draft_funnel": dict(sorted(DRAFT_FUNNEL.items())),
        "evaluated_draft_rejection_counts": dict(sorted(DRAFT_REJECTIONS.items())),
    }, edges


def select_hash_ranked(
    drafts: Sequence[DraftEpisode],
    *,
    count: int,
    salt: str,
    domain_cap: int,
    excluded_modules: set[str],
) -> list[DraftEpisode]:
    ordered = sorted(
        (draft for draft in drafts if draft.module not in excluded_modules),
        key=lambda draft: miner.stable_token(SEED, salt, draft.module),
    )
    selected: list[DraftEpisode] = []
    domains: Counter[str] = Counter()
    for draft in ordered:
        domain = top_level_domain(draft.module)
        if domains[domain] >= domain_cap:
            continue
        selected.append(draft)
        domains[domain] += 1
        if len(selected) == count:
            break
    return selected


def mine_splits(
    declarations: dict[str, miner.Declaration], prior: PriorExclusions
) -> tuple[list[DraftEpisode], list[DraftEpisode], dict[str, Any], dict[str, frozenset[str]]]:
    drafts, mining_summary, edges = mine_drafts(declarations, prior)
    calibration_eligible = [
        draft
        for draft in drafts
        if draft.cohort_trial < CALIBRATION_TRIAL_LIMIT
        and draft.target_seed_trial < CALIBRATION_TRIAL_LIMIT
    ]
    calibration = select_hash_ranked(
        calibration_eligible,
        count=CALIBRATION_COUNT,
        salt="calibration-hash-rank",
        domain_cap=MAX_DOMAIN_CALIBRATION,
        excluded_modules=set(),
    )
    blind = select_hash_ranked(
        drafts,
        count=BLIND_COUNT,
        salt="blind-hash-rank",
        domain_cap=MAX_DOMAIN_BLIND,
        excluded_modules={draft.module for draft in calibration},
    )
    mining_summary.update(
        {
            "calibration_selected": len(calibration),
            "blind_selected": len(blind),
            "calibration_requested": CALIBRATION_COUNT,
            "blind_requested": BLIND_COUNT,
        }
    )
    return calibration, blind, mining_summary, edges


def render_split(
    drafts: Sequence[DraftEpisode],
    declarations: dict[str, miner.Declaration],
    *,
    benchmark_id: str,
    prefix: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for episode_index, draft in enumerate(drafts):
        episode_id = f"{prefix}_{episode_index:04d}"
        candidate_id = {
            name: f"C{index:02d}" for index, name in enumerate(draft.candidates, 1)
        }
        target_id = {
            name: f"T{index:02d}" for index, name in enumerate(draft.targets, 1)
        }
        public_rows.append(
            {
                "benchmark_id": benchmark_id,
                "candidates": [
                    {
                        "id": candidate_id[name],
                        "statement": common.canonical_public_type(declarations[name].type),
                    }
                    for name in draft.candidates
                ],
                "episode_id": episode_id,
                "schema_version": PUBLIC_SCHEMA,
                "selection_budget": B,
                "source_project": "mathlib",
                "targets": [
                    {
                        "id": target_id[name],
                        "statement": common.canonical_public_type(declarations[name].type),
                    }
                    for name in draft.targets
                ],
                "task": CANONICAL_TASK,
            }
        )
        direct_rows = [
            {
                "id": target_id[target],
                "direct_candidates": sorted(candidate_id[name] for name in direct),
            }
            for target, direct in zip(draft.targets, draft.incidence, strict=True)
        ]
        active = sorted(
            set().union(*(set(row["direct_candidates"]) for row in direct_rows))
        )
        label_rows.append(
            {
                "active_candidates": active,
                "benchmark_id": benchmark_id,
                "candidate_displayed_use_counts": {
                    candidate_id[name]: sum(name in direct for direct in draft.incidence)
                    for name in draft.candidates
                },
                "candidate_recurrent_corpus_use_counts": {
                    candidate_id[name]: count
                    for name, count in draft.recurrent_use_counts
                },
                "candidate_sources": {
                    candidate_id[name]: name for name in draft.candidates
                },
                "coverage_histogram": {
                    str(score): count for score, count in draft.coverage_histogram
                },
                "episode_id": episode_id,
                "construction_gate_predictions": {
                    label: sorted(candidate_id[name] for name in portfolio)
                    for label, portfolio in draft.construction_diagnostics
                },
                "optimal_coverage": draft.optimal_coverage,
                "optimal_portfolios": sorted(
                    sorted(candidate_id[name] for name in portfolio)
                    for portfolio in draft.optimal_portfolios
                ),
                "schema_version": LABEL_SCHEMA,
                "source_module": draft.module,
                "target_sources": {
                    target_id[name]: name for name in draft.targets
                },
                "targets": direct_rows,
            }
        )
    return public_rows, label_rows


def validate_split(
    public_rows: Sequence[dict[str, Any]],
    label_rows: Sequence[dict[str, Any]],
    declarations: dict[str, miner.Declaration],
    edges: dict[str, frozenset[str]],
    prior: PriorExclusions,
    *,
    benchmark_id: str,
    prefix: str,
) -> dict[str, Any]:
    require(len(public_rows) == len(label_rows), "public/label row count")
    modules: list[str] = []
    domains: Counter[str] = Counter()
    exact_seen: set[tuple[str, ...]] = set()
    alpha_seen: set[tuple[str, ...]] = set()
    total_active = total_optima = total_multi = total_edges = 0
    optimal_coverage_distribution: Counter[int] = Counter()
    for episode_index, (public, labels) in enumerate(
        zip(public_rows, label_rows, strict=True)
    ):
        episode_id = f"{prefix}_{episode_index:04d}"
        require(public["episode_id"] == labels["episode_id"] == episode_id, "episode ID")
        require(public["benchmark_id"] == labels["benchmark_id"] == benchmark_id, "benchmark ID")
        require(public["schema_version"] == PUBLIC_SCHEMA, "public schema")
        require(labels["schema_version"] == LABEL_SCHEMA, "label schema")
        require(public["selection_budget"] == B, "selection budget")
        require(public["task"] == CANONICAL_TASK, "task wording")
        candidates = public["candidates"]
        targets = public["targets"]
        candidate_ids = [f"C{index:02d}" for index in range(1, K + 1)]
        target_ids = [f"T{index:02d}" for index in range(1, TARGET_COUNT + 1)]
        require([row["id"] for row in candidates] == candidate_ids, "candidate IDs")
        require([row["id"] for row in targets] == target_ids, "target IDs")
        require(len(candidates) == K and len(targets) == TARGET_COUNT, "episode shape")
        module = labels["source_module"]
        modules.append(module)
        domains[top_level_domain(module)] += 1
        require(module_hash(module) not in prior.module_hashes, "prior module overlap")
        candidate_sources = labels["candidate_sources"]
        target_sources = labels["target_sources"]
        require(list(candidate_sources) == candidate_ids, "candidate provenance order")
        require(list(target_sources) == target_ids, "target provenance order")
        require(
            all(
                declarations[name].module == module
                for name in list(candidate_sources.values()) + list(target_sources.values())
            ),
            "cross-module source",
        )
        for row in candidates + targets:
            statement = row["statement"]
            require(statement == common.canonical_public_type(statement), "whitespace")
            require(not is_prior_statement(statement, prior), "prior statement overlap")
            exact = common.normalized_statement_signature(statement)
            alpha = common.alpha_normalized_statement_signature(statement)
            require(exact not in exact_seen, "split exact statement duplicate")
            require(alpha not in alpha_seen, "split alpha statement duplicate")
            exact_seen.add(exact)
            alpha_seen.add(alpha)
        source_names = list(candidate_sources.values()) + list(target_sources.values())
        require(
            not any(
                miner.name_visible_in_type(source, row["statement"])
                for source in source_names
                for row in candidates + targets
            ),
            "source-name leakage",
        )
        direct_rows = labels["targets"]
        require([row["id"] for row in direct_rows] == target_ids, "label target order")
        incidence: list[frozenset[str]] = []
        for row in direct_rows:
            target_source = target_sources[row["id"]]
            expected = {
                candidate_id
                for candidate_id, candidate_source in candidate_sources.items()
                if candidate_source in edges[target_source]
            }
            actual = frozenset(row["direct_candidates"])
            require(actual == expected and bool(actual), "exact direct-edge intersection")
            incidence.append(actual)
        active = set().union(*incidence)
        require(active == set(labels["active_candidates"]), "active candidate set")
        require(len(active) >= MIN_ACTIVE_CANDIDATES, "too few active candidates")
        total_active += len(active)
        use_counts = {
            candidate_id: sum(candidate_id in direct for direct in incidence)
            for candidate_id in candidate_ids
        }
        require(use_counts == labels["candidate_displayed_use_counts"], "use counts")
        require(max(use_counts.values()) <= MAX_SINGLETON_COVERAGE, "singleton coverage cap")
        require(
            min(labels["candidate_recurrent_corpus_use_counts"].values())
            >= MIN_RECURRENT_USES,
            "nonrecurrent displayed candidate",
        )
        optimum, optimal, histogram = exhaustive_optima(candidate_ids, incidence)
        stored_optimal = tuple(tuple(row) for row in labels["optimal_portfolios"])
        require(optimum == labels["optimal_coverage"], "optimal coverage replay")
        require(set(optimal) == set(stored_optimal), "complete argmax replay")
        require(
            {str(key): value for key, value in sorted(histogram.items())}
            == labels["coverage_histogram"],
            "coverage histogram replay",
        )
        optimal_sets = {frozenset(row) for row in optimal}
        optimal_union = set().union(*optimal_sets)
        require(len(active - optimal_union) >= MIN_NONOPTIMAL_ACTIVE, "nonoptimal active count")
        require(all(use_counts[name] >= 2 for name in optimal_union), "optimal member reuse")
        require(
            all(
                incidence_coverage(portfolio - {name}, incidence) < optimum
                for portfolio in optimal_sets
                for name in portfolio
            ),
            "nonessential optimal member",
        )
        require(histogram.get(optimum - 1, 0) >= MIN_NEAR_OPTIMAL, "near-optimal count")
        require(sum(len(row) >= 2 for row in incidence) >= MIN_MULTI_EDGE_TARGETS, "multi-edge targets")
        predictions = labels["construction_gate_predictions"]
        require(predictions, "construction-gate predictions")
        require(
            not any(frozenset(row) in optimal_sets for row in predictions.values()),
            "construction-gated method is optimal",
        )
        total_optima += len(optimal)
        total_multi += sum(len(row) >= 2 for row in incidence)
        total_edges += sum(len(row) for row in incidence)
        optimal_coverage_distribution[optimum] += 1
    require(len(modules) == len(set(modules)), "duplicate module")
    return {
        "episodes": len(public_rows),
        "distinct_modules": len(set(modules)),
        "top_level_domains": len(domains),
        "domain_counts": dict(sorted(domains.items())),
        "candidates_per_episode": K,
        "targets_per_episode": TARGET_COUNT,
        "selection_budget": B,
        "mean_active_candidates": (
            str(Fraction(total_active, len(public_rows))) if public_rows else "0"
        ),
        "total_direct_in_pool_edges": total_edges,
        "total_multi_edge_targets": total_multi,
        "total_accepted_optimal_portfolios": total_optima,
        "optimal_coverage_distribution": {
            str(key): value for key, value in sorted(optimal_coverage_distribution.items())
        },
        "construction_gated_method_optimal_hits": 0,
        "prior_module_or_statement_overlap": 0,
        "source_name_visible_pairs": 0,
        "all_candidates_recurrent": True,
    }


def _statement_signatures(
    public_rows: Sequence[dict[str, Any]],
) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    exact = {
        common.normalized_statement_signature(item["statement"])
        for row in public_rows
        for item in row["candidates"] + row["targets"]
    }
    alpha = {
        common.alpha_normalized_statement_signature(item["statement"])
        for row in public_rows
        for item in row["candidates"] + row["targets"]
    }
    return exact, alpha


def build_bundle(
    parquet_dir: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
]:
    prior = load_prior_exclusions()
    declarations = common.declarations_from_parquets(parquet_dir)
    calibration_drafts, blind_drafts, mining_summary, edges = mine_splits(
        declarations, prior
    )
    calibration_public, calibration_labels = render_split(
        calibration_drafts,
        declarations,
        benchmark_id=CALIBRATION_ID,
        prefix="MLP4C",
    )
    blind_public, blind_labels = render_split(
        blind_drafts,
        declarations,
        benchmark_id=BLIND_ID,
        prefix="MLP4B",
    )
    require(
        sha256_bytes(jsonl_bytes(calibration_public))
        == FROZEN_CALIBRATION_PUBLIC_SHA256,
        "frozen calibration public bytes changed",
    )
    require(
        sha256_bytes(jsonl_bytes(calibration_labels))
        == FROZEN_CALIBRATION_LABELS_SHA256,
        "frozen calibration label bytes changed",
    )
    require(
        sha256_bytes(jsonl_bytes(blind_public))
        == PINNED_LEAN_PREFLIGHT_BLIND_PUBLIC_SHA256,
        "pinned-Lean-preflight blind public bytes changed",
    )
    require(
        sha256_bytes(jsonl_bytes(blind_labels))
        == PINNED_LEAN_PREFLIGHT_BLIND_LABELS_SHA256,
        "pinned-Lean-preflight blind label bytes changed",
    )
    calibration_summary = validate_split(
        calibration_public,
        calibration_labels,
        declarations,
        edges,
        prior,
        benchmark_id=CALIBRATION_ID,
        prefix="MLP4C",
    )
    blind_summary = validate_split(
        blind_public,
        blind_labels,
        declarations,
        edges,
        prior,
        benchmark_id=BLIND_ID,
        prefix="MLP4B",
    )
    require(
        not {row["source_module"] for row in calibration_labels}
        & {row["source_module"] for row in blind_labels},
        "calibration/blind module overlap",
    )
    calibration_exact, calibration_alpha = _statement_signatures(calibration_public)
    blind_exact, blind_alpha = _statement_signatures(blind_public)
    require(not calibration_exact & blind_exact, "cross-split exact statement overlap")
    require(not calibration_alpha & blind_alpha, "cross-split alpha statement overlap")
    return (
        calibration_public,
        calibration_labels,
        blind_public,
        blind_labels,
        {
            "declarations": len(declarations),
            "mining": mining_summary,
            "calibration": calibration_summary,
            "blind": blind_summary,
        },
    )


def _write_exclusive(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            require(written > 0, f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def materialize(parquet_dir: Path, public_dir: Path, private_dir: Path) -> dict[str, Any]:
    require(
        public_dir.resolve(strict=False) != private_dir.resolve(strict=False),
        "public/private directories coincide",
    )
    paths = {
        "calibration_public": public_dir / "calibration.public.jsonl",
        "calibration_a_public": public_dir / "calibration_a.public.jsonl",
        "calibration_b_public": public_dir / "calibration_b.public.jsonl",
        "blind_public": public_dir / "blind.public.jsonl",
        "manifest": public_dir / "manifest.preinference.json",
        "generation_receipt": public_dir / "generation_receipt.json",
        "construction_diagnostics": public_dir / "gated_construction_diagnostics.json",
        "calibration_labels": public_dir / "calibration.labels.jsonl",
        "calibration_a_labels": public_dir / "calibration_a.labels.jsonl",
        "calibration_b_labels": public_dir / "calibration_b.labels.jsonl",
        "blind_labels": private_dir / "blind.labels.jsonl",
        "private_manifest": private_dir / "private_manifest.json",
    }
    require(
        not any(path.exists() for path in paths.values()),
        "refusing to overwrite v4 artifacts",
    )
    parquet_inputs = verified_parquet_inventory(parquet_dir)
    calibration_public, calibration_labels, blind_public, blind_labels, summary = (
        build_bundle(parquet_dir)
    )
    payloads = {
        "calibration_public": jsonl_bytes(calibration_public),
        "calibration_a_public": jsonl_bytes(calibration_public[:15]),
        "calibration_b_public": jsonl_bytes(calibration_public[15:]),
        "blind_public": jsonl_bytes(blind_public),
        "calibration_labels": jsonl_bytes(calibration_labels),
        "calibration_a_labels": jsonl_bytes(calibration_labels[:15]),
        "calibration_b_labels": jsonl_bytes(calibration_labels[15:]),
        "blind_labels": jsonl_bytes(blind_labels),
    }
    require(
        payloads["calibration_a_public"] + payloads["calibration_b_public"]
        == payloads["calibration_public"],
        "calibration public batch concatenation mismatch",
    )
    require(
        payloads["calibration_a_labels"] + payloads["calibration_b_labels"]
        == payloads["calibration_labels"],
        "calibration label batch concatenation mismatch",
    )
    diagnostics_object = construction_diagnostics.render_bundle(
        calibration_public,
        blind_public,
        calibration_bytes=payloads["calibration_public"],
        blind_bytes=payloads["blind_public"],
    )
    diagnostics_bytes = canonical_json_bytes(diagnostics_object)
    for split_name, label_rows in (
        ("calibration", calibration_labels),
        ("blind", blind_labels),
    ):
        emitted = diagnostics_object["splits"][split_name]["predictions"]
        for label_row in label_rows:
            expected = {
                name: prediction
                for name, prediction in label_row["construction_gate_predictions"].items()
                if not name.startswith("true_")
            }
            require(
                emitted[label_row["episode_id"]] == expected,
                "standalone public construction-diagnostic replay mismatch",
            )
    v1_receipt = json.loads(common.V1_RECEIPT_PATH.read_text(encoding="utf-8"))
    inventory_bytes = canonical_json_bytes({"parquet_inputs": parquet_inputs})
    config = construction_config()
    config_bytes = canonical_json_bytes(config)
    selection_ledger = {
        split_name: [
            {
                "episode_id": row["episode_id"],
                "source_module": row["source_module"],
                "candidate_sources": row["candidate_sources"],
                "target_sources": row["target_sources"],
            }
            for row in rows
        ]
        for split_name, rows in (
            ("calibration", calibration_labels),
            ("blind", blind_labels),
        )
    }
    selection_ledger_sha256 = sha256_bytes(canonical_json_bytes(selection_ledger))
    generation_receipt = {
        "schema_version": "lemma-portfolio.dependency-compression-generation.v4",
        "created_on": "2026-09-01",
        "seed": SEED,
        "builder_identity": {
            "vcs_commit": None,
            "vcs_note": "workspace snapshot is not a Git working tree",
            "content_sha256": sha256_path(Path(__file__)),
        },
        "construction_diagnostics_script_sha256": sha256_path(
            Path(construction_diagnostics.__file__).resolve()
        ),
        "pinned_lean_audit_script_sha256": sha256_path(
            Path(__file__).with_name("audit_pinned_lean.py")
        ),
        "static_bundle_audit_script_sha256": sha256_path(
            Path(__file__).with_name("audit_static_bundle.py")
        ),
        "evaluated_blind_predictions_read_or_used_by_builder": 0,
        "development_assistance": (
            "Codex agents assisted design/code; authors are responsible; item "
            "admission is deterministic and no blind evaluation prediction enters it."
        ),
        "construction_config": config,
        "construction_config_sha256": sha256_bytes(config_bytes),
        "private_selection_ledger_sha256": selection_ledger_sha256,
        "private_selection_ledger_fields": [
            "episode_id",
            "source_module",
            "candidate_sources",
            "target_sources",
        ],
        "pinned_lean_blind_preflight": {
            "status": "pass",
            "public_sha256": PINNED_LEAN_PREFLIGHT_BLIND_PUBLIC_SHA256,
            "labels_sha256": PINNED_LEAN_PREFLIGHT_BLIND_LABELS_SHA256,
            "reports": 480,
            "old_edges": 814,
            "direct_value_edges": 814,
            "changed_targets": 0,
            "changed_episodes": 0,
            "removed_edges": 0,
            "added_edges": 0,
            "empty_targets": 0,
            "candidate_type_eqv_collisions": 0,
            "candidate_target_type_eqv_collisions": 0,
            "target_type_eqv_collisions": 0,
            "mathlib_commit": "db584cd6d46c92f209a44c0f1c829460d327499d",
            "lean_commit": "d8b18978322de05a8f3dba51ef03cf5461676c17",
        },
        "source": {
            "dataset_version": "v4.33.0",
            "mathlib_commit": "db584cd6d46c92f209a44c0f1c829460d327499d",
            "parquet_file_count": v1_receipt["parquet_file_count"],
            "parquet_total_bytes": v1_receipt["parquet_total_bytes"],
            "parquet_manifest_sha256": v1_receipt["parquet_manifest_sha256"],
            "recomputed_parquet_inventory_sha256": sha256_bytes(inventory_bytes),
            "source_generation_receipt_sha256": sha256_path(common.V1_RECEIPT_PATH),
            "parquet_inputs": parquet_inputs,
        },
        "outputs": {
            "calibration_public_sha256": sha256_bytes(payloads["calibration_public"]),
            "calibration_a_public_sha256": sha256_bytes(payloads["calibration_a_public"]),
            "calibration_b_public_sha256": sha256_bytes(payloads["calibration_b_public"]),
            "calibration_labels_commitment_sha256": sha256_bytes(payloads["calibration_labels"]),
            "calibration_a_labels_sha256": sha256_bytes(payloads["calibration_a_labels"]),
            "calibration_b_labels_sha256": sha256_bytes(payloads["calibration_b_labels"]),
            "blind_public_sha256": sha256_bytes(payloads["blind_public"]),
            "blind_labels_commitment_sha256": sha256_bytes(payloads["blind_labels"]),
            "gated_construction_diagnostics_sha256": sha256_bytes(diagnostics_bytes),
        },
        "summary": summary,
    }
    generation_receipt_bytes = canonical_json_bytes(generation_receipt)
    manifest = {
        "schema_version": "lemma-portfolio.dependency-compression-manifest.v4",
        "status": "FROZEN_PREINFERENCE_LOCAL_UNTIMESTAMPED",
        "created_on": "2026-09-01",
        "task_definition": {
            "unit": "one target portfolio and sixteen displayed candidate declarations",
            "selection_budget": B,
            "hidden_incidence": "D(t) is the exact direct proof-body edge intersection with displayed candidates",
            "objective": "F(S) is the number of targets whose hidden incidence intersects S",
            "accepted_answers": "all size-three argmax portfolios",
            "primary_metric": "optimal-portfolio accuracy",
            "secondary_metrics": [
                "normalized target coverage F(S)/F*",
                "direct-edge recall sum_t |D(t) intersection S| / sum_t |D(t)|",
            ],
            "validity_boundary": "historical direct-body dependency coverage, not causal lemma utility",
            "blindness_boundary": "the source declarations are public Mathlib theorems; only the newly composed episodes, hidden incidence labels, and post-freeze model evaluation are sealed",
        },
        "construction": {
            "config_sha256": sha256_bytes(config_bytes),
            "private_selection_ledger_sha256": selection_ledger_sha256,
            "all_displayed_candidates_recurrent_in_corpus": True,
            "pinned_lean_excluded_module_hashes": sorted(
                PINNED_LEAN_EXCLUDED_MODULE_HASHES
            ),
            "construction_gated_method_optimal_hits": 0,
            "split_selection": "fixed-seed SHA-256 rank with a top-level-domain cap",
            "evaluated_blind_predictions_read_or_used_by_builder": 0,
            "development_assistance": (
                "Codex agents assisted design/code; authors are responsible; item "
                "admission is deterministic and no blind evaluation prediction enters it."
            ),
            "prior_deduplication": "module hashes plus exact and leading-binder-alpha statement signatures against v1, rejected v2, and v3",
        },
        "generation_receipt": {
            "file": "generation_receipt.json",
            "sha256": sha256_bytes(generation_receipt_bytes),
            "binds_all_256_parquet_file_names_sizes_and_sha256": True,
        },
        "committed_public_construction_diagnostics": {
            "file": "gated_construction_diagnostics.json",
            "sha256": sha256_bytes(diagnostics_bytes),
            "method_count_per_episode": 18,
            "labels_read": 0,
            "evaluated_blind_predictions_read": 0,
            "report_as_independent_baseline": False,
        },
        "splits": {
            "calibration": {
                "benchmark_id": CALIBRATION_ID,
                "episodes": len(calibration_public),
                "public_file": "calibration.public.jsonl",
                "public_sha256": sha256_bytes(payloads["calibration_public"]),
                "label_commitment_sha256": sha256_bytes(payloads["calibration_labels"]),
                "development_batches": {
                    "A": {
                        "inclusive_episode_id_range": ["MLP4C_0000", "MLP4C_0014"],
                        "episodes": 15,
                        "public_file": "calibration_a.public.jsonl",
                        "public_sha256": sha256_bytes(payloads["calibration_a_public"]),
                        "labels_file": "calibration_a.labels.jsonl",
                        "labels_sha256": sha256_bytes(payloads["calibration_a_labels"]),
                    },
                    "B": {
                        "inclusive_episode_id_range": ["MLP4C_0015", "MLP4C_0029"],
                        "episodes": 15,
                        "public_file": "calibration_b.public.jsonl",
                        "public_sha256": sha256_bytes(payloads["calibration_b_public"]),
                        "labels_file": "calibration_b.labels.jsonl",
                        "labels_sha256": sha256_bytes(payloads["calibration_b_labels"]),
                    },
                },
            },
            "blind": {
                "benchmark_id": BLIND_ID,
                "episodes": len(blind_public),
                "public_file": "blind.public.jsonl",
                "public_sha256": sha256_bytes(payloads["blind_public"]),
                "label_commitment_sha256": sha256_bytes(payloads["blind_labels"]),
            },
        },
        "summary": summary,
        "label_protocol": {
            "blind_labels_in_public_directory": False,
            "calibration_labels_release": "separate public development artifact; never included in blind model packets",
            "private_file_mode": "0600",
            "open_blind_labels_only_after_all_blind_outputs_are_frozen": True,
            "no_blind_scoring_before_output_panel_closure": True,
        },
        "audit_status": {
            "parquet_graph_validation": "pass",
            "pinned_lean_module_exclusion_count": len(
                PINNED_LEAN_EXCLUDED_MODULE_HASHES
            ),
            "exact_pinned_lean_direct_value_reextraction": (
                "preflight_pass_on_hash-locked_final bytes; independent "
                "post-materialization receipt pending"
            ),
            "pinned_lean_audit_script": "audit_pinned_lean.py",
            "blind_frontier_inference": "not_started_at_local_freeze",
        },
    }
    manifest_bytes = canonical_json_bytes(manifest)
    private_manifest = {
        "schema_version": "lemma-portfolio.dependency-compression-private.v4",
        "status": "SEALED_PREINFERENCE",
        "public_manifest_sha256": sha256_bytes(manifest_bytes),
        "calibration_labels_sha256": sha256_bytes(payloads["calibration_labels"]),
        "blind_labels_sha256": sha256_bytes(payloads["blind_labels"]),
        "private_selection_ledger_sha256": selection_ledger_sha256,
        "calibration_source_modules_sha256": sha256_bytes(
            "\n".join(sorted(row["source_module"] for row in calibration_labels)).encode()
        ),
        "blind_source_modules_sha256": sha256_bytes(
            "\n".join(sorted(row["source_module"] for row in blind_labels)).encode()
        ),
    }
    # Private bytes are durably created before public commitments are exposed.
    _write_exclusive(paths["calibration_labels"], payloads["calibration_labels"], 0o644)
    _write_exclusive(paths["calibration_a_labels"], payloads["calibration_a_labels"], 0o644)
    _write_exclusive(paths["calibration_b_labels"], payloads["calibration_b_labels"], 0o644)
    _write_exclusive(paths["blind_labels"], payloads["blind_labels"], 0o600)
    _write_exclusive(paths["private_manifest"], canonical_json_bytes(private_manifest), 0o600)
    _write_exclusive(paths["calibration_public"], payloads["calibration_public"], 0o644)
    _write_exclusive(paths["calibration_a_public"], payloads["calibration_a_public"], 0o644)
    _write_exclusive(paths["calibration_b_public"], payloads["calibration_b_public"], 0o644)
    _write_exclusive(paths["blind_public"], payloads["blind_public"], 0o644)
    _write_exclusive(paths["construction_diagnostics"], diagnostics_bytes, 0o644)
    _write_exclusive(paths["generation_receipt"], generation_receipt_bytes, 0o644)
    _write_exclusive(paths["manifest"], manifest_bytes, 0o644)
    return {
        "status": "materialized",
        "public_dir": str(public_dir),
        "private_dir": str(private_dir),
        "public_manifest_sha256": sha256_bytes(manifest_bytes),
        "summary": summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet-dir", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--materialize", action="store_true")
    parser.add_argument("--public-dir", type=Path)
    parser.add_argument("--private-dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.dry_run:
        result = build_bundle(args.parquet_dir)[-1]
    else:
        require(
            args.public_dir is not None and args.private_dir is not None,
            "materialization requires --public-dir and --private-dir",
        )
        result = materialize(args.parquet_dir, args.public_dir, args.private_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
