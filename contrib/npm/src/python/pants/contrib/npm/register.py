# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.base.build_file_aliases import BuildFileAliases
from pants.goal.task_registrar import TaskRegistrar as task

from pants.contrib.npm.targets.npm_module import NpmModule
from pants.contrib.npm.targets.npm_remote_module import NpmRemoteModule


def build_file_aliases():
  return BuildFileAliases.create(
    targets={
      'npm_module': NpmModule,
      'npm_remote_module': NpmRemoteModule,
    },
  )
