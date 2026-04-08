from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class KeycloakLoginPageLocators:
    """Page element locators for the Keycloak login page."""

    def get_locator_username_input(self) -> WebLocator:
        """Locator for the username input field.

        Returns:
            WebLocator: Username input locator.
        """
        return WebLocator("#username", By.CSS_SELECTOR)

    def get_locator_password_input(self) -> WebLocator:
        """Locator for the password input field.

        Returns:
            WebLocator: Password input locator.
        """
        return WebLocator("#password", By.CSS_SELECTOR)

    def get_locator_sign_in_button(self) -> WebLocator:
        """Locator for the Sign In button.

        Returns:
            WebLocator: Sign In button locator.
        """
        return WebLocator("#kc-login", By.CSS_SELECTOR)

    def get_locator_otp_input(self) -> WebLocator:
        """Locator for the OTP input field on the MFA challenge page.

        Returns:
            WebLocator: OTP input locator.
        """
        return WebLocator("#otp", By.CSS_SELECTOR)

    def get_locator_totp_setup_input(self) -> WebLocator:
        """Locator for the OTP input field on the CONFIGURE_TOTP setup page.

        Returns:
            WebLocator: TOTP setup OTP input locator.
        """
        return WebLocator("#totp", By.CSS_SELECTOR)

    def get_locator_totp_setup_submit_button(self) -> WebLocator:
        """Locator for the submit button on the CONFIGURE_TOTP setup page.

        Returns:
            WebLocator: TOTP setup submit button locator.
        """
        return WebLocator("input[type='submit']", By.CSS_SELECTOR)

    def get_locator_totp_secret_key(self) -> WebLocator:
        """Locator for the manual TOTP secret key on the CONFIGURE_TOTP page.

        Returns:
            WebLocator: TOTP secret key locator.
        """
        return WebLocator("#kc-totp-secret-key", By.CSS_SELECTOR)

    def get_locator_totp_manual_mode_button(self) -> WebLocator:
        """Locator for the 'Unable to scan?' link that reveals the manual key.

        Returns:
            WebLocator: Manual mode button locator.
        """
        return WebLocator("#mode-manual", By.CSS_SELECTOR)
