from datetime import datetime

from keywords.cloud_platform.fault_management.fm_client_cli.object.alarm_action_enum import AlarmAction


class FaultManagementClientCLIObject:
    """
    Class to assist in constructing the parameters for the fmClientCli command.
    """

    DEFAULT_ALARM_ID = "100.106"

    def __init__(self):
        """
        Constructor
        """
        self.alarm_action = AlarmAction.CREATE
        self.alarm_id = FaultManagementClientCLIObject.DEFAULT_ALARM_ID
        self.alarm_state: str = "set"
        self.entity_type_id: str = "k8s_application"
        self.entity_id: str = "resource=host.starlingx.windriver.com,name=controller-0"
        self.timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.severity: str = "major"
        self.reason_text: str = "Application Apply Failure"
        self.alarm_type: str = "processing-error"
        self.probable_cause: str = "processor overload"
        self.proposed_repair_action: str = "Retry applying the application"

    def set_alarm_action(self, alarm_action: AlarmAction):
        """
        Setter for the alarm_action.
        """
        self.alarm_action = alarm_action

    def get_alarm_action(self) -> AlarmAction:
        """
        Getter for the alarm_action.
        """
        return self.alarm_action

    def set_alarm_id(self, alarm_id: str):
        """
        Setter for the alarm_id.
        """
        self.alarm_id = alarm_id

    def get_alarm_id(self) -> str:
        """
        Getter for the alarm_id.
        """
        return self.alarm_id

    def set_alarm_state(self, alarm_state: str):
        """
        Setter for the alarm_state.

        Args: alarm_state (str): "set" or "clear"
        """
        self.alarm_state = alarm_state

    def get_alarm_state(self) -> str:
        """
        Getter for the alarm_state.
        """
        return self.alarm_state

    def set_entity_type_id(self, entity_type_id: str):
        """
        Setter for the entity_type_id.
        """
        self.entity_type_id = entity_type_id

    def get_entity_type_id(self) -> str:
        """
        Getter for the entity_type_id.
        """
        return self.entity_type_id

    def set_entity_id(self, entity_id: str):
        """
        Setter for the entity_id.
        """
        self.entity_id = entity_id

    def get_entity_id(self) -> str:
        """
        Getter for the entity_id.
        """
        return self.entity_id

    def set_timestamp(self, timestamp: str):
        """
        Setter for the timestamp.
        """
        self.timestamp = timestamp

    def get_timestamp(self) -> str:
        """
        Getter for the timestamp.
        """
        return self.timestamp

    def set_severity(self, severity: str):
        """
        Setter for the severity.
        """
        self.severity = severity

    def get_severity(self) -> str:
        """
        Getter for the severity.
        """
        return self.severity

    def set_reason_text(self, reason_text: str):
        """
        Setter for the reason_text.
        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """
        Getter for the reason_text.
        """
        return self.reason_text

    def set_alarm_type(self, alarm_type: str):
        """
        Setter for the alarm_type.
        """
        self.alarm_type = alarm_type

    def get_alarm_type(self) -> str:
        """
        Getter for the alarm_type.
        """
        return self.alarm_type

    def set_probable_cause(self, probable_cause: str):
        """
        Setter for the probable_cause.
        """
        self.probable_cause = probable_cause

    def get_probable_cause(self) -> str:
        """
        Getter for the probable_cause.
        """
        return self.probable_cause

    def set_proposed_repair_action(self, proposed_repair_action: str):
        """
        Setter for the proposed_repair_action.
        """
        self.proposed_repair_action = proposed_repair_action

    def get_proposed_repair_action(self) -> str:
        """
        Getter for the proposed_repair_action.
        """
        return self.proposed_repair_action
