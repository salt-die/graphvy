"""
A Line canvas instruction with an arrow at the end.  For directed edges in
graph_widget.py.
"""
from math import atan2, cos, sin

from kivy.graphics import Color, Line
from kivy.uix.widget import Widget


class Triangle(Line):
    __slots__ = 'x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'color'

    def __init__(self, color, width, size):
        """
        Triangle points are: (-3, 0), (-6, 1), (-6, -1). Looks like:
        (Two characters per x, One line per y, O is origin)

                           |
               o           |
            ---------o-----O---
               o           |
                           |

        Tip is off origin so that arrow is less covered by nodes.
        """
        self.x1 = -3 * size
        self.y1 =  0 * size
        self.x2 = -6 * size
        self.y2 =  1 * size
        self.x3 = -6 * size
        self.y3 = -1 * size

        self.color = Color(*color)
        super().__init__(points=[0, 0, 0, 0, 0, 0], close=True, width=width)


    def update(self, x1, y1, x2, y2):
        theta = atan2(y2 - y1, x2 - x1)
        cosine, sine = cos(theta), sin(theta)

        # Rotate the base arrow by theta and move it to x2, y2
        px1 = self.x1 * cosine + self.y1 * -sine + x2
        py1 = self.x1 *  sine  + self.y1 * cosine + y2
        px2 = self.x2 * cosine + self.y2 * -sine + x2
        py2 = self.x2 *  sine  + self.y2 * cosine + y2
        px3 = self.x3 * cosine + self.y3 * -sine + x2
        py3 = self.x3 *  sine  + self.y3 * cosine + y2

        self.points = px1, py1, px2, py2, px3, py3


class Arrow(Line):
    __slots__ = 'color', 'head'

    def __init__(self, line_color, head_color, width, size=3):
        self.color = Color(*line_color)
        super().__init__(points=[0, 0, 0, 0], width=width)

        self.head = Triangle(color=head_color, width=width, size=size)

    def update(self, x1, y1, x2, y2):
        self.points = x1, y1, x2, y2
        self.head.update(x1, y1, x2, y2)


if __name__ == '__main__':
    from random import random
    from kivy.app import App

    HEAD_COLOR = 0.26, 0.276, 0.567, 1
    EDGE_COLOR = 0.16, 0.176, 0.467, 1


    class TestArrows(Widget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.bind(size=self.update_canvas, pos=self.update_canvas)

        def update_canvas(self, *args):
            self.canvas.clear()
            with self.canvas:
                for _ in range(20):
                    arrow = Arrow(EDGE_COLOR, HEAD_COLOR, width=2)
                    arrow.update(random() * self.width, random() * self.height,
                                 random() * self.width, random() * self.height)


    class ArrowsApp(App):
        def build(self):
            return TestArrows()

    ArrowsApp().run()