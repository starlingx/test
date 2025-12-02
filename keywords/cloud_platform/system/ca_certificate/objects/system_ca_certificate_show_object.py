class SystemCaCertificateShowObject:
    """
    System Certificate Object
    """

    def __init__(self):
        self.uuid = None
        self.certtype = None
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

    def set_cert_type(self, certtype: str) -> None:
        """
        Setter for certtype.

        Args:
            certtype (str): the certtype value
        """
        self.certtype = certtype

    def get_cert_type(self) -> str:
        """
        Getter for certtype.

        Returns:
            str: certtype
        """
        return self.certtype

    def set_signature(self, signature: str) -> None:
        """
        Setter signature.

        Args:
            signature (str): the signature
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
            start_date (str): the start_date
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
