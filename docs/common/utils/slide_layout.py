#!/usr/bin/env python3
"""Apply the theme's per-slide layout controls to a pandoc-rendered pptx.

pandoc drops slide classes, so common/slide-layout.lua leaves one speaker-notes
line, "ncar-layout: vcenter scale=1.4", on each slide that asks for a layout.
This step removes the line and applies what pptx can express:

  vcenter   body text anchored at the middle of its placeholder; a table moved
            to the middle of the area pandoc gave it (an estimate: PowerPoint
            sizes table rows itself, so the height is rows x line height)
  scale=S   every body and table run at S times its inherited size
  hcenter, fill   nothing: a text box cannot shrink-wrap, and nothing measures

Footnote paragraphs (style_footnotes.py) keep their size. Idempotent: the
marker is gone after the first pass."""

import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.oxml.ns import qn
from pptx.util import Pt

MARKER    = "ncar-layout:"
FOOTNOTES = ("†", "‡")
NOT_BODY  = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.DATE,
             PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER}
LINE      = 1.2           # line height / font size, for the table estimate
CELL_PAD  = Pt(7.2)       # a cell's default top + bottom margins (0.05 in each)


def _take_marker(slide):
    """The slide's layout words, with their notes paragraph removed."""
    if not slide.has_notes_slide:
        return None
    tf = slide.notes_slide.notes_text_frame
    if tf is None:
        return None
    for p in tf.paragraphs:
        if p.text.strip().startswith(MARKER):
            words = p.text.strip()[len(MARKER):].split()
            body = p._p.getparent()
            body.remove(p._p)
            if body.find(qn("a:p")) is None:
                etree.SubElement(body, qn("a:p"))
            return words
    return None


def _lvl_size(txstyle, level):
    """sz (hundredths of a point) for a paragraph level in a list-style element."""
    if txstyle is None:
        return None
    lvl = txstyle.find(qn(f"a:lvl{level + 1}pPr"))
    rpr = lvl.find(qn("a:defRPr")) if lvl is not None else None
    return int(rpr.get("sz")) if rpr is not None and rpr.get("sz") else None


def _inherited(shape, slide, level):
    """A body placeholder's size at a level: its layout's lstStyle, then the master."""
    try:
        idx = shape.placeholder_format.idx
        lph = slide.slide_layout.placeholders.get(idx=idx)
    except (KeyError, ValueError, AttributeError):
        lph = None
    if lph is not None:
        sz = _lvl_size(lph._element.find(".//" + qn("a:lstStyle")), level)
        if sz:
            return sz
    master = slide.slide_layout.slide_master._element
    return _lvl_size(master.find(".//" + qn("p:bodyStyle")), level) or 1800


def _other_size(slide):
    master = slide.slide_layout.slide_master._element
    return _lvl_size(master.find(".//" + qn("p:otherStyle")), 0) or 1800


def _scale_paragraphs(paragraphs, scale, size_at):
    for p in paragraphs:
        if p.text.lstrip().startswith(FOOTNOTES):
            continue
        base = size_at(p.level)
        for r in p._p.iter(qn("a:rPr"), qn("a:endParaRPr")):
            sz = int(r.get("sz")) if r.get("sz") else base
            r.set("sz", str(round(sz * scale)))


def _is_body(shape):
    return (shape.is_placeholder and shape.has_text_frame
            and shape.placeholder_format.type not in NOT_BODY)


def lay_out(slide, words):
    scale = 1.0
    for w in words:
        if w.startswith("scale="):
            try:
                scale = float(w[len("scale="):])
            except ValueError:
                pass
    vcenter = "vcenter" in words
    for shape in slide.shapes:
        if _is_body(shape):
            if scale != 1.0:
                # runs without an rPr inherit too: give each one, so sz has a home
                for r in shape.text_frame._txBody.iter(qn("a:r")):
                    if r.find(qn("a:rPr")) is None:
                        r.insert(0, etree.Element(qn("a:rPr")))
                _scale_paragraphs(shape.text_frame.paragraphs, scale,
                                  lambda lvl, s=shape: _inherited(s, slide, lvl))
            if vcenter:
                shape.text_frame._txBody.find(qn("a:bodyPr")).set("anchor", "ctr")
        elif getattr(shape, "has_table", False):
            other = _other_size(slide)
            rows = list(shape.table.rows)
            biggest = other
            for row in rows:
                for cell in row.cells:
                    tf = cell.text_frame
                    if scale != 1.0:
                        for r in tf._txBody.iter(qn("a:r")):
                            if r.find(qn("a:rPr")) is None:
                                r.insert(0, etree.Element(qn("a:rPr")))
                        _scale_paragraphs(tf.paragraphs, scale, lambda lvl: other)
                    for r in tf._txBody.iter(qn("a:rPr")):
                        if r.get("sz"):
                            biggest = max(biggest, int(r.get("sz")))
            if vcenter and rows:
                est = int(len(rows) * (Pt(biggest / 100) * LINE + CELL_PAD))
                if est < shape.height:
                    shape.top = shape.top + (shape.height - est) // 2
                    shape.height = est


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: slide_layout.py <file.pptx>", file=sys.stderr)
        return 2
    pptx = Path(sys.argv[1]).resolve()
    if not pptx.exists():
        print(f"error: {pptx} not found", file=sys.stderr)
        return 2

    prs = Presentation(str(pptx))
    done = 0
    for slide in prs.slides:
        words = _take_marker(slide)
        if words is not None:
            lay_out(slide, words)
            done += 1
    prs.save(str(pptx))
    print(f"slide_layout: laid out {done} slide(s) → {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
