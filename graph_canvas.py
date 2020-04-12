"""
Hold shift to drag-select vertices. Ctrl-click to select individual vertices, and again to pin them.
Space to pause/unpause the layout algorithm. Ctrl-Space to pause/unpause the Graph callback.
"""
from functools import wraps
from math import hypot
from random import random
import time

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.config import Config
from kivy.graphics.instructions import CanvasBase
from kivy.properties import OptionProperty, ObjectProperty
from kivy.uix.layout import Layout
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivymd.app import MDApp

import graph_tool as gt
from graph_tool.draw import random_layout, sfdp_layout
import numpy as np

from convenience_classes import Node, Edge, Selection, SelectedSet, PinnedSet, GraphInterface
from colormap import get_colormap
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

    rule(G) should return a callable that updates G when called.
    """
    tool = OptionProperty("Grab", options=TOOLS)
    adjacency_list = ObjectProperty(None)

    _mouse_pos_disabled = False

    _selected = SelectedSet()
    _pinned = PinnedSet()

    _touches = []

    _callback_paused = True
    _layout_paused = False

    delay = .05



    def __init__(self, *args, G=None, rule=None, multigraph=False, **kwargs):
        self.touch_down_dict = {'Grab': lambda touch: None,
                                'Select': self.select_touch_down,
                                'Pin': self.pin_touch_down,
                                'Add Node': self.add_node_touch_down,
                                'Delete Node': self.delete_node_touch_down,
                                'Add Edge': self.add_edge_touch_down,
                                'Delete Edge': self.delete_edge_touch_down}

        super().__init__(*args, **kwargs)

        self.resize_event = Clock.schedule_once(lambda dt: None, 0)  # Dummy event to save a conditional
        self.load_graph(G)  # Several attributes set/reset here

        self.bind(size=self._delayed_resize, pos=self._delayed_resize,
                  tool=self.retool, adjacency_list=self.populate_adjacency_list)
        Window.bind(mouse_pos=self.on_mouse_pos)

        self.update_layout = Clock.schedule_interval(self.step_layout, UPDATE_INTERVAL)

        self.load_rule(rule)

        self.multigraph = multigraph

    def load_graph(self, G=None, random=(50, 80)):
        # Halt layout and graph_rule
        layout_needs_unpause = False
        callback_needs_unpause = False
        if hasattr(self, 'update_layout') and not self._layout_paused:
            self.pause_layout()
            layout_needs_unpause = True
        if hasattr(self, 'rule_callback') and not self._callback_paused:
            self.pause_callback()
            callback_needs_unpause = True

        # Setup interface
        none_attrs = ['_highlighted', 'edges', 'nodes', 'background_color', '_background', 'select_rect',
                      '_edge_instructions', '_node_instructions', '_source_color', '_source_circle', 'coords',
                      '_source', 'rule_callback']
        self.__dict__.update(dict.fromkeys(none_attrs))

        self.offset_x = .25
        self.offset_y = .25
        self.scale = .5

        if G is None:
            self.G = GraphInterface(self, erdos_random_graph(*random)) if random else GraphInterface(self)
        else:
            self.G = GraphInterface(self, G)
        self.G.set_fast_edge_removal()

        if 'pos' not in self.G.vp:
            self.G.vp.pos = random_layout(self.G, (1, 1))
        self.G.vp.pinned = self.G.new_vertex_property('bool')

        self.set_node_colormap()
        self.set_edge_colormap()

        self.setup_canvas()
        self.update_canvas()
        self.populate_adjacency_list()

        # Resume layout and graph rule
        if layout_needs_unpause:
            self.pause_layout()
        if getattr(self, 'rule', None):
            self.load_rule(self.rule)
            if callback_needs_unpause:
                self.pause_callback()

    def populate_adjacency_list(self, *args):
        if self.adjacency_list is None:
            return

        self.adjacency_list.clear_widgets()
        for node in self.nodes.values():
            self.adjacency_list.add_widget(node.make_list_item())

    def set_node_colormap(self, property_=None, states=1, end=None):
        if property_ is None:
            self.node_colors = self.G.vp.default = self.G.new_vertex_property('bool')
        else:
            self.node_colors = property_
        self.node_colormap = get_colormap(states=states, end=end, for_nodes=True)

    def set_edge_colormap(self, property_=None, states=1, end=None):
        if property_ is None:
            self.edge_colors = self.G.ep.default = self.G.new_edge_property('bool')
        else:
            self.edge_colors =  property_
        self.edge_colormap = get_colormap(states=states, end=end, for_nodes=False)

    def load_rule(self, rule):
        self.rule = rule
        if rule is None:
            return

        if not self._callback_paused:
            self.pause_callback()

        self.rule_callback = rule(self.G)
        self.update_graph = Clock.schedule_interval(self.callback, 0)
        self.update_graph.cancel()

    def previous_state(self, node):
        """Return a highlighted node to its previous state."""
        if node in self._selected:
            node.freeze(SELECTED_COLOR)
        elif node in self._pinned:
            node.freeze(PINNED_COLOR)
        else:
            node.unfreeze()

    @redraw_canvas_after
    def callback(self, dt):
        self.rule_callback()

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, node):
        """Freezes highlighted nodes or returns un-highlighted nodes to the proper color."""
        lit = self.highlighted
        if lit is not None and lit is not self.source:
            self.previous_state(lit)

        if node is not None:
            node.freeze(HIGHLIGHTED_NODE)

        self._highlighted = node

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, node):
        source = self.source
        if source is not None:
            self._source_color.a = 0
            self.previous_state(source)

        if node is not None:
            node.freeze(HIGHLIGHTED_NODE)
            self._source_circle.circle = *self.coords[int(node.vertex)], SOURCE_RADIUS
            self._source_color.a = 1

        self._source = node

    def _delayed_resize(self, *args):
        self.resize_event.cancel()
        self.resize_event = Clock.schedule_once(self.update_canvas, self.delay)

    def retool(self, instance, value):
        if value == 'Select':
            self.select_rect.set_corners()
        self.source = None

    def pause_layout(self):
        self._layout_paused = not self._layout_paused
        if self._layout_paused:
            self.update_layout.cancel()
        else:
            self.update_layout()

    def pause_callback(self):
        self._callback_paused = not self._callback_paused
        if self.rule_callback is not None:
            if self._callback_paused:
                self.update_graph.cancel()
            else:
                self.update_graph()

    def setup_canvas(self):
        """Populate the canvas with the initial instructions."""
        self.canvas.clear()

        with self.canvas.before:
            self.background_color = Color(*BACKGROUND_COLOR)
            self._background = Rectangle(size=self.size, pos=self.pos)

        self._edge_instructions = CanvasBase()
        with self._edge_instructions:
            self.edges = {edge: Edge(edge, self) for edge in self.G.edges()}
        self.canvas.add(self._edge_instructions)

        self._node_instructions = CanvasBase()
        with self._node_instructions:
            self._source_color = Color(*SOURCE_COLOR)
            self._source_circle = Line(width=SOURCE_WIDTH)
            self.nodes = {vertex: Node(vertex, self) for vertex in self.G.vertices()}
        self.canvas.add(self._node_instructions)

        with self.canvas.after:
            self.select_rect = Selection()
            Color(1, 1, 1, 1)

    @limit(UPDATE_INTERVAL)
    def update_canvas(self, dt=None):  # dt for use by kivy Clock
        """Update node coordinates and edge colors."""
        if self.resize_event.is_triggered:
            return

        self._background.size = self.size
        self._background.pos = self.pos

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

    def select_touch_down(self, touch=None):
        if self.highlighted is not None and self.highlighted not in self._pinned:
            if self.highlighted in self._selected:
                self._selected.remove(self.highlighted)
            else:
                self._selected.add(self.highlighted)

    def pin_touch_down(self, touch=None):
        if self.highlighted is not None:
            if self.highlighted in self._pinned:
                self._pinned.remove(self.highlighted)
            else:
                if self.highlighted in self._selected:
                    self._selected.remove(self.highlighted)
                self._pinned.add(self.highlighted)

    @redraw_canvas_after
    def add_node_touch_down(self, touch):
        if self.highlighted is None:
            vertex = self.G.add_vertex(1)
            self.G.vp.pos[vertex][:] = self.invert_coords(touch.x, touch.y)
            self.highlighted = self.nodes[vertex]

    @redraw_canvas_after
    def delete_node_touch_down(self, touch=None):
         if self.highlighted is not None:
            self.G.remove_vertex(self.highlighted.vertex)

    @redraw_canvas_after
    def add_edge_touch_down(self, touch=None):
        if self.highlighted is None:
            self.source = None
        else:
            if self.source is None:
                self.source = self.highlighted
            else:
                if self.multigraph or self.G.edge(self.source.vertex, self.highlighted.vertex) is None:
                    self.G.add_edge(self.source.vertex, self.highlighted.vertex)
                self.source = None

    @redraw_canvas_after
    def delete_edge_touch_down(self, touch=None):
        if self.highlighted is None:
            self.source = None
        else:
            if self.source is None:
                self.source = self.highlighted
            else:
                edge = self.G.edge(self.source.vertex, self.highlighted.vertex)
                if edge is not None:
                    self.G.remove_edge(edge)
                self.source = None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return

        touch.grab(self)
        self._touches.append(touch)
        self._mouse_pos_disabled = True

        if touch.button == 'right':
            touch.multitouch_sim = True
            # We're going to change the color of multitouch dots to match our color scheme:
            with Window.canvas.after:
                touch.ud._drawelement = _, ellipse = Color(*HIGHLIGHTED_EDGE), Ellipse(size=(20, 20), segments=15)
            ellipse.pos = touch.x - 10, touch.y - 10

            return True

        highlighted = self.highlighted

        self.touch_down_dict[self.tool](touch)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return
        touch.ungrab(self)
        self._touches.remove(touch)
        self._mouse_pos_disabled = False
        self.select_rect.color.a = 0

    @redraw_canvas_after
    def on_touch_move(self, touch):
        """Zoom if multitouch, else if a node is highlighted, drag it, else move the entire graph."""

        if touch.grab_current is not self:
            return

        if len(self._touches) > 1:
            return self.transform_on_touch(touch)

        if touch.button == 'right' or self.tool not in ('Select', 'Grab'):
            return

        if self.tool == 'Select':
            self.select_rect.color.a = SELECT_RECT_COLOR[-1]
            return self.on_drag_select(touch)

        if self._selected:
            dx, dy = self.invert_coords(touch.dx, touch.dy, delta=True)
            for node in self._selected:
                x, y = self.G.vp.pos[node.vertex]
                self.G.vp.pos[node.vertex][:] = x + dx, y + dy
            return True

        if self.highlighted is not None:
            self.G.vp.pos[self.highlighted.vertex][:] = self.invert_coords(touch.x, touch.y)
            return True

        self.offset_x += touch.dx / self.width
        self.offset_y += touch.dy / self.height
        return True

    def transform_on_touch(self, touch):
        ax, ay = self._touches[-2].pos  # Anchor coords
        x, y = self.invert_coords(ax, ay)

        cx = (touch.x - ax) / self.width
        cy = (touch.y - ay) / self.height
        current_length = hypot(cx, cy)

        px = (touch.px - ax) / self.width
        py = (touch.py - ay) / self.height
        previous_length = hypot(px, py)

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

        if self._mouse_pos_disabled or self.coords is None or not self.collide_point(mx, my):
            return

        if (self.adjacency_list
            and not self.adjacency_list.is_hidden
            and any(widget.collide_point(mx, my) for widget in self.walk()
                    if widget is not self and not isinstance(widget, Layout))):
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

    LSHIFT, RSHIFT = 304, 13
    LCTRL, RCTRL   = 305, 306
    SPACE          = 32


    class GraphApp(MDApp):
        def build(self):
            # self.graph_canvas = GraphCanvas(rule=EdgeCentricGASEP)

            # self.graph_canvas = GraphCanvas(rule=EdgeFlipGASEP)

            G = gt.Graph()
            G.add_vertex(2)
            G.add_edge(0, 1)
            G.add_edge(1, 0)
            self.graph_canvas = GraphCanvas(G=G, rule=Gravity)

            Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
            return self.graph_canvas

        def on_key_down(self, *args):
            if args[1] in (LSHIFT, RSHIFT):
                self.graph_canvas.tool = 'Select'
            elif args[1] in (LCTRL, RCTRL):
                self.graph_canvas.tool = 'Pin'
            elif args[1] == SPACE:
                if self.graph_canvas.tool == 'Pin':
                    self.graph_canvas.pause_callback()
                else:
                    self.graph_canvas.pause_layout()

        def on_key_up(self, *args):
            if args[1] in (RSHIFT, LSHIFT, LCTRL, RCTRL):
                self.graph_canvas.tool = 'Grab'


    GraphApp().run()
