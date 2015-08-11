# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.base.exceptions import TargetDefinitionException
from pants.base.payload import Payload
from pants.base.payload_field import PrimitiveField
from pants.base.target import Target
from pants.contrib.npm.subsystems.npm_subsystem import NpmSubsystem


class NpmRemoteModule(Target):
  """Represents the name and version of a remote npm module existing in an npm repository."""

  @classmethod
  def subsystems(cls):
    return super(NpmRemoteModule, cls).subsystems() + (NpmSubsystem,)

  def __init__(self, name=None, version=None, *args, **kwargs):
    payload = Payload()
    payload.add_fields({
      'version': PrimitiveField(version),
      'name': PrimitiveField(name)
    })
    super(NpmRemoteModule, self).__init__(name=name, *args, **kwargs)
    if not version:
      raise TargetDefinitionException(self, "The `version` argument is required, and should specify a semantic version.")
