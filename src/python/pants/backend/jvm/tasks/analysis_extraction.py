# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os

from pants.backend.jvm.subsystems.dependency_context import DependencyContext
from pants.backend.jvm.subsystems.zinc import Zinc
from pants.backend.jvm.tasks.nailgun_task import NailgunTask


class AnalysisExtraction(NailgunTask):
  """A task that handles extracting product and dependency information from zinc analysis."""

  cache_target_dirs = True

  @classmethod
  def subsystem_dependencies(cls):
    return super(AnalysisExtraction, cls).subsystem_dependencies() + (DependencyContext, Zinc)

  @classmethod
  def register_options(cls, register):
    super(AnalysisExtraction, cls).register_options(register)

    register('--unused-deps', choices=['ignore', 'warn', 'fatal'], default='ignore',
             fingerprint=True,
             help='Controls whether unused deps are checked, and whether they cause warnings or '
                  'errors. This option uses zinc\'s analysis to determine which deps are unused, '
                  'and can thus result in false negatives: thus it is disabled by default.')

  @classmethod
  def prepare(cls, options, round_manager):
    super(AnalysisExtraction, cls).prepare(options, round_manager)
    round_manager.require_data('zinc_analysis')
    round_manager.require_data('runtime_classpath')

  @classmethod
  def product_types(cls):
    return ['classes_by_source', 'product_deps_by_src']

  def _mk_dep_analyzer(self):
    return JvmDependencyAnalyzer(get_buildroot(),
                                 self.context.products.get_data('runtime_classpath'),
                                 self.context.products.get_data('product_deps_by_src'))

  def _create_empty_products(self):
    if self.context.products.is_required_data('classes_by_source'):
      make_products = lambda: defaultdict(MultipleRootedProducts)
      self.context.products.safe_create_data('classes_by_source', make_products)

    if self.context.products.is_required_data('product_deps_by_src') \
        or self._unused_deps_check_enabled:
      self.context.products.safe_create_data('product_deps_by_src', dict)

  @property
  def _unused_deps_check_enabled(self):
    return self.get_options().unused_deps != 'ignore'

  def _check_unused_deps(self, dep_analyzer, target):
    """Uses `product_deps_by_src` to check unused deps and warn or error."""
    with self.context.new_workunit('unused-check', labels=[WorkUnitLabel.COMPILER]):
      # Compute replacement deps.
      replacement_deps = dep_analyzer.compute_unused_deps(target)

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
      if self.get_options().unused_deps == 'fatal':
        raise TaskError(unused_msg)
      else:
        self.context.log.warn('Target {} had {}\n'.format(target.address.spec, unused_msg))

  def execute(self):
    self._create_empty_products()

    zinc_analysis = self.context.products.get_data('zinc_analysis')
    classpath_product = self.context.products.get_data('runtime_classpath')
    fingerprint_strategy = DependencyContext.global_instance().create_fingerprint_strategy(
        classpath_product)

    targets = zinc_analysis.keys()
    with self.invalidated(targets,
                          fingerprint_strategy=fingerprint_strategy,
                          invalidate_dependents=True) as invalidation_check:
      # Parse products for any relevant targets.
      for vt in invalidation_check.all_vts:
        if not vt.valid:
          pass

      # Once all products are parsed, if the unused deps check is enabled, run it for
      # each target.
      if self._unused_deps_check_enabled:
        dep_analyzer = self._mk_dep_analyzer()
        for vt in invalidation_check.invalid_vts:
          self._check_unused_deps(dep_analyzer, vt.target)

  def _register_vts(self, compile_contexts):
    classes_by_source = self.context.products.get_data('classes_by_source')
    product_deps_by_src = self.context.products.get_data('product_deps_by_src')
    zinc_args = self.context.products.get_data('zinc_args')

    # Register a mapping between sources and classfiles (if requested).
    if classes_by_source is not None:
      ccbsbc = self.compute_classes_by_source(compile_contexts).items()
      for compile_context, computed_classes_by_source in ccbsbc:
        classes_dir = compile_context.classes_dir

        for source in compile_context.sources:
          classes = computed_classes_by_source.get(source, [])
          classes_by_source[source].add_abs_paths(classes_dir, classes)

    # Register classfile product dependencies (if requested).
    if product_deps_by_src is not None:
      for compile_context in compile_contexts:
        product_deps_by_src[compile_context.target] = \
            self._analysis_parser.parse_deps_from_path(compile_context.analysis_file)

  def _compute_classes_by_source(self, compile_contexts):
    """Compute a map of (context->(src->classes)) for the given compile_contexts.

    It's possible (although unfortunate) for multiple targets to own the same sources, hence
    the top level division. Srcs are relative to buildroot. Classes are absolute paths.

    Returning classes with 'None' as their src indicates that the compiler analysis indicated
    that they were un-owned. This case is triggered when annotation processors generate
    classes (or due to bugs in classfile tracking in zinc/jmake.)
    """
    buildroot = get_buildroot()
    # Build a mapping of srcs to classes for each context.
    classes_by_src_by_context = defaultdict(dict)
    for compile_context in compile_contexts:
      # Walk the context's jar to build a set of unclaimed classfiles.
      unclaimed_classes = set()
      with compile_context.open_jar(mode='r') as jar:
        for name in jar.namelist():
          if not name.endswith('/'):
            unclaimed_classes.add(os.path.join(compile_context.classes_dir, name))

      # Grab the analysis' view of which classfiles were generated.
      classes_by_src = classes_by_src_by_context[compile_context]
      if os.path.exists(compile_context.analysis_file):
        # TODO: Need to support (optionally) writing out a JSON version of the products.
        products = {}
        #products = self._analysis_parser.parse_products_from_path(compile_context.analysis_file,
        #                                                          compile_context.classes_dir)
        for src, classes in products.items():
          relsrc = os.path.relpath(src, buildroot)
          classes_by_src[relsrc] = classes
          unclaimed_classes.difference_update(classes)

      # Any remaining classfiles were unclaimed by sources/analysis.
      classes_by_src[None] = list(unclaimed_classes)
    return classes_by_src_by_context
