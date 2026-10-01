#!/usr/bin/env python3
"""Restyle on-slide footnotes in a pandoc-rendered pptx.

Pandoc's pptx writer ignores inline font size/color from markdown, so a
"footnote" authored in the `.qmd` renders at full body size and the brand
text color — indistinguishable from an ordinary paragraph. This script
finds every body paragraph whose text begins with a footnote marker
(`†`, or `‡` for a second one) and restyles it to read as a footnote: the
theme's muted gray, a smaller size, a little space above to set it off from
the bullets, and the marker itself in the brand accent orange (the HTML and
PDF themes draw the same, and also move footnotes to the slide's foot, which
pptx cannot do without splitting the slide). Author the line
in the deck as a normal paragraph, e.g.

    *† Shown for CPU jobs to keep it concrete — the idea generalizes …*

and this step does the rest. The leading marker stays visible.

Idempotent: re-running only re-applies the same properties. Harmless to
decks with no footnote paragraphs (it touches nothing)."""

import copy
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor

MARKERS     = ("†", "‡")               # dagger, double dagger
FOOT_SIZE   = Pt(13)                   # body is 18–20 pt; this is a clear step down
FOOT_COLOR  = RGBColor(0x6B, 0x7C, 0x99)   # the theme's $ncar-muted
MARK_COLOR  = RGBColor(0xFA, 0xA1, 0x19)   # BrandOrange, the theme's accent
FOOT_BEFORE = Pt(10)                   # vertical gap above the footnote


def _split_marker(para):
    """The first run, cut so the marker is a run of its own (idempotent)."""
    first = para.runs[0]
    text = first.text.lstrip()
    marker = text[0]
    if text.rstrip() != marker:
        mark = copy.deepcopy(first._r)
        first._r.addprevious(mark)
        first.text = text[1:].lstrip()
        para.runs[0].text = marker + " "
    return para.runs[0]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: style_footnotes.py <file.pptx>", file=sys.stderr)
        return 2
    pptx = Path(sys.argv[1]).resolve()
    if not pptx.exists():
        print(f"error: {pptx} not found", file=sys.stderr)
        return 2

    prs = Presentation(str(pptx))
    styled = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                if not para.runs or not para.runs[0].text.lstrip().startswith(MARKERS):
                    continue
                para.space_before = FOOT_BEFORE
                mark = _split_marker(para)
                for run in para.runs:          # every run — the code span too
                    run.font.size = FOOT_SIZE
                    run.font.color.rgb = MARK_COLOR if run._r is mark._r else FOOT_COLOR
                styled += 1
    prs.save(str(pptx))
    print(f"style_footnotes: restyled {styled} footnote paragraph(s) → {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
