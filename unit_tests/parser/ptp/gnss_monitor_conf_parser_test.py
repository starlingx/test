"""Unit tests for GnssMonitorConfParser."""

from keywords.ptp.cat.gnss_monitor_conf_parser import GnssMonitorConfParser


def test_parse_gnss_monitor_config():
    """Test parsing of GNSS monitor configuration output."""
    sample_output = ["[global]\n", "##\n", "## Default Data Set\n", "##\n", "devices /dev/ttyACM0 /dev/gnssx\n", "satellite_count 8\n", "signal_quality_db 30\n"]

    parser = GnssMonitorConfParser(sample_output)
    values_dict = parser.get_output_values_dict()

    assert values_dict["devices"] == "/dev/ttyACM0 /dev/gnssx"
    assert values_dict["satellite_count"] == "8"
    assert values_dict["signal_quality_db"] == "30"


def test_parse_minimal_config():
    """Test parsing minimal configuration."""
    minimal_output = ["[global]\n", "devices /dev/ttyACM0\n", "satellite_count 15\n", "signal_quality_db 40\n"]

    parser = GnssMonitorConfParser(minimal_output)
    values_dict = parser.get_output_values_dict()

    assert values_dict["devices"] == "/dev/ttyACM0"
    assert values_dict["satellite_count"] == "15"
    assert values_dict["signal_quality_db"] == "40"


def test_parse_config_with_prompts():
    """Test parsing configuration with command prompts and passwords."""
    output_with_prompts = ["~$ cat /etc/linuxptp/ptpinstance/gnss-monitor-ptp.conf\n", "[global]\n", "Password: \n", "devices /dev/ttyACM0\n", "satellite_count 10\n", "signal_quality_db 25\n"]

    parser = GnssMonitorConfParser(output_with_prompts)
    values_dict = parser.get_output_values_dict()

    # Should ignore prompts and passwords
    assert "~$" not in str(values_dict)
    assert "Password:" not in str(values_dict)

    assert values_dict["devices"] == "/dev/ttyACM0"
    assert values_dict["satellite_count"] == "10"
    assert values_dict["signal_quality_db"] == "25"


def test_parse_empty_config():
    """Test parsing empty configuration."""
    empty_output = ["[global]\n", "##\n", "## Default Data Set\n", "##\n"]

    parser = GnssMonitorConfParser(empty_output)
    values_dict = parser.get_output_values_dict()

    assert len(values_dict) == 0


def test_parse_config_with_spaces_in_values():
    """Test parsing configuration with spaces in device values."""
    output_with_spaces = ["[global]\n", "devices /dev/ttyACM0 /dev/gnssx /dev/ttyUSB0\n", "satellite_count 12\n", "signal_quality_db 35\n"]

    parser = GnssMonitorConfParser(output_with_spaces)
    values_dict = parser.get_output_values_dict()

    assert values_dict["devices"] == "/dev/ttyACM0 /dev/gnssx /dev/ttyUSB0"
    assert values_dict["satellite_count"] == "12"
    assert values_dict["signal_quality_db"] == "35"
