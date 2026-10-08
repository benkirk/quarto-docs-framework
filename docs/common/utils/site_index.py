#!/usr/bin/env python3
"""Write <site>/index.html listing the decks: `make site`, or `site_index.py --out _site <deck>...`.

Each deck's title and subtitle come from <deck>.qmd's front matter, in the order given;
the first deck names the page. `--extra DIR` (repeatable) adds every DIR/*.html under
the site, titled by its <title>; `--noindex` adds the robots meta tag. Brand colors and
Poppins as in the revealjs theme.
"""

import argparse
import datetime
import html
import pathlib
import re
import sys

import yaml

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap">
<style>
:root {{
  --bg: #F1F0EE; --surface: #FFFFFF; --ink: #00357A; --text: #1F2A3C; --muted: #6B7C99;
  --line: #D9DBE0; --brand: #0057C2; --accent: #FAA119;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #011837; --surface: #0A2246; --ink: #E3EAF4; --text: #D5DEEA; --muted: #9AABC2;
    --line: #22395E; --brand: #42C0FF; color-scheme: dark;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--text);
  font-family: Poppins, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.5;
  padding: 40px 16px 56px;
}}
main {{ max-width: 760px; margin: 0 auto; }}
header {{ border-left: 6px solid var(--accent); padding-left: 18px; margin-bottom: 32px; }}
h1 {{ margin: 0; color: var(--ink); font-size: clamp(26px, 4vw, 36px); line-height: 1.15; font-weight: 700; }}
.sub {{ margin: 6px 0 0; color: var(--muted); font-size: 18px; }}
h2 {{ color: var(--ink); font-size: 14px; letter-spacing: .08em; text-transform: uppercase; margin: 32px 0 10px; }}
ol, ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }}
a.card {{
  display: grid; grid-template-columns: 3.2em 1fr; align-items: baseline; gap: 12px;
  background: var(--surface); border: 1px solid var(--line); padding: 12px 16px;
  color: inherit; text-decoration: none;
}}
a.card:hover, a.card:focus-visible {{ border-color: var(--brand); outline: none; }}
a.card .n {{ color: var(--brand); font-weight: 600; font-variant-numeric: tabular-nums; }}
a.card .t {{ color: var(--ink); font-weight: 600; }}
a.card .s {{ color: var(--muted); display: block; font-size: 14px; }}
footer {{ margin-top: 40px; color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<main>
<header>
<h1>{title}</h1>
{subtitle}
</header>
<h2>Decks</h2>
<ol>
{decks}
</ol>
{extras}
<footer>Built {date}. Open a deck, then press <kbd>?</kbd> for the keyboard controls.</footer>
</main>
</body>
</html>
"""


def front_matter(qmd):
    text = qmd.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = yaml.safe_load(m.group(1)) if m else {}
    return meta if isinstance(meta, dict) else {}


def card(href, number, title, subtitle):
    sub = f'<span class="s">{html.escape(subtitle)}</span>' if subtitle else ""
    return (f'<li><a class="card" href="{html.escape(href)}"><span class="n">{number}</span>'
            f'<span><span class="t">{html.escape(title)}</span>{sub}</span></a></li>')


def page_title(path):
    m = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8", errors="replace"), re.S)
    return html.unescape(m.group(1).strip()) if m else path.stem


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=pathlib.Path, help="site directory")
    ap.add_argument("--extra", action="append", default=[], help="directory of extra pages")
    ap.add_argument("--title", help="page title (default: the first deck's)")
    ap.add_argument("--noindex", action="store_true", help="ask search engines not to index")
    ap.add_argument("decks", nargs="+", help="deck names, each with a <deck>.qmd")
    args = ap.parse_args()

    decks = [(d, front_matter(pathlib.Path(f"{d}.qmd"))) for d in args.decks]
    first = decks[0][1]
    title = args.title or str(first.get("title") or args.decks[0])
    subtitle = "" if args.title else str(first.get("subtitle") or "")

    cards = [card(f"{d}.html", i, str(meta.get("title") or d), str(meta.get("subtitle") or ""))
             for i, (d, meta) in enumerate(decks, 1)]

    extras = []
    for d in args.extra:
        pages = sorted((args.out / d).glob("*.html"))
        if not pages:
            print(f"site_index: no pages under {args.out / d}", file=sys.stderr)
        extras += [card(f"{d}/{p.name}", "", page_title(p), "") for p in pages]
    extra_block = f"<h2>Companion pages</h2>\n<ul>\n{chr(10).join(extras)}\n</ul>" if extras else ""

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(PAGE.format(
        robots='<meta name="robots" content="noindex">\n' if args.noindex else "",
        title=html.escape(title),
        subtitle=f'<p class="sub">{html.escape(subtitle)}</p>' if subtitle else "",
        decks="\n".join(cards),
        extras=extra_block,
        date=datetime.date.today().strftime("%B %-d, %Y"),
    ), encoding="utf-8")
    print(f"wrote {args.out / 'index.html'}: {len(decks)} decks, {len(extras)} extra pages")


if __name__ == "__main__":
    main()
