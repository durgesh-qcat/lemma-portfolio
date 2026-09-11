#!/usr/bin/env python3
"""Fail-closed, aggregate-only audit of the Mathlib static dependency labels.

The checked-in label file necessarily contains private declaration provenance.
This reproducer keeps that provenance inside one local Lean stdin stream.  Lean
checks every target declaration value and emits only aggregate integer counters; this
wrapper never writes the generated Lean program or relays Lean diagnostics.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence


APIBENCH_ROOT = Path(__file__).resolve().parents[1]

PINNED_MATHLIB_COMMIT = "db584cd6d46c92f209a44c0f1c829460d327499d"
PINNED_LEAN_TOOLCHAIN = "leanprover/lean4:v4.33.0"
PINNED_LEAN_VERSION = "4.33.0"
PINNED_LEAN_COMMIT = "d8b18978322de05a8f3dba51ef03cf5461676c17"

DEFAULT_INPUTS = {
    "manifest": APIBENCH_ROOT / "pilot" / "mathlib_manifest.json",
    "public": APIBENCH_ROOT / "pilot" / "mathlib_public.jsonl",
    "labels": APIBENCH_ROOT / "pilot" / "mathlib_labels.jsonl",
    "responses": APIBENCH_ROOT / "pilot" / "model_gpt56sol_max_v2.json",
    "model_results": APIBENCH_ROOT / "pilot" / "static_model_results_v2.json",
    "baseline_summary": APIBENCH_ROOT / "pilot" / "static_baselines_v5_summary.json",
}

EXPECTED_INPUT_HASHES = {
    "public": "f59cfa80bdfffa5dfd487d89c087604b885e24945ca29d774b0ad06a123b8796",
    "labels": "aa80f0ecafb3fda1d56b96707d12e1a21fd5570c9632a444f3344d8296e290ad",
    "responses": "70afb44817776f81e2a9c074b1389099b6c5af673b8dffa146e6dae67105c51d",
    "model_results": "3d5da3a19371eccb44abc396226a156af0bb94e1de7cb52f548d62fb3b9f5bfa",
    "baseline_summary": "8cf367831ed35881786d0004034409f674c3704c3f8fa3df3a53b402b567e83c",
}

EXPECTED_LEAN_AGGREGATE = {
    "added_edges": 0,
    "axiom_targets": 0,
    "changed_episodes": 0,
    "changed_targets": 0,
    "constructor_targets": 0,
    "definition_targets": 8,
    "direct_value_edges": 183,
    "empty_targets": 0,
    "inductive_targets": 0,
    "old_edges": 183,
    "opaque_targets": 0,
    "quotient_targets": 0,
    "recursor_targets": 0,
    "removed_edges": 0,
    "reports": 166,
    "theorem_targets": 158,
}

EXPECTED_AGGREGATE = {
    "changed_episodes": 0,
    "changed_targets": 0,
    "corrected_model_exact_count": 21,
    "corrected_model_exact_rate": 0.7,
    "corrected_model_hit_count_dist": {"0": 3, "1": 6, "2": 21},
    "corrected_model_macro_author_coverage": 0.8,
    "corrected_model_macro_reuse_coverage": 0.8,
    "corrected_model_oracle_normalized_macro_reuse": 0.8,
    "corrected_model_utility_dist": {"0.0": 3, "0.5": 6, "1.0": 21},
    "corrected_oracle_macro_author_coverage": 1.0,
    "corrected_oracle_macro_reuse_coverage": 1.0,
    "direct_value_edges": 183,
    "empty_targets": 0,
    "episode_change_count_dist": {"0": 30},
    "old_edges": 183,
    "removed_edges": 0,
    "reports": 166,
}

EXPECTED_AGGREGATE_SHA256 = (
    "9f19c75998fe957ba21c22de90c82c19f121188bf9d480bcfbc891b53660d7aa"
)

_LEAN_OUTPUT_KEYS = frozenset(EXPECTED_LEAN_AGGREGATE)
_LEAN_VERSION = re.compile(
    rf"^Lean \(version {re.escape(PINNED_LEAN_VERSION)}, .*?, "
    rf"commit {PINNED_LEAN_COMMIT}, Release\)\n?$"
)


class AuditError(RuntimeError):
    """A deliberately provenance-free, safe-to-display audit failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError("an input contains a duplicate JSON object key")
        result[key] = value
    return result


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicates,
        )
    except AuditError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"{label} input is unreadable or invalid") from error


def _load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise AuditError(f"{label} input is unreadable or invalid") from error
    rows: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_object_without_duplicates)
        except AuditError:
            raise
        except json.JSONDecodeError as error:
            raise AuditError(f"{label} input is unreadable or invalid") from error
        _require(isinstance(row, dict), f"{label} JSONL rows must be objects")
        rows.append(row)
    return rows


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("ascii")


def _verify_hash(path: Path, expected: str, label: str) -> None:
    try:
        actual = sha256_bytes(path.read_bytes())
    except OSError as error:
        raise AuditError(f"{label} input is unreadable") from error
    _require(actual == expected, f"{label} input SHA-256 mismatch")


def _run_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
    timeout: int = 300,
    failure: str,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            env=env,
            input=stdin,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AuditError(failure) from error
    _require(result.returncode == 0, failure)
    return result


def verify_environment(
    *,
    mathlib_checkout: Path,
    lean_project: Path,
    lake: Path,
    elan_home: Path | None,
) -> dict[str, str]:
    """Verify that Lake will load the clean, pinned checkout with pinned Lean."""

    try:
        checkout = mathlib_checkout.resolve(strict=True)
        project = lean_project.resolve(strict=True)
        lake_binary = lake.resolve(strict=True)
    except OSError as error:
        raise AuditError("an explicit environment path does not exist") from error
    _require(checkout.is_dir(), "the Mathlib checkout path is not a directory")
    _require(project.is_dir(), "the Lean project path is not a directory")
    _require(lake_binary.is_file(), "the Lake path is not a file")

    top = _run_checked(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=checkout,
        failure="Mathlib Git identity check failed",
    ).stdout.strip()
    try:
        top_path = Path(top).resolve(strict=True)
    except OSError as error:
        raise AuditError("Mathlib Git identity check failed") from error
    _require(top_path == checkout, "Mathlib path is not the supplied Git root")

    head = _run_checked(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        failure="Mathlib commit check failed",
    ).stdout.strip()
    _require(head == PINNED_MATHLIB_COMMIT, "Mathlib commit mismatch")
    status = _run_checked(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=checkout,
        failure="Mathlib cleanliness check failed",
    ).stdout
    _require(not status.strip(), "Mathlib has tracked worktree changes")

    for root, label in ((checkout, "Mathlib"), (project, "Lean project")):
        try:
            toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as error:
            raise AuditError(f"{label} toolchain file is unreadable") from error
        _require(toolchain == PINNED_LEAN_TOOLCHAIN, f"{label} toolchain mismatch")

    manifest = _load_json(project / "lake-manifest.json", "Lean project manifest")
    _require(isinstance(manifest, dict), "Lean project manifest must be an object")
    packages = manifest.get("packages")
    _require(isinstance(packages, list), "Lean project manifest packages are invalid")
    mathlib_packages = [
        package
        for package in packages
        if isinstance(package, dict) and package.get("name") == "mathlib"
    ]
    _require(len(mathlib_packages) == 1, "Lean project must resolve one Mathlib package")
    _require(
        mathlib_packages[0].get("rev") == PINNED_MATHLIB_COMMIT,
        "Lean project Mathlib revision mismatch",
    )
    packages_dir = manifest.get("packagesDir")
    _require(isinstance(packages_dir, str) and packages_dir, "packagesDir is invalid")
    try:
        resolved_package = (project / packages_dir / "mathlib").resolve(strict=True)
    except OSError as error:
        raise AuditError("Lean project Mathlib package path is unavailable") from error
    _require(
        resolved_package == checkout,
        "Lean project does not resolve the explicitly supplied Mathlib checkout",
    )

    environment = os.environ.copy()
    if elan_home is not None:
        try:
            resolved_elan = elan_home.resolve(strict=True)
        except OSError as error:
            raise AuditError("the explicit ELAN_HOME path does not exist") from error
        _require(resolved_elan.is_dir(), "the explicit ELAN_HOME path is not a directory")
        environment["ELAN_HOME"] = str(resolved_elan)
    version = _run_checked(
        [str(lake_binary), "env", "lean", "--version"],
        cwd=project,
        env=environment,
        failure="Lean version check failed",
    ).stdout
    _require(_LEAN_VERSION.fullmatch(version) is not None, "Lean version/commit mismatch")
    return environment


@dataclass(frozen=True)
class Corpus:
    public: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    responses: dict[str, dict[str, Any]]


def load_and_validate_inputs(paths: dict[str, Path]) -> Corpus:
    for label, expected in EXPECTED_INPUT_HASHES.items():
        _verify_hash(paths[label], expected, label)

    manifest = _load_json(paths["manifest"], "Mathlib manifest")
    _require(isinstance(manifest, dict), "Mathlib manifest must be an object")
    source = manifest.get("source")
    hashes = manifest.get("hashes")
    _require(isinstance(source, dict), "Mathlib source metadata is invalid")
    _require(isinstance(hashes, dict), "Mathlib hash metadata is invalid")
    _require(
        source.get("mathlib_commit") == PINNED_MATHLIB_COMMIT,
        "Mathlib manifest commit mismatch",
    )
    _require(source.get("dataset_version") == "v4.33.0", "dataset version mismatch")
    _require(
        hashes.get("public_jsonl_sha256") == EXPECTED_INPUT_HASHES["public"],
        "manifest public hash mismatch",
    )
    _require(
        hashes.get("private_jsonl_sha256") == EXPECTED_INPUT_HASHES["labels"],
        "manifest label hash mismatch",
    )
    _require(
        hashes.get("static_baselines_v5_summary_sha256")
        == EXPECTED_INPUT_HASHES["baseline_summary"],
        "manifest baseline-summary hash mismatch",
    )

    public = _load_jsonl(paths["public"], "public")
    labels = _load_jsonl(paths["labels"], "labels")
    responses_value = _load_json(paths["responses"], "responses")
    # The two result files are hash-bound audit inputs, not trusted score sources.
    _require(
        isinstance(_load_json(paths["model_results"], "model results"), dict),
        "model results must be an object",
    )
    _require(
        isinstance(_load_json(paths["baseline_summary"], "baseline summary"), dict),
        "baseline summary must be an object",
    )
    _require(isinstance(responses_value, dict), "responses must be an object")
    responses = responses_value

    _require(len(public) == 30 and len(labels) == 30, "corpus must have 30 episodes")
    expected_episode_ids = [f"MLP_{index:04d}" for index in range(30)]
    _require(
        [row.get("episode_id") for row in public] == expected_episode_ids,
        "public episode IDs/order mismatch",
    )
    _require(
        [row.get("episode_id") for row in labels] == expected_episode_ids,
        "label episode IDs/order mismatch",
    )
    _require(set(responses) == set(expected_episode_ids), "response episode set mismatch")

    all_candidates: list[str] = []
    all_targets: list[str] = []
    target_count = 0
    old_edge_count = 0
    candidate_ids = [f"C{index:02d}" for index in range(1, 13)]
    for public_episode, label_episode in zip(public, labels, strict=True):
        episode_id = public_episode["episode_id"]
        _require(public_episode.get("budget") == 2, "public budget mismatch")
        public_candidates = public_episode.get("candidates")
        public_targets = public_episode.get("targets")
        candidate_sources = label_episode.get("candidate_sources")
        target_sources = label_episode.get("target_sources")
        label_targets = label_episode.get("targets")
        oracle = label_episode.get("oracle_helpers")
        _require(isinstance(public_candidates, list), "public candidates are invalid")
        _require(isinstance(public_targets, list), "public targets are invalid")
        _require(isinstance(candidate_sources, dict), "candidate provenance is invalid")
        _require(isinstance(target_sources, dict), "target provenance is invalid")
        _require(isinstance(label_targets, list), "target labels are invalid")
        _require(isinstance(oracle, list), "oracle portfolio is invalid")
        _require(
            [row.get("id") for row in public_candidates if isinstance(row, dict)]
            == candidate_ids,
            "candidate IDs/order mismatch",
        )
        _require(set(candidate_sources) == set(candidate_ids), "candidate map mismatch")
        target_ids = [row.get("id") for row in public_targets if isinstance(row, dict)]
        _require(len(target_ids) in {4, 5, 6}, "target count is invalid")
        _require(len(set(target_ids)) == len(target_ids), "target IDs are duplicated")
        _require(set(target_sources) == set(target_ids), "target map mismatch")
        _require(
            [row.get("id") for row in label_targets if isinstance(row, dict)] == target_ids,
            "target label IDs/order mismatch",
        )
        _require(
            len(oracle) == 2 and len(set(oracle)) == 2 and set(oracle) <= set(candidate_ids),
            "oracle portfolio is invalid",
        )
        candidate_values = list(candidate_sources.values())
        target_values = list(target_sources.values())
        _require(
            all(isinstance(value, str) and value for value in candidate_values),
            "candidate provenance values are invalid",
        )
        _require(
            all(isinstance(value, str) and value for value in target_values),
            "target provenance values are invalid",
        )
        all_candidates.extend(candidate_values)
        all_targets.extend(target_values)
        for target in label_targets:
            _require(isinstance(target, dict), "target label is invalid")
            required = target.get("required_candidates")
            _require(
                isinstance(required, list)
                and required
                and len(required) == len(set(required))
                and set(required) <= set(candidate_ids),
                "target requirements are invalid",
            )
            old_edge_count += len(required)
            target_count += 1
        response = responses.get(episode_id)
        _require(isinstance(response, dict), "model response is invalid")
        selected = response.get("selected")
        _require(
            isinstance(selected, list)
            and len(selected) == 2
            and len(set(selected)) == 2
            and set(selected) <= set(candidate_ids),
            "model selection is invalid",
        )

    _require(target_count == 166, "target total mismatch")
    _require(old_edge_count == 183, "old dependency-edge total mismatch")
    _require(
        len(all_candidates) == len(set(all_candidates)) == 360,
        "candidate declarations must be globally unique",
    )
    _require(
        len(all_targets) == len(set(all_targets)) == 166,
        "target declarations must be globally unique",
    )
    _require(not set(all_candidates).intersection(all_targets), "target/candidate overlap")
    return Corpus(public=public, labels=labels, responses=responses)


def _lean_string(value: str) -> str:
    _require(
        not any(ord(character) < 0x20 for character in value),
        "Lean provenance string contains a control character",
    )
    return json.dumps(value, ensure_ascii=False)


def _lean_array(values: Sequence[str]) -> str:
    return "#[" + ", ".join(_lean_string(value) for value in values) + "]"


def render_lean_program(corpus: Corpus) -> str:
    """Create the private stdin program; callers must never persist or print it."""

    episodes: list[str] = []
    for label_episode in corpus.labels:
        candidate_sources = label_episode["candidate_sources"]
        target_sources = label_episode["target_sources"]
        targets: list[str] = []
        for target in label_episode["targets"]:
            expected = [candidate_sources[item] for item in target["required_candidates"]]
            targets.append(
                "{ declaration := "
                + _lean_string(target_sources[target["id"]])
                + ", expected := "
                + _lean_array(expected)
                + " }"
            )
        episodes.append(
            "{ candidates := "
            + _lean_array([candidate_sources[f"C{index:02d}"] for index in range(1, 13)])
            + ", targets := #["
            + ", ".join(targets)
            + "] }"
        )

    return """import Mathlib
import Lean.Util.FoldConsts

meta section

open Lean Lean.Elab Lean.Elab.Command

structure AuditTarget where
  declaration : String
  expected : Array String

structure AuditEpisode where
  candidates : Array String
  targets : Array AuditTarget

def auditEpisodes : Array AuditEpisode := #[
  """ + ",\n  ".join(episodes) + """
]

def sameStringSet (left right : Array String) : Bool :=
  left.size == right.size && left.all (fun value => right.contains value)

syntax (name := staticDependencyAuditCommand) "#static_dependency_audit" : command

@[command_elab staticDependencyAuditCommand]
def elabStaticDependencyAudit : CommandElab
  | `(#static_dependency_audit) => do
      let environment ← getEnv
      let mut reports : Nat := 0
      let mut edges : Nat := 0
      let mut oldEdges : Nat := 0
      let mut changedTargets : Nat := 0
      let mut changedEpisodes : Nat := 0
      let mut removedEdges : Nat := 0
      let mut addedEdges : Nat := 0
      let mut emptyTargets : Nat := 0
      let mut axiomTargets : Nat := 0
      let mut definitionTargets : Nat := 0
      let mut theoremTargets : Nat := 0
      let mut opaqueTargets : Nat := 0
      let mut quotientTargets : Nat := 0
      let mut inductiveTargets : Nat := 0
      let mut constructorTargets : Nat := 0
      let mut recursorTargets : Nat := 0
      for episode in auditEpisodes do
        let mut episodeChanged := false
        for target in episode.targets do
          let declaration := target.declaration.toName
          let some information := environment.find? declaration
            | throwError "unknown target declaration"
          match information with
          | .axiomInfo _ => axiomTargets := axiomTargets + 1
          | .defnInfo _ => definitionTargets := definitionTargets + 1
          | .thmInfo _ => theoremTargets := theoremTargets + 1
          | .opaqueInfo _ => opaqueTargets := opaqueTargets + 1
          | .quotInfo _ => quotientTargets := quotientTargets + 1
          | .inductInfo _ => inductiveTargets := inductiveTargets + 1
          | .ctorInfo _ => constructorTargets := constructorTargets + 1
          | .recInfo _ => recursorTargets := recursorTargets + 1
          let some value := information.value? (allowOpaque := true)
            | throwError "target theorem has no accessible value"
          let directValue := value.getUsedConstantsAsSet
          let matched := directValue.toArray.map (fun name => name.toString)
            |>.filter fun name => episode.candidates.contains name
          reports := reports + 1
          edges := edges + matched.size
          oldEdges := oldEdges + target.expected.size
          if matched.isEmpty then emptyTargets := emptyTargets + 1
          let removed := target.expected.filter fun name => !matched.contains name
          let added := matched.filter fun name => !target.expected.contains name
          removedEdges := removedEdges + removed.size
          addedEdges := addedEdges + added.size
          if !sameStringSet matched target.expected then
            changedTargets := changedTargets + 1
            episodeChanged := true
        if episodeChanged then changedEpisodes := changedEpisodes + 1
      IO.println <| (Json.mkObj [
        ("reports", toJson reports),
        ("direct_value_edges", toJson edges),
        ("old_edges", toJson oldEdges),
        ("changed_targets", toJson changedTargets),
        ("changed_episodes", toJson changedEpisodes),
        ("removed_edges", toJson removedEdges),
        ("added_edges", toJson addedEdges),
        ("empty_targets", toJson emptyTargets),
        ("axiom_targets", toJson axiomTargets),
        ("definition_targets", toJson definitionTargets),
        ("theorem_targets", toJson theoremTargets),
        ("opaque_targets", toJson opaqueTargets),
        ("quotient_targets", toJson quotientTargets),
        ("inductive_targets", toJson inductiveTargets),
        ("constructor_targets", toJson constructorTargets),
        ("recursor_targets", toJson recursorTargets)
      ]).compress
  | _ => throwUnsupportedSyntax

#static_dependency_audit
"""


def parse_lean_aggregate(stdout: str) -> dict[str, int]:
    """Accept exactly one aggregate-only JSON line and no declaration payload."""

    lines = stdout.splitlines()
    _require(len(lines) == 1 and bool(lines[0]), "Lean output is not one aggregate line")
    try:
        value = json.loads(lines[0], object_pairs_hook=_object_without_duplicates)
    except AuditError:
        raise
    except json.JSONDecodeError as error:
        raise AuditError("Lean output is not valid aggregate JSON") from error
    _require(isinstance(value, dict), "Lean aggregate must be an object")
    _require(set(value) == _LEAN_OUTPUT_KEYS, "Lean aggregate schema mismatch")
    _require(
        all(type(item) is int and item >= 0 for item in value.values()),
        "Lean aggregate values must be nonnegative integers",
    )
    return value


def run_lean_extraction(
    *,
    corpus: Corpus,
    lean_project: Path,
    lake: Path,
    environment: dict[str, str],
    timeout: int,
) -> dict[str, int]:
    source = render_lean_program(corpus)
    result = _run_checked(
        [str(lake.resolve()), "env", "lean", "--stdin"],
        cwd=lean_project.resolve(),
        env=environment,
        stdin=source,
        timeout=timeout,
        failure="Lean dependency extraction failed; diagnostics suppressed",
    )
    aggregate = parse_lean_aggregate(result.stdout)
    _require(not result.stderr.strip(), "Lean emitted unexpected diagnostics")
    _require(aggregate == EXPECTED_LEAN_AGGREGATE, "Lean aggregate mismatch")
    return aggregate


def _coverage(
    selected: frozenset[str], requirements: list[frozenset[str]]
) -> frozenset[int]:
    return frozenset(
        index
        for index, required in enumerate(requirements)
        if required and required.issubset(selected)
    )


def _reuse_coverage(
    selected: frozenset[str], requirements: list[frozenset[str]]
) -> frozenset[int]:
    covered = _coverage(selected, requirements)
    reused = {
        candidate
        for candidate in selected
        if sum(candidate in requirements[index] for index in covered) >= 2
    }
    return frozenset(
        index for index in covered if requirements[index].intersection(reused)
    )


def _oracle_selection(
    candidate_ids: list[str], requirements: list[frozenset[str]]
) -> frozenset[str]:
    best_score: tuple[int, int, int, tuple[str, ...]] | None = None
    best = frozenset[str]()
    for size in range(3):
        for values in itertools.combinations(candidate_ids, size):
            selected = frozenset(values)
            candidate_score = (
                len(_reuse_coverage(selected, requirements)),
                len(_coverage(selected, requirements)),
                -size,
                tuple(sorted(selected)),
            )
            if best_score is None or candidate_score > best_score:
                best_score = candidate_score
                best = selected
    return best


def compute_canonical_aggregate(
    corpus: Corpus, lean_aggregate: dict[str, int]
) -> dict[str, Any]:
    _require(lean_aggregate == EXPECTED_LEAN_AGGREGATE, "Lean aggregate mismatch")
    exact_count = 0
    hit_count: Counter[int] = Counter()
    utility: Counter[Fraction] = Counter()
    model_author: list[Fraction] = []
    model_reuse: list[Fraction] = []
    oracle_author: list[Fraction] = []
    oracle_reuse: list[Fraction] = []
    candidate_ids = [f"C{index:02d}" for index in range(1, 13)]

    for public_episode, label_episode in zip(corpus.public, corpus.labels, strict=True):
        requirements = [
            frozenset(target["required_candidates"])
            for target in label_episode["targets"]
        ]
        selected = frozenset(corpus.responses[public_episode["episode_id"]]["selected"])
        oracle = _oracle_selection(candidate_ids, requirements)
        denominator = len(requirements)
        model_covered = _coverage(selected, requirements)
        model_reused = _reuse_coverage(selected, requirements)
        oracle_covered = _coverage(oracle, requirements)
        oracle_reused = _reuse_coverage(oracle, requirements)
        author_value = Fraction(len(model_covered), denominator)
        reuse_value = Fraction(len(model_reused), denominator)
        exact_count += int(selected == oracle)
        hit_count[len(selected.intersection(oracle))] += 1
        utility[author_value] += 1
        model_author.append(author_value)
        model_reuse.append(reuse_value)
        oracle_author.append(Fraction(len(oracle_covered), denominator))
        oracle_reuse.append(Fraction(len(oracle_reused), denominator))

    episode_count = len(corpus.public)
    model_author_macro = sum(model_author, Fraction()) / episode_count
    model_reuse_macro = sum(model_reuse, Fraction()) / episode_count
    oracle_author_macro = sum(oracle_author, Fraction()) / episode_count
    oracle_reuse_macro = sum(oracle_reuse, Fraction()) / episode_count
    _require(oracle_reuse_macro > 0, "oracle reuse denominator is zero")

    aggregate: dict[str, Any] = {
        "changed_episodes": lean_aggregate["changed_episodes"],
        "changed_targets": lean_aggregate["changed_targets"],
        "corrected_model_exact_count": exact_count,
        "corrected_model_exact_rate": float(Fraction(exact_count, episode_count)),
        "corrected_model_hit_count_dist": {
            str(index): hit_count[index] for index in range(3)
        },
        "corrected_model_macro_author_coverage": float(model_author_macro),
        "corrected_model_macro_reuse_coverage": float(model_reuse_macro),
        "corrected_model_oracle_normalized_macro_reuse": float(
            model_reuse_macro / oracle_reuse_macro
        ),
        "corrected_model_utility_dist": {
            str(float(value)): utility[value] for value in sorted(utility)
        },
        "corrected_oracle_macro_author_coverage": float(oracle_author_macro),
        "corrected_oracle_macro_reuse_coverage": float(oracle_reuse_macro),
        "direct_value_edges": lean_aggregate["direct_value_edges"],
        "empty_targets": lean_aggregate["empty_targets"],
        "episode_change_count_dist": {"0": episode_count},
        "old_edges": lean_aggregate["old_edges"],
        "removed_edges": lean_aggregate["removed_edges"],
        "reports": lean_aggregate["reports"],
    }
    _require(aggregate == EXPECTED_AGGREGATE, "canonical aggregate mismatch")
    rendered = canonical_bytes(aggregate)
    _require(
        sha256_bytes(rendered) == EXPECTED_AGGREGATE_SHA256,
        "canonical aggregate SHA-256 mismatch",
    )
    return aggregate


def audit(
    *,
    paths: dict[str, Path],
    mathlib_checkout: Path,
    lean_project: Path,
    lake: Path,
    elan_home: Path | None,
    timeout: int,
) -> bytes:
    corpus = load_and_validate_inputs(paths)
    environment = verify_environment(
        mathlib_checkout=mathlib_checkout,
        lean_project=lean_project,
        lake=lake,
        elan_home=elan_home,
    )
    lean_aggregate = run_lean_extraction(
        corpus=corpus,
        lean_project=lean_project,
        lake=lake,
        environment=environment,
        timeout=timeout,
    )
    aggregate = compute_canonical_aggregate(corpus, lean_aggregate)
    return canonical_bytes(aggregate)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Re-extract and aggregate-audit the 30-episode Mathlib pilot",
    )
    parser.add_argument("--mathlib-checkout", type=Path, required=True)
    parser.add_argument("--lean-project", type=Path, required=True)
    parser.add_argument("--lake", type=Path, required=True)
    parser.add_argument("--elan-home", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_INPUTS["manifest"])
    parser.add_argument("--public", type=Path, default=DEFAULT_INPUTS["public"])
    parser.add_argument("--labels", type=Path, default=DEFAULT_INPUTS["labels"])
    parser.add_argument("--responses", type=Path, default=DEFAULT_INPUTS["responses"])
    parser.add_argument(
        "--model-results", type=Path, default=DEFAULT_INPUTS["model_results"]
    )
    parser.add_argument(
        "--baseline-summary", type=Path, default=DEFAULT_INPUTS["baseline_summary"]
    )
    parser.add_argument("--timeout", type=int, default=300)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    paths = {
        "manifest": args.manifest,
        "public": args.public,
        "labels": args.labels,
        "responses": args.responses,
        "model_results": args.model_results,
        "baseline_summary": args.baseline_summary,
    }
    try:
        output = audit(
            paths=paths,
            mathlib_checkout=args.mathlib_checkout,
            lean_project=args.lean_project,
            lake=args.lake,
            elan_home=args.elan_home,
            timeout=args.timeout,
        )
    except AuditError as error:
        parser.exit(2, f"error: {error}\n")
    except Exception:
        # Never leak private provenance through an unexpected parser/tool error.
        parser.exit(2, "error: static dependency audit failed closed\n")
    sys.stdout.buffer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
