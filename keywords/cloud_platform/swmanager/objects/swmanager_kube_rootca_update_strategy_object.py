class SwManagerKubeRootcaUpdateStrategyObject:
    """Object representing a kube-rootca-update strategy."""

    def __init__(self):
        """Initialize strategy object."""
        self.strategy_name = None
        self.controller_apply_type = None
        self.storage_apply_type = None
        self.worker_apply_type = None
        self.max_parallel_worker_hosts = None
        self.default_instance_action = None
        self.alarm_restrictions = None
        self.current_phase = None
        self.current_phase_completion_percentage = None
        self.state = None
        self.expiry_date = None
        self.subject = None

    def get_state(self) -> str:
        """Get strategy state.

        Returns:
            str: Strategy state value.
        """
        return self.state

    def set_state(self, state: str) -> None:
        """Set strategy state.

        Args:
            state (str): Strategy state value.
        """
        self.state = state

    def get_current_phase(self) -> str:
        """Get current phase of strategy execution.

        Returns:
            str: Current phase name.
        """
        return self.current_phase

    def set_current_phase(self, phase: str) -> None:
        """Set current phase of strategy execution.

        Args:
            phase (str): Phase name.
        """
        self.current_phase = phase

    def get_current_stage(self) -> str:
        """Get current stage extracted from phase.

        Returns:
            str: Current stage name (first part before hyphen in phase).
        """
        if self.current_phase and "-" in self.current_phase:
            return self.current_phase.split("-")[0]
        return self.current_phase

    def get_current_phase_completion(self) -> str:
        """Get current phase completion percentage.

        Returns:
            str: Completion percentage string.
        """
        return self.current_phase_completion_percentage

    def set_current_phase_completion_percentage(self, percentage: str) -> None:
        """Set current phase completion percentage.

        Args:
            percentage (str): Completion percentage string.
        """
        self.current_phase_completion_percentage = percentage

    def is_building(self) -> bool:
        """Check if strategy is building.

        Returns:
            bool: True if building, False otherwise.
        """
        return self.state == "building"

    def is_build_failed(self) -> bool:
        """Check if strategy build failed.

        Returns:
            bool: True if build failed, False otherwise.
        """
        return self.state == "build-failed"

    def is_ready_to_apply(self) -> bool:
        """Check if strategy is ready to apply.

        Returns:
            bool: True if ready to apply, False otherwise.
        """
        return self.state == "ready-to-apply"

    def is_applying(self) -> bool:
        """Check if strategy is applying.

        Returns:
            bool: True if applying, False otherwise.
        """
        return self.state == "applying"

    def is_apply_failed(self) -> bool:
        """Check if strategy apply failed.

        Returns:
            bool: True if apply failed, False otherwise.
        """
        return self.state == "apply-failed"

    def is_applied(self) -> bool:
        """Check if strategy is applied.

        Returns:
            bool: True if applied, False otherwise.
        """
        return self.state == "applied"
