"""TODO: ctrl + left/right (move past word), ctrl + backspace/del (del word), shift + del (del line)
    ...: ctrl + enter to continue input, shift + enter to run code now
    ...: Smart movement through leading indentation.
    ...: Except for first line, up/down to work normally on multi-line console input.
"""
from collections import deque
from itertools import takewhile
import sys

from kivy.uix.codeinput import CodeInput
from pygments.lexers import PythonConsoleLexer

from .keys import *
from .console import Console
from .input_handler import InputHandler
from .style import GraphvyStyle

from ..constants import HIGHLIGHTED_EDGE


class GraphvyConsole(CodeInput):
    prompt_1 = '\n>>> '
    prompt_2 = '\n... '

    _home_pos      = 0
    _indent_level  = 0
    _history_index = 0

    def __init__(self, *args, locals=None, **kwargs):
        super().__init__(*args, background_color=(0, 0, 0, 1), cursor_color=HIGHLIGHTED_EDGE, **kwargs)
        self.style         = GraphvyStyle
        self.lexer         = PythonConsoleLexer()
        self.font_name     = './UbuntuMono-R.ttf'

        self.history       = deque([''])
        self.console       = Console(self, locals)
        self.input_handler = InputHandler(self)

        self.text = (f'Python {sys.version.splitlines()[0]}\n'
                     'Welcome to the GraphvyConsole -- `G` references current graph.\n')
        self.prompt()

    def prompt(self, needs_more=False):
        if needs_more:
            prompt = self.prompt_2
            self._indent_level  = self.count_indents()
            if self.text.rstrip().endswith(':'): self._indent_level += 1
        else:
            prompt = self.prompt_1
            self._indent_level = 0

        indent = self.tab_width * self._indent_level
        self.text += prompt + ' ' * indent
        self._home_pos = self.cursor_index() - indent
        self.reset_undo()

    def count_indents(self):
        return sum(1 for _ in takewhile(str.isspace, self.history[1])) // self.tab_width

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """Emulate a python console: disallow editing of previous console output."""
        if keycode[0] in CTRL or keycode[0] in SHIFT and 'ctrl' in modifiers: return

        key = Key(keycode[0], 'shift' in modifiers, 'ctrl' in modifiers)

        # force `selection_from` <= `selection_to` (mouse selections can reverse the order):
        _from, _to    = sorted((self.selection_from, self.selection_to))
        has_selection = bool(self.selection_text)
        i, home, end  = self.cursor_index(), self._home_pos, len(self.text)

        read_only = i < home or has_selection and _from < home
        at_home   = i == home
        at_end    = i == end

        kwargs = locals(); del kwargs['self']
        if handle := self.input_handler(key, read_only): return handle(**kwargs)

        return super().keyboard_on_key_down(window, keycode, text, modifiers)

    def move_cursor(self, pos):
        """Similar to `do_cursor_movement` but we account for `_home_pos` and we return the new cursor index."""
        if   pos == 'end'  : i = len(self.text)
        elif pos == 'home' : i = self._home_pos
        elif pos == 'left' : i = self.cursor_index() - 1
        elif pos == 'right': i = self.cursor_index() + 1
        self.cursor = self.get_cursor_from_index(i)
        return i

    def input_from_history(self, reverse=False):
        self._history_index += -1 if reverse else 1
        self._history_index = min(max(0, self._history_index), len(self.history) - 1)
        self.text = self.text[: self._home_pos] + self.history[self._history_index]


if __name__ == "__main__":
    from textwrap import dedent
    from kivy.app import App
    from kivy.lang import Builder

    KV = """
    GraphvyConsole:
        background_color: 0,         0,     0, 1
        cursor_color:     0.760, 0.235, 0.239, 1
    """

    class GraphvyInterpreter(App):
        def build(self):
            return Builder.load_string(dedent(KV))


    GraphvyInterpreter().run()