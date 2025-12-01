from keywords.cloud_platform.system.healthquery.objects.system_health_query_object import SystemHealthQueryObject
from keywords.cloud_platform.system.healthquery.system_health_query_parser import SystemHealthQueryParser


class SystemHealthQueryKubeUpgradeOutput:
    """
    Parses the output of the 'system health-query-kube-upgrade' command into a list of SystemHealthQueryObject instances.
    """

    def __init__(self, system_health_query_output: str):
        """
        Initializes class SystemHealthQueryKubeUpgradeOutput.

        Args:
            system_health_query_output (str): Output of the 'system health-query-kube-upgrade' command.
        """
        self.system_health_queries = []

        system_health_query_parser = SystemHealthQueryParser(system_health_query_output)
        health_checks = system_health_query_parser.get_output_values_dict()

        for check_name, check_data in health_checks.items():
            system_health_query_object = SystemHealthQueryObject()
            system_health_query_object.set_check_name(check_name)
            system_health_query_object.set_status(check_data["status"])

            if "reason" in check_data:
                system_health_query_object.set_reason(check_data["reason"])

            self.system_health_queries.append(system_health_query_object)

    def is_all_healthy(self) -> bool:
        """
        Checks if all health checks have OK status.

        Returns:
            bool: True if all health checks have OK status, False otherwise.
        """
        return all(item.is_ok() for item in self.system_health_queries)

    def get_failed_checks(self) -> list[SystemHealthQueryObject]:
        """
        Retrieves health checks that are not OK.

        Returns:
            list[SystemHealthQueryObject]: List of health check objects with non-OK status.
        """
        return [item for item in self.system_health_queries if not item.is_ok()]
