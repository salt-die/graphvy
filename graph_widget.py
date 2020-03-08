### TODO: Drag-select vertices
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
HIGHLIGHTED_COLOR = 0.5135, 0.646 , 0.839, 1

NODE_RADIUS = 3; BOUNDS = NODE_RADIUS * 2
NODE_WIDTH = 3
EDGE_WIDTH = 2

def collides(mx, my, x, y):
    """Return true if x, y in coords bounding box."""
    return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS


class Node(Line):
    def __init__(self, pos, x, y):
        self.pos = pos
        self.frozen_pos = (*pos,)
        self.color = Color(*NODE_COLOR)
        super().__init__(circle=(x, y, NODE_RADIUS), width=NODE_WIDTH)

    def freeze(self, x=None, y=None):
        self.frozen_pos = (*self.pos,) if x is None else (x, y)

    def reset(self):
        self.pos[:] = self.frozen_pos


class GraphCanvas(Widget):
    """Dynamic graph layout widget.  Layout updates as graph changes."""

    _mouse_pos_disabled = False
    _highlighted = None
    _touches = []

    offset_x = .25
    offset_y = .25
    scale = .5

    def __init__(self, G=None, pos=None, graph_callback=None, *args, **kwargs):
        self.G = gt.generation.graph() if G is None else G
        self.G_pos = random_layout(G, (1, 1)) if pos is None else pos

        super().__init__(*args, **kwargs)

        self.setup_canvas()

        self.bind(size=self.update_canvas, pos=self.update_canvas)
        Window.bind(mouse_pos=self.on_mouse_pos,
                    on_key_down=self.on_key_down,
                    on_key_up=self.on_key_up)

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

    def step_layout(self, dt):
        sfdp_layout(self.G, pos=self.G_pos, K=K, init_step=STEP, max_iter=1)

        if self.highlighted is not None:
            self.highlighted.reset()

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

    def setup_canvas(self, *args):
        self.canvas.clear()
        with self.canvas.before:
            Color(*BACKGROUND_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.coords = coords = dict(zip(self.G.vertices(), self.transform_coords()))

        self.nodes = []
        self.edges = []
        with self.canvas:
            Color(*EDGE_COLOR)
            for u, v in self.G.edges():
                self.edges.append(Line(points=[*coords[u], *coords[v]], width=EDGE_WIDTH))

            for vertex, (x, y) in coords.items():
                self.nodes.append(Node(self.G_pos[int(vertex)], x, y))

    def transform_coords(self, x=None, y=None):
        """Transform vertex coordinates to canvas coordinates."""

        if x is not None:
            return ((x * self.scale + self.offset_x) * self.width,
                    (y * self.scale + self.offset_y) * self.height)

        arr = self.G_pos.get_2d_array((0, 1)).T
        np.multiply(arr, self.scale, out=arr)
        np.add(arr, (self.offset_x, self.offset_y), out=arr)
        np.multiply(arr, (self.width, self.height), out=arr)
        return arr

    def invert_coords(self, x, y):
        """Transform canvas coordinates to vertex coordinates."""

        return (((x / self.width) - self.offset_x) / self.scale,
                ((y / self.height) - self.offset_y) / self.scale)

    def on_touch_down(self, touch):
        self._mouse_pos_disabled = True
        self._touches.append(touch)
        return True

    def on_touch_up(self, touch):
        self._mouse_pos_disabled = False
        self._touches.remove(touch)

    def on_touch_move(self, touch):
        """
        Zoom if multitouch, else if a node is highlighted, drag it, else move the entire graph.
        """

        if len(self._touches) > 1:
            return self.transform_on_touch(touch)

        if self.highlighted is not None:
            x, y = self.invert_coords(touch.x, touch.y)
            self.highlighted.freeze(x, y)
            return True

        self.offset_x += touch.dx / self.width
        self.offset_y += touch.dy / self.height
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

    def on_key_up(self, *args):
        print(args)

    def on_key_down(self, *args):
        # TODO: SHIFT will activate selection mode, allowing one to drag-select vertices
        print(args)


if __name__ == "__main__":
    class GraphApp(App):
        def build(self):
            g = gt.generation.random_graph(50, lambda:(random.randint(1, 2), random.randint(1, 2)))
            return GraphCanvas(g)

    GraphApp().run()