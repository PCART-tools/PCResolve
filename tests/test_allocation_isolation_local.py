import copy

from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


def test_public_allocation_results_are_independent_across_expansion(tmp_path):
    source = (Path(__file__).parent / 'fixtures' / 'value_flow_fresh_instance_methods'
              / 'sample.py').read_text(encoding='utf-8')
    (tmp_path / 'sample.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    root = analyzer.analyze(FunctionRef('sample', 'Box'))
    edge = root.find_calls(callee_name='self.update')[0]
    parent_allocation = root.inputs['entry_binding']['fresh_receiver_origin']['allocation']
    edge_allocation = edge.instance_method_bindings[0]['origin']['allocation']
    expected = copy.deepcopy(parent_allocation)
    assert edge_allocation == expected
    assert edge_allocation is not parent_allocation

    child = analyzer.expand(root, edge.id, isolate=True, preserve_lineage=True)
    sibling = analyzer.expand(root, edge.id, isolate=True, preserve_lineage=True)
    child_allocation = child.inputs['entry_binding']['fresh_receiver_origin']['allocation']
    sibling_allocation = sibling.inputs['entry_binding']['fresh_receiver_origin']['allocation']
    assert child_allocation == sibling_allocation == expected
    child_allocation['assumptions'].append('local mutation')
    child_allocation['receiver_class']['qualname'] = 'changed'
    assert parent_allocation == edge_allocation == sibling_allocation == expected
    assert child.to_dict()['inputs']['entry_binding']['fresh_receiver_origin']['allocation'] == child_allocation
