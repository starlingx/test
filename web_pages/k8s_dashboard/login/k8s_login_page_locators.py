from selenium.webdriver.common.by import By

from framework.web.web_locator import WebLocator


class K8sLoginPageLocators:
    """
    Page Elements class that contains elements for the Login Page.
    """

    def get_locator_token_input(self) -> WebLocator:
        """
        Locator for the Token Input field.

        Returns: WebLocator
        """
        return WebLocator("token", By.ID)

    def get_locator_signin_button(self) -> WebLocator:
        """
        Locator for the Login Button

        Returns: WebLocator
        """
        return WebLocator("//span[contains(text(),'Sign in')]", By.XPATH)

    def get_locator_overview_dashboard(self) -> WebLocator:
        """
        Locator for the Overview Dashboard element.

        Returns: WebLocator
        """
        return WebLocator("//div[contains(@class,'kd-toolbar-tools')]", By.XPATH)

    def get_locator_kubeconfig_option(self) -> WebLocator:
        """
        Locator for the Kubeconfig Option.

        Returns: WebLocator
        """
        return WebLocator("//input[contains(@value,'kubeconfig')]/..", By.XPATH)

    def get_locator_input_kubeconfig_file(self) -> WebLocator:
        """
        Locator for the Kubeconfig File Input.

        Returns: WebLocator
        """
        return WebLocator("""[title="fileInput"]""", By.CSS_SELECTOR)

    def get_locator_user_button(self) -> WebLocator:
        """
        Locator for the User Button.

        Returns: WebLocator
        """
        return WebLocator(".kd-user-panel-icon", By.CSS_SELECTOR)

    def get_locator_sign_out_button(self) -> WebLocator:
        """
        Locator for the Sign Out Button.

        Returns: WebLocator
        """
        return WebLocator("//button[contains(text(),'Sign out')]", By.XPATH)
