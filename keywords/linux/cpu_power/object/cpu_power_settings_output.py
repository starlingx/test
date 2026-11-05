import re

from keywords.files.object.head_files_output import HeadFilesOutput
from keywords.linux.cpu_power.object.cpu_power_settings_object import CpuPowerSettingsObject

INTEL_PSTATE_STATUS = "/sys/devices/system/cpu/intel_pstate/status"
INTEL_PSTATE_NO_TURBO = "/sys/devices/system/cpu/intel_pstate/no_turbo"
AMD_PSTATE_STATUS = "/sys/devices/system/cpu/amd_pstate/status"
CPUFREQ_BOOST = "/sys/devices/system/cpu/cpufreq/boost"
SCALING_DRIVER = "/sys/devices/system/cpu/cpufreq/policy0/scaling_driver"
CPUIDLE_DRIVER = "/sys/devices/system/cpu/cpuidle/current_driver"
CPU0_CSTATE_NAME_PATTERN = re.compile(r"/sys/devices/system/cpu/cpu0/cpuidle/state(\d+)/name")
SMT_ACTIVE = "/sys/devices/system/cpu/smt/active"
INTEL_IDLE_MAX_CSTATE = "/sys/module/intel_idle/parameters/max_cstate"
ACPI_IDLE_MAX_CSTATE = "/sys/module/processor/parameters/max_cstate"


class CpuPowerSettingsOutput:
    """Derives effective P-state, C-state, turbo and SMT settings from sysfs files."""

    FILE_PATTERNS = [
        INTEL_PSTATE_STATUS,
        INTEL_PSTATE_NO_TURBO,
        AMD_PSTATE_STATUS,
        CPUFREQ_BOOST,
        SCALING_DRIVER,
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_governor",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq",
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq",
        CPUIDLE_DRIVER,
        "/sys/devices/system/cpu/cpuidle/current_governor_ro",
        "/sys/devices/system/cpu/cpu0/cpuidle/state*/name",
        "/sys/devices/system/cpu/cpu0/cpuidle/state*/disable",
        SMT_ACTIVE,
        "/sys/devices/system/cpu/smt/control",
        INTEL_IDLE_MAX_CSTATE,
        ACPI_IDLE_MAX_CSTATE,
        "/sys/module/kvm_intel/parameters/nested",
        "/sys/module/kvm_amd/parameters/nested",
    ]

    def __init__(self, head_files_output: HeadFilesOutput):
        """Constructor.

        Args:
            head_files_output (HeadFilesOutput): Contents of the CPU power sysfs files.
        """
        evidence = head_files_output.get_file_contents()
        self.cpu_power_settings_object = CpuPowerSettingsObject()
        self.cpu_power_settings_object.set_evidence(evidence)
        self.cpu_power_settings_object.set_p_state_management(self._derive_p_state_management(evidence))
        self.cpu_power_settings_object.set_c_state_management(self._derive_c_state_management(evidence))
        self.cpu_power_settings_object.set_turbo(self._derive_turbo(evidence))
        self.cpu_power_settings_object.set_smt(self._derive_smt(evidence))

    @staticmethod
    def _consensus(indicators: list[str]) -> str:
        """Return a state only when every available indicator agrees.

        Args:
            indicators (list[str]): enabled/disabled readings from independent files.

        Returns:
            str: The agreed state, or unknown when there are no indicators or they disagree.
        """
        states = set(indicators)
        return states.pop() if len(states) == 1 else "unknown"

    def _derive_p_state_management(self, evidence: dict[str, str]) -> str:
        """Derive whether the OS manages P-states from the pstate and cpufreq drivers.

        Args:
            evidence (dict[str, str]): sysfs path to contents.

        Returns:
            str: enabled, disabled or unknown.
        """
        indicators = []
        pstate_status = evidence.get(INTEL_PSTATE_STATUS) or evidence.get(AMD_PSTATE_STATUS)
        if pstate_status in {"active", "passive", "guided"}:
            indicators.append("enabled")
        elif pstate_status == "disable":
            indicators.append("disabled")
        scaling_driver = evidence.get(SCALING_DRIVER)
        if scaling_driver:
            indicators.append("disabled" if scaling_driver == "none" else "enabled")
        return self._consensus(indicators)

    @staticmethod
    def _derive_c_state_management(evidence: dict[str, str]) -> str:
        """Derive whether idle states deeper than POLL are usable on cpu0.

        Args:
            evidence (dict[str, str]): sysfs path to contents.

        Returns:
            str: enabled, disabled or unknown.
        """
        idle_driver = evidence.get(CPUIDLE_DRIVER)
        max_cstate = None
        if idle_driver == "intel_idle":
            max_cstate = evidence.get(INTEL_IDLE_MAX_CSTATE)
        elif idle_driver == "acpi_idle":
            max_cstate = evidence.get(ACPI_IDLE_MAX_CSTATE)
        if idle_driver == "none" or max_cstate == "0":
            return "disabled"

        states = []
        for path, name in evidence.items():
            match = CPU0_CSTATE_NAME_PATTERN.fullmatch(path)
            if match:
                disabled = evidence.get(f"/sys/devices/system/cpu/cpu0/cpuidle/state{match.group(1)}/disable")
                states.append((name.upper(), disabled))
        if any(name != "POLL" and disabled == "0" for name, disabled in states):
            return "enabled"
        if states and all(name == "POLL" or disabled == "1" for name, disabled in states):
            return "disabled"
        return "unknown"

    def _derive_turbo(self, evidence: dict[str, str]) -> str:
        """Derive whether turbo is allowed from intel_pstate no_turbo and cpufreq boost.

        Args:
            evidence (dict[str, str]): sysfs path to contents.

        Returns:
            str: enabled, disabled or unknown.
        """
        indicators = []
        no_turbo = evidence.get(INTEL_PSTATE_NO_TURBO)
        if no_turbo in {"0", "1"}:
            indicators.append("enabled" if no_turbo == "0" else "disabled")
        boost = evidence.get(CPUFREQ_BOOST)
        if boost in {"0", "1"}:
            indicators.append("enabled" if boost == "1" else "disabled")
        return self._consensus(indicators)

    @staticmethod
    def _derive_smt(evidence: dict[str, str]) -> str:
        """Derive whether SMT is active.

        Args:
            evidence (dict[str, str]): sysfs path to contents.

        Returns:
            str: enabled, disabled or unknown.
        """
        return {"1": "enabled", "0": "disabled"}.get(evidence.get(SMT_ACTIVE), "unknown")

    def get_cpu_power_settings_object(self) -> CpuPowerSettingsObject:
        """Get the derived CPU power settings.

        Returns:
            CpuPowerSettingsObject: Derived settings and their sysfs evidence.
        """
        return self.cpu_power_settings_object
