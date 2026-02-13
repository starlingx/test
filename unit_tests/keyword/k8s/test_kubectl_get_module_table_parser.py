from keywords.k8s.module.object.kubectl_get_module_table_parser import KubectlGetModuleTableParser


def test_parse_single_module():
    """Test parsing single module output."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    parser = KubectlGetModuleTableParser(output)
    values = parser.get_output_values_list()
    assert len(values) == 1
    assert values[0]["NAME"] == "kmm-hello-world"
    assert values[0]["AGE"] == "5m"


def test_parse_multiple_modules():
    """Test parsing multiple modules output."""
    output = (
        "NAME       AGE\n",
        "module-1   5m\n",
        "module-2   10m\n",
    )
    parser = KubectlGetModuleTableParser(output)
    values = parser.get_output_values_list()
    assert len(values) == 2
    assert values[0]["NAME"] == "module-1"
    assert values[1]["NAME"] == "module-2"
