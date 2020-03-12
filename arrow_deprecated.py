"""
Temporary file for a Line canvas instruction with an arrow at the end.  For directed edges in
graph_widget.py.  We still need to unvectorized it and refactor a bit; this is just a
proof-of-concept.
"""

from kivy.app import App
from kivy.graphics import Color, Line
from kivy.uix.widget import Widget

import numpy as np

HEAD_COLOR = 0.26, 0.276, 0.567, 1
EDGE_COLOR = 0.16, 0.176, 0.467, 1

def rotation_matrix(theta):
    return np.array([[np.cos(theta), np.sin(theta)],
                     [-np.sin(theta), np.cos(theta)]])

class Triangle(Line):
    base = np.array([[0,  0], [3, 1], [3,  -1]])

    def __init__(self, coords, size=1):
        self.base = size * self.base / 150
        self.coords = coords
        self.color = Color(*HEAD_COLOR)
        super().__init__(points=[0, 0, 0, 0, 0, 0], close=True, width=2)


    def update_points(self, size):
        theta = np.arctan2(*np.subtract.reduce(self.coords, axis=0)[::-1])
        new_points = (self.base @ rotation_matrix(theta) + self.coords[1]) * size
        self.points = new_points.flatten().tolist()


class Arrow(Line):
    def __init__(self, coords, size=1):
        self.coords = coords
        self.color = Color(*EDGE_COLOR)
        super().__init__(points=[0, 0, 0, 0], width=2)
        self.head = Triangle(coords)

    def update_points(self, size):
        self.points = (self.coords * size).flatten().tolist()
        self.head.update_points(size)


class TestArrows(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        with self.canvas:

            self.arrows = [Arrow(np.random.random((2, 2))) for _ in range(20)]

        self.bind(size=self.update_canvas, pos=self.update_canvas)


    def update_canvas(self, *args):
        for arrow in self.arrows:
            arrow.update_points(self.size)


if __name__ == '__main__':
    class ArrowsApp(App):
        def build(self):
            return TestArrows()

    ArrowsApp().run()