# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
from glob import glob

from pants.base.exceptions import TargetDefinitionException
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField
from pants.base.target import Target


class NpmModule(Target):
  # TODO: add support for resources; currently ignored
  def __init__(self, address=None, version=None, main=None, resources=None, **kwargs):
    # TODO: define glob patterns in the subsystem
    sources = glob(os.path.join(address.spec_path, '*.js'))
    payload = Payload()
    payload.add_fields({
      'sources': self.create_sources_field(sources=sources,
                                           sources_rel_path='',
                                           key_arg='sources'),
      'version': PrimitiveField(version),
      'main': PrimitiveField(main),
    })
    super(NpmModule, self).__init__(address=address, payload=payload, **kwargs)
    if not version:
      raise TargetDefinitionException(self, "The `version` argument is required, and should specify a semantic version.")
