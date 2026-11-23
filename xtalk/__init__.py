"""xtalk: a Python interpreter for xTalk (the LiveCode script family).

    from xtalk import Interp
    it = Interp(script_text)        # handlers, functions, commands
    it.call('myFunction', 'a', 2)   # run a handler, returns its value as text
    it.eval('word 2 of "a b c"')    # one expression

Everything is text, as in LiveCode; behaviour is checked against LiveCode 9.6.3 (tests/golden.json).
"""
from .interp import Interp, XtError  # noqa: F401
