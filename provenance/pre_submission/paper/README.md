# Paper files

The three checked PDFs are:

- `LemmaPortfolio_MATHAI2026_anonymous_review_with_supplement.pdf`: the
  anonymous four-page submission body, references, and technical supplement;
- `LemmaPortfolio_MATHAI2026_author_check_preprint.pdf`: the named author copy;
- `LemmaPortfolio_MATHAI2026_anonymous_technical_supplement.pdf`: the standalone
  anonymous supplement.

The LaTeX source is in `source/`.  From that directory, build with:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error review.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error preprint.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -jobname=supplement supplement/supplement.tex
```

The anonymous Overleaf ZIP is distributed separately.  It omits `preprint.tex`
and all named author metadata.
