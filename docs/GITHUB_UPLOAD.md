# GitHub upload: safe, plain-language procedure

Do **not** send anyone your GitHub password, email password, personal access
token, or browser cookie.  This repository can be uploaded through GitHub's
normal sign-in flow without sharing any secret.

Keep the repository **private during double-blind review**.  A named public
repository can reveal the authors even when the PDF says “Anonymous Authors.”

## Easiest method: GitHub Desktop

1. Install GitHub Desktop from <https://desktop.github.com/> and sign in there.
2. Unzip the supplied full-repository ZIP.
3. In GitHub Desktop choose **File → Add Local Repository** and select the inner
   `lemma-portfolio` folder.
4. Choose **Publish repository**.
5. Use the name `lemma-portfolio` and leave **Keep this code private** checked.
6. On GitHub.com, open **Settings → Collaborators** to invite a coauthor.

Before publishing, run `python3 verify_release.py`; the last line must be
`ALL CHECKS PASSED`.

When the venue permits public release, change visibility to public and create a
versioned release from the submitted commit. The prepared release assets are:

- `LemmaPortfolio_full_repository.zip`;
- `LemmaPortfolio_MATHAI2026_anonymous_reproducibility.zip`;
- `LemmaPortfolio_MATHAI2026_anonymous_Overleaf.zip`;
- the three checked paper PDFs;
- `LemmaPortfolio_Mathlib4Benchmark_v4.33.0_source_parquet.zip`, which keeps the
  211 MB construction-source snapshot out of ordinary Git history; and
- `ARTIFACT_SHA256SUMS`, which authenticates every release asset.

Only after the anonymity policy permits it should the permanent GitHub URL be
added to the camera-ready paper. GitHub never requires you to send a password
to a collaborator: use GitHub Desktop's normal sign-in window, or invite the
collaborator by username under **Settings → Collaborators**.

Official GitHub instructions:

- <https://docs.github.com/en/desktop/adding-and-cloning-repositories/adding-an-existing-project-to-github-using-github-desktop>
- <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility>
