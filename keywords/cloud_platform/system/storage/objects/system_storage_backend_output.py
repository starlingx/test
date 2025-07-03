from framework.exceptions.keyword_exception import KeywordException
from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.system.host.objects.storage_capabilities_object import StorageCapabilities
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

        if isinstance(system_storage_backend_list_output, RestResponse):  # came from REST and is already in dict format
            json_object = system_storage_backend_list_output.get_json_content()
            if "storage_backends" in json_object:
                storage_backends = json_object["storage_backends"]
            else:
                storage_backends = [json_object]
        else:
            system_table_parser = SystemTableParser(system_storage_backend_list_output)
            storage_backends = system_table_parser.get_output_values_list()

        system_storage_backend_object = None
        for value in storage_backends:

            if "name" not in value:
                raise KeywordException(f"The output line {value} was not valid because it is missing an 'name'.")

            if not value["name"]:
                # If there is no name, then this line contains extra info about the last line.
                # We should add the capabilities to the last entry.
                if "capabilities" in value:
                    system_storage_backend_object.add_capabilities(value["capabilities"])
                continue

            system_storage_backend_object = SystemStorageBackendObject(value["name"])

            if "uuid" in value:
                system_storage_backend_object.set_uuid(value["uuid"])

            if "backend" in value:
                system_storage_backend_object.set_backend(value["backend"])

            if "state" in value:
                system_storage_backend_object.set_state(value["state"])

            if "task" in value:
                system_storage_backend_object.set_task(value["task"])

            if "services" in value:
                system_storage_backend_object.set_services(value["services"])

            if "capabilities" in value:
                storage_capabilities = value["capabilities"]
                # if it's from REST, then we are already in dict format
                if isinstance(storage_capabilities, dict):
                    storage_capabilities_object = StorageCapabilities()
                    if "replication" in storage_capabilities:
                        storage_capabilities_object.set_replication(storage_capabilities["replication"])
                    if "min_replication" in storage_capabilities:
                        storage_capabilities_object.set_min_replication(storage_capabilities["min_replication"])
                    if "deployment_model" in storage_capabilities:
                        storage_capabilities_object.set_deployment_model(storage_capabilities["deployment_model"])
                else:
                    system_storage_backend_object.add_capabilities(storage_capabilities)

            self.system_storage_backends.append(system_storage_backend_object)

    def get_system_storage_backends(self) -> list[SystemStorageBackendObject]:
        """
        Returns a list of objects representing each row of the table displayed as the result of executing the 'system storage-backend-list' command.

        Args: None.

        Returns:
            list[SystemStorageBackendObject]: list of objects representing each row of the table displayed as the result of executing the
        'system storage-backend-list' command.
        """
        return self.system_storage_backends

    def get_system_storage_backend(self, backend: str) -> SystemStorageBackendObject:
        """
        Gets the given backend

        Args:
            backend (str): the name of the backend ceph or ceph-rook

        Raises:
            KeywordException: the given name is not exist

        Returns:
            SystemStorageBackendObject: the given backend object
        """
        backends = list(filter(lambda item: item.get_backend() == backend, self.system_storage_backends))
        if len(backends) == 0:
            raise KeywordException(f"No application with name {backend} was found.")
        return backends[0]

    def is_backend_configured(self, backend: str) -> bool:
        """
        Verifies if Given backend is configured.

        Args:
             backend (str): backend ceph or ceph-rook.

        Returns:
             bool: True if backend configured; False otherwise.
        """
        backends = list(filter(lambda item: item.get_backend() == backend, self.system_storage_backends))
        if len(backends) == 0:
            return False
        return True
