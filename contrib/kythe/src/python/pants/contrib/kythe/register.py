# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.contrib.kythe.tasks.extract_java import ExtractJava
from pants.contrib.kythe.tasks.index_java import IndexJava
from pants.contrib.kythe.tasks.index_scala import IndexScala
from pants.goal.task_registrar import TaskRegistrar as task



def register_goals():
  task(name='extract', action=ExtractJava).install('kythe')
  task(name='index-java', action=IndexJava).install('kythe')
  task(name='index-scala', action=IndexScala).install('kythe')
