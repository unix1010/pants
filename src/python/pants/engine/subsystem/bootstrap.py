# coding=utf-8
# Copyright 2017 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os

import cffi

from pants.util.contextutil import temporary_dir
from pants.util.fileutil import atomic_copy

TYPEDEFS = '''
    typedef uint64_t   Id;
    typedef void*      Handle;

    typedef struct {
      Id id_;
    } TypeId;

    typedef struct {
      Id id_;
    } TypeConstraint;

    typedef struct {
      Id id_;
    } Function;

    typedef struct {
      Handle   handle;
      TypeId   type_id;
    } Value;

    typedef struct {
      Id       id_;
      TypeId   type_id;
    } Key;

    typedef Key Field;

    typedef struct {
      uint8_t*  bytes_ptr;
      uint64_t  bytes_len;
      Value     handle_;
    } Buffer;

    typedef struct {
      Value*     values_ptr;
      uint64_t   values_len;
      Value      handle_;
    } ValueBuffer;

    typedef struct {
      Buffer       path;
      uint8_t      tag;
    } RawStat;

    typedef struct {
      RawStat*     stats_ptr;
      uint64_t     stats_len;
      Value        _value;
    } RawStats;

    typedef struct {
      Value  value;
      _Bool   is_throw;
    } RunnableComplete;

    typedef uint64_t EntryId;

    typedef void ExternContext;

    typedef void RawScheduler;

    typedef struct {
      uint64_t runnable_count;
      uint64_t scheduling_iterations;
    } ExecutionStat;

    typedef struct {
      Key             subject;
      TypeConstraint  product;
      uint8_t         state_tag;
      Value           state_value;
    } RawNode;

    typedef struct {
      RawNode*  nodes_ptr;
      uint64_t  nodes_len;
      // NB: there are more fields in this struct, but we can safely (?)
      // ignore them because we never have collections of this type.
    } RawNodes;

    typedef Key              (*extern_ptr_key_for)(ExternContext*, Value*);
    typedef Value            (*extern_ptr_val_for)(ExternContext*, Key*);
    typedef Value            (*extern_ptr_clone_val)(ExternContext*, Value*);
    typedef void             (*extern_ptr_drop_handles)(ExternContext*, Handle*, uint64_t);
    typedef Buffer           (*extern_ptr_id_to_str)(ExternContext*, Id);
    typedef Buffer           (*extern_ptr_val_to_str)(ExternContext*, Value*);
    typedef _Bool            (*extern_ptr_satisfied_by)(ExternContext*, TypeConstraint*, TypeId*);
    typedef Value            (*extern_ptr_store_list)(ExternContext*, Value**, uint64_t, _Bool);
    typedef Value            (*extern_ptr_store_bytes)(ExternContext*, uint8_t*, uint64_t);
    typedef RawStats         (*extern_ptr_lift_directory_listing)(ExternContext*, Value*);
    typedef Value            (*extern_ptr_project)(ExternContext*, Value*, Field*, TypeId*);
    typedef ValueBuffer      (*extern_ptr_project_multi)(ExternContext*, Value*, Field*);
    typedef Value            (*extern_ptr_create_exception)(ExternContext*, uint8_t*, uint64_t);
    typedef RunnableComplete (*extern_ptr_invoke_runnable)(ExternContext*, Function*, Value*, uint64_t, _Bool);
'''

HEADER = '''
    RawScheduler* scheduler_create(ExternContext*,
                                   extern_ptr_key_for,
                                   extern_ptr_val_for,
                                   extern_ptr_clone_val,
                                   extern_ptr_drop_handles,
                                   extern_ptr_id_to_str,
                                   extern_ptr_val_to_str,
                                   extern_ptr_satisfied_by,
                                   extern_ptr_store_list,
                                   extern_ptr_store_bytes,
                                   extern_ptr_lift_directory_listing,
                                   extern_ptr_project,
                                   extern_ptr_project_multi,
                                   extern_ptr_create_exception,
                                   extern_ptr_invoke_runnable,
                                   Field,
                                   Field,
                                   Field,
                                   Field,
                                   Field,
                                   Field,
                                   Field,
                                   Function,
                                   Function,
                                   Function,
                                   Function,
                                   Function,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint,
                                   TypeConstraint);
    void scheduler_destroy(RawScheduler*);

    void intrinsic_task_add(RawScheduler*, Function, TypeId, TypeConstraint, TypeConstraint);
    void singleton_task_add(RawScheduler*, Function, TypeConstraint);

    void task_add(RawScheduler*, Function, TypeConstraint);
    void task_add_select(RawScheduler*, TypeConstraint);
    void task_add_select_variant(RawScheduler*, TypeConstraint, Buffer);
    void task_add_select_literal(RawScheduler*, Key, TypeConstraint);
    void task_add_select_dependencies(RawScheduler*, TypeConstraint, TypeConstraint, Field, _Bool);
    void task_add_select_projection(RawScheduler*, TypeConstraint, TypeConstraint, Field, TypeConstraint);
    void task_end(RawScheduler*);

    uint64_t graph_len(RawScheduler*);
    uint64_t graph_invalidate(RawScheduler*, Key*, uint64_t);
    void graph_visualize(RawScheduler*, char*);
    void graph_trace(RawScheduler*, char*);


    void execution_reset(RawScheduler*);
    void execution_add_root_select(RawScheduler*, Key, TypeConstraint);
    void execution_add_root_select_dependencies(RawScheduler*,
                                                Key,
                                                TypeConstraint,
                                                TypeConstraint,
                                                Field,
                                                _Bool);
    ExecutionStat execution_execute(RawScheduler*);
    RawNodes* execution_roots(RawScheduler*);

    void nodes_destroy(RawNodes*);
'''

BINARY_NAME = '_native_engine'
BINARY_ENGINE_NAME = 'engine'

if __name__ == '__main__':
  """Define and compile the static functions that will later be filled in by `@ffi.def_extern`."""

  binary_filename = '{}.so'.format(BINARY_NAME)
  engine_binary_filename = 'lib{}.so'.format(BINARY_ENGINE_NAME)

  ffibuilder = cffi.FFI()

  ffibuilder.cdef(TYPEDEFS + HEADER + '''
      extern "Python" Key              extern_key_for(ExternContext*, Value*);
      extern "Python" Value            extern_val_for(ExternContext*, Key*);
      extern "Python" Value            extern_clone_val(ExternContext*, Value*);
      extern "Python" void             extern_drop_handles(ExternContext*, Handle*, uint64_t);
      extern "Python" Buffer           extern_id_to_str(ExternContext*, Id);
      extern "Python" Buffer           extern_val_to_str(ExternContext*, Value*);
      extern "Python" _Bool            extern_satisfied_by(ExternContext*, TypeConstraint*, TypeId*);
      extern "Python" Value            extern_store_list(ExternContext*, Value**, uint64_t, _Bool);
      extern "Python" Value            extern_store_bytes(ExternContext*, uint8_t*, uint64_t);
      extern "Python" RawStats         extern_lift_directory_listing(ExternContext*, Value*);
      extern "Python" Value            extern_project(ExternContext*, Value*, Field*, TypeId*);
      extern "Python" ValueBuffer      extern_project_multi(ExternContext*, Value*, Field*);
      extern "Python" Value            extern_create_exception(ExternContext*, uint8_t*, uint64_t);
      extern "Python" RunnableComplete extern_invoke_runnable(ExternContext*, Function*, Value*, uint64_t, _Bool);
      ''')

  # TODO: Can't use `__file__`, because this code runs inside a pex chroot.
  build_root = os.getcwd()
  with temporary_dir() as tmpdir:
    # Copy the engine binary into the temporary build directory.
    atomic_copy(os.path.join(build_root, 'src/rust/engine/target/release', binary_engine_filename),
                os.path.join(tmpdir, binary_engine_filename))

    # Compile against the engine binary.
    ffibuilder.set_source(
        BINARY_NAME,
        TYPEDEFS + HEADER,
        libraries=[BINARY_ENGINE_NAME],
      )
    ffibuilder.compile(tmpdir=tmpdir, verbose=True)

    # Copy both binaries to the dest.
    for filename in (binary_filename, engine_binary_filename):
      atomic_copy(os.path.join(tmpdir, filename),
                  os.path.join(build_root, 'src/python/pants/engine/subsystem', filename))
