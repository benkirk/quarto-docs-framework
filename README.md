# quarto-docs-framework

NCAR-branded [Quarto](https://quarto.org) template for HPC-style
documentation decks (`.pptx` / `.html` / `.pdf`). Clone, set up the conda
env, copy the sample deck, write Markdown.

The example deck under `docs/sample/` is a **cookbook** showing one
example of every capability you're likely to need: text formatting, math,
tables, two-column layouts, image embeds, syntax-highlighted code,
auto-captured shell output, mermaid diagrams, speaker notes, and the
`{{< include >}}` shortcode. `docs/sample/old.qmd` is preserved as a
richer real-world example (database schema / REST API / deployment
diagrams).

## Quick start

```bash
git clone <this-repo> quarto-docs-framework
cd quarto-docs-framework

# 1. Build the conda env (also installs + registers the bash Jupyter
#    kernel so executable {bash} chunks work).
make conda-env
conda activate ./conda-env

# 2. Render the sample deck.
cd docs/sample
make pptx              # → sample.pptx (NCAR-branded, fonts embedded)
make html              # → sample.html (revealjs)
make pdf               # → sample.pdf  (beamer)
```

Open `sample.pptx` to see what each cookbook slide looks like, then start
editing `sample.qmd` (or copy it to a new deck — see "Adding a new deck"
below).

## Layout

```
quarto-docs-framework/
├── Makefile               # top-level: `make conda-env`, env mgmt
├── conda-env.yaml         # quarto + jupyter + bash_kernel + helpers
├── docs/
│   ├── Make.common        # shared per-deck recipes (pptx/html/pdf/clean)
│   ├── common/
│   │   ├── _quarto.yml    # shared Quarto config (symlinked into decks)
│   │   ├── assets/fonts/  # Poppins .fntdata blobs (EOT-subsetted)
│   │   ├── branding/ncar/template.pptx
│   │   └── utils/
│   │       ├── embed_poppins.py    # post-render font embedder
│   │       └── enable_autofit.py   # primes "Shrink text on overflow"
│   └── sample/                     # the cookbook deck
│       ├── Makefile        (3-line include of ../Make.common)
│       ├── _quarto.yml     (symlink → ../common/_quarto.yml)
│       ├── sample.qmd      (the cookbook)
│       ├── old.qmd         (richer real-world example, kept for reference)
│       └── images/         (drop your PNGs / JPGs here)
└── conda-env/              # local conda prefix, gitignored
```

Room to grow: additional brand packages (`docs/common/branding/ucar/`,
`.../cisl/`) or additional shared assets (`docs/common/assets/images/`)
drop in as sibling subdirs without disturbing existing decks.

## Build pipeline

Per deck, `make pptx` runs:

1. `quarto render <deck>.qmd --to pptx -o <deck>.pptx`
   - Uses `reference-doc: ../common/branding/ncar/template.pptx` from the
     deck's `_quarto.yml`, so the output inherits NCAR theme colors,
     title slide layout, masters, etc.
2. `python3 ../common/utils/enable_autofit.py <deck>.pptx`
   - Flips every body placeholder's autofit dropdown from "Do not Autofit"
     to "Shrink text on overflow." See "About text autofit" below.
3. `python3 ../common/utils/embed_poppins.py <deck>.pptx`
   - Re-injects the four Poppins variants as `<p:embeddedFont>` entries.
     Pandoc strips these on reference-doc copy; the script puts them
     back so the font travels with the file.

`make html` (revealjs) and `make pdf` (beamer) bypass steps 2 and 3 — the
template, fonts, and autofit step are pptx-specific.

## Adding a new deck

```bash
cd docs
mkdir roadmap && cd roadmap

cat > Makefile <<'EOF'
include ../Make.common
EOF

# then author roadmap.qmd. _quarto.yml is auto-symlinked from
# ../common/_quarto.yml on first `make` invocation.
make pptx
```

`Make.common` infers the deck name from `$(notdir $(CURDIR))`, so the
output file is `<dirname>.pptx`. Override with `OUT=foo` if needed.

A deck that needs custom Quarto config (a different reference template,
extra extensions, etc.) can replace the symlinked `_quarto.yml` with a
real file — `make` sees the file already exists and skips the symlink
recipe.

## Executable shell chunks

Quarto can capture the live output of a shell command at render time:

````markdown
```{bash}
#| echo: true
which mpicxx && mpicxx --version
```
````

Both the command and its captured stdout land on the slide. This needs
the Jupyter `bash` kernel, which `make conda-env` installs and registers
into the env (`bash_kernel` pip package + `python -m bash_kernel.install
--sys-prefix`). The deck's frontmatter must opt in:

```yaml
engine: jupyter
jupyter: bash
```

Code runs on the build host, not the viewer's machine — output is baked
into the .pptx.

## About text autofit

Pandoc's PPTX writer emits empty `<a:bodyPr/>` on every placeholder,
which corresponds to PowerPoint's "Do not Autofit" — long text overflows
the placeholder visually. `enable_autofit.py` rewrites these to
`<a:bodyPr><a:normAutofit/></a:bodyPr>`, which sets the dropdown to
"Shrink text on overflow."

Caveat: PowerPoint computes the actual `fontScale` only on edit, not on
load, so the file still opens with overflowing text — but a single click
into any overflowing cell triggers the recompute and the text shrinks
permanently. After saving, subsequent opens render correctly.

A fully automated post-render shrink would need to drive PowerPoint
externally (e.g. a LibreOffice round-trip, AppleScript UI scripting, or
a `.pptm` macro). None of these are wired up — author-side discipline
(split walls of text into multiple slides, use columns) is cheaper and
more robust.

For revealjs HTML output, tag overflowing slides with `{.smaller}`:

```markdown
## Wall of text {.smaller}
```

PPTX silently ignores `{.smaller}`; revealjs honors it.

## Template constraints

The reference template under `docs/common/branding/ncar/template.pptx`
must stay pandoc-compliant. Two things pandoc is strict about:

- **`slideLayout1` placeholders**: must include all five of `ctrTitle`,
  `subTitle`, `dt`, `ftr`, `sldNum`. Pandoc emits empty `<p:sp/>` stubs
  for any missing placeholder, which PowerPoint then flags as corrupt
  ("Repair?" prompt on open).
- **Layout names**: pandoc looks up layouts by display name. The title
  slide layout must be named exactly `Title Slide`; other layouts pandoc
  knows about are `Title and Content`, `Section Header`, `Two Content`,
  `Comparison`, `Content with Caption`, `Blank`. Missing names don't
  break the build but trigger a `Couldn't find layout named …` warning
  and fall back to pandoc's bundled layout (losing NCAR styling for that
  slide).

Verify after any template edit:

```bash
unzip -p docs/common/branding/ncar/template.pptx \
  ppt/slideLayouts/slideLayout1.xml | grep -oE '<p:ph[^/]*/>'
# expect 5 matches
```

## About the font embedding

The theme is wired to Poppins via `<a:fontScheme name="Poppins">`, so
slide masters/layouts all dereference to Poppins through `+mj-lt` /
`+mn-lt`. Embedding the font blobs on top of that is only needed when
the `.pptx` will be opened on a machine without Poppins installed —
without the embed, PowerPoint substitutes (typically Calibri) and the
deck loses its look.

If portability stops mattering, drop the `embed_poppins.py` step from
`docs/Make.common` and delete `docs/common/assets/fonts/` +
`docs/common/utils/embed_poppins.py`.
