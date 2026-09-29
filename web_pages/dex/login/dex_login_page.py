"""Page object for the DEX login UI used by STX OIDC browser-based authentication."""

import time

from selenium.webdriver.common.by import By

from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.dex.login.dex_login_page_locators import DexLoginPageLocators


class DexLoginPage(BasePage):
    """Page class for the DEX connector-selection page and DEX-native login form.

    Handles selecting a DEX connector (Local LDAP / WAD / Keycloak) when the
    connector-selection page is presented, and submitting the DEX-native login
    form used by the Local LDAP and WAD connectors. The Keycloak connector
    redirects to Keycloak, whose login (and MFA) is handled by KeycloakLoginPage.
    """

    def __init__(self, driver: WebDriverCore):
        """Constructor.

        Args:
            driver (WebDriverCore): The web driver instance.
        """
        self.driver = driver
        self.locators = DexLoginPageLocators()

    def navigate_to_login_url(self, url: str) -> None:
        """Navigate to the oidc-login listener URL, retrying until DEX is reachable.

        The listener (started by 'source local_starlingxrc oidc') needs a few
        seconds to come up and redirect to DEX. navigate_to_url reloads until a
        condition is met, so we wait for either the connector-selection links or
        the DEX-native login (#login) field to appear.

        Args:
            url (str): The oidc-login listener URL (e.g. http://[oam_ip]:8000/).
        """
        conditions = [
            WebConditionElementVisible(self.locators.get_locator_username_input()),
            WebConditionElementVisible(self.locators.get_locator_connector_links()),
        ]
        self.driver.navigate_to_url(url, conditions)

    def select_connector_if_present(self, connector: str = "") -> None:
        """Select a DEX connector on the connector-selection page, if that page is shown.

        DEX shows a connector-selection page only when multiple connectors are
        configured. When a single connector exists, DEX skips straight to the
        login form and this method is a no-op.

        Args:
            connector (str): Connector id/name to select (e.g. 'ldap-1', 'wad-1',
                'keycloak'). Empty selects the first available connector.
        """
        time.sleep(2)
        connector_links = self.driver.driver.find_elements(By.CSS_SELECTOR, self.locators.get_locator_connector_links().locator)

        # If a login field is already present we are past connector selection.
        has_login_field = bool(self.driver.driver.find_elements(By.CSS_SELECTOR, "#login, #username"))
        if not connector_links or has_login_field:
            get_logger().log_info("No connector-selection page shown; proceeding to login form")
            return

        get_logger().log_info(f"Connector-selection page detected ({len(connector_links)} connectors)")
        selected = None
        if connector:
            for link in connector_links:
                href = (link.get_attribute("href") or "").lower()
                text = (link.text or "").lower()
                if connector.lower() in href or connector.lower() in text:
                    selected = link
                    break
        if not selected:
            selected = connector_links[0]
        get_logger().log_info(f"Selecting connector: {selected.text or selected.get_attribute('href')}")
        selected.click()
        time.sleep(3)

    def submit_native_login(self, username: str, password: str) -> None:
        """Fill and submit the DEX-native login form (Local LDAP / WAD connectors).

        Waits for the DEX username field to appear first, since the Horizon WebSSO
        redirect chain (Horizon -> Keystone -> DEX) can take a few seconds to land
        on the DEX login form before the fields are present.

        Args:
            username (str): Login username.
            password (str): Login password.
        """
        self._wait_for_login_form()
        self.driver.set_text(self.locators.get_locator_username_input(), username)
        self.driver.set_text(self.locators.get_locator_password_input(), password)
        submit_locator = self.locators.get_locator_sign_in_button()
        if self.driver.is_exists(submit_locator):
            self.driver.click(submit_locator)
        else:
            self.driver.click(self.locators.get_locator_generic_submit_button())
        get_logger().log_info(f"DEX-native login submitted - current URL: {self.driver.get_current_url()}")

    def _wait_for_login_form(self, timeout: int = 60, poll_interval: int = 2) -> None:
        """Wait until the DEX-native username field is present before filling the form.

        Args:
            timeout (int): Maximum seconds to wait for the login field. Defaults to 60.
            poll_interval (int): Seconds between checks. Defaults to 2.
        """
        deadline = time.time() + timeout
        username_input = self.locators.get_locator_username_input()
        while time.time() < deadline:
            if self.driver.is_exists(username_input):
                get_logger().log_info(f"DEX login form ready - current URL: {self.driver.get_current_url()}")
                return
            time.sleep(poll_interval)
        get_logger().log_info(f"DEX login form not detected within {timeout}s - current URL: {self.driver.get_current_url()}")

    def grant_access_if_present(self) -> None:
        """Click "Grant Access" on the DEX approval page, if that page is shown.

        After a successful login DEX may present an approval/consent page (when
        the client is not pre-approved) that the user must accept before being
        redirected back to the application. If no approval page is shown this is
        a no-op.
        """
        time.sleep(3)
        if "approval" not in self.driver.get_current_url().lower():
            get_logger().log_info("No DEX approval page shown; proceeding")
            return
        get_logger().log_info("DEX approval page detected; granting access")
        self.driver.click(self.locators.get_locator_grant_access_button())
        time.sleep(3)
        get_logger().log_info(f"DEX approval granted - current URL: {self.driver.get_current_url()}")
