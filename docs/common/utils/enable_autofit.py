#!/usr/bin/env python3
"""Set every body-text placeholder in a pandoc-rendered pptx to "autofit on".

Pandoc emits `<a:bodyPr />` (empty) for body placeholders, which means
"no autofit, overflow." This script replaces empty bodyPr with one that
contains a bare `<a:normAutofit/>` — i.e. flips the "Shrink text on
overflow" dropdown to ON.

Note: PowerPoint computes the actual fontScale on edit, not on load.
For real shrink-to-fit at render time, follow this with the AppleScript
driver (autofit_powerpoint.applescript) which opens the file in
PowerPoint, touches each text frame to force scale recomputation, and
saves. Without that step, this script alone won't visibly shrink
overflowing text — it just primes the placeholder so a single click
inside the cell triggers the recompute.

Idempotent: any bodyPr that already contains an autofit child
(`normAutofit`, `spAutoFit`, `noAutofit`) is left alone."""

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

EMPTY_BODYPR = re.compile(rb"<a:bodyPr\s*/>")
NEW_BODYPR   = b"<a:bodyPr><a:normAutofit/></a:bodyPr>"


def patch_slide(xml: bytes) -> tuple[bytes, int]:
    return EMPTY_BODYPR.subn(NEW_BODYPR, xml)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: enable_autofit.py <file.pptx>", file=sys.stderr)
        return 2
    pptx = Path(sys.argv[1]).resolve()
    if not pptx.exists():
        print(f"error: {pptx} not found", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / pptx.name
        total = 0
        with zipfile.ZipFile(pptx, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
                    data, n = patch_slide(data)
                    total += n
                zout.writestr(info, data)
        shutil.move(tmp, pptx)
    print(f"enable_autofit: enabled normAutofit on {total} placeholder(s) → {pptx.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
