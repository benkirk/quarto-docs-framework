#!/usr/bin/env python3
"""Merge a section-divider slide's orphaned subtitle back onto the same slide.

pandoc's pptx writer renders a heading above slide-level (a `#` when
`slide-level: 2`) as a title-only "Section Header" slide, and drops any markdown
that follows it — before the next slide-level heading — onto a SEPARATE,
untitled "Title and Content" slide. The NCAR template's Section Header layout
has a body/subtitle placeholder (idx=1) that pandoc never fills, so the two
render as two slides instead of one.

This closes that gap. For every Section Header slide immediately followed by
such an orphan (no title text, but body text), it moves the orphan's body into
the Section Header slide's subtitle placeholder and deletes the orphan, so:

    # Job Sort

    Prioritizing job execution — one subtitle line.

    ## The End Goal
    ...

renders as a single divider slide carrying the subtitle. Authoring stays
ordinary markdown — no raw OpenXML, no per-slide attributes.

Raw-zip surgery via lxml (no python-pptx), so it composes with the other
post-render utilities. **Run it FIRST in the pptx recipe**, before
embed_poppins.py rewrites presentation.xml with embedded fonts.

Idempotent: a Section Header already carrying body text, or one followed by a
normal titled slide, is left alone (a second run is a no-op)."""

import copy
import posixpath
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"p": P, "a": A, "r": R}

SECTION_LAYOUT = "Section Header"
TITLE_PH = {"title", "ctrTitle"}
CHROME_PH = {"dt", "ftr", "sldNum"}  # date, footer, slide number — ignore


def _resolve(base_dir, target):
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, target))


def _parse(data):
    return etree.fromstring(data)


def _serialize(root):
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _rels_for(parts, part_name):
    """(rels_part_name, [(Id, Type, resolved_target), ...]) for a part."""
    d = posixpath.dirname(part_name)
    rels_name = posixpath.join(d, "_rels", posixpath.basename(part_name) + ".rels")
    if rels_name not in parts:
        return rels_name, []
    root = _parse(parts[rels_name])
    rels = [(rel.get("Id"), rel.get("Type"), _resolve(d, rel.get("Target")))
            for rel in root.findall("{%s}Relationship" % PR)]
    return rels_name, rels


def _layout_name(parts, slide_part):
    for _id, typ, tgt in _rels_for(parts, slide_part)[1]:
        if typ.endswith("/slideLayout"):
            csld = _parse(parts[tgt]).find("{%s}cSld" % P)
            return csld.get("name") if csld is not None else None
    return None


def _classify(root):
    """(has_title, has_body, first_body_sp) for a slide's shape tree."""
    tree = root.find("p:cSld/p:spTree", NS)
    has_title = has_body = False
    body_sp = None
    for sp in tree.findall("p:sp", NS):
        ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if ph is None:
            continue
        typ = ph.get("type") or "body"
        text = "".join(t.text or "" for t in sp.findall(".//a:t", NS)).strip()
        if not text:
            continue
        if typ in TITLE_PH:
            has_title = True
        elif typ not in CHROME_PH:
            has_body = True
            if body_sp is None:
                body_sp = sp
    return has_title, has_body, body_sp


def _merge_into(section_root, body_sp):
    """Append body_sp (a copy) to the section slide as its idx=1 subtitle."""
    tree = section_root.find("p:cSld/p:spTree", NS)
    sp = copy.deepcopy(body_sp)
    # inherit the Section Header layout's subtitle geometry, not the orphan's
    sp_pr = sp.find("p:spPr", NS)
    if sp_pr is not None:
        xfrm = sp_pr.find("a:xfrm", NS)
        if xfrm is not None:
            sp_pr.remove(xfrm)
    ph = sp.find("p:nvSpPr/p:nvPr/p:ph", NS)
    ph.set("type", "body")
    ph.set("idx", "1")
    # keep the shape id unique within the destination slide
    ids = {int(e.get("id")) for e in tree.iter("{%s}cNvPr" % P)
           if (e.get("id") or "").isdigit()}
    sp.find("p:nvSpPr/p:cNvPr", NS).set("id", str((max(ids) + 1) if ids else 2))
    tree.append(sp)


def main():
    if len(sys.argv) != 2:
        print("usage: section_subtitle.py <file.pptx>", file=sys.stderr)
        return 2
    pptx = Path(sys.argv[1]).resolve()
    if not pptx.exists():
        print(f"error: {pptx} not found", file=sys.stderr)
        return 2

    with zipfile.ZipFile(pptx, "r") as zin:
        parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}

    pres = _parse(parts["ppt/presentation.xml"])
    sld_id_lst = pres.find("p:sldIdLst", NS)
    presrels_name, presrels = _rels_for(parts, "ppt/presentation.xml")
    relmap = {rid: tgt for rid, _typ, tgt in presrels}

    ordered = [(el, el.get("{%s}id" % R), relmap[el.get("{%s}id" % R)])
               for el in sld_id_lst.findall("p:sldId", NS)]

    info = {}
    for _el, _rid, part in ordered:
        root = _parse(parts[part])
        has_title, has_body, body_sp = _classify(root)
        info[part] = dict(root=root, has_title=has_title, has_body=has_body,
                          body_sp=body_sp, layout=_layout_name(parts, part))

    merged, orphans = [], []
    for i in range(len(ordered) - 1):
        _s_el, _s_rid, s_part = ordered[i]
        o_el, o_rid, o_part = ordered[i + 1]
        s, o = info[s_part], info[o_part]
        if (s["layout"] == SECTION_LAYOUT and s["has_title"] and not s["has_body"]
                and not o["has_title"] and o["has_body"]):
            _merge_into(s["root"], o["body_sp"])
            merged.append(s_part)
            orphans.append((o_el, o_rid, o_part))

    if not merged:
        print("section_subtitle: no section-header subtitles to merge")
        return 0

    # Delete each orphan slide and everything that belongs only to it.
    delete_names = set()
    del_rids = {rid for _el, rid, _p in orphans}
    for o_el, _o_rid, o_part in orphans:
        sld_id_lst.remove(o_el)
        rels_name, rels = _rels_for(parts, o_part)
        delete_names.update({o_part, rels_name})
        for _id, typ, tgt in rels:
            if typ.endswith("/notesSlide"):
                delete_names.update({tgt, _rels_for(parts, tgt)[0]})

    presrels_root = _parse(parts[presrels_name])
    for rel in presrels_root.findall("{%s}Relationship" % PR):
        if rel.get("Id") in del_rids:
            presrels_root.remove(rel)

    ct_root = _parse(parts["[Content_Types].xml"])
    del_partnames = {"/" + n for n in delete_names if n.endswith(".xml")}
    for ov in ct_root.findall("{%s}Override" % CT):
        if ov.get("PartName") in del_partnames:
            ct_root.remove(ov)

    modified = {
        "ppt/presentation.xml": _serialize(pres),
        presrels_name: _serialize(presrels_root),
        "[Content_Types].xml": _serialize(ct_root),
    }
    for s_part in merged:
        modified[s_part] = _serialize(info[s_part]["root"])

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / pptx.name
        with zipfile.ZipFile(pptx, "r") as zin, \
                zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for i in zin.infolist():
                if i.filename in delete_names:
                    continue
                zout.writestr(i, modified.get(i.filename, zin.read(i.filename)))
        shutil.move(str(tmp), str(pptx))

    print(f"section_subtitle: merged {len(merged)} subtitle(s), "
          f"removed {len(orphans)} orphan slide(s) → {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
