# Value-flow evaluation matrix

Analyzer revision: `b1545c294cd134421f0bf7227a1019573e0d0adf`; Python: `3.13.9`.

83 entry cases. Semantic gold is manually specified; unknown absence is not a no-flow proof.

| Dimension | Checks | Outcomes |
|---|---:|---|
| binding | 54 | matched=46, unresolved=8 |
| boundary | 6 | matched=6 |
| call_inventory | 82 | matched=81, mismatch=1 |
| call_presence | 41 | matched=40, mismatch=1 |
| call_return | 41 | negative_no_path=7, positive_found=32, positive_missing=1, unresolved=1 |
| entry_return | 137 | negative_flow_reported=6, negative_no_path=56, positive_found=61, positive_missing=14 |
| parameter_flow | 65 | negative_no_path=17, positive_found=37, unresolved=11 |
| receiver_flow | 7 | positive_found=4, unresolved=3 |
| target | 39 | matched=34, unresolved=5 |

## Cases

| Case | Category | Checks | Gaps |
|---|---|---:|---:|
| binding.positional_only | binding/positional | 12 | 0 |
| binding.keyword_only | binding/keyword | 11 | 0 |
| binding.default_argument | binding/default | 11 | 0 |
| binding.variadic_argument | binding/varargs | 12 | 1 |
| binding.variadic_keyword | binding/kwargs | 10 | 1 |
| binding.literal_star | binding/expansion | 10 | 5 |
| binding.star_and_keyword | binding/expansion | 9 | 4 |
| binding.literal_keywords | binding/expansion | 11 | 0 |
| binding.module_alias | binding/imports | 7 | 0 |
| binding.function_alias | binding/imports | 7 | 0 |
| binding.reexport_chain | binding/imports | 7 | 0 |
| binding.local_alias | binding/alias | 7 | 4 |
| binding.rebound_import | binding/unknown | 4 | 0 |
| binding.repeated_calls | binding/context | 15 | 0 |
| binding.instance_receiver | dispatch/receiver | 11 | 0 |
| binding.receiver_alias | dispatch/receiver | 11 | 0 |
| binding.static_descriptor | dispatch/descriptor | 7 | 4 |
| binding.class_descriptor | dispatch/descriptor | 9 | 6 |
| binding.inherited_method | dispatch/inheritance | 10 | 0 |
| binding.overridden_method | dispatch/inheritance | 14 | 0 |
| binding.explicit_parent | dispatch/inheritance | 11 | 0 |
| binding.super_parent | dispatch/inheritance | 11 | 10 |
| binding.decorated_replacement | dispatch/decorator | 7 | 3 |
| binding.unavailable_definition | binding/unknown | 4 | 0 |
| containers.nested_index | containers/selection | 3 | 0 |
| containers.negative_index | containers/selection | 4 | 0 |
| containers.reverse_stride | containers/selection | 4 | 0 |
| containers.slice_then_index | containers/selection | 4 | 0 |
| containers.caught_out_of_range | containers/selection | 3 | 0 |
| containers.returned_dictionary | containers/dictionaries | 3 | 1 |
| containers.overwritten_dynamic_key | containers/dictionaries | 4 | 1 |
| containers.missing_dictionary_default | containers/dictionaries | 3 | 0 |
| containers.unpacked_dictionary_overwrite | containers/dictionaries | 3 | 1 |
| containers.dictionary_alias_write | heap/aliases | 3 | 0 |
| containers.nested_alias_clear | heap/aliases | 2 | 0 |
| containers.detached_rebinding | heap/aliases | 3 | 0 |
| containers.cyclic_selected_element | heap/cycles | 2 | 0 |
| containers.append_result | protocol/mutation_returns | 4 | 1 |
| containers.conditional_append | heap/branches | 3 | 0 |
| containers.conditional_clear | heap/branches | 3 | 0 |
| containers.unconditional_branch_clear | heap/branches | 3 | 0 |
| containers.cross_call_append | heap/interprocedural | 9 | 0 |
| containers.cross_call_clear | heap/interprocedural | 7 | 1 |
| containers.dictionary_comprehension | comprehensions/dictionaries | 3 | 0 |
| containers.filtered_comprehension | comprehensions/filters | 3 | 0 |
| containers.empty_comprehension | comprehensions/empty | 2 | 0 |
| containers.comprehension_scope | comprehensions/scope | 3 | 0 |
| containers.joined_values | protocol/strings | 3 | 0 |
| containers.popped_element | protocol/mutation_returns | 5 | 1 |
| contract.depth_one | boundary | 7 | 0 |
| contract.depth_two | boundary | 4 | 0 |
| contract.missing_file | boundary | 5 | 0 |
| contract.function_budget | boundary | 2 | 0 |
| contract.call_budget | boundary | 1 | 0 |
| control.reassignment | scalar | 3 | 0 |
| control.control_only | control | 3 | 0 |
| control.conditional | control | 4 | 0 |
| control.short_circuit | control | 3 | 0 |
| control.loop_zero_or_one | loop | 4 | 0 |
| control.continue_skips_assignment | loop | 3 | 0 |
| control.break_or_else | loop | 4 | 0 |
| control.matching_exception | exception | 3 | 0 |
| control.finally_overrides_return | exception | 9 | 0 |
| control.finally_rebinds_local | exception | 3 | 0 |
| control.raised_exit | exception | 2 | 0 |
| control.closure_late_binding | closure | 6 | 0 |
| control.default_snapshot | closure | 6 | 0 |
| control.nonlocal_write | closure | 3 | 2 |
| control.lambda_call | closure | 2 | 1 |
| control.discarded_by_callee | interprocedural | 7 | 0 |
| control.discarded_call_result | interprocedural | 9 | 0 |
| control.chained_calls | interprocedural | 2 | 0 |
| control.mutual_left | recursion | 14 | 0 |
| control.recursion_without_result | recursion | 2 | 0 |
| control.return_projection | projection | 10 | 0 |
| control.awaited_call | async | 7 | 0 |
| control.unawaited_effect | async | 8 | 0 |
| control.consumed_generator | generator | 2 | 1 |
| control.unconsumed_generator_effect | generator | 8 | 0 |
| stdlib.splituser | real_code | 2 | 1 |
| stdlib.splitvalue | real_code | 2 | 1 |
| stdlib.splitnport | real_code | 3 | 1 |
| stdlib.get_sep | real_code | 2 | 0 |

## Failing or unresolved checks

Multiple checks can describe the same underlying defect. These counts are not independent defects.

### binding.variadic_argument

The head is constant; x and y bind distinct elements of rest. rest[1] returns y and excludes x.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |

### binding.variadic_keyword

Both named arguments are collected in values, retaining their keys. Selecting right returns y and excludes x.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |

### binding.literal_star

Expanding a two-element tuple binds x to first and y to second. The exact tuple shape is available without executing code.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | y | True | False | positive_missing |
| parameter_flow | positional#0:x->first | True | False | unresolved |
| parameter_flow | positional#0:x->second | False | False | unresolved |
| parameter_flow | positional#0:y->second | True | False | unresolved |
| parameter_flow | positional#0:y->first | False | False | unresolved |

### binding.star_and_keyword

Unknown-length positional expansion fills ignored only; the explicit result keyword independently binds y. No positional element is returned.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | y | True | False | positive_missing |
| binding | after_star#0:kw:result | result | None | unresolved |
| parameter_flow | after_star#0:y->result | True | False | unresolved |
| parameter_flow | after_star#0:items->result | False | False | unresolved |

### binding.local_alias

chosen receives the imported function object without rebinding or branching, preserving its signature and return dependency.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |
| target | chosen#0 | helpers:identity | None | unresolved |
| binding | chosen#0:0 | data | None | unresolved |
| parameter_flow | chosen#0:x->data | True | False | unresolved |

### binding.static_descriptor

The unshadowed builtin staticmethod descriptor does not prepend self or cls. The only explicit argument binds data.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |
| target | Descriptors.static_echo#0 | cases:Descriptors.static_echo | None | unresolved |
| binding | Descriptors.static_echo#0:0 | data | None | unresolved |
| parameter_flow | Descriptors.static_echo#0:x->data | True | False | unresolved |

### binding.class_descriptor

The unshadowed builtin classmethod descriptor supplies Descriptors as cls; x binds data, not cls.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |
| target | Descriptors.class_echo#0 | cases:Descriptors.class_echo | None | unresolved |
| binding | Descriptors.class_echo#0:receiver | cls | None | unresolved |
| binding | Descriptors.class_echo#0:0 | data | None | unresolved |
| parameter_flow | Descriptors.class_echo#0:x->data | True | False | unresolved |
| receiver_flow | Descriptors.class_echo#0:x->cls | False | False | unresolved |

### binding.super_parent

Zero-argument super in the nominal ParentDispatch method searches its sole Base. The resulting bound echo receives self implicitly and x as data.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| call_inventory | lexical_calls | True | False | mismatch |
| entry_return | x | True | False | positive_missing |
| call_presence | super().echo#0 | True | False | mismatch |
| target | super().echo#0 | cases:Base.echo | None | unresolved |
| binding | super().echo#0:receiver | self | None | unresolved |
| binding | super().echo#0:0 | data | None | unresolved |
| parameter_flow | super().echo#0:x->data | True | None | unresolved |
| receiver_flow | super().echo#0:self->self | True | None | unresolved |
| receiver_flow | super().echo#0:x->self | False | None | unresolved |
| call_return | super().echo#0 | True | None | unresolved |

### binding.decorated_replacement

replace executes during definition and replaces the original identity body with replace.replacement, which ignores data and returns None. The stale original body must not invent x-to-return flow.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| target | replaced_identity#0 | cases:replace.replacement | None | unresolved |
| binding | replaced_identity#0:0 | data | None | unresolved |
| parameter_flow | replaced_identity#0:x->data | True | False | unresolved |

### containers.returned_dictionary

The returned dictionary explicitly contains the supplied key and value.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | key | True | False | positive_missing |

### containers.overwritten_dynamic_key

The final chosen entry is y even if the earlier dynamic key equals chosen; lookup never returns key or x.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |

### containers.unpacked_dictionary_overwrite

The later key entry overwrites the unpacked x with y.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |

### containers.append_result

list.append always returns None, despite storing x as a side effect.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| call_return | values.append#0 | True | False | positive_missing |

### containers.cross_call_clear

clear_values removes x from the returned list; x nevertheless reaches the callee values parameter before the mutation.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |

### containers.popped_element

pop(0) returns only the first element x; y remains in the local list and is discarded.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |

### control.nonlocal_write

Calling replace assigns y to the enclosing value binding through nonlocal, replacing x before return.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | False | True | negative_flow_reported |
| entry_return | y | True | False | positive_missing |

### control.lambda_call

A direct local lambda call returns its argument unchanged.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |

### control.consumed_generator

Advancing generate_one with next obtains its first yielded x; generation and consumption form a real value path.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | x | True | False | positive_missing |

### stdlib.splituser

CPython str host contract: both result substrings derive from host; None on a delimiter-free path does not erase the other may-flow paths.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | host | True | False | positive_missing |

### stdlib.splitvalue

CPython attr=value partition returns substrings derived from attr; documented input is str.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | attr | True | False | positive_missing |

### stdlib.splitnport

Host survives rpartition and/or integer conversion; defport is returned on the missing or empty port branch. Both parameters have normal-execution value paths.

| Dimension | Subject | Expected | Actual | Outcome |
|---|---|---|---|---|
| entry_return | host | True | False | positive_missing |
