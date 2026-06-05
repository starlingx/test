"""Horizon Login Page locators."""

from framework.web.web_locator import WebLocator
from selenium.webdriver.common.by import By


class HorizonLoginPageLocators:
    """Page Elements class that contains locators for the Horizon Login Page."""

    def get_locator_username_input(self) -> WebLocator:
        """Locator for the Username Input field.

        Returns:
            WebLocator: CSS selector for the username input.
        """
        return WebLocator("#id_username", By.CSS_SELECTOR)

    def get_locator_password_input(self) -> WebLocator:
        """Locator for the Password Input field.

        Returns:
            WebLocator: CSS selector for the password input.
        """
        return WebLocator("#id_password", By.CSS_SELECTOR)

    def get_locator_login_button(self) -> WebLocator:
        """Locator for the Login Button.

        Returns:
            WebLocator: CSS selector for the login button.
        """
        return WebLocator("#loginBtn", By.CSS_SELECTOR)

    def get_locator_user_dropdown(self) -> WebLocator:
        """Locator for the user dropdown menu (visible when logged in).

        Returns:
            WebLocator: CSS selector for the user dropdown.
        """
        return WebLocator(".nav-user-dropdown, #user_info, .user-menu", By.CSS_SELECTOR)

    def get_locator_nav_user(self) -> WebLocator:
        """Locator for the navigation user menu element.

        Returns:
            WebLocator: CSS selector for navigation user menu.
        """
        return WebLocator(".nav .user-menu", By.CSS_SELECTOR)

    def get_locator_top_bar_user(self) -> WebLocator:
        """Locator for the top bar user name element.

        Returns:
            WebLocator: CSS selector for the top bar user name.
        """
        return WebLocator("#user_info span.user-name", By.CSS_SELECTOR)

    def get_locator_logout_link(self) -> WebLocator:
        """Locator for the logout link element.

        Returns:
            WebLocator: CSS selector for the logout link.
        """
        return WebLocator("a[href*='logout']", By.CSS_SELECTOR)

    def get_locator_error_message(self) -> WebLocator:
        """Locator for login error alert messages.

        Returns:
            WebLocator: CSS selector for the error message element.
        """
        return WebLocator(".alert-danger, .alert.alert-danger, .error", By.CSS_SELECTOR)
