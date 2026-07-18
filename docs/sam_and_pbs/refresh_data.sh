#!/usr/bin/env bash
# Regenerate the frozen artifacts under data/ and the _tree_*.qmd mermaid
# fragments from live SAM data, using the hpc-scheduling-tools repo four
# levels up.  Run manually from this directory when the slides should pick
# up fresh numbers; rendering the deck itself never needs SAM access.
set -euo pipefail
cd "$(dirname "$0")"

REPO=../../../..                       # hpc-scheduling-tools checkout
source "${REPO}/config_env.sh"         # tool env + SAM credentials

mkdir -p data
tmpdb=$(mktemp -t sam_and_pbs_accounting)

"${REPO}/fsparsetree_mr.py" Derecho data/derecho.tree
"${REPO}/samuel2sql.py"     Derecho "${tmpdb}"

sqlite3 "${tmpdb}" .schema > data/accounting_schema.txt
sqlite3 "${tmpdb}" "
    select 'users',        count(*) from users        union all
    select 'projects',     count(*) from projects     union all
    select 'projectusers', count(*) from projectusers union all
    select 'gpu_projects', count(*) from gpu_projects union all
    select 'gpu_users',    count(*) from gpu_users    union all
    select 'queues',       count(*) from queues       union all
    select 'wcoverride',   count(*) from wcoverride
    " | column -t -s'|' > data/accounting_counts.txt
# The membership lookup deliberately uses the deck author's own username,
# so no one else's project memberships get committed to this repo.
sqlite3 -header -column "${tmpdb}" "
    select projects.code, project_status.code as status, projects.active
    from projectusers
    join project_status on status = project_status.id
    join projects on projectusers.pid = projects.id
    join users on projectusers.uid = users.uid
    where users.name is 'benkirk'" > data/accounting_lookup.txt
sqlite3 -header -column "${tmpdb}" "
    select queue, wallclocklimit from queues
    order by queue limit 12" > data/queues_lookup.txt
rm -f "${tmpdb}"

./tree2mermaid.py data/derecho.tree derecho \
    --stack --max-children 4 --include ASD --include WNA \
    --percent-level 1 --percent-level 2 --count-level 2 \
    --qmd --fig-width 9.5 > _tree_overview.qmd
./tree2mermaid.py data/derecho.tree CESM0002grp \
    --max-children 4 --include CESM0002 --include CESM0028grp \
    --qmd --fig-width 5.5 > _tree_cesm.qmd
./tree2mermaid.py data/derecho.tree NMMM0003grp \
    --depth 1 --max-children 5 --include NMMM0080 --include NMMM0003 \
    --qmd --fig-width 5.5 > _tree_pool.qmd

echo "refreshed: data/ + _tree_{overview,cesm,pool}.qmd" >&2
