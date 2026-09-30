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
make html              # → sample.html (revealjs, NCAR web theme)
make pdf               # → sample.pdf  (beamer, NCAR beamer theme; needs TeX)
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
│   │   ├── _extensions/benkirk/ncar/  # NCAR beamer theme (vendored; symlinked into decks)
│   │   ├── assets/fonts/  # Poppins .fntdata blobs (EOT-subsetted)
│   │   ├── branding/ncar/template.pptx
│   │   └── utils/
│   │       ├── embed_poppins.py    # post-render font embedder
│   │       └── enable_autofit.py   # primes "Shrink text on overflow"
│   └── sample/                     # the cookbook deck
│       ├── Makefile        (3-line include of ../Make.common)
│       ├── _quarto.yml     (symlink → ../common/_quarto.yml)
│       ├── _extensions     (symlink → ../common/_extensions, made by make)
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
2. `python3 ../common/utils/section_subtitle.py <deck>.pptx`
   - Merges the paragraph after a `#` section heading back onto the
     Section Header slide as its subtitle. Pandoc otherwise drops it onto
     a separate untitled slide.
3. `python3 ../common/utils/enable_autofit.py <deck>.pptx`
   - Flips every body placeholder's autofit dropdown from "Do not Autofit"
     to "Shrink text on overflow." See "About text autofit" below.
4. `python3 ../common/utils/embed_poppins.py <deck>.pptx`
   - Re-injects the four Poppins variants as `<p:embeddedFont>` entries.
     Pandoc strips these on reference-doc copy; the script puts them
     back so the font travels with the file.
5. `python3 ../common/utils/style_footnotes.py <deck>.pptx`
   - Restyles body paragraphs that start with `†` as footnotes (smaller,
     muted), since pandoc ignores inline size and color in markdown.
6. `python3 ../common/utils/link_captions.py <deck>.pptx`
   - Captions each linked picture (see "Linked images" below) with its URL,
     bottom center, muted; the caption box is itself the link.

`make html` (revealjs) and `make pdf` (beamer) bypass steps 2 through 6 — the
template, fonts, autofit, and the other pptx fix-ups are pptx-specific.

### Linked images

Wrap an image in a link and the picture opens that page, in every format:

```markdown
[![](images/dashboard.png){height="72%" fig-align="center"}](https://example.org/dashboard)
```

Each format also shows the URL, small and muted, so a reader knows the
picture is live: the slide footer in HTML, a line at the foot of the PDF page
(`common/linked-images.lua`), and a caption box in pptx (`link_captions.py`;
pandoc can't add one without splitting the slide). One line per slide, from
its first linked image. `{height="72%"}` is the full-width screenshot recipe
and fits all three.

### PDF (beamer)

`make pdf` renders with `--to ncar-beamer`. That format comes from the NSF NCAR
beamer theme ([benkirk/NCAR_beamer_template](https://github.com/benkirk/NCAR_beamer_template)),
which is vendored in `docs/common/_extensions/benkirk/ncar/`. Make symlinks
`_extensions` into each deck directory, just as it does for `_quarto.yml`.

- **You need Quarto 1.6 or newer** (the conda env pins it): the theme's Lua
  filter uses a pandoc macro that older Quarto releases lack.
- **You need TeX with XeLaTeX.** Quarto's own TinyTeX (`quarto install
  tinytex`) works and installs missing LaTeX packages on the fly. So does a
  system TeX Live.
- **No fonts to install.** The theme bundles Poppins and the official logo
  lockups.
- **Theme options** go in a deck's front matter:
  `themeoptions: [brand=ucar, title=light, fonts=bundled]`. A deck-level
  list replaces the shared one, so keep `fonts=bundled` (from the shared
  `_quarto.yml`): it uses the theme's own Poppins instead of probing for a
  system copy, which is noisy under XeLaTeX and leaves `missfont.log` behind.
  - `titlegraphic: images/photo.jpg` puts a photo on the title slide.
  - `fineprint: "..."` adds small print under the title block.
- **Markdown extras:**
  - `## Title {.feature background-image="images/photo.jpg"}` makes a
    full-bleed photo slide (`background=` also works; `background-image=`
    doubles as the revealjs background).
  - `## Thank you! {.closing}` makes a closing slide.
  - `### Heading {.example}` / `{.alert}` give block variants.
  - `[text]{.alert}` emphasizes text.
- **Beamer never shrinks overflowing text.** The shared config uses 10pt,
  which matches the pptx template's text density. Add `{.shrink}` to a dense
  slide's heading to scale that one slide down; pptx ignores the class.
- **To update the theme:** `cd docs/common && quarto update benkirk/NCAR_beamer_template`.

### HTML (revealjs)

`make html` renders with `--to ncar-revealjs`, the web format from the same
vendored extension. The deck looks like the PDF: title slide with the brand
waves (or `titlegraphic:`), section dividers with subtitles, content slides
with the accent tab and logo, `.feature` and `.closing` slides. The same
`themeoptions:` apply (`brand=`, `title=`). Open `<deck>.html` in a browser
and keep `<deck>_files/` beside it.

- **Presenting:** `s` speaker view (notes), `m` slide menu, `b`/`c`
  whiteboard / draw on the slide, `f` full screen.
- **HTML-only extras:**
  - `## Title {.brand-dark}` puts a content slide on Space with white text;
    pptx and PDF draw an ordinary slide.
  - Overflowing content slides shrink to fit (see "About text autofit").
  - Mermaid and Graphviz draw live in the browser; mermaid uses the brand
    colors and Poppins, not the baked-PNG look of pptx/PDF.
- **One file to share:** in a deck's front matter,
  ```yaml
  format:
    ncar-revealjs:
      embed-resources: true
      chalkboard: false     # the whiteboard can't be embedded
  ```
  gives a single self-contained `.html`.
- **PDF from the browser:** open `<deck>.html?print-pdf` in Chrome and print
  with background graphics. `make pdf` is usually the better handout.

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

A directory can hold several decks that share images and fragments, e.g. a
full deck plus one deck per part:

```make
DECKS := roadmap 1-intro 2-details
include ../Make.common
```

Each `<name>.qmd` builds `<name>.pptx` / `.html` / `.pdf`, and `make pptx`
builds all of them. Put shared slide bodies in `_*.qmd` fragments and pull
them in with `{{< include _1-intro.qmd >}}`; quarto skips underscore files
when rendering, and make treats every `_*.qmd` and `data/*` in the directory
as a prerequisite of every deck, so editing one rebuilds them all.

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

The HTML deck fits itself: a content slide that runs past the bottom margin
shrinks its body text (down to 65%) until it fits, keeping the title size.
`{.smaller}` still sets a slide smaller from the start:

```markdown
## Wall of text {.smaller}
```

PPTX silently ignores `{.smaller}`; revealjs honors it. Opt a slide out of
the HTML autofit with `{.no-autofit}` (or `{.scrollable}`), or a whole deck
with `themeoptions: [autofit=false]`.

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

## License

Copyright © 2026 University Corporation for Atmospheric Research.

This framework is licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) (Creative
Commons Attribution-ShareAlike 4.0 International); the full text is in
[`LICENSE.txt`](LICENSE.txt). You may share and adapt it with attribution,
provided you distribute your changes under the same license.

These parts are **not** covered by that license:

- **NSF, NCAR, UCAR and UCP logos and brand marks.** These appear in
  `docs/common/branding/` and in the vendored theme. They are trademarks
  used under the
  [UCAR brand guidelines](https://ucar.canto.com/v/branding).
- **The Poppins font** (`docs/common/assets/fonts/` and the vendored theme)
  is licensed under the [SIL Open Font License](https://openfontlicense.org).
