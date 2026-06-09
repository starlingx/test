"""Horizon Login Page object for browser-based Horizon interactions."""

from config.configuration_manager import ConfigurationManager
from framework.web.condition.web_condition_element_not_visible import WebConditionElementNotVisible
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.login.horizon_login_page_locators import HorizonLoginPageLocators


class HorizonLoginPage(BasePage):
    """Page class that contains operations for the Horizon Login Page."""

    def __init__(self, driver: WebDriverCore) -> None:
        """Initialize HorizonLoginPage.

        Args:
            driver (WebDriverCore): WebDriverCore instance to use for interactions.
        """
        self.locators = HorizonLoginPageLocators()
        self.driver = driver

    def navigate_to_login_page(self) -> None:
        """Navigate to the Horizon login page.

        Uses the Horizon URL from the lab configuration and waits for the
        username input field to be visible.
        """
        url = ConfigurationManager.get_lab_config().get_horizon_url()
        self._navigate_to_url(url)

    def navigate_to_login_page_with_url(self, horizon_url: str) -> None:
        """Navigate to the Horizon login page using a specific URL.

        Args:
            horizon_url (str): The base Horizon URL to navigate to.
        """
        login_url = f"{horizon_url.rstrip('/')}/auth/login/"
        self._navigate_to_url(login_url)

    def _navigate_to_url(self, url: str) -> None:
        """Navigate to the given URL and wait for the login page to load.

        Args:
            url (str): URL to navigate to.
        """
        username_input = self.locators.get_locator_username_input()
        condition = WebConditionElementVisible(username_input)
        self.driver.navigate_to_url(url, [condition])

    def login_as_admin(self) -> None:
        """Login using the Horizon admin credentials from the lab configuration."""
        username = ConfigurationManager.get_lab_config().get_horizon_credentials().get_user_name()
        password = ConfigurationManager.get_lab_config().get_horizon_credentials().get_password()
        self.login(username, password)

    def login(self, username: str, password: str) -> None:
        """Login with the specified credentials.

        Sets username and password, then clicks login with a condition
        that waits for the login button to disappear (page transition).

        Args:
            username (str): Username to enter.
            password (str): Password to enter.
        """
        self.set_username(username)
        self.set_password(password)
        login_button = self.locators.get_locator_login_button()
        condition = WebConditionElementNotVisible(login_button)
        self.driver.click(login_button, [condition])

    def set_username(self, username: str) -> None:
        """Set the username in the username input field.

        Args:
            username (str): Username to enter.
        """
        username_input = self.locators.get_locator_username_input()
        self.driver.set_text(username_input, username)

    def set_password(self, password: str) -> None:
        """Set the password in the password input field.

        Args:
            password (str): Password to enter.
        """
        password_input = self.locators.get_locator_password_input()
        self.driver.set_text(password_input, password)

    def click_login(self) -> None:
        """Click the Login button."""
        login_button = self.locators.get_locator_login_button()
        self.driver.click(login_button)

    def logout(self) -> None:
        """Logout from Horizon by navigating to the logout URL.

        Uses the Horizon URL from the lab configuration to construct
        the logout endpoint.
        """
        base_url = ConfigurationManager.get_lab_config().get_horizon_url().rstrip("/")
        logout_url = f"{base_url}/auth/logout/"
        self.driver.navigate_to_url(logout_url)

    def is_logged_in(self) -> bool:
        """Check if the user is currently logged in.

        Checks for the presence of user menu elements which are only
        visible when authenticated.

        Returns:
            bool: True if user is logged in, False otherwise.
        """
        if self.driver.is_exists(self.locators.get_locator_user_dropdown()):
            return True
        if self.driver.is_exists(self.locators.get_locator_nav_user()):
            return True
        if self.driver.is_exists(self.locators.get_locator_top_bar_user()):
            return True
        return self.driver.is_exists(self.locators.get_locator_logout_link())

    def is_login_error_displayed(self) -> bool:
        """Check if a login error message is displayed.

        Returns:
            bool: True if an error message is visible, False otherwise.
        """
        error_locator = self.locators.get_locator_error_message()
        return self.driver.is_exists(error_locator)

    def is_text_present(self, text: str) -> bool:
        """Check if the given text is present on the current page.

        Args:
            text (str): Text to search for in the page.

        Returns:
            bool: True if text is found on the page.
        """
        return self.driver.is_text_on_page(text)
