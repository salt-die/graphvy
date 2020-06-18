from code import InteractiveConsole
from collections import deque
from io import StringIO
import sys


class RedirectConsoleOut:
    """Redirect sys.excepthook and sys.stdout in a single context manager.
       InteractiveConsole (IC) `write` method won't be used if sys.excepthook isn't sys.__excepthook__,
       so we redirect sys.excepthook when pushing to the IC.  This redirect probably isn't necessary:
       testing was done in IPython which sets sys.excepthook to a crashhandler, but running this file
       normally would probably avoid the need for a redirect; still, better safe than sorry.
    """
    def __init__(self):
        self.stack = deque()

    def __enter__(self):
        self.old_hook = sys.excepthook
        self.old_out  = sys.stdout

        sys.excepthook = sys.__excepthook__
        sys.stdout     = StringIO()

        sys.stdout.write('\n')

    def __exit__(self, type, value, tb):
        self.stack.append(sys.stdout.getvalue())

        sys.stdout     = self.old_out
        sys.excepthook = self.old_hook


class Console(InteractiveConsole):
    def __init__(self, text_input, locals=None, filename="<console>"):
        super().__init__(locals, filename)
        self.text_input  = text_input
        self.out_context = RedirectConsoleOut()

    def push(self, line):
        out = self.out_context
        with out: needs_more = super().push(line)

        if not needs_more:
            out.stack.reverse()
            self.text_input.text += ''.join(out.stack)
        out.stack.clear()

        return needs_more

    def write(self, data):
        self.out_context.stack.append(data)
