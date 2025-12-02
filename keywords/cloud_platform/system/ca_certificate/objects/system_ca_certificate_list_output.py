from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.ca_certificate.objects.system_ca_certificate_list_object import SystemCaCertificateListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemCaCertificateListOutput:
    """
    Class for System ca-certificate-list Output
    """

    def __init__(self, system_ca_certificate_output):
        system_table_parser = SystemTableParser(system_ca_certificate_output)
        self.certificates = []

        # Parse each row as a certificate
        for row in system_table_parser.get_output_values_list():
            cert_obj = SystemCaCertificateListObject()
            if "uuid" in row:
                cert_obj.set_uuid(row["uuid"])
            elif "expiry_date" in row:
                cert_obj.set_expiry_date(row["expiry_date"])
            elif "subject" in row:
                cert_obj.set_subject(row["subject"])
            self.certificates.append(cert_obj)

    def get_certificates(self) -> List[SystemCaCertificateListObject]:
        """Returns list of all certificates"""
        return self.certificates

    def get_certificate_by_uuid(self, uuid: str) -> SystemCaCertificateListObject:
        """Returns certificate with matching UUID.

        Args:
            uuid (str): The UUID of the certificate to find

        Returns:
            SystemCaCertificateListObject: The matching certificate.

        Raises:
            KeywordException: If certificate with specified UUID is not found.
        """
        for cert in self.certificates:
            if cert.get_uuid() == uuid:
                return cert
        raise KeywordException(f"Certificate with UUID '{uuid}' not found in certificate list")
