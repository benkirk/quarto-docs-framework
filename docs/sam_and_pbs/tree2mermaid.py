#!/usr/bin/env python3
"""Convert a PBS fairshare resource_group file into a mermaid diagram.

Reads the four-column tree format emitted by fsparsetree_mr.py
(`Vertex_name  fairshare_id  parent  #shares`) and prints a mermaid
`graph TD` for the subtree under a chosen vertex, one node per vertex
labeled with its share.  Used to freeze real-data diagrams into the deck
(see refresh_data.sh); the committed `_tree_*.qmd` fragments are its
output.

    tree2mermaid.py <treefile> <root> [--depth N] [--max-children N]
                    [--include NAME ...] [--qmd] [--fig-width IN]

- Children render sorted by share, largest first.  --max-children keeps
  the top N per parent and elides the rest into a single "(+k more)"
  node; --include forces specific vertices to survive the cut.
- Shares are labeled raw (thousands-separated) by default; a tier that
  uses SAM's percentage*100 convention is labeled as percentages by
  naming its level (depth below the root, children of the root = 1)
  with --percent-level.
- Interior `<code>grp` vertices and their self-leaves get distinct
  styling so the project-tree model reads at a glance.
- --qmd wraps the graph in a ```{mermaid} fence, ready for
  `{{< include _file.qmd >}}` from a slide.
"""
import argparse
import sys


def parse_tree(path):
    """Return ({name: share}, {parent: [child, ...]}) preserving file order."""
    shares, children = {}, {}
    with open(path) as f:
        for line in f:
            fields = line.split()
            if len(fields) != 4:
                continue
            name, _fsid, parent, share = fields
            shares[name] = int(share)
            children.setdefault(parent, []).append(name)
    return shares, children


def format_share(share, as_percent):
    """Percentage*100 tiers read as percentages, everything else raw."""
    if as_percent:
        return ("%.2f%%" % (share / 100.0)).replace(".00%", "%")
    return format(share, ",")


def emit(shares, children, root, depth, max_children, include,
         percent_levels, out):
    grp_nodes, leaf_nodes, elision_nodes = [], [], []

    def walk(name, level):
        kids = children.get(name, [])
        if not kids or level >= depth:
            return
        ordered = sorted(kids, key=lambda k: -shares[k])
        if max_children and len(ordered) > max_children:
            keep = ordered[:max_children]
            keep += [k for k in ordered[max_children:] if k in include]
            elided = len(ordered) - len(keep)
        else:
            keep, elided = ordered, 0
        for kid in keep:
            label = format_share(shares[kid], level + 1 in percent_levels)
            out.append('    %s --> %s["%s<br/>%s"]'
                       % (name, kid, kid, label))
            if kid.endswith("grp"):
                grp_nodes.append(kid)
            elif kid + "grp" == name:
                leaf_nodes.append(kid)
            walk(kid, level + 1)
        if elided:
            node = "%s_more" % name
            out.append('    %s --> %s(["(+%d more)"])' % (name, node, elided))
            elision_nodes.append(node)

    out.append("graph TD")
    out.append('    %s["%s<br/>%s"]'
               % (root, root, format_share(shares[root], 0 in percent_levels)))
    if root.endswith("grp"):
        grp_nodes.append(root)
    walk(root, 0)

    out.append("    classDef grp fill:#cfe2f3,stroke:#1f4e79,stroke-width:2px")
    out.append("    classDef selfleaf fill:#fff2cc,stroke:#bf9000")
    out.append("    classDef elided fill:#f3f3f3,stroke:#999999,"
               "stroke-dasharray:4 3,color:#666666")
    for cls, nodes in (("grp", grp_nodes), ("selfleaf", leaf_nodes),
                       ("elided", elision_nodes)):
        if nodes:
            out.append("    class %s %s" % (",".join(nodes), cls))


def main(argv):
    parser = argparse.ArgumentParser(
        prog="tree2mermaid.py",
        description="Render a resource_group subtree as a mermaid graph.")
    parser.add_argument("treefile")
    parser.add_argument("root", help="vertex whose subtree to draw")
    parser.add_argument("--depth", type=int, default=99,
                        help="levels below the root to draw (default: all)")
    parser.add_argument("--max-children", type=int, default=0,
                        help="per parent, keep the N largest children and "
                             "elide the rest (default: keep all)")
    parser.add_argument("--include", action="append", default=[],
                        help="vertex to keep even past --max-children "
                             "(repeatable)")
    parser.add_argument("--percent-level", action="append", type=int,
                        default=[], metavar="N",
                        help="format shares at this depth below the root "
                             "(children of the root = 1) as percentage*100 "
                             "(repeatable)")
    parser.add_argument("--qmd", action="store_true",
                        help="wrap output in a ```{mermaid} fence")
    parser.add_argument("--fig-width", type=float, default=0,
                        help="mermaid fig-width cell option, in inches")
    args = parser.parse_args(argv[1:])

    shares, children = parse_tree(args.treefile)
    if args.root not in shares:
        sys.stderr.write("tree2mermaid.py: no vertex '%s' in %s\n"
                         % (args.root, args.treefile))
        return 1

    out = []
    emit(shares, children, args.root, args.depth, args.max_children,
         set(args.include), set(args.percent_level), out)
    if args.qmd:
        out.insert(0, "```{mermaid}")
        if args.fig_width:
            out.insert(1, "%%%%| fig-width: %g" % args.fig_width)
        out.append("```")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
