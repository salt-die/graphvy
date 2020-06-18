from itertools import chain
from .key import Key

SHIFT, CTRL = (303, 304), (305, 306)

EXACT = map(Key, (13,  9, 275, 276, 278, 279))
ANY_MODS = (Key(code, Key.ANY, Key.ANY) for code in (273, 274, 8, 127))

KEYS \
 = ENTER, TAB, RIGHT, LEFT, HOME, END, UP, DOWN, BACKSPACE, DELETE \
 = tuple(chain(EXACT, ANY_MODS))

del EXACT; del ANY_MODS

CUT  = Key(120, False, True)  # <ctrl + c>
COPY = Key(99 , False, True)  # <ctrl + x>
REDO = Key(122,  True, True)  # <ctrl + shift + z>

SELECT_LEFT  = Key(276, True, False)  # <shift + left>
SELECT_RIGHT = Key(275, True, False)  # <shift + right>
SELECT_HOME  = Key(278, True, False)  # <shift + home>
SELECT_END   = Key(279, True, False)  # <shift + end>