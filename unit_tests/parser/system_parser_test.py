from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.application.object.system_application_list_output import SystemApplicationListOutput
from keywords.cloud_platform.system.host.objects.system_host_label_assign_output import SystemHostLabelAssignOutput
from keywords.cloud_platform.system.host.objects.system_host_output import SystemHostOutput
from keywords.cloud_platform.system.system_table_parser import SystemTableParser
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

system_output = [
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
    '| id | hostname     | personality | administrative | operational | availability |\n',
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
    '| 1  | controller-0 | controller  | unlocked       | enabled     | available    |\n',
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
]

system_output_error = [
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
    '| id | hostname     | administrative | operational | availability |\n',
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
    '| 1  | controller-0 | controller  | unlocked       | enabled     | available    |\n',
    '+----+--------------+-------------+----------------+-------------+--------------+\n',
]

application_list_output = [
    '+--------------------------+----------+-------------------------------------------+------------------+----------+-----------+\n',  # noqa: E501
    '| application              | version  | manifest name                             | manifest file    | status   | progress  |\n',  # noqa: E501
    '+--------------------------+----------+-------------------------------------------+------------------+----------+-----------+\n',  # noqa: E501
    '| cert-manager             | 22.12-9  | cert-manager-fluxcd-manifests             | fluxcd-manifests | applied  | completed |\n',  # noqa: E501
    '| nginx-ingress-controller | 22.12-2  | nginx-ingress-controller-fluxcd-manifests | fluxcd-manifests | applied  | completed |\n',  # noqa: E501
    '| oidc-auth-apps           | 22.12-8  | oidc-auth-apps-fluxcd-manifests           | fluxcd-manifests | uploaded | completed |\n',  # noqa: E501
    '| platform-integ-apps      | 22.12-72 | platform-integ-apps-fluxcd-manifests      | fluxcd-manifests | applied  | completed |\n',  # noqa: E501
    '+--------------------------+----------+-------------------------------------------+------------------+----------+-----------+\n ',  # noqa: E501
]

system_host_show_output = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "| action                 | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "| apparmor               | disabled                                                             |\n",
    "| availability           | available                                                            |\n",
    "| bm_ip                  | 0000:111:bbbb:000::000                                               |\n",
    "| bm_type                | dynamic                                                              |\n",
    "| bm_username            | sysadmin                                                             |\n",
    "| boot_device            | /dev/disk/by-path/pci-0000:cc:00.0-sas-0x0000000000000000-lun-0      |\n",
    "| capabilities           | {'is_max_cpu_configurable': 'configurable', 'mgmt_ipsec': 'enabled', |\n",
    "|                        | 'Personality': 'Controller-Active'}                                  |\n",
    "| clock_synchronization  | ntp                                                                  |\n",
    "| config_applied         | 00000000-bbbb-4444-aaaa-666666666666                                 |\n",
    "| config_status          | None                                                                 |\n",
    "| config_target          | 00000000-bbbb-4444-aaaa-666666666666                                 |\n",
    "| console                | ttyS0,115200n8                                                       |\n",
    "| created_at             | 2024-08-23T09:21:51.460082+00:00                                     |\n",
    "| cstates_available      | C1,C1E,C6,POLL                                                       |\n",
    "| device_image_update    | None                                                                 |\n",
    "| hostname               | controller-0                                                         |\n",
    "| hw_settle              | 0                                                                    |\n",
    "| id                     | 1                                                                    |\n",
    "| install_output         | text                                                                 |\n",
    "| install_state          | None                                                                 |\n",
    "| install_state_info     | None                                                                 |\n",
    "| inv_state              | inventoried                                                          |\n",
    "| invprovision           | provisioned                                                          |\n",
    "| iscsi_initiator_name   | iqn.2000-01.io.sssssssss:3sssssssssss                                |\n",
    "| location               | {}                                                                   |\n",
    "| max_cpu_mhz_allowed    | None                                                                 |\n",
    "| max_cpu_mhz_configured | None                                                                 |\n",
    "| mgmt_mac               | dd:ff:ee:77:22:bb                                                    |\n",
    "| min_cpu_mhz_allowed    | None                                                                 |\n",
    "| nvme_host_id           | 33333333-7777-4444-9999-888888888888                                 |\n",
    "| nvme_host_nqn          | nqn.2014-08.org.nvmexpress:uuid:9bbbbbbb-2222-4444-aaaa-888888888888 |\n",
    "| operational            | enabled                                                              |\n",
    "| personality            | controller                                                           |\n",
    "| reboot_needed          | False                                                                |\n",
    "| reserved               | False                                                                |\n",
    "| rootfs_device          | /dev/disk/by-path/pci-0000:5c:00.0-sas-0x0000000000000000-lun-0      |\n",
    "| serialid               | None                                                                 |\n",
    "| software_load          | 24.09                                                                |\n",
    "| subfunction_avail      | available                                                            |\n",
    "| subfunction_oper       | enabled                                                              |\n",
    "| subfunctions           | controller,worker                                                    |\n",
    "| sw_version             | 24.09                                                                |\n",
    "| task                   |                                                                      |\n",
    "| tboot                  |                                                                      |\n",
    "| ttys_dcd               | False                                                                |\n",
    "| updated_at             | 2024-08-26T19:54:26.730136+00:00                                     |\n",
    "| uptime                 | 295248                                                               |\n",
    "| uuid                   | bbbbbbbb-9999-4444-8888-aaaaaaaaaaaa                                 |\n",
    "| vim_progress_status    | services-enabled                                                     |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_host_show_output_error_first_row = [
    "+------------------------ ----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "| action                 | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_host_show_output_error_second_row = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               |                                                                      |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "| action                 | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_host_show_output_error_third_row = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------ ----------------------------------------------------------------------+\n",
    "| action                 | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_host_show_output_error_some_row = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "| action                  none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_host_show_output_error_last_row = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "| action                 | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------ ----------------------------------------------------------------------+\n",
]

system_host_show_output_error_first_property_name = [
    "+------------------------+----------------------------------------------------------------------+\n",
    "| Property               | Value                                                                |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
    "|                        | none                                                                 |\n",
    "| administrative         | unlocked                                                             |\n",
    "+------------------------+----------------------------------------------------------------------+\n",
]

system_application_upload = [
    '+---------------+----------------------------------+\n',
    '| Property      | Value                            |\n',
    '+---------------+----------------------------------+\n',
    '| active        | True                             |\n',
    '| app_version   | 0.1.0                            |\n',
    '| created_at    | 2024-10-16T14:58:17.305376+00:00 |\n',
    '| manifest_file | fluxcd-manifests                 |\n',
    '| manifest_name | hello-kitty-fluxcd-manifests     |\n',
    '| name          | hello-kitty                      |\n',
    '| progress      | None                             |\n',
    '| status        | removing                         |\n',
    '| updated_at    | 2024-10-16T15:50:59.902779+00:00 |\n',
    '+---------------+----------------------------------+\n',
    "Please use 'system application-list' or 'system application-show hello-kitty' to view the current progress.\n",
]

system_host_if_ptp_remove_wrapped_output = [
    '+--------------------------------------+---------+-----------+---------------+\n',
    '| uuid                                 | name    | ptp_insta | parameters    |\n',
    '|                                      |         | nce_name  |               |\n',
    '+--------------------------------------+---------+-----------+---------------+\n',
    "| 0000c96e-6dab-48c2-875a-48af194c893c | n4_p2   | ptp4      | ['masterOnly= |\n",
    "|                                      |         |           | 1']           |\n",
    '|                                      |         |           |               |\n',
    '| 24003e49-f9c4-4794-970e-506fa5c215c0 | n1_if   | clock1    | []            |\n',
    '| 51e06821-b045-4a6e-854b-6bd829b5c9e2 | ptp1if1 | ptp1      | []            |\n',
    "| a689d398-329f-46b4-a99f-23b9a2417c27 | n5_p2   | ptp5      | ['masterOnly= |\n",
    "|                                      |         |           | 1']           |\n",
    '|                                      |         |           |               |\n',
    '+--------------------------------------+---------+-----------+---------------+\n',
]

def test_system_parser():
    """
    Tests the system parser
    Returns:

    """
    system_table_parser = SystemTableParser(system_output)
    output_list = system_table_parser.get_output_values_list()

    assert len(output_list) == 1
    output = output_list[0]
    assert output['id'] == '1'
    assert output['hostname'] == 'controller-0'
    assert output['personality'] == 'controller'
    assert output['administrative'] == 'unlocked'
    assert output['operational'] == 'enabled'
    assert output['availability'] == 'available'


def test_system_parser_application_list_output():
    """
    Tests that the system parser works with application list output
    Returns:

    """

    system_table_parser = SystemTableParser(application_list_output)
    output_list = system_table_parser.get_output_values_list()

    assert len(output_list) == 4

    # validate first application only
    output = output_list[0]
    assert output['application'] == 'cert-manager'
    assert output['version'] == '22.12-9'
    assert output['manifest name'] == 'cert-manager-fluxcd-manifests'
    assert output['manifest file'] == 'fluxcd-manifests'
    assert output['status'] == 'applied'
    assert output['progress'] == 'completed'


def test_system_parser_error():
    """
    Tests the system parser with an error in the input
    Returns:

    """
    try:
        configuration_locations_manager = ConfigurationFileLocationsManager()
        ConfigurationManager.load_configs(configuration_locations_manager)
        SystemTableParser(system_output_error).get_output_values_list()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == 'Number of headers and + separator do not match expected value'


def test_system_host_output():
    """
    Tests the system host output parser
    Returns:

    """
    system_host_output = SystemHostOutput(system_output)
    hosts = system_host_output.get_hosts()

    assert len(hosts) == 1

    host = hosts[0]
    assert host.get_id() == 1
    assert host.get_host_name() == 'controller-0'
    assert host.get_personality() == 'controller'
    assert host.get_administrative() == 'unlocked'
    assert host.get_operational() == 'enabled'
    assert host.get_availability() == 'available'


def test_system_host_output_error():
    """
    Tests the system host output parser with an error in the input
    Returns:

    """
    try:
        configuration_locations_manager = ConfigurationFileLocationsManager()
        ConfigurationManager.load_configs(configuration_locations_manager)
        SystemHostOutput(system_output_error).get_hosts()
        assert False, "There should be an exception when we parse the output."
    except KeywordException as e:
        assert e.args[0] == 'Number of headers and + separator do not match expected value'


def test_system_application_output():
    """
    Tests the system application output
    Returns:

    """
    system_application_output = SystemApplicationListOutput(application_list_output)
    applications = system_application_output.get_applications()

    assert len(applications) == 4

    application = applications[0]

    assert application.get_application() == 'cert-manager'
    assert application.get_version() == '22.12-9'
    assert application.get_manifest_name() == 'cert-manager-fluxcd-manifests'
    assert application.get_manifest_file() == 'fluxcd-manifests'
    assert application.get_status() == 'applied'
    assert application.get_progress() == 'completed'

def test_system_table_parser_with_wrapped_table_entry():
    """
    Test the system vertical parser with a table that has a column wrapped.
    Returns:

    """

    system_vertical_table_parser = SystemTableParser(system_host_if_ptp_remove_wrapped_output)
    list_of_values = system_vertical_table_parser.get_output_values_list()
    assert len(list_of_values) == 4

    first_entry = list_of_values[0]
    assert len(first_entry.keys()) == 4
    assert first_entry['uuid'] == '0000c96e-6dab-48c2-875a-48af194c893c'
    assert first_entry['name'] == 'n4_p2'
    assert first_entry['ptp_instance_name'] == 'ptp4'
    assert first_entry['parameters'] == "['masterOnly=1']"

    second_entry = list_of_values[1]
    assert len(second_entry.keys()) == 4
    assert second_entry['uuid'] == '24003e49-f9c4-4794-970e-506fa5c215c0'
    assert second_entry['name'] == 'n1_if'
    assert second_entry['ptp_instance_name'] == 'clock1'
    assert second_entry['parameters'] == "[]"

def test_system_host_label_assign_output():
    """
    Tests the system_host_label_assign output.
    Returns:

    """

    system_host_label_assign_output = [
        '+-------------+--------------------------------------+\n',
        '| Property    | Value                                |\n',
        '+-------------+--------------------------------------+\n',
        '| uuid        | b800c011-2065-4912-b1fd-4b4717cd5620 |\n',
        '| host_uuid   | 4feff42d-bc8d-4006-9922-a7fa10a6ee19 |\n',
        '| label_key   | kube-cpu-mgr-policy                  |\n',
        '| label_value | static                               |\n',
        '+-------------+--------------------------------------+\n',
        '+-------------+--------------------------------------+\n',
        '| Property    | Value                                |\n',
        '+-------------+--------------------------------------+\n',
        '| uuid        | 0260240f-bcca-41f5-9f32-b3acc030dfb0 |\n',
        '| host_uuid   | 4feff42d-bc8d-4006-9922-a7fa10a6ee19 |\n',
        '| label_key   | kube-topology-mgr-policy             |\n',
        '| label_value | best-effort                          |\n',
        '+-------------+--------------------------------------+\n',
    ]

    system_host_label_assign_output = SystemHostLabelAssignOutput(system_host_label_assign_output)
    host_labels = system_host_label_assign_output.get_all_host_labels()

    assert len(host_labels) == 2

    first_host_label = host_labels[0]
    second_host_label = host_labels[1]

    assert first_host_label.get_uuid() == 'b800c011-2065-4912-b1fd-4b4717cd5620'
    assert first_host_label.get_host_uuid() == '4feff42d-bc8d-4006-9922-a7fa10a6ee19'
    assert first_host_label.get_label_key() == 'kube-cpu-mgr-policy'
    assert first_host_label.get_label_value() == 'static'

    assert second_host_label.get_uuid() == '0260240f-bcca-41f5-9f32-b3acc030dfb0'
    assert second_host_label.get_host_uuid() == '4feff42d-bc8d-4006-9922-a7fa10a6ee19'
    assert second_host_label.get_label_key() == 'kube-topology-mgr-policy'
    assert second_host_label.get_label_value() == 'best-effort'


def test_system_vertical_table_parser():
    """
    Tests the system vertical parser
    Returns:
    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output)
    output_dict = system_vertical_table_parser.get_output_values_dict()

    assert len(output_dict.keys()) == 51
    assert len(output_dict.values()) == 51

    assert output_dict['action'] == 'none'
    assert output_dict['administrative'] == 'unlocked'
    assert output_dict['apparmor'] == 'disabled'
    assert output_dict['availability'] == 'available'
    assert output_dict['bm_ip'] == '0000:111:bbbb:000::000'
    assert output_dict['bm_type'] == 'dynamic'
    assert output_dict['bm_username'] == 'sysadmin'
    assert output_dict['boot_device'] == '/dev/disk/by-path/pci-0000:cc:00.0-sas-0x0000000000000000-lun-0'
    assert output_dict['capabilities'] == "{'is_max_cpu_configurable': 'configurable', 'mgmt_ipsec': 'enabled', 'Personality': 'Controller-Active'}"
    assert output_dict['clock_synchronization'] == 'ntp'
    assert output_dict['config_applied'] == '00000000-bbbb-4444-aaaa-666666666666'
    assert output_dict['config_status'] == 'None'
    assert output_dict['config_target'] == '00000000-bbbb-4444-aaaa-666666666666'
    assert output_dict['console'] == 'ttyS0,115200n8'
    assert output_dict['created_at'] == '2024-08-23T09:21:51.460082+00:00'
    assert output_dict['cstates_available'] == 'C1,C1E,C6,POLL'
    assert output_dict['device_image_update'] == 'None'
    assert output_dict['hostname'] == 'controller-0'
    assert output_dict['hw_settle'] == '0'
    assert output_dict['id'] == '1'
    assert output_dict['install_output'] == 'text'
    assert output_dict['install_state'] == 'None'
    assert output_dict['install_state_info'] == 'None'
    assert output_dict['inv_state'] == 'inventoried'
    assert output_dict['invprovision'] == 'provisioned'
    assert output_dict['iscsi_initiator_name'] == 'iqn.2000-01.io.sssssssss:3sssssssssss'
    assert output_dict['location'] == '{}'
    assert output_dict['max_cpu_mhz_allowed'] == 'None'
    assert output_dict['max_cpu_mhz_configured'] == 'None'
    assert output_dict['mgmt_mac'] == 'dd:ff:ee:77:22:bb'
    assert output_dict['min_cpu_mhz_allowed'] == 'None'
    assert output_dict['nvme_host_id'] == '33333333-7777-4444-9999-888888888888'
    assert output_dict['nvme_host_nqn'] == 'nqn.2014-08.org.nvmexpress:uuid:9bbbbbbb-2222-4444-aaaa-888888888888'
    assert output_dict['operational'] == 'enabled'
    assert output_dict['personality'] == 'controller'
    assert output_dict['reboot_needed'] == 'False'
    assert output_dict['reserved'] == 'False'
    assert output_dict['rootfs_device'] == '/dev/disk/by-path/pci-0000:5c:00.0-sas-0x0000000000000000-lun-0'
    assert output_dict['serialid'] == 'None'
    assert output_dict['software_load'] == '24.09'
    assert output_dict['subfunction_avail'] == 'available'
    assert output_dict['subfunction_oper'] == 'enabled'
    assert output_dict['subfunctions'] == 'controller,worker'
    assert output_dict['sw_version'] == '24.09'
    assert output_dict['task'] == ''
    assert output_dict['tboot'] == ''
    assert output_dict['ttys_dcd'] == 'False'
    assert output_dict['updated_at'] == '2024-08-26T19:54:26.730136+00:00'
    assert output_dict['uptime'] == '295248'
    assert output_dict['uuid'] == 'bbbbbbbb-9999-4444-8888-aaaaaaaaaaaa'
    assert output_dict['vim_progress_status'] == 'services-enabled'


def test_system_vertical_table_parser_error_in_first_row():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_first_row)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_system_vertical_table_parser_error_in_second_row():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_second_row)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have a header with 'Property' and 'Value' labels."


def test_system_vertical_table_parser_error_in_third_row():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_third_row)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_system_vertical_table_parser_error_in_some_row():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_some_row)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_system_vertical_table_parser_error_in_last_row():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_last_row)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "It is expected that a table have exactly two columns."


def test_system_vertical_table_parser_error_in_first_property_name():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_host_show_output_error_first_property_name)
    try:
        system_vertical_table_parser.get_output_values_dict()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == "The property name in the first data row cannot be empty."


def test_system_vertical_table_parser_with_valid_table_with_a_text_in_the_end():
    """
    Tests the system vertical parser
    Returns:

    """
    system_vertical_table_parser = SystemVerticalTableParser(system_application_upload)
    output_dict = system_vertical_table_parser.get_output_values_dict()
    assert len(output_dict.keys()) == 9
    assert len(output_dict.values()) == 9

    assert output_dict.get("active") == "True"
    assert output_dict.get("app_version") == "0.1.0"
    assert output_dict.get("created_at") == "2024-10-16T14:58:17.305376+00:00"
    assert output_dict.get("manifest_file") == "fluxcd-manifests"
    assert output_dict.get("manifest_name") == "hello-kitty-fluxcd-manifests"
    assert output_dict.get("name") == "hello-kitty"
    assert output_dict.get("progress") == "None"
    assert output_dict.get("status") == "removing"
    assert output_dict.get("updated_at") == "2024-10-16T15:50:59.902779+00:00"
