# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.base.exceptions import TargetDefinitionException
from pants.base.target import Target


class NpmRemoteModule(Target):
  def __init__(self, version=None, *args, **kwargs):
    super(NpmRemoteModule, self).__init__(*args, **kwargs)
    if not version:
      raise TargetDefinitionException(self, "The `version` argument is required, and should specify a semantic version.")
