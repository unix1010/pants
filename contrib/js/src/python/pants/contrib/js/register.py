# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.base.target import Target
from pants.base.build_file_aliases import BuildFileAliases
from pants.goal.task_registrar import TaskRegistrar as task


class JsLibrary(Target):
  def __init__(self, resources=None, *args, **kwargs):
    # TODO: payload
    super(JsLibrary, self).__init__(*args, **kwargs)

class NpmModule(Target):
  def __init__(self, entry=None, *args, **kwargs):
    # TODO: payload
    super(NpmModule, self).__init__(*args, **kwargs)

class NpmRemoteModule(Target):
  def __init__(self, rev=None, *args, **kwargs):
    # TODO: payload
    super(NpmRemoteModule, self).__init__(*args, **kwargs)


def build_file_aliases():
  return BuildFileAliases.create(
    targets={
      'js_library': JsLibrary,
      'npm_module': NpmModule,
      'npm_remote_module': NpmRemoteModule,
    },
  )
