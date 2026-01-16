from keywords.k8s.k8s_table_parser_base import K8sTableParserBase


def test_header_with_parentheses():
    """
    Tests that headers with special characters like PORT(S) are parsed correctly.
    """
    service_output = (
        "NAME         TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE\n",
        "kubernetes   ClusterIP   10.96.0.1    <none>        443/TCP   5d\n",
        "my-service   NodePort    10.96.0.2    <none>        80/TCP    2d\n",
    )

    parser = K8sTableParserBase(service_output)
    parser.possible_headers = ["NAME", "TYPE", "CLUSTER-IP", "EXTERNAL-IP", "PORT(S)", "AGE"]
    output_values = parser.get_output_values_list()

    assert len(output_values) == 2
    assert output_values[0]["PORT(S)"] == "443/TCP"
    assert output_values[1]["PORT(S)"] == "80/TCP"
