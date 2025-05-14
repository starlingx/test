from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class HealthKeywords(BaseKeyword):
    """Class for health Keywords for Cloud Platform"""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def validate_healty_cluster(self):
        """Function to validate the health of the cluster

        This function checks the health of the cluster which consists of
            1. validate all pods are healty
            2. validate no alarms are present
            3. validate all apps are healty and applied
        """
        # Validate all pods are healthy
        self.validate_pods_health()
        # Validate no alarms are present
        self.validate_no_alarms()
        # Validate all apps are healthy and applied
        self.validate_apps_health_and_applied()

    def validate_pods_health(self):
        """Function to validate the health of all pods in the cluster"""
        healthy_status = ["Running", "Succeeded", "Completed"]
        KubectlGetPodsKeywords(self.ssh_connection).wait_for_all_pods_status(healthy_status, timeout=300)

    def validate_no_alarms(self):
        """Function to validate no alarms are present in the cluster"""
        AlarmListKeywords(self.ssh_connection).wait_for_all_alarms_cleared()

    def validate_apps_health_and_applied(self):
        """Function to validate all apps are healthy and applied"""
        healthy_status = ["applied", "uploaded"]
        SystemApplicationListKeywords(self.ssh_connection).validate_all_apps_status(healthy_status)
