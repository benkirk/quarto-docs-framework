#!/usr/bin/env bash
# Regenerate the frozen data under data/ (and the charts drawn from it).
# Hand-run only: rendering the decks never needs a sam-queries checkout.
#
#   SAMUEL_REPO=~/codes/project_samuel/devel ./refresh_data.sh
#
# Reads the checkout's origin/main (fetch first). Needs a python3 with
# matplotlib for the charts, e.g. the sam-queries conda env.
set -euo pipefail
cd "$(dirname "$0")"
repo=${SAMUEL_REPO:-$HOME/codes/project_samuel/devel}
ref=${SAMUEL_REF:-origin/main}

# LOC = every text line in the tree (code, tests, docs, fixtures): the same
# method as the March 2026 "Project SAMuel Progression" slide, which it
# reproduces exactly (8,791 / 51,829 / 64,202 / 75,420).
lines() { git -C "$repo" grep -I -c '' "$1" -- "${@:2}" | awk -F: '{s+=$NF} END{print s+0}'; }

out=data/loc_progression.tsv
printf 'date\tcommits\tlines\tpython_lines\n' > "$out"
first=$(git -C "$repo" log --reverse --format=%ad --date=short "$ref" | awk 'NR == 1')
# Month-ends from the first commit through today (today closes the series).
month_ends() {
    python3 -c 'import sys, datetime as dt
d, today = dt.date.fromisoformat(sys.argv[1]).replace(day=1), dt.date.today()
while True:
    n = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    print(min(n - dt.timedelta(days=1), today))
    if n > today: break
    d = n' "$1"
}
for end in $(month_ends "$first"); do
    rev=$(git -C "$repo" rev-list -1 --before="$end 23:59:59" "$ref")
    printf '%s\t%s\t%s\t%s\n' "$end" "$(git -C "$repo" rev-list --count "$rev")" \
        "$(lines "$rev" .)" "$(lines "$rev" '*.py')" >> "$out"
done
cat "$out"

python3 plot_progression.py
