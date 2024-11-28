from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.fm_client_cli.object.alarm_action_enum import AlarmAction
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject


class FaultManagementClientCLIKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'fmClientCli' command.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor
        Args:
            ssh_connection: the SSH connection to the host.
        """
        self.ssh_connection = ssh_connection

    def raise_alarm(self, fm_client_cli_object: FaultManagementClientCLIObject = None):
        """
        Raises an alarm as configured in the parameter 'fm_client_cli_object'.

        Args:
            fm_client_cli_object(FaultManagementClientCLIObject): the object containing the configuration of the alarm
            to be raised.

        """
        if not fm_client_cli_object:
            fm_client_cli_object = FaultManagementClientCLIObject()
        fm_client_cli_object.set_alarm_action(AlarmAction.CREATE)
        fm_client_cli_object.set_alarm_state("set")

        command = (
            f"fmClientCli {fm_client_cli_object.get_alarm_action().value} \"f0aaasdsadsd###"
            f"{fm_client_cli_object.get_alarm_id()}###"
            f"{fm_client_cli_object.get_alarm_state()}###"
            f"{fm_client_cli_object.get_entity_type_id()}###"
            f"{fm_client_cli_object.get_entity_id()}###"
            f"{fm_client_cli_object.get_timestamp()}###"
            f"{fm_client_cli_object.get_severity()}###"
            f"{fm_client_cli_object.get_reason_text()}###"
            f"{fm_client_cli_object.get_alarm_type()}###"
            f"{fm_client_cli_object.get_probable_cause()}###"
            f"{fm_client_cli_object.get_proposed_repair_action()}###"
            f"True###False###False###\""
        )

        self.ssh_connection.send(command)

    def delete_alarm(self, fm_client_cli_object: FaultManagementClientCLIObject):
        """
        Deletes the alarm as configured in the fm_client_cli_object parameter.

        Args:
            fm_client_cli_object(FaultManagementClientCLIObject): the object containing the configuration of the alarm
            to be deleted.

        """
        fm_client_cli_object.set_alarm_action(AlarmAction.DELETE)
        command = f"fmClientCli {fm_client_cli_object.get_alarm_action().value} {fm_client_cli_object.get_entity_id()}"

        self.ssh_connection.send(command)
