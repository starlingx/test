from framework.web.web_locator import WebLocator
from selenium.webdriver.common.by import By


class HorizonHostInventoryPageLocators:
    """
    Page Elements class that contains elements for the Admin -> Platform -> Host Inventory Page.
    """

    def get_locator_controller_table_displayed_headers(self) -> WebLocator:
        """
        Locator for the list of visible table headers of the Controller Hosts table.

        Returns: WebLocator
        """
        return WebLocator("#hostscontroller th:not(.hidden)", By.CSS_SELECTOR)

    def get_locator_controller_table_row_information(self, host_name: str):
        """
        Locator which allows us to find all the row information associated with the host_name passed in.
        Args:
            host_name: Name of the host for which we want to find information.

        Returns: A Locator

        """
        return WebLocator(f"tr[id*='hostscontroller'][ data-display='{host_name}'] td:not(.hidden)", By.CSS_SELECTOR)

    def get_locator_worker_table_displayed_headers(self) -> WebLocator:
        """
        Locator for the list of visible table headers of the Worker Hosts table.

        Returns: WebLocator
        """
        return WebLocator("#hostsworker th:not(.hidden)", By.CSS_SELECTOR)
