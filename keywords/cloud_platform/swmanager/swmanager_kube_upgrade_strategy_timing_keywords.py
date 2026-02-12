from datetime import datetime
from typing import Optional

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.swmanager.objects.swmanager_kube_upgrade_strategy_timing import SwManagerKubeUpgradeStrategyTiming
from keywords.cloud_platform.upgrade.objects.upgrade_event import UpgradeEvent
from keywords.cloud_platform.upgrade.record_upgrade_event_keywords import RecordUpgradeEventKeywords


class SwManagerKubeUpgradeStrategyTimingKeywords:
    """Keywords for extracting and parsing kube upgrade strategy timing information."""

    def extract_kube_upgrade_strategy_timings(self, output: list[str], from_version: str, to_version: str) -> list[SwManagerKubeUpgradeStrategyTiming]:
        """Extract individual timings from sw-manager kube-upgrade-strategy show --details output.

        This function parses the hierarchical output from 'sw-manager kube-upgrade-strategy show --details'
        and extracts timing information for all stages and steps within the apply-phase. The build-phase
        is intentionally ignored as it's not relevant for upgrade performance analysis.

        The output structure is:
        - build-phase (ignored)
        - apply-phase
          - stage 0: kube-upgrade-start
            - step: kube-upgrade-start
          - stage 1: kube-upgrade-download-images
            - step: kube-upgrade-download-images
          - stage N: kube-upgrade-kubelet v1.32.2
            - step: query-alarms
            - step: swact-hosts
            - step: lock-hosts
            - step: kube-host-upgrade-kubelet
            - step: system-stabilize
            - step: unlock-hosts
            - step: wait-alarms-clear

        Each stage and step has start-date-time and end-date-time fields that are parsed to calculate
        the duration. This provides granular visibility into where time is spent during the upgrade.

        Args:
            output (list[str]): Command output lines from 'sw-manager kube-upgrade-strategy show --details'.
            from_version (str): The starting Kubernetes version.
            to_version (str): The target Kubernetes version.

        Returns:
            list[SwManagerKubeUpgradeStrategyTiming]: List of timing objects for apply-phase stages and steps,
                each containing name, start time, end time, and calculated duration in seconds/minutes.
        """
        timings = []
        in_apply_phase = False
        current_stage = None

        for line in output:
            stripped = line.strip()

            # Track when entering/exiting build-phase (ignored)
            if "build-phase:" in stripped:
                in_apply_phase = False
                continue
            # Track when entering apply-phase (where we extract timings)
            if "apply-phase:" in stripped:
                in_apply_phase = True
                current_stage = None
                continue

            # Skip all lines outside apply-phase
            if not in_apply_phase:
                continue

            # Extract and track current stage name for later timing association
            if "stage-name:" in stripped:
                current_stage = stripped.split("stage-name:")[-1].strip()
                continue

            # Create new timing object for each step
            if "step-name:" in stripped:
                step_name = stripped.split("step-name:")[-1].strip()
                timing = SwManagerKubeUpgradeStrategyTiming()
                timing.set_name(step_name)
                timing.set_is_stage(False)
                timing.set_parent_stage(current_stage)
                timing.set_from_version(from_version)
                timing.set_to_version(to_version)
                timings.append(timing)
                continue

            # Extract entity names for steps and propagate to parent stage
            if "entity-names:" in stripped and timings and not timings[-1].is_stage():
                entity_names_str = stripped.split("entity-names:")[-1].strip()
                timings[-1].set_entity_names(entity_names_str)
                # Find parent stage and add entity names to it
                for timing in reversed(timings):
                    if timing.is_stage() and timing.get_name() == current_stage:
                        timing.set_entity_names(entity_names_str)
                        break
                continue

            # Handle start-date-time for both stages and steps
            if "start-date-time:" in stripped:
                start_time = self._parse_datetime(stripped.split("start-date-time:")[-1].strip())
                if start_time:
                    # Create new stage timing if we have a stage name and previous timing is complete
                    if current_stage and (not timings or timings[-1].get_start_date_time()):
                        timing = SwManagerKubeUpgradeStrategyTiming()
                        timing.set_name(current_stage)
                        timing.set_start_date_time(start_time)
                        timing.set_is_stage(True)
                        timing.set_from_version(from_version)
                        timing.set_to_version(to_version)
                        timings.append(timing)
                    # Set start time on most recent timing object (step)
                    elif timings and not timings[-1].get_start_date_time():
                        timings[-1].set_start_date_time(start_time)
                continue

            # Handle end-date-time and calculate duration
            if "end-date-time:" in stripped and timings:
                end_time = self._parse_datetime(stripped.split("end-date-time:")[-1].strip())
                # Only set end time if start time exists and end time hasn't been set yet
                if end_time and timings[-1].get_start_date_time() and not timings[-1].get_end_date_time():
                    timings[-1].set_end_date_time(end_time)
                    timings[-1].calculate_duration()

        return timings

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string from strategy output.

        Args:
            datetime_str (str): Datetime string in format 'YYYY-MM-DD HH:MM:SS'.

        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails.
        """
        try:
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            return None

    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable string.

        Args:
            seconds (int): Duration in seconds.

        Returns:
            str: Formatted duration as '1 minute 2 seconds'.
        """
        minutes = seconds // 60
        secs = seconds % 60
        minute_str = "minute" if minutes == 1 else "minutes"
        second_str = "second" if secs == 1 else "seconds"

        if minutes > 0 and secs > 0:
            return f"{minutes} {minute_str} {secs} {second_str}"
        elif minutes > 0:
            return f"{minutes} {minute_str}"
        else:
            return f"{secs} {second_str}"

    def format_upgrade_timings(self, timings: list[SwManagerKubeUpgradeStrategyTiming], from_version: str, to_version: str) -> str:
        """Format upgrade timings into a readable string.

        Args:
            timings (list[SwManagerKubeUpgradeStrategyTiming]): List of timing objects.
            from_version (str): The starting Kubernetes version.
            to_version (str): The target Kubernetes version.

        Returns:
            str: Formatted timing information.
        """
        total_duration_seconds = self.calculate_total_duration(timings)
        output_lines = [f"\nTotal KPI: Kubernetes upgrade from {from_version} to {to_version}: {self.format_duration(total_duration_seconds)}"]

        for timing in timings:
            entity_info = f" {timing.get_entity_names()}" if timing.get_entity_names() else ""
            duration = self.format_duration(timing.get_duration_seconds())
            if timing.is_stage():
                output_lines.append(f"       Stage: {timing.get_name()}{entity_info}: {duration}")
            else:
                parent = timing.get_parent_stage()
                output_lines.append(f"                  Step [{parent}]: {timing.get_name()}{entity_info}: {duration}")

        return "\n".join(output_lines)

    def calculate_total_duration(self, timings: list[SwManagerKubeUpgradeStrategyTiming]) -> int:
        """Calculate total duration from first to last step.

        Args:
            timings (list[SwManagerKubeUpgradeStrategyTiming]): List of timing objects.

        Returns:
            int: Total duration in seconds.
        """
        # Find kube-upgrade-start step (first step)
        start_step = next((t for t in timings if t.get_name() == "kube-upgrade-start" and not t.is_stage()), None)
        # Find kube-upgrade-cleanup step (last step)
        cleanup_step = next((t for t in timings if t.get_name() == "kube-upgrade-cleanup" and not t.is_stage()), None)

        start_time = start_step.get_start_date_time()
        end_time = cleanup_step.get_end_date_time()

        get_logger().log_info(f"K8 Upgrade start time: {start_time}")
        get_logger().log_info(f"K8 Upgrade end time: {end_time}")

        # Calculate wall clock duration: cleanup end - start begin
        duration = int((end_time - start_time).total_seconds())
        get_logger().log_info(f"Total wall clock duration: {self.format_duration(duration)}")

        return duration

    def save_kube_upgrade_kpi_to_database(self, timings: list[SwManagerKubeUpgradeStrategyTiming], from_version: str, to_version: str) -> None:
        """Save Kubernetes upgrade KPI to database.

        Args:
            timings (list[SwManagerKubeUpgradeStrategyTiming]): List of timing objects.
            from_version (str): The starting Kubernetes version.
            to_version (str): The target Kubernetes version.
        """
        record_keywords = RecordUpgradeEventKeywords()

        # Save total upgrade duration
        total_duration = self.calculate_total_duration(timings)
        total_event = UpgradeEvent(event_name="kube-upgrade-total", retry=0, operation="kube-upgrade", entry="kubernetes", is_upgrade=True, is_patch=False)
        total_event.set_duration(total_duration)
        total_event.set_from_version(from_version)
        total_event.set_to_version(to_version)
        record_keywords.record_upgrade_event(total_event)

        # Save each stage timing
        for timing in timings:
            if timing.is_stage():
                # Clean entity names by removing brackets and quotes
                entity = timing.get_entity_names() or "kubernetes"
                entity = entity.strip("[]").replace("'", "").replace('"', "")

                stage_event = UpgradeEvent(event_name=f"kube-stage:{timing.get_name()}", retry=0, operation="kube-upgrade", entry=entity, is_upgrade=True, is_patch=False)
                stage_event.set_duration(timing.get_duration_seconds())
                stage_event.set_from_version(from_version)
                stage_event.set_to_version(to_version)
                record_keywords.record_upgrade_event(stage_event)

        # Save each step timing
        for timing in timings:
            if not timing.is_stage():
                # Clean entity names by removing brackets and quotes
                entity = timing.get_entity_names() or "kubernetes"
                entity = entity.strip("[]").replace("'", "").replace('"', "")

                step_event = UpgradeEvent(event_name=f"kube-step:{timing.get_name()}", retry=0, operation="kube-upgrade", entry=entity, is_upgrade=True, is_patch=False)
                step_event.set_duration(timing.get_duration_seconds())
                step_event.set_from_version(from_version)
                step_event.set_to_version(to_version)
                record_keywords.record_upgrade_event(step_event)
