"""Output parser for openssl x509 certificate text output."""

from keywords.openssl.object.cert_key_info_object import CertKeyInfoObject


class CertKeyInfoOutput:
    """Parses openssl x509 -text output to extract key algorithm information.

    Sample input (from openssl x509 -noout -text):
        Public Key Algorithm: id-ecPublicKey
            Public-Key: (384 bit)
            ASN1 OID: secp384r1
    Or:
        Public Key Algorithm: rsaEncryption
            Public-Key: (4096 bit)
    """

    def __init__(self, openssl_text_output: str) -> None:
        """Constructor.

        Args:
            openssl_text_output (str): Raw output from openssl x509 -noout -text.
        """
        self.cert_key_info = self._parse(openssl_text_output)

    def get_cert_key_info(self) -> CertKeyInfoObject:
        """Get the parsed certificate key info object.

        Returns:
            CertKeyInfoObject: Parsed key info with type, curve, and size.
        """
        return self.cert_key_info

    def _parse(self, raw: str) -> CertKeyInfoObject:
        """Parse openssl x509 text output for key algorithm details.

        Args:
            raw (str): Raw openssl x509 -text output.

        Returns:
            CertKeyInfoObject: Parsed key information.
        """
        key_info = CertKeyInfoObject()

        if "id-ecPublicKey" in raw:
            key_info.set_type("ECDSA")
            if "secp384r1" in raw:
                key_info.set_curve("secp384r1")
                key_info.set_size(384)
            elif "secp521r1" in raw:
                key_info.set_curve("secp521r1")
                key_info.set_size(521)
            elif "prime256v1" in raw:
                key_info.set_curve("prime256v1")
                key_info.set_size(256)
        elif "rsaEncryption" in raw:
            key_info.set_type("RSA")
            for line in raw.split("\n"):
                if "Public-Key:" in line:
                    size_str = line.split("(")[1].split(" ")[0] if "(" in line else "0"
                    key_info.set_size(int(size_str))
                    break

        return key_info
