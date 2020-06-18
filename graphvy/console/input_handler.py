from keys import *

class InputHandler:
    def __init__(self, text_input):
        self.text_input = text_input

        self.pre        = {        COPY: self._copy,
                                    CUT: self._cut,
                                   REDO: self._redo}

        self.post       = {        LEFT: self._left,
                                  RIGHT: self._right,
                                    END: self._end,
                                   HOME: self._home,
                            SELECT_LEFT: self._select_left,
                           SELECT_RIGHT: self._select_right,
                             SELECT_END: self._select_end,
                            SELECT_HOME: self._select_home,
                                    TAB: self._tab,
                                  ENTER: self._enter,
                                     UP: self._up,
                                   DOWN: self._down,
                              BACKSPACE: self._backspace}

    def __call__(self, key, read_only):
        if handle := self.pre.get(key): return handle

        if read_only: return self._read_only

        for key in key.iter_similar():
            if handle := self.post.get(key): return handle

    def _copy(self, **kwargs): self.text_input.copy()

    def _cut(self, read_only, **kwargs):
        self.text_input.copy() if read_only else self.text_input.cut()

    def _redo(self, **kwargs): self.text_input.do_redo()

    def _left(self, at_home, **kwargs):
        self.text_input.cancel_selection()
        if not at_home: self.text_input.move_cursor('left')

    def _right(self, at_end, **kwargs):
        self.text_input.cancel_selection()
        if not at_end: self.text_input.move_cursor('right')

    def _end(self, **kwargs):
        self.text_input.cancel_selection()
        self.text_input.move_cursor('end')

    def _home(self, **kwargs):
        self.text_input.cancel_selection()
        self.text_input.move_cursor('home')

    def _select_left(self, at_home, has_selection, _from, _to, **kwargs):
        if at_home: return
        i = self.text_input.move_cursor('left')
        if not has_selection: self.text_input.select_text(i, i + 1)
        elif   i <   _from  : self.text_input.select_text(i, _to)
        elif   i >=  _from  : self.text_input.select_text(_from, i)

    def _select_right(self, at_end, has_selection, _from, _to, **kwargs):
        if at_end: return
        i = self.text_input.move_cursor('right')
        if not has_selection: self.text_input.select_text(i - 1, i)
        elif   i >  _to    : self.text_input.select_text(_from, i)
        elif   i <= _to    : self.text_input.select_text(i, _to)

    def _select_end(self, has_selection, _to, _from, i, end, **kwargs):
        if not has_selection: start = i
        elif    _to == i    : start = _from
        else                : start = _to
        self.text_input.select_text(start, end)
        self.text_input.move_cursor('end')

    def _select_home(self, has_selection, _to, _from, i, home, **kwargs):
        if not has_selection: fin = i
        elif   _from == i   : fin = _to
        else                : fin = _from
        self.text_input.select_text(home, fin)
        self.text_input.move_cursor('home')

    def _tab(self, has_selection, at_home, **kwargs):
        ti = self.text_input
        if not has_selection and at_home: ti.insert_text(' ' * ti.tab_width)

    def _enter(self, home, **kwargs):
        ti = self.text_input
        text = ti.text[home:].rstrip()

        if text and (len(ti.history) == 1 or ti.history[1] != text):
            ti.history.popleft()
            ti.history.appendleft(text)
            ti.history.appendleft('')
        ti._history_index = 0

        needs_more = ti.console.push(text)
        ti.prompt(needs_more)

    def _up(self, **kwargs): self.text_input.input_from_history()

    def _down(self, **kwargs): self.text_input.input_from_history(reverse=True)

    def _backspace(self, at_home, has_selection, window, keycode, text, modifiers, **kwargs):
        ti = self.text_input
        if not at_home or has_selection:
            super(ti.__class__, ti).keyboard_on_key_down(window, keycode, text, modifiers)

    def _read_only(self, key, window, keycode, text, modifiers, **kwargs):
        ti = self.text_input
        ti.cancel_selection()
        ti.move_cursor('end')
        if key.code not in KEYS:
            super(ti.__class__, ti).keyboard_on_key_down(window, keycode, text, modifiers)