from enum import IntEnum


class RevocationReason(IntEnum):
    """RFC 5280 certificate revocation reason codes.

    These correspond to the CRL reason codes defined in RFC 5280 Section 5.3.1.
    Used with openssl cmp -revreason parameter.
    """

    UNSPECIFIED = 0
    KEY_COMPROMISE = 1
    CA_COMPROMISE = 2
    AFFILIATION_CHANGED = 3
    SUPERSEDED = 4
    CESSATION_OF_OPERATION = 5
    CERTIFICATE_HOLD = 6
    REMOVE_FROM_CRL = 8
    PRIVILEGE_WITHDRAWN = 9
    AA_COMPROMISE = 10
