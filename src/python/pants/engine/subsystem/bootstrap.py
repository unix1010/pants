import cffi

ffibuilder = cffi.FFI()

ffibuilder.cdef('''
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
      bool   is_throw;
    } RunnableComplete;

    typedef uint64_t EntryId;

    typedef void ExternContext;

    extern "Python" Key              extern_key_for(ExternContext*, Value*);
    extern "Python" Value            extern_val_for(ExternContext*, Key*);
    extern "Python" Value            extern_clone_val(ExternContext*, Value*);
    extern "Python" void             extern_drop_handles(ExternContext*, Handle*, uint64_t);
    extern "Python" Buffer           extern_id_to_str(ExternContext*, Id);
    extern "Python" Buffer           extern_val_to_str(ExternContext*, Value*);
    extern "Python" bool             extern_satisfied_by(ExternContext*, TypeConstraint*, TypeId*);
    extern "Python" Value            extern_store_list(ExternContext*, Value**, uint64_t, bool);
    extern "Python" Value            extern_store_bytes(ExternContext*, uint8_t*, uint64_t);
    extern "Python" RawStats         extern_lift_directory_listing(ExternContext*, Value*);
    extern "Python" Value            extern_project(ExternContext*, Value*, Field*, TypeId*);
    extern "Python" ValueBuffer      extern_project_multi(ExternContext*, Value*, Field*);
    extern "Python" Value            extern_create_exception(ExternContext*, uint8_t*, uint64_t);
    extern "Python" RunnableComplete extern_invoke_runnable(ExternContext*, Function*, Value*, uint64_t, bool);

    typedef Key              (*extern_ptr_key_for)(ExternContext*, Value*);
    typedef Value            (*extern_ptr_val_for)(ExternContext*, Key*);
    typedef Value            (*extern_ptr_clone_val)(ExternContext*, Value*);
    typedef void             (*extern_ptr_drop_handles)(ExternContext*, Handle*, uint64_t);
    typedef Buffer           (*extern_ptr_id_to_str)(ExternContext*, Id);
    typedef Buffer           (*extern_ptr_val_to_str)(ExternContext*, Value*);
    typedef bool             (*extern_ptr_satisfied_by)(ExternContext*, TypeConstraint*, TypeId*);
    typedef Value            (*extern_ptr_store_list)(ExternContext*, Value**, uint64_t, bool);
    typedef Value            (*extern_ptr_store_bytes)(ExternContext*, uint8_t*, uint64_t);
    typedef RawStats         (*extern_ptr_lift_directory_listing)(ExternContext*, Value*);
    typedef Value            (*extern_ptr_project)(ExternContext*, Value*, Field*, TypeId*);
    typedef ValueBuffer      (*extern_ptr_project_multi)(ExternContext*, Value*, Field*);
    typedef Value            (*extern_ptr_create_exception)(ExternContext*, uint8_t*, uint64_t);
    typedef RunnableComplete (*extern_ptr_invoke_runnable)(ExternContext*, Function*, Value*, uint64_t, bool);

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
    void task_add_select_dependencies(RawScheduler*, TypeConstraint, TypeConstraint, Field, bool);
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
                                                bool);
    ExecutionStat execution_execute(RawScheduler*);
    RawNodes* execution_roots(RawScheduler*);

    void nodes_destroy(RawNodes*);
    ''')

# NB: We set no source, because we don't actually have a header for the rust code.
ffibuilder.set_source("_my_example", "")
