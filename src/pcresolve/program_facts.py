## @package pcresolve.program_facts
#  Internal syntax facts and pure binding operations shared by analysis policies.
#  This layer neither resolves owners nor computes value-flow summaries.

import ast
from dataclasses import dataclass


## Exact source location of a syntactic call within a source snapshot.
@dataclass(frozen=True)
class SourceSpan:
    file_path: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    ## Read a span without changing the caller's file-path representation.
    #  @param file_path Source file path, already chosen by the analysis session.
    #  @param node AST node with source positions.
    #  @return Span; unavailable end positions remain None.
    @classmethod
    def from_ast(cls, file_path, node):
        return cls(file_path, node.lineno, node.col_offset,
                   getattr(node, 'end_lineno', None), getattr(node, 'end_col_offset', None))

    ## Source coordinates independent of the file path.
    #  @return Four-element start/end coordinate tuple.
    @property
    def coordinates(self):
        return (self.lineno, self.col_offset, self.end_lineno, self.end_col_offset)

    ## Opaque identity of a call in one source snapshot, preserving flow-0.2 IDs.
    #  @return File path and complete source coordinates.
    @property
    def key(self):
        return '%s:%s:%s:%s:%s' % ((self.file_path,) + self.coordinates)


## Parameter kinds and declaration-time defaults without an analysis payload type.
#  Default values can be AST nodes or already collected source facts. They remain
#  in their defining scope; this class never evaluates or traces them.
@dataclass(frozen=True)
class FunctionSignature:
    positional_only: tuple = ()
    positional_or_keyword: tuple = ()
    keyword_only: tuple = ()
    vararg: str = ''
    kwarg: str = ''
    defaults: tuple = ()

    ## Positional parameter order after any receiver binding performed by the adapter.
    #  @return Ordered parameter names.
    @property
    def positional(self):
        return self.positional_only + self.positional_or_keyword

    ## Names accepting explicit keywords under Python signature rules.
    #  @return Set of positional-or-keyword and keyword-only names.
    @property
    def keyword_names(self):
        return set(self.positional_or_keyword + self.keyword_only)

    ## Construct a signature while preserving default-to-parameter identity.
    #  @param args Function or lambda ast.arguments.
    #  @param positional Optional positional nodes after receiver binding.
    #  @return Signature with declaration-time AST defaults.
    @classmethod
    def from_ast(cls, args, positional=None):
        declared = args.posonlyargs + args.args
        selected = declared if positional is None else positional
        defaults = list(zip(declared[len(declared) - len(args.defaults):], args.defaults))
        defaults.extend((param, value) for param, value in zip(args.kwonlyargs, args.kw_defaults)
                        if value is not None)
        return cls(
            tuple(param.arg for param in args.posonlyargs if param in selected),
            tuple(param.arg for param in args.args if param in selected),
            tuple(param.arg for param in args.kwonlyargs),
            args.vararg.arg if args.vararg else '', args.kwarg.arg if args.kwarg else '',
            tuple((param.arg, value) for param, value in defaults
                  if param in selected or param in args.kwonlyargs))


## Pure syntax binding for the value-flow adapter, including explicit uncertainty.
#  Records also expose complete statically decidable callability facts. Dynamic
#  expansion prevents a missing/duplicate claim when it could supply the slot.
#  @param node ast.Call; its expressions are retained as opaque payloads.
#  @param signature Callee signature after receiver binding.
#  @return (Binding records, ordered boundary reasons), without session mutation.
def bind_ast_call(node, signature):
    records, reasons = [], []
    positional = signature.positional
    defaults = {name for name, _ in signature.defaults}
    position = 0
    uncertain_position = False
    uncertain_keywords = False
    bound = {}

    def destination_kind(parameter):
        if parameter == signature.vararg:
            return 'var_positional'
        if parameter == signature.kwarg:
            return 'var_keyword'
        return 'parameter' if parameter else 'unresolved'

    def add_record(record):
        parameter = record['parameter']
        record['destination_kind'] = destination_kind(parameter)
        duplicate_key = (parameter, tuple(record.get('target_path', ())))
        if (parameter and parameter not in (signature.vararg, signature.kwarg)
                and parameter in bound):
            record['status'] = 'duplicate'
            record['conflicts_with'] = bound[parameter]['argument']
            if 'duplicate_argument_binding' not in reasons:
                reasons.append('duplicate_argument_binding')
        elif (parameter == signature.kwarg and duplicate_key in bound):
            record['status'] = 'duplicate'
            record['conflicts_with'] = bound[duplicate_key]['argument']
            if 'duplicate_argument_binding' not in reasons:
                reasons.append('duplicate_argument_binding')
        records.append(record)
        if parameter and record['status'] == 'exact':
            bound[duplicate_key if parameter == signature.kwarg else parameter] = record

    def positional_record(argument, slot, expanded=False):
        nonlocal position
        parameter = None
        target_path = []
        if not uncertain_position and position < len(positional):
            parameter = positional[position]
        elif signature.vararg and (not uncertain_position or position >= len(positional)):
            parameter = signature.vararg
            target_path = [position - len(positional)] if not uncertain_position else ['*']
        add_record({'argument': slot, 'node': argument, 'parameter': parameter,
                    'target_path': target_path, 'status': 'exact' if parameter else 'unresolved',
                    'binding_kind': 'starred' if expanded else 'explicit'})
        position += 1

    for source_position, argument in enumerate(node.args):
        if isinstance(argument, ast.Starred):
            if isinstance(argument.value, (ast.Tuple, ast.List)):
                for star_index, element in enumerate(argument.value.elts):
                    positional_record(element, {'position': position,
                        'expanded_from': source_position, 'star_index': star_index}, True)
            else:
                parameter = signature.vararg if signature.vararg and position >= len(positional) else None
                add_record({'argument': {'position': source_position, 'starred': True},
                    'node': argument.value, 'parameter': parameter,
                    'target_path': ['*'] if parameter else [],
                    'status': 'exact' if parameter else 'unresolved',
                    'binding_kind': 'dynamic_starred'})
                uncertain_position = True
                reasons.append('dynamic_argument_expansion')
            continue
        positional_record(argument, {'position': position})

    keyword_arguments = []
    for keyword in node.keywords:
        if (keyword.arg is None and isinstance(keyword.value, ast.Dict)
                and all(isinstance(key, ast.Constant) and isinstance(key.value, str)
                        for key in keyword.value.keys)
                and len({key.value for key in keyword.value.keys}) == len(keyword.value.keys)):
            keyword_arguments.extend((key.value, value, True)
                                     for key, value in zip(keyword.value.keys, keyword.value.values))
        else:
            keyword_arguments.append((keyword.arg, keyword.value, False))
    allowed = signature.keyword_names
    for key, argument, expanded in keyword_arguments:
        if key is None:
            parameter = signature.kwarg if signature.kwarg and not allowed else None
            target_path = ['*'] if parameter else []
            reasons.append('dynamic_argument_expansion')
            uncertain_keywords = True
        else:
            parameter = key if key in allowed else (signature.kwarg or None)
            target_path = [key] if signature.kwarg and parameter == signature.kwarg else []
        add_record({'argument': {'keyword': key}, 'node': argument,
            'parameter': parameter, 'target_path': target_path,
            'status': 'exact' if parameter else 'unresolved',
            'binding_kind': ('dynamic_keyword' if key is None else
                             'expanded_keyword' if expanded else 'explicit')})

    required = [name for name in positional + signature.keyword_only if name not in defaults]
    for parameter in required:
        could_be_positional = parameter in positional and uncertain_position
        could_be_keyword = parameter in signature.keyword_names and uncertain_keywords
        if parameter not in bound and not could_be_positional and not could_be_keyword:
            records.append({'argument': None, 'node': None, 'parameter': parameter,
                            'target_path': [], 'status': 'missing',
                            'binding_kind': 'required',
                            'destination_kind': 'parameter'})
            if 'missing_required_parameter' not in reasons:
                reasons.append('missing_required_parameter')
    if any(record['status'] == 'unresolved'
           and record['binding_kind'] in ('explicit', 'starred', 'expanded_keyword')
           for record in records):
        reasons.append('invalid_argument_binding')
    if any(record['status'] in ('duplicate', 'missing') for record in records):
        if 'invalid_argument_binding' not in reasons:
            reasons.append('invalid_argument_binding')
    return records, reasons


## Existing ownership projection choices, separate from signature syntax facts.
@dataclass(frozen=True)
class SourceBindingPolicy:
    collect_packs: bool
    ambiguous_keywords_use_default: bool


CONTEXT_BINDING = SourceBindingPolicy(False, False)
OWNERSHIP_BINDING = SourceBindingPolicy(True, True)


## Select a positional item only when one known-start starred pack can supply it.
#  @param stars Mapping of expansion start offsets to opaque source payloads.
#  @param index Target positional offset.
#  @param project Pure callback producing a selected item source.
#  @return Projected source or None when ambiguous.
def starred_item_source(stars, index, project):
    if any(start is None for start in stars):
        return None
    matches = [(start, source) for start, source in sorted(stars.items()) if start <= index]
    if len(matches) != 1:
        return None
    start, source = matches[0]
    return project(source, index - start)


## Project opaque call-edge sources onto a parameter under the consumer's policy.
#  Ownership keeps its existing explicit-keyword priority, even for legacy
#  summaries without parameter-kind metadata. No library/value decisions occur here.
#  @param signature Callee signature with collected default source payloads.
#  @param parameter Target parameter name.
#  @param positional Explicit sources keyed by positional offset.
#  @param keywords Explicit sources keyed by keyword name.
#  @param stars Starred positional source payloads and known/unknown start offsets.
#  @param star_keywords Starred keyword source payloads in source order.
#  @param project Pure callback producing a container-item projection.
#  @param policy Consumer's pack/default ambiguity policy.
#  @return Source list, or None when unavailable or ambiguous.
def bind_parameter_sources(signature, parameter, positional, keywords, stars,
                           star_keywords, project, policy):
    if parameter in keywords:
        return [keywords[parameter]]
    names = signature.positional
    if parameter == signature.vararg or parameter == signature.kwarg:
        if not policy.collect_packs:
            return None
        if parameter == signature.vararg:
            values = [positional[index] for index in sorted(positional) if index >= len(names)]
            values.extend(stars.values())
        else:
            explicit = set(names + signature.keyword_only)
            values = [value for name, value in keywords.items() if name not in explicit]
            values.extend(star_keywords)
        return values or None
    if parameter in names:
        index = names.index(parameter)
        if index in positional:
            return [positional[index]]
        selected = starred_item_source(stars, index, project)
        if selected is not None:
            return [selected]
    if len(star_keywords) == 1:
        return [project(star_keywords[0], parameter)]
    if star_keywords and not policy.ambiguous_keywords_use_default:
        return None
    defaults = dict(signature.defaults)
    return [defaults[parameter]] if parameter in defaults else None
