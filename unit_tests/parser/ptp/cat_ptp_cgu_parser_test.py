from keywords.ptp.cat.objects.ptp_cgu_component_output import PtpCguComponentOutput

output = [
    "Found ZL80032 CGU\n",
    "DPLL Config ver: 1.3.0.1\n",
    "DPLL FW ver: 6021\n",
    "\n",
    "CGU Input status:\n",
    "                |       |    priority    |       |\n",
    "   input (idx) |  state   | EEC (0) | PPS (1) | ESync fail |\n",
    "----------------------------------------------------------------\n",
    "   CVL-SDP22 (0) |  invalid |   255 |    5 |   N/A   |\n",
    "   CVL-SDP20 (1) |  invalid |   255 |    4 |   N/A   |\n",
    " C827_0-RCLKA (2) |  invalid |    8 |    8 |   N/A   |\n",
    " C827_0-RCLKB (3) |  invalid |    9 |    9 |   N/A   |\n",
    "     SMA1 (4) |  invalid |    3 |    3 |   N/A   |\n",
    " SMA2/U.FL2 (5) |  invalid |    2 |    2 |   N/A   |\n",
    "   GNSS-1PPS (6) |  valid |    0 |    0 |   N/A   |\n",
    "\n",
    "EEC DPLL:\n",
    "        Current reference:    GNSS-1PPS\n",
    "        Status:             locked_ho_acq\n",
    "\n",
    "PPS DPLL:\n",
    "        Current reference:    GNSS-1PPS\n",
    "        Status:             locked_ho_acq\n",
    "        Phase offset [ps]:             4094\n",
]


def test_cat_ptp_cgu_output():
    """
    Test the cat ptp cgu parser and output.

    """
    ptp_cgu_output = PtpCguComponentOutput(output)
    ptp_cgu_component = ptp_cgu_output.get_cgu_component()

    assert ptp_cgu_component.get_chip_model() == "ZL80032"
    assert ptp_cgu_component.get_config_version() == "1.3.0.1"
    assert ptp_cgu_component.get_fw_version() == "6021"

    eec_dpll_object = ptp_cgu_component.get_eec_dpll()
    assert eec_dpll_object.current_reference == "GNSS-1PPS"
    assert eec_dpll_object.status == "locked_ho_acq"

    pps_dpll_object = ptp_cgu_component.get_pps_dpll()
    assert pps_dpll_object.get_current_reference() == "GNSS-1PPS"
    assert pps_dpll_object.get_status() == "locked_ho_acq"
    assert pps_dpll_object.get_phase_offset() == 4094

    # validate one of the input objects
    input_object = ptp_cgu_component.get_cgu_input("CVL-SDP22")
    assert input_object.get_idx() == 0
    assert input_object.get_eec() == 255
    assert input_object.get_pps() == 5
    assert input_object.get_state() == "invalid"
    assert input_object.get_esync_fail() == "N/A"
