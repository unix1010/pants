# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import random
import time

from pants.ui.console import ParallelConsole


def main():
  """A mock-data driven demo of EngineConsole capabilities."""

  worker_count = 8
  random_workers = range(1, worker_count + 1)
  random_sleeps = (0, 0, 0, 0, 0, 0.01, 0.02, 0.03, 0.04, 0.05)
  random_products = ('FileContent', 'FileFingerprint', 'DirectoryListing',
                     'PythonBinary', 'PythonLibrary', 'Sources', 'PathGlobs')

  print('[workunit]')
  time.sleep(.3)
  print('  [workunit1]')
  time.sleep(.2)
  print('  [workunit2]', end='')
  time.sleep(.1)

  e = ParallelConsole(workers=worker_count, padding=4)
  e.start()
  start = time.time()
  for i in range(1000):
    random_product = random.choice(random_products)
    random_requester = random.choice(random_products)
    random_worker = random.choice(random_workers)
    # random_status = random.choice((True, False))
    e.set_activity(random_worker, 'computing {} for {}'.format(random_product, random_requester))
    time.sleep(random.choice(random_sleeps))
  e.stop(True, 'computed 6 trillion products in 93 iterations in {} seconds'.format(time.time() - start))

  print('  [workunit3]')
  time.sleep(.3)
  print('[end]')


if __name__ == '__main__':
  main()