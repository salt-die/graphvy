"""
Hold shift to drag-select vertices.
"""
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.vector import Vector
from kivy.uix.widget import Widget
from kivy.core.window import Window

import graph_tool as gt
from graph_tool.draw import random_layout, sfdp_layout

import numpy as np

STEP = 0.005 # move step
K = 0.5      # preferred edge length

BACKGROUND_COLOR = 0, 0, 0, 1
NODE_COLOR = .027, .292, .678, 1
EDGE_COLOR = .16, .176, .467, 1
HIGHLIGHTED_COLOR = 0.5135, 0.646, 0.839, 1
SELECT_RECT_COLOR = 1, 1, 1, .8
SELECTED_COLOR = 0.5135, 0.646, 0.839, 1

NODE_RADIUS = 3; BOUNDS = NODE_RADIUS * 2
NODE_WIDTH = 3
EDGE_WIDTH = 2
SELECT_WIDTH = 1.2

def collides(mx, my, x, y):
    """Return true if mx, my (mouse x, y) in (x, y)'s bounding box."""
    return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS


class Node(Line):
    def __init__(self, pos, x, y):
        self.color = Color(*NODE_COLOR)

        self.pos = pos # pos is a reference to the mutable vertex position
        self.frozen_pos = (*pos,) # if a node is frozen, this will be its position

        super().__init__(circle=(x, y, NODE_RADIUS), width=NODE_WIDTH)

    def freeze(self):
        self.frozen_pos = (*self.pos,)

    def reset(self):
        self.pos[:] = self.frozen_pos


class Selection(Line):
    def __init__(self, *args, **kwargs):
        self.color = Color(*SELECT_RECT_COLOR)

        super().__init__(points=[0, 0, 0, 0, 0, 0, 0, 0], width=SELECT_WIDTH, close=True)

        self.set_corners()

    def set_corners(self, x1=0, y1=0, x2=0, y2=0):
        min_x, max_x = self.min_x, self.max_x = (x1, x2) if x1 <= x2 else (x2, x1)
        min_y, max_y = self.min_y, self.max_y = (y1, y2) if y1 <= y2 else (y2, y1)

        self.points = min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y

    def __contains__(self, coord):
        """Return True if coord is within the rectangle."""
        x, y = coord
        return self.min_x <= x <= self.max_x and self.min_y <= y <= self.max_y


class Selected(list):
    """List that correctly colors nodes that are added to it."""
    def append(self, node):
        super().append(node)
        node.freeze()
        node.color.rgba = SELECTED_COLOR

    def __del__(self):
        for node in self:
            node.color.rgba = NODE_COLOR


class GraphCanvas(Widget):
    """Dynamic graph layout widget.  Layout updates as graph changes."""

    _mouse_pos_disabled = False
    _highlighted = None # For highlighted property.
    _selected = Selected() # List of selected nodes for dragging multiple nodes.
    _pinned = [] # List of nodes that won't be moved by layout algorithm.

    _touches = []

    offset_x = .25
    offset_y = .25
    scale = .5

    is_selecting = False
    _drag_selection = False # For is_drag_select property.

    def __init__(self, *args, G=None, pos=None, graph_callback=None, **kwargs):
        self.G = gt.Graph() if G is None else G
        self.G_pos = random_layout(G, (1, 1)) if pos is None else pos

        super().__init__(*args, **kwargs)

        # Following attributes set in setup_canvas:
        self.rect = None
        self.edges = None
        self.nodes = None
        self.select_rect = None
        self.setup_canvas()

        self.coords = None # Set in update_canvas for edges to easily reference node coordinates.

        self.bind(size=self.update_canvas, pos=self.update_canvas)
        Window.bind(mouse_pos=self.on_mouse_pos)

        self.update_layout = Clock.schedule_interval(self.step_layout, 1/30)

        if graph_callback is not None:
            self.update_graph = Clock.schedule_interval(graph_callback)

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, node):
        """Freezes highlighted nodes."""
        if self.highlighted is not None:
            self.highlighted.color.rgba = NODE_COLOR
        if node is not None:
            node.freeze()
            node.color.rgba = HIGHLIGHTED_COLOR
        self._highlighted = node

    @property
    def is_drag_select(self):
        return self._drag_selection

    @is_drag_select.setter
    def is_drag_select(self, boolean):
        self._drag_selection = boolean
        self.select_rect.set_corners()
        self.select_rect.color.a = int(boolean) * SELECT_RECT_COLOR[-1]

    def step_layout(self, dt):
        sfdp_layout(self.G, pos=self.G_pos, K=K, init_step=STEP, max_iter=1)

        if self.highlighted is not None:
            self.highlighted.reset()

        for node in self._selected:
            node.reset()

        self.update_canvas()

    def update_canvas(self, *args):
        if args:
            self.rect.size = self.size
            self.rect.pos = self.pos

        self.coords = coords = dict(zip(self.G.vertices(), self.transform_coords()))

        for node, (x, y) in zip(self.nodes, coords.values()):
            node.circle = x, y, NODE_RADIUS

        for edge, (u, v) in zip(self.edges, self.G.edges()):
            edge.points = *coords[u], *coords[v]

    def setup_canvas(self):
        self.canvas.clear()

        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        with self.canvas:
            Color(*EDGE_COLOR)
            self.edges = [Line(points=[0, 0, 0, 0], width=EDGE_WIDTH) for u, v in self.G.edges()]
            self.nodes = [Node(pos, x, y) for pos, (x, y) in zip(self.G_pos, self.transform_coords())]

        with self.canvas.after:
            self.select_rect = Selection()

    def transform_coords(self, x=None, y=None):
        """
        Transform vertex coordinates to canvas coordinates.  Return the entire array of vertex
        coordinates if no specific coordinate is passed.
        """

        if x is not None:
            return ((x * self.scale + self.offset_x) * self.width,
                    (y * self.scale + self.offset_y) * self.height)

        arr = self.G_pos.get_2d_array((0, 1)).T
        np.multiply(arr, self.scale, out=arr)
        np.add(arr, (self.offset_x, self.offset_y), out=arr)
        np.multiply(arr, (self.width, self.height), out=arr)
        return arr

    def invert_coords(self, x, y, delta=False):
        """Transform canvas coordinates to vertex coordinates."""
        off_x, off_y = (0, 0) if delta else (self.offset_x, self.offset_y)

        return ((x / self.width) - off_x) / self.scale, ((y / self.height) - off_y) / self.scale

    def on_touch_down(self, touch):
        self._touches.append(touch)

        self._mouse_pos_disabled = True

        if self.is_selecting:
            self.is_drag_select = True
            self.highlighted = None

        return True

    def on_touch_up(self, touch):
        self._touches.remove(touch)

        if not self._selected:
            self._mouse_pos_disabled = False

        self.is_drag_select = False

    def on_touch_move(self, touch):
        """
        Zoom if multitouch, else if a node is highlighted, drag it, else move the entire graph.
        """
        if len(self._touches) > 1:
            return self.transform_on_touch(touch)

        if self.is_drag_select:
            return self.drag_select(touch)

        if self._selected:
            dx, dy = self.invert_coords(touch.dx, touch.dy, delta=True)
            for node in self._selected:
                fx, fy = node.frozen_pos
                node.frozen_pos = fx + dx, fy + dy
            return True

        if self.highlighted is not None:
            self.highlighted.frozen_pos = self.invert_coords(touch.x, touch.y)
            return True

        self.offset_x += touch.dx / self.width
        self.offset_y += touch.dy / self.height
        return True

    def drag_select(self, touch):
        self.select_rect.set_corners(touch.ox, touch.oy, touch.x, touch.y)

        self._selected = Selected()
        for node, coord in zip(self.nodes, self.coords.values()):
            if coord in self.select_rect:
                self._selected.append(node)

        return True

    def transform_on_touch(self, touch):
        ax, ay = self._touches[-2].pos # Anchor coords
        x, y = self.invert_coords(ax, ay)

        anchor = Vector(self._touches[-2].spos)
        current = Vector(touch.spos) - anchor
        previous = Vector(touch.psx, touch.psy) - anchor
        self.scale += current.length() - previous.length()

        x, y = self.transform_coords(x, y)
        # Make sure the anchor is a fixed point:
        self.offset_x += (ax - x) / self.width
        self.offset_y += (ay - y) / self.height

        return True

    def on_mouse_pos(self, *args):
        if self._mouse_pos_disabled:
            return

        mx, my = args[-1]

        # Keeping track of highlighted node should prevent us from having to check collisions
        # between nodes and touch too often.
        if self.highlighted is not None:
            x, y = self.transform_coords(*self.highlighted.pos)
            if collides(mx, my, x, y):
                return
            self.highlighted = None

        # Now we loop through all nodes until we find a collision with mouse:
        for node, (x, y) in zip(self.nodes, self.coords.values()):
            if collides(mx, my, x, y):
                self.highlighted = node
                return


if __name__ == "__main__":
    class GraphApp(App):
        def build(self):
            G = gt.generation.random_graph(50, lambda: (random.randint(1, 2), random.randint(1, 2)))
            self.GC = GraphCanvas(G=G)
            Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
            return self.GC

        def on_key_down(self, *args):
            """Will use key presses to change GraphCanvas's modes when testing; Ideally, we'd use
               buttons in some other widget..."""
            if args[1] == 304: # shift
                self.GC.is_selecting = True

        def on_key_up(self, *args):
            if args[1] == 304: # shift
                self.GC.is_selecting = False


    GraphApp().run()
