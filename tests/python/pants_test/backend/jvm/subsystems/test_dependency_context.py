# coding=utf-8
# Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import mock

from pants.backend.jvm.subsystems.dependency_context import DependencyContext
from pants.backend.jvm.targets.java_library import JavaLibrary
from pants_test.base_test import BaseTest
from pants_test.subsystem.subsystem_util import init_subsystem


class CompileContextTest(BaseTest):
  def generate_targets(self):
    self.lib_aa = self.make_target(
      'com/foo:AA',
      target_type=JavaLibrary,
      sources=['com/foo/AA.scala'],
    )

    self.lib_a = self.make_target(
      'com/foo:A',
      target_type=JavaLibrary,
      sources=['com/foo/A.scala'],
    )

    self.lib_b = self.make_target(
      'com/foo:B',
      target_type=JavaLibrary,
      sources=['com/foo/B.scala'],
      dependencies=[self.lib_a, self.lib_aa],
      exports=[':A'],
    )

    self.lib_c = self.make_target(
      'com/foo:C',
      target_type=JavaLibrary,
      sources=['com/foo/C.scala'],
      dependencies=[self.lib_b],
      exports=[':B'],
    )

    self.lib_c_alias = self.make_target(
      'com/foo:C_alias',
      dependencies=[self.lib_c],
    )

    self.lib_d = self.make_target(
      'com/foo:D',
      target_type=JavaLibrary,
      sources=['com/foo/D.scala'],
      dependencies=[self.lib_c_alias],
      exports=[':C_alias'],
    )

    self.lib_e = self.make_target(
      'com/foo:E',
      target_type=JavaLibrary,
      sources=['com/foo/E.scala'],
      dependencies=[self.lib_d],
    )

  def test_resolve_logic(self):
    self.generate_targets()
    init_subsystem(DependencyContext)
    dep_context = DependencyContext.global_instance()
    def strict_dependencies(t):
      return dep_context.strict_dependencies(t)
    self.assertEqual(set(strict_dependencies(self.lib_b)), {self.lib_a, self.lib_aa})
    self.assertEqual(set(strict_dependencies(self.lib_c)), {self.lib_b, self.lib_a})
    self.assertEqual(set(strict_dependencies(self.lib_c_alias)), {self.lib_c, self.lib_b, self.lib_a})
    self.assertEqual(set(strict_dependencies(self.lib_d)), {self.lib_c, self.lib_b, self.lib_a})
    self.assertEqual(set(strict_dependencies(self.lib_e)), {self.lib_d, self.lib_c, self.lib_b, self.lib_a})
