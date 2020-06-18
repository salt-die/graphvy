from dataclasses import dataclass

@dataclass(frozen=True)
class Key:
    # ANY equals everything! -- if you don't care about matching modifiers, set them equal to Key.ANY
    ANY = type('ANY', (), {  '__eq__': lambda *args: True,
                           '__repr__': lambda  self: 'ANY',
                           '__hash__': lambda  self: -1})()

    code:  int
    shift: bool = False
    ctrl:  bool = False

    def __eq__(self, other):
        if isinstance(other, int): return other == self.code
        return self.__dict__ == other.__dict__

    def iter_similar(self):
        """Return an iterator that yields keys equal to self."""
        yield self
        yield Key(self.code, self.shift, Key.ANY)
        yield Key(self.code,    Key.ANY, self.ctrl)
        yield Key(self.code,    Key.ANY, Key.ANY)