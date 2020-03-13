"""Constants for graph widget."""

SFDP_SETTINGS = dict(init_step=0.005, # move step; increase for sfdp to converge more quickly
                     K=0.5,           # preferred edge length
                     C=0.3,           # relative strength repulsive forces
                     p=2.0,           # repulsive force exponent
                     max_iter=2)

BACKGROUND_COLOR  =     0,     0,     0,   1
NODE_COLOR        = 0.027, 0.292, 0.678,   1
EDGE_COLOR        =  0.16, 0.176, 0.467, 0.8
HEAD_COLOR        =  0.26, 0.276, 0.567,   1
HIGHLIGHTED_NODE  = 0.758, 0.823,  0.92,   1
HIGHLIGHTED_EDGE  = 0.760, 0.235, 0.239,   1
HIGHLIGHTED_HEAD  = 0.770, 0.245, 0.249,   1
PINNED_COLOR      = 0.770, 0.455, 0.350,   1
SELECT_RECT_COLOR =     1,     1,     1, 0.8
SELECTED_COLOR    = 0.514, 0.646, 0.839,   1

NODE_RADIUS  = 3
BOUNDS       = NODE_RADIUS * 2

NODE_WIDTH   = 3
EDGE_WIDTH   = 2
SELECT_WIDTH = 1.2

LSHIFT, RSHIFT = 304, 13
LCTRL, RCTRL   = 305, 306
SPACE          = 32

UPDATE_INTERVAL = 1/30