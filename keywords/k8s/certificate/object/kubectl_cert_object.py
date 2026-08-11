"""KubectlCertObject keywords."""


class KubectlCertObject:
    """
    Class to hold attributes of a 'kubectl get certificate' certificate entry.
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): Name of the certs.
        """
        self.name = name
        self.ready = None
        self.age = None
        self.secret = None
        self.algorithm = None
        self.size = None
        self.issuer_ref = None
        self.revision = None

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
             str: The name of the certs.
        """
        return self.name

    def set_secret(self, secret: str) -> None:
        """
        Setter for SECRET

        Args:
            secret (str): The secret associated with the certs.

        Returns: None
        """
        self.secret = secret

    def get_secret(self) -> str:
        """
        Getter for SECRET entry
        """
        return self.secret

    def set_ready(self, ready: str) -> None:
        """
        Setter for READY

        Args:
            ready (str): The ready associated with the certs.

        Returns: None
        """
        self.ready = ready

    def get_ready(self) -> str:
        """
        Getter for READY entry
        """
        return self.ready

    def set_age(self, age: str) -> None:
        """
        Setter for AGE.

        Args:
            age (str): The age associated with the certs.

        Returns: None
        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry.

        Returns:
             str: The age of the certs.
        """
        return self.age

    def set_algorithm(self, algorithm: str) -> None:
        """Set the private key algorithm.

        Args:
            algorithm (str): Key algorithm (e.g., "RSA", "ECDSA").
        """
        self.algorithm = algorithm

    def get_algorithm(self) -> str:
        """Get the private key algorithm.

        Returns:
            str: Key algorithm.
        """
        return self.algorithm

    def set_size(self, size: str) -> None:
        """Set the private key size.

        Args:
            size (str): Key size (e.g., "384", "4096").
        """
        self.size = size

    def get_size(self) -> str:
        """Get the private key size.

        Returns:
            str: Key size.
        """
        return self.size

    def set_issuer_ref(self, issuer_ref: str) -> None:
        """Set the issuer reference name.

        Args:
            issuer_ref (str): Issuer name (e.g., "system-local-ca").
        """
        self.issuer_ref = issuer_ref

    def get_issuer_ref(self) -> str:
        """Get the issuer reference name.

        Returns:
            str: Issuer name.
        """
        return self.issuer_ref

    def set_revision(self, revision: str) -> None:
        """Set the certificate revision.

        Args:
            revision (str): Revision number.
        """
        self.revision = revision

    def get_revision(self) -> str:
        """Get the certificate revision.

        Returns:
            str: Revision number.
        """
        return self.revision

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            str: Human-readable certificate info.
        """
        return f"Cert({self.name}, ready={self.ready}, algorithm={self.algorithm}, size={self.size})"
