from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.k8s_dashboard.login.k8s_login_page_locators import K8sLoginPageLocators


class K8sLoginPage(BasePage):
    """
    Page class that contains operations for the Login Page.
    """

    def __init__(self, driver: WebDriverCore):
        self.locators = K8sLoginPageLocators()
        self.driver = driver

    def navigate_to_login_page(self, dashboard_url: str) -> None:
        """
        Navigates to the Kubernetes Dashboard Login Page.

        Args:
            dashboard_url (str): The URL of the Kubernetes Dashboard.
        """
        signin_btn = self.locators.get_locator_signin_button()
        condition = WebConditionElementVisible(signin_btn)
        self.driver.navigate_to_url(dashboard_url, [condition])

    def login_with_token(self, token: str) -> None:
        """
        Logs in to the Kubernetes Dashboard using the provided token.

        Args:
            token (str): The authentication token to use for login.
        """
        self.set_token(token)
        self.click_signin()

    def login_with_kubeconfig(self, kubeconfig_path: str) -> None:
        """
        Logs in to the Kubernetes Dashboard using the provided kubeconfig file.

        Args:
            kubeconfig_path (str): The file path to the kubeconfig file.
        """
        condition = WebConditionElementVisible(self.locators.get_locator_input_kubeconfig_file())
        kubeconfig_option = self.locators.get_locator_kubeconfig_option()
        self.driver.click(kubeconfig_option, conditions=[condition])

        # this actually needs to be changed to send_keys
        kubeconfig_input = self.locators.get_locator_input_kubeconfig_file()
        self.driver.set_text(kubeconfig_input, kubeconfig_path)

        self.click_signin()

    def click_user_button(self) -> None:
        """
        This function will click on the User button.
        """
        condition = WebConditionElementVisible(self.locators.get_locator_sign_out_button())
        self.driver.click(locator=self.locators.get_locator_user_button(), conditions=[condition])

    def logout(self) -> None:
        """
        This function will logout from the k8s dashboard.
        """
        # click at user button first
        self.click_user_button()
        # click at logout button
        self.click_signout()

    def set_token(self, token: str) -> None:
        """
        Sets the provided authentication token in the token input field.

        Args:
            token (str): The authentication token to be entered in the input field.
        """
        token_input = self.locators.get_locator_token_input()
        self.driver.set_text(token_input, token)

    def click_signin(self):
        """
        This function will click on the Signin button and check if the dashboard appears
        """
        condition = WebConditionElementVisible(self.locators.get_locator_overview_dashboard())

        signin_button = self.locators.get_locator_signin_button()
        self.driver.click(signin_button, conditions=[condition])

    def click_signout(self):
        """
        This function will click on the Signout button and check if the login page appears
        """
        condition = WebConditionElementVisible(self.locators.get_locator_signin_button())
        signin_button = self.locators.get_locator_sign_out_button()
        self.driver.click(signin_button, conditions=[condition])
