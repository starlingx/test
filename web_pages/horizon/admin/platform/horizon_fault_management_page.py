"""Horizon Fault Management (Active Alarms) Page object for browser-based interactions."""

import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.admin.platform.horizon_fault_management_page_locators import HorizonFaultManagementPageLocators


class HorizonFaultManagementPage(BasePage):
    """Page class that contains operations for the Admin -> Fault Management -> Active Alarms Page."""

    def __init__(self, driver: WebDriverCore) -> None:
        """Initialize HorizonFaultManagementPage.

        Args:
            driver (WebDriverCore): WebDriverCore instance to use for interactions.
        """
        self.locators = HorizonFaultManagementPageLocators()
        self.driver = driver

    def navigate_to_active_alarms_page(self) -> None:
        """Navigate to the Admin -> Fault Management -> Active Alarms page.

        Uses the Horizon URL from lab configuration and navigates to
        /admin/active_alarms/. Waits for the Angular dynamic table to
        be visible confirming page load.
        """
        base_url = ConfigurationManager.get_lab_config().get_horizon_url().rstrip("/")
        url = f"{base_url}/admin/active_alarms/"
        table_locator = self.locators.get_locator_alarms_table()
        condition = WebConditionElementVisible(table_locator)
        self.driver.navigate_to_url(url, [condition])
        self._wait_for_table_rows_loaded()

    def is_alarm_present(self, alarm_id: str) -> bool:
        """Check if an alarm with the given ID is present in the active alarms table.

        Args:
            alarm_id (str): The alarm ID to check for (e.g., '100.103').

        Returns:
            bool: True if the alarm is present, False otherwise.
        """
        alarm_locator = self.locators.get_locator_alarm_id_cell(alarm_id)
        return self.driver.is_exists(alarm_locator)

    def wait_for_alarm_to_appear(self, alarm_id: str, timeout: int = 600, poll_interval: int = 10) -> None:
        """Wait for an alarm with the given ID to appear in the active alarms table.

        Refreshes the page periodically until the alarm is found or the timeout is reached.

        Args:
            alarm_id (str): The alarm ID to wait for (e.g., '100.103').
            timeout (int): Maximum time to wait in seconds. Defaults to 600.
            poll_interval (int): Time between page refreshes in seconds. Defaults to 10.

        Raises:
            TimeoutError: If the alarm does not appear within the timeout.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            self._wait_for_table_rows_loaded()
            if self.is_alarm_present(alarm_id):
                get_logger().log_info(f"Alarm {alarm_id} found in active alarms table")
                return
            get_logger().log_info(f"Alarm {alarm_id} not found yet, refreshing page...")
            time.sleep(poll_interval)
            self.driver.refresh()

        raise TimeoutError(f"Alarm {alarm_id} did not appear within {timeout} seconds")

    def wait_for_alarm_to_clear(self, alarm_id: str, timeout: int = 600, poll_interval: int = 10) -> None:
        """Wait for an alarm with the given ID to disappear from the active alarms table.

        Refreshes the page periodically until the alarm is gone or the timeout is reached.

        Args:
            alarm_id (str): The alarm ID to wait for clearance (e.g., '100.103').
            timeout (int): Maximum time to wait in seconds. Defaults to 600.
            poll_interval (int): Time between page refreshes in seconds. Defaults to 10.

        Raises:
            TimeoutError: If the alarm is still present after the timeout.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            self._wait_for_table_rows_loaded()
            if not self.is_alarm_present(alarm_id):
                get_logger().log_info(f"Alarm {alarm_id} cleared from active alarms table")
                return
            get_logger().log_info(f"Alarm {alarm_id} still present, refreshing page...")
            time.sleep(poll_interval)
            self.driver.refresh()

        raise TimeoutError(f"Alarm {alarm_id} was not cleared within {timeout} seconds")

    def _wait_for_table_rows_loaded(self) -> None:
        """Wait for the Angular dynamic alarms table content to be fully rendered.

        Waits up to 30 seconds for the table footer with item count to appear,
        indicating Angular has finished rendering the table content.
        """
        footer_locator = self.locators.get_locator_table_footer()
        timeout = time.time() + 30
        while time.time() < timeout:
            if self.driver.is_exists(footer_locator):
                return
            time.sleep(1)
