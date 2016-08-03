# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import unittest

from pants.ui.colors import (COLORS, black, blue, colorize, cyan, green, magenta, red, strip_escape,
                             white, yellow)


class ColorsTest(unittest.TestCase):
  def test_colors(self):
    for color in COLORS:
      for background_color in COLORS:
        print(colorize('{} on {}'.format(color, background_color), color, background_color))

  def test_color_helpers(self):
    print(black('black'))
    print(red('red'))
    print(green('green'))
    print(yellow('yellow'))
    print(blue('blue'))
    print(magenta('magenta'))
    print(cyan('cyan'))
    print(white('white'))

  def test_color_helpers_background(self):
    for background_color in COLORS:
      print(black('black', background=background_color))
      print(red('red', background=background_color))
      print(green('green', background=background_color))
      print(yellow('yellow', background=background_color))
      print(blue('blue', background=background_color))
      print(magenta('magenta', background=background_color))
      print(cyan('cyan', background=background_color))
      print(white('white', background=background_color))

  def test_uncolorize(self):
    for color in COLORS:
      self.assertEquals(color, strip_escape(colorize(color, color)))
      for background_color in COLORS:
        self.assertEquals(color, strip_escape(colorize(color, color, background_color)))
