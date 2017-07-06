# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.backend.jvm.subsystems.dependency_context import DependencyContext
from pants.backend.jvm.tasks.jvm_dependency_analyzer import JvmDependencyAnalyzer
from pants.base.build_environment import get_buildroot
from pants.base.workunit import WorkUnitLabel
from pants.task.task import Task
from pants.util.memo import memoized_property


class UnusedDeps(Task):
  """A task that handles extracting product and dependency information from zinc analysis."""

  cache_target_dirs = True

  @classmethod
  def subsystem_dependencies(cls):
    return super(UnusedDeps, cls).subsystem_dependencies() + (DependencyContext,)

  @classmethod
  def register_options(cls, register):
    super(UnusedDeps, cls).register_options(register)

    register('--mode', choices=['ignore', 'warn', 'fatal'], default='ignore',
             fingerprint=True,
             help='Controls whether unused deps are checked, and whether they cause warnings or '
                  'errors. This option uses zinc\'s analysis to determine which deps are unused '
                  'and can result in false negatives: thus, it is disabled by default.')

  @classmethod
  def prepare(cls, options, round_manager):
    super(UnusedDeps, cls).prepare(options, round_manager)
    if cls._enabled(options):
      round_manager.require_data('product_deps_by_src')
      round_manager.require_data('runtime_classpath')
      round_manager.require_data('zinc_analysis')

  @memoized_property
  def _dep_analyzer(self):
    return JvmDependencyAnalyzer(get_buildroot(),
                                 self.context.products.get_data('runtime_classpath'),
                                 self.context.products.get_data('product_deps_by_src'))

  @classmethod
  def _enabled(cls, options):
    return options.mode != 'ignore'

  def execute(self):
    if not self._enabled(self.get_options()):
      return

    zinc_analysis = self.context.products.get_data('zinc_analysis')
    classpath_product = self.context.products.get_data('runtime_classpath')
    product_deps_by_src = self.context.products.get_data('product_deps_by_src')

    fingerprint_strategy = DependencyContext.global_instance().create_fingerprint_strategy(
        classpath_product)

    targets = zinc_analysis.keys()
    with self.invalidated(targets,
                          fingerprint_strategy=fingerprint_strategy,
                          invalidate_dependents=True) as invalidation_check:
      for vt in invalidation_check.invalid_vts:
        self._check_unused_deps(vt.target)

  def _check_unused_deps(self, target):
    """Uses `product_deps_by_src` to check unused deps and warn or error."""
    # Compute replacement deps.
    replacement_deps = self._dep_analyzer.compute_unused_deps(target)

    if not replacement_deps:
      return

    # Warn or error for unused.
    def joined_dep_msg(deps):
      return '\n  '.join('\'{}\','.format(dep.address.spec) for dep in sorted(deps))
    flat_replacements = set(r for replacements in replacement_deps.values() for r in replacements)
    replacements_msg = ''
    if flat_replacements:
      replacements_msg = 'Suggested replacements:\n  {}\n'.format(joined_dep_msg(flat_replacements))
    unused_msg = (
        'unused dependencies:\n  {}\n{}'
        '(If you\'re seeing this message in error, you might need to '
        'change the `scope` of the dependencies.)'.format(
          joined_dep_msg(replacement_deps.keys()),
          replacements_msg,
        )
      )
    if self.get_options().mode == 'fatal':
      raise TaskError(unused_msg)
    else:
      self.context.log.warn('Target {} had {}\n'.format(target.address.spec, unused_msg))
