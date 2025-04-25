from keywords.ptp.cat.objects.clock_conf_output import ClockConfOutput

# fmt off
clock_conf_output = ["ifname [enp138s0f0]\n", "base_port [enp138s0f0]\n", "sma1 input\n", "ifname [enp81s0f0]\n", "base_port [enp81s0f0]\n", "sma1 output\n", "sysadmin@controller-0:~$ \n"]


def test_clock_conf_output():
    """
    Test the cat clock conf parser and output.

    """
    clock_config_output = ClockConfOutput(clock_conf_output)
    clock_config_objects = clock_config_output.get_clock_conf_objects()

    assert len(clock_config_objects), 2

    clock_config_object = clock_config_objects[0]
    assert clock_config_object.get_ifname() == "enp138s0f0"
    assert clock_config_object.get_base_port() == "enp138s0f0"
    assert clock_config_object.get_sma_name() == "sma1"
    assert clock_config_object.get_sma_mode() == "input"

    clock_config_object = clock_config_objects[1]
    assert clock_config_object.get_ifname() == "enp81s0f0"
    assert clock_config_object.get_base_port() == "enp81s0f0"
    assert clock_config_object.get_sma_name() == "sma1"
    assert clock_config_object.get_sma_mode() == "output"
