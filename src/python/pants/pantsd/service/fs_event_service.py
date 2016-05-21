# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import fnmatch
import logging
import os
import traceback

from concurrent.futures import ThreadPoolExecutor

from pants.pantsd.service.pants_service import PantsService
from pants.pantsd.watchman import Watchman
from pants.util.fileutil import glob_to_regex


class FSEventService(PantsService):
  """Filesystem Event Service.

  This is the primary service coupling to watchman and is responsible for subscribing to and
  reading events from watchman's UNIX socket and firing callbacks in pantsd. Callbacks are
  executed in a configurable threadpool but are generally expected to be short-lived.
  """

  ZERO_DEPTH = ['depth', 'eq', 0]

  def __init__(self, watchman, build_root, path_ignore_patterns, worker_count):
    """
    :param Watchman watchman: The Watchman instance as provided by the WatchmanLauncher subsystem.
    :param str build_root: The current build root.
    :param list path_ignores: A list of path ignore patterns for Watchman.
    :param int worker_count: The total number of workers to use for the internally managed
                             ThreadPoolExecutor.
    """
    super(FSEventService, self).__init__()
    self._logger = logging.getLogger(__name__)
    self._watchman = watchman
    self._build_root = os.path.realpath(build_root)
    self._path_ignore_patterns = path_ignore_patterns
    self._worker_count = worker_count
    self._executor = None
    self._handlers = {}

  def setup(self, executor=None):
    self._executor = executor or ThreadPoolExecutor(max_workers=self._worker_count)

  def terminate(self):
    """An extension of PantsService.terminate() that shuts down the executor if so configured."""
    if self._executor:
      self._logger.info('shutting down threadpool')
      self._executor.shutdown()
    super(FSEventService, self).terminate()

  def _generate_ruleset_from_ignore_patterns(self, path_ignore_patterns):
    for glob_pattern in path_ignore_patterns:
      # N.B. 'wholename' ensures we match against the full relative ('x/y/z') vs file path ('z').
      yield ['not', ['pcre', glob_to_regex(glob_pattern), 'wholename']]

  def register_all_files_handler(self, callback, name='all_files'):
    """Registers a subscription for all files under a given watch path.

    :param func callback: the callback to execute on each filesystem event
    :param str name:      the subscription name as used by watchman
    """
    self.register_handler(
      name,
      dict(
        fields=['name'],
        # N.B. In this expression we intentionally avoid directory change events (['type', 'd']).
        # The reason for this is two-fold:
        #
        #   1) Directory change detection in Watchman is super aggressive - simply opening a file
        #      in vim with no writes is enough to immediately invalidate the parent dir's
        #      DirectoryListing. This seems inefficient when nothing relevant is actually changing.
        #
        #   2) Directory change detection does not cover the build_root without moving the watch-
        #      project target one level higher than the buildroot, which could be problematic.
        #
        # Instead, we key directory invalidation off of file change events by doing an
        # `os.path.dirname(file)` during invalidation subject generation, which covers both cases.
        expression=[
          'allof',  # All of the below rules must be true to match.
          ['anyof', ['type', 'f'], ['type', 'l']]  # Match only files and symlinks.
        ] + list(
          self._generate_ruleset_from_ignore_patterns(self._path_ignore_patterns)
        )
      ),
      callback
    )

  def register_handler(self, name, metadata, callback):
    """Register subscriptions and their event handlers.

    :param str name:      the subscription name as used by watchman
    :param dict metadata: a dictionary of metadata to be serialized and passed to the watchman
                          subscribe command. this should include the match expression as well
                          as any required callback fields.
    :param func callback: the callback to execute on each matching filesystem event
    """
    assert name not in self._handlers, 'duplicate handler name: {}'.format(name)
    assert (
      isinstance(metadata, dict) and 'fields' in metadata and 'expression' in metadata
    ), 'invalid handler metadata!'
    self._handlers[name] = Watchman.EventHandler(name=name, metadata=metadata, callback=callback)

  def fire_callback(self, handler_name, event_data):
    """Fire an event callback for a given handler."""
    return self._handlers[handler_name].callback(event_data)

  def run(self):
    """Main service entrypoint. Called via Thread.start() via PantsDaemon.run()."""

    if not (self._watchman and self._watchman.is_alive()):
      raise self.ServiceError('watchman is not running, bailing!')

    # Enable watchman for the build root.
    self._watchman.watch_project(self._build_root)

    futures = {}
    id_counter = 0
    subscriptions = self._handlers.values()

    # Setup subscriptions and begin the main event firing loop.
    for handler_name, event_data in self._watchman.subscribed(self._build_root, subscriptions):
      # On death, break from the loop and contextmgr to terminate callback threads.
      if self.is_killed: break

      if event_data:
        # As we receive events from watchman, submit them asynchronously to the executor.
        future = self._executor.submit(self.fire_callback, handler_name, event_data)
        futures[future] = handler_name

      # Process and log results for completed futures.
      for completed_future in [_future for _future in futures if _future.done()]:
        handler_name = futures.pop(completed_future)
        id_counter += 1

        try:
          result = completed_future.result()
        except Exception:
          result = traceback.format_exc()

        if result is not None:
          # Truthy results or those that raise exceptions are treated as failures.
          self._logger.warning('callback ID {} for {} failed: {}'
                               .format(id_counter, handler_name, result))
        else:
          self._logger.debug('callback ID {} for {} succeeded'.format(id_counter, handler_name))
