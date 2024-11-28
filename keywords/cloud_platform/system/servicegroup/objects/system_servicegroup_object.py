from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.servicegroup.objects.system_servicegroup_output import SystemServiceGroupObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemServiceGroupOutput:
    """
    This class parses the output of 'system servicegroup-list' commands into a list of SystemServiceGroupObject
    """

    def __init__(self, system_servicegroup_list_output):
        """
        Constructor

        Args:
            system_servicegroup_list_output: String output of 'system servicegroup-list' command
        """

        self.system_servicegroup_list: [SystemServiceGroupObject] = []
        system_table_parser = SystemTableParser(system_servicegroup_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:

            if 'service_group_name' not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing a 'service_group_name'.")

            system_servicegroup_object = SystemServiceGroupObject(value['service_group_name'])

            if 'uuid' in value:
                system_servicegroup_object.set_uuid(value['uuid'])

            if 'hostname' in value:
                system_servicegroup_object.set_hostname(value['hostname'])

            if 'state' in value:
                system_servicegroup_object.set_state(value['state'])

            self.system_servicegroup_list.append(system_servicegroup_object)
