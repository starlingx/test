"""System Certificate Object."""

import re


class SystemCertificateObject:
    """Object representing a system certificate."""

    def __init__(self, name: str = None):
        """Initialize system certificate object.

        Args:
            name (str): Certificate name.
        """
        self.name = name
        self.residual_time = None
        self.issue_date = None
        self.expiry_date = None
        self.issuer = None
        self.subject = None
        self.renewal = None
        self.file_path = None
        self.namespace = None
        self.secret = None
        self.secret_type = None

    def set_name(self, name: str) -> None:
        """Set certificate name.

        Args:
            name (str): Certificate name.
        """
        self.name = name

    def get_name(self) -> str:
        """Get certificate name.

        Returns:
            str: Certificate name.
        """
        return self.name

    def set_residual_time(self, residual_time: str) -> None:
        """Set residual time string.

        Args:
            residual_time (str): Residual time (e.g., '89d', '364d').
        """
        self.residual_time = residual_time

    def get_residual_time(self) -> str:
        """Get residual time string.

        Returns:
            str: Residual time (e.g., '89d').
        """
        return self.residual_time

    def get_residual_time_days(self) -> int:
        """Get residual time as integer days.

        Returns:
            int: Number of days remaining, or -1 if not parseable.
        """
        if not self.residual_time:
            return -1
        match = re.match(r"(\d+)d", self.residual_time)
        return int(match.group(1)) if match else -1

    def set_issue_date(self, issue_date: str) -> None:
        """Set issue date string.

        Args:
            issue_date (str): Issue date (e.g., 'February 29 20:10:20 2024').
        """
        self.issue_date = issue_date

    def get_issue_date(self) -> str:
        """Get issue date string.

        Returns:
            str: Issue date.
        """
        return self.issue_date

    def set_expiry_date(self, expiry_date: str) -> None:
        """Set expiry date string.

        Args:
            expiry_date (str): Expiry date.
        """
        self.expiry_date = expiry_date

    def get_expiry_date(self) -> str:
        """Get expiry date string.

        Returns:
            str: Expiry date.
        """
        return self.expiry_date

    def set_issuer(self, issuer: str) -> None:
        """Set certificate issuer.

        Args:
            issuer (str): Certificate issuer.
        """
        self.issuer = issuer

    def get_issuer(self) -> str:
        """Get certificate issuer.

        Returns:
            str: Certificate issuer.
        """
        return self.issuer

    def set_subject(self, subject: str) -> None:
        """Set certificate subject.

        Args:
            subject (str): Certificate subject.
        """
        self.subject = subject

    def get_subject(self) -> str:
        """Get certificate subject.

        Returns:
            str: Certificate subject.
        """
        return self.subject

    def set_renewal(self, renewal: str) -> None:
        """Set renewal type.

        Args:
            renewal (str): Renewal type (e.g., 'Automatic', 'Manual').
        """
        self.renewal = renewal

    def get_renewal(self) -> str:
        """Get renewal type.

        Returns:
            str: Renewal type.
        """
        return self.renewal

    def is_automatic_renewal(self) -> bool:
        """Check if certificate has automatic renewal.

        Returns:
            bool: True if renewal is Automatic.
        """
        return self.renewal == "Automatic"

    def is_self_signed(self) -> bool:
        """Check if certificate is self-signed.

        Returns:
            bool: True if issuer equals subject, False otherwise.
        """
        return self.issuer == self.subject if self.issuer and self.subject else False

    def set_file_path(self, file_path: str) -> None:
        """Set certificate file path.

        Args:
            file_path (str): Certificate file path.
        """
        self.file_path = file_path

    def get_file_path(self) -> str:
        """Get certificate file path.

        Returns:
            str: Certificate file path.
        """
        return self.file_path

    def set_namespace(self, namespace: str) -> None:
        """Set certificate namespace.

        Args:
            namespace (str): Kubernetes namespace.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """Get certificate namespace.

        Returns:
            str: Kubernetes namespace.
        """
        return self.namespace

    def set_secret(self, secret: str) -> None:
        """Set certificate secret name.

        Args:
            secret (str): K8s secret name.
        """
        self.secret = secret

    def get_secret(self) -> str:
        """Get certificate secret name.

        Returns:
            str: K8s secret name.
        """
        return self.secret

    def set_secret_type(self, secret_type: str) -> None:
        """Set certificate secret type.

        Args:
            secret_type (str): Secret type (e.g., 'kubernetes.io/tls', 'Opaque').
        """
        self.secret_type = secret_type

    def get_secret_type(self) -> str:
        """Get certificate secret type.

        Returns:
            str: Secret type.
        """
        return self.secret_type
