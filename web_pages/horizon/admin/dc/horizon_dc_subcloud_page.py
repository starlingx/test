import time

from config.configuration_manager import ConfigurationManager
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.admin.dc.horizon_dc_subcloud_page_locators import HorizonDCSubcloudPageLocators


class HorizonDCSubcloudPage(BasePage):
    """Page class for Horizon DC Subcloud operations."""

    def __init__(self, driver: WebDriverCore):
        """Initialize Horizon DC Subcloud page.

        Args:
            driver (WebDriverCore): Web driver instance.
        """
        self.locators = HorizonDCSubcloudPageLocators()
        self.driver = driver

    def navigate_to_dc_subcloud_page(self) -> None:
        """Navigate to Distributed Cloud Admin Cloud Overview Subclouds page."""
        url = ConfigurationManager.get_lab_config().get_horizon_url() + "/dc_admin"
        self.driver.navigate_to_url(url)
        time.sleep(10)

    def expand_subcloud(self, subcloud_name: str) -> None:
        """Expand subcloud details by clicking expand button.

        Args:
            subcloud_name (str): Name of the subcloud to expand.
        """
        expand_button = self.locators.get_locator_subcloud_expand_button(subcloud_name)
        if self.driver.is_exists(expand_button):
            self.driver.click(expand_button)
            time.sleep(15)

    def get_kube_rootca_sync_status(self, subcloud_name: str) -> str:
        """Get kube-rootca sync status for subcloud.

        Args:
            subcloud_name (str): Name of the subcloud.

        Returns:
            str: Kube-rootca sync status value.
        """
        status_locator = self.locators.get_locator_kube_rootca_sync_status(subcloud_name)
        element = self.driver.driver.find_element(status_locator.by, status_locator.locator)

        status_text = element.get_attribute("textContent")
        return status_text.strip() if status_text else ""
