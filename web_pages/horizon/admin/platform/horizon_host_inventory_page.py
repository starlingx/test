from typing import List

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.admin.platform.horizon_host_inventory_page_locators import HorizonHostInventoryPageLocators
from web_pages.horizon.admin.platform.objects.horizon_host_object import HorizonHostObject


class HorizonHostInventoryPage(BasePage):
    """
    Page class that contains operations for the Admin -> Platform -> Host Inventory Page.
    """

    def __init__(self, driver: WebDriverCore):
        self.locators = HorizonHostInventoryPageLocators()
        self.driver = driver

    def navigate_to_host_inventory_page(self) -> None:
        """
        This function will navigate to the Admin -> Platform -> Host Inventory Page.
        Returns:

        """

        url = ConfigurationManager.get_lab_config().get_horizon_url() + "/admin"
        self.driver.navigate_to_url(url)

    def get_controller_hosts_table_headers(self) -> List[str]:
        """
        This function will return the list of Header Labels associated with all the headers
        of the Controller Hosts table.
        Returns: List[str]

        """
        all_headers_locator = self.locators.get_locator_controller_table_displayed_headers()
        all_headers = self.driver.get_all_elements_text(all_headers_locator)
        get_logger().log_info(f"Controller Hosts table headers: {all_headers}")
        return all_headers

    def get_controller_host_information(self, host_name: str) -> HorizonHostObject:
        """
        This function will return the information about the host as seen from the Host Inventory Page
        Returns: List[str]

        """
        row_info_locator = self.locators.get_locator_controller_table_row_information(host_name)
        row_info_list = self.driver.get_all_elements_text(row_info_locator)
        get_logger().log_info(f"Controller Hosts row information: {row_info_list}")

        horizon_host_object = HorizonHostObject(row_info_list)
        return horizon_host_object
