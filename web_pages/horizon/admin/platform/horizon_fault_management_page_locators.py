"""Horizon Fault Management (Active Alarms) Page locators."""

from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class HorizonFaultManagementPageLocators:
    """Page Elements class that contains locators for the Admin -> Fault Management -> Active Alarms Page."""

    def get_locator_alarms_table(self) -> WebLocator:
        """Locator for the alarms table rendered by Angular hz-dynamic-table.

        Returns:
            WebLocator: CSS selector for the alarms table.
        """
        return WebLocator(
            "hz-dynamic-table table.table",
            By.CSS_SELECTOR,
        )

    def get_locator_table_footer(self) -> WebLocator:
        """Locator for the table footer showing item count (indicates Angular rendering is complete).

        Returns:
            WebLocator: CSS selector for the table footer element.
        """
        return WebLocator(
            "tfoot[hz-table-footer]",
            By.CSS_SELECTOR,
        )

    def get_locator_alarm_id_cell(self, alarm_id: str) -> WebLocator:
        """Locator for an hz-field element containing the specified alarm ID text.

        Uses normalize-space() to handle any leading/trailing whitespace in the element.

        Args:
            alarm_id (str): The alarm ID to search for (e.g., '750.002').

        Returns:
            WebLocator: XPath locator for the hz-field element containing the alarm ID.
        """
        return WebLocator(
            f"//hz-dynamic-table//table//tbody//tr//hz-field[normalize-space(text())='{alarm_id}']",
            By.XPATH,
        )
