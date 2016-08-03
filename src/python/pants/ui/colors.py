# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from functools import partial
import re


ESCAPE = '\x1b'
ESCAPE_START = '{}['.format(ESCAPE)
ESCAPE_END = '{}[0m'.format(ESCAPE)  # Clears all formatting.
COLORS = {
  'black': 0,
  'red': 1,
  'green': 2,
  'yellow': 3,
  'blue': 4,
  'magenta': 5,
  'cyan': 6,
  'white': 7
}


def colorize(s, color, background=None):
  """Color a string using printable terminal escape sequences.

  :param string s: A string to colorize.
  :param string color: The foreground color name.
  :param string background: The background color name.
  """
  assert color in COLORS, 'invalid color: {}'.format(color)
  if background:
    assert background in COLORS, 'invalid background color: {}'.format(background)

  # Generate an escape sequence like: '\x1b[33mpants\x1b[0m'
  return ''.join(
    (
      ESCAPE_START,
      str(30 + COLORS[color]),
      ';{}m'.format(40 + COLORS[background]) if background else 'm',
      s,
      ESCAPE_END
    )
  )


def strip_color(s):
  return re.sub(r'{}\[.+?m'.format(ESCAPE), '', s)


black = partial(colorize, color='black')
red = partial(colorize, color='red')
green = partial(colorize, color='green')
yellow = partial(colorize, color='yellow')
blue = partial(colorize, color='blue')
magenta = partial(colorize, color='magenta')
cyan = partial(colorize, color='cyan')
white = partial(colorize, color='white')
