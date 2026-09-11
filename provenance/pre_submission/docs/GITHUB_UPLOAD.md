# GitHub repository: safe, plain-language procedure

Do **not** send anyone your GitHub password, email password, personal access
token, or browser cookie.  This repository can be uploaded through GitHub's
normal sign-in flow without sharing any secret.

The intended private repository is
<https://github.com/durgesh-qcat/lemma-portfolio>.  Keep it **private during
double-blind review**.  A named public repository can reveal the authors even
when the PDF says “Anonymous Authors.”

## Clone or open the repository

An invited collaborator can accept the GitHub invitation and then use GitHub
Desktop, or run:

```sh
git clone https://github.com/durgesh-qcat/lemma-portfolio.git
cd lemma-portfolio
python3 verify_release.py
```

The last line must be `ALL CHECKS PASSED`.

## If the remote repository ever has to be recreated

1. Install GitHub Desktop from <https://desktop.github.com/> and sign in there.
2. In GitHub Desktop choose **File → Add Local Repository** and select the
   existing local `lemma-portfolio` folder that contains its `.git` history.
   A ZIP downloaded from GitHub does not contain that history; choose
   **Create a Repository from Existing Files** if only a ZIP is available.
3. Choose **Publish repository**.
4. Use the name `lemma-portfolio` and leave **Keep this code private** checked.
5. On GitHub.com, open **Settings → Collaborators** to invite a coauthor.

Invite collaborators by username and give a paper co-author write access.  They
can work on a branch and open a pull request without receiving the owner's
password.  See `COLLABORATING.md`.

When the venue permits public release, change visibility to public and create a
versioned release from the submitted commit. The prepared release assets are:

- `LemmaPortfolio_full_repository.zip`;
- `LemmaPortfolio_MATHAI2026_anonymous_reproducibility.zip`;
- `LemmaPortfolio_MATHAI2026_anonymous_Overleaf.zip`;
- the three checked paper PDFs;
- `LemmaPortfolio_Mathlib4Benchmark_v4.33.0_source_parquet.zip`, which keeps the
  211 MB construction-source snapshot out of ordinary Git history; and
- `ARTIFACT_SHA256SUMS`, which authenticates every release asset.

The 208 MiB Parquet archive exceeds GitHub's ordinary 100 MiB file limit.  It
must be attached to a GitHub Release and must never be committed to normal Git
history.

Only after the anonymity policy permits it should the permanent GitHub URL be
added to the camera-ready paper. GitHub never requires you to send a password
to a collaborator: use GitHub Desktop's normal sign-in window, or invite the
collaborator by username under **Settings → Collaborators**.

Official GitHub instructions:

- <https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop>
- <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility>
