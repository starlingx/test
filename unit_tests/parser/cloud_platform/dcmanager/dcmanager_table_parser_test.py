from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser

dcmanager_subcloud_list_output = [
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
    "| id | name      | management | availability | deploy status | sync    | backup status | prestage status |\n",
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
    "|  5 | subcloud3 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "|  6 | subcloud2 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "|  7 | subcloud1 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
]

dcmanager_subcloud_list_output_error = [
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
    "| id | name      | management | availability | deploy status | sync    | backup status |\n",
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
    "|  5 | subcloud3 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "|  6 | subcloud2 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "|  7 | subcloud1 | managed    | online       | complete      | in-sync | None          | None            |\n",
    "+----+-----------+------------+--------------+---------------+---------+---------------+-----------------+\n",
]


def test_dcmanager_table_parser():
    """
    Tests the dcmanager table parser
    Returns:

    """
    dcmanager_table_parser = DcManagerTableParser(dcmanager_subcloud_list_output)
    output_list = dcmanager_table_parser.get_output_values_list()

    assert len(output_list) == 3
    output = output_list[0]

    assert output['id'] == '5'
    assert output['name'] == 'subcloud3'
    assert output['management'] == 'managed'
    assert output['availability'] == 'online'
    assert output['deploy status'] == 'complete'
    assert output['sync'] == 'in-sync'
    assert output['backup status'] == 'None'
    assert output['prestage status'] == 'None'


def test_system_parser_error():
    """
    Tests the dcmanager table parser with an error in the input
    Returns:

    """
    try:
        configuration_locations_manager = ConfigurationFileLocationsManager()
        ConfigurationManager.load_configs(configuration_locations_manager)
        dcmanager_table_parser = DcManagerTableParser(dcmanager_subcloud_list_output_error)
        dcmanager_table_parser.get_output_values_list()
        assert False, "There should be an exception when parsing the output."
    except KeywordException as e:
        assert e.args[0] == 'Number of headers and values do not match'
