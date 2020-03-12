from functools import partial
from itertools import islice, starmap
from random import choice, choices, randrange as randint

import graph_tool as gt


def nth(iterator, n):
    """Return the nth item from an iterator."""
    return next(islice(iterator, n, None))


class AsyncDynamicBase:
    def __init__(self, G, *, niter=1):
        self.G = G
        self.niter = niter

    @property
    def rv(self):
        """Choose a random vertex from G."""
        return self.G.vertex(randint(G.num_vertices()))

    @property
    def re(self):
        """Choose a random edge from G."""
        return nth(self.G.edges(), randint(self.G.num_edges()))

    def update(self):
        for _ in range(self.niter):
            self.step()

    def step(self):
        pass


class GraphASEP(AsyncDynamicBase):
    def __init__(self, G, *, niter=1):
        super().__init__(G, niter=niter)

        # The number of edges and vertices remain constant in a GASEP
        self.num_vertices = G.num_vertices()
        self.num_edges = G.num_edges()

    @property
    def rv(self):
        """Choose a random vertex from G."""
        return self.G.vertex(randint(self.num_vertices))

    @property
    def re(self):
        """Choose a random edge from G."""
        return nth(self.G.edges(), randint(self.num_edges))


class EdgeCentricGASEP(GraphASEP):
    def flip(self, source, target):
        """Flip an edge if the flipped edge doesn't exist."""
        if self.G.edge(target, source) is None:
            self.G.add_edge(target, source)
            return True

    def head_move(self, out_deg, source, target):
        """Move source along an out_edge if possible."""
        new_source = nth(source.out_neighbors(), randint(out_deg))

        if self.G.edge(new_source, target) is None:
            self.G.add_edge(new_source, target)
            return True

    def tail_move(self, out_deg, source, target):
        """Move target along an out_edge if possible."""
        new_target = nth(target.out_neighbors(), randint(out_deg))

        if self.G.edge(source, new_target) is None:
            self.G.add_edge(source, new_target)
            return True

    def step(self):
        source, target = edge = self.re
        self.G.remove_edge(edge)
        source_out, target_out = source.out_degree(), target.out_degree()

        head, tail = partial(self.head_move, source_out), partial(self.tail_move, target_out)
        move, = choices((head, tail, self.flip), (source_out, target_out, 1))

        if not move(source, target):
            self.G.add_edge(source, target)

    def __call__(self):
        self.step()