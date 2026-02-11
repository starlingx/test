from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class HorizonDCSubcloudPageLocators:
    """Locators for Horizon DC Subcloud page."""

    def get_locator_subcloud_expand_button(self, subcloud_name: str) -> WebLocator:
        """Get locator for subcloud expand button.

        Args:
            subcloud_name (str): Name of the subcloud.

        Returns:
            WebLocator: Locator for subcloud expand button.
        """
        return WebLocator("tbody tr:first-child td:first-child span", By.CSS_SELECTOR)

    def get_locator_kube_rootca_sync_status(self, subcloud_name: str) -> WebLocator:
        """Get locator for kube-rootca sync status.

        Args:
            subcloud_name (str): Name of the subcloud.

        Returns:
            WebLocator: Locator for kube-rootca sync status element.
        """
        return WebLocator("//dt[normalize-space()='kube-rootca']/following-sibling::dd[1]", By.XPATH)
