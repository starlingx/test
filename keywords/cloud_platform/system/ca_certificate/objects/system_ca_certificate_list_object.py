class SystemCaCertificateListObject:
    """
    System Certificate Object
    """

    def __init__(self):
        self.uuid = None
        self.cert_type = None
        self.signature = None
        self.start_date = None
        self.expiry_date = None
        self.subject = None

    def set_uuid(self, uuid: str) -> None:
        """
        Setter for uuid.

        Args:
            uuid (str): uuid value
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid.

        Returns:
            str: uuid
        """
        return self.uuid

    def set_cert_type(self, cert_type: str) -> None:
        """
        Setter for cert_type.

        Args:
            cert_type (str): cert_type value
        """
        self.cert_type = cert_type

    def get_cert_type(self) -> str:
        """
        Getter for cert_type.

        Returns:
            str: cert_type
        """
        return self.cert_type

    def set_signature(self, signature: str) -> None:
        """
        Setter for signature.

        Args:
            signature (str): signature value
        """
        self.signature = signature

    def get_signature(self) -> str:
        """
        Getter for signature.

        Returns:
            str: signature
        """
        return self.signature

    def set_start_date(self, start_date: str) -> None:
        """
        Setter for start_date.

        Args:
            start_date (str): start_date value
        """
        self.start_date = start_date

    def get_start_date(self) -> str:
        """
        Getter for start_date.

        Returns:
            str: start_date
        """
        return self.start_date

    def set_expiry_date(self, expiry_date: str) -> None:
        """
        Setter for expiry_date.

        Args:
            expiry_date (str): expiry_date
        """
        self.expiry_date = expiry_date

    def get_expiry_date(self) -> str:
        """
        Getter for expiry_date.

        Returns:
            str: expiry_date
        """
        return self.expiry_date

    def set_subject(self, subject: str) -> None:
        """
        Setter for subject.

        Args:
            subject (str): the subject
        """
        self.subject = subject

    def get_subject(self) -> str:
        """
        Getter for subject.

        Returns:
            str: subject
        """
        return self.subject
