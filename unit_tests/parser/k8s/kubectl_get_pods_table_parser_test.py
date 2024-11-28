from keywords.k8s.pods.object.kubectl_get_pods_table_parser import KubectlGetPodsTableParser


def test_get_pods_table_parser():
    """
    Tests the k8s_get_pods table parser
    Returns:

    """

    get_pods_output = (
        'NAME                                           READY   STATUS    RESTARTS       AGE   IP                              NODE           NOMINATED NODE   READINESS GATES\n',
        'my-pod-name-748c5cfd47-8bpk5                   1/1     Running   36 (59m ago)   18d   abcd:123::1331:765f:6111:bd78   controller-0   <none>           <none>         \n',
        'another-pod-name-86c99d74dd-rvswf              2/2     Running   94 (59m ago)   18d   bcde:123::1331:765f:6111:ac67   controller-0   <none>           <none>         \n',
    )

    table_parser = KubectlGetPodsTableParser(get_pods_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 2, "There are two entries in this get pods table."
    first_line = output_values[0]

    assert first_line['NAME'] == 'my-pod-name-748c5cfd47-8bpk5'
    assert first_line['READY'] == '1/1'
    assert first_line['STATUS'] == 'Running'
    assert first_line['RESTARTS'] == '36 (59m ago)'
    assert first_line['AGE'] == '18d'
    assert first_line['IP'] == 'abcd:123::1331:765f:6111:bd78'
    assert first_line['NODE'] == 'controller-0'
    assert first_line['NOMINATED NODE'] == '<none>'
    assert first_line['READINESS GATES'] == '<none>'


def test_get_pods_table_parser_substring_header():
    """
    Tests the k8s_get_pods table parser
    Returns:

    """

    get_pods_output = (
        'NAMESPACE                     NAME                                              READY   STATUS             RESTARTS         AGE\n',
        'cert-manager                  cert-manager-77f946d54b-9597p                     1/1     Running            12 (2d8h ago)    2d14h\n',
        'cert-manager                  cert-manager-cainjector-5df9bd5969-4j2h6          1/1     Running            18 (2d8h ago)    2d14h\n',
        'cert-manager                  cert-manager-webhook-5cbd9c8648-wfhsf             1/1     Running            9 (2d8h ago)     2d14h\n',
        'default                       load-generator                                    0/1     ImagePullBackOff   0                2d21h\n',
    )

    table_parser = KubectlGetPodsTableParser(get_pods_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 4, "There are four entries in this get pods table."
    first_line = output_values[2]

    assert first_line['NAMESPACE'] == 'cert-manager'
    assert first_line['NAME'] == 'cert-manager-webhook-5cbd9c8648-wfhsf'
    assert first_line['READY'] == '1/1'
    assert first_line['STATUS'] == 'Running'
    assert first_line['RESTARTS'] == '9 (2d8h ago)'
    assert first_line['AGE'] == '2d14h'


def test_get_pods_table_parser_missing_header():
    """
    Tests that the k8s_get_pods table parser will pick up if a header isn't part of KubectlGetPodsTableParser's possible_headers

    """

    get_pods_output = (
        'NAME                               INVALID_HEADER   READY   STATUS    RESTARTS       AGE   IP                              NODE           NOMINATED NODE   READINESS GATES\n',
        'my-pod-name-748c5cfd47-8bpk5       some_value       1/1     Running   36 (59m ago)   18d   abcd:123::1331:765f:6111:bd78   controller-0   <none>           <none>         \n',
        'another-pod-name-86c99d74dd-rvswf  some_value       2/2     Running   94 (59m ago)   18d   bcde:123::1331:765f:6111:ac67   controller-0   <none>           <none>         \n',
    )

    table_parser = KubectlGetPodsTableParser(get_pods_output)
    try:
        table_parser.get_output_values_list()
        assert False, "There should be an exception hit by the table parser."
    except Exception as e:
        assert "Header Missing: INVALID_HEADER must be added to the list of possible_headers." in str(e)
