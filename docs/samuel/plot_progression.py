"""Draw images/loc_progression.png from data/loc_progression.tsv (refresh time only)."""
import csv
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

HERE = Path(__file__).parent
FONTS = HERE.parent / "common/_extensions/benkirk/ncar/ncar-assets/fonts/Poppins"
for ttf in FONTS.glob("*.ttf"):
    font_manager.fontManager.addfont(str(ttf))

NCAR_BLUE, INK, MUTED, GRID = "#0057C2", "#00357A", "#6B7280", "#E5E7EB"
LEGACY_LOC = 250_000          # "roughly 250K lines", Confessions of a Vibe Coder, slide 3
TALK = date(2026, 3, 11)      # the March talk the series picks up from

rows = list(csv.DictReader(open(HERE / "data/loc_progression.tsv"), delimiter="\t"))
x = [date.fromisoformat(r["date"]) for r in rows]
y = [int(r["lines"]) for r in rows]

plt.rcParams.update({"font.family": "Poppins", "font.size": 13})
fig, ax = plt.subplots(figsize=(10, 4.2), dpi=200)
ax.fill_between(x, y, color=NCAR_BLUE, alpha=0.10, linewidth=0)
ax.plot(x, y, color=NCAR_BLUE, linewidth=2, solid_joinstyle="round", solid_capstyle="round")

ax.axhline(LEGACY_LOC, color=MUTED, linewidth=1.2, linestyle=(0, (4, 3)))
ax.text(x[0], LEGACY_LOC, "legacy SAM, ~250K lines†", color=MUTED, fontsize=11,
        va="bottom", ha="left")

def mark(i, label, dx, dy, ha="center"):
    ax.plot(x[i], y[i], "o", color=NCAR_BLUE, markersize=8,
            markeredgecolor="white", markeredgewidth=2, zorder=3)
    ax.annotate(label, (x[i], y[i]), xytext=(dx, dy), textcoords="offset points",
                ha=ha, color=INK, fontsize=11)

talk = max(i for i, d in enumerate(x) if d <= TALK)
mark(0, f"{y[0]/1e3:,.1f}K", 0, 12)
mark(talk, f"the March talk\n{y[talk]/1e3:,.0f}K", 0, 14)
mark(len(x) - 1, f"today\n{y[-1]/1e3:,.0f}K", -14, 4, ha="right")

ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e3:,.0f}K" if v else "0"))
ax.set_ylim(0, max(y) * 1.15)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.spines["bottom"].set_color(MUTED)
ax.tick_params(colors=MUTED, length=0)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
# One tick per data point (each a month-end), the year shown where it changes.
ax.set_xticks(x, [f"{d:%b}\n{d:%Y}" if i == 0 or d.month == 1 else f"{d:%b}"
                  for i, d in enumerate(x)])
FOOTNOTE = ("† Every text line on main (code, tests, docs, fixtures): the method of the March talk.\n"
            "   Legacy SAM's ~250K was counted differently, so read it as a landmark, not a race.")
fig.tight_layout(rect=(0, 0.11, 1, 1))
fig.text(0.01, 0.015, FOOTNOTE, color=MUTED, fontsize=10, ha="left", va="bottom")
fig.savefig(HERE / "images/loc_progression.png", transparent=False, facecolor="white")
