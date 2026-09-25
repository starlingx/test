"""Selenium locators for the DEX login page (connector selection and native login form)."""

from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class DexLoginPageLocators:
    """Page element locators for the DEX login and connector-selection pages.

    Covers the DEX connector-selection page (shown when multiple connectors are
    configured) and the DEX-native login form used by the Local LDAP and WAD
    connectors. The Keycloak connector redirects to Keycloak, whose form is
    handled by KeycloakLoginPageLocators.
    """

    def get_locator_connector_links(self) -> WebLocator:
        """Locator for the DEX connector-selection links ("Log in with <connector>").

        Returns:
            WebLocator: Connector link locator (matches local, oidc, and auth links).
        """
        return WebLocator("a.dex-btn-icon--local, a.dex-btn-icon--oidc, a[href*='/auth/']", By.CSS_SELECTOR)

    def get_locator_username_input(self) -> WebLocator:
        """Locator for the DEX-native username input field.

        Returns:
            WebLocator: Username input locator.
        """
        return WebLocator("#login", By.CSS_SELECTOR)

    def get_locator_password_input(self) -> WebLocator:
        """Locator for the DEX-native password input field.

        Returns:
            WebLocator: Password input locator.
        """
        return WebLocator("#password", By.CSS_SELECTOR)

    def get_locator_sign_in_button(self) -> WebLocator:
        """Locator for the DEX-native login submit button.

        Returns:
            WebLocator: Submit button locator.
        """
        return WebLocator("#submit-login", By.CSS_SELECTOR)

    def get_locator_generic_submit_button(self) -> WebLocator:
        """Locator for a generic submit button (fallback for differing DEX themes).

        Returns:
            WebLocator: Generic submit button locator.
        """
        return WebLocator("button[type='submit'], input[type='submit']", By.CSS_SELECTOR)
