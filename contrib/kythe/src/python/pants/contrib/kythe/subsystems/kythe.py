# coding=utf-8
# Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.subsystem.subsystem import Subsystem


class Kythe(Subsystem):
  options_scope = 'kythe'

  @classmethod
  def register_options(cls, register):
    super(Kythe, cls).register_options(register)
    register('--corpus', type=str, fingerprint=True,
        help='The kythe Corpus value for this codebase. Usually this is a unique identifier '
             'for the version controlled repository holding the code.')

  def corpus(self):
    corpus = self.get_options().corpus
    if not corpus:
      raise ValueError('A `corpus` must be set in order to perform kythe indexing. '
                       'See `./pants help {}`'.format(self.options_scope))
    return corpus
