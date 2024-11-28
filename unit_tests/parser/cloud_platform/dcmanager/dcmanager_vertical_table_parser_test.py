from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser

dcmanager_subcloud_show_output = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+-----------------------------+----------------------------------+\n",
    "| id                          | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "| description                 | None                             |\n",
    "| location                    | None                             |\n",
    "| software_version            | 32.09                            |\n",
    "| management                  | managed                          |\n",
    "| availability                | online                           |\n",
    "| deploy_status               | complete                         |\n",
    "| management_subnet           | 1111:10:22:221::/64              |\n",
    "| management_start_ip         | 1111:10:22:221::2                |\n",
    "| management_end_ip           | 1111:10:22:221::ffff             |\n",
    "| management_gateway_ip       | 1111:10:22:221::1                |\n",
    "| systemcontroller_gateway_ip | 1111:10:22:220::1                |\n",
    "| group_id                    | 1                                |\n",
    "| peer_group_id               | None                             |\n",
    "| created_at                  | 2024-09-20 14:29:32.854298       |\n",
    "| updated_at                  | 2024-09-26 06:51:46.972787       |\n",
    "| backup_status               | None                             |\n",
    "| backup_datetime             | None                             |\n",
    "| prestage_status             | None                             |\n",
    "| prestage_versions           | None                             |\n",
    "| dc-cert_sync_status         | in-sync                          |\n",
    "| firmware_sync_status        | in-sync                          |\n",
    "| identity_sync_status        | in-sync                          |\n",
    "| kubernetes_sync_status      | in-sync                          |\n",
    "| kube-rootca_sync_status     | in-sync                          |\n",
    "| load_sync_status            | in-sync                          |\n",
    "| patching_sync_status        | in-sync                          |\n",
    "| platform_sync_status        | in-sync                          |\n",
    "| usm_sync_status             | in-sync                          |\n",
    "| region_name                 | b7ba03ff122a45f6b2e6a2ae1c6be86d |\n",
    "+-----------------------------+----------------------------------+\n",
]

dcmanager_subcloud_show_output_error_first_row = [
    "+----------------------------- ----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+-----------------------------+----------------------------------+\n",
    "| id                          | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+-----------------------------+----------------------------------+\n",
]

dcmanager_subcloud_show_output_error_second_row = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       |                                  |\n",
    "+-----------------------------+----------------------------------+\n",
    "| id                          | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+-----------------------------+----------------------------------+\n",
]

dcmanager_subcloud_show_output_error_third_row = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+----------------------------- ----------------------------------+\n",
    "| id                          | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+-----------------------------+----------------------------------+\n",
]

dcmanager_subcloud_show_output_error_some_row = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+-----------------------------+----------------------------------+\n",
    "| id                           7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+-----------------------------+----------------------------------+\n",
]

dcmanager_subcloud_show_output_error_last_row = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+-----------------------------+----------------------------------+\n",
    "| id                          | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+----------------------------- ----------------------------------+\n",
]

dcmanager_host_show_output_error_first_property_name = [
    "+-----------------------------+----------------------------------+\n",
    "| Field                       | Value                            |\n",
    "+-----------------------------+----------------------------------+\n",
    "|                             | 7                                |\n",
    "| name                        | subcloud1                        |\n",
    "+-----------------------------+----------------------------------+\n",
]


def test_dcmanager_vertical_table_parser():
    """
    Tests the dcmanager vertical parser
    Returns:
    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output)
    output_dict = dcmanager_vertical_table_parser.get_output_values_dict()

    assert len(output_dict.keys()) == 31
    assert len(output_dict.values()) == 31

    assert output_dict['id'] == '7'
    assert output_dict['name'] == 'subcloud1'
    assert output_dict['description'] == 'None'
    assert output_dict['location'] == 'None'
    assert output_dict['software_version'] == '32.09'
    assert output_dict['management'] == 'managed'
    assert output_dict['availability'] == 'online'
    assert output_dict['deploy_status'] == 'complete'
    assert output_dict['management_subnet'] == '1111:10:22:221::/64'
    assert output_dict['management_start_ip'] == '1111:10:22:221::2'
    assert output_dict['management_end_ip'] == '1111:10:22:221::ffff'
    assert output_dict['management_gateway_ip'] == '1111:10:22:221::1'
    assert output_dict['systemcontroller_gateway_ip'] == '1111:10:22:220::1'
    assert output_dict['group_id'] == '1'
    assert output_dict['peer_group_id'] == 'None'
    assert output_dict['created_at'] == '2024-09-20 14:29:32.854298'
    assert output_dict['updated_at'] == '2024-09-26 06:51:46.972787'
    assert output_dict['backup_status'] == 'None'
    assert output_dict['backup_datetime'] == 'None'
    assert output_dict['prestage_status'] == 'None'
    assert output_dict['prestage_versions'] == 'None'
    assert output_dict['dc-cert_sync_status'] == 'in-sync'
    assert output_dict['firmware_sync_status'] == 'in-sync'
    assert output_dict['identity_sync_status'] == 'in-sync'
    assert output_dict['kubernetes_sync_status'] == 'in-sync'
    assert output_dict['kube-rootca_sync_status'] == 'in-sync'
    assert output_dict['load_sync_status'] == 'in-sync'
    assert output_dict['patching_sync_status'] == 'in-sync'
    assert output_dict['platform_sync_status'] == 'in-sync'
    assert output_dict['usm_sync_status'] == 'in-sync'
    assert output_dict['region_name'] == 'b7ba03ff122a45f6b2e6a2ae1c6be86d'


def test_dcmanager_vertical_table_parser_error_in_first_row():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output_error_first_row)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_dcmanager_vertical_table_parser_error_in_second_row():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output_error_second_row)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have a header with 'Field' and 'Value' labels."


def test_dcmanager_vertical_table_parser_error_in_third_row():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output_error_third_row)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_dcmanager_vertical_table_parser_error_in_some_row():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output_error_some_row)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_dcmanager_vertical_table_parser_error_in_last_row():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output_error_last_row)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_system_vertical_table_parser_error_in_first_property_name():
    """
    Tests the system vertical parser
    Returns:

    """
    dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_host_show_output_error_first_property_name)
    try:
        dcmanager_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "The field name in the first data row cannot be empty."
