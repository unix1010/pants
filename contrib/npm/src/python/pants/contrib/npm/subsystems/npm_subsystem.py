# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
from collections import namedtuple

from pants.backend.core.wrapped_globs import Globs
from pants.option.custom_types import list_option
from pants.subsystem.subsystem import Subsystem
from pants.util.memo import memoized_property


# Used to create Globs objects in the absence of a ParseContext
# TODO: add a constructor for Globs that doesn't require a parse_context
FakeParseContext = namedtuple('FakeParseContext', ['rel_path'])

class NpmSubsystem(Subsystem):
  options_scope = 'npm'

  @classmethod
  def register_options(cls, register):
    register('--source-globs', advanced=True, type=list_option, default=['*.js', '*.jsx'],
              help='The set of globs to use to match sources owned by npm_module targets.')

  def source_globs(self, address):
    """Given a target address, return an object representing the sources of the target.

    This is intended to encourage 1:1:1 by disallowing manual configuration of sources.
    """
    return Globs(FakeParseContext(address.spec_path))(*self.get_options().source_globs)
