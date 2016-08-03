# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import sys

from blessed import Terminal


class EngineConsole(Terminal):
  """A console UI for the v2 engine."""

  def __init__(self, workers, padding=0, stream=None):
    """
    :param int workers: Number of workers to display output for.
    :param file stream: The stream to emit output on.
    """
    self._stream = stream or sys.stdout
    super(EngineConsole, self).__init__(stream=self._stream)
    self._workers = workers
    self._padding = padding
    self._initial_position = None
    self._display_map = None

  @property
  def padding(self):
    return ' ' * self._padding

  def get_proper_column(self):
    return self.get_proper_location()[1]

  def get_proper_location(self):
    y, x = self.get_location()
    return (x - 1, y - 1)

  def _initialize_swimlanes(self, worker_count):
    # Initialize the printable space for the top level engine status slot.
    self._display_map = {0: self.get_location()}
    # print(self.bright_white_on_blue(' ' * int(self.width / 3)))

    # Initialize the printable space for the worker status slots.
    for i in range(1, worker_count + 1):
      print('{pad}{term.bright_green}⚡{term.normal}'.format(pad=self.padding, term=self), end=' ')
      self._stream.flush()
      # Capture the cursor location after the line label as our future starting point for writes.
      self._display_map[i] = self.get_proper_location()
      print()

  def _write_line(self, pos, line):
    with self.location(*self._display_map[pos]):
      print(line.ljust(self.width - 10), end='')
      self._stream.flush()

  def _ensure_newline(self):
    """Ensures a clean start on a non-indented line."""
    if self.get_proper_column() != 0:
      print()

  def _reset_to_initial_position(self):
    """Clears the terminal back to the original position."""
    print(self.move(*self._initial_position), self.clear_eos, end='')

  def _set_initial_position(self):
    # We reverse this because the inputs to Terminal.move() differ from Terminal.location(). This
    # is used with the former (which is permanent) whereas most other output uses the latter.
    self._initial_position = reversed(self.get_proper_location())

  def start(self):
    """Starts the console display."""
    assert self._display_map is None, 'EngineConsole already activated!'
    self._ensure_newline()
    self._set_initial_position()
    self._initialize_swimlanes(self._workers)

  def stop(self):
    """Stops the console display."""
    # Clear output state completely?
    self._display_map = None
    self._reset_to_initial_position()
    print('{pad}{term.bright_green}✓{term.normal} computed 10 trillion products in 9 iterations in .4 seconds'
          .format(pad=self.padding, term=self))

  def set_action(self, worker, status):
    """Sets the current action for a given worker."""
    self._write_line(worker, status)

  def set_result(self, worker, result):
    """Sets the result for a given worker."""
    self._write_line(worker, result)

