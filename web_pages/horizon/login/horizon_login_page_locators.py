"""Horizon Login Page locators."""

from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


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

    def get_locator_table_row_by_display_name(self, name: str) -> WebLocator:
        """Locator for a visible element containing the resource display name.

        Targets any visible element on the page whose direct text content
        contains the specified resource name.

        Args:
            name (str): The display name of the resource to find.

        Returns:
            WebLocator: XPath locator for the element containing the display name.
        """
        return WebLocator(f"//*[contains(text(), '{name}')]", By.XPATH)

    def get_locator_auth_method_select(self) -> WebLocator:
        """Locator for the Horizon authentication-method dropdown (Keystone / OpenID Connect).

        Horizon presents this select when WebSSO is enabled, letting the user
        choose the authentication method before signing in.

        Returns:
            WebLocator: CSS selector for the auth-method select element.
        """
        return WebLocator("#id_auth_type, select[name='auth_type']", By.CSS_SELECTOR)

    def get_locator_oidc_auth_option(self) -> WebLocator:
        """Locator for the "OpenID Connect" option in the auth-method dropdown.

        Returns:
            WebLocator: XPath for the OpenID Connect option.
        """
        return WebLocator("//option[contains(translate(text(),'OPENID CNCT','openid cnct'),'openid connect')]", By.XPATH)

    def get_locator_keystone_auth_option(self) -> WebLocator:
        """Locator for the "Keystone Credentials" option in the auth-method dropdown.

        Returns:
            WebLocator: XPath for the Keystone Credentials option.
        """
        return WebLocator("//option[contains(translate(text(),'KEYSTONE','keystone'),'keystone')]", By.XPATH)
