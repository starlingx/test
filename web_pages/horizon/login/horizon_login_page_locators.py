from framework.web.web_locator import WebLocator
from selenium.webdriver.common.by import By


class HorizonLoginPageLocators:
    """
    Page Elements class that contains elements for the Login Page.
    """

    def get_locator_username_input(self) -> WebLocator:
        """
        Locator for the Username Input field.

        Returns: WebLocator
        """
        return WebLocator("#id_username", By.CSS_SELECTOR)

    def get_locator_password_input(self) -> WebLocator:
        """
        Locator for the Password Input field.

        Returns: WebLocator
        """
        return WebLocator("#id_password", By.CSS_SELECTOR)

    def get_locator_login_button(self) -> WebLocator:
        """
        Locator for the Login Button

        Returns: WebLocator
        """
        return WebLocator("#loginBtn", By.CSS_SELECTOR)
