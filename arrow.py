"""
A Line canvas instruction with an arrow at the end.
"""
import numpy as np
from math import atan2, sin, cos  # Should be slightly faster than numpy for non-arrays.

from kivy.graphics import Color, Line
from kivy.uix.widget import Widget

BASE = np.array([[-3, 0], [-6, 1], [-6, -1]], dtype=float)
ROTATION = np.zeros((2, 2), dtype=float)  # Used as a buffer for Triangle rotation matrix
BUFFER = np.zeros((3, 2), dtype=float)    # Buffer for matmul with ROTATION

class Triangle(Line):
    __slots__ = 'base', 'color', 'group_name'

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
        self.base =  BASE * size
        self.group_name = str(id(self)) if group_name is None else group_name

        self.color = Color(*color, group=self.group_name)
        super().__init__(close=True, width=width, group=self.group_name)

    def update(self, x1, y1, x2, y2):
        theta = atan2(y2 - y1, x2 - x1)

        ROTATION[(0, 1), (0, 1)] = cos(theta)

        sine = sin(theta)
        ROTATION[0, 1] = sine
        ROTATION[1, 0] = -sine

        np.matmul(self.base, ROTATION, out=BUFFER)
        np.add(BUFFER, (x2, y2), out=BUFFER)

        self.points = *BUFFER.reshape(1, -1)[0],

    def resize(self, size):
        self.base = BASE * size


class Arrow(Line):
    __slots__ = 'group_name', 'color', 'head'

    def __init__(self, line_color, head_color, width, head_size):
        self.group_name = str(id(self))

        self.color = Color(*line_color, group=self.group_name)
        super().__init__(width=width, group=self.group_name)

        self.head = Triangle(color=head_color, width=width, size=head_size, group_name=self.group_name)

    def update(self, x1, y1, x2, y2):
        self.points = x1, y1, x2, y2
        self.head.update(x1, y1, x2, y2)

    def resize_head(self, size):
        self.head.resize(size)
