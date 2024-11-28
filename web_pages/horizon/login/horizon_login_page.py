from config.configuration_manager import ConfigurationManager
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.horizon.login.horizon_login_page_locators import HorizonLoginPageLocators


class HorizonLoginPage(BasePage):
    """
    Page class that contains operations for the Login Page.
    """

    def __init__(self, driver: WebDriverCore):
        self.locators = HorizonLoginPageLocators()
        self.driver = driver

    def navigate_to_login_page(self):
        """
        This function will navigate to the Login Page.
        Returns:

        """

        url = ConfigurationManager.get_lab_config().get_horizon_url()
        username_input = self.locators.get_locator_username_input()
        condition = WebConditionElementVisible(username_input)
        self.driver.navigate_to_url(url, [condition])

    def login_as_admin(self) -> None:
        """
        This function will login using the horizon credentials from the config.
        Returns:

        """
        username = ConfigurationManager.get_lab_config().get_horizon_credentials().get_user_name()
        password = ConfigurationManager.get_lab_config().get_horizon_credentials().get_password()

        self.set_username(username)
        self.set_password(password)
        self.click_login()

    def set_username(self, username: str) -> None:
        """
        This function will set the username passed in the username input.
        Args:
            username: Username to enter.

        Returns:

        """

        username_input = self.locators.get_locator_username_input()
        self.driver.set_text(username_input, username)

    def set_password(self, password: str) -> None:
        """
        This function will set the password passed in the password input.
        Args:
            password: Password to enter.

        Returns:

        """

        password_input = self.locators.get_locator_password_input()
        self.driver.set_text(password_input, password)

    def click_login(self) -> None:
        """
        This function will click on the Login button.

        Returns:

        """

        login_button = self.locators.get_locator_login_button()
        self.driver.click(login_button)
