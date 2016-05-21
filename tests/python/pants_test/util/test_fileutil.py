# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import random
import re
import unittest

from pants.util.contextutil import temporary_file, temporary_file_path
from pants.util.fileutil import atomic_copy, create_size_estimators, glob_to_regex


class FileutilTest(unittest.TestCase):
  def test_atomic_copy(self):
    with temporary_file() as src:
      src.write(src.name)
      src.flush()
      with temporary_file() as dst:
        atomic_copy(src.name, dst.name)
        dst.close()
        with open(dst.name) as new_dst:
          self.assertEquals(src.name, new_dst.read())
        self.assertEqual(os.stat(src.name).st_mode, os.stat(dst.name).st_mode)

  def test_line_count_estimator(self):
    with temporary_file_path() as src:
      self.assertEqual(create_size_estimators()['linecount']([src]), 0)

  def test_random_estimator(self):
    seedValue = 5
    # The number chosen for seedValue doesn't matter, so long as it is the same for the call to
    # generate a random test number and the call to create_size_estimators.
    random.seed(seedValue)
    rand = random.randint(0, 10000)
    random.seed(seedValue)
    with temporary_file_path() as src:
      self.assertEqual(create_size_estimators()['random']([src]), rand)


class GlobToRegexTest(unittest.TestCase):
  def assert_rule_match(self, glob, expected_matches, negate=False):
    if negate:
      asserter, match_state = self.assertIsNone, 'erroneously matches'
    else:
      asserter, match_state = self.assertIsNotNone, "doesn't match"

    regex = glob_to_regex(glob)
    for expected in expected_matches:
      asserter(re.match(regex, expected), 'glob_to_regex(`{}`) -> `{}` {} path `{}`'
                                          .format(glob, regex, match_state, expected))

  def assert_not_rule_match(self, *args, **kwargs):
    kwargs['negate'] = True
    return self.assert_rule_match(*args, **kwargs)

  def test_glob_to_regex_wildcard_0(self):
    self.assert_rule_match('a/b/*/f.py', ('a/b/c/f.py', 'a/b/q/f.py'))

  def test_glob_to_regex_wildcard_0_neg(self):
    self.assert_not_rule_match('a/b/*/f.py', ('a/b/c/d/f.py','a/b/c/d/e/f.py'))

  def test_glob_to_regex_wildcard_1(self):
    self.assert_rule_match('/foo/bar/*', ('foo/bar/baz', 'foo/bar/bar'))
    # self.assert_not_rule_match('/foo/bar/*', ('/foo/bar/baz', '/foo/bar/bar'))

  def test_glob_to_regex_wildcard_2(self):
    self.assert_rule_match('/*/bar/b*', ('foo/bar/baz', 'foo/bar/bar'))

  def test_glob_to_regex_wildcard_3(self):
    self.assert_rule_match('/*/[be]*/b*', ('foo/bar/baz', 'foo/bar/bar'))

  def test_glob_to_regex_wildcard_4(self):
    self.assert_rule_match('/foo*/bar', ('foofighters/bar', 'foofighters.venv/bar'))

  def test_glob_to_regex_wildcard_4_neg(self):
    self.assert_not_rule_match('/foo*/bar', ('/foofighters/baz/bar',))

  def test_glob_to_regex_dots_anchored(self):
    self.assert_rule_match('/.*',
                           ('.', '..', '.pants.d', '.pids', '.some/hidden/nested/dir/file.py'))

  def test_glob_to_regex_dots_anchored_neg(self):
    self.assert_not_rule_match('/.*', ('a', '0' 'a/.non/anchored/dot/dir/path.py', 'dist'))

  def test_glob_to_regex_dots(self):
    self.assert_rule_match('.*', ('.pants.d', '.', '..', '.pids'))

  def test_glob_to_regex_dots_neg(self):
    self.assert_not_rule_match(
      '.*',
      ('a', '0' 'a/non/dot/dir/file.py', 'dist', 'all/nested/.dot/dir/paths')
    )

  def test_glob_to_regex_dirs_anchored(self):
    self.assert_rule_match('/dist/', ('dist', 'dist/super_rad.pex', 'dist/nested/dirs/too.c'))

  def test_glob_to_regex_dirs_anchored_neg(self):
    self.assert_not_rule_match('/dist/',
                               ('not_dist', 'nested/dist', 'dist.py', 'nested/dist/dir.py'))

  def test_glob_to_regex_dirs(self):
    self.assert_rule_match('dist/', ('dist', 'dist/nested/path.py', 'dist/another/nested/dir'))

  def test_glob_to_regex_dirs_neg(self):
    self.assert_not_rule_match('dist/', ('not_dist', 'cdist', 'dist.py', 'nested/dist/dir.py'))

  def test_glob_to_regex_dirs_dots(self):
    self.assert_rule_match(
      'build-support/*.venv/',
      ('build-support/*.venv',
       'build-support/rbt.venv/setup.py',
       'build-support/isort.venv/bin/isort')
    )

  def test_glob_to_regex_dirs_dots_neg(self):
    self.assert_not_rule_match('build-support/*.venv/',
                               ('build-support/rbt.venv.but_actually_a_file',))

  def test_glob_to_regex_literals(self):
    self.assert_rule_match('a', ('a',))

  def test_glob_to_regex_literal_dir(self):
    self.assert_rule_match('a/b/c', ('a/b/c',))

  def test_glob_to_regex_literal_file(self):
    self.assert_rule_match('a/b/c.py', ('a/b/c.py',))
