"""Convenience classes for Graphvy"""
from random import random

from graph_tool import Graph
from kivy.graphics import Color, Line
from kivymd.uix.behaviors import BackgroundColorBehavior, HoverBehavior
from kivymd.uix.list import OneLineListItem

from arrow import Arrow
from constants import *


class AdjacencyListItem(OneLineListItem, BackgroundColorBehavior, HoverBehavior):
    __slots__ = 'node'

    def __init__(self, node, *args, **kwargs):
        self.node = node

        super().__init__(*args,
                         md_bg_color=SELECTED_COLOR,
                         theme_text_color='Custom',
                         text_color=NODE_COLOR, **kwargs)
        self.update_text()

        self.bind(on_release=self._on_release)

    def on_enter(self, *args):
        adjacency_list = self.node.canvas.adjacency_list
        if not adjacency_list.is_hidden and adjacency_list.is_selected:
            self.node.canvas.highlighted = self.node

    def on_leave(self, *args):
        pass

    def _on_release(self, *args):
        self.node.canvas.touch_down_dict[self.node.canvas.tool]()

    def update_text(self):
        self.text = f'{self.node.vertex}: {", ".join(map(str, self.node.vertex.out_neighbors()))}'


class Node(Line):
    __slots__ = 'color', 'vertex', 'canvas', 'group_name', 'list_item'

    def __init__(self, vertex, canvas):
        self.group_name = str(id(self))

        self.vertex = vertex
        self.canvas = canvas

        color = canvas.node_colormap[canvas.node_colors[vertex]]
        self.color = Color(*color, group=self.group_name)
        super().__init__(width=NODE_WIDTH, group=self.group_name)

        self.list_item = None  # Set in make_list_item

    def update_out_edges(self):
        edges = self.canvas.edges
        for edge in self.vertex.out_edges():
            edges[edge].update()

    def freeze(self, color=None):
        self.canvas.G.vp.pinned[self.vertex] = 1
        if color is not None:
            self.color.rgba = color

            if self.list_item is not None:
                self.list_item.md_bg_color = tuple(min(c * 1.2, 1) for c in color)

        self.update_out_edges()

    def unfreeze(self):
        canvas = self.canvas
        canvas.G.vp.pinned[self.vertex] = 0
        self.color.rgba = canvas.node_colormap[canvas.node_colors[self.vertex]]
        if self.list_item is not None:
            self.list_item.md_bg_color = SELECTED_COLOR
        self.update_out_edges()

    def collides(self, mx, my):
        x, y = self.canvas.coords[int(self.vertex)]
        return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS

    def make_list_item(self):
        self.list_item = AdjacencyListItem(self)
        return self.list_item

    def update(self):
        canvas = self.canvas
        if not canvas.G.vp.pinned[self.vertex]:
            self.color.rgba = canvas.node_colormap[canvas.node_colors[self.vertex]]
        self.circle = *canvas.coords[int(self.vertex)], NODE_RADIUS


class Edge(Arrow):
    __slots__ = 'edge', 's', 't', 'canvas', '_directed'

    def __init__(self, edge, canvas, directed=True):
        self.edge = edge
        self.s, self.t = edge
        self.canvas = canvas
        self._directed = directed

        super().__init__(width=EDGE_WIDTH, head_size=HEAD_SIZE)

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

        if self.canvas.G.vp.pinned[self.s]:
            color = HIGHLIGHTED_EDGE
        else:
            color = self.canvas.edge_colormap[self.canvas.edge_colors[self.edge]]
        hcolor =  tuple(min(c * 1.2, 1) for c in color)
        self.color.rgba = color
        self.head.color.rgba = hcolor


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
    An interface from a graph_tool Graph to the graph canvas that updates the canvas when an edge/vertex
    has been added/removed.
    """
    __slots__ = 'canvas'

    def __init__(self, canvas, *args, **kwargs):
        self.canvas = canvas
        super().__init__(*args, **kwargs)

    def add_vertex(self, *args, **kwargs):
        node = super().add_vertex(*args, **kwargs)

        with self.canvas._node_instructions:
            self.canvas.nodes[node] = Node(node, self.canvas)

        self.vp.pos[node][:] = random(), random()

        if self.canvas.adjacency_list:
            self.canvas.adjacency_list.add_widget(self.canvas.nodes[node].make_list_item())

        return node

    def remove_vertex(self, node, fast=True):
        for edge in set(node.all_edges()):
            self.remove_edge(edge)

        instruction = self.canvas.nodes[node]
        canvas = self.canvas
        #
        # --- Remove the canvas instructions corresponding to node. Prepare last node to take its place. ---
        #
        if canvas.highlighted is instruction:
            canvas.highlighted = None

        if instruction in canvas._pinned:
            canvas._pinned.remove(instruction)
        elif instruction in canvas._selected:
            canvas._selected.remove(instruction)

        last = self.num_vertices() - 1
        pos = int(node)
        if pos != last:
            last_vertex = self.vertex(last)
            last_node = canvas.nodes.pop(last_vertex)
            edge_instructions = tuple(canvas.edges.pop(edge) for edge in set(last_vertex.all_edges()))
        else:
            last_vertex = None

        if canvas.adjacency_list:
            canvas.adjacency_list.remove_widget(canvas.nodes[node].list_item)
        canvas._node_instructions.remove_group(instruction.group_name)
        del canvas.nodes[node]
        #
        # --- Prep done.
        #

        super().remove_vertex(node, fast=True)  # Interface relies on fast=True, we ignore the previous fast value

        #
        # --- Swap the vertex descriptor of the last node and edge descriptors of all edges adjacent to ---
        # --- it and fix our node and edge dictionary that used these descriptors. (Node deletion       ---
        # --- invalidated these descriptors.)                                                           ---
        #
        if last_vertex is None:
            return

        last_node.vertex = self.vertex(pos)         # Update descriptor
        canvas.nodes[last_node.vertex] = last_node  # Update node dict

        for edge_instruction, edge in zip(edge_instructions, set(last_node.vertex.all_edges())):
            edge_instruction.s, edge_instruction.t = edge  # Update descriptor
            canvas.edges[edge] = edge_instruction          # Update edge dict

        if canvas.adjacency_list:  # Reposition the adjacency list item
            canvas.adjacency_list.remove_widget(last_node.list_item)
            last_node.list_item.update_text()
            canvas.adjacency_list.add_widget(last_node.list_item, index=self.num_vertices() - pos - 1)

    def add_edge(self, *args, **kwargs):
        edge = super().add_edge(*args, **kwargs)

        # Make a new canvas instruction corresponding to edge.
        with self.canvas._edge_instructions:
            self.canvas.edges[edge] = Edge(edge, self.canvas)
        if self.canvas.adjacency_list:
            self.canvas.nodes[self.canvas.edges[edge].s].list_item.update_text()

        return edge

    def remove_edge(self, edge):
        # Remove canvas instruction corresponding to edge
        source = edge.source()
        instruction = self.canvas.edges.pop(edge)
        self.canvas._edge_instructions.remove_group(instruction.group_name)

        super().remove_edge(edge)

        if self.canvas.adjacency_list:
            self.canvas.nodes[source].list_item.update_text()
