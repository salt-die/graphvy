from kivy.utils import get_hex_from_color
from pygments.style import Style
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, String, Text, Token, Generic

from ..constants import NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, HIGHLIGHTED_EDGE

NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, HIGHLIGHTED_EDGE \
 = (get_hex_from_color(color[:-1])
    for color in (NODE_COLOR, HIGHLIGHTED_NODE, SELECTED_COLOR, PINNED_COLOR, HIGHLIGHTED_EDGE))


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

              Operator:               PINNED_COLOR,
              Operator.Word:          HIGHLIGHTED_EDGE,

              String:                 PINNED_COLOR,
              String.Affix:           HIGHLIGHTED_EDGE,
              String.Escape:          HIGHLIGHTED_EDGE,
              String.Interpol:        HIGHLIGHTED_EDGE,

              Token.Punctuation:      PINNED_COLOR}
