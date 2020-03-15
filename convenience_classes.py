"""Convenience classes for graph widget."""
from kivy.graphics import Color, Line
from graph_tool import Graph

from arrow import Arrow
from constants import *


class Node(Line):
    __slots__ = 'color', 'vertex', 'canvas', 'group_name', 'is_frozen'

    def __init__(self, vertex, canvas):
        self.group_name = str(id(self))

        self.vertex = vertex
        self.canvas = canvas

        self.color = Color(*NODE_COLOR, group=self.group_name)
        super().__init__(width=NODE_WIDTH, group=self.group_name)

    def recolor_out_edges(self, color):
        edges = self.canvas.edges
        for edge in self.vertex.out_edges():
            edges[edge].color.rgba = color

    def freeze(self, color):
        self.canvas.G.vp.pinned[self.vertex] = 1
        self.color.rgba = color
        self.recolor_out_edges(HIGHLIGHTED_EDGE)

    def unfreeze(self):
        self.canvas.G.vp.pinned[self.vertex] = 0
        self.color.rgba = NODE_COLOR
        self.recolor_out_edges(EDGE_COLOR)

    def collides(self, mx, my):
        x, y = self.canvas.coords[int(self.vertex)]
        return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS

    def update(self):
        self.circle = *self.canvas.coords[int(self.vertex)], NODE_RADIUS


class Edge(Arrow):
    __slots__ = 's', 't', 'canvas'

    def __init__(self, edge, canvas):
        self.s, self.t = edge
        self.canvas = canvas
        color = HIGHLIGHTED_EDGE if self.canvas.G.vp.pinned[self.s] else EDGE_COLOR
        super().__init__(line_color=color,
                         head_color=HEAD_COLOR,
                         width=EDGE_WIDTH,
                         head_size=HEAD_SIZE)

    def update(self):
        super().update(*self.canvas.coords[int(self.s)], *self.canvas.coords[int(self.t)])


class Selection(Line):
    __slots__ = 'color', 'min_x', 'max_x', 'min_y', 'max_y', 'group_name'

    def __init__(self, *args, **kwargs):
        self.group_name = str(id(self))
        self.color = Color(*SELECT_RECT_COLOR, group=self.group_name)

        super().__init__(width=SELECT_WIDTH, close=True, group=self.group_name)

        self.set_corners()

    def set_corners(self, x1=0, y1=0, x2=0, y2=0):
        min_x, max_x = self.min_x, self.max_x = (x1, x2) if x1 <= x2 else (x2, x1)
        min_y, max_y = self.min_y, self.max_y = (y1, y2) if y1 <= y2 else (y2, y1)

        self.points = min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y

    def __contains__(self, coord):
        """Return True if coord is within the rectangle."""
        x, y = coord
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


class NodeSet(set):
    """Set that correctly colors nodes that are added to/removed from it."""
    def __init__(self, *args, color, **kwargs):
        self.color = color
        super().__init__(*args, **kwargs)

    def add(self, node):
        super().add(node)
        node.freeze(self.color)


class SelectedSet(NodeSet):
    def remove(self, node):
        super().remove(node)
        node.unfreeze()

class PinnedSet(NodeSet):
    def remove(self, node):
        super().remove(node)
        node.color.rgba = HIGHLIGHTED_NODE


class GraphInterface(Graph):
    """
    An interface from a graph_tool Graph to graph widget that updates the widget when an edge/vertex
    has been added/removed.  Our solution to dealing with dynamic graphs that change size.
    """
    __slots__ = "graph_widget"

    def __init__(self, graph_widget, *args, **kwargs):
        self.graph_widget = graph_widget
        super().__init__(*args, **kwargs)

    def add_vertex(self, *args, **kwargs):
        node = super().add_vertex(*args, **kwargs)
        self.graph_widget.make_vertex(node)
        return node

    def remove_vertex(self, node, fast=True):
        for edge in node.all_edges():
            self.remove_edge(edge)
        self.graph_widget.pre_unmake_node(node)
        super().remove_vertex(node, fast=True)  # Interface relies on fast=True
        self.graph_widget.post_unmake_node()

    def add_edge(self, *args, **kwargs):
        edge = super().add_edge(*args, **kwargs)
        self.graph_widget.make_edge(edge)
        return edge

    def remove_edge(self, edge):
        self.graph_widget.unmake_edge(edge)
        super().remove_edge(edge)

