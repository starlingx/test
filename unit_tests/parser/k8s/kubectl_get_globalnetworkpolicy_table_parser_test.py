from keywords.k8s.globalnetworkpolicy.object.kubectl_get_globalnetworkpolicy_table_parser import KubectlGetGlobalNetworkPolicyTableParser


def test_get_globalnetworkpolicy_table_parser():
    """Tests the k8s_get_globalnetworkpolicy table parser."""
    get_globalnetworkpolicy_output = [
        "NAME                             AGE\n",
        "controller-cluster-host-if-gnp   15d\n",
        "controller-mgmt-if-gnp           15d\n",
        "gnp-oam-overrides                1m\n",
    ]

    table_parser = KubectlGetGlobalNetworkPolicyTableParser(get_globalnetworkpolicy_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 3, "There are three entries in this get globalnetworkpolicy table."
    first_line = output_values[0]

    assert first_line["NAME"] == "controller-cluster-host-if-gnp"
    assert first_line["AGE"] == "15d"

    second_line = output_values[1]
    assert second_line["NAME"] == "controller-mgmt-if-gnp"
    assert second_line["AGE"] == "15d"

    third_line = output_values[2]
    assert third_line["NAME"] == "gnp-oam-overrides"
    assert third_line["AGE"] == "1m"


def test_get_globalnetworkpolicy_table_parser_empty():
    """Tests the k8s_get_globalnetworkpolicy table parser with empty output."""
    get_globalnetworkpolicy_output = [
        "NAME   AGE\n",
    ]

    table_parser = KubectlGetGlobalNetworkPolicyTableParser(get_globalnetworkpolicy_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 0, "There should be no entries in empty table."
