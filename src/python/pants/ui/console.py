# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import sys

from blessed import Terminal


class ParallelConsole(Terminal):
  """A console UI for displaying concurrent work status."""

  def __init__(self, workers, padding=0, stream=None, swimlane_glyph=None):
    """
    :param int workers: Number of workers to display output for.
    :param file stream: The stream to emit output on.
    """
    _stream = stream or sys.stdout
    super(ParallelConsole, self).__init__(stream=_stream)
    self._workers = workers
    self._swimlane_glyph = swimlane_glyph or self.bright_green('⚡')
    self._padding = padding
    self._initial_position = None
    self._display_map = None

  @property
  def padding(self):
    return ' ' * self._padding

  def _get_status_glyph(self, success):
    return self.bright_green('✓') if success else self.bright_red('✗')

  def get_proper_column(self):
    return self.get_proper_location()[1]

  def get_proper_location(self):
    y, x = self.get_location()
    return (x - 1, y - 1)

  def _initialize_swimlanes(self, worker_count):
    self._display_map = {0: self.get_location()}

    # Initialize the printable space for the worker status slots.
    for i in range(1, worker_count + 1):
      self.stream.write('{}{} '.format(self.padding, self._swimlane_glyph))
      self.stream.flush()
      # Capture the cursor location after the line label as our future starting point for writes.
      self._display_map[i] = self.get_proper_location()
      self.stream.write('\n')

  def _write_line(self, pos, line):
    with self.location(*self._display_map[pos]):
      self.stream.write(line.ljust(self.width - 10))
      self.stream.flush()

  def _ensure_newline(self):
    """Ensures a clean start on a non-indented line."""
    if self.get_proper_column() != 0:
      self.stream.write('\n')

  def _reset_to_initial_position(self):
    """Clears the terminal back to the original position."""
    self.stream.write(self.move(*self._initial_position))   # Move to initial position.
    self.stream.write(self.clear_eos)                       # Clear to end of screen.
    self.stream.flush()

  def _set_initial_position(self):
    # We reverse this because the inputs to Terminal.move() differ from Terminal.location(). This
    # is used with the former (which is permanent) whereas most other output uses the latter.
    self._initial_position = reversed(self.get_proper_location())

  def start(self):
    """Starts the console display."""
    assert self._display_map is None, 'console already activated!'
    self._ensure_newline()
    self._set_initial_position()
    self.stream.write(self.hide_cursor)
    self._initialize_swimlanes(self._workers)

  def stop(self, success, summary=None):
    """Stops the console display.

    :param bool success: True if the parallel work ran without error, False otherwise.
    :param string summary: A string summary to display. This will cause the worker output to clear.
    """
    self._display_map = None
    self.stream.write(self.normal_cursor)
    if summary:
      self._reset_to_initial_position()
      self.stream.write('{}{} {}'.format(self.padding, self._get_status_glyph(success), summary))
      self._ensure_newline()

  def set_activity(self, worker, activity):
    """Sets the current activity for a given worker.

    :param int worker: The worker ID.
    :param string activity: The worker activity.
    """
    self._write_line(worker, activity)
