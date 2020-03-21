"""
Hold shift to drag-select vertices. Ctrl-click to select individual vertices, and again to pin them.
Space to pause/unpause the layout algorithm. Ctrl-Space to pause/unpause the Graph callback.
"""
### TODO: path highlighter
### TODO: bezier lines (only when paused; computationally heavy)
### TODO: degree histogram
### TODO: hide/filter nodes
### TODO: node/edge states visible
from functools import wraps
from random import random
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.config import Config
from kivy.graphics.instructions import CanvasBase
from kivy.uix.widget import Widget
from kivy.core.window import Window

import graph_tool as gt
from graph_tool.draw import random_layout, sfdp_layout
import numpy as np

from convenience_classes import Node, Edge, Selection, SelectedSet, PinnedSet, GraphInterface
from constants import *

Config.set('input', 'mouse', 'mouse,multitouch_on_demand')


def erdos_random_graph(nodes, edges, prune=True):
    G = gt.Graph()
    G.add_vertex(nodes)
    for _ in range(edges):
        G.add_edge(0, 0)
    gt.generation.random_rewire(G, model='erdos')

    if prune:
        G = gt.topology.extract_largest_component(G, directed=False, prune=True)
    return G


def redraw_canvas_after(func):
    """For methods that change vertex coordinates."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        args[0].update_canvas()
        return results

    return wrapper


def limit(interval):
    """Limits how often a function can be called to once every interval seconds."""
    def deco(func):
        last_call = time.time()

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            nonlocal last_call
            if now - last_call > interval:
                last_call = now
                return func(*args, **kwargs)

        return wrapper
    return deco


class GraphCanvas(Widget):
    """
    Dynamic graph layout widget.  Layout updates as graph changes.

    graph_callback(G) should return a callable that updates G when called.
    """

    _mouse_pos_disabled = False

    _highlighted = None  # For highlighted property.
    _selected = SelectedSet()
    _pinned = PinnedSet()

    _touches = []

    offset_x = .25
    offset_y = .25
    scale = .5

    is_selecting = False
    _drag_selection = False  # For is_drag_select property.
    ctrl_pressed = False

    _callback_paused = False
    _layout_paused = False

    def __init__(self, *args, G=None, graph_callback=None, **kwargs):
        if G is None:
            self.G = GraphInterface(self, erdos_random_graph(50, 80))
        else:
            self.G = GraphInterface(self, G)

        self.G.set_fast_edge_removal()
        self.G.vp.pos = random_layout(self.G, (1, 1))
        self.G.vp.pinned = self.G.new_vertex_property('bool')

        super().__init__(*args, **kwargs)

        # Following attributes set in setup_canvas:
        self.edges = None  # dict from self.G.edges() to Edge instruction group
        self.nodes = None  # dict from self.G.vertices() to Node instruction group
        self.background = None
        self.select_rect = None
        self._edge_instructions = None
        self._node_instructions = None
        self.setup_canvas()

        self.coords = None  # Set in transform_coords
        self._last_node_to_pos = None  # Set in unmake_node

        self.bind(size=self.update_canvas, pos=self.update_canvas)
        Window.bind(mouse_pos=self.on_mouse_pos)

        self.update_layout = Clock.schedule_interval(self.step_layout, UPDATE_INTERVAL)

        if graph_callback is not None:
            self.graph_callback = graph_callback(self.G)
            self.update_graph = Clock.schedule_interval(self.callback, 0)
        else:
            self.graph_callback = None

    @redraw_canvas_after
    def callback(self, dt):
        self.graph_callback()

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, node):
        """Freezes highlighted nodes or returns un-highlighted nodes to the proper color."""
        lit = self.highlighted
        if lit is not None:
            if lit in self._selected:
                lit.color.rgba = SELECTED_COLOR
            elif lit in self._pinned:
                lit.color.rgba = PINNED_COLOR
            else:
                lit.unfreeze()

        if node is not None:
            node.freeze(HIGHLIGHTED_NODE)

        self._highlighted = node

    @property
    def is_drag_select(self):
        return self._drag_selection

    @is_drag_select.setter
    def is_drag_select(self, boolean):
        """Make select_rect visible or non-visible depending on state."""
        self._drag_selection = boolean
        self.select_rect.set_corners()
        self.select_rect.color.a = int(boolean) * SELECT_RECT_COLOR[-1]

    def pause(self):
        """Pause/unpause graph_callback if ctrl is pressed or pause/unpause layout."""
        if self.ctrl_pressed:
            self._callback_paused = not self._callback_paused
            if self.graph_callback is not None:
                if self._callback_paused:
                    self.update_graph.cancel()
                else:
                    self.update_graph()
            return

        self._layout_paused = not self._layout_paused
        if self._layout_paused:
            self.update_layout.cancel()
        else:
            self.update_layout()

    def setup_canvas(self):
        """Populate the canvas with the initial instructions."""
        self.canvas.clear()

        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self.background = Rectangle(size=self.size, pos=self.pos)

        self._edge_instructions = CanvasBase()
        with self._edge_instructions:
            self.edges = {edge: Edge(edge, self) for edge in self.G.edges()}
        self.canvas.add(self._edge_instructions)

        self._node_instructions = CanvasBase()
        with self._node_instructions:
            self.nodes = {vertex: Node(vertex, self) for vertex in self.G.vertices()}
        self.canvas.add(self._node_instructions)

        with self.canvas.after:
            self.select_rect = Selection()
            Color(1, 1, 1, 1)

    def make_node(self, node):
        """Make new canvas instructions corresponding to node."""
        with self._node_instructions:
            self.nodes[node] = Node(node, self)
        self.G.vp.pos[node][:] = random(), random()

    def pre_unmake_node(self, node):
        """Remove the canvas instructions corresponding to node. Prepare last node to take its place."""
        instruction = self.nodes[node]

        if self.highlighted is instruction:
            self.highlighted = None
        if instruction in self._pinned:
            self._pinned.remove(instruction)
        elif instruction in self._selected:
            self._selected.remove(instruction)

        last = self.G.num_vertices() - 1
        if int(node) != last:
            last_vertex = self.G.vertex(last)
            last_node = self.nodes.pop(last_vertex)
            last_node_edges = tuple(self.edges.pop(edge) for edge in last_vertex.all_edges())
            self._last_node_to_pos = last_node, int(node), last_node_edges

        del self.nodes[node]
        self._node_instructions.remove_group(instruction.group_name)

    def post_unmake_node(self):
        """
        Swap the vertex descriptor of the last node and edge descriptors of all edges adjacent to
        it and fix our node and edge dictionary that used these descriptors. (Node deletion
        invalidated these descriptors.)
        """

        if self._last_node_to_pos is None:
            return

        node, pos, edge_instructions = self._last_node_to_pos

        node.vertex = self.G.vertex(pos)  # Update descriptor
        self.nodes[node.vertex] = node    # Update node dict

        for edge_instruction, edge in zip(edge_instructions, node.vertex.all_edges()):
            edge_instruction.s, edge_instruction.t = edge  # Update descriptor
            self.edges[edge] = edge_instruction            # Update edge dict

        # In case edge index order changed, we should correct edge color by re-freezing/unfreezing the source node.
        # It's important we do this after the above loop or recoloring could try to iterate over edges that have
        # invalid descriptors still.
        for edge_instruction in edge_instructions:
            s = self.nodes[edge_instruction.s]
            (s.freeze if self.G.vp.pinned[edge_instruction.s] else s.unfreeze)()

        self._last_node_to_pos = None

    def make_edge(self, edge):
        """Make new canvas instructions corresponding to edge."""
        with self._edge_instructions:
            self.edges[edge] = Edge(edge, self)

    def unmake_edge(self, edge):
        """Remove the canvas instructions corresponding to edge."""
        instruction = self.edges.pop(edge)
        self._edge_instructions.remove_group(instruction.group_name)

    @limit(UPDATE_INTERVAL)
    def update_canvas(self, *args):
        """Update node coordinates and edge colors."""
        self.background.size = self.size
        self.background.pos = self.pos

        self.transform_coords()

        for node in self.nodes.values():
            node.update()

        for edge in self.edges.values():
            edge.update()

    @redraw_canvas_after
    def step_layout(self, dt):
        sfdp_layout(self.G, pos=self.G.vp.pos, pin=self.G.vp.pinned, **SFDP_SETTINGS)

    def transform_coords(self, x=None, y=None):
        """
        Transform vertex coordinates to canvas coordinates.  If no specific coordinate is passed
        transform all coordinates and set to self.coords.
        """

        if x is not None:
            return ((x * self.scale + self.offset_x) * self.width,
                    (y * self.scale + self.offset_y) * self.height)

        self.coords = coords = self.G.vp.pos.get_2d_array((0, 1)).T
        np.multiply(coords, self.scale, out=coords)
        np.add(coords, (self.offset_x, self.offset_y), out=coords)
        np.multiply(coords, (self.width, self.height), out=coords)

    def invert_coords(self, x, y, delta=False):
        """Transform canvas coordinates to vertex coordinates."""
        off_x, off_y = (0, 0) if delta else (self.offset_x, self.offset_y)
        return (x / self.width - off_x) / self.scale, (y / self.height - off_y) / self.scale

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return

        touch.grab(self)
        self._touches.append(touch)
        self._mouse_pos_disabled = True

        if touch.button == 'right':
            touch.multitouch_sim = True
            return True

        if self.ctrl_pressed:
            if self.highlighted is not None:
                if self.highlighted in self._pinned:
                    self._pinned.remove(self.highlighted)
                elif self.highlighted in self._selected:
                    self._selected.remove(self.highlighted)  # This order is important else
                    self._pinned.add(self.highlighted)       # node color will be incorrect.
                else:
                    self._selected.add(self.highlighted)
            return True

        if self.is_selecting:
            self.is_drag_select = True
            self.highlighted = None

        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        self._touches.remove(touch)
        self._mouse_pos_disabled = False
        self.is_drag_select = False

    @redraw_canvas_after
    def on_touch_move(self, touch):
        """Zoom if multitouch, else if a node is highlighted, drag it, else move the entire graph."""

        if touch.grab_current is not self:
            return

        if len(self._touches) > 1:
            return self.transform_on_touch(touch)

        if touch.button == 'right' or self.ctrl_pressed:
            return

        if self.is_drag_select:
            return self.on_drag_select(touch)

        if self._selected:
            dx, dy = self.invert_coords(touch.dx, touch.dy, delta=True)
            for node in self._selected:
                x, y = self.G.vp.pos[node.vertex]
                self.G.vp.pos[node.vertex][:] = x + dx, y + dy
            return True

        if self.highlighted is not None:
            self.G.vp.pos[self.highlighted.vertex][:] = *self.invert_coords(touch.x, touch.y),
            return True

        self.offset_x += touch.dx / self.width
        self.offset_y += touch.dy / self.height
        return True

    def transform_on_touch(self, touch):
        ax, ay = self._touches[-2].pos  # Anchor coords
        x, y = self.invert_coords(ax, ay)

        cx = (touch.x - ax) / self.width
        cy = (touch.y - ay) / self.height
        current_length = (cx**2 + cy**2)**.5

        px = (touch.px - ax) / self.width
        py = (touch.py - ay) / self.height
        previous_length = (px**2 + py**2)**.5

        self.scale += current_length - previous_length

        # Make sure the anchor is a fixed point:
        x, y = self.transform_coords(x, y)
        self.offset_x += (ax - x) / self.width
        self.offset_y += (ay - y) / self.height

        return True

    def on_drag_select(self, touch):
        selected = self._selected
        rect = self.select_rect
        coords = self.coords

        rect.set_corners(touch.ox, touch.oy, touch.x, touch.y)
        coords_within = ((rect.min_x, rect.min_y) <= coords) & (coords <= (rect.max_x, rect.max_y))
        node_indices = np.argwhere(np.all(coords_within, axis=1))
        nodes = (self.nodes[self.G.vertex(index)] for index in node_indices)

        for node in selected.symmetric_difference(nodes):  # Note: Don't use update, we depend on
            if node in selected:                           # remove/add methods of subclassed set.
                selected.remove(node)
            elif node not in self._pinned:
                selected.add(node)

        return True

    @limit(UPDATE_INTERVAL)
    def on_mouse_pos(self, *args):
        mx, my = args[-1]

        if self._mouse_pos_disabled or not self.collide_point(mx, my):
            return

        if self.parent and any(widget.collide_point(mx, my)
                               for widget in self.parent.children if widget is not self):
            return

        # Check collision with already highlighted node first:
        if self.highlighted is not None and self.highlighted.collides(mx, my):
            return

        self.highlighted = None

        collisions = np.argwhere(np.all(np.isclose(self.coords, (mx, my), atol=BOUNDS), axis=1))
        if len(collisions):
            self.highlighted = self.nodes[self.G.vertex(collisions[0][0])]


if __name__ == "__main__":
    from dynamic_graph import EdgeCentricGASEP, EdgeFlipGASEP, Gravity


    class GraphApp(App):
        def build(self):
            # self.graph_canvas = GraphCanvas(graph_callback=EdgeCentricGASEP)

            G = gt.Graph()
            G.add_vertex(2)
            G.add_edge(0, 1)
            G.add_edge(1, 0)
            self.graph_canvas = GraphCanvas(G=G, graph_callback=Gravity)

            Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
            return self.graph_canvas

        def on_key_down(self, *args):
            # Will use key presses to change GraphCanvas's modes when testing; Ideally, we'd use
            # buttons in some other widget.
            if args[1] in (LSHIFT, RSHIFT):
                self.graph_canvas.is_selecting = True
            elif args[1] in (LCTRL, RCTRL):
                self.graph_canvas.ctrl_pressed = True
            elif args[1] == SPACE:
                self.graph_canvas.pause()

        def on_key_up(self, *args):
            if args[1] in (RSHIFT, LSHIFT):
                self.graph_canvas.is_selecting = False
            elif args[1] in (LCTRL, RCTRL):
                self.graph_canvas.ctrl_pressed = False

    GraphApp().run()
