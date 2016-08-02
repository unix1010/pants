# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import unittest

from pants.ui.engine import EngineConsole


class EngineConsoleTest(unittest.TestCase):
  def test_lifecycle(self):
    e = EngineConsole(workers=8)
    e.start()
    e.stop()
