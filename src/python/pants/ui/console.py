# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import sys
import termios
from contextlib import contextmanager

from blessed import Terminal


class ProperTerminal(Terminal):
  def get_proper_column(self):
    """Retrieves the cursor column location with an offset appropriate for use with Terminal.location().
    """
    return self.get_proper_location()[1]

  def get_proper_location(self):
    """Retrieves the cursor location with an offset appropriate for use with Terminal.location()."""
    y, x = self.get_location()
    return (x - 1, y - 1)


class ParallelConsole(object):
  """A console UI for displaying concurrent work status."""

  def __init__(self, workers, padding=0, stream=None, swimlane_glyph=None):
    """
    :param int workers: Number of workers to display output for.
    :param int padding: The amount of whitespace padding to insert before all input. This is useful
                        for nesting appropriately under work unit output, etc.
    :param file stream: The stream to emit output on (defaults to sys.stdout).
    :param string swimlane_glyph: A glyph string to display in front of every worker's swimlane.
    """
    self._workers = workers
    self._padding = padding
    self._stream = stream or sys.stdout
    self._term = ProperTerminal(stream=self._stream)
    self._swimlane_glyph = swimlane_glyph or self._term.bright_green('⚡')

    self._initial_position = None
    self._display_map = None
    self._summary = None

  @property
  def padding(self):
    """Returns the indentation padding as a string."""
    return ' ' * self._padding

  def _initialize_swimlanes(self, worker_count):
    """Draws initial swimlanes for the worker count and maps cursor positions to index positions.

    :param int worker_count: The number of swimlanes to map.
    """
    self._display_map = {0: self._term.get_location()}

    # Initialize the printable space for the worker status slots.
    for i in range(1, worker_count + 1):
      self._stream.write('{}{} '.format(self.padding, self._swimlane_glyph))
      # Without a flush here, the captured post-write cursor position won't be guaranteed.
      self._stream.flush()
      # Capture the cursor location after the line label as our future starting point for writes.
      self._display_map[i] = self._term.get_proper_location()
      self._stream.write('\n')

  def _write_line(self, pos, line):
    """Writes a line to the worker swimlane given an index position.

    :param int pos: The index position to write to.
    :param string line: The line to display at the index position.
    """
    with self._term.location(*self._display_map[pos]):
      self._stream.write(line.ljust(self._term.width - 10))
      self._stream.flush()

  def _ensure_newline(self):
    """Ensures a clean start on a non-indented line."""
    if self._term.get_proper_column() != 0:
      self._stream.write('\n')

  def _set_initial_position(self):
    """Sets the initial position of the cursor before drawing."""
    # We reverse this because the inputs to Terminal.move() differ from Terminal.location(). This
    # is used with the former (which is permanent) whereas most other output uses the latter.
    self._initial_position = reversed(self._term.get_proper_location())

  def _reset_to_initial_position(self):
    """Clears the terminal back to the original position."""
    self._stream.write(self._term.move(*self._initial_position))   # Move to initial position.
    self._stream.write(self._term.clear_eos)                 # Clear to end of screen.
    self._stream.flush()

  def _get_status_glyph(self, success):
    """Returns a glyph appropriate for prefixing a status summary line based on success/failure.

    :param bool success: True if success, False if not.
    """
    return self._term.bright_green('✓') if success else self._term.bright_red('✗')

  def _start(self):
    """Starts the console display."""
    assert self._display_map is None, 'console already activated!'
    self._summary = None
    self._ensure_newline()
    self._set_initial_position()
    self._stream.write(self._term.hide_cursor)
    self._initialize_swimlanes(self._workers)

  def _stop(self):
    """Stops the console display."""
    self._display_map = None
    self._stream.write(self._term.normal_cursor)
    if self._summary:
      success, summary = self._summary
      self._reset_to_initial_position()
      self._stream.write('{}{} {}'.format(self.padding, self._get_status_glyph(success), summary))
      self._ensure_newline()

  @contextmanager
  def _echo_disabled(self):
    """A context manager that disables tty input echoing.

    This helps prevent user input from scrolling fixed curses output off the screen. Mostly lifted
    from the stdlib's `getpass` module.
    """
    # TODO(kwlzn): this is not pailgun friendly.
    fd = os.open('/dev/tty', os.O_RDWR | os.O_NOCTTY)
    orig_attrs = termios.tcgetattr(fd)
    new_attrs = orig_attrs[:]
    new_attrs[3] &= ~termios.ECHO
    flags = termios.TCSAFLUSH | getattr(termios, 'TCSASOFT', 0)
    try:
      termios.tcsetattr(fd, flags, new_attrs)
      yield
    finally:
      termios.tcsetattr(fd, flags, orig_attrs)

  @contextmanager
  def active(self):
    """A contextmanager that controls the lifecycle of a single invocation of the console.

    May be called multiple times against the same object.
    """
    with self._echo_disabled():
      try:
        self._start()
        yield
      finally:
        self._stop()

  def clear(self):
    """Clears the screen."""
    self._stream.write(self._term.clear)

  def set_summary(self, success, summary):
    """Sets the summary, which is displayed when stop() is called.

    :param bool success: True if the parallel work ran without error, False otherwise.
    :param string summary: A string summary to display. This will cause the worker output to clear.
    """
    self._summary = success, summary

  def set_activity(self, worker, activity):
    """Sets the current activity for a given worker.

    :param int worker: The worker ID.
    :param string activity: The worker activity.
    """
    self._write_line(worker, activity)
