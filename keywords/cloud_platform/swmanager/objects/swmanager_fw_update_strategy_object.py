from typing import Optional


class SwmanagerFwUpdateStrategyObject:
    """
    This class represents a sw-manager fw-update-strategy as an object.
    """

    def __init__(self) -> None:
        """Initializes a SwmanagerFwUpdateStrategyObject with default values."""
        self.strategy_uuid: Optional[str] = None
        self.controller_apply_type: Optional[str] = None
        self.storage_apply_type: Optional[str] = None
        self.worker_apply_type: Optional[str] = None
        self.default_instance_action: Optional[str] = None
        self.alarm_restrictions: Optional[str] = None
        self.current_phase: Optional[str] = None
        self.current_stage: Optional[str] = None
        self.current_step: Optional[str] = None
        self.current_phase_completion: Optional[str] = None
        self.state: Optional[str] = None
        self.inprogress: Optional[str] = None
        self.build_result: Optional[str] = None
        self.build_reason: Optional[str] = None

    def set_strategy_uuid(self, strategy_uuid: str) -> None:
        """Sets the strategy_uuid of the fw-update-strategy."""
        self.strategy_uuid = strategy_uuid

    def get_strategy_uuid(self) -> Optional[str]:
        """Gets the strategy_uuid of the fw-update-strategy."""
        return self.strategy_uuid

    def set_controller_apply_type(self, controller_apply_type: str) -> None:
        """Sets the controller_apply_type of the fw-update-strategy."""
        self.controller_apply_type = controller_apply_type

    def get_controller_apply_type(self) -> Optional[str]:
        """Gets the controller_apply_type of the fw-update-strategy."""
        return self.controller_apply_type

    def set_storage_apply_type(self, storage_apply_type: str) -> None:
        """Sets the storage_apply_type of the fw-update-strategy."""
        self.storage_apply_type = storage_apply_type

    def get_storage_apply_type(self) -> Optional[str]:
        """Gets the storage_apply_type of the fw-update-strategy."""
        return self.storage_apply_type

    def set_worker_apply_type(self, worker_apply_type: str) -> None:
        """Sets the worker_apply_type of the fw-update-strategy."""
        self.worker_apply_type = worker_apply_type

    def get_worker_apply_type(self) -> Optional[str]:
        """Gets the worker_apply_type of the fw-update-strategy."""
        return self.worker_apply_type

    def set_default_instance_action(self, default_instance_action: str) -> None:
        """Sets the default_instance_action of the fw-update-strategy."""
        self.default_instance_action = default_instance_action

    def get_default_instance_action(self) -> Optional[str]:
        """Gets the default_instance_action of the fw-update-strategy."""
        return self.default_instance_action

    def set_alarm_restrictions(self, alarm_restrictions: str) -> None:
        """Sets the alarm_restrictions of the fw-update-strategy."""
        self.alarm_restrictions = alarm_restrictions

    def get_alarm_restrictions(self) -> Optional[str]:
        """Gets the alarm_restrictions of the fw-update-strategy."""
        return self.alarm_restrictions

    def set_current_phase(self, current_phase: str) -> None:
        """Sets the current_phase of the fw-update-strategy."""
        self.current_phase = current_phase

    def get_current_phase(self) -> Optional[str]:
        """Gets the current_phase of the fw-update-strategy."""
        return self.current_phase

    def set_current_stage(self, current_stage: str) -> None:
        """Sets the current_stage of the fw-update-strategy."""
        self.current_stage = current_stage

    def get_current_stage(self) -> Optional[str]:
        """Gets the current_stage of the fw-update-strategy."""
        return self.current_stage

    def set_current_step(self, current_step: str) -> None:
        """Sets the current_step of the fw-update-strategy."""
        self.current_step = current_step

    def get_current_step(self) -> Optional[str]:
        """Gets the current_step of the fw-update-strategy."""
        return self.current_step

    def set_current_phase_completion(self, current_phase_completion: str) -> None:
        """Sets the current_phase_completion of the fw-update-strategy."""
        self.current_phase_completion = current_phase_completion

    def get_current_phase_completion(self) -> Optional[str]:
        """Gets the current_phase_completion of the fw-update-strategy."""
        return self.current_phase_completion

    def set_state(self, state: str) -> None:
        """Sets the state of the fw-update-strategy."""
        self.state = state

    def get_state(self) -> Optional[str]:
        """Gets the state of the fw-update-strategy."""
        return self.state

    def set_inprogress(self, inprogress: str) -> None:
        """Sets the inprogress of the fw-update-strategy."""
        self.inprogress = inprogress

    def get_inprogress(self) -> Optional[str]:
        """Gets the inprogress of the fw-update-strategy."""
        return self.inprogress

    def set_build_result(self, build_result: str) -> None:
        """Sets the build_result of the fw-update-strategy."""
        self.build_result = build_result

    def get_build_result(self) -> Optional[str]:
        """Gets the build_result of the fw-update-strategy."""
        return self.build_result

    def set_build_reason(self, build_reason: str) -> None:
        """Sets the build_reason of the fw-update-strategy."""
        self.build_reason = build_reason

    def get_build_reason(self) -> Optional[str]:
        """Gets the build_reason of the fw-update-strategy."""
        return self.build_reason
