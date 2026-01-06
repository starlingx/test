from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.application.object.system_application_list_object import SystemApplicationListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemApplicationListOutput:
    """This class parses the output of the command 'system application-list'.

    The parsing result is a 'SystemApplicationListObject' instance.

    Example:
        'system application-list'
        +--------------------------+----------+-------------------------------------------+------------------+----------+-----------+
        | application              | version  | manifest name                             | manifest file    | status   | progress  |
        +--------------------------+----------+-------------------------------------------+------------------+----------+-----------+
        | cert-manager             | 24.09-78 | cert-manager-fluxcd-manifests             | fluxcd-manifests | applied  | completed |
        | dell-storage             | 24.09-25 | dell-storage-fluxcd-manifests             | fluxcd-manifests | uploaded | completed |
        | deployment-manager       | 24.09-19 | deployment-manager-fluxcd-manifests       | fluxcd-manifests | applied  | completed |
        | nginx-ingress-controller | 24.09-61 | nginx-ingress-controller-fluxcd-manifests | fluxcd-manifests | applied  | completed |
        | oidc-auth-apps           | 24.09-56 | oidc-auth-apps-fluxcd-manifests           | fluxcd-manifests | uploaded | completed |
        | platform-integ-apps      | 24.      | platform-integ-apps-fluxcd-manifests      | fluxcd-manifests | uploaded | completed |
        |                          | 09-140   |                                           |                  |          |           |
        |                          |          |                                           |                  |          |           |
        | rook-ceph                | 24.09-36 | rook-ceph-fluxcd-manifests                | fluxcd-manifests | uploaded | completed |
        +--------------------------+----------+-------------------------------------------+------------------+----------+-----------+

    """

    def __init__(self, system_application_list_output: str) -> None:
        """Initialize SystemApplicationListOutput with parsed application data.

        Args:
            system_application_list_output (str): The output of the 'system application-list' command.
        """
        self.system_applications: [SystemApplicationListObject] = []
        system_table_parser = SystemTableParser(system_application_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                self.system_applications.append(
                    SystemApplicationListObject(
                        value["application"],
                        value["version"],
                        value["manifest name"],
                        value["manifest file"],
                        value["status"],
                        value["progress"],
                    )
                )
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_applications(self) -> list[SystemApplicationListObject]:
        """Get the list of all application objects.

        Returns:
            list[SystemApplicationListObject]: List of SystemApplicationListObject instances.
        """
        return self.system_applications

    def get_application(self, application: str) -> SystemApplicationListObject:
        """Get a specific application by name.

        Args:
            application (str): The name of the application to retrieve.

        Returns:
            SystemApplicationListObject: The application object.

        Raises:
            KeywordException: If no application with the given name is found.
        """
        applications = list(filter(lambda app: app.get_application() == application, self.system_applications))
        if len(applications) == 0:
            raise KeywordException(f"No application with name {application} was found.")

        return applications[0]

    def application_exists(self, application: str) -> bool:
        """Check if an application exists in the list.

        Args:
            application (str): The name of the application to check.

        Returns:
            bool: True if the application exists, False otherwise.
        """
        applications = list(filter(lambda app: app.get_application() == application, self.system_applications))
        return len(applications) > 0

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Validate that output contains all required keys.

        Args:
            value (dict): The parsed output value to validate.

        Returns:
            bool: True if the output is valid, False otherwise.
        """
        valid = True
        if "application" not in value:
            get_logger().log_error(f"application is not in the output value: {value}")
            valid = False
        if "version" not in value:
            get_logger().log_error(f"version is not in the output value: {value}")
            valid = False
        if "manifest name" not in value:
            get_logger().log_error(f"manifest name is not in the output value: {value}")
            valid = False
        if "manifest file" not in value:
            get_logger().log_error(f"manifest file is not in the output value: {value}")
            valid = False
        if "status" not in value:
            get_logger().log_error(f"status is not in the output value: {value}")
            valid = False
        if "progress" not in value:
            get_logger().log_error(f"progress is not in the output value: {value}")
            valid = False

        return valid

    def is_in_application_list(self, application_name: str) -> bool:
        """
        Verifies if there is an application with the name 'app_name' on the host.

        Args:
             application_name (str): a string representing the application's name.

        Returns:
             bool: True if there is an application with the name 'app_name' on the host; False otherwise.
        """
        applications = list(filter(lambda app: app.get_application() == application_name, self.system_applications))
        if len(applications) == 0:
            return False
        return True
