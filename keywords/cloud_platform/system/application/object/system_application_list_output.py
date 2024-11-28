from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.application.object.system_application_list_object import SystemApplicationListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemApplicationListOutput:
    """
    This class parses the output of the command 'system application-list'
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

    def __init__(self, system_application_list_output):
        """
        Constructor
        Args:
            system_application_list_output: the output of the command 'system application-list'.
        """
        self.system_applications: [SystemApplicationListObject] = []
        system_table_parser = SystemTableParser(system_application_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                self.system_applications.append(
                    SystemApplicationListObject(
                        value['application'],
                        value['version'],
                        value['manifest name'],
                        value['manifest file'],
                        value['status'],
                        value['progress'],
                    )
                )
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_applications(self) -> [SystemApplicationListObject]:
        """
        Returns the list of applications objects
        Returns:

        """
        return self.system_applications

    def get_application(self, application: str) -> SystemApplicationListObject:
        """
        Gets the given application
        Args:
            application (): the name of the application

        Returns: the application object

        """
        applications = list(filter(lambda app: app.get_application() == application, self.system_applications))
        if len(applications) == 0:
            raise KeywordException(f"No application with name {application} was found.")

        return applications[0]

    @staticmethod
    def is_valid_output(value):
        """
        Checks to ensure the output has the correct keys
        Args:
            value (): the value to check

        Returns:

        """
        valid = True
        if 'application' not in value:
            get_logger().log_error(f'application is not in the output value: {value}')
            valid = False
        if 'version' not in value:
            get_logger().log_error(f'version is not in the output value: {value}')
            valid = False
        if 'manifest name' not in value:
            get_logger().log_error(f'manifest name is not in the output value: {value}')
            valid = False
        if 'manifest file' not in value:
            get_logger().log_error(f'manifest file is not in the output value: {value}')
            valid = False
        if 'status' not in value:
            get_logger().log_error(f'status is not in the output value: {value}')
            valid = False
        if 'progress' not in value:
            get_logger().log_error(f'progress is not in the output value: {value}')
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
