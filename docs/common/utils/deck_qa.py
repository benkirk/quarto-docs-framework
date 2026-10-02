#!/usr/bin/env python3
"""Check built decks for layout defects: `make qa`, or `deck_qa.py <deck>...` in a deck dir.

Reads the already-built <deck>.{html,pdf,pptx} and writes to _qa/:
  report.txt        everything below, per deck (also printed)
  usage.tsv         per HTML slide: kind, body use, fit, layout classes
  names.txt         plain-text names from qa-names.txt (one per line), if the file exists
  <deck>-html.png   contact sheet of every HTML slide; <deck>-pdf.png the same for the PDF
Failures (exit 1): slide counts that differ between formats, PDF text past the right margin,
into the footer band or overlapping other text, HTML content past the right edge, and a bare
`<word>` in the sources (revealjs reads it as a tag, and `<code>` swallows the slides after it).
Hints (never fail): short slides, `.smaller` without `.fill`, slides the HTML autofit shrank.
Needs poppler (pdftoppm, pdftotext) and Pillow; the HTML checks need Playwright for Python
(`python -m playwright install chromium`, or set CHROME to a Chromium binary) and are skipped
without it.
"""

import argparse
import functools
import glob
import html
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading
import zipfile

SHORT_USE = 0.65      # a text slide using less of its body than this is "short"
EDGE = 0.94           # beamerouterthemeNCAR.sty: text margin = 0.06 \paperwidth
COLS_EDGE = 0.97      # beamer columns overhang that margin, to ~0.96 W
TOL = 1.5             # pt of slack before a PDF word counts as past an edge

MEASURE_JS = r"""
(i) => {
  const s = Reveal.getSlides()[i];
  const h = s.querySelector(':scope > h2');
  if (!s.classList.contains('level2') || !h) return {level2: false};
  const cls = [...s.classList];
  const sr = s.getBoundingClientRect(), cs = getComputedStyle(s);
  const shift = parseFloat(s.style.getPropertyValue('--ncar-shift')) || 0;
  const fit = parseFloat(s.style.getPropertyValue('--ncar-fit')) || 1;
  const scale = parseFloat(s.getAttribute('data-ncar-scale')) || 1;
  const skip = 'h2, svg.ncar-waves, .ncar-footnotes, aside, style, script, .footer';
  const kids = [...s.children].filter(e => !e.matches(skip));
  let bot = 0, right = 0;
  for (const k of kids) for (const e of [k, ...k.querySelectorAll('*')]) {
    const r = e.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      bot = Math.max(bot, r.bottom - sr.top); right = Math.max(right, r.right - sr.left);
    }
  }
  const foot = s.querySelector(':scope > .ncar-footnotes');
  const floor = s.clientHeight - parseFloat(cs.paddingBottom);
  const limit = foot ? foot.getBoundingClientRect().top - sr.top : floor;
  const top = h.getBoundingClientRect().bottom - sr.top + 20;
  const has = sel => kids.some(k => k.matches(sel) || k.querySelector(sel));
  const kind = has('table') ? 'table' : has('pre') ? 'code'
    : has('img, svg, .cell-output-display') ? 'figure' : has('.columns') ? 'columns' : 'text';
  return {level2: true, title: h.textContent.trim(), cls: cls.join(' '), kind,
          columns: has('.columns'),
          use: Math.max(0, (bot - shift - top) / (limit - top)), fit, scale,
          overRight: right > sr.width - parseFloat(cs.paddingRight) + 16};  // inline-code padding overhangs
}
"""


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def contact_sheet(pngs, out, cols=4, width=480, gap=6):
    from PIL import Image, ImageDraw
    if not pngs:
        return
    thumbs = []
    for p in pngs:
        im = Image.open(p).convert("RGB")
        thumbs.append(im.resize((width, round(im.height * width / im.width))))
    h = max(t.height for t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (width + gap) + gap, rows * (h + gap) + gap), "#888888")
    draw = ImageDraw.Draw(sheet)
    for n, t in enumerate(thumbs):
        x, y = gap + (n % cols) * (width + gap), gap + (n // cols) * (h + gap)
        sheet.paste(t, (x, y))
        draw.rectangle((x, y, x + 26, y + 14), fill="#000000")
        draw.text((x + 3, y + 2), str(n + 1), fill="#FFFFFF")
    sheet.save(out)


# --------------------------------------------------------------------------- PDF

BOX = r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)"'
WORD = re.compile(r'<word %s>(.*?)</word>' % BOX)
LINE = re.compile(r'<line %s>(.*?)</line>' % BOX, re.S)
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">')


def boxes(pattern, text):
    return [(float(a), float(b), float(c), float(d), t) for a, b, c, d, t in pattern.findall(text)]


def pdf_pages(pdf):
    """[(width, height, words, lines)] per page, each a list of (x0, y0, x1, y1, text)."""
    xml = run(["pdftotext", "-bbox-layout", pdf, "-"])
    pages = []
    for chunk in xml.split("<page ")[1:]:
        w, h = map(float, PAGE.match("<page " + chunk).groups())
        words = [b[:4] + (html.unescape(b[4]),) for b in boxes(WORD, chunk)]
        lines = [b[:4] + (" ".join(wd[4] for wd in boxes(WORD, b[4])),) for b in boxes(LINE, chunk)]
        pages.append((w, h, words, lines))
    return pages


def frame_number(w, h, words):
    """The frame-number word at the bottom left, or None (title, section, closing pages)."""
    num = [wd for wd in words if wd[4].isdigit() and wd[0] < w * 0.1 and wd[1] > h * 0.85]
    return num[0] if num else None


def frames(pages):
    """Each page's frame index: beamer overlays (incremental lists) repeat a frame's number."""
    idx, prev, out = -1, None, []
    for w, h, words, _ in pages:
        n = frame_number(w, h, words)
        num = n[4] if n else None
        if num is None or num != prev:
            idx += 1
        prev = num
        out.append(idx)
    return out


def table_overruns(lines, w, h):
    """Lines crossing a column edge, where an edge is an x that three or more lines start at.

    pdftotext keeps each table cell a line of its own, and merges two touching cells into one,
    so a cell that overruns its column is a line spanning the next column's edge."""
    body = [ln for ln in lines if ln[1] > h * 0.16]          # below the frame title
    starts = {}
    for ln in body:
        starts.setdefault(round(ln[0]), []).append(ln)
    out = []
    for a in body:
        for x, col in starts.items():
            if len(col) < 3 or not a[0] + 5 < x < a[2] - 1:
                continue
            near = [b for b in col if abs(b[1] - a[1]) < 3 * (a[3] - a[1])]
            # a right-aligned column: shorter numbers start further right, same right edge
            if near and not all(abs(b[2] - a[2]) < 1 for b in near):
                out.append(("runs into the next table column", repr(a[4])))
                break
    return out


def pdf_problems(w, h, words, lines, slide=None):
    """Text past the right margin, into the footer, overlapping, or across a table column.

    `slide` is the HTML measurement of the same slide, when the slide counts agree: it says
    whether the page has columns (a wider right edge) or is a table (column checks)."""
    out = []
    edge = w * (COLS_EDGE if slide is None or slide.get("columns") else EDGE) + TOL
    for x0, y0, x1, y1, t in words:
        if x1 > edge:
            out.append(("past the right margin", repr(t)))
    # the frame number (bottom left) marks the footline; small words beside it are the
    # linked-image URL line, which belongs there
    n = frame_number(w, h, words)
    if n:
        for wd in words:
            if wd is n or wd[3] <= n[1] + TOL or (wd[1] >= n[1] - 1 and wd[3] - wd[1] < 8.5):
                continue
            if wd[0] < n[2] + 6 or wd[3] > n[3] + TOL:   # meets the number, or below the footline
                out.append(("into the footer", repr(wd[4])))
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            vo = min(a[3], b[3]) - max(a[1], b[1])
            ho = min(a[2], b[2]) - max(a[0], b[0])
            if ho > 1.0 and vo > 0.5 * min(a[3] - a[1], b[3] - b[1]):
                out.append(("overlapping text", "%r/%r" % (a[4], b[4])))
    if slide and slide.get("kind") == "table":
        out += table_overruns(lines, w, h)
    return out


def check_pdf(deck, qa, slides):
    pdf = deck + ".pdf"
    if not os.path.exists(pdf):
        return None, ["no %s; run make pdf" % pdf]
    pages = pdf_pages(pdf)
    index = frames(pages)
    nframes = index[-1] + 1 if index else 0
    lines = []
    for n, ((w, h, words, text_lines), f) in enumerate(zip(pages, index), 1):
        slide = slides[f] if len(slides) == nframes else None
        meta = slide if slide and slide.get("level2") else None
        found = {}
        for kind, detail in pdf_problems(w, h, words, text_lines, meta):
            found.setdefault(kind, []).append(detail)
        for kind, details in found.items():
            more = " (+%d more)" % (len(details) - 3) if len(details) > 3 else ""
            lines.append("p%d [s%d]: %s: %s%s" % (n, f + 1, kind, ", ".join(details[:3]), more))
    if shutil.which("pdftoppm"):
        d = os.path.join(qa, deck, "pdf")
        os.makedirs(d, exist_ok=True)
        for old in glob.glob(os.path.join(d, "*.png")):
            os.remove(old)
        run(["pdftoppm", "-r", "80", "-png", pdf, os.path.join(d, "p")])
        contact_sheet(sorted(glob.glob(os.path.join(d, "*.png"))),
                      os.path.join(qa, deck + "-pdf.png"))
    return nframes, lines


# -------------------------------------------------------------------------- HTML

def serve(directory):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=directory)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def check_html(decks, qa):
    """{deck: (count, [slide dicts])}, or a string saying why the HTML checks were skipped."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Playwright for Python is not installed"
    httpd = serve(os.getcwd())
    base = "http://127.0.0.1:%d/" % httpd.server_address[1]
    results = {}
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
            except Exception as e:  # noqa: BLE001 -- any launch failure means "skip"
                return "no browser (%s); run `python -m playwright install chromium` or set " \
                       "CHROME" % str(e).splitlines()[0]
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            for deck in decks:
                if not os.path.exists(deck + ".html"):
                    continue
                d = os.path.join(qa, deck, "html")
                os.makedirs(d, exist_ok=True)
                for old in glob.glob(os.path.join(d, "*.png")):
                    os.remove(old)
                page.goto(base + deck + ".html")
                page.wait_for_function("window.Reveal && Reveal.isReady()")
                page.evaluate("document.fonts.ready.then(() => true)")
                page.evaluate("Reveal.configure({transition: 'none', backgroundTransition: 'none'})")
                n = page.evaluate("Reveal.getTotalSlides()")
                slides = []
                for i in range(n):
                    # `##` slides nest under their `#` divider: Reveal.slide(i) would stay on it
                    page.evaluate("i => { const ix = Reveal.getIndices(Reveal.getSlides()[i]);"
                                  " Reveal.slide(ix.h, ix.v); }", i)
                    page.wait_for_timeout(400)
                    page.screenshot(path=os.path.join(d, "s%03d.png" % (i + 1)))
                    slides.append(page.evaluate(MEASURE_JS, i))
                contact_sheet(sorted(glob.glob(os.path.join(d, "*.png"))),
                              os.path.join(qa, deck + "-html.png"))
                results[deck] = (n, slides)
            browser.close()
    finally:
        httpd.shutdown()
    return results


def html_findings(slides):
    fails, hints = [], []
    for n, s in enumerate(slides, 1):
        if not s.get("level2"):
            continue
        cls = s["cls"].split()
        tag = 's%d "%s"' % (n, s["title"])
        if s["overRight"]:
            fails.append("%s: content past the right edge" % tag)
        if "smaller" in cls and "ncar-fill" not in cls:
            hints.append("%s: .smaller without .fill shrinks the HTML text; drop it, or add "
                         ".fill with a PDF scale=" % tag)
        floor = 1.0 if "ncar-fill" in cls else s["scale"]
        if s["fit"] < floor - 0.05:
            hints.append("%s: HTML autofit shrank it to %.2f; the PDF (no autofit) may "
                         "overflow" % (tag, s["fit"]))
        special = {"ncar-layout", "feature", "closing", "brand-dark"}
        if s["kind"] in ("text", "columns") and s["use"] <= SHORT_USE and not special & set(cls):
            hints.append('%s: short (%s, uses %.0f%% of the body); try {.vcenter scale="1.15"}'
                         % (tag, s["kind"], 100 * s["use"]))
    return fails, hints


# ------------------------------------------------------------------- pptx, names

def pptx_count(deck):
    path = deck + ".pptx"
    if not os.path.exists(path):
        return None
    with zipfile.ZipFile(path) as z:
        return sum(1 for f in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", f))


def plain_names(names):
    """file:line hits of each listed name outside code, notes, link targets and attributes."""
    pat = re.compile(r"(?<![\w/.`-])(%s)(?![\w`-])" % "|".join(map(re.escape, names)))
    hits = []
    for f in sorted(glob.glob("*.qmd")):
        fence = notes = False
        for n, line in enumerate(open(f, encoding="utf-8"), 1):
            s = line.strip()
            if s.startswith("```"):
                fence = not fence
                continue
            if s.startswith("::: {.notes"):
                notes = True
            if fence or notes:
                notes = notes and s != ":::"
                continue
            prose = re.sub(r"`[^`]*`|\]\([^)]*\)|\{[^}]*\}|https?://\S+", "", line)
            hits += ["%s:%d: %s" % (f, n, m.group(1)) for m in pat.finditer(prose)]
    return hits


# ------------------------------------------------------------------- sources

INCLUDE = re.compile(r"\{\{<\s*include\s+(\S+)\s*>\}\}")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
CODE_SPAN = re.compile(r"(`+).+?\1")
BARE_TAG = re.compile(r"</?[a-z_]+>")


def deck_sources(deck):
    """<deck>.qmd and every file it includes, recursively, in reading order."""
    seen, order = set(), []

    def visit(path):
        if path in seen or not os.path.exists(path):
            return
        seen.add(path)
        order.append(path)
        for line in open(path, encoding="utf-8"):
            for inc in INCLUDE.findall(line):
                visit(os.path.normpath(os.path.join(os.path.dirname(path), inc)))
    visit(deck + ".qmd")
    return order


def bare_tags(path):
    """file:line hits of `<word>` outside code fences, code spans and raw-HTML lines."""
    hits, fence, front = [], None, False
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if n == 1 and line.strip() == "---":
            front = True
            continue
        if front:
            front = line.strip() not in ("---", "...")
            continue
        m = FENCE.match(line)
        if m and (fence is None or m.group(1).startswith(fence)):
            fence = m.group(1) if fence is None else None
            continue
        if fence or line.lstrip().startswith("<"):
            continue
        for tag in BARE_TAG.findall(CODE_SPAN.sub("", line)):
            hits.append("%s:%d: bare %s; put it in backticks" % (path, n, tag))
    return hits


# -------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("decks", nargs="+")
    ap.add_argument("--out", default="_qa")
    args = ap.parse_args()
    qa = args.out
    os.makedirs(qa, exist_ok=True)

    html_res = check_html(args.decks, qa)
    report, usage, failed = [], ["deck\tslide\tkind\tuse\tfit\ttitle\tclasses"], False
    if isinstance(html_res, str):
        report.append("HTML checks skipped: " + html_res)
        html_res = {}
    for deck in args.decks:
        report.append("== %s ==" % deck)
        # an included .yml or .py is shown inside a code fence, not read as markdown
        tags = [h for f in deck_sources(deck) if f.endswith((".qmd", ".md"))
                for h in bare_tags(f)]
        failed |= bool(tags)
        report += ["source " + h for h in tags]
        html_n, slides = html_res.get(deck, (None, []))
        pdf_n, pdf_lines = check_pdf(deck, qa, slides)
        counts = {"pptx": pptx_count(deck), "pdf": pdf_n, "html": html_n}
        known = {k: v for k, v in counts.items() if v is not None}
        same = len(set(known.values())) <= 1
        failed |= not same
        report.append("slides: %s%s" % (", ".join("%s %d" % kv for kv in known.items()),
                                        "" if same else "  MISMATCH"))
        titles = {n: s.get("title", "") for n, s in enumerate(slides, 1)} if same else {}
        for line in pdf_lines:
            m = re.match(r"p\d+ \[s(\d+)\]", line)
            title = titles.get(int(m.group(1))) if m else None
            report.append("PDF %s%s" % (line, ' ("%s")' % title if title else ""))
        failed |= any(line.startswith("p") for line in pdf_lines)
        fails, hints = html_findings(slides)
        failed |= bool(fails)
        report += ["HTML " + f for f in fails] + ["hint " + h for h in hints]
        for n, s in enumerate(slides, 1):
            if s.get("level2"):
                usage.append("%s\t%d\t%s\t%.2f\t%.2f\t%s\t%s"
                             % (deck, n, s["kind"], s["use"], s["fit"], s["title"], s["cls"]))
    if os.path.exists("qa-names.txt"):
        names = [n.strip() for n in open("qa-names.txt", encoding="utf-8")
                 if n.strip() and not n.lstrip().startswith("#")]
        hits = plain_names(names) if names else []
        with open(os.path.join(qa, "names.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(hits) + "\n")
        report.append("== names ==\n%d plain-text uses of qa-names.txt names (see %s/names.txt)"
                      % (len(hits), qa))
    with open(os.path.join(qa, "usage.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(usage) + "\n")
    with open(os.path.join(qa, "report.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\n%s; contact sheets and per-slide PNGs in %s/" % ("FAILED" if failed else "ok", qa))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
