# Collaborating on the private repository

No collaborator needs another person's password or access token.  The repository
owner invites each co-author by GitHub username under **Settings → Collaborators**.

## First-time setup

After accepting the invitation, a collaborator can use GitHub Desktop or run:

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 verify_release.py
```

The verification must end with `ALL CHECKS PASSED` before scientific edits begin.

## Editing the paper safely

The editable LaTeX source is in `paper/source/`.  The main entry points are:

- `review.tex`: anonymous MATH-AI review version;
- `preprint.tex`: named author-check version; and
- `supplement.tex`: separate technical supplement.

Create a branch so simultaneous edits do not overwrite each other:

```sh
git switch -c name/short-description
```

Edit the files, compile locally or in Overleaf, and then save the change:

```sh
git add paper/source
git commit -m "Describe the paper change"
git push -u origin name/short-description
```

On GitHub, open a pull request.  The repository owner or another co-author can
read the change, discuss it, and merge it into `main`.  GitHub Desktop provides
buttons for the same branch, commit, push, and pull-request operations.

Generated LaTeX build files do not belong in source control.  Replace the checked
PDFs under `paper/` only after compiling and visually inspecting all pages.
Whenever a tracked file changes, regenerate `SHA256SUMS` and run the verifier:

```sh
python3 tools/build_sha256s.py
python3 verify_release.py
```

## Editing benchmark results

Never hand-edit a published score.  Preserve the raw model answers, run the
scorer, review the item-level output, regenerate the paper tables from the
machine-readable result, and document the provenance of the new row.  Keep the
original V4 files immutable; substantive additions should receive a new release
version.

## Double-blind review

This full repository contains author names and must remain private during review.
Do not paste its URL into the anonymous paper.  Reviewers should receive the
separate anonymous reproducibility ZIP.  Add the permanent public repository URL
to the camera-ready paper only after the venue permits de-anonymization.
