from framework.logging import log_banners


def test_get_banner():
    """
    Tests that surround_with_asterisks works for a short string.
    """

    test_string_0 = "Starting a new Test!"
    test_string_1 = "Test Suite: critical_test_suite"
    test_string_2 = "Test Case: verify_important_test_scenario"
    banner = log_banners.get_banner([test_string_0, test_string_1, test_string_2])

    assert len(banner) == 5
    assert banner[0] == "*****************************************************"
    assert banner[1] == "***** Starting a new Test!                      *****"
    assert banner[2] == "***** Test Suite: critical_test_suite           *****"
    assert banner[3] == "***** Test Case: verify_important_test_scenario *****"
    assert banner[4] == "*****************************************************"
