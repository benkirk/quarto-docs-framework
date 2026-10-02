#!/usr/bin/env python3
"""Style every table in a pandoc-rendered pptx as the HTML deck draws them.

pandoc writes each table with PowerPoint's built-in "Medium Style 2 - Accent 1"
and no way to choose another, so tables come out with a Light Blue header and
banded fills, unlike the revealjs theme (ncar-revealjs.scss, `table`). This
replaces the style with direct cell formatting, which PowerPoint and
LibreOffice both render:

  header row   no fill; bold Dark Blue capitals, letter-spaced, at 0.8x the body
               size; a 3 px NCAR Blue rule beneath
  body rows    a 1 px rule beneath each, in Dark Blue 20% into Light Gray; every
               second row filled with Light Gray at 60% on white
  columns      left alone when pandoc took widths from the source (the dash
               counts of a wide pipe table); when it split them evenly, re-split
               in proportion to each column's longest cell, each 10-60% wide

Run it last, after slide_layout.py has scaled the runs. Idempotent: a second
pass writes the same properties."""

import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.oxml.ns import qn

NO_STYLE    = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # "No Style, No Grid"
PX          = 7620                     # EMU per revealjs px (1600 px wide)
HEAD_RULE   = (3 * PX, "0057C2")       # 3px solid var(--ncar-primary)
ROW_RULE    = (1 * PX, "C1CBD7")       # mix(#00357A, #F1F0EE, 20%)
BAND_FILL   = "F7F6F5"                 # rgba(#F1F0EE, 0.6) on white
HEAD_SCALE  = 0.8                      # th 0.8em of the table's 0.85em, ~0.8x td
HEAD_SPC    = 0.04                     # letter-spacing: 0.04em
SHARE       = (0.10, 0.60)             # column width bounds when re-split


def _ln(tag, rule):
    ln = etree.Element(qn(tag))
    if rule is None:
        etree.SubElement(ln, qn("a:noFill"))
        return ln
    width, color = rule
    ln.set("w", str(width))
    fill = etree.SubElement(ln, qn("a:solidFill"))
    etree.SubElement(fill, qn("a:srgbClr"), val=color)
    return ln


def _style_cell(tc, rule, fill):
    """Borders and fill on a cell's tcPr, in schema order, replacing any before."""
    tc_pr = tc.find(qn("a:tcPr"))
    if tc_pr is None:
        tc_pr = etree.SubElement(tc, qn("a:tcPr"))
    for child in list(tc_pr):
        if child.tag in {qn(t) for t in ("a:lnL", "a:lnR", "a:lnT", "a:lnB",
                                         "a:noFill", "a:solidFill")}:
            tc_pr.remove(child)
    pos = 0
    for tag, r in (("a:lnL", None), ("a:lnR", None), ("a:lnT", None), ("a:lnB", rule)):
        tc_pr.insert(pos, _ln(tag, r))
        pos += 1
    if fill is None:
        tc_pr.insert(pos, etree.Element(qn("a:noFill")))
    else:
        solid = etree.Element(qn("a:solidFill"))
        etree.SubElement(solid, qn("a:srgbClr"), val=fill)
        tc_pr.insert(pos, solid)


def _header_runs(tc, base):
    for r in tc.iter(qn("a:r")):
        r_pr = r.find(qn("a:rPr"))
        if r_pr is None:
            r_pr = etree.Element(qn("a:rPr"))
            r.insert(0, r_pr)
        if r_pr.get("cap") != "all":   # idempotent: scale the size only once
            size = int(r_pr.get("sz") or base) * HEAD_SCALE
            r_pr.set("sz", str(round(size)))
            r_pr.set("spc", str(round(size * HEAD_SPC)))
        r_pr.set("b", "1")
        r_pr.set("cap", "all")


def _rebalance(tbl):
    cols = tbl.findall(qn("a:tblGrid") + "/" + qn("a:gridCol"))
    widths = [int(c.get("w")) for c in cols]
    if len(cols) < 2 or max(widths) - min(widths) > len(cols):
        return
    longest = [1] * len(cols)
    for tr in tbl.findall(qn("a:tr")):
        for i, tc in enumerate(tr.findall(qn("a:tc"))[:len(cols)]):
            text = "".join(t.text or "" for t in tc.iter(qn("a:t")))
            longest[i] = max(longest[i], len(text))
    total = sum(widths)
    shares = [min(max(n / sum(longest), SHARE[0]), SHARE[1]) for n in longest]
    norm = sum(shares)
    for col, share in zip(cols, shares):
        col.set("w", str(round(total * share / norm)))


def style_table(tbl, base):
    tbl_pr = tbl.find(qn("a:tblPr"))
    tbl_pr.attrib.pop("bandRow", None)
    style_id = tbl_pr.find(qn("a:tableStyleId"))
    if style_id is None:
        style_id = etree.SubElement(tbl_pr, qn("a:tableStyleId"))
    style_id.text = NO_STYLE

    rows = tbl.findall(qn("a:tr"))
    header = tbl_pr.get("firstRow") == "1" and rows and any(
        (t.text or "").strip() for t in rows[0].iter(qn("a:t")))
    for i, tr in enumerate(rows):
        is_head = header and i == 0
        body_index = i - 1 if header else i
        band = not is_head and body_index % 2 == 1
        for tc in tr.findall(qn("a:tc")):
            _style_cell(tc, HEAD_RULE if is_head else ROW_RULE, BAND_FILL if band else None)
            if is_head:
                _header_runs(tc, base)
    _rebalance(tbl)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: style_tables.py <file.pptx>", file=sys.stderr)
        return 2
    pptx = Path(sys.argv[1]).resolve()
    if not pptx.exists():
        print(f"error: {pptx} not found", file=sys.stderr)
        return 2

    prs = Presentation(str(pptx))
    styled = 0
    for slide in prs.slides:
        master = slide.slide_layout.slide_master._element
        other = master.find(".//" + qn("p:otherStyle") + "/" + qn("a:lvl1pPr") + "/" + qn("a:defRPr"))
        base = int(other.get("sz")) if other is not None and other.get("sz") else 1800
        for shape in slide.shapes:
            if getattr(shape, "has_table", False):
                style_table(shape.table._tbl, base)
                styled += 1
    prs.save(str(pptx))
    print(f"style_tables: styled {styled} table(s) → {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
