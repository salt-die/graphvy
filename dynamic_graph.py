from functools import partial
from itertools import islice, chain
from random import choice, choices, randrange as randint


def nth(iterator, n):
    """Return the nth item from an iterator."""
    return next(islice(iterator, n, None))


class AsyncDynamicBase:
    """Asynchronous graphs update nodes/edges randomly."""

    __slots__ = 'G', 'niter'

    def __init__(self, G, *, niter=1):
        self.G = G  # Graph
        self.niter = niter  # Default iterations for self.update

    @property
    def rv(self):
        """Choose a random vertex from G."""
        return self.G.vertex(randint(G.num_vertices()))

    @property
    def re(self):
        """Choose a random edge from G."""
        return self.G.edge(*nth(self.G.iter_edges(), randint(self.G.num_edges())))

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


class GASEPBase(AsyncDynamicBase):
    """Mix-in for Dynamic Graphs."""

    def head_move(self, out_deg, source, target, multigraph=False):
        """Move source along an out_edge if possible."""
        new_source = nth(source.out_neighbors(), randint(out_deg))

        if multigraph or self.G.edge(new_source, target) is None:
            self.G.add_edge(new_source, target)
            return True

    def tail_move(self, out_deg, source, target, multigraph=False):
        """Move target along an out_edge if possible."""
        new_target = nth(target.out_neighbors(), randint(out_deg))

        if multigraph or self.G.edge(source, new_target) is None:
            self.G.add_edge(source, new_target)
            return True

    def flip(self, source, target, multigraph=False):
        """Flip an edge if the flipped edge doesn't exist."""
        if multigraph or self.G.edge(target, source) is None:
            self.G.add_edge(target, source)
            return True


class EdgeCentricGASEP(GASEPBase):
    """
    Edge-centric as we'll base our dynamics off of randomly chosen edges rather than randomly chosen
    nodes.  Node-centric dynamics will lead to a different steady-state.
    """

    def step(self):
        if not self.G.num_edges():
            return

        source, target = edge = self.re
        self.G.remove_edge(edge)  # We'll add edge back if our random move was excluded.

        source_out = source.out_degree()
        target_out = target.out_degree()

        if source_out + target_out == 0:  # No moves possible.
            self.G.add_edge(source, target)
            return

        head = partial(self.head_move, source_out)
        tail = partial(self.tail_move, target_out)
        move, = choices((head, tail), (source_out, target_out))

        if not move(source, target):
            self.G.add_edge(source, target)


class EdgeFlipGASEP(GASEPBase):
    """Same as EdgeCentricGASEP, but with one extra move(edges can flip orientation)."""

    def step(self):
        if not self.G.num_edges():
            return

        source, target = edge = self.re
        self.G.remove_edge(edge)  # We'll add edge back if our random move was excluded.

        source_out = source.out_degree()
        target_out = target.out_degree()

        head = partial(self.head_move, source_out)
        tail = partial(self.tail_move, target_out)
        move, = choices((head, tail, self.flip), (source_out, target_out, 1))

        if not move(source, target):
            self.G.add_edge(source, target)


PHOTON = 0
MATTER = 1
ANTIMATTER = 2


class Gravity(GASEPBase):
    """
    An asynchronous graph that very loosely resembles gravity. (MATTER will attract; ANTIMATTER repulses)
    NOT ACTUAL PHYSICS -- I just like the flavor.
    """

    __slots__ = 'flavors', 'dynamics'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flavors = self.G.new_edge_property('int')
        self.dynamics = self.photon_dynamics, self.matter_dynamics, self.antimatter_dynamics

    def photon_move(self):
        source, target = self.particle
        self.G.remove_edge(self.particle)

        source_out = source.out_degree()
        target_out = target.out_degree()

        if source_out + target_out == 0:  # No moves possible.
            self.G.add_edge(source, target)
            return

        head = partial(self.head_move, source_out)
        tail = partial(self.tail_move, target_out)
        move, = choices((head, tail), (source_out, target_out))

        if not move(source, target):
            self.G.add_edge(source, target)

    def creation(self):
        s, t = self.particle
        if s == t:
            return False

        if (e := self.G.edge(t, s)) and self.flavors[e] == PHOTON:
            self.flavors[e] = MATTER
            self.flavors[self.particle] = ANTIMATTER
            return True
        return False

    def annihilation(self):
        s, t = self.particle
        if (e := self.G.edge(t, s)) and self.flavors[e] == ANTIMATTER:
            self.flavors[e] = PHOTON
            self.flavors[self.particle] = PHOTON
            return True
        return False

    def shrink_space(self):
        source, target = self.particle
        photons = [edge for edge in chain(source.out_edges(), target.out_edges())
                   if self.flavors[edge] == PHOTON and edge.source() != edge.target()]
        if not photons:
            return False

        photon = source, target = choice(photons)
        G = self.G
        flavors = self.flavors

        G.remove_edge(photon)
        for edge in list(target.out_edges()):
            if not G.edge(source, edge.target()):
                e = G.add_edge(source, edge.target())
                flavors[e] = flavors[edge]
            G.remove_edge(edge)
        for edge in list(target.in_edges()):
            if not G.edge(edge.source(), source):
                e = G.add_edge(edge.source(), source)
                flavors[e] = flavors[edge]
            G.remove_edge(edge)
        G.remove_vertex(target, fast=True)
        return True

    def expand_space(self):
        end_to_cleave = choice(tuple(self.particle))

        s, t = self.particle
        G = self.G
        flavors = self.flavors

        new_node = G.add_vertex(1)
        for edge in list(end_to_cleave.in_edges()):
            if randint(2):
                e = G.add_edge(edge.source(), new_node)
                flavors[e] = flavors[edge]
                G.remove_edge(edge)
        for edge in list(end_to_cleave.out_edges()):
            if randint(2):
                e = G.add_edge(new_node, edge.target())
                flavors[e] = flavors[edge]
                G.remove_edge(edge)
        e = G.add_edge(end_to_cleave, new_node)
        flavors[e] = PHOTON

    def emit_photon(self):
        end = choice(tuple(self.particle))
        if not self.G.edge(end, end):
            e = self.G.add_edge(end, end)
            self.flavors[e] = PHOTON

    def absorb_photon(self):
        source, target = self.particle

        photons = []
        if (e := self.G.edge(source, source)) and self.flavors[e] == PHOTON:
            photons.append(e)
        if (e := self.G.edge(target, target)) and self.flavors[e] == PHOTON:
            photons.append(e)
        if not photons:
            return False

        self.G.remove_edge(choice(photons))
        return True

    def photon_dynamics(self):
        if not self.creation():
            self.photon_move()

    def matter_dynamics(self):
        if not self.annihilation():
            if not self.shrink_space():
                self.emit_photon()

    def antimatter_dynamics(self):
        if not self.absorb_photon():
            self.expand_space()

    def step(self):
        if not self.G.num_edges():
            return

        self.particle = self.re
        flavor = self.flavors[self.particle]
        self.dynamics[flavor]()
