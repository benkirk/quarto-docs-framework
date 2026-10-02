---
name: deck-polish
description: >-
  A visual format pass over a Quarto deck in this framework: whitespace, overflow, table
  widths, diagram shape and font consistency, in every format (HTML, PDF, pptx). Load
  before a polish or "check the deck" pass to run `make qa`, read what it reports, and
  apply the known fixes, rather than rebuilding screenshot and measurement tooling.
---

# Polish a deck

`make qa` does the looking; this skill covers what to do with what it finds. The
layout controls themselves are documented in README "Centering and scaling a short
slide". Don't restate them; use them.

## Loop

1. `make -C docs/<deck> qa` (or `make qa DECKS=<name>` in a multi-deck directory). It
   builds every format, then writes `_qa/report.txt`, `usage.tsv`, `<deck>-html.png`
   and `<deck>-pdf.png` contact sheets, and per-slide PNGs.
2. Fix the failures (`source ...`, `PDF ...`, `HTML ...`, a slide-count MISMATCH)
   first. Then read both contact sheets yourself: the checks find overflow, not ugliness.
3. Work through the `hint` lines.
4. Rebuild and rerun until the report is clean. Then look at the sheets once more.
5. pptx is only counted. For a look, `soffice --headless --convert-to pdf deck.pptx`
   gives a contact sheet; the fonts will fall back to serif, so judge layout only.

## Known fixes

| Finding | Fix |
|---|---|
| short slide (hint) | `{.vcenter scale="1.15"}`. One size for every short slide, so text size stays steady across them. If the PDF then overflows, keep `{.vcenter}` alone |
| `.smaller` without `.fill` (hint) | drop `.smaller`: in HTML it shrinks the text to about 60% and leaves the slide empty |
| standalone table | `{.center .fill scale="S"}`. HTML fills, and S is sized so the PDF fits (beamer has no autofit) |
| CLI or code output | `{.vcenter .fill scale="S"}`, with S < 1 if a line runs past the margin |
| table past the right margin, or a cell running into the next column | give the pipe table explicit dash widths, e.g. `\|------------\|----------------------\|`. Pandoc only honors them when the separator row is longer than 72 characters, so pad the dashes past that |
| a date or hyphenated token breaking across lines in HTML | `[2024-08-27]{style="white-space: nowrap"}`. Beamer and pptx drop the span attributes |
| HTML autofit shrank a slide (hint) | the content overflowed at its scale. Lower `scale=` or trim; check that PDF page |
| a dot diagram whose text is squashed in the PDF | `fig-width` and `fig-height` disagree with the graph's own aspect. Set only `fig-width`, or reshape: a vertical chain in a 40% column beside the bullets |
| pptx count one higher, with content after a `.columns` block | move that content into the last column. `single-body.lua` handles content after a table or diagram, but leaves slides that already hold columns alone |
| `source ... bare <tag>` | put the placeholder in backticks. Unquoted, revealjs reads it as a tag, and `<code>` swallows every slide after it |
| a diagram that is a thin strip | reshape toward 2–3:1. A wide chain becomes a snake or a grid: Graphviz `layout=neato` with pinned `pos="x,y!"` (clusters are lost under neato). A column holding a diagram wants one taller than wide |

## Rules

- **Ask before reversing a deck decision.** If a decision is recorded in the deck's plan
  or handoff (for example, "bullet slides keep the deck's size"), ask before overturning it.
- **Monospace** goes on CLIs, daemons, packages, scripts, databases and branch names.
  Products (Kubernetes, Redis, Argo CD) and environment names stay plain. Diagram labels
  stay in one sans face.
  - List the names in `qa-names.txt` in the deck directory, one per line, and `make qa`
    reports each plain-text use. Section subtitles on the blue divider slides stay plain.
- **Generated tables** (frozen `_out_*.qmd` files written by a script): change the generator
  as well as the output, or the next refresh undoes the fix.
- Measure before scaling. `usage.tsv`'s `use` column is the share of the slide body the
  content fills in HTML. Up to 0.65 has room for ×1.15.

## Deferred: build these only if the friction repeats

- **No ignore list.** A deliberately dense demo slide (the sample's "Wall of Text") is
  reported on every run. If that gets noisy, add a `qa-ignore.txt` of `slide kind` pairs.
- **Sample deck overflows** found by the first `make qa`: p3 (the numbered list meets the
  frame number), p9 (a paragraph runs off the page) and the `_quarto.yml` slide (code plus
  column). Fix them, or ignore them once that list exists.
- **The table-column rule is heuristic.** It needs three lines starting at the same x, and it
  skips right-aligned number columns. It was tuned on this theme's longtable output. A
  different table style may need the threshold raised, or its own rule.
- **The PDF right edge** is 0.94 W for full-width pages and 0.97 W for column pages, which
  overhang the margin. A theme margin change moves both (`EDGE` / `COLS_EDGE`).
- **Overlays:** incremental pages map to one frame by the printed frame number. An
  unnumbered frame with overlays would miscount.
- **Diagrams are invisible to the PDF text checks** when they are mermaid PNGs. Only the
  HTML autofit hint and the contact sheet catch them.
- **pptx overflow is not checked.** PowerPoint autofit hides most of it. A LibreOffice
  render through the PDF checks would be the next step, with font fallback as the caveat.
- **Not in CI**, which would need a browser and TeX. A PDF-only mode (`--no-html`) is the
  likely first step.
- **Speed:** about 0.4 s a slide for the HTML pass. If decks grow, skip the screenshots or
  run in parallel.
- **Theme follow-ups seen in the SAMuel pass:**
  - revealjs inline code breaks at hyphens inside table cells;
  - two-line slide titles run into the title rule in HTML.

  Both belong in the theme repo.
