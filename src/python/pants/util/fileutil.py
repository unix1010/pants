# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import random
import shutil

from pants.util.contextutil import temporary_file


def atomic_copy(src, dst):
  """Copy the file src to dst, overwriting dst atomically."""
  with temporary_file(root_dir=os.path.dirname(dst)) as tmp_dst:
    shutil.copyfile(src, tmp_dst.name)
    os.chmod(tmp_dst.name, os.stat(src).st_mode)
    os.rename(tmp_dst.name, dst)


def create_size_estimators():
  """Create a dict of name to a function that returns an estimated size for a given target.

  The estimated size is used to build the largest targets first (subject to dependency constraints).
  Choose 'random' to choose random sizes for each target, which may be useful for distributed
  builds.
  :returns: Dict of a name to a function that returns an estimated size.
  """
  def line_count(filename):
    with open(filename, 'rb') as fh:
      return sum(1 for line in fh)
  return {
    'linecount': lambda srcs: sum(line_count(src) for src in srcs),
    'filecount': lambda srcs: len(srcs),
    'filesize': lambda srcs: sum(os.path.getsize(src) for src in srcs),
    'nosize': lambda srcs: 0,
    'random': lambda srcs: random.randint(0, 10000),
  }


def glob_to_regex(glob):
  """Given a glob pattern, return a regex that will match it's path relative to the buildroot.

  :param string glob: The glob pattern.
  :returns: A regex string that will match a relative glob path with no leading `/`.
  """
  replacement_map = (('?', r'.'),
                     ('.', r'[.]'),
                     ('**/', r'(?:.*/)?'),
                     ('*', r'[^/]*'))

  for from_pattern, to_pattern in replacement_map:
    glob = glob.replace(from_pattern, to_pattern)

  # Treat trailing slashes as "the dir and everything beneath it".
  if glob.endswith('/'):
    glob = r'{}(/.*|$)'.format(glob[:-1])

  if glob.startswith('/'):
    glob = r'^{}'.format(glob[1:])

  return glob
