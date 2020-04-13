![Graphvy Preview](preview.gif)

This is a dynamic graph layout app written with Kivy and graph-tool.  Instructions for installing graph-tool tool can
be found [here](https://graph-tool.skewed.de/).

To load arbitrary rules for dynamic graphs, one needs a py file that defines a local variable named `rule` such that
`rule(G)` (where G is our graph) returns a callable that updates `G` when called.  Any imported files should be placed
in cwd of `__main__`.

To allow proper coloring of edge/node states, rules should have attributes `node_states`, `edge_states` that are dicts
with keys being the names of the node/edge properties and values being 1 or 2-tuples of either number of states or the
range of the states (if continuous-valued).  These attributes are only needed for coloring; optional otherwise.

#TODO

* path highlighter
* bezier lines (only when paused; computationally heavy)
* degree histogram
* hide/filter nodes
* recycleview for adjacencylist
