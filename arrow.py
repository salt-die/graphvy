"""
A Line canvas instruction with an arrow at the end.
"""
from math import atan2, cos, sin

from kivy.graphics import Color, Line
from kivy.uix.widget import Widget


class Triangle(Line):
    __slots__ = 'x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'color', 'group_name'

    def __init__(self, color, width, size, group_name=None):
        """
        Triangle points are: (-3, 0), (-6, 1), (-6, -1). Looks like:
        (Two characters per x unit, One line per y unit, O is origin)

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

        if group_name is None:
            self.group_name = str(id(self))
        else:
            self.group_name = group_name

        self.color = Color(*color, group=self.group_name)
        super().__init__(close=True, width=width, group=self.group_name)


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
    __slots__ = 'group_name', 'color', 'head'

    def __init__(self,
                 line_color,
                 head_color,
                 width,
                 head_size):

        self.group_name = str(id(self))
        self.color = Color(*line_color, group=self.group_name)
        super().__init__(width=width, group=self.group_name)

        self.head = Triangle(color=head_color,
                             width=width,
                             size=head_size,
                             group_name=self.group_name)

    def update(self, x1, y1, x2, y2):
        self.points = x1, y1, x2, y2
        self.head.update(x1, y1, x2, y2)
