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

from pants.backend.jvm.subsystems.dependency_context import DependencyContext
from pants.backend.jvm.subsystems.zinc import Zinc


class AnalysisExtraction(NailgunTask):
  """A task that handles extracting product and dependency information from zinc analysis."""

  cache_target_dirs = True

  @classmethod
  def subsystem_dependencies(cls):
    return super(AnalysisExtraction, cls).subsystem_dependencies() + (DependencyContext, Zinc)


    return ResolvedJarAwareFingerprintStrategy(classpath_products, self._dep_context)

  @classmethod
  def prepare(cls, options, round_manager):
    super(AnalysisExtraction, cls).prepare(options, round_manager)
    round_manager.require_data('zinc_analysis')
    round_manager.require_data('runtime_classpath')

  def execute(self):
    zinc_analysis = self.context.products.get_data('zinc_analysis')
    classpath_products = self.context.products.get_data('runtime_classpath')
    fingerprint_strategy = self._fingerprint_strategy(classpath_products)

    targets = zinc_analysis.keys()
    with self.invalidated(targets, invalidate_dependents=True) as invalidation_check:
