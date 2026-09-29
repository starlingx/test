"""Keyword for logging into the Horizon web UI via browser-based OIDC (DEX) SSO.

Drives a headless Selenium browser through the Horizon WebSSO flow: navigate to
the Horizon login page, select the "OpenID Connect" authentication method, sign
in, complete the DEX login (connector selection + DEX-native form for LDAP/WAD,
plus the DEX "Grant Access" approval page), and confirm the Horizon dashboard
loads.

Reuses DexLoginPage (connector selection, DEX-native login, Grant Access) and
HorizonLoginPage (navigation, dashboard/logged-in check) so the DEX handling is
shared with the STX-CLI OIDC login flow.
"""

import time

from selenium.webdriver.common.by import By

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.web.webdriver_core import WebDriverCore
from keywords.base_keyword import BaseKeyword
from web_pages.dex.login.dex_login_page import DexLoginPage
from web_pages.horizon.login.horizon_login_page import HorizonLoginPage


class HorizonOidcLoginKeywords(BaseKeyword):
    """Log into Horizon via browser-based OIDC (DEX) SSO for LDAP/WAD connectors."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the controller
                (kept for parity with other OIDC keywords; the login itself runs
                entirely in the browser).
        """
        self.ssh_connection = ssh_connection

    def login_to_horizon_via_oidc(self, horizon_url: str, username: str, password: str, connector: str = "") -> bool:
        """Log into Horizon through the browser OIDC (DEX) flow and confirm the dashboard loads.

        Opens a headless browser, navigates to Horizon, selects the OpenID Connect
        auth method and signs in, completes the DEX login (connector selection +
        DEX-native form + Grant Access approval), then verifies the Horizon
        dashboard is loaded.

        Args:
            horizon_url (str): The Horizon base URL (e.g. https://[oam_ip]:8443).
            username (str): OIDC/LDAP login username.
            password (str): OIDC/LDAP login password.
            connector (str): DEX connector to select (e.g. 'ldap-1', 'wad-1').
                Empty selects the first connector or skips selection if only one.

        Returns:
            bool: True if the Horizon dashboard loaded after OIDC login.
        """
        driver = WebDriverCore()
        try:
            horizon_login_page = HorizonLoginPage(driver)
            dex_login_page = DexLoginPage(driver)

            get_logger().log_info(f"Navigating to Horizon login page: {horizon_url}")
            horizon_login_page.navigate_to_login_page_with_url(horizon_url)
            time.sleep(2)

            get_logger().log_info("Selecting OpenID Connect auth method and signing in")
            self._select_oidc_and_sign_in(driver, horizon_login_page)

            get_logger().log_info(f"Completing DEX login (connector='{connector}')")
            dex_login_page.select_connector_if_present(connector)
            dex_login_page.submit_native_login(username, password)
            dex_login_page.grant_access_if_present()

            is_loaded = self._wait_for_horizon_dashboard(driver, horizon_login_page, horizon_url)
            get_logger().log_info(f"Horizon dashboard loaded after OIDC login: {is_loaded} (url={driver.get_current_url()})")
            if not is_loaded:
                self._log_landing_page_diagnostics(driver)
            return is_loaded
        finally:
            driver.quit()

    def _log_landing_page_diagnostics(self, driver: WebDriverCore) -> None:
        """Log the final URL, title, and page-source snippet to diagnose a failed login.

        Distinguishes a federation authorization failure ("not authorized for any
        projects or domains") from a plain login page (session/cookie not carried).

        Args:
            driver (WebDriverCore): The web driver instance.
        """
        raw = driver.driver
        page_source = raw.page_source or ""
        markers = [
            "not authorized for any projects or domains",
            "Login failed",
            "logout_reason",
            "id_username",
            "Sign Out",
            "dashboard",
        ]
        found = [marker for marker in markers if marker.lower() in page_source.lower()]
        get_logger().log_info(f"Landing page diagnostics - title='{raw.title}' url='{driver.get_current_url()}' markers={found}")
        get_logger().log_info(f"Landing page source (first 800 chars): {page_source[:800]}")

    def _wait_for_horizon_dashboard(self, driver: WebDriverCore, horizon_login_page: HorizonLoginPage, horizon_url: str) -> bool:
        """Wait for the Keystone federation WebSSO redirect to complete and Horizon to load.

        After Grant Access, the browser is on the Keystone federation callback
        (:5000/.../websso), which posts back to Horizon (:8443/auth/websso/) and
        then redirects to the dashboard. Poll until the logged-in indicator is
        present rather than checking once mid-redirect.

        Args:
            driver (WebDriverCore): The web driver instance.
            horizon_login_page (HorizonLoginPage): The Horizon login page object.
            horizon_url (str): The Horizon base URL to nudge to if the federation
                callback stalls.

        Returns:
            bool: True if the Horizon dashboard (logged-in indicator) loaded in time.
        """
        deadline = time.time() + 60
        while time.time() < deadline:
            if horizon_login_page.is_logged_in():
                return True
            # If still parked on the Keystone federation callback (:5000/...websso),
            # nudge the browser to the Horizon dashboard so the session cookie set by
            # the federation post is used to render the authenticated UI.
            current_url = driver.get_current_url()
            if ":5000/" in current_url and "/websso" in current_url:
                get_logger().log_info("Still on federation callback; navigating to Horizon dashboard to complete SSO")
                driver.navigate_to_url(horizon_url)
            time.sleep(3)
        return horizon_login_page.is_logged_in()

    def _select_oidc_and_sign_in(self, driver: WebDriverCore, horizon_login_page: HorizonLoginPage) -> None:
        """Select the OpenID Connect auth method (if a selector is shown) and click Sign In.

        Mirrors the manual flow: scan any auth-method <select> for an OIDC/OpenID/
        DEX/SSO option and select it via the Select control; if there is no such
        dropdown, fall back to a WebSSO link or simply click the Sign In button so
        Horizon redirects to DEX.

        Args:
            driver (WebDriverCore): The web driver instance.
            horizon_login_page (HorizonLoginPage): The Horizon login page object.
        """
        raw = driver.driver
        time.sleep(2)
        selected = self._select_oidc_option(raw)

        if not selected:
            get_logger().log_info("No OIDC auth-method option found; trying WebSSO link / default sign in")
            websso_links = raw.find_elements(By.XPATH, "//a[contains(@href, 'websso') or contains(@href, 'sso')]")
            if websso_links:
                get_logger().log_info("Clicking WebSSO link")
                websso_links[0].click()
                time.sleep(3)
                return

        # Click the Sign In / login button to submit the selected auth method.
        login_button = horizon_login_page.locators.get_locator_login_button()
        if driver.is_exists(login_button):
            driver.click(login_button)
        else:
            submit_buttons = raw.find_elements(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button.btn-primary")
            for button in submit_buttons:
                if button.is_displayed():
                    button.click()
                    break
        time.sleep(3)

    def _select_oidc_option(self, raw_driver: object) -> bool:
        """Scan auth-method <select> elements and select the OIDC/OpenID/DEX/SSO option.

        Args:
            raw_driver (object): The underlying Selenium WebDriver.

        Returns:
            bool: True if an OIDC option was found and selected, False otherwise.
        """
        for select_element in raw_driver.find_elements(By.TAG_NAME, "select"):
            for option in select_element.find_elements(By.TAG_NAME, "option"):
                option_text = (option.text or "").lower()
                option_value = (option.get_attribute("value") or "").lower()
                if any(token in option_text or token in option_value for token in ["oidc", "openid", "dex", "sso"]):
                    get_logger().log_info(f"Selecting auth-method option: {option.text} (value={option_value})")
                    option.click()
                    time.sleep(1)
                    return True
        return False
