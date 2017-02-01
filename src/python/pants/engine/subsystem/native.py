# coding=utf-8
# Copyright 2016 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import cffi
import threading

import pkg_resources
import six

from pants.base.project_tree import Dir, File, Link
from pants.binaries.binary_util import BinaryUtil
from pants.option.custom_types import dir_option
from pants.subsystem.subsystem import Subsystem
from pants.util.memo import memoized_property
from pants.util.objects import datatype
from pants.engine.subsystem.bootstrap import TYPEDEFS, HEADER
from pants.engine.subsystem._native_engine import ffi, lib


@ffi.def_extern()
def extern_key_for(context_handle, val):
  """Return a Key for a Value."""
  c = ffi.from_handle(context_handle)
  return c.value_to_key(val)


@ffi.def_extern()
def extern_val_for(context_handle, key):
  """Return a Value for a Key."""
  c = ffi.from_handle(context_handle)
  return c.key_to_value(key)


@ffi.def_extern()
def extern_clone_val(context_handle, val):
  """Clone the given Value."""
  c = ffi.from_handle(context_handle)
  item = c.from_value(val)
  return c.to_value(item, type_id=val.type_id)


@ffi.def_extern()
def extern_drop_handles(context_handle, handles_ptr, handles_len):
  """Drop the given Handles."""
  c = ffi.from_handle(context_handle)
  handles = ffi.unpack(handles_ptr, handles_len)
  c.drop_handles(handles)


@ffi.def_extern()
def extern_id_to_str(context_handle, id_):
  """Given an Id for `obj`, write str(obj) and return it."""
  c = ffi.from_handle(context_handle)
  return c.utf8_buf(six.text_type(c.from_id(id_)))


@ffi.def_extern()
def extern_val_to_str(context_handle, val):
  """Given a Value for `obj`, write str(obj) and return it."""
  c = ffi.from_handle(context_handle)
  return c.utf8_buf(six.text_type(c.from_value(val)))


@ffi.def_extern()
def extern_satisfied_by(context_handle, constraint_id, cls_id):
  """Given two TypeIds, return constraint.satisfied_by(cls)."""
  c = ffi.from_handle(context_handle)
  return c.from_id(constraint_id.id_).satisfied_by_type(c.from_id(cls_id.id_))


@ffi.def_extern()
def extern_store_list(context_handle, vals_ptr_ptr, vals_len, merge):
  """Given storage and an array of Values, return a new Value to represent the list."""
  c = ffi.from_handle(context_handle)
  vals = tuple(c.from_value(val) for val in ffi.unpack(vals_ptr_ptr, vals_len))
  if merge:
    # Expect each obj to represent a list, and do a de-duping merge.
    merged_set = set()
    def merged():
      for outer_val in vals:
        for inner_val in outer_val:
          if inner_val in merged_set:
            continue
          merged_set.add(inner_val)
          yield inner_val
    vals = tuple(merged())
  return c.to_value(vals)


@ffi.def_extern()
def extern_store_bytes(context_handle, bytes_ptr, bytes_len):
  """Given a context and raw bytes, return a new Value to represent the content."""
  c = ffi.from_handle(context_handle)
  return c.to_value(bytes(ffi.buffer(bytes_ptr, bytes_len)))


@ffi.def_extern()
def extern_lift_directory_listing(context_handle, directory_listing_val):
  """Given a context and a Value representing a DirectoryListing, return RawStats."""
  c = ffi.from_handle(context_handle)
  directory_listing = c.from_value(directory_listing_val)

  raw_stats_len = len(directory_listing.dependencies)
  raw_stats = ffi.new('RawStat[]', raw_stats_len)
  for i, stat in enumerate(directory_listing.dependencies):
    raw_stats[i].path = c.buf(stat.path)
    if type(stat) == Dir:
      raw_stats[i].tag = 0
    elif type(stat) == File:
      raw_stats[i].tag = 1
    elif type(stat) == Link:
      raw_stats[i].tag = 2
    else:
      raise Exception('Unrecognized stat type: {}'.format(stat))

  return (raw_stats, raw_stats_len, c.to_value(raw_stats, type_id=c.bytes_id))


@ffi.def_extern()
def extern_project(context_handle, val, field, type_id):
  """Given a Value for `obj`, a field name, and a type, project the field as a new Value."""
  c = ffi.from_handle(context_handle)
  obj = c.from_value(val)
  field_name = c.from_key(field)
  typ = c.from_id(type_id.id_)

  projected = getattr(obj, field_name)
  if type(projected) is not typ:
    projected = typ(projected)

  return c.to_value(projected)


@ffi.def_extern()
def extern_project_multi(context_handle, val, field):
  """Given a Key for `obj`, and a field name, project the field as a list of Keys."""
  c = ffi.from_handle(context_handle)
  obj = c.from_value(val)
  field_name = c.from_key(field)

  return c.vals_buf(tuple(c.to_value(p) for p in getattr(obj, field_name)))


@ffi.def_extern()
def extern_create_exception(context_handle, msg_ptr, msg_len):
  """Given a utf8 message string, create an Exception object."""
  c = ffi.from_handle(context_handle)
  msg = bytes(ffi.buffer(msg_ptr, msg_len)).decode('utf-8')
  return c.to_value(Exception(msg))


@ffi.def_extern()
def extern_invoke_runnable(context_handle, func, args_ptr, args_len, cacheable):
  """Given a destructured rawRunnable, run it."""
  c = ffi.from_handle(context_handle)
  runnable = c.from_id(func.id_)
  args = tuple(c.from_value(arg) for arg in ffi.unpack(args_ptr, args_len))

  try:
    val = runnable(*args)
    is_throw = False
  except Exception as e:
    val = e
    is_throw = True

  return RunnableComplete(c.to_value(val), is_throw)


class Value(datatype('Value', ['handle', 'type_id'])):
  """Corresponds to the native object of the same name."""


class Key(datatype('Key', ['id_', 'type_id'])):
  """Corresponds to the native object of the same name."""


class Function(datatype('Function', ['id_'])):
  """Corresponds to the native object of the same name."""


class TypeConstraint(datatype('TypeConstraint', ['id_'])):
  """Corresponds to the native object of the same name."""


class TypeId(datatype('TypeId', ['id_'])):
  """Corresponds to the native object of the same name."""


class RunnableComplete(datatype('RunnableComplete', ['value', 'is_throw'])):
  """Corresponds to the native object of the same name."""


class ExternContext(object):
  """A wrapper around python objects used in static extern functions in this module.

  In the native context, python objects are identified by an unsigned-integer Id which is
  assigned and memoized here. Note that this is independent-from and much-lighter-than
  the Digest computed when an object is stored via storage.py (which is generally only necessary
  for multi-processing or cache lookups).
  """

  def __init__(self):
    # A handle to this object to ensure that the native wrapper survives at least as
    # long as this object.
    self.handle = ffi.new_handle(self)

    # The native code will invoke externs concurrently, so locking is needed around
    # datastructures in this context.
    self._lock = threading.RLock()

    # Memoized object Ids.
    self._id_generator = 0
    self._id_to_obj = dict()
    self._obj_to_id = dict()
    self.bytes_id = TypeId(self.to_id(bytes))

    # An anonymous Id for Values that keep *Buffers alive.
    self.anon_id = TypeId(self.to_id(int))

    # Outstanding FFI object handles.
    self._handles = set()

  def buf(self, bytestring):
    buf = ffi.new('uint8_t[]', bytestring)
    return (buf, len(bytestring), self.to_value(buf, type_id=self.anon_id))

  def utf8_buf(self, string):
    return self.buf(string.encode('utf-8'))

  def vals_buf(self, keys):
    buf = ffi.new('Value[]', keys)
    return (buf, len(keys), self.to_value(buf, type_id=self.anon_id))

  def to_value(self, obj, type_id=None):
    handle = ffi.new_handle(obj)
    self._handles.add(handle)
    type_id = type_id or TypeId(self.to_id(type(obj)))
    return Value(handle, type_id)

  def from_value(self, val):
    return ffi.from_handle(val.handle)

  def drop_handles(self, handles):
    self._handles -= set(handles)

  def put(self, obj):
    with self._lock:
      # If we encounter an existing id, return it.
      new_id = self._id_generator
      _id = self._obj_to_id.setdefault(obj, new_id)
      if _id is not new_id:
        # Object already existed.
        return _id

      # Object is new/unique.
      self._id_to_obj[_id] = obj
      self._id_generator += 1
      return _id

  def get(self, id_):
    return self._id_to_obj[id_]

  def to_id(self, typ):
    return self.put(typ)

  def value_to_key(self, val):
    obj = self.from_value(val)
    type_id = TypeId(val.type_id.id_)
    return Key(self.put(obj), type_id)

  def key_to_value(self, key):
    return self.to_value(self.get(key.id_), type_id=key.type_id)

  def to_key(self, obj):
    type_id = TypeId(self.put(type(obj)))
    return Key(self.put(obj), type_id)

  def from_id(self, cdata):
    return self.get(cdata)

  def from_key(self, cdata):
    return self.get(cdata.id_)


class Native(object):
  """Encapsulates fetching a platform specific version of the native portion of the engine.
  """

  class Factory(Subsystem):
    options_scope = 'native-engine'

    @classmethod
    def subsystem_dependencies(cls):
      return (BinaryUtil.Factory,)

    @staticmethod
    def _default_native_engine_version():
      return pkg_resources.resource_string(__name__, 'native_engine_version').strip()

    @classmethod
    def register_options(cls, register):
      register('--version', advanced=True, default=cls._default_native_engine_version(),
               help='Native engine version.')
      register('--supportdir', advanced=True, default='bin/native-engine',
               help='Find native engine binaries under this dir. Used as part of the path to '
                    'lookup the binary with --binary-util-baseurls and --pants-bootstrapdir.')
      register('--visualize-to', default=None, type=dir_option,
               help='A directory to write execution graphs to as `dot` files. The contents '
                    'of the directory will be overwritten if any filenames collide.')

    def create(self):
      binary_util = BinaryUtil.Factory.create()
      options = self.get_options()
      return Native(binary_util, options.version, options.supportdir, options.visualize_to)

  def __init__(self, binary_util, version, supportdir, visualize_to_dir):
    """
    :param binary_util: The BinaryUtil subsystem instance for binary retrieval.
    :param version: The binary version of the native engine.
    :param supportdir: The supportdir for the native engine.
    :param visualize_to_dir: An existing directory (or None) to visualize executions to.
    """
    self._binary_util = binary_util
    self._version = version
    self._supportdir = supportdir
    self._visualize_to_dir = visualize_to_dir

  @property
  def visualize_to_dir(self):
    return self._visualize_to_dir

  @memoized_property
  def lib(self):
    """Return the `native-engine` module."""
    return lib

  @memoized_property
  def context(self):
    # We statically initialize a ExternContext to correspond to the queue of dropped
    # Handles that the native code maintains.
    return ffi.init_once(ExternContext, 'ExternContext singleton')

  def new(self, cdecl, init):
    return ffi.new(cdecl, init)

  def gc(self, cdata, destructor):
    """Register a method to be called when `cdata` is garbage collected.

    Returns a new reference that should be used in place of `cdata`.
    """
    return ffi.gc(cdata, destructor)

  def unpack(self, cdata_ptr, count):
    """Given a pointer representing an array, and its count of entries, return a list."""
    return ffi.unpack(cdata_ptr, count)

  def buffer(self, cdata):
    return ffi.buffer(cdata)

  def new_scheduler(self,
                    construct_snapshot,
                    construct_path_stat,
                    construct_dir,
                    construct_file,
                    construct_link,
                    constraint_has_products,
                    constraint_address,
                    constraint_variants,
                    constraint_path_globs,
                    constraint_snapshot,
                    constraint_read_link,
                    constraint_directory_listing,
                    constraint_dir,
                    constraint_file,
                    constraint_link):
    """Create and return an ExternContext and native Scheduler."""

    def tc(constraint):
      return TypeConstraint(self.context.to_id(constraint))

    scheduler =\
      self.lib.scheduler_create(
        # Context.
        self.context.handle,
        # Externs.
        lib.extern_key_for,
        lib.extern_val_for,
        lib.extern_clone_val,
        lib.extern_drop_handles,
        lib.extern_id_to_str,
        lib.extern_val_to_str,
        lib.extern_satisfied_by,
        lib.extern_store_list,
        lib.extern_store_bytes,
        lib.extern_lift_directory_listing,
        lib.extern_project,
        lib.extern_project_multi,
        lib.extern_create_exception,
        lib.extern_invoke_runnable,
        # Field names.
        # TODO: See https://github.com/pantsbuild/pants/issues/4207
        self.context.to_key('name'),
        self.context.to_key('products'),
        self.context.to_key('default'),
        self.context.to_key('include'),
        self.context.to_key('exclude'),
        self.context.to_key('dependencies'),
        self.context.to_key('path'),
        # Constructors/functions.
        Function(self.context.to_id(construct_snapshot)),
        Function(self.context.to_id(construct_path_stat)),
        Function(self.context.to_id(construct_dir)),
        Function(self.context.to_id(construct_file)),
        Function(self.context.to_id(construct_link)),
        # TypeConstraints.
        tc(constraint_address),
        tc(constraint_has_products),
        tc(constraint_variants),
        tc(constraint_path_globs),
        tc(constraint_snapshot),
        tc(constraint_read_link),
        tc(constraint_directory_listing),
        tc(constraint_dir),
        tc(constraint_file),
        tc(constraint_link),
      )
    return self.gc(scheduler, self.lib.scheduler_destroy)
