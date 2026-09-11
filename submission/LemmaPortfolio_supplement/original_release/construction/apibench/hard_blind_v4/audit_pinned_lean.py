#!/usr/bin/env python3
"""Fail-closed, aggregate-only pinned-Lean audit for LemmaPortfolio v4.

Private declaration names are rendered only into a single Lean stdin stream.
Lean re-extracts each target's direct proof-body constants and emits exactly one
aggregate JSON line. This wrapper never writes or prints the generated program,
private labels, source modules, declaration names, or Lean diagnostics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Sequence

try:
    from apibench.hard_blind_v4 import build_hard_blind_v4 as release
    from apibench.scripts import audit_static_direct_value_labels as lean_audit
except ImportError:  # Direct execution from this directory.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from apibench.hard_blind_v4 import build_hard_blind_v4 as release
    from apibench.scripts import audit_static_direct_value_labels as lean_audit


AGGREGATE_KEYS = frozenset(
    {
        "reports",
        "candidate_declarations",
        "target_declarations",
        "direct_value_edges",
        "old_edges",
        "changed_targets",
        "changed_episodes",
        "removed_edges",
        "added_edges",
        "empty_targets",
        "candidate_axiom_declarations",
        "candidate_definition_declarations",
        "candidate_theorem_declarations",
        "candidate_opaque_declarations",
        "candidate_quotient_declarations",
        "candidate_inductive_declarations",
        "candidate_constructor_declarations",
        "candidate_recursor_declarations",
        "target_axiom_declarations",
        "target_definition_declarations",
        "target_theorem_declarations",
        "target_opaque_declarations",
        "target_quotient_declarations",
        "target_inductive_declarations",
        "target_constructor_declarations",
        "target_recursor_declarations",
        "candidate_type_eqv_collisions",
        "candidate_target_type_eqv_collisions",
        "target_type_eqv_collisions",
    }
)


class V4PinnedLeanAuditError(RuntimeError):
    """A provenance-free v4 audit invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise V4PinnedLeanAuditError(message)


@dataclass(frozen=True)
class Corpus:
    public: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    split: str
    benchmark_id: str
    manifest_sha256: str
    generation_receipt_sha256: str
    public_sha256: str
    labels_sha256: str


def _load_json(path: Path, label: str) -> dict[str, Any]:
    value = lean_audit._load_json(path, label)
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def _load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    return lean_audit._load_jsonl(path, label)


def load_corpus(
    *,
    manifest_path: Path,
    generation_receipt_path: Path,
    public_path: Path,
    labels_path: Path,
    split: str,
) -> Corpus:
    """Hash-bind and validate one public/private pair without emitting provenance."""

    manifest = _load_json(manifest_path, "manifest")
    receipt = _load_json(generation_receipt_path, "generation receipt")
    require(
        manifest.get("schema_version")
        == "lemma-portfolio.dependency-compression-manifest.v4",
        "manifest schema mismatch",
    )
    require(
        receipt.get("schema_version")
        == "lemma-portfolio.dependency-compression-generation.v4",
        "generation receipt schema mismatch",
    )
    receipt_sha256 = release.sha256_path(generation_receipt_path)
    require(
        manifest.get("generation_receipt", {}).get("sha256") == receipt_sha256,
        "generation receipt SHA-256 mismatch",
    )
    require(split in {"calibration", "blind"}, "invalid split")
    split_manifest = manifest.get("splits", {}).get(split)
    require(isinstance(split_manifest, dict), "split manifest missing")
    public_sha256 = release.sha256_path(public_path)
    labels_sha256 = release.sha256_path(labels_path)
    require(
        split_manifest.get("public_sha256") == public_sha256,
        "public SHA-256 mismatch",
    )
    require(
        split_manifest.get("label_commitment_sha256") == labels_sha256,
        "label SHA-256 mismatch",
    )
    receipt_outputs = receipt.get("outputs")
    require(isinstance(receipt_outputs, dict), "generation output commitments missing")
    require(
        receipt_outputs.get(f"{split}_public_sha256") == public_sha256,
        "generation public commitment mismatch",
    )
    require(
        receipt_outputs.get(f"{split}_labels_commitment_sha256") == labels_sha256,
        "generation label commitment mismatch",
    )
    source = receipt.get("source")
    require(isinstance(source, dict), "generation source metadata missing")
    require(
        source.get("mathlib_commit") == lean_audit.PINNED_MATHLIB_COMMIT,
        "Mathlib commit mismatch",
    )
    require(source.get("dataset_version") == "v4.33.0", "dataset version mismatch")

    public = _load_jsonl(public_path, "public")
    labels = _load_jsonl(labels_path, "labels")
    require(len(public) == len(labels) == split_manifest.get("episodes"), "row count mismatch")
    expected_prefix = "MLP4C" if split == "calibration" else "MLP4B"
    candidate_ids = [f"C{index:02d}" for index in range(1, release.K + 1)]
    target_ids = [f"T{index:02d}" for index in range(1, release.TARGET_COUNT + 1)]
    all_candidate_sources: list[str] = []
    all_target_sources: list[str] = []
    for index, (public_row, label_row) in enumerate(zip(public, labels, strict=True)):
        episode_id = f"{expected_prefix}_{index:04d}"
        require(
            public_row.get("episode_id") == label_row.get("episode_id") == episode_id,
            "episode ID/order mismatch",
        )
        require(
            public_row.get("benchmark_id")
            == label_row.get("benchmark_id")
            == split_manifest.get("benchmark_id"),
            "benchmark ID mismatch",
        )
        require(public_row.get("schema_version") == release.PUBLIC_SCHEMA, "public schema mismatch")
        require(label_row.get("schema_version") == release.LABEL_SCHEMA, "label schema mismatch")
        require(public_row.get("selection_budget") == release.B, "selection budget mismatch")
        candidates = public_row.get("candidates")
        targets = public_row.get("targets")
        require(isinstance(candidates, list) and isinstance(targets, list), "public episode shape invalid")
        require([row.get("id") for row in candidates] == candidate_ids, "candidate IDs/order mismatch")
        require([row.get("id") for row in targets] == target_ids, "target IDs/order mismatch")
        candidate_sources = label_row.get("candidate_sources")
        target_sources = label_row.get("target_sources")
        direct_rows = label_row.get("targets")
        require(isinstance(candidate_sources, dict), "candidate provenance invalid")
        require(isinstance(target_sources, dict), "target provenance invalid")
        require(isinstance(direct_rows, list), "target labels invalid")
        require(list(candidate_sources) == candidate_ids, "candidate provenance order mismatch")
        require(list(target_sources) == target_ids, "target provenance order mismatch")
        require([row.get("id") for row in direct_rows] == target_ids, "target-label order mismatch")
        require(
            all(isinstance(value, str) and value for value in candidate_sources.values()),
            "candidate provenance value invalid",
        )
        require(
            all(isinstance(value, str) and value for value in target_sources.values()),
            "target provenance value invalid",
        )
        incidence: list[frozenset[str]] = []
        for target_row in direct_rows:
            direct = target_row.get("direct_candidates")
            require(
                isinstance(direct, list)
                and direct
                and direct == sorted(direct)
                and len(direct) == len(set(direct))
                and set(direct) <= set(candidate_ids),
                "direct-candidate set invalid",
            )
            incidence.append(frozenset(direct))
        use_counts = {
            candidate_id: sum(candidate_id in direct for direct in incidence)
            for candidate_id in candidate_ids
        }
        require(
            label_row.get("candidate_displayed_use_counts") == use_counts,
            "displayed-use counts mismatch",
        )
        active = sorted(candidate for candidate, count in use_counts.items() if count)
        require(label_row.get("active_candidates") == active, "active-candidate set mismatch")
        optimum, optimal, histogram = release.exhaustive_optima(candidate_ids, incidence)
        require(label_row.get("optimal_coverage") == optimum, "optimal coverage mismatch")
        require(
            label_row.get("optimal_portfolios") == [list(row) for row in optimal],
            "optimal portfolios incomplete or noncanonical",
        )
        require(
            label_row.get("coverage_histogram")
            == {str(score): count for score, count in sorted(histogram.items())},
            "coverage histogram mismatch",
        )
        all_candidate_sources.extend(candidate_sources.values())
        all_target_sources.extend(target_sources.values())
    require(
        len(all_candidate_sources) == len(set(all_candidate_sources)),
        "candidate provenance reused across episodes",
    )
    require(
        len(all_target_sources) == len(set(all_target_sources)),
        "target provenance reused across episodes",
    )
    require(
        not set(all_candidate_sources) & set(all_target_sources),
        "candidate/target provenance overlap",
    )
    return Corpus(
        public=public,
        labels=labels,
        split=split,
        benchmark_id=split_manifest["benchmark_id"],
        manifest_sha256=release.sha256_path(manifest_path),
        generation_receipt_sha256=receipt_sha256,
        public_sha256=public_sha256,
        labels_sha256=labels_sha256,
    )


def render_lean_program(corpus: Corpus) -> str:
    """Render the private stdin-only edge, kind, and type-equivalence audit."""

    episodes: list[str] = []
    for label_episode in corpus.labels:
        candidate_sources = label_episode["candidate_sources"]
        target_sources = label_episode["target_sources"]
        targets: list[str] = []
        for target in label_episode["targets"]:
            expected = [
                candidate_sources[candidate_id]
                for candidate_id in target["direct_candidates"]
            ]
            targets.append(
                "{ declaration := "
                + lean_audit._lean_string(target_sources[target["id"]])
                + ", expected := "
                + lean_audit._lean_array(expected)
                + " }"
            )
        episodes.append(
            "{ candidates := "
            + lean_audit._lean_array(
                [candidate_sources[f"C{index:02d}"] for index in range(1, release.K + 1)]
            )
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

syntax (name := v4DependencyAuditCommand) "#v4_dependency_audit" : command

@[command_elab v4DependencyAuditCommand]
def elabV4DependencyAudit : CommandElab
  | `(#v4_dependency_audit) => do
      let environment ← getEnv
      let mut reports : Nat := 0
      let mut candidateDeclarations : Nat := 0
      let mut targetDeclarations : Nat := 0
      let mut edges : Nat := 0
      let mut oldEdges : Nat := 0
      let mut changedTargets : Nat := 0
      let mut changedEpisodes : Nat := 0
      let mut removedEdges : Nat := 0
      let mut addedEdges : Nat := 0
      let mut emptyTargets : Nat := 0
      let mut candidateAxiom : Nat := 0
      let mut candidateDefinition : Nat := 0
      let mut candidateTheorem : Nat := 0
      let mut candidateOpaque : Nat := 0
      let mut candidateQuotient : Nat := 0
      let mut candidateInductive : Nat := 0
      let mut candidateConstructor : Nat := 0
      let mut candidateRecursor : Nat := 0
      let mut targetAxiom : Nat := 0
      let mut targetDefinition : Nat := 0
      let mut targetTheorem : Nat := 0
      let mut targetOpaque : Nat := 0
      let mut targetQuotient : Nat := 0
      let mut targetInductive : Nat := 0
      let mut targetConstructor : Nat := 0
      let mut targetRecursor : Nat := 0
      let mut candidateTypeEqv : Nat := 0
      let mut candidateTargetTypeEqv : Nat := 0
      let mut targetTypeEqv : Nat := 0
      for episode in auditEpisodes do
        let candidateInfos ← episode.candidates.mapM fun candidate => do
          let some information := environment.find? candidate.toName
            | throwError "unknown candidate declaration"
          pure information
        let targetInfos ← episode.targets.mapM fun target => do
          let some information := environment.find? target.declaration.toName
            | throwError "unknown target declaration"
          pure information
        candidateDeclarations := candidateDeclarations + candidateInfos.size
        targetDeclarations := targetDeclarations + targetInfos.size
        for information in candidateInfos do
          match information with
          | .axiomInfo _ => candidateAxiom := candidateAxiom + 1
          | .defnInfo _ => candidateDefinition := candidateDefinition + 1
          | .thmInfo _ => candidateTheorem := candidateTheorem + 1
          | .opaqueInfo _ => candidateOpaque := candidateOpaque + 1
          | .quotInfo _ => candidateQuotient := candidateQuotient + 1
          | .inductInfo _ => candidateInductive := candidateInductive + 1
          | .ctorInfo _ => candidateConstructor := candidateConstructor + 1
          | .recInfo _ => candidateRecursor := candidateRecursor + 1
        for information in targetInfos do
          match information with
          | .axiomInfo _ => targetAxiom := targetAxiom + 1
          | .defnInfo _ => targetDefinition := targetDefinition + 1
          | .thmInfo _ => targetTheorem := targetTheorem + 1
          | .opaqueInfo _ => targetOpaque := targetOpaque + 1
          | .quotInfo _ => targetQuotient := targetQuotient + 1
          | .inductInfo _ => targetInductive := targetInductive + 1
          | .ctorInfo _ => targetConstructor := targetConstructor + 1
          | .recInfo _ => targetRecursor := targetRecursor + 1
        let candidateTypes := candidateInfos.map (fun information => information.type)
        let targetTypes := targetInfos.map (fun information => information.type)
        for i in List.range candidateTypes.size do
          for j in List.range candidateTypes.size do
            if i < j && candidateTypes[i]!.eqv candidateTypes[j]! then
              candidateTypeEqv := candidateTypeEqv + 1
        for candidateType in candidateTypes do
          for targetType in targetTypes do
            if candidateType.eqv targetType then
              candidateTargetTypeEqv := candidateTargetTypeEqv + 1
        for i in List.range targetTypes.size do
          for j in List.range targetTypes.size do
            if i < j && targetTypes[i]!.eqv targetTypes[j]! then
              targetTypeEqv := targetTypeEqv + 1
        let mut episodeChanged := false
        for target in episode.targets do
          let declaration := target.declaration.toName
          let some information := environment.find? declaration
            | throwError "unknown target declaration"
          let some value := information.value? (allowOpaque := true)
            | throwError "target declaration has no accessible value"
          let directValue := value.getUsedConstantsAsSet
          let matched := episode.candidates.filter fun candidate =>
            directValue.contains candidate.toName
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
        ("candidate_declarations", toJson candidateDeclarations),
        ("target_declarations", toJson targetDeclarations),
        ("direct_value_edges", toJson edges),
        ("old_edges", toJson oldEdges),
        ("changed_targets", toJson changedTargets),
        ("changed_episodes", toJson changedEpisodes),
        ("removed_edges", toJson removedEdges),
        ("added_edges", toJson addedEdges),
        ("empty_targets", toJson emptyTargets),
        ("candidate_axiom_declarations", toJson candidateAxiom),
        ("candidate_definition_declarations", toJson candidateDefinition),
        ("candidate_theorem_declarations", toJson candidateTheorem),
        ("candidate_opaque_declarations", toJson candidateOpaque),
        ("candidate_quotient_declarations", toJson candidateQuotient),
        ("candidate_inductive_declarations", toJson candidateInductive),
        ("candidate_constructor_declarations", toJson candidateConstructor),
        ("candidate_recursor_declarations", toJson candidateRecursor),
        ("target_axiom_declarations", toJson targetAxiom),
        ("target_definition_declarations", toJson targetDefinition),
        ("target_theorem_declarations", toJson targetTheorem),
        ("target_opaque_declarations", toJson targetOpaque),
        ("target_quotient_declarations", toJson targetQuotient),
        ("target_inductive_declarations", toJson targetInductive),
        ("target_constructor_declarations", toJson targetConstructor),
        ("target_recursor_declarations", toJson targetRecursor),
        ("candidate_type_eqv_collisions", toJson candidateTypeEqv),
        ("candidate_target_type_eqv_collisions", toJson candidateTargetTypeEqv),
        ("target_type_eqv_collisions", toJson targetTypeEqv)
      ]).compress
  | _ => throwUnsupportedSyntax

#v4_dependency_audit
"""


def verify_environment(
    *,
    mathlib_checkout: Path,
    lean_project: Path,
    lake: Path,
    elan_home: Path | None,
) -> dict[str, str]:
    """Accept either the clean Mathlib root itself or a pinned downstream project."""

    try:
        checkout = mathlib_checkout.resolve(strict=True)
        project = lean_project.resolve(strict=True)
        lake_binary = lake.resolve(strict=True)
    except OSError as error:
        raise lean_audit.AuditError("an explicit environment path does not exist") from error
    if project != checkout:
        return lean_audit.verify_environment(
            mathlib_checkout=checkout,
            lean_project=project,
            lake=lake_binary,
            elan_home=elan_home,
        )
    require(checkout.is_dir(), "Mathlib checkout path is not a directory")
    require(lake_binary.is_file(), "Lake path is not a file")
    top = lean_audit._run_checked(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=checkout,
        failure="Mathlib Git identity check failed",
    ).stdout.strip()
    require(Path(top).resolve(strict=True) == checkout, "Mathlib path is not its Git root")
    head = lean_audit._run_checked(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        failure="Mathlib commit check failed",
    ).stdout.strip()
    require(head == lean_audit.PINNED_MATHLIB_COMMIT, "Mathlib commit mismatch")
    status = lean_audit._run_checked(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=checkout,
        failure="Mathlib cleanliness check failed",
    ).stdout
    require(not status.strip(), "Mathlib has tracked worktree changes")
    try:
        toolchain = (checkout / "lean-toolchain").read_text(encoding="utf-8").strip()
        manifest = lean_audit._load_json(checkout / "lake-manifest.json", "Mathlib manifest")
    except (OSError, UnicodeError) as error:
        raise lean_audit.AuditError("Mathlib environment metadata is unreadable") from error
    require(toolchain == lean_audit.PINNED_LEAN_TOOLCHAIN, "Mathlib toolchain mismatch")
    require(isinstance(manifest, dict), "Mathlib manifest must be an object")
    environment = os.environ.copy()
    if elan_home is not None:
        try:
            resolved_elan = elan_home.resolve(strict=True)
        except OSError as error:
            raise lean_audit.AuditError("the explicit ELAN_HOME path does not exist") from error
        require(resolved_elan.is_dir(), "the explicit ELAN_HOME path is not a directory")
        environment["ELAN_HOME"] = str(resolved_elan)
    version = lean_audit._run_checked(
        [str(lake_binary), "env", "lean", "--version"],
        cwd=checkout,
        env=environment,
        failure="Lean version check failed",
    ).stdout
    require(lean_audit._LEAN_VERSION.fullmatch(version) is not None, "Lean version/commit mismatch")
    return environment


def parse_lean_aggregate(stdout: str) -> dict[str, int]:
    lines = stdout.splitlines()
    require(len(lines) == 1 and bool(lines[0]), "Lean output is not one aggregate line")
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as error:
        raise V4PinnedLeanAuditError("Lean output is not aggregate JSON") from error
    require(isinstance(value, dict), "Lean aggregate must be an object")
    require(set(value) == AGGREGATE_KEYS, "Lean aggregate schema mismatch")
    require(
        all(type(item) is int and item >= 0 for item in value.values()),
        "Lean aggregate values must be nonnegative integers",
    )
    return value


def verify_aggregate(corpus: Corpus, aggregate: dict[str, int]) -> None:
    reports = sum(len(episode["targets"]) for episode in corpus.labels)
    candidates = release.K * len(corpus.labels)
    expected_edges = sum(
        len(target["direct_candidates"])
        for episode in corpus.labels
        for target in episode["targets"]
    )
    require(aggregate["reports"] == reports, "target report count mismatch")
    require(aggregate["target_declarations"] == reports, "target declaration count mismatch")
    require(
        aggregate["candidate_declarations"] == candidates,
        "candidate declaration count mismatch",
    )
    require(aggregate["old_edges"] == expected_edges, "label edge count mismatch")
    require(
        aggregate["direct_value_edges"] == expected_edges,
        "Lean direct-value edge count mismatch",
    )
    for key in (
        "added_edges",
        "changed_episodes",
        "changed_targets",
        "empty_targets",
        "removed_edges",
        "candidate_type_eqv_collisions",
        "candidate_target_type_eqv_collisions",
        "target_type_eqv_collisions",
    ):
        require(aggregate[key] == 0, f"Lean aggregate {key} is nonzero")
    candidate_kind_keys = tuple(
        f"candidate_{kind}_declarations"
        for kind in (
            "axiom", "definition", "theorem", "opaque", "quotient",
            "inductive", "constructor", "recursor",
        )
    )
    target_kind_keys = tuple(
        f"target_{kind}_declarations"
        for kind in (
            "axiom", "definition", "theorem", "opaque", "quotient",
            "inductive", "constructor", "recursor",
        )
    )
    require(
        sum(aggregate[key] for key in candidate_kind_keys) == candidates,
        "candidate declaration-kind count mismatch",
    )
    require(
        sum(aggregate[key] for key in target_kind_keys) == reports,
        "target declaration-kind count mismatch",
    )


def audit(
    *,
    manifest_path: Path,
    generation_receipt_path: Path,
    public_path: Path,
    labels_path: Path,
    split: str,
    mathlib_checkout: Path,
    lean_project: Path,
    lake: Path,
    elan_home: Path | None,
    timeout: int,
) -> dict[str, Any]:
    corpus = load_corpus(
        manifest_path=manifest_path,
        generation_receipt_path=generation_receipt_path,
        public_path=public_path,
        labels_path=labels_path,
        split=split,
    )
    environment = verify_environment(
        mathlib_checkout=mathlib_checkout,
        lean_project=lean_project,
        lake=lake,
        elan_home=elan_home,
    )
    source = render_lean_program(corpus)
    result = lean_audit._run_checked(
        [str(lake.resolve()), "env", "lean", "--stdin"],
        cwd=lean_project.resolve(),
        env=environment,
        stdin=source,
        timeout=timeout,
        failure="v4 Lean dependency extraction failed; diagnostics suppressed",
    )
    aggregate = parse_lean_aggregate(result.stdout)
    require(not result.stderr.strip(), "Lean emitted unexpected diagnostics")
    verify_aggregate(corpus, aggregate)
    return {
        "schema_version": "lemma-portfolio.pinned-lean-direct-value-audit.v4",
        "benchmark_id": corpus.benchmark_id,
        "split": split,
        "public_manifest_sha256": corpus.manifest_sha256,
        "generation_receipt_sha256": corpus.generation_receipt_sha256,
        "public_sha256": corpus.public_sha256,
        "labels_sha256": corpus.labels_sha256,
        "mathlib_commit": lean_audit.PINNED_MATHLIB_COMMIT,
        "lean_toolchain": lean_audit.PINNED_LEAN_TOOLCHAIN,
        "lean_commit": lean_audit.PINNED_LEAN_COMMIT,
        "extraction": (
            "ConstantInfo.value? (allowOpaque := true), then "
            "Expr.getUsedConstantsAsSet, intersected with all displayed candidates"
        ),
        "aggregate": aggregate,
        "private_names_emitted": 0,
        "status": "pass",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--generation-receipt", type=Path, required=True)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--split", choices=("calibration", "blind"), required=True)
    parser.add_argument("--mathlib-checkout", type=Path, required=True)
    parser.add_argument("--lean-project", type=Path, required=True)
    parser.add_argument("--lake", type=Path, required=True)
    parser.add_argument("--elan-home", type=Path)
    parser.add_argument("--timeout", type=int, default=600)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        result = audit(
            manifest_path=args.manifest,
            generation_receipt_path=args.generation_receipt,
            public_path=args.public,
            labels_path=args.labels,
            split=args.split,
            mathlib_checkout=args.mathlib_checkout,
            lean_project=args.lean_project,
            lake=args.lake,
            elan_home=args.elan_home,
            timeout=args.timeout,
        )
    except Exception:
        parser.exit(2, "error: v4 pinned-Lean audit failed closed\n")
    sys.stdout.write(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
