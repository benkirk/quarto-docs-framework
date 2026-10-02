#!/usr/bin/env python3
"""Rebuild the "Section Header" layout of template.pptx as the brand divider.

The HTML and PDF decks draw every `#` divider on the brand field: NCAR Blue,
the white logo top left, and the brand's waves in Light Blue with translucent
bands between them (ncar-revealjs.lua, beamerouterthemeNCAR.sty). This writes
the same into the template's Section Header layout, which pandoc uses for `#`:

  * background `tx2` (dk2, NCAR Blue), master art hidden (showMasterSp="0")
  * the white NSF NCAR logo, top left, from the vendored theme's assets
  * the three wave lines and two bands, as vector shapes in `accent1`
  * a white title (Poppins Bold 44pt) and subtitle (18pt), slide number

Colors are theme slots, so a UCAR template with its own theme recolors it.
section_subtitle.py adds the per-slide parts: "SECTION n", the orange tab,
and the vertical placement of the title block.

Run from anywhere; rewrites template.pptx in place, and a second run produces
the same layout:

    python3 docs/common/branding/ncar/build_divider_layout.py
"""

import posixpath
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.pptx"
LOGO = (HERE.parent.parent / "_extensions/benkirk/ncar/ncar-assets/web"
        / "NSF-NCAR_Logo_Color-White_RGB.png")
# pandoc keeps only the template's media named ppt/media/image*
LOGO_PART = "ppt/media/image-divider-logo.png"

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

LAYOUT_NAME = "Section Header"

# The revealjs theme lays slides out at 1600x900 px; the pptx is 12192000 x
# 6858000 EMU, so 1 px = 7620 EMU and 1 px of type = 0.6 pt.
PX = 7620
W, H = 1600, 900
MARGIN = 96                      # $ncar-margin
LOGO_TOP, LOGO_H = 72, 58        # section dividers set the logo at top: 72px
LOGO_W = round(LOGO_H * 1200 / 313)
TITLE_Y, TITLE_W, TITLE_PT = 400, 0.62 * W, 44     # h1: 2.6em of 28px, 62% wide
BODY_Y, BODY_W, BODY_PT = 520, 0.60 * W, 18        # .ncar-subtitle: 1.1em, 60%

# The brand's three wave lines (ncar-revealjs.lua WAVES, from tools/fit-waves.py
# in the beamer theme): two cubics each, top edge to bottom edge, as {x, y}
# fractions of the slide: start, ctrl, ctrl, peak, ctrl, ctrl, end.
WAVES = [
    [(0.4862, 0.0000), (0.5087, 0.1976), (0.6068, 0.4965), (0.6068, 0.6766),
     (0.6068, 0.8741), (0.5756, 0.9681), (0.5674, 1.0000)],
    [(0.5138, 0.0000), (0.5402, 0.1583), (0.6570, 0.4747), (0.6570, 0.6423),
     (0.6570, 0.8307), (0.6286, 0.9166), (0.6000, 1.0000)],
    [(0.5427, 0.0000), (0.5762, 0.1381), (0.7073, 0.4410), (0.7073, 0.6182),
     (0.7073, 0.8242), (0.6639, 0.9245), (0.6320, 1.0000)],
]
SHIFT = 0.26                     # SHIFT.section
LINE_PX = 2.4                    # stroke-width
BANDS = [(0, 1, 18000), (1, 2, 10000)]   # line k to line m, alpha (1/1000 %)
PATH_W, PATH_H = 16000, 9000     # path units: 0.1 px


def _pt(k, i):
    x, y = WAVES[k][i]
    return round((x + SHIFT) * PATH_W), round(y * PATH_H)


def _cubics(k, order):
    """`a:cubicBezTo` elements along line k, visiting its points in `order`."""
    out = []
    for j in range(1, len(order), 3):
        pts = "".join('<a:pt x="%d" y="%d"/>' % _pt(k, i) for i in order[j:j + 3])
        out.append("<a:cubicBezTo>%s</a:cubicBezTo>" % pts)
    return "".join(out)


def _geom(path):
    return ('<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>'
            '<a:rect l="0" t="0" r="r" b="b"/><a:pathLst>%s</a:pathLst></a:custGeom>'
            % path)


def _shape(sid, name, geom, fill, line):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr/>'
            f'<p:nvPr userDrawn="1"/></p:nvSpPr><p:spPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{W * PX}" cy="{H * PX}"/></a:xfrm>'
            f'{geom}{fill}{line}</p:spPr></p:sp>')


def wave_shapes(first_id):
    fwd, back = list(range(7)), list(range(6, -1, -1))
    shapes, sid = [], first_id
    for k, m, alpha in BANDS:
        x1, y1 = _pt(k, 0)
        x2, y2 = _pt(m, 6)
        path = (f'<a:path w="{PATH_W}" h="{PATH_H}" stroke="0">'
                f'<a:moveTo><a:pt x="{x1}" y="{y1}"/></a:moveTo>{_cubics(k, fwd)}'
                f'<a:lnTo><a:pt x="{x2}" y="{y2}"/></a:lnTo>{_cubics(m, back)}'
                f'<a:close/></a:path>')
        fill = (f'<a:solidFill><a:schemeClr val="accent1"><a:alpha val="{alpha}"/>'
                f'</a:schemeClr></a:solidFill>')
        shapes.append(_shape(sid, f"Wave band {k + 1}", _geom(path), fill, "<a:ln><a:noFill/></a:ln>"))
        sid += 1
    for k in range(3):
        x1, y1 = _pt(k, 0)
        path = (f'<a:path w="{PATH_W}" h="{PATH_H}" fill="none">'
                f'<a:moveTo><a:pt x="{x1}" y="{y1}"/></a:moveTo>{_cubics(k, fwd)}</a:path>')
        line = (f'<a:ln w="{round(LINE_PX * PX)}"><a:solidFill><a:schemeClr val="accent1"/>'
                f'</a:solidFill></a:ln>')
        shapes.append(_shape(sid, f"Wave line {k + 1}", _geom(path), "<a:noFill/>", line))
        sid += 1
    return shapes


def _xfrm(x, y, w, h):
    return (f'<a:xfrm><a:off x="{round(x * PX)}" y="{round(y * PX)}"/>'
            f'<a:ext cx="{round(w * PX)}" cy="{round(h * PX)}"/></a:xfrm>')


WHITE = '<a:solidFill><a:schemeClr val="bg1"/></a:solidFill>'
NO_INSET = 'lIns="0" tIns="0" rIns="0" bIns="0"'


def layout_xml():
    title = (
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/>'
        '</p:cNvSpPr><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
        f'<p:spPr>{_xfrm(MARGIN, TITLE_Y, TITLE_W, 110)}<a:prstGeom prst="rect"><a:avLst/>'
        f'</a:prstGeom></p:spPr><p:txBody><a:bodyPr {NO_INSET} anchor="t"><a:normAutofit/></a:bodyPr>'
        '<a:lstStyle><a:lvl1pPr algn="l"><a:lnSpc><a:spcPct val="90000"/></a:lnSpc>'
        f'<a:defRPr sz="{TITLE_PT * 100}" b="1" cap="none" baseline="0">{WHITE}'
        '<a:latin typeface="+mj-lt"/></a:defRPr></a:lvl1pPr></a:lstStyle>'
        '<a:p><a:r><a:rPr lang="en-US"/><a:t>Section title</a:t></a:r></a:p></p:txBody></p:sp>')
    body = (
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Text Placeholder 2"/><p:cNvSpPr>'
        '<a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
        f'<p:spPr>{_xfrm(MARGIN, BODY_Y, BODY_W, 120)}<a:prstGeom prst="rect"><a:avLst/>'
        f'</a:prstGeom></p:spPr><p:txBody><a:bodyPr {NO_INSET} anchor="t"><a:normAutofit/></a:bodyPr>'
        '<a:lstStyle><a:lvl1pPr marL="0" indent="0"><a:spcBef><a:spcPts val="0"/></a:spcBef>'
        f'<a:buNone/><a:defRPr sz="{BODY_PT * 100}" b="0">{WHITE}</a:defRPr></a:lvl1pPr></a:lstStyle>'
        '<a:p><a:r><a:rPr lang="en-US"/><a:t>Subtitle</a:t></a:r></a:p></p:txBody></p:sp>')
    logo = (
        '<p:pic><p:nvPicPr><p:cNvPr id="4" name="NSF NCAR logo" descr="NSF NCAR"/>'
        '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr userDrawn="1"/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId2"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr>{_xfrm(MARGIN, LOGO_TOP, LOGO_W, LOGO_H)}<a:prstGeom prst="rect"><a:avLst/>'
        '</a:prstGeom></p:spPr></p:pic>')
    # the revealjs slide number sits at the bottom left, 12pt, in the text color
    slide_num = (
        '<p:sp><p:nvSpPr><p:cNvPr id="5" name="Slide Number"/><p:cNvSpPr txBox="1"/>'
        '<p:nvPr userDrawn="1"/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="13014" y="6481724"/><a:ext cx="477640" cy="365125"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr anchor="ctr"/><a:lstStyle/><a:p><a:pPr algn="ctr"/>'
        '<a:fld id="{C5EF2332-01BF-834F-8236-50238282D533}" type="slidenum">'
        f'<a:rPr lang="en-US" sz="1200">{WHITE}<a:latin typeface="+mn-lt"/></a:rPr>'
        '<a:t>‹#›</a:t></a:fld></a:p></p:txBody></p:sp>')
    shapes = wave_shapes(6) + [logo, title, body, slide_num]
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<p:sldLayout xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}" type="secHead" '
        'preserve="1" showMasterSp="0">'
        f'<p:cSld name="{LAYOUT_NAME}">'
        '<p:bg><p:bgPr><a:solidFill><a:schemeClr val="tx2"/></a:solidFill><a:effectLst/>'
        '</p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/>'
        '<p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        + "".join(shapes) +
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
    ).encode("utf-8")


def rels_xml(master_target):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<Relationships xmlns="{PR}">'
        f'<Relationship Id="rId1" Type="{REL}/slideMaster" Target="{master_target}"/>'
        f'<Relationship Id="rId2" Type="{REL}/image" '
        f'Target="../media/{posixpath.basename(LOGO_PART)}"/></Relationships>'
    ).encode("utf-8")


def find_layout(parts):
    for name, data in parts.items():
        if name.startswith("ppt/slideLayouts/slideLayout") and name.endswith(".xml"):
            csld = etree.fromstring(data).find("{%s}cSld" % P)
            if csld is not None and csld.get("name") == LAYOUT_NAME:
                return name
    sys.exit(f"build_divider_layout: no layout named {LAYOUT_NAME!r} in {TEMPLATE}")


def main():
    with zipfile.ZipFile(TEMPLATE) as zin:
        infos = zin.infolist()
        parts = {i.filename: zin.read(i.filename) for i in infos}

    layout = find_layout(parts)
    rels_name = posixpath.join(posixpath.dirname(layout), "_rels",
                               posixpath.basename(layout) + ".rels")
    master = next(r.get("Target") for r in etree.fromstring(parts[rels_name])
                  if r.get("Type").endswith("/slideMaster"))
    parts[layout] = layout_xml()
    parts[rels_name] = rels_xml(master)
    parts[LOGO_PART] = LOGO.read_bytes()

    names = [i.filename for i in infos]
    if LOGO_PART not in names:
        names.append(LOGO_PART)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / TEMPLATE.name
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                # fixed timestamps, so an unchanged rebuild is byte-identical
                zout.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), parts[name],
                              zipfile.ZIP_DEFLATED)
        shutil.move(str(tmp), str(TEMPLATE))
    print(f"build_divider_layout: rebuilt {layout} ({LAYOUT_NAME}) → {TEMPLATE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
