## @package value_flow_mapping_parameters.helpers


def clean(mapping):
    alias = mapping
    del alias['out']
    return alias
