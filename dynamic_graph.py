from functools import partial
from itertools import islice
from random import choices, randrange as randint


def nth(iterator, n):
    """Return the nth item from an iterator."""
    return next(islice(iterator, n, None))


class AsyncDynamicBase:
    """Asynchronous graphs update nodes/edges randomly."""

    __slots__ = 'G', 'niter'

    def __init__(self, G, *, niter=1):
        self.G = G # Graph
        self.niter = niter # Default iterations for self.update

    @property
    def rv(self):
        """Choose a random vertex from G."""
        return self.G.vertex(randint(G.num_vertices()))

    @property
    def re(self):
        """Choose a random edge from G."""
        return nth(self.G.edges(), randint(self.G.num_edges()))

    def update(self):
        """Apply self.step niter times."""
        for _ in range(self.niter):
            self.step()

    def step(self):
        """A single iteration of graph dynamics."""
        raise NotImplementedError

    def __call__(self):
        """Alternative method of stepping."""
        return self.step()


class GraphASEP(AsyncDynamicBase):
    """
    Totally Asymmetric Simple Exclusion Process (TASEP) is normally defined on a 1-D lattice. Our
    Graph TASEP (GASEP) moves these dynamics to a graph with the particles represented by edges.
    """

    __slots__ = 'num_vertices', 'num_edges'

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
    """
    Edge-centric as we'll base our dynamics off of randomly chosen edges rather than randomly chosen
    nodes.  Node-centric dynamics will lead to a different steady-state.
    """

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
        self.G.remove_edge(edge) # We'll add edge back if our random move was excluded.

        source_out = source.out_degree()
        target_out = target.out_degree()

        if source_out + target_out == 0: # No moves possible.
            self.G.add_edge(source, target)
            return

        head = partial(self.head_move, source_out)
        tail = partial(self.tail_move, target_out)
        move, = choices((head, tail), (source_out, target_out))

        if not move(source, target):
            self.G.add_edge(source, target)


class EdgeFlipGASEP(EdgeCentricGASEP):
    """Same as EdgeCentricGASEP, but with one extra move(edges can flip orientation)."""

    def flip(self, source, target):
        """Flip an edge if the flipped edge doesn't exist."""
        if self.G.edge(target, source) is None:
            self.G.add_edge(target, source)
            return True

    def step(self):
        source, target = edge = self.re
        self.G.remove_edge(edge) # We'll add edge back if our random move was excluded.

        source_out = source.out_degree()
        target_out = target.out_degree()

        head = partial(self.head_move, source_out)
        tail = partial(self.tail_move, target_out)
        move, = choices((head, tail, self.flip), (source_out, target_out, 1))

        if not move(source, target):
            self.G.add_edge(source, target)
