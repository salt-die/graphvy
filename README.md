This is a dynamic graph layout app written with Kivy and graph-tool.  Instructions for installing graph-tool tool can
be found [here](https://graph-tool.skewed.de/).

To load arbitrary rules for dynamic graphs, one needs a py file that defines a local variable named `rule` such that
`rule(G)` (where G is our graph) returns a callable that updates `G` when called.  Any imported files should be placed
in cwd of `__main__`.
