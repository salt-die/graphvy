"""Convenience classes for Graphvy"""
### CONSIDER: Node and Edge maybe shouldn't subclass
### TODO: CALCULATE HIGHLIGHT COLORS FROM NORMAL COLORS IF WE IMPLEMENT A COLOR PICKER
from graph_tool import Graph
from kivy.graphics import Color, Line
from kivymd.uix.behaviors import BackgroundColorBehavior
from kivymd.uix.list import OneLineListItem

from arrow import Arrow
from constants import *


class AdjacencyListItem(OneLineListItem, BackgroundColorBehavior):
    __slots__ = 'node'

    def __init__(self, node, *args, **kwargs):
        self.node = node

        super().__init__(*args, md_bg_color=LIST_BACKGROUND, **kwargs)
        self.update_text()

        self.bind(on_press=self._on_press)

    def _on_press(self, *args):
        node = self.node
        canvas = node.canvas
        pinned = canvas._pinned
        selected = canvas._selected

        if canvas.tool == 'Select':
            if node in selected:
                selected.remove(node)
            elif node not in pinned:
                selected.add(node)

        elif canvas.tool == 'Pin':
            if node in pinned:
                pinned.remove(node, unfreeze=True)
            else:
                if node in selected:
                    selected.remove(node)
                pinned.add(node)

        elif canvas.tool == 'Delete Node':
            canvas.G.remove_vertex(node.vertex)

        elif canvas.tool == 'Add Edge':
            if canvas.source is None:
                canvas.source = node
            else:
                if canvas.multigraph or canvas.G.edge(canvas.source.vertex, node.vertex) is None:
                    canvas.G.add_edge(canvas.source.vertex, node.vertex)
                canvas.source = None

        elif canvas.tool == 'Delete Edge':
            if canvas.source is None:
                canvas.source = node
            else:
                edge = canvas.G.edge(canvas.source.vertex, node.vertex)
                if edge is not None:
                    canvas.G.remove_edge(edge)
                canvas.source = None

        else:
            canvas.highlighted = node

    def update_text(self):
        self.text = f'{self.node.vertex}: {", ".join(map(str, self.node.vertex.out_neighbors()))}'


class Node(Line):
    __slots__ = 'color', 'vertex', 'canvas', 'group_name', 'list_item'

    def __init__(self, vertex, canvas):
        self.group_name = str(id(self))

        self.vertex = vertex
        self.canvas = canvas

        self.color = Color(*NODE_COLOR, group=self.group_name)
        super().__init__(width=NODE_WIDTH, group=self.group_name)

        self.list_item = None  # Set in make_list_item

    def recolor_out_edges(self, line_color, head_color):
        edges = self.canvas.edges
        for edge in self.vertex.out_edges():
            edges[edge].color.rgba = line_color
            edges[edge].head.color.rgba = head_color

    def freeze(self, color=None):
        self.canvas.G.vp.pinned[self.vertex] = 1
        if color is not None:
            self.color.rgba = color

            if self.list_item is not None:
                self.list_item.md_bg_color = color

        self.recolor_out_edges(HIGHLIGHTED_EDGE, HIGHLIGHTED_HEAD)

    def unfreeze(self):
        self.canvas.G.vp.pinned[self.vertex] = 0
        self.color.rgba = NODE_COLOR
        if self.list_item is not None:
            self.list_item.md_bg_color = LIST_BACKGROUND
        self.recolor_out_edges(EDGE_COLOR, HEAD_COLOR)

    def collides(self, mx, my):
        x, y = self.canvas.coords[int(self.vertex)]
        return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS

    def make_list_item(self):
        self.list_item = AdjacencyListItem(self)
        return self.list_item

    def update(self):
        self.circle = *self.canvas.coords[int(self.vertex)], NODE_RADIUS


class Edge(Arrow):
    __slots__ = 's', 't', 'canvas', '_directed'

    def __init__(self, edge, canvas, directed=True):
        self.s, self.t = edge
        self.canvas = canvas
        self._directed = directed

        if self.canvas.G.vp.pinned[self.s]:
            line_color = HIGHLIGHTED_EDGE
            head_color = HIGHLIGHTED_HEAD
        else:
            line_color = EDGE_COLOR
            head_color = HEAD_COLOR
        super().__init__(line_color=line_color,
                         head_color=head_color,
                         width=EDGE_WIDTH,
                         head_size=HEAD_SIZE)

    @property
    def directed(self):
        return self._directed

    @directed.setter
    def directed(self, boolean):
        self._directed = self.head.color.a = boolean

    def update(self):
        x1, y1, x2, y2 = *self.canvas.coords[int(self.s)], *self.canvas.coords[int(self.t)]
        self.points = x1, y1, x2, y2
        if self.directed:
            self.head.update(x1, y1, x2, y2)


class Selection(Line):
    __slots__ = 'color', 'min_x', 'max_x', 'min_y', 'max_y', 'group_name'

    def __init__(self):
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=SELECTED_COLOR, **kwargs)

    def remove(self, node):
        super().remove(node)
        node.unfreeze()


class PinnedSet(NodeSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, color=PINNED_COLOR, **kwargs)

    def remove(self, node, unfreeze=False):
        super().remove(node)
        if unfreeze:
            node.unfreeze()
        else:
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
        self.graph_widget.make_node(node)
        return node

    def remove_vertex(self, node, fast=True):
        for edge in set(node.all_edges()):
            self.remove_edge(edge)

        self.graph_widget.pre_unmake_node(node)
        super().remove_vertex(node, fast=True)  # Interface relies on fast=True, we ignore the previous fast value
        self.graph_widget.post_unmake_node()

    def add_edge(self, *args, **kwargs):
        edge = super().add_edge(*args, **kwargs)
        self.graph_widget.make_edge(edge)
        return edge

    def remove_edge(self, edge):
        self.graph_widget.pre_unmake_edge(edge)
        super().remove_edge(edge)
        self.graph_widget.post_unmake_edge()
