from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.web.action.web_action import WebAction
from framework.web.web_action_executor import WebActionExecutor
from framework.web.web_locator import WebLocator
from selenium.webdriver.remote.webelement import WebElement
from unit_tests.framework.web.mock_web_action import MockWebAction
from unit_tests.framework.web.mock_web_condition import MockWebCondition


class MockWebActionExecutor(WebActionExecutor):

    def __init__(self, web_action: WebAction, number_of_expected_fails: int = 0):
        """
        Constructor which will instantiate the driver object.
        Args:
            web_action: Action that we want to perform.

        """

        self.web_action = web_action
        self.progressive_sleep = 0
        self.progressive_sleep_increment = 0
        self.number_of_expected_fails = number_of_expected_fails

    def _find_element(self, locator: WebLocator) -> WebElement:
        """
        Mocks the find_element function because we don't want to have the test depend on a UI.
        Args:
            locator: Element that we are trying to find in the DOM.

        Returns: None
        """

        if self.number_of_expected_fails > 0:
            self.number_of_expected_fails -= 1
            raise Exception("Failed to Find Element")

        return None

    def _find_all_elements(self, locator: WebLocator):
        """
        Mocks the find_elements function because we don't want to have the test depend on a UI.
        Args:
            locator: Element that we are trying to find in the DOM.

        Returns: None
        """

        if self.number_of_expected_fails > 0:
            self.number_of_expected_fails -= 1
            raise Exception("Failed to Find Element")

        return [1, 2, 3]  # Returning multiple values to trigger the looping mechanism.


def test_success_no_condition():
    """
    Tests that the action executor will work well if it is assigned a successful action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction()
    action_executor = MockWebActionExecutor(mock_action)
    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_element_not_found():
    """
    Tests that the action executor will throw an error if the element is not found.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction()
    action_executor = MockWebActionExecutor(mock_action, number_of_expected_fails=1000)

    try:
        action_executor.execute_action()
        assert False, "There should be an exception when trying to execute the action."
    except Exception as e:
        assert e.args[0] == 'Failed to perform Action Mock Action'


def test_element_found_on_second_try():
    """
    Tests that the action executor will pass if the element is found on the second try.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction()
    action_executor = MockWebActionExecutor(mock_action, number_of_expected_fails=1)
    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_stale_element_exception_recovery():
    """
    Tests that the action executor will pass if the action fails on the first try, but works on the retry.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction(number_of_expected_fails=1)  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)
    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_condition_is_met():
    """
    Tests that the action executor will pass if there is a passing condition on the action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_condition = MockWebCondition()
    mock_action = MockWebAction(web_conditions=[mock_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)
    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_condition_is_met_but_action_fails():
    """
    Tests that the action executor will fail if the action fails, even if there is a passing condition on the action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_condition = MockWebCondition()
    mock_action = MockWebAction(number_of_expected_fails=1000, web_conditions=[mock_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)

    try:
        action_executor.execute_action()
        assert False, "There should be an exception when trying to execute the action."
    except Exception as e:
        assert e.args[0] == 'Failed to perform Action Mock Action'


def test_action_fails_once_and_condition_fails_once():
    """
    Tests that the action executor will test the scenario where:
    - Action Fails
    - Action Passes
    - Condition Fails
    - Condition Passes
    The executor should recover and pass the action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_condition = MockWebCondition(number_of_expected_fails=1)
    mock_action = MockWebAction(number_of_expected_fails=1, web_conditions=[mock_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)

    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_action_fails_once_and_condition_fails_twice():
    """
    Tests that the action executor will test the scenario where:
    - Action Fails
    - Action Passes
    - Condition Fails
    - Condition Fails
    - Action Passes
    - Condition Passes
    The executor should recover and pass the action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_condition = MockWebCondition(number_of_expected_fails=2)
    mock_action = MockWebAction(number_of_expected_fails=1, web_conditions=[mock_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)

    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_multiple_conditions_one_pass():
    """
    Tests that the action executor will succeed if we have multiple conditions, but only one is True.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    pass_condition = MockWebCondition()
    fail_condition = MockWebCondition(number_of_expected_fails=1000)
    mock_action = MockWebAction(number_of_expected_fails=1, web_conditions=[fail_condition, pass_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)

    output = action_executor.execute_action()
    assert output == "Success", "Mock Action was executed successfully."


def test_condition_fail():
    """
    Tests that the action executor will fail if the condition is never met.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    fail_condition = MockWebCondition(number_of_expected_fails=1000)
    mock_action = MockWebAction(number_of_expected_fails=1, web_conditions=[fail_condition])  # Simulate a Stale Element Exception
    action_executor = MockWebActionExecutor(mock_action)

    try:
        action_executor.execute_action()
        assert False, "There should be an exception when trying to execute the action."
    except Exception as e:
        assert e.args[0] == 'Failed to perform Action Mock Action'


def test_mass_action_success_no_condition():
    """
    Tests that the action executor will work well if it is assigned a successful mass action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction()
    action_executor = MockWebActionExecutor(mock_action)
    output = action_executor.execute_mass_action()
    assert output == ["Success", "Success", "Success"], "Mock Action was executed successfully."


def test_mass_action_element_not_found():
    """
    Tests that the action executor will throw an error if the element is not found during a mass action.
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(configuration_locations_manager)

    mock_action = MockWebAction()
    action_executor = MockWebActionExecutor(mock_action, number_of_expected_fails=1000)

    try:
        action_executor.execute_mass_action()
        assert False, "There should be an exception when trying to execute the action."
    except Exception as e:
        assert e.args[0] == 'Failed to perform Mass Action Mock Action'
