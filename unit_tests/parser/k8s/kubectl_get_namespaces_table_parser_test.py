from keywords.k8s.namespace.object.kubectl_get_namespaces_table_parser import KubectlGetNamespacesTableParser


def test_get_namespaces_table_parser():
    """
    Tests the k8s_get_namepaces table parser
    Returns:

    """

    get_namespaces_output = [
        'NAME                          STATUS   AGE\n',
        'cert-manager                  Active   19d\n',
        'default                       Active   19d\n',
        'deployment                    Active   19d\n',
        'kube-node-lease               Active   19d\n',
        'kube-public                   Active   19d\n',
        'kube-system                   Active   19d\n',
    ]

    table_parser = KubectlGetNamespacesTableParser(get_namespaces_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 6, "There are six entries in this get pods table."
    first_line = output_values[0]

    assert first_line['NAME'] == 'cert-manager'
    assert first_line['STATUS'] == 'Active'
    assert first_line['AGE'] == '19d'
