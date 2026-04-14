import base64
import datetime
import hashlib
import hmac
import re
import struct
import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.web.condition.web_condition_element_visible import WebConditionElementVisible
from framework.web.web_locator import WebLocator
from framework.web.webdriver_core import WebDriverCore
from web_pages.base_page import BasePage
from web_pages.keycloak.login.keycloak_login_page_locators import KeycloakLoginPageLocators


class KeycloakLoginPage(BasePage):
    """Page class for Keycloak login with MFA — handles both first-time CONFIGURE_TOTP and OTP challenge."""

    def __init__(self, driver: WebDriverCore):
        """Constructor.

        Args:
            driver (WebDriverCore): The web driver instance.
        """
        self.driver = driver
        self.locators = KeycloakLoginPageLocators()

    def navigate_to_login_url(self, url: str) -> None:
        """Navigate to the OIDC login URL, retrying until the kubelogin listener is ready.

        Args:
            url (str): The OIDC login URL to navigate to.
        """
        condition = WebConditionElementVisible(self.locators.get_locator_username_input())
        self.driver.navigate_to_url(url, [condition])

    def enter_credentials(self, username: str, password: str) -> None:
        """Enter username and password then click Sign In.

        Args:
            username (str): Keycloak username.
            password (str): Keycloak password.
        """
        self.driver.set_text(self.locators.get_locator_username_input(), username)
        self.driver.set_text(self.locators.get_locator_password_input(), password)
        self.driver.click(self.locators.get_locator_sign_in_button())
        get_logger().log_info(f"After Sign In - current URL: {self.driver.get_current_url()}")

    def normalize_totp_secret(self, secret: str) -> str:
        """Strip spaces and non-Base32 characters from a TOTP secret.

        Args:
            secret (str): Raw TOTP secret string.

        Returns:
            str: Cleaned Base32 secret.
        """
        return re.sub(r"[^A-Z2-7]", "", secret.upper())

    def generate_totp(self, secret: str) -> str:
        """Generate the current TOTP code using RFC 6238.

        Args:
            secret (str): Base32-encoded TOTP secret.

        Returns:
            str: 6-digit OTP code as a zero-padded string.
        """
        key = base64.b32decode(self.normalize_totp_secret(secret))
        counter = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) // 30
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        offset_byte = hmac_hash[-1] & 0x0F
        code = struct.unpack(">I", hmac_hash[offset_byte : offset_byte + 4])[0] & 0x7FFFFFFF
        return str(code % 1000000).zfill(6)

    def submit_otp(self, input_locator: WebLocator, submit_locator: WebLocator, totp_secret: str) -> None:
        """Submit a TOTP code, waiting for the next window between rejections.

        Tries the current TOTP window. If rejected, waits until the next 30-second
        window boundary before retrying — this is required because Keycloak's
        brute-force protection rejects any further submissions on the same execution
        URL until the current window expires. Retries up to 3 windows total.

        Args:
            input_locator (WebLocator): Locator for the OTP input field.
            submit_locator (WebLocator): Locator for the submit button.
            totp_secret (str): Base32-encoded TOTP secret.

        Raises:
            KeywordException: If all attempts are exhausted without success.
        """
        url_before = self.driver.get_current_url()
        for attempt in range(1, 4):
            otp_code = self.generate_totp(totp_secret)
            get_logger().log_info(f"Submitting OTP attempt {attempt}: {otp_code}")
            self.driver.set_text(input_locator, otp_code)
            self.driver.click(submit_locator)
            deadline = time.time() + 8
            while time.time() < deadline:
                if self.driver.get_current_url() != url_before:
                    get_logger().log_info(f"OTP accepted on attempt {attempt}")
                    return
                time.sleep(0.5)
            if attempt < 3:
                seconds_until_next_window = 30 - (int(time.time()) % 30)
                get_logger().log_info(f"OTP rejected on attempt {attempt}, waiting {seconds_until_next_window}s for next window")
                time.sleep(seconds_until_next_window)
        raise KeywordException(f"OTP authentication failed after 3 attempts. URL: {self.driver.get_current_url()}")

    def wait_for_mfa_page(self, timeout: int = 30) -> str:
        """Wait for either the OTP challenge page or CONFIGURE_TOTP setup page.

        Args:
            timeout (int): Maximum seconds to wait.

        Returns:
            str: 'otp' if OTP challenge page, 'configure_totp' if CONFIGURE_TOTP page.

        Raises:
            KeywordException: If neither page appears within timeout seconds.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if "CONFIGURE_TOTP" in self.driver.get_current_url():
                return "configure_totp"
            if self.driver.is_exists(self.locators.get_locator_otp_input()):
                return "otp"
            if self.driver.is_exists(self.locators.get_locator_totp_setup_input()):
                return "configure_totp"
            time.sleep(0.5)
        raise KeywordException(f"No MFA page appeared within {timeout} seconds. URL: {self.driver.get_current_url()}")

    def handle_configure_totp(self) -> None:
        """Handle the first-time CONFIGURE_TOTP registration flow.

        Reads the TOTP secret from the page, generates an OTP from it,
        and submits it to complete device registration.
        """
        get_logger().log_info(f"CONFIGURE_TOTP page detected - current URL: {self.driver.get_current_url()}")
        if self.driver.is_exists(self.locators.get_locator_totp_manual_mode_button()):
            self.driver.click(self.locators.get_locator_totp_manual_mode_button())
        raw_secret = self.driver.get_text(self.locators.get_locator_totp_secret_key())
        page_secret = self.normalize_totp_secret(raw_secret)
        get_logger().log_info(f"Captured TOTP secret from page: {page_secret}")
        self.submit_otp(
            self.locators.get_locator_totp_setup_input(),
            self.locators.get_locator_totp_setup_submit_button(),
            page_secret,
        )

    def handle_otp_challenge(self, totp_secret: str) -> None:
        """Handle the OTP challenge page for an already-enrolled user.

        Args:
            totp_secret (str): Base32-encoded TOTP secret registered for the user.
        """
        get_logger().log_info(f"OTP challenge page detected - current URL: {self.driver.get_current_url()}")
        self.submit_otp(
            self.locators.get_locator_otp_input(),
            self.locators.get_locator_sign_in_button(),
            totp_secret,
        )

    def login(self, username: str, password: str, totp_secret: str = None) -> None:
        """Perform the full Keycloak login flow including MFA.

        Handles both first-time CONFIGURE_TOTP registration and subsequent
        OTP challenge flows automatically based on what Keycloak presents.

        Args:
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32-encoded TOTP secret for OTP challenge.
                Pass None for first-time login where CONFIGURE_TOTP is expected.

        Raises:
            KeywordException: If OTP challenge appears but no totp_secret was provided.
        """
        self.enter_credentials(username, password)
        page = self.wait_for_mfa_page()
        if page == "configure_totp":
            self.handle_configure_totp()
        else:
            if not totp_secret:
                raise KeywordException("OTP challenge page appeared but no totp_secret was provided.")
            self.handle_otp_challenge(totp_secret)

    def login_no_mfa(self, username: str, password: str) -> None:
        """Perform Keycloak login for a user with no MFA configured.

        Enters credentials and waits for the page to redirect away from the
        login URL, indicating authentication completed without any OTP step.

        Args:
            username (str): Keycloak username.
            password (str): Keycloak password.

        Raises:
            KeywordException: If login did not complete within 30 seconds.
        """
        self.enter_credentials(username, password)
        deadline = time.time() + 30
        while time.time() < deadline:
            if "login-actions" not in self.driver.get_current_url():
                get_logger().log_info(f"Login completed - current URL: {self.driver.get_current_url()}")
                return
            time.sleep(0.5)
        raise KeywordException(f"Login did not complete within 30 seconds. URL: {self.driver.get_current_url()}")

    def login_with_invalid_otp(self, username: str, password: str) -> None:
        """Perform Keycloak login with valid credentials but a deliberately invalid OTP.

        Enters username and password, waits for the OTP challenge page, then
        submits '000000' as the OTP code. Keycloak rejects the invalid code and
        stays on the OTP challenge page. Returns after rejection is confirmed.

        Args:
            username (str): Keycloak username.
            password (str): Keycloak password.

        Raises:
            KeywordException: If the OTP challenge page does not appear after credentials.
            KeywordException: If Keycloak did not reject the invalid OTP within 10 seconds.
        """
        self.enter_credentials(username, password)
        page = self.wait_for_mfa_page()
        if page != "otp":
            raise KeywordException(f"Expected OTP challenge page but got '{page}'. User may not have OTP enrolled.")
        get_logger().log_info("OTP challenge page detected - submitting invalid OTP code")
        url_before = self.driver.get_current_url()
        self.driver.set_text(self.locators.get_locator_otp_input(), "000000")
        self.driver.click(self.locators.get_locator_sign_in_button())
        deadline = time.time() + 10
        while time.time() < deadline:
            if self.driver.get_current_url() == url_before:
                get_logger().log_info("Invalid OTP rejected by Keycloak - authentication failed as expected")
                return
            time.sleep(0.5)
        raise KeywordException(f"Keycloak did not reject the invalid OTP within 10 seconds. URL: {self.driver.get_current_url()}")
