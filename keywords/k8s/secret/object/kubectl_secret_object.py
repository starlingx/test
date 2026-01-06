import base64
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend


class KubectlSecretObject:
    """
    Class to hold attributes of a 'kubectl get secrets' command entry
    """

    def __init__(self, name: str):
        """Initialize the secret object with name.

        Args:
            name (str): Name of the secret.
        """
        self.name = name
        self.type = None
        self.data = None
        self.age = None
        self._metadata = {}
        self._raw_json = {}

    def get_name(self) -> str:
        """
        Getter for NAME entry
        """
        return self.name

    def set_name(self, name: str) -> None:
        """
        Setter for NAME entry

        Args:
            name (str): secret name
        """
        self.name = name

    def get_type(self) -> str:
        """
        Getter for TYPE entry
        """
        return self.type

    def set_type(self, type: str) -> None:
        """
        Setter for TYPE entry

        Args:
            type (str): secret type
        """
        self.type = type

    def get_data(self) -> int:
        """
        Getter for DATA entry
        """
        return self.data

    def set_data(self, data: int) -> None:
        """
        Setter for DATA entry

        Args:
            data (int): secret data
        """
        self.data = data

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """
        return self.age

    def set_age(self, age: str) -> None:
        """
        Setter for AGE entry

        Args:
            age (str): secret age
        """
        self.age = age

    def load_json(self, secret_json: dict) -> None:
        """Load and parse secret JSON data into object attributes.

        Args:
            secret_json (dict): JSON dictionary containing secret metadata and data.
        """
        self._raw_json = secret_json
        self._metadata = secret_json.get("metadata", {})
        self.data = secret_json.get("data", {})
        self.type = secret_json.get("type", None)
        self.name = self._metadata.get("name", self.name)

    def get_metadata(self) -> dict:
        """Return metadata portion of the secret JSON.

        Returns:
            dict: Metadata dictionary.
        """
        return self._metadata

    def get_namespace(self) -> Optional[str]:
        """Return the namespace of the secret.

        Returns:
            Optional[str]: The namespace if available, otherwise None.
        """
        return self._metadata.get("namespace")

    def get_raw_json(self) -> dict:
        """Return the full raw JSON dictionary for the secret.

        Returns:
            dict: Complete raw JSON.
        """
        return self._raw_json

    def get_tls_crt(self) -> Optional[str]:
        """Return decoded TLS certificate content.

        Returns:
            Optional[str]: Base64-decoded certificate string or None if missing.
        """
        return self.data.get("tls.crt") if isinstance(self.data, dict) else None

    def get_decoded_data(self, key: str) -> Optional[str]:
        """Return the decoded string of a specific key in the secret data.

        Args:
            key (str): The key to decode from the secret.

        Returns:
            Optional[str]: The decoded value, or None if key is missing.
        """
        if not isinstance(self.data, dict):
            return None
        value = self.data.get(key)
        if value:
            try:
                return base64.b64decode(value).decode("utf-8")
            except Exception:
                pass
        return None

    def get_certificate_issuer(self) -> str | None:
        """
        Retrieves the Issuer information from the 'tls.crt' data of the parsed secret.
        """
        encoded_cert = self.get_tls_crt()
        if not encoded_cert:
            return None
        decoded_cert = base64.b64decode(encoded_cert)
        cert = x509.load_pem_x509_certificate(decoded_cert, default_backend())
        return cert.issuer.rfc4514_string()

    def get_certificate_subject(self) -> str | None:
        """
        Retrieves the Subject information from the 'tls.crt' data of the parsed secret.
        """
        encoded_cert = self.get_tls_crt()
        if not encoded_cert:
            return None
        decoded_cert = base64.b64decode(encoded_cert)
        cert = x509.load_pem_x509_certificate(decoded_cert, default_backend())
        return cert.subject.rfc4514_string()
