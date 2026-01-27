from keywords.k8s.crd.object.kubectl_hosts_table_parser import KubectlHostsTableParser


def test_get_hosts_table_parser():
    """
    Tests the k8s_get_hosts table parser
    Returns:

    """

    get_hosts_output = (
        'NAME           ADMINISTRATIVE   OPERATIONAL   AVAILABILITY   PROFILE                INSYNC   SCOPE       RECONCILED\n',
        'controller-0   unlocked         enabled       available      controller-0-profile   true     bootstrap   true\n',
        'controller-1   unlocked         enabled       available      controller-0-profile   true     bootstrap   true \n',
    )

    table_parser = KubectlHostsTableParser(get_hosts_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 2, "There are two entries in this get hosts table."
    first_line = output_values[0]

    assert first_line['NAME'] == 'controller-0'
    assert first_line['ADMINISTRATIVE'] == 'unlocked'
    assert first_line['OPERATIONAL'] == 'enabled'
    assert first_line['AVAILABILITY'] == 'available'
    assert first_line['PROFILE'] == 'controller-0-profile'
    assert first_line['INSYNC'] == 'true'
    assert first_line['SCOPE'] == 'bootstrap'
    assert first_line['RECONCILED'] == 'true'


