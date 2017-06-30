# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import shutil
import tempfile
from abc import abstractmethod
from contextlib import contextmanager

import six
from six import binary_type, string_types
from twitter.common.collections import maybe_list

from pants.backend.jvm.argfile import safe_args
from pants.backend.jvm.subsystems.jar_tool import JarTool
from pants.backend.jvm.targets.java_agent import JavaAgent
from pants.backend.jvm.targets.jvm_binary import Duplicate, JarRules, JvmBinary, Skip
from pants.backend.jvm.tasks.classpath_util import ClasspathUtil
from pants.backend.jvm.tasks.nailgun_task import NailgunTask
from pants.base.exceptions import TaskError
from pants.java.jar.manifest import Manifest
from pants.java.util import relativize_classpath
from pants.util.contextutil import temporary_dir
from pants.util.dirutil import safe_mkdtemp
from pants.util.meta import AbstractClass


class AnalysisExtraction(NailgunTask):
  """A task that handles extracting product and dependency information from zinc analysis."""

  cache_target_dirs = True

  @classmethod
  def subsystem_dependencies(cls):
    return super(AnalysisExtraction, cls).subsystem_dependencies() + (Zinc,)

  @classmethod
  def prepare(cls, options, round_manager):
    super(AnalysisExtraction, cls).prepare(options, round_manager)
    round_manager.require_data('zinc_analysis')

  @staticmethod
  def _flag(bool_value):
    return 'true' if bool_value else 'false'

  _DUPLICATE_ACTION_TO_NAME = {
      Duplicate.SKIP: 'SKIP',
      Duplicate.REPLACE: 'REPLACE',
      Duplicate.CONCAT: 'CONCAT',
      Duplicate.CONCAT_TEXT: 'CONCAT_TEXT',
      Duplicate.FAIL: 'THROW',
  }

  def execute(self):
    zinc_analysis = self.context.products.get_data('zinc_analysis')
    targets = zinc_analysis.keys()
    with self.invalidated(targets, invalidate_dependents=True) as invalidation_check:
