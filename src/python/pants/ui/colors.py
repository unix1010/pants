# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import re
from functools import partial


ESCAPE = '\x1b'
ESCAPE_SEQ_PREFIX = '{}['.format(ESCAPE)
ESCAPE_SEQ_SUFFIX = 'm'
ESCAPE_CLEAR = '{}0{}'.format(ESCAPE_SEQ_PREFIX, ESCAPE_SEQ_SUFFIX)  # Clears all formatting.
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
  """Color a string using simple, printable terminal escape sequences.

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
      ESCAPE_SEQ_PREFIX,
      str(30 + COLORS[color]),
      ';{}'.format(40 + COLORS[background]) if background else '',
      ESCAPE_SEQ_SUFFIX,
      s,
      ESCAPE_CLEAR
    )
  )


def strip_escape(s):
  return re.sub(r'{}\[.+?{}'.format(ESCAPE, ESCAPE_SEQ_SUFFIX), '', s)


black = partial(colorize, color='black')
red = partial(colorize, color='red')
green = partial(colorize, color='green')
yellow = partial(colorize, color='yellow')
blue = partial(colorize, color='blue')
magenta = partial(colorize, color='magenta')
cyan = partial(colorize, color='cyan')
white = partial(colorize, color='white')
