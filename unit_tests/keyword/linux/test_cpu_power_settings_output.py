from keywords.files.object.head_files_output import HeadFilesOutput
from keywords.linux.cpu_power.object.cpu_power_settings_object import CpuPowerSettingsObject
from keywords.linux.cpu_power.object.cpu_power_settings_output import CpuPowerSettingsOutput


def _settings(files: dict[str, str]) -> CpuPowerSettingsObject:
    """Build settings from a path-to-content mapping.

    Args:
        files (dict[str, str]): sysfs path to contents.

    Returns:
        CpuPowerSettingsObject: Derived settings.
    """
    text = "".join(f"==> {path} <==\n{content}\n" for path, content in files.items())
    return CpuPowerSettingsOutput(HeadFilesOutput(text)).get_cpu_power_settings_object()


def test_performance_host_with_c_states_and_turbo():
    """Derive the settings seen on a lab host running intel_cpufreq in passive mode."""
    settings = _settings(
        {
            "/sys/devices/system/cpu/intel_pstate/status": "passive",
            "/sys/devices/system/cpu/intel_pstate/no_turbo": "0",
            "/sys/devices/system/cpu/cpufreq/policy0/scaling_driver": "intel_cpufreq",
            "/sys/devices/system/cpu/cpuidle/current_driver": "intel_idle",
            "/sys/module/intel_idle/parameters/max_cstate": "9",
            "/sys/devices/system/cpu/cpu0/cpuidle/state0/name": "POLL",
            "/sys/devices/system/cpu/cpu0/cpuidle/state0/disable": "0",
            "/sys/devices/system/cpu/cpu0/cpuidle/state1/name": "C1",
            "/sys/devices/system/cpu/cpu0/cpuidle/state1/disable": "0",
            "/sys/devices/system/cpu/smt/active": "1",
        }
    )
    assert settings.get_p_state_management() == "enabled"
    assert settings.get_c_state_management() == "enabled"
    assert settings.get_turbo() == "enabled"
    assert settings.get_smt() == "enabled"


def test_c_states_disabled_when_only_poll_is_usable():
    """Report C-states disabled when every non-POLL state is disabled."""
    settings = _settings(
        {
            "/sys/devices/system/cpu/cpu0/cpuidle/state0/name": "POLL",
            "/sys/devices/system/cpu/cpu0/cpuidle/state0/disable": "0",
            "/sys/devices/system/cpu/cpu0/cpuidle/state1/name": "C1",
            "/sys/devices/system/cpu/cpu0/cpuidle/state1/disable": "1",
        }
    )
    assert settings.get_c_state_management() == "disabled"


def test_c_states_disabled_by_max_cstate_zero():
    """Report C-states disabled when the active idle driver is limited to state 0."""
    settings = _settings({"/sys/devices/system/cpu/cpuidle/current_driver": "intel_idle", "/sys/module/intel_idle/parameters/max_cstate": "0"})
    assert settings.get_c_state_management() == "disabled"


def test_disagreeing_turbo_indicators_are_unknown():
    """Return unknown instead of guessing when indicators disagree."""
    settings = _settings({"/sys/devices/system/cpu/intel_pstate/no_turbo": "1", "/sys/devices/system/cpu/cpufreq/boost": "1"})
    assert settings.get_turbo() == "unknown"


def test_no_evidence_is_unknown():
    """Return unknown for every setting when nothing was readable."""
    settings = _settings({})
    assert settings.to_dictionary()["derived"] == {"p_state_management": "unknown", "c_state_management": "unknown", "turbo": "unknown", "smt": "unknown"}
