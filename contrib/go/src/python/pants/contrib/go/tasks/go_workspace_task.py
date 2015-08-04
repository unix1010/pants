# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
from collections import defaultdict

from pants.base.build_environment import get_buildroot
from pants.util.dirutil import safe_mkdir

from pants.contrib.go.tasks.go_task import GoTask


class GoWorkspaceTask(GoTask):
  """Sets up a standard Go workspace and links Go source code to the workspace.

  Enables the use of Go tools which require a $GOPATH and correctly organized
  "src/", "pkg/", and "bin/" directories (e.g. `go install` or `go test`).

  Intended as a super class for tasks which require and maintain a Go workspace.
  """

  @classmethod
  def prepare(cls, options, round_manager):
    super(GoWorkspaceTask, cls).prepare(options, round_manager)
    round_manager.require_data('go_remote_lib_src')

  def get_gopath(self, target):
    """Returns the $GOPATH for the given target."""
    return os.path.join(self.workdir, target.id)

  def ensure_workspace(self, target):
    """Ensures that an up-to-date Go workspace exists for the given target.

    Creates any necessary symlinks to source files based on the target and its transitive
    dependencies, and removes any symlinks which do not correspond to any needed dep.
    """
    gopath = self.get_gopath(target)
    for dir in ('bin', 'pkg', 'src'):
      safe_mkdir(os.path.join(gopath, dir))
    required_links = set()
    for dep in target.closure():
      if self.is_remote_lib(dep):
        self._symlink_remote_lib(gopath, dep, required_links)
      else:
        self._symlink_local_src(gopath, dep, required_links)
    self.remove_unused_links(os.path.join(gopath, 'src'), required_links)

  def remove_unused_links(self, dir, required_links):
    """Recursively remove any links in dir which are not contained in required_links."""
    for root, _, files in os.walk(dir):
      for f in files:
        fpath = os.path.join(root, f)
        if os.path.islink(fpath) and fpath not in required_links:
          os.unlink(fpath)

  def _symlink_local_src(self, gopath, go_local_src, required_links):
    """Creates symlinks from the given gopath to the source files of the given local package.

    Also duplicates directory structure leading to source files of package within
    gopath, in order to provide isolation to the package.

    Adds the symlinks to the source files to required_links.
    """
    src_dir = os.path.join(gopath, 'src', go_local_src.address.spec_path)
    safe_mkdir(src_dir)
    for src in go_local_src.sources_relative_to_buildroot():
      src_link = os.path.join(src_dir, os.path.basename(src))
      if not os.path.islink(src_link):
        os.symlink(os.path.join(get_buildroot(), src), src_link)
      required_links.add(src_link)

  def _symlink_remote_lib(self, gopath, go_remote_lib, required_links):
    """Creates a symlink from the given gopath to the directory of the given remote library.

    Adds the symlink to the remote lib to required_links.
    """
    # Transforms github.com/user/lib --> $GOPATH/src/github.com/user
    remote_lib_dir = os.path.join(gopath,
                                  'src',
                                  os.path.dirname(self.global_import_id(go_remote_lib)))
    safe_mkdir(remote_lib_dir)
    remote_lib_source_dir = self.context.products.get_data('go_remote_lib_src')[go_remote_lib]
    remote_lib_link = os.path.join(remote_lib_dir,
                                   os.path.basename(remote_lib_source_dir))
    if not os.path.islink(remote_lib_link):
      os.symlink(remote_lib_source_dir, remote_lib_link)
    required_links.add(remote_lib_link)
