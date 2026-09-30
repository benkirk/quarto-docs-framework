# CLAUDE.md

Guidance for working in this repository. Keep it accurate — update it when the
structure or conventions below change.

## What this is

An NCAR-branded [Quarto](https://quarto.org) framework for documentation decks
(`.pptx` primary; `.html`/revealjs and `.pdf`/beamer secondary). Decks live
under `docs/<deck>/` as a `.qmd` plus a 1-line Makefile; shared machinery is in
`docs/common/` (branded `template.pptx`, `_quarto.yml`, Lua filter, post-render
utilities) and `docs/Make.common`. `docs/sample/sample.qmd` is the cookbook —
copy it for new decks; the README covers layout, template constraints, and font
embedding.

## Environment & build

- **Env**: `source etc/config_env.sh` (or `conda activate ./conda-env`; build it
  with `make conda-env`). Quarto **requires real conda activation** — the
  `activate.d` scripts export `QUARTO_DENO`, `QUARTO_PANDOC`, etc.; merely
  putting `conda-env/bin` on `PATH` fails with a missing-deno error.
- **Build**: `make pptx` (also `html`, `pdf`) inside the deck directory.
  `Make.common` names the output after the directory (`OUT`) and auto-symlinks
  `_quarto.yml` and `_extensions`. The pptx recipe post-processes with
  `section_subtitle.py`, `enable_autofit.py`, `embed_poppins.py`, and
  `style_footnotes.py`.
- **PDF** is `--to ncar-beamer`: the NCAR beamer theme, vendored from
  `benkirk/NCAR_beamer_template` into `docs/common/_extensions/benkirk/ncar/`.
  Don't edit the vendored copy. Change the theme repo, then re-vendor with
  `cd docs/common && quarto update benkirk/NCAR_beamer_template` (the
  vendored `_extension.yml` records no source, so the bare `quarto update`
  fails). The extension's Lua filter loads the theme in place
  through `\input@path`, so nothing is copied into deck directories. Needs
  XeLaTeX (TinyTeX or TeX Live) and Quarto >= 1.6 (`quarto-required` in the
  shared `_quarto.yml`; `conda-env.yaml` pins it). Beamer has no autofit: dense slides
  overflow silently, so render the PDF and look at it, then trim the content
  or add `{.shrink}` to the heading. A full-width 16:9 screenshot is taller than
  the frame's content area; cap it with `{height="72%" fig-align="center"}`
  (pptx ignores the attribute and fits the placeholder anyway).
- **Format conditionals**: `when-format="beamer"` matches the custom
  `ncar-beamer` format; `when-format="ncar-beamer"` matches nothing. Always
  write `beamer`.
- **Divider subtitles**: a paragraph right after a `#` divider becomes that
  divider's subtitle in both formats: `section_subtitle.py` for pptx, and the
  theme's `\sectionsubtitle` (via its Lua filter) for beamer. Only plain
  paragraphs qualify; anything else after a divider stays a slide of its own.
- **Front matter must be line 1** of every deck `.qmd`: anything above the
  opening `---` (an editor mode-line, a comment) hides it from Quarto, and
  `date: last-modified` renders literally (#7). CI checks this; set editor
  modes in the editor config, not in the file.
- **Fragments are prerequisites**: every deck in a directory depends on its
  `_*.qmd` fragments, `data/*` and `images/*`, so editing any of them rebuilds all of them. A
  file included from anywhere else (e.g. `../other_deck/_x.qmd`) is invisible
  to make; `touch <deck>.qmd` after editing one.
- **Several decks in one directory**: set `DECKS := a b c` before the include;
  each `<name>.qmd` builds `<name>.{pptx,html,pdf}`. They share one `.quarto/`
  cache, so `Make.common` is `.NOTPARALLEL`.
- Executable ```{bash} cells run at render time via the jupyter `bash` kernel
  (deck frontmatter: `engine: jupyter`, `jupyter: bash`). Keep them
  deterministic — CI renders the sample deck.

## pandoc pptx gotchas (hard-won — read before restructuring slides)

- **Content after a table or image splits the slide** into an untitled
  continuation. Order: bullets *before* tables; speaker notes (`::: {.notes}`)
  *before* a full-bleed image; use `:::: {.columns}` to put a diagram beside
  text. Verified template-independent (pandoc writer behavior).
- **Raw-HTML `<figure>` wrappers demote columns slides to the Comparison
  layout**: quarto wraps rendered diagrams in `` `<figure>`{=html} `` inlines,
  pandoc's layout chooser counts them as text, and the other column's text gets
  stuffed into Comparison's tiny per-column heading box.
  `docs/common/strip-raw-figure.lua` (wired into the shared `_quarto.yml`,
  pptx-only) strips them; don't remove it.
- **A lead paragraph before a table demotes the slide** to Content with
  Caption: the title moves into a small side caption and the title bar stays
  empty. Put the lead in the slide title (or the notes) and start the body
  with the table. Text followed by an image lands in Two Content the same
  way, so a wide chart shrinks to half width; bake a chart's footnote into the
  PNG instead.
- **Diagnosing layout problems**: `unzip -p deck.pptx
  ppt/slides/_rels/slideN.xml.rels` — in the NCAR template, layout4 = Title and
  Content, 6 = Two Content, 7 = Comparison. Hunt for orphan slides by
  extracting each slide's title and looking for "(no title)".
- **"Why is my line spacing 0.8?"**: `enable_autofit.py` turns on PowerPoint's
  shrink-on-overflow; when a box overflows, PowerPoint squeezes line spacing to
  its 0.8 floor on recompute. The master's body sizes (20/18/16/14/12 pt) are
  chosen so typical content *fits* and autofit never fires — don't bump them
  back up.
- Template edits must stay pandoc-compliant (layout names, the five
  `slideLayout1` placeholders) — see README "Template constraints" and its
  verification one-liner.

## Mermaid diagrams

- ```{mermaid} blocks render to PNG at build time through a headless browser;
  size with `%%| fig-width` (≈10 full-bleed, ≈5 in a column). Labels render in
  Trebuchet MS (mermaid's default theme font), not Poppins — diagrams are baked
  images, outside the template's font machinery.
- Layout tricks that work: subgraphs with `direction TB` + invisible `~~~`
  links to stack wide fan-outs vertically; an invisible `~~~` edge plus the
  real edge to force a child *below* its parent while the arrow points up.
  Avoid self-loops (sprawling arc, detached label) and `<br/>` in subgraph
  titles (clipped — a long title truncates mid-word rather than wrapping).
  Reversed arrow syntax (`A <-. l .- B`) silently renders the head on the
  wrong end — don't use it.
- **Subgraphs constrain layout hard; for multi-lane flows prefer node classes.**
  A subgraph's contents are kept contiguous, so two zones with edges between
  them land diagonally (wasting a quadrant) and the connecting edges cross —
  and a crossing edge that passes *behind* a node reads as an edge that does
  not exist. `direction` inside a subgraph is silently **ignored** whenever an
  edge crosses the subgraph boundary, which is exactly when you want it. Moving
  nodes between/inside the subgraphs does not help. If parallel lanes must stay
  readable, drop the boxes and mark the grouping with `classDef` fills plus a
  prefix in the node label (`CSG · …`, `HSG · …`); plain rank ordering then
  guarantees no crossings. `docs/sam_and_pbs/sam_and_pbs.qmd`'s "SAM to PBS
  Schematic" is the worked example — it took four renders to learn this.
- **Look at the rendered PNG, not the source.** Every mermaid failure above is
  silent: no warning, no error, just a diagram that is wrong or unreadable.
  Extract it from the deck and view it:
  `unzip -p deck.pptx ppt/slides/_rels/slideN.xml.rels` for the media id, then
  pull `ppt/media/imageM.png`. Check the aspect ratio too — a 16:9 content area
  is ≈2.4:1, so a much wider diagram scales down until the labels are unusable.
  The same goes for tall ones: a hub with five outputs as `flowchart LR` came
  out 1.4:1 with its right and bottom labels clipped (the renderer mis-measures
  wrapped `<br/>` lines). As `flowchart TB` with one short line per label, it
  was 2.7:1 and clean.
- `docs/sam_and_pbs/tree2mermaid.py` converts PBS `resource_group` trees into
  styled mermaid; its frozen inputs/fragments regenerate via `refresh_data.sh`
  (needs the `hpc-scheduling-tools` checkout four levels up + SAM credentials;
  rendering the deck itself never does).

## CI

`.github/workflows/ci-build-sample.yaml` renders the sample deck. Notes:
login-shell default (`bash -el`) is required for conda activation, and
because of it a `run:` script must not end with `exit N` (in a login shell
`exit` runs `~/.bash_logout`, which returns 1 on the runner and overrides
N; end with a test such as `test "$bad" -eq 0` instead);
`quarto install chrome-headless-shell` is required — quarto wedges forever
against the runner's system Chrome when rendering mermaid (job + `timeout`
guards keep any future hang to minutes, not the 6-hour cap).

## Git

- Standalone repo (often checked out nested inside `hpc-scheduling-tools/docs/`,
  which git-ignores it). Default branch `main`; branch + PR to merge.
- Generated outputs (`*.pptx`, `~$*` lock files, `*_files/`) stay untracked.
