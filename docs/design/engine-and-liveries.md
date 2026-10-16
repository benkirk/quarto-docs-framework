# One engine, many liveries

A design for taking this framework from one brand (NSF NCAR) to many: CU Boulder,
NASA, and a family of NASA program flavors, each onboarded from a reference
PowerPoint the customer supplies. It is written to be the founding design of two
new repositories (section 2), forked from this one and from the NCAR beamer theme,
so that the NCAR pair keeps serving its users untouched.

Vocabulary, used throughout:

| Term | Meaning |
|---|---|
| **engine** (the chassis) | everything that is the same whoever's logo is on the slide: the layout machinery, styles that read roles and geometry rather than colors and lengths, the Lua filters, the autofit script, the pptx post-processors, QA and site tooling |
| **livery** | one brand flavor as a directory of data and assets: palette mapped onto roles, type, logos, art, geometry, the pandoc-compliant `template.pptx`, and the customer's reference deck |
| **flavor** | a livery that `extends` another and overrides a few keys (a NASA program under NASA). Not a separate concept, just a short livery |

An airline paints identical aircraft in its own livery. That is the whole idea.

## 1. Where the brand lives today

The survey behind this design found the NCAR brand in roughly thirty places across
three copies of the same data. The seam already exists, which is why the design is an
opening of it rather than a rewrite.

**The beamer theme is two-layered.** `ncar_branding.sty` (vendored under
`docs/common/_extensions/benkirk/ncar/`) owns the palette (eleven `\definecolor`s,
lines 34-46), six semantic roles switched by `brand=ncar|ucar|ncarucar`
(`BrandPrimary`, `BrandPrimaryText`, `BrandPrimaryContrast`, `BrandSecondary`,
`BrandAccent`, `BrandText`, lines 49-62), the fonts (Poppins, bundled under
`ncar-assets/fonts/Poppins/`), and the logo lockups. The color, inner and outer
themes read roles about 80% of the time. The leaks that read raw palette names:

- callouts in `ncar-beamer.lua:321-332` (`NCARBlue`, `UCARAquaContrast`, `BrandOrange`)
- `example text`, `block title example`, `block title alerted` in `beamercolorthemeNCAR.sty`
- `\cmark`, `\xmark`, `\pmark` and the `ncar` listings style in `ncar_branding.sty`
- feature frames (`LightBlue`, `Space`) and the slide footnotes (`CoolGray4`, `CoolGray7`)
- `ncar.theme`, the highlight theme, with NCAR hexes

**The revealjs side carries the data again**: `$ncar-*` variables in
`ncar-revealjs.scss` (and five `--ncar-*` custom properties on `:root`, overridden under
`html.ncar-brand-ucar`), a `BRANDS` table in `ncar-revealjs.lua:63`, logo `url()`s in
`ncar-revealjs.css`, and the Poppins `@font-face` rules. The waves are inline SVG drawn
by the Lua filter from the same control points the TikZ uses.

**The pptx side carries it a third time**, split between the template and the
scripts. `template.pptx`'s `theme1.xml` has the scheme (dk1 `00357A`, dk2 `0057C2`,
lt2 `F1F0EE`, accent1 `42C0FF`, accent4 `FAA119`, accent5 `FDD509`; both fonts Poppins).
The content-slide waves on the master are a raster, `ppt/media/image1.png`; only the
Section Header layout is procedural (`branding/ncar/build_divider_layout.py`). The
post-render scripts hardcode hex constants and Poppins paths and take no brand
argument: `style_footnotes.py:35-36`, `style_tables.py:30-32`,
`slide_layout.py:43-45`, `link_captions.py`, `section_subtitle.py:58-70` (the divider
geometry and the Poppins files it measures with), `embed_poppins.py:28` (the
`.fntdata` blobs and the `Poppins` typeface name), `site_index.py` (palette and Google
Fonts link), and `linked-images.lua:11`. Only `section_subtitle.py` and
`build_divider_layout.py` write theme scheme slots and are brand-neutral already.

**The glue is brand-named**: `Make.common` renders `--to ncar-revealjs` and
`--to ncar-beamer` and links `common/` into each deck directory as `_ncar`; the shared
`_quarto.yml` says `reference-doc: _ncar/branding/ncar/template.pptx`.

**Geometry is a fourth copy.** The same lengths appear as `0.06\paperwidth`,
`0.018\paperwidth`, `0.06\paperheight` in `beamerouterthemeNCAR.sty:38-41`, as
`$ncar-margin: 96px`, `$ncar-tab: 29px`, `$ncar-logo-h: 58px` in the scss (lines
82-84, in 1600x900 slide pixels), as `TAB_W = 29` in `section_subtitle.py:66`, and as
`EDGE = 0.94` in `deck_qa.py:33`.

## 2. Repositories

Two new repositories, forked, with general nouns. The NCAR repositories stay exactly as
they are for the people who use `\usetheme{NCAR}` from LaTeX and for the NCAR decks
built here.

```
benkirk/NCAR_beamer_template ──fork──▶ beamer-livery-theme   engine + reference liveries (ncar, ucar, ncarucar)
                                           │ vendored into the framework (quarto add / quarto update)
benkirk/quarto-docs-framework ─fork──▶ quarto-livery-decks   framework: Make.common, post-processors, QA,
                                           │             liveries/ for cu, nasa, nasa/<program>
                                           │ git submodule
                                        <customer>-decks  the customer's .qmd decks; each deck Makefile
                                                          includes ../framework/docs/Make.common and sets LIVERY
                              optional: <customer>-liveries  a customer's liveries in their own repo, vendored
                                                          into quarto-livery-decks, only when logo license, privacy
                                                          or ownership require a separate home
```

Names, settled 2026-10-16 before the forks were created:

| What | Name |
|---|---|
| engine repo | `beamer-livery-theme` |
| Quarto extension directory, hence format names | `engine` → `engine-beamer`, `engine-revealjs` |
| LaTeX theme and brand package | `\usetheme[livery=<dir>]{Engine}`, `engine_livery.sty` |
| framework repo | `quarto-livery-decks` |
| links Make creates in a deck directory | `_engine` (today `_ncar`) and `_livery` |

With the rename, every `ncar@` macro, `ncar-*` CSS class and HTML id, `--ncar-*` custom
property, `ncar-layout:` notes line, and `ncar-beamer:` warning prefix takes the new
noun. `when-format="beamer"` keeps working, because the base format is unchanged.

**Why forks rather than refactoring in place.** The Quarto format names derive from the
extension's directory name and an extension cannot alias another's formats, so a clean
rename is a breaking change for anyone using `ncar-beamer` from Quarto. The LaTeX entry
point `\usetheme{NCAR}` and the `ncar@` macro namespace are the same story. A fork gives
the general names a clean start and the NCAR names an undisturbed home.

**Coexistence and the exit.** The ncar livery in the engine is the forward path for NCAR
decks, and byte-level parity of its output with today's is the acceptance test of the
whole refactor (section 8). Once that holds, two optional moves end the double
maintenance: `beamerthemeNCAR.sty` upstream becomes a shim
(`\usetheme[livery=ncar]{Engine}` behind the old option names), and this repo becomes a
thin consumer of `quarto-livery-decks` with `LIVERY=ncar`. Neither is required by this design.

**Where liveries live** is a licensing and ownership question, not a code one. The
reference liveries ship with the engine (they are its test fixtures). New liveries
start in `quarto-livery-decks/docs/common/liveries/`. A customer's set moves to its own repo
only when the assets demand it: NASA insignia and program lockups may well. The contract
is per directory, so a repo can hold one livery or ten; this is deliberately neither one
repo per customer per style nor one per customer.

## 3. The template is the spec

Each brand reproduces its reference deck's layout, not only its palette. So geometry has
one source of truth: the livery's pandoc-compliant `template.pptx`, built from the
reference deck's own master and layouts (section 6). beamer and revealjs imitate it from
measurements the compile step extracts (placeholder boxes, logo box, footer, divider
field), stored as fractions of the slide and converted to beamer paper fractions and to
1600x900 slide pixels.

This inverts today's flow, where scss constants were copied into Python, and makes
"pptx primary" literal. Fidelity is graded: pptx exact (it is the customer's master);
HTML and PDF faithful to the measured geometry; whatever parameters cannot express goes
into the livery's override files (section 4).

Consequences for the engine: every length in `beamerouterthemeNCAR.sty:38-41`, every
`$ncar-*` length in the scss, and the geometry constants in `section_subtitle.py`,
`slide_layout.py` and `deck_qa.py` become livery values, with today's numbers recorded
as the ncar livery's measurements.

## 4. The livery contract

```
liveries/<name>/
  _brand.yml      the authoring manifest, in the Quarto/Posit brand.yml standard, kept
                  strictly standard: color.palette plus color.primary/secondary/foreground/
                  background, typography fonts with file sources, logo light and dark
  livery.yml      engine knobs the standard has no slot for: extends; roles (primary-text,
                  primary-contrast, accent, muted, surface, warning, dark); art {title,
                  content, section, closing, feature}; divider {label, eyebrow, tab};
                  pptx {template, fonts, typeface}; aspect (16:9 default); overrides
  template.pptx   THE SPEC: pandoc-compliant, derived from the reference deck (section 6)
  logos/          pdf (LaTeX) and png/svg (web, RGB), same basenames, light and dark variants
  art/            background art per slide kind: svg (web) + pdf (LaTeX) + png (pptx master
                  and layouts). The NCAR waves become three such files, exported once from
                  the existing TikZ and SVG generators; the engine has no procedural motif
  fonts/          ttf; fonts/pptx/*.fntdata embedded once by hand in PowerPoint (Options >
                  Save > Embed fonts; no reliable Python writer exists). Absent: embedding
                  is skipped with a warning
  overrides/      the escape hatch: livery-extra.sty, livery-extra.css, livery-extra.lua
  reference/      the customer's deck(s), extracted media, report.md, onboarding notes.
                  Never read at build time
  build/          GENERATED by livery_build.py, committed, freshness checked in CI:
                  livery.json   the one resolved truth, extends applied, geometry included;
                                Lua (quarto.json) and Python both read it
                  livery.sty    \definecolor palette, \colorlet roles, logo, font and
                                geometry macros: what \usetheme[livery=...] inputs
                  livery.css    @font-face, logo and art url()s, :root{--engine-*} values
                  livery.theme  the pandoc highlight theme in the palette
```

**Why brand.yml for authoring and nothing more.** It is Quarto's own brand standard
(1.6+), so a livery author gets a documented schema and tooling instead of a house
format. But Quarto's own `brand:` processing is not used at render time: it reaches only
revealjs (not beamer, not pptx), its generated Sass layer sits below the theme's scss
(which would silently win), and its Lua API needs Quarto 1.7. So `_brand.yml` is read by
the compile step only, and the shared `_quarto.yml` never sets `brand:`.

**Why derived, committed outputs.** LaTeX cannot read YAML, and standalone users need a
`.sty`; the pptx post-processors run outside Quarto; `extends` should resolve exactly
once, in one place. Committed generated files are already the repo's pattern
(`build_divider_layout.py`, the README screenshots), with a `--check` mode in CI.

**pptx color contract.** The template's `theme1.xml` scheme carries the roles, so most
post-processors need no brand argument at all; they write scheme slots the way
`section_subtitle.py` already does:

| slot | role | | slot | role |
|---|---|---|---|---|
| `dk1` | text | | `accent1` | secondary |
| `lt1` | white | | `accent4` | accent |
| `dk2` | primary | | `accent5` | warning |
| `lt2` | surface | | | |

Muted and the caution fill have no slot and come from `livery.json`.

**`extends`.** A deep merge inside the generator; the child's files override the
parent's by name. A flavor without its own template gets the parent's template recolored
(scheme swap in `theme1.xml`, logo media swap), which is the same operation the
onboarding pipeline performs, so it costs nothing extra.

**Geometry in `livery.json`**, measured from the template (section 6), in fractions of
the slide: content area, title box, logo box (corner, height, aspect), footer and slide
number boxes, the divider's field and label box, the body size ladder (today
20/18/16/14/12 pt, chosen so autofit never fires). The engine converts to its units.

## 5. The engine contract

For `beamer-livery-theme`:

- `\usetheme[livery=<absolute dir>]{Engine}` inputs `<dir>/build/livery.sty` and the
  optional `overrides/livery-extra.sty`. The color, inner and outer themes read only
  roles and geometry macros; the leaks listed in section 1 move to roles, with new
  roles `BrandMuted`, `BrandSurface`, `BrandWarning`, `BrandDark` for what the six
  cannot express. Page backgrounds per style (title, content, section, closing, feature)
  come from `art/` as PDF includes instead of TikZ.
- `engine-beamer.lua` reads the metadata key `livery:`, resolves it to an absolute path
  (the `\input@path` trick stays), and passes `livery=`. Absent, the engine's bundled
  ncar reference livery applies, so an old framework and a new engine still build.
- `engine-revealjs.lua` reads `livery:` → `build/livery.json`. `add_dependency()`
  attaches `build/livery.css` plus the livery's fonts, logos and art as dependency
  resources, and injects a `:root{--engine-*}` style block. The scss expresses every
  color and length as `var(--engine-*)` with the ncar values as defaults, so one
  compiled theme serves every livery. Backgrounds are the livery's SVGs.
- `highlight-style` is overridable by the project (`_livery/build/livery.theme`).
- The reference liveries live under `liveries/` in the engine repo; vendoring brings
  them along under the extension directory, and the framework's `liveries/ncar` becomes a
  link to the vendored copy.

For `quarto-livery-decks`:

- The post-processors keep their jobs and lose their constants, parameterized by
  `livery.json` and scheme slots: `embed_fonts.py` (was `embed_poppins.py`; typeface
  and blobs from the livery), `section_subtitle.py` (fonts to measure with, divider
  label and geometry), `style_tables.py`, `style_footnotes.py`, `slide_layout.py`
  (slots; muted and caution fill from the livery), `link_captions.py`,
  `linked-images.lua` (`quarto.json.decode` of `livery.json`), `site_index.py`
  (palette and font family; a Google Fonts link only for a google source),
  `deck_qa.py` (`EDGE` from the livery's margin).
- `Make.common`: `LIVERY ?= ncar`; `LIVERY_DIR ?= $(SHARED_COMMON)/liveries/$(LIVERY)`;
  a `.livery` stamp whose content is `$(LIVERY)` and an `ln -sfn` rule for the `_livery`
  link (a missing-only rule, like today's three, would silently keep the old livery
  after `make LIVERY=cu`); `DEPS += _livery`; `FORMAT_HTML ?= engine-revealjs` and
  `FORMAT_PDF ?= engine-beamer`; `LIVERY_DIR` exported for the scripts.
- The shared `_quarto.yml`: `reference-doc: _livery/template.pptx` and a top-level
  `livery: _livery`, the key by which both Lua filters find the livery. No `brand:`.
- CI: `livery_build.py --check` over every livery; a matrix over liveries rendering the
  quickstart deck with `LIVERY=$x`, grepping `ppt/theme/theme1.xml` for the livery's
  primary hex, `embeddedFontLst` for its typeface, and the HTML for `livery.css`; the
  consumer workflow checks the `_livery` link beside the three it checks today.

## 6. Onboarding a brand from a reference PowerPoint

Every new brand starts from a deck the customer supplies: a visual guide, not a
pandoc-compliant template. Reverse-engineering it is a repeatable step, with three tools
and a short list of judgement calls.

**What the tools can rely on.** python-pptx enumerates masters, layouts, placeholders
(type, index, box), pictures and media, and can rename layouts. It cannot edit
`theme1.xml`, embed fonts, set `showMasterSp`, add typed placeholders to a layout, or
cleanly delete layouts. The repo convention holds: python-pptx for the report,
lxml-on-zip for the writes, fixed zip timestamps for reproducible files.

**Tools**, in `docs/common/utils/`:

1. `livery_inspect.py reference.pptx <livery dir>` writes `reference/report.md` (slide
   size and aspect; the twelve scheme slots; the font scheme; per master and layout its
   name, type, placeholders with boxes, pictures and background fill; every `srgbClr`
   ranked by frequency), extracts the media into `reference/media/`, and seeds
   `_brand.yml` (palette from the slots and the frequent hexes, fonts from the font
   scheme) and a `livery.yml` with a blank layout-mapping table.
2. `livery_template.py <livery dir>` produces the compliant template from the reference's
   master and the mapped layouts: renames them to pandoc's names (`Title Slide`,
   `Title and Content`, `Section Header`, `Two Content`, `Comparison`,
   `Content with Caption`, `Blank`), guarantees the five `slideLayout1` placeholders
   (`ctrTitle`, `subTitle`, `dt`, `ftr`, `sldNum`), writes the slot contract into
   `clrScheme` and the font scheme, places art and logo media as `ppt/media/image*`,
   injects `fonts/pptx/*.fntdata` if present, and then measures the result into the
   geometry block of `livery.json`.
3. `livery_check.py <livery dir>` verifies layout names, the five placeholders, the slot
   contract, media naming and `build/` freshness, then runs
   `make -C docs/quickstart qa LIVERY=<name>`.

**The human steps**, in order: inspect → map the reference layouts onto pandoc's (which
of a customer's six title variants is "Title Slide"; which rich layouts pandoc can never
pick and should be dropped) → choose the roles (customer slots are arbitrarily ordered,
`dk2` is not reliably the primary; the builder warns on WCAG contrast for the
small-text role) → logo variants and clear space → art per slide kind (vector preferred;
rasters acceptable on masters, never as a procedural recipe) → build, template, check →
open the template in PowerPoint (the "Repair?" prompt cannot be automated) → `make
screenshots` contact sheet reviewed against the reference and committed under
`reference/` → commit.

**Not doable, by design**: extracting the reference's embedded fonts (licensing, EOT
decoding; the customer supplies the TTFs), and vectorizing bitmap art.

## 7. Phasing

0. This document, copied into both forks as their founding design; nouns settled.
1. `quarto-livery-decks`: de-brand the framework with the ncar livery as the migration proof.
   Move `branding/ncar/` to `liveries/ncar/`, write its `_brand.yml` and `livery.yml`
   from `ncar_branding.sty`, add `livery_build.py` and the `livery.py` loader,
   parameterize the post-processors one per commit, add `LIVERY` to Make, and wire CI.
   Every step is parity-checked (section 8).
2. `beamer-livery-theme`: the engine refactor of section 5 (rename, roles only, geometry from
   the livery, art files, `livery=`); re-vendor into the framework; `liveries/ncar`
   becomes a link to the vendored reference livery.
3. CU Boulder: the first foreign livery and the first run of the onboarding tools (no
   waves, other fonts, a template from a reference deck). Joins the CI matrix.
4. NASA general, then the first program flavor via `extends` (recolored template, its
   own lockups).

## 8. Verification

- Phase 1 holds a baseline built on `main` (`make all`, `make qa`, `make screenshots`
  for `docs/sample` and `docs/quickstart`) and checks after every step: per-part XML
  diff of the unzipped pptx (timestamps differ, XML must not), `pdftotext` equal, an
  empty `git diff docs/quickstart/screenshots`, and the greps CI already runs
  (`image-divider-logo.png`, `ncar-section-label`, `embeddedFontLst`).
- Phase 2: the ncar livery's generated `livery.sty` diff-equals the color block of
  `ncar_branding.sty:34-62`; the engine's own sample decks render byte-equal under
  `livery=ncar` and under the old `brand=ucar`.
- Phases 3 and 4: `livery_check.py`, `make qa LIVERY=<name>`, a reviewed contact sheet
  against the reference deck, and PowerPoint opening the template without a repair
  prompt.

## 9. Risks and open questions

- Reproducing pptx geometry in HTML and PDF from measurements will be approximate for
  exotic layouts. The override files are the valve; decide per livery how far to chase.
- A 4:3 reference deck: `aspect` is in the contract, but phase 3 should confirm the
  engine handles it or declare 16:9 only.
- pandoc's layout chooser is fixed. The demotions documented in `CLAUDE.md` (Two
  Content, Comparison, Content with Caption) apply to every livery, and a reference
  deck's richer layouts are unreachable from Markdown; drop them from the template.
- Body size ladders: a brand face far from Poppins' x-height may need its own ladder to
  keep autofit quiet. It is a livery value, so this is a per-brand tuning, not an
  engine change.
- Naming is settled (section 2). The nouns were picked before the forks were created, since
  they end up in format names, macro namespaces and CSS classes.
