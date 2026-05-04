import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from config.configuration_manager import ConfigurationManager
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.web_locator import WebLocator
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.admin.dc.horizon_dc_orchestration_page_locators import HorizonDCOrchestrationPageLocators


class HorizonDCOrchestrationPage(BasePage):
    """Page class for Horizon DC Orchestration operations."""

    def __init__(self, driver: WebDriverCore):
        self.locators = HorizonDCOrchestrationPageLocators()
        self.driver = driver

    def navigate_to_dc_orchestration_page(self) -> None:
        """Navigate to Distributed Cloud Admin Orchestration page."""
        url = ConfigurationManager.get_lab_config().get_horizon_url() + "/dc_admin/dc_orchestration/"
        condition = WebConditionElementVisible(self.locators.get_locator_create_strategy_button())
        self.driver.navigate_to_url(url, [condition])

    def _select_by_value(self, locator: WebLocator, value: str) -> None:
        """Select an option by value from a dropdown.

        Args:
            locator (WebLocator): WebLocator for the select element.
            value (str): Value attribute of the option to select.
        """
        element = self.driver.driver.find_element(locator.by, locator.locator)
        Select(element).select_by_value(value)

    def _check_for_page_errors(self) -> None:
        """Check for error messages on the page and raise if found."""
        time.sleep(2)
        errors = self.driver.driver.find_elements(By.CSS_SELECTOR, ".alert-danger")
        for error in errors:
            error_text = error.text.strip()
            if error_text:
                raise Exception(f"Horizon error: {error_text}")

    def get_strategy_detail_text(self) -> str:
        """Get the strategy detail text.

        Returns:
            str: Strategy detail text.
        """
        return self.driver.get_text(self.locators.get_locator_strategy_detail())

    def click_create_strategy(self) -> None:
        """Click the Create Strategy button to open the modal."""
        self.driver.click(self.locators.get_locator_create_strategy_button())
        time.sleep(3)

    def click_apply_strategy(self) -> None:
        """Click the Apply Strategy button."""
        self.driver.click(self.locators.get_locator_apply_strategy_button())
        time.sleep(3)

    def click_abort_strategy(self) -> None:
        """Click the Abort Strategy button."""
        self.driver.click(self.locators.get_locator_abort_strategy_button())

    def click_delete_strategy(self) -> None:
        """Click the Delete Strategy button."""
        self.driver.click(self.locators.get_locator_delete_strategy_button())

    def click_modal_submit(self) -> None:
        """Click the submit button in the modal dialog."""
        self.driver.click(self.locators.get_locator_modal_submit_button())
        time.sleep(5)

    def create_kubernetes_strategy(
        self,
        to_version: str,
        subcloud: str = None,
        subcloud_group: str = None,
        stop_on_failure: bool = True,
        subcloud_apply_type: str = "parallel",
        max_parallel_subclouds: str = "20",
    ) -> None:
        """Create a Kubernetes orchestration strategy.

        Args:
            to_version (str): Kubernetes version to upgrade to (e.g. 'v1.30.6').
            subcloud (str): Subcloud name. If set, selects specific subcloud. If None, keeps 'All subclouds' default.
            subcloud_group (str): Subcloud group name. If set, switches Apply to 'Subcloud Group'.
            stop_on_failure (bool): Whether to stop on failure.
            subcloud_apply_type (str): 'parallel' or 'serial'.
            max_parallel_subclouds (str): Max parallel subclouds.
        """
        self.click_create_strategy()

        # Select strategy type
        self._select_by_value(self.locators.get_locator_strategy_type_select(), "kubernetes")
        time.sleep(2)

        # Select Kubernetes version
        self._select_by_value(self.locators.get_locator_to_version_select(), to_version)

        # Apply target: default is Subcloud with 'All subclouds' selected
        if subcloud_group:
            self._select_by_value(self.locators.get_locator_apply_to_select(), "subcloud_group")
            time.sleep(1)
            self._select_by_value(self.locators.get_locator_subcloud_group_select(), subcloud_group)
        elif subcloud:
            # Subcloud is already the default Apply to, just pick the specific subcloud
            time.sleep(1)
            self._select_by_value(self.locators.get_locator_subcloud_select(), subcloud)

        # Stop on failure
        checkbox = self.locators.get_locator_stop_on_failure_checkbox()
        is_checked = self.driver.get_attribute(checkbox, "checked")
        if stop_on_failure != bool(is_checked):
            self.driver.click(checkbox)

        # Apply type and max parallel (visible when applying to all subclouds)
        if not subcloud and not subcloud_group:
            self._select_by_value(self.locators.get_locator_subcloud_apply_type_select(), subcloud_apply_type)
            self.driver.set_text(self.locators.get_locator_max_parallel_subclouds_input(), max_parallel_subclouds)

        self.click_modal_submit()
        self._check_for_page_errors()

    def delete_strategy(self) -> None:
        """Delete the current strategy."""
        self.click_delete_strategy()
        time.sleep(2)
        self.driver.click(self.locators.get_locator_modal_delete_confirm_button())
        time.sleep(5)

    def apply_strategy(self) -> None:
        """Apply the current strategy."""
        self.click_apply_strategy()
        self.click_modal_submit()

    def get_steps_table_rows_text(self) -> list[str]:
        """Get text content of all rows in the steps table.

        Returns:
            list[str]: Text of each row.
        """
        return self.driver.get_all_elements_text(self.locators.get_locator_steps_table_rows())
