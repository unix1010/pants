# coding=utf-8
# Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os

from pants.backend.jvm.subsystems.jvm import JVM
from pants.backend.jvm.tasks.nailgun_task import NailgunTask
from pants.base.exceptions import TaskError
from pants.base.workunit import WorkUnitLabel
from pants.java.jar.jar_dependency import JarDependency
from pants.util.dirutil import safe_mkdir
from pants.util.memo import memoized_property
from pants.contrib.kythe.subsystems.kythe import Kythe

from pants.backend.jvm.targets.scala_jar_dependency import ScalaJarDependency


class IndexScala(NailgunTask):
  _SCALAMETA_INDEXER_MAIN = 'org.pantsbuild.scalameta.kythe.Indexer'
  _SCALAHOST_TOOL = 'scalahost-nsc'

  cache_target_dirs = True

  @classmethod
  def subsystem_dependencies(cls):
    return super(IndexScala, cls).subsystem_dependencies() + (Kythe,)

  @classmethod
  def product_types(cls):
    return ['kythe_entries_files']

  @classmethod
  def prepare(cls, options, round_manager):
    super(IndexScala, cls).prepare(options, round_manager)
    round_manager.require_data('runtime_classpath')

  @classmethod
  def register_options(cls, register):
    super(IndexScala, cls).register_options(register)
    cls.register_jvm_tool(register,
                          'kythe-scala-indexer',
                          classpath=[ScalaJarDependency('org.pantsbuild.scalameta.kythe',
                                                        'kythe-indexer',
                                                        '1492363605')],
                          main=cls._SCALAMETA_INDEXER_MAIN)
    cls.register_jvm_tool(register,
                          cls._SCALAHOST_TOOL,
                          # NB: This dependency is full-versioned to match the compiler, so we
                          # might not be able to ship it with pants.
                          classpath=[JarDependency('org.scalameta',
                                                   'scalahost-nsc_2.11.10',
                                                   '1.8.0-520-f6d600cd.1492126021620')])

  @property
  def cache_target_dirs(self):
    return True

  @memoized_property
  def _scalahost_nsc(self):
    jars = self.tool_classpath(cls._SCALAHOST_TOOL)
    if len(jars) != 1:
      raise TaskError('Expected exactly one jar for the `{}` tool. Got: {}'.format(
        cls._SCALAHOST_TOOL, jars))
    return jars[0]

  def _is_indexed(self, target):
    return ...

  def execute(self):
    def entries_file(_vt):
      return os.path.join(_vt.results_dir, 'index.entries')

    with self.invalidated(self.context.targets(predicate=self._is_indexed),
                          invalidate_dependents=True) as invalidation_check:
      for vt in invalidation_check.all_vts:
        dest = entries_file(vt)
        if not vt.valid:
          self._index(vt, dest)
        self.context.products.get_data('kythe_entries_files', dict)[vt.target] = dest

  def _index(self, vt, entries_file):
    classpath_products = self.context.products.get_data('runtime_classpath')
    corpus = Kythe.global_instance().get_options().corpus
    self.context.log.info('Kythe indexing {}'.format(vt.target.address.spec))

    target_classpath = ClasspathUtils.classpath(target.closure(bfs=True))
    args = [
        '--classpath={}'.format(os.pathsep.join(target_classpath)),
        '--pluginpath={}'.format(self._scalahost_nsc),
        '--out={}'.format(entries_file),
        '--corpus={}'.format(corpus),
        # The source_root of the target.
        '--root={}'.format(vt.target.target_base),
        '--sourcepath={}'.format(','.join(vt.target.sources_relative_to_buildroot())),
      ]
    result = self.runjava(classpath=self.tool_classpath('kythe-scala-indexer'),
                          main=self._SCALAMETA_INDEXER_MAIN,
                          jvm_options=self.get_options().jvm_options,
                          args=args, workunit_name='kythe-index',
                          workunit_labels=[WorkUnitLabel.COMPILER])
    if result != 0:
      raise TaskError('java {main} ... exited non-zero ({result})'.format(
        main=self._SCALAMETA_INDEXER_MAIN, result=result))