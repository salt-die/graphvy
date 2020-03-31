This is a dynamic graph layout app written with Kivy and graph-tool.  Instructions for installing graph-tool tool can
be found [here](https://graph-tool.skewed.de/).

To load arbitrary rules for dynamic graphs, one needs a py file that defines a local variable named `rule` such that
`rule(G)` (where G is our graph) returns a callable that updates `G` when called.  Any imported files should be placed
in cwd of `__main__`.


#TODO

* path highlighter
* bezier lines (only when paused; computationally heavy)
* degree histogram
* hide/filter nodes
* node/edge states visible - generate a gradient depending on the type of property map -- allow user customization after
* default node colors stored in Node/Edge classes to allow changing individual colors or displaying states
* recycleview for adjacencylist