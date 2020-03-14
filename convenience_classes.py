"""Convenience classes for graph widget."""
from kivy.graphics import Color, Line

from constants import *


class Node(Line):
    __slots__ = 'color', 'vertex', 'canvas'

    def __init__(self, vertex, canvas):
        self.color = Color(*NODE_COLOR)
        self.vertex = vertex
        self.canvas = canvas

        super().__init__(circle=(0, 0, NODE_RADIUS), width=NODE_WIDTH)

    def freeze(self, color):
        self.canvas.G.vp.pinned[self.vertex] = 1
        self.color.rgba = color

    def unfreeze(self):
        self.canvas.G.vp.pinned[self.vertex] = 0
        self.color.rgba = NODE_COLOR

    def collides(self, mx, my):
        x, y = self.canvas.coords[self.vertex]
        return x - BOUNDS <= mx <= x + BOUNDS and y - BOUNDS <= my <= y + BOUNDS


class Selection(Line):
    __slots__ = 'color', 'min_x', 'max_x', 'min_y', 'max_y'

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