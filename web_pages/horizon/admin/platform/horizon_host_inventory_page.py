"""Page object for the Horizon Admin -> Platform -> Host Inventory page."""

from typing import List

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.admin.platform.horizon_host_inventory_page_locators import HorizonHostInventoryPageLocators
from web_pages.horizon.admin.platform.objects.horizon_host_object import HorizonHostObject


class HorizonHostInventoryPage(BasePage):
    """Page class that contains operations for the Admin -> Platform -> Host Inventory page."""

    def __init__(self, driver: WebDriverCore):
        self.locators = HorizonHostInventoryPageLocators()
        self.driver = driver

    def navigate_to_host_inventory_page(self) -> None:
        """Navigate to the Admin -> Platform -> Host Inventory page."""
        url = ConfigurationManager.get_lab_config().get_horizon_url() + "/admin"
        self.driver.navigate_to_url(url)

    def get_controller_hosts_table_headers(self) -> List[str]:
        """Return the header labels of the Controller Hosts table.

        Returns:
            List[str]: The list of header labels displayed in the Controller Hosts table.
        """
        all_headers_locator = self.locators.get_locator_controller_table_displayed_headers()
        all_headers = self.driver.get_all_elements_text(all_headers_locator)
        get_logger().log_info(f"Controller Hosts table headers: {all_headers}")
        return all_headers

    def get_controller_host_information(self, host_name: str) -> HorizonHostObject:
        """Return the information about a host as seen from the Host Inventory page.

        Args:
            host_name (str): Name of the controller host (e.g. 'controller-0').

        Returns:
            HorizonHostObject: Parsed row information for the host.
        """
        row_info_locator = self.locators.get_locator_controller_table_row_information(host_name)
        row_info_list = self.driver.get_all_elements_text(row_info_locator)
        get_logger().log_info(f"Controller Hosts row information: {row_info_list}")

        horizon_host_object = HorizonHostObject(row_info_list)
        return horizon_host_object

    def get_controller_edit_host_button_text(self, host_name: str) -> str:
        """Return the text of the 'Edit Host' button for the specified controller host.

        Args:
            host_name (str): Name of the controller host (e.g. 'controller-0').

        Returns:
            str: The text of the Edit Host button.
        """
        edit_button_locator = self.locators.get_locator_controller_table_edit_host_button(host_name)
        edit_button_text = self.driver.get_text(edit_button_locator)
        return edit_button_text

    def is_edit_host_button_present(self, host_name: str) -> bool:
        """Check whether the 'Edit Host' action button is present for a controller host.

        Uses a presence check (is_exists) rather than reading the button text, so it
        returns cleanly when the button is absent - for example for a reader-role
        user who can view the host inventory but is not authorized to edit hosts.

        Args:
            host_name (str): Name of the controller host (e.g. 'controller-0').

        Returns:
            bool: True if the Edit Host button is present, False otherwise.
        """
        edit_button_locator = self.locators.get_locator_controller_table_edit_host_button(host_name)
        return self.driver.is_exists(edit_button_locator)
