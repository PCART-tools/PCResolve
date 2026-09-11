# Value-flow evaluation matrix

Analyzer revision: `67c4ad69cc6894a4eb7e257f678892d01229876f`; Python: `3.13.9`.

83 entry cases. Semantic gold is manually specified; unknown absence is not a no-flow proof.

| Dimension | Checks | Outcomes |
|---|---:|---|
| binding | 54 | matched=54 |
| boundary | 6 | matched=6 |
| call_inventory | 82 | matched=82 |
| call_presence | 41 | matched=41 |
| call_return | 41 | negative_no_path=7, positive_found=34 |
| entry_return | 137 | negative_no_path=62, positive_found=75 |
| parameter_flow | 65 | negative_no_path=20, positive_found=45 |
| receiver_flow | 7 | negative_no_path=2, positive_found=5 |
| target | 39 | matched=39 |

## Cases

| Case | Category | Checks | Gaps |
|---|---|---:|---:|
| binding.positional_only | binding/positional | 12 | 0 |
| binding.keyword_only | binding/keyword | 11 | 0 |
| binding.default_argument | binding/default | 11 | 0 |
| binding.variadic_argument | binding/varargs | 12 | 0 |
| binding.variadic_keyword | binding/kwargs | 10 | 0 |
| binding.literal_star | binding/expansion | 10 | 0 |
| binding.star_and_keyword | binding/expansion | 9 | 0 |
| binding.literal_keywords | binding/expansion | 11 | 0 |
| binding.module_alias | binding/imports | 7 | 0 |
| binding.function_alias | binding/imports | 7 | 0 |
| binding.reexport_chain | binding/imports | 7 | 0 |
| binding.local_alias | binding/alias | 7 | 0 |
| binding.rebound_import | binding/unknown | 4 | 0 |
| binding.repeated_calls | binding/context | 15 | 0 |
| binding.instance_receiver | dispatch/receiver | 11 | 0 |
| binding.receiver_alias | dispatch/receiver | 11 | 0 |
| binding.static_descriptor | dispatch/descriptor | 7 | 0 |
| binding.class_descriptor | dispatch/descriptor | 9 | 0 |
| binding.inherited_method | dispatch/inheritance | 10 | 0 |
| binding.overridden_method | dispatch/inheritance | 14 | 0 |
| binding.explicit_parent | dispatch/inheritance | 11 | 0 |
| binding.super_parent | dispatch/inheritance | 11 | 0 |
| binding.decorated_replacement | dispatch/decorator | 7 | 0 |
| binding.unavailable_definition | binding/unknown | 4 | 0 |
| containers.nested_index | containers/selection | 3 | 0 |
| containers.negative_index | containers/selection | 4 | 0 |
| containers.reverse_stride | containers/selection | 4 | 0 |
| containers.slice_then_index | containers/selection | 4 | 0 |
| containers.caught_out_of_range | containers/selection | 3 | 0 |
| containers.returned_dictionary | containers/dictionaries | 3 | 0 |
| containers.overwritten_dynamic_key | containers/dictionaries | 4 | 0 |
| containers.missing_dictionary_default | containers/dictionaries | 3 | 0 |
| containers.unpacked_dictionary_overwrite | containers/dictionaries | 3 | 0 |
| containers.dictionary_alias_write | heap/aliases | 3 | 0 |
| containers.nested_alias_clear | heap/aliases | 2 | 0 |
| containers.detached_rebinding | heap/aliases | 3 | 0 |
| containers.cyclic_selected_element | heap/cycles | 2 | 0 |
| containers.append_result | protocol/mutation_returns | 4 | 0 |
| containers.conditional_append | heap/branches | 3 | 0 |
| containers.conditional_clear | heap/branches | 3 | 0 |
| containers.unconditional_branch_clear | heap/branches | 3 | 0 |
| containers.cross_call_append | heap/interprocedural | 9 | 0 |
| containers.cross_call_clear | heap/interprocedural | 7 | 0 |
| containers.dictionary_comprehension | comprehensions/dictionaries | 3 | 0 |
| containers.filtered_comprehension | comprehensions/filters | 3 | 0 |
| containers.empty_comprehension | comprehensions/empty | 2 | 0 |
| containers.comprehension_scope | comprehensions/scope | 3 | 0 |
| containers.joined_values | protocol/strings | 3 | 0 |
| containers.popped_element | protocol/mutation_returns | 5 | 0 |
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
| control.nonlocal_write | closure | 3 | 0 |
| control.lambda_call | closure | 2 | 0 |
| control.discarded_by_callee | interprocedural | 7 | 0 |
| control.discarded_call_result | interprocedural | 9 | 0 |
| control.chained_calls | interprocedural | 2 | 0 |
| control.mutual_left | recursion | 14 | 0 |
| control.recursion_without_result | recursion | 2 | 0 |
| control.return_projection | projection | 10 | 0 |
| control.awaited_call | async | 7 | 0 |
| control.unawaited_effect | async | 8 | 0 |
| control.consumed_generator | generator | 2 | 0 |
| control.unconsumed_generator_effect | generator | 8 | 0 |
| stdlib.splituser | real_code | 2 | 0 |
| stdlib.splitvalue | real_code | 2 | 0 |
| stdlib.splitnport | real_code | 3 | 0 |
| stdlib.get_sep | real_code | 2 | 0 |

## Failing or unresolved checks

Multiple checks can describe the same underlying defect. These counts are not independent defects.
