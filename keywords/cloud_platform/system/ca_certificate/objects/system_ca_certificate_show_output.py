from keywords.cloud_platform.system.ca_certificate.objects.system_ca_certificate_show_object import SystemCaCertificateShowObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemCaCertificateShowOutput:
    """
    Class for System ca-certificate-show Output
    """

    def __init__(self, system_ca_certificate_output):
        system_table_parser = SystemTableParser(system_ca_certificate_output)
        self.output_values = system_table_parser.get_output_values_list()
        self.system_ca_certificate_show_object = SystemCaCertificateShowObject()

        uuid = self.get_property_value("uuid")
        if uuid:
            self.system_ca_certificate_show_object.set_uuid(uuid)

        cert_type = self.get_property_value("certtype")
        if cert_type:
            self.system_ca_certificate_show_object.set_cert_type(cert_type)

        signature = self.get_property_value("signature")
        if signature:
            self.system_ca_certificate_show_object.set_signature(signature)

        start_date = self.get_property_value("start_date")
        if start_date:
            self.system_ca_certificate_show_object.set_start_date(start_date)

        expiry_date = self.get_property_value("expiry_date")
        if expiry_date:
            self.system_ca_certificate_show_object.set_expiry_date(expiry_date)

        subject = self.get_property_value("subject")
        if subject:
            self.system_ca_certificate_show_object.set_subject(subject)

    def get_property_value(self, property: str) -> str:
        """
        Returns the value of the property.

        Args:
            property (str): the property name to get the value for

        Returns:
            str: property value
        """
        values = list(filter(lambda property_dict: property_dict["Property"] == property, self.output_values))
        if len(values) == 0:
            return None  # no key was found

        return values[0]["Value"]
