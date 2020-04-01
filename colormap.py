import palettable
import numpy as np
from constants import NODE_COLOR, EDGE_COLOR


class ConstantMap:
    def __init__(self, color):
        self.color = color

    def __getitem__(self, key):
        return self.color


class ContinuousMap:
    def __init__(self, colormap, start, end):
        self.scale = end - start
        self.start = start
        self.colormap = colormap

    def __getitem__(self, key):
        return self.colormap((key - self.start) / self.scale)


def get_colormap(states=1, end=None, *, for_nodes=True):
    """
    Returns a color map for an arbitrary number of states, or a continuous range of states if `end` is not None.
    Note that if there are 10 or less states the colors are not sequential.
    """
    if end is None:
        if states == 1:
            return ConstantMap(NODE_COLOR if for_nodes else EDGE_COLOR)
        if states <= 10:
            colors = getattr(palettable.cartocolors.qualitative, f'Vivid_{states}').mpl_colors
            return [(*color, 1) for color in colors]
        return palettable.cartocolors.sequential.Emrld_7.mpl_colormap(np.linspace(0, 1, states))
    return ContinuousMap(palettable.cartocolors.sequential.Emrld_7.mpl_colormap, states, end)
