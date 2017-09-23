# coding=utf-8
# Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.engine.rules import RootRule, rule
from pants.engine.selectors import Select
from pants.util.objects import datatype


class ExecuteProcessRequest(datatype('ExecuteProcessRequest', ['argv', 'env'])):
  def __new__(cls, argv, env):
    if type(env) != dict:
      raise ValueError('ExecuteProcessRequest env must be a dict')
    # TODO: Find a cute list comprehension to flatten this
    # env_tuples = tuple((k, v) for k, v in sorted(env.items()))
    env_list = []
    for k, v in env.viewitems():
      env_list.append(k)
      env_list.append(v)
    return super(ExecuteProcessRequest, cls).__new__(cls, argv, tuple(env_list))

class ExecuteProcessResult(datatype('ExecuteProcessResult', ['stdout', 'stderr', 'exit_code'])):
  pass

def create_process_rules():
  return [execute_process_noop, RootRule(ExecuteProcessRequest)]

@rule(ExecuteProcessResult, [Select(ExecuteProcessRequest)])
def execute_process_noop(*args):
  raise Exception('This task is replaced intrinsically, and should never run.')
