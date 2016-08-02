# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

python_library(
  name = 'engine',
  sources = ['engine.py'],
  dependencies = ['3rdparty/python:blessed']
)

python_binary(
  name = 'engine_bin',
  dependencies = [':engine'],
  entry_point = 'pants.ui.engine:main'
)
