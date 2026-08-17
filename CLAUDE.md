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
  `Make.common` names the output after the directory and auto-symlinks
  `_quarto.yml`. The pptx recipe post-processes with `enable_autofit.py` and
  `embed_poppins.py`.
- **Stale-fragment gotcha**: make only tracks the deck's own `.qmd` — after
  editing an included fragment (`_*.qmd`) or `data/`, `touch <deck>.qmd` (or the
  render is skipped).
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
- `docs/sam_and_pbs/tree2mermaid.py` converts PBS `resource_group` trees into
  styled mermaid; its frozen inputs/fragments regenerate via `refresh_data.sh`
  (needs the `hpc-scheduling-tools` checkout four levels up + SAM credentials;
  rendering the deck itself never does).

## CI

`.github/workflows/ci-build-sample.yaml` renders the sample deck. Notes:
login-shell default (`bash -el`) is required for conda activation;
`quarto install chrome-headless-shell` is required — quarto wedges forever
against the runner's system Chrome when rendering mermaid (job + `timeout`
guards keep any future hang to minutes, not the 6-hour cap).

## Git

- Standalone repo (often checked out nested inside `hpc-scheduling-tools/docs/`,
  which git-ignores it). Default branch `main`; branch + PR to merge.
- Generated outputs (`*.pptx`, `~$*` lock files, `*_files/`) stay untracked.
