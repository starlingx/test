from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.storage.objects.system_storage_backend_object import SystemStorageBackendObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemStorageBackendOutput:
    """
    This class parses the output of 'system storage-backend-list' commands into a list of SystemStorageBackendObject
    """

    def __init__(self, system_storage_backend_list_output):
        """
        Constructor

        Args:
            system_storage_backend_list_output: String output of 'system storage-backend-list' command

            ['+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n',
             '| uuid                                 | name       | backend | state      | task | services | capabilities       |\n',
             '+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n',
             '| 256056b3-2811-49fe-87b3-37a2e9bcf6d9 | ceph-store | ceph    | configured | None | None     | replication: 1     |\n',
             '|                                      |            |         |            |      |          | min_replication: 1 |\n',
             '+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n']

        """

        self.system_storage_backends: [SystemStorageBackendObject] = []
        system_table_parser = SystemTableParser(system_storage_backend_list_output)
        output_values = system_table_parser.get_output_values_list()

        system_storage_backend_object = None
        for value in output_values:

            if 'name' not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'name'.")

            if not value['name']:
                # If there is no name, then this line contains extra info about the last line.
                # We should add the capabilities to the last entry.
                if 'capabilities' in value:
                    system_storage_backend_object.add_capabilities(value['capabilities'])
                continue

            system_storage_backend_object = SystemStorageBackendObject(value['name'])

            if 'uuid' in value:
                system_storage_backend_object.set_uuid(value['uuid'])

            if 'backend' in value:
                system_storage_backend_object.set_backend(value['backend'])

            if 'state' in value:
                system_storage_backend_object.set_state(value['state'])

            if 'task' in value:
                system_storage_backend_object.set_task(value['task'])

            if 'services' in value:
                system_storage_backend_object.set_services(value['services'])

            if 'capabilities' in value:
                system_storage_backend_object.add_capabilities(value['capabilities'])

            self.system_storage_backends.append(system_storage_backend_object)
