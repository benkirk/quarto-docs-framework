# CLAUDE.md

Guidance for working in this repository. Keep it accurate — update it when the
structure or conventions below change.

## What this is

An NCAR-branded [Quarto](https://quarto.org) framework for documentation decks
(`.pptx` primary; `.html`/revealjs and `.pdf`/beamer secondary). Decks live
under `docs/<deck>/` as a `.qmd` plus a 1-line Makefile; shared machinery is in
`docs/common/` (branded `template.pptx`, `_quarto.yml`, Lua filter, post-render
utilities) and `docs/Make.common`. `docs/quickstart/quickstart.qmd` is the
short exemplar to copy for new decks; `docs/sample/sample.qmd` is the cookbook
of every pattern. The README covers layout, template constraints, and font
embedding.

- **README images** are `docs/quickstart/screenshots/*.png`, committed. After
  editing the quickstart deck run `make screenshots` there, look at them, and
  commit them. Slides are found by title (`SLIDES` in `screenshots.py`), so a
  renamed slide needs that list updated. Where the MathJax CDN is blocked, set
  `MATHJAX` to a local MathJax 2.7 (the npm tarball from registry.npmjs.org),
  or the equations shoot as raw TeX.

Other repos can take the framework as a submodule and keep their decks in their
own tree (README "Using the framework from another repo"); the deck Makefile
includes `../framework/docs/Make.common`. So nothing may assume a deck sits in
`docs/<deck>/`: the shared `_quarto.yml` reaches `common/` as `_ncar/`, a link
Make creates in each deck directory. `ci-consumer.yaml` builds a deck that way.

## Environment & build

- **Env**: `source etc/config_env.sh` (or `conda activate ./conda-env`; build it
  with `make conda-env`). Quarto **requires real conda activation** — the
  `activate.d` scripts export `QUARTO_DENO`, `QUARTO_PANDOC`, etc.; merely
  putting `conda-env/bin` on `PATH` fails with a missing-deno error.
- **Build**: `make pptx` (also `html`, `pdf`) inside the deck directory.
  `Make.common` names the output after the directory (`OUT`) and auto-symlinks
  `_quarto.yml` and `_extensions`. The pptx recipe post-processes with
  `section_subtitle.py`, `enable_autofit.py`, `embed_poppins.py`,
  `style_footnotes.py`, `link_captions.py`, `slide_layout.py`, and
  `style_tables.py` (tables drawn as in the HTML theme).
- **Publishing**: `make site` gathers the HTML decks into `_site/` (one shared
  `libs/`, `images/`, `SITE_EXTRA` directories, an index from `site_index.py`;
  `SITE_NOINDEX=1` marks every page noindex) and `make publish` force-pushes it
  as the one commit on `PUBLISH_BRANCH` (gh-pages) under `PUBLISH_PREFIX`.
  README "Publishing the HTML decks".
- **Slide footnotes** (a paragraph starting with `†`, or `‡` for a second): the
  theme (>= 2.4.0) lifts every one on a slide, columns included, to the slide's
  foot in HTML and PDF, under a short muted rule with the marker in the accent
  orange; pptx can't move content, so `style_footnotes.py` mutes them in place
  in the same colors. `*† text*` works too.
- **Linked images** (`[![](x.png)](url)`): the picture is the link in every
  format, and each shows the URL: the HTML footer and a PDF foot line come from
  `docs/common/linked-images.lua`, the pptx caption box from `link_captions.py`
  (after pandoc, because anything after an image splits a pptx slide). A deck
  should not hand-roll footers for this. README "Linked images".
- **Short slides** (`{.hcenter}`, `{.vcenter}`, `{.center}`, `scale="S"`,
  `{.fill}`, each independent): the theme (>= 2.5.0) centers and scales the
  body in HTML and PDF. pptx drops slide classes, so `common/slide-layout.lua`
  writes them as a notes line, `ncar-layout: vcenter scale=1.4`, which
  `slide_layout.py` applies and deletes; it can't do `hcenter` or `fill`, and
  centers a table by an estimated height. `.center` is the theme's, not
  Quarto's (which moves the title). README "Centering and scaling a short slide".
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
- **HTML** is `--to ncar-revealjs`, from the same vendored extension (see
  "revealjs (HTML) theme" below).
- **Theme options** (`themeoptions:` in a deck's front matter) replace the
  shared list in `docs/common/_quarto.yml`, so a deck that sets any must
  repeat `fonts=bundled`. Theme 2.3: `mathfont=` (default a serif math font,
  NewCM Book scaled to Poppins; `stix`, `lm`, `pagella`, `sans`, `fira`,
  `poppins` for the old Poppins-letter look, `keep`, or a font name; Quarto's
  own `mathfont:` key still wins) and `waves=false` (drops the faint wave
  lines behind content slides in PDF and HTML; pptx has them on the master).
  The waves are fitted to the brand's cover art by `tools/fit-waves.py` in
  the theme repo, which prints the TikZ and Lua blocks to paste.
- **Format conditionals**: `when-format="beamer"` matches the custom
  `ncar-beamer` format; `when-format="ncar-beamer"` matches nothing. Always
  write `beamer`.
- **Poppins has no arrows or ⚠**: theme 2.6 borrows ⚠ → ← ↔ ⇒ from DejaVu
  Sans in the PDF, so `## ⚠︎ Title` and `A → B` work in every format. Any other
  missing symbol still drops out of the PDF, with a warning in the log.
- **Divider subtitles**: a paragraph right after a `#` divider becomes that
  divider's subtitle in every format: `section_subtitle.py` for pptx, the
  theme's `\sectionsubtitle` (via its Lua filter) for beamer, and
  `ncar-revealjs.lua` for HTML. Only plain
  paragraphs qualify; anything else after a divider stays a slide of its own.
  In pptx the blue field, logo and waves are the template's Section Header
  layout, built by `branding/ncar/build_divider_layout.py` (rerun it after any
  template edit); `section_subtitle.py` adds "SECTION n", the tab and placement.
- **Front matter must be line 1** of every deck `.qmd`: anything above the
  opening `---` (an editor mode-line, a comment) hides it from Quarto, and
  `date: last-modified` renders literally (#7). CI checks this; set editor
  modes in the editor config, not in the file.
- **Fragments are prerequisites**: every deck in a directory depends on its
  `_*.qmd` fragments, `data/*`, `images/*` and deck-local `*.lua` filters, so editing any of
  them rebuilds all of them. A
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
  continuation. `docs/common/single-body.lua` (shared `_quarto.yml`,
  pptx-only) moves the paragraphs after one table or image (a † footnote, a
  remark) into its caption, which pandoc draws at the slide's foot;
  `style_footnotes.py` then styles a footnote there, left-aligned. Anything
  else after it (a list, code, a second table) still splits, on purpose. Never
  wrap such a body in a 100% column: pandoc gives the table the whole
  placeholder and silently drops the text after it (the slide count doesn't
  change, so `make qa` can't see it). Content *after* `.columns` still splits,
  so put it inside the last column. Code blocks are text and never split.
- **Speaker notes can go anywhere.** Pandoc only picks Two Content when the
  body *starts* with the columns div, so notes written before columns split the
  slide; `docs/common/notes-last.lua` (shared `_quarto.yml`, pptx-only) moves
  every slide's notes to its end. Notes after an image or table do not split.
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

## revealjs (HTML) theme

Lives in the vendored extension (`ncar-revealjs.{scss,css,js,lua}`,
`title-slide.html`); change it in the theme repo, like beamer. Things that
bit while building it:

- **The slide is 1600x900 slide pixels** (`width`/`height`, `margin: 0`);
  every length in the scss is in those units and reveal scales the whole
  slide. The waves are inline SVG in slide pixels, drawn by the Lua filter.
- **`url()`s go in `ncar-revealjs.css`, never the scss.** The scss compiles
  into `libs/revealjs/dist/theme/`, where relative URLs break; the css is an
  HTML dependency whose resources (fonts, `ncar-assets/web/` logos) are
  copied beside it and inlined under `embed-resources`. Web logos are
  separate RGB files: the PDF lockups are CMYK and convert off-color.
- **`hash-type: number` strips `#title-slide`**: target `.ncar-title`.
- **`?print-pdf` moves slides into `.pdf-page` and forces `padding: 0
  !important`**: use descendant selectors (`section.slide`, not
  `.slides > section`), restate padding under `html.reveal-print`, and keep
  `isolation: isolate` so the `z-index:-1` waves stay above the background.
- **A pandoc `Div` whose first block is a heading becomes a `<section>`**,
  which reveal counts as an extra slide (wrong numbering, a vanished slide).
  Wrap slide content in raw `<div>` tags from the filter instead.
- **pandoc's embed-resources inlines `<img src>`, not SVG `<image href>`**:
  the title photo is an `<img>` behind the wave SVG.
- **Mermaid pins its SVG to its natural width** (tiny labels); the scss
  lets it fill the column, capped by `calc(600px * var(--ncar-fit))`. The
  autofit script (`ncar-revealjs.js`) sets `--ncar-fit` when it shrinks a
  slide; `em` does not work there (mermaid sets `font-size: 16px`). Graphviz
  SVGs get the same cap.
- **Mermaid must render unscaled.** Quarto renders each diagram inside its
  slide, which reveal has scaled to the window, and mermaid measured labels at
  that scale (0.8 at 1280 px): boxes 20% small, labels clipped. The theme's
  script renders in mermaid's own scratch element instead (theme 2.2.0).
- **A percentage image height resolves against the whole slide**, so the
  beamer screenshot recipe `{height="72%"}` overflowed; the theme's Lua filter
  maps it onto the content height (2.2.0): 72% is the full cap, a smaller
  percentage is proportionally smaller.
- **`chalkboard` blocks `embed-resources`**, and `-M chalkboard:false` does
  not override a format option; set it in the deck's `format:` block.
- **`make qa` first** (README "Checking a deck"): it does the screenshots,
  overflow and slide-count checks below. Load the `deck-polish` skill for a
  format pass.
- **Check it in a browser, not the source**: serve the deck directory
  (`python3 -m http.server`; Playwright blocks `file://`) and screenshot each
  slide type, at 16:9 and a letterboxed size, plus `?print-pdf`. Run
  `Reveal.configure({transition: 'none'})` first or shots catch a fade, and walk
  `Reveal.getSlides()` with `Reveal.getIndices()`: the `##` slides nest
  vertically under their `#` divider, so `Reveal.slide(n)` stays on the divider.

## Mermaid diagrams

- ```{mermaid} blocks render to PNG at build time through a headless browser
  (pptx and PDF; the HTML deck draws them live, in brand colors and Poppins);
  size with `%%| fig-width` (≈10 full-bleed, ≈5 in a column). Labels render in
  Trebuchet MS (mermaid's default theme font), not Poppins — diagrams are baked
  images, outside the template's font machinery.
- **Install Chrome Headless Shell once** (`quarto install chrome-headless-shell`).
  With only the system Chrome, quarto's handshake can wedge and a render hangs
  with no output (CI hit it; so did a local `make all`, for 29 minutes).
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

## Graphviz diagrams

- ```{dot} cells render like mermaid (a PNG in pptx and PDF, live in revealjs) through
  Quarto's bundled Graphviz (WASM): nothing to install. Size them with `//| fig-width`.
- Use Graphviz where mermaid's layout fails: its clusters really cluster, and `rankdir`,
  `rank=same` and compass ports (`node:port:e`) steer the routing. Keep mermaid for
  simple flows and sequence diagrams.
- **Set `fontname` on `graph`, `node` and `edge`** ("Helvetica" renders as the WASM
  sans). Unset, it falls back to Times, so cluster labels come out serif. The WASM
  build cannot load Poppins.
- HTML-like labels (tables, ER boxes) have two silent traps:
  - an empty `<font></font>` makes Graphviz drop the whole label to plain text; emit an
    empty `<td></td>` instead;
  - a colon in a `port` name reads as `port:compass`, so name ports `col__out`, not
    `col:out`.
- As with mermaid: look at the rendered image, and keep it near 2.4:1.

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
