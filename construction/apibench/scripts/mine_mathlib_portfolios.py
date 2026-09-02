#!/usr/bin/env python3
"""Mine static LemmaPortfolio episodes from Mathlib dependency/type Parquet files.

This is a fast corpus-construction pass, not the causal prover evaluator.  It
uses direct elaborated constant dependencies, removes dependencies already
visible in target statements, and constructs multi-helper portfolios whose
gold helpers are reused by multiple targets.  Final paper episodes still need
cutoff replay and paired prover validation.

DuckDB is the only non-stdlib dependency.  The Mathlib Initiative datasets are
documented at:
  https://huggingface.co/datasets/mathlib-initiative/mathlib-const-dep
  https://huggingface.co/datasets/mathlib-initiative/mathlib-types

The frozen LemmaPortfolio-30 v1 release predates the rejection of obviously
reflexive declarations.  Use ``--generation-profile mathlib-30-v1`` to replay
that release exactly.  The stricter profile remains the default for future
generation; profile changes must produce a new benchmark version.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import re
from typing import Any, Iterable

try:
    import duckdb
except ImportError:  # Pure mining/scoring helpers remain importable for tests.
    duckdb = None  # type: ignore[assignment]


INTERNAL_NAME = re.compile(r"(?:^|\.)(?:_proof|_aux|_simp|eq_[0-9]+)(?:_|\.|$)")
TYPE_TOKEN = re.compile(r"[\w\u0080-\uffff'][\w\u0080-\uffff'.]*", re.UNICODE)

V1_GENERATION_PROFILE = "mathlib-30-v1"
STRICT_GENERATION_PROFILE = "strict-current"
GENERATION_PROFILES = (V1_GENERATION_PROFILE, STRICT_GENERATION_PROFILE)

# This filter intentionally trades recall for a cleaner theorem/lemma proxy.
# Lean's Parquet export does not include ConstantInfo kind, so cutoff replay is
# the authoritative filter later.
PROP_MARKERS = (
    " = ",
    " ≠ ",
    " ↔ ",
    " ≤ ",
    " ≥ ",
    " < ",
    " > ",
    " ∈ ",
    " ∉ ",
    " ⊆ ",
    " → False",
)
PROP_HEADS = (
    "Continuous ",
    "ContinuousAt ",
    "Measurable ",
    "AEMeasurable ",
    "Monotone ",
    "Antitone ",
    "Injective ",
    "Surjective ",
    "Bijective ",
    "Finite ",
    "IsOpen ",
    "IsClosed ",
    "Differentiable ",
    "Summable ",
    "Tendsto ",
    "Pairwise ",
    "Disjoint ",
    "Nonempty ",
    "Function.Injective ",
    "Function.Surjective ",
    "Function.Bijective ",
)


@dataclass(frozen=True)
class Declaration:
    name: str
    module: str
    type: str
    doc: str | None
    deps: frozenset[str]


def parquet_expression(paths: list[Path]) -> str:
    escaped = [str(path).replace("'", "''") for path in paths]
    return "read_parquet([" + ",".join(f"'{path}'" for path in escaped) + "])"


def load_declarations(dep_paths: list[Path], type_paths: list[Path]) -> dict[str, Declaration]:
    if duckdb is None:  # pragma: no cover - exercised by dependency-light CLI users
        raise RuntimeError("DuckDB is required to read Parquet: python -m pip install duckdb")
    if not dep_paths or not type_paths:
        raise ValueError("dependency and type Parquet paths must both be nonempty")
    connection = duckdb.connect()
    dep_relation = parquet_expression(dep_paths)
    type_relation = parquet_expression(type_paths)
    query = f"""
        SELECT d.name, d.module, t.type, t.docString, d.deps
        FROM {dep_relation} d
        JOIN {type_relation} t USING (name, module)
        WHERE d.allowCompletion AND t.allowCompletion
          AND d.module LIKE 'Mathlib.%'
    """
    declarations: dict[str, Declaration] = {}
    for name, module, type_text, doc, deps in connection.execute(query).fetchall():
        if not all(isinstance(value, str) for value in (name, module, type_text)):
            continue
        declarations[name] = Declaration(
            name=name,
            module=module,
            type=type_text,
            doc=doc if isinstance(doc, str) else None,
            deps=frozenset(deps or []),
        )
    return declarations


def clean_public_name(name: str) -> bool:
    return (
        not name.startswith("_")
        and "._" not in name
        and not INTERNAL_NAME.search(name)
        and not name.split(".")[-1].startswith("inst")
    )


def _body_after_forall(text: str) -> str:
    """Drop one leading pretty-printed `forall` binder group."""

    if not text.startswith("∀ "):
        return text
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    for index, character in enumerate(text[2:], start=2):
        if character in pairs:
            depth += 1
        elif character in closers:
            depth -= 1
        elif character == "," and depth == 0:
            return text[index + 1 :].strip()
    return text


def proposition_conclusion(type_text: str) -> str:
    """Approximate the outer conclusion of a Lean pretty-printed type."""

    text = " ".join(type_text.split())
    previous = None
    while text != previous and text.startswith("∀ "):
        previous = text
        text = _body_after_forall(text)

    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    last_arrow = -1
    for index, character in enumerate(text):
        if character in pairs:
            depth += 1
        elif character in closers:
            depth -= 1
        elif (
            character == "→"
            and depth == 0
            and index + 1 < len(text)
            and text[index + 1].isspace()
        ):
            last_arrow = index
    if last_arrow >= 0:
        return text[last_arrow + 1 :].strip()
    return text


def proposition_like(type_text: str) -> bool:
    if not 20 <= len(type_text) <= 1800 or "⋯" in type_text:
        return False
    conclusion = proposition_conclusion(type_text)
    if any(marker in conclusion for marker in PROP_MARKERS):
        return True
    return (
        conclusion.startswith(PROP_HEADS)
        or conclusion.startswith("¬ ")
        or ".Is" in conclusion[:120]
    )


def obviously_reflexive(type_text: str) -> bool:
    """Reject pretty-printed conclusions whose two equality sides are identical."""

    conclusion = proposition_conclusion(type_text)
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = set(pairs.values())
    equality_positions: list[int] = []
    for index, character in enumerate(conclusion):
        if character in pairs:
            depth += 1
        elif character in closers:
            depth -= 1
        elif (
            character == "="
            and depth == 0
            and index > 0
            and index + 1 < len(conclusion)
            and conclusion[index - 1].isspace()
            and conclusion[index + 1].isspace()
        ):
            equality_positions.append(index)
    if len(equality_positions) != 1:
        return False
    index = equality_positions[0]
    normalize = lambda text: " ".join(text.split())
    return normalize(conclusion[:index]) == normalize(conclusion[index + 1 :])


def type_name_tokens(type_text: str) -> frozenset[str]:
    tokens: set[str] = set()
    for token in TYPE_TOKEN.findall(type_text):
        normalized = token.strip(".'")
        if not normalized:
            continue
        tokens.add(normalized)
        tokens.add(normalized.split(".")[-1])
    return frozenset(tokens)


def name_visible_in_type(name: str, type_text: str) -> bool:
    """Conservatively detect a dependency that belongs to the statement."""

    tokens = type_name_tokens(type_text)
    return name in tokens or name.split(".")[-1] in tokens


def proof_only_edges(
    declarations: dict[str, Declaration],
    *,
    generation_profile: str = STRICT_GENERATION_PROFILE,
) -> dict[str, frozenset[str]]:
    if generation_profile not in GENERATION_PROFILES:
        raise ValueError(f"unknown generation profile: {generation_profile}")
    reject_obvious_reflexivity = generation_profile == STRICT_GENERATION_PROFILE
    eligible = {
        name
        for name, declaration in declarations.items()
        if clean_public_name(name)
        and proposition_like(declaration.type)
        and (
            not reject_obvious_reflexivity
            or not obviously_reflexive(declaration.type)
        )
    }
    result: dict[str, frozenset[str]] = {}
    for target in declarations.values():
        if target.name not in eligible:
            continue
        visible = type_name_tokens(target.type)
        result[target.name] = frozenset(
            dependency
            for dependency in target.deps
            if dependency in eligible
            and declarations[dependency].module == target.module
            and dependency not in visible
            and dependency.split(".")[-1] not in visible
        )
    return result


def stable_token(seed: str, *parts: str) -> int:
    digest = hashlib.sha256("\0".join((seed, *parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def choose_episode(
    module: str,
    declarations: dict[str, Declaration],
    edges: dict[str, frozenset[str]],
    *,
    seed: str,
    episode_index: int,
    candidate_count: int,
    target_count: int,
    budget: int,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    module_names = sorted(
        name
        for name, declaration in declarations.items()
        if declaration.module == module and name in edges
    )
    reverse: dict[str, set[str]] = defaultdict(set)
    for target in module_names:
        for helper in edges[target]:
            reverse[helper].add(target)

    hubs = [
        helper
        for helper, consumers in reverse.items()
        if helper in module_names and len(consumers) >= 2
    ]
    hubs.sort(
        key=lambda helper: (
            -min(len(reverse[helper]), target_count),
            stable_token(seed, module, helper),
        )
    )
    if len(hubs) < budget:
        return None

    # Pick helpers greedily for complementary, reusable target coverage.
    chosen_helpers: list[str] = []
    chosen_targets: set[str] = set()
    for _ in range(budget):
        eligible = [helper for helper in hubs if helper not in chosen_helpers]
        if not eligible:
            return None
        helper = max(
            eligible,
            key=lambda item: (
                min(len(reverse[item] - chosen_targets), 3),
                min(len(reverse[item]), 5),
                -stable_token(seed, module, item),
            ),
        )
        fresh = sorted(
            reverse[helper] - chosen_targets,
            key=lambda target: stable_token(seed, module, helper, target),
        )
        if len(fresh) < 2:
            return None
        chosen_helpers.append(helper)
        chosen_targets.update(fresh[:3])

    # Fill or trim deterministically, retaining at least two uses per helper.
    target_list = sorted(chosen_targets, key=lambda target: stable_token(seed, module, target))
    if len(target_list) > target_count:
        mandatory: set[str] = set()
        for helper in chosen_helpers:
            uses = [target for target in target_list if helper in edges[target]]
            mandatory.update(uses[:2])
        remainder = [target for target in target_list if target not in mandatory]
        target_list = list(mandatory) + remainder[: max(0, target_count - len(mandatory))]
        target_list.sort(key=lambda target: stable_token(seed, module, target))
    if len(target_list) < 4 or any(
        sum(helper in edges[target] for target in target_list) < 2
        for helper in chosen_helpers
    ):
        return None

    # Targets must not directly depend on one another.
    target_set = set(target_list)
    if any(edges[target].intersection(target_set) for target in target_list):
        return None

    used_by_targets = set().union(*(edges[target] for target in target_list))
    distractors = [
        name
        for name in module_names
        if name not in target_set
        and name not in chosen_helpers
        and name not in used_by_targets
    ]
    distractors.sort(key=lambda name: stable_token(seed, module, "distractor", name))
    if len(distractors) < candidate_count - len(chosen_helpers):
        return None
    candidate_names = chosen_helpers + distractors[: candidate_count - len(chosen_helpers)]
    candidate_names.sort(key=lambda name: stable_token(seed, module, "candidate-order", name))

    candidate_id = {name: f"C{index + 1:02d}" for index, name in enumerate(candidate_names)}
    target_id = {name: f"T{index + 1:02d}" for index, name in enumerate(target_list)}
    public = {
        "schema_version": "lemma-portfolio.static.v1",
        "episode_id": f"MLP_{episode_index:04d}",
        "source_project": "mathlib",
        "source_module_hash": hashlib.sha256(module.encode()).hexdigest()[:16],
        "budget": budget,
        "candidates": [
            {"id": candidate_id[name], "cost": 1, "statement": declarations[name].type}
            for name in candidate_names
        ],
        "targets": [
            {"id": target_id[name], "statement": declarations[name].type}
            for name in target_list
        ],
        "task": (
            f"Select at most {budget} candidate IDs whose addition would be most useful "
            "for proving the target portfolio. Return JSON: {\"selected\": [...]}"
        ),
    }
    private = {
        "episode_id": public["episode_id"],
        "source_module": module,
        "candidate_sources": {candidate_id[name]: name for name in candidate_names},
        "target_sources": {target_id[name]: name for name in target_list},
        "oracle_helpers": sorted(candidate_id[name] for name in chosen_helpers),
        "targets": [
            {
                "id": target_id[name],
                "required_candidates": sorted(
                    candidate_id[helper]
                    for helper in chosen_helpers
                    if helper in edges[name]
                ),
            }
            for name in target_list
        ],
    }
    return public, private


def mine(
    declarations: dict[str, Declaration],
    *,
    seed: str,
    count: int,
    candidate_count: int,
    target_count: int,
    budget: int,
    generation_profile: str = STRICT_GENERATION_PROFILE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    edges = proof_only_edges(
        declarations,
        generation_profile=generation_profile,
    )
    modules = sorted(
        {declaration.module for declaration in declarations.values()},
        key=lambda module: stable_token(seed, module),
    )
    public_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    for module in modules:
        result = choose_episode(
            module,
            declarations,
            edges,
            seed=seed,
            episode_index=len(public_rows),
            candidate_count=candidate_count,
            target_count=target_count,
            budget=budget,
        )
        if result is None:
            continue
        public, private = result
        public_rows.append(public)
        private_rows.append(private)
        if len(public_rows) >= count:
            break
    return public_rows, private_rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def expand_paths(patterns: list[str]) -> list[Path]:
    import glob

    return sorted(Path(path) for pattern in patterns for path in glob.glob(pattern))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deps", nargs="+", required=True, help="Parquet paths/globs")
    parser.add_argument("--types", nargs="+", required=True, help="Parquet paths/globs")
    parser.add_argument("--public-out", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--candidates", type=int, default=12)
    parser.add_argument("--targets", type=int, default=6)
    parser.add_argument("--budget", type=int, default=2)
    parser.add_argument(
        "--generation-profile",
        choices=GENERATION_PROFILES,
        default=STRICT_GENERATION_PROFILE,
        help=(
            "versioned construction profile; use mathlib-30-v1 only to replay "
            "the frozen v1 release"
        ),
    )
    args = parser.parse_args()
    if args.budget <= 0 or args.candidates < args.budget or args.targets < 4:
        parser.error("require positive budget, candidates >= budget, and targets >= 4")
    dep_paths = expand_paths(args.deps)
    type_paths = expand_paths(args.types)
    declarations = load_declarations(dep_paths, type_paths)
    public_rows, private_rows = mine(
        declarations,
        seed=args.seed,
        count=args.count,
        candidate_count=args.candidates,
        target_count=args.targets,
        budget=args.budget,
        generation_profile=args.generation_profile,
    )
    write_jsonl(args.public_out, public_rows)
    write_jsonl(args.private_out, private_rows)
    commitment = hashlib.sha256(args.private_out.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "declarations": len(declarations),
                "episodes": len(public_rows),
                "private_sha256": commitment,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
