from kivy.utils import get_hex_from_color
from pygments.style import Style
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, String, Text, Token, Generic

#from ..constants import NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, EDGE_COLOR, HIGHLIGHTED_EDGE

NODE_COLOR        = 0.051, 0.278, 0.631,   1
HIGHLIGHTED_NODE  = 0.758, 0.823,  0.92,   1
SELECTED_COLOR    = 0.514, 0.646, 0.839,   1
PINNED_COLOR      = 0.770, 0.455, 0.350,   1
EDGE_COLOR        =  0.16, 0.176, 0.467, 0.8
HIGHLIGHTED_EDGE  = 0.760, 0.235, 0.239,   1

NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, EDGE_COLOR, HIGHLIGHTED_EDGE \
 = (get_hex_from_color(color[:-1])
    for color in (NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, EDGE_COLOR, HIGHLIGHTED_EDGE))


class GraphvyStyle(Style):
    styles = {Generic:                HIGHLIGHTED_NODE,
              Generic.Traceback:      HIGHLIGHTED_EDGE,
              Generic.Error:          PINNED_COLOR,
              Text:                   HIGHLIGHTED_NODE,

              Comment:                SELECTED_COLOR,
              Error:                  PINNED_COLOR,

              Keyword:                HIGHLIGHTED_EDGE,
              Keyword.Type:           HIGHLIGHTED_EDGE,
              Keyword.Namespace:      HIGHLIGHTED_EDGE,
              Keyword.Constant:       PINNED_COLOR,

              Name:                   HIGHLIGHTED_NODE,
              Name.Builtin.Pseudo:    SELECTED_COLOR,
              Name.Variable.Magic:    SELECTED_COLOR,

              Name.Builtin:           NODE_COLOR,
              Name.Class:             NODE_COLOR,
              Name.Function:          NODE_COLOR,

              Name.Decorator:         PINNED_COLOR,
              Name.Exception:         PINNED_COLOR,

              Number:                 SELECTED_COLOR,

              Operator:               EDGE_COLOR,
              Operator.Word:          HIGHLIGHTED_EDGE,

              String:                 PINNED_COLOR,
              String.Affix:           HIGHLIGHTED_EDGE,
              String.Escape:          HIGHLIGHTED_EDGE,
              String.Interpol:        HIGHLIGHTED_EDGE,

              Token.Punctuation:      EDGE_COLOR}
