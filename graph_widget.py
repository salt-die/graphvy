"""
Hold shift to drag-select vertices. Ctrl-click to select individual vertices, and again to pin them.
Space to pause/unpause the layout algorithm. Ctrl-Space to pause/unpause the Graph callback.
"""
### TODO: path highlighter
### TODO: bezier lines (only when paused; computationally heavy)
### TODO: degree histogram
### TODO: hide/filter nodes
from functools import wraps
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.config import Config
from kivy.graphics.instructions import CanvasBase
from kivy.vector import Vector
from kivy.uix.widget import Widget
from kivy.core.window import Window

from graph_tool.draw import random_layout, sfdp_layout
import numpy as np

from convenience_classes import Node, Edge, Selection, SelectedSet, PinnedSet, GraphInterface
from constants import *

Config.set('input', 'mouse', 'mouse,multitouch_on_demand')


def redraw_canvas_after(func):
    """For methods that change vertex coordinates or edge colors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        results = func(*args, **kwargs)
        args[0].update_canvas()
        return results

    return wrapper


def limit(interval):
    def deco(func):
        """Limits how quickly a function can be called."""
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

    graph_callback(G) should return a function that updates G when called.
    """

    _mouse_pos_disabled = False

    _highlighted = None  # For highlighted property.
    _selected = SelectedSet(color=SELECTED_COLOR)
    _pinned = PinnedSet(color=PINNED_COLOR)

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
        self.G = GraphInterface(self) if G is None else GraphInterface(self, G)
        self.G.vp.pos = random_layout(self.G, (1, 1))
        self.G.vp.pinned = self.G.new_vertex_property('bool')

        super().__init__(*args, **kwargs)

        # Following attributes set in setup_canvas:
        self.edges = None
        self.nodes = None
        self.rect = None
        self.select_rect = None
        self.edge_instructions = None
        self.node_instructions = None
        self.setup_canvas()

        self.coords = None  # Set in transform_coords

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
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.edge_instructions = CanvasBase()
        with self.edge_instructions:
            self.edges = {edge: Edge(edge, self) for edge in self.G.edges()}
        self.canvas.add(self.edge_instructions)

        self.node_instructions = CanvasBase()
        with self.node_instructions:
            self.nodes = {vertex: Node(vertex, self) for vertex in self.G.vertices()}
        self.canvas.add(self.node_instructions)

        with self.canvas.after:
            self.select_rect = Selection()

    def make_node(self, node):
        """Make a new canvas instruction corresponding to node."""
        with self.node_instructions:
            self.nodes[node] = Node(node, self)

    def pre_unmake_node(self, node):
        """Remove the canvas instruction corresponding to node."""
        last = self.G.num_vertices() - 1
        if int(node) != last:
            self._last_node_to_pos = self.nodes[G.vertex(last)], int(node)
        else:
            self._last_node_to_pos = None
        instruction = self.nodes.pop(node)
        self.node_instructions.remove_group(instruction.group_name)

    def post_unmake_node(self):
        """Swap the vertex descriptor of the last node. (Node deletion invalidated it.)"""
        if self._last_node_to_pos is None:
            return
        node, pos = self._last_node_to_pos
        node.vertex = self.G.vertex(pos)
        self._last_node_to_pos = None

    def make_edge(self, edge):
        """Make a new canvas instruction corresponding to edge."""
        with self.edge_instructions:
            self.edges[edge] = Edge(edge, self)

    def unmake_edge(self, edge):
        """Remove the canvas instruction corresponding to edge."""
        instruction = self.edges.pop(edge)
        self.edge_instructions.remove_group(instruction.group_name)

    @limit(UPDATE_INTERVAL)
    def update_canvas(self, *args):
        """Update node coordinates and edge colors."""
        if args:
            self.rect.size = self.size
            self.rect.pos = self.pos

        self.transform_coords()
        coords = self.coords

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
        return (((x / self.width) - off_x) / self.scale,
                ((y / self.height) - off_y) / self.scale)

    @redraw_canvas_after
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
                    self._selected.remove(self.highlighted) # This order is important else
                    self._pinned.add(self.highlighted)      # node color will be incorrect.
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
        """
        Zoom if multitouch, else if a node is highlighted, drag it, else move the entire graph.
        """

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
            self.G.vp.pos[self.highlighted.vertex][:] = self.invert_coords(touch.x, touch.y)
            return True

        self.offset_x += touch.dx / self.width
        self.offset_y += touch.dy / self.height
        return True

    def on_drag_select(self, touch):
        selected = self._selected
        self.select_rect.set_corners(touch.ox, touch.oy, touch.x, touch.y)

        for node in self.nodes.values():
            coord = self.coords[int(node.vertex)]
            if node in selected:
                if coord not in self.select_rect:
                    selected.remove(node)
            else:
                if node not in self._pinned and coord in self.select_rect:
                    selected.add(node)

        return True

    def transform_on_touch(self, touch):
        ax, ay = self._touches[-2].pos  # Anchor coords
        x, y = self.invert_coords(ax, ay)

        anchor = Vector(self._touches[-2].pos) / self.size
        current = Vector(touch.pos) / self.size - anchor
        previous = Vector(touch.px, touch.py) / self.size - anchor
        self.scale += current.length() - previous.length()

        x, y = self.transform_coords(x, y)
        # Make sure the anchor is a fixed point:
        self.offset_x += (ax - x) / self.width
        self.offset_y += (ay - y) / self.height

        return True

    @limit(UPDATE_INTERVAL)
    def on_mouse_pos(self, *args):
        mx, my = args[-1]

        if self._mouse_pos_disabled or not self.collide_point(mx, my):
            return

        # Keeping track of highlighted node should prevent us from having to check collisions
        # between nodes and touch too often.
        if self.highlighted is not None and self.highlighted.collides(mx, my):
            return

        self.highlighted = None

        # Now we loop through all nodes until we find a collision with mouse:
        for node in self.nodes.values():
            if node.collides(mx, my):
                self.highlighted = node
                return


if __name__ == "__main__":
    import random
    import graph_tool as gt
    from dynamic_graph import EdgeCentricGASEP

    class GraphApp(App):
        def build(self):
            G = gt.generation.random_graph(50, lambda: (random.randint(1, 2), random.randint(1, 2)))
            self.GC = GraphCanvas(G=G, graph_callback=EdgeCentricGASEP)

            Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
            return self.GC

        def on_key_down(self, *args):
            """
            Will use key presses to change GraphCanvas's modes when testing; Ideally, we'd use
            buttons in some other widget.
            """
            if args[1] in (LSHIFT, RSHIFT):
                self.GC.is_selecting = True
            elif args[1] in (LCTRL, RCTRL):
                self.GC.ctrl_pressed = True
            elif args[1] == SPACE:
                self.GC.pause()

        def on_key_up(self, *args):
            if args[1] in (RSHIFT, LSHIFT):
                self.GC.is_selecting = False
            elif args[1] in (LCTRL, RCTRL):
                self.GC.ctrl_pressed = False

    GraphApp().run()
