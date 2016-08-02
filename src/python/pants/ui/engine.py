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

  def get_row(self):
    return self.get_location()[0]

  def get_column(self):
    return self.get_location()[1]

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
    if self.get_column() != 1:
      print()

  def get_proper_location(self):
    y, x = self.get_location()
    return (x - 1, y - 1)
  #
  # def _reset_to_initial_position(self):
  #   """Clears the terminal back to the original position."""
  #   print(self.)

  def _set_initial_position(self):
    self._initial_position = self.get_proper_location()

  def start(self):
    """Starts the console display."""
    assert self._display_map is None, 'EngineConsole already activated!'
    self._ensure_newline()
    self._set_initial_position()
    self._initialize_swimlanes(self._workers)
    # self.set_status('Engine Running')

  def stop(self):
    """Stops the console display."""
    # Clear output state completely?
    # self.set_status('Engine Shutdown')
    self._display_map = None
    # self._reset_to_initial_position()

  def set_status(self, status):
    """Sets the status for the engine."""
    # self._write_line(0, self.bright_green(status.ljust(int(self.width / 3))))

  def set_action(self, worker, status):
    """Sets the current action for a given worker."""
    self._write_line(worker, status)

  def set_result(self, worker, result):
    """Sets the result for a given worker."""
    self._write_line(worker, result)


def main():
  import time, random
  worker_count = 8
  random_workers = range(1, worker_count + 1)
  random_sleeps = (0, 0, 0, 0, 0, 0.1) #, 0.2) #, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
  random_products = ('FileContent', 'FileFingerprint', 'DirectoryListing',
                     'PythonBinary', 'PythonLibrary', 'Sources', 'PathGlobs')
  print('[workunit]'); time.sleep(.5)
  print('  [workunit1]'); time.sleep(.3)
  print('  [workunit2]'); time.sleep(.1)
  e = EngineConsole(workers=worker_count, padding=4)
  e.start()
  for i in range(500):
    random_product = random.choice(random_products)
    random_requester = random.choice(random_products)
    random_worker = random.choice(random_workers)
    e.set_action(random_worker, 'computing {} for {}'.format(random_product, random_requester))
    time.sleep(random.choice(random_sleeps))
  e.stop()
  print('  [workunit3]'); time.sleep(.3)
  print('[end]')
