import requests
import urllib3

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class KeycloakAdminKeywords(BaseKeyword):
    """Keywords for Keycloak Admin REST API operations.

    Uses the Keycloak Admin REST API directly via HTTP requests rather than SSH.
    response.raise_for_status() is used for HTTP error handling in place of
    validate_success_return_code, which applies to SSH connections only.
    """

    def __init__(self, keycloak_url: str, realm: str, admin_username: str, admin_password: str):
        """Constructor.

        Args:
            keycloak_url (str): Base Keycloak URL e.g. https://keycloak.example.com
            realm (str): Keycloak realm name.
            admin_username (str): Keycloak admin username.
            admin_password (str): Keycloak admin password.
        """
        self.base_url = keycloak_url
        self.realm = realm
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.token = None

    def get_admin_token(self) -> str:
        """Obtain an admin access token from Keycloak.

        Returns:
            str: Admin access token.

        Raises:
            requests.exceptions.HTTPError: If the token request fails.
        """
        url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        data = {
            "client_id": "admin-cli",
            "username": self.admin_username,
            "password": self.admin_password,
            "grant_type": "password",
        }
        response = requests.post(url, data=data, verify=False)
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token

    def get_user_id(self, username: str) -> str:
        """Get the Keycloak user ID for a given username.

        Args:
            username (str): Keycloak username to look up.

        Returns:
            str: Keycloak user UUID.

        Raises:
            KeywordException: If the user is not found in the realm.
            requests.exceptions.HTTPError: If the API request fails.
        """
        self.get_admin_token()
        url = f"{self.base_url}/admin/realms/{self.realm}/users"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers, params={"username": username, "exact": "true"}, verify=False)
        response.raise_for_status()
        users = response.json()
        if not users:
            raise KeywordException(f"User '{username}' not found in realm '{self.realm}'")
        return users[0]["id"]

    def delete_user_otp_credentials(self, username: str) -> None:
        """Delete all OTP credentials for a Keycloak user.

        Args:
            username (str): Keycloak username whose OTP credentials to delete.

        Raises:
            requests.exceptions.HTTPError: If any API request fails.
        """
        self.get_admin_token()
        user_id = self.get_user_id(username)
        url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/credentials"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        for credential in response.json():
            if credential.get("type") == "otp":
                cred_id = credential["id"]
                del_url = f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/credentials/{cred_id}"
                del_response = requests.delete(del_url, headers=headers, verify=False)
                del_response.raise_for_status()
                get_logger().log_info(f"Deleted OTP credential '{cred_id}' for user '{username}'")

    def clear_user_brute_force_lockout(self, username: str) -> None:
        """Clear brute-force lockout for a Keycloak user.

        Resets the failed OTP attempt counter so the next login attempt is
        accepted. Required after repeated failed OTP submissions which lock
        the user's authentication execution.

        Args:
            username (str): Keycloak username to clear lockout for.

        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        self.get_admin_token()
        user_id = self.get_user_id(username)
        url = f"{self.base_url}/admin/realms/{self.realm}/attack-detection/brute-force/users/{user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(url, headers=headers, verify=False)
        response.raise_for_status()
        get_logger().log_info(f"Cleared brute-force lockout for user '{username}'")
