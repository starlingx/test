import re

from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.cat.objects.ptp_cgu_component_object import PtpCguComponentObject
from keywords.ptp.cat.objects.ptp_cgu_eec_dpll_object import PtpCguEecDpllObject
from keywords.ptp.cat.objects.ptp_cgu_input_object import PtpCguInputObject
from keywords.ptp.cat.objects.ptp_cgu_pps_dpll_object import PtpCguPpsDpllObject


class CatPtpCguParser:
    """
    Class for PTP CGU Parser.
    """

    def __init__(self, cat_ptp_cgu_output: list[str]):
        """
        Constructor.

        Args:
            cat_ptp_cgu_output (list[str]): a list of strings representing the output of a 'cat /sys/kernel/debug/ice/0000:51:00.0/cgu' command.
        """
        self.cat_ptp_cgu_output = cat_ptp_cgu_output

    def parse_ptp_cgu_objects(self) -> PtpCguComponentObject:
        """
        Parses the CGU output and returns a CGUComponent object containing all the parsed information.

        Regular Expression Explanations:

        1. Chip Model and Versions:
            r"Found (\S+) CGU\\nDPLL Config ver: (.*)\\nDPLL FW ver: (.*)"
                - Found: Matches the literal "Found ".
                - (\S+): Captures one or more non-whitespace characters (the chip model).
                - CGU\\nDPLL Config ver: Matches the literal string. \\n is the newline char.
                - (.*): Captures any characters (including spaces) until the next part of the pattern (config version).
                - \\nDPLL FW ver: Matches the literal string.
                - (.*): Captures any characters until the end of the line (firmware version).

        2. CGU Input Status:
            r"\\s*(\\S+)\\s*\\((\\d+)\\)\\s*\\|\\s*(\\S+)\\s*\\|\\s*(\\d+)\\s*\\|\\s*(\\d+)\\s*\\|\\s*(N/A|\\S+)\\s*\\|"
                - \\s*: Matches zero or more whitespace characters.
                - (\\S+): Captures one or more non-whitespace characters (input name).
                - \\((\\d+)\\): Captures one or more digits inside parentheses (input index).
                - \\|: Matches the literal "|" character (needs to be escaped).
                - (\\S+): Captures one or more non-whitespace characters (state).
                - (\\d+): Captures one or more digits (EEC and PPS values).
                - (N/A|\\S+): Captures either "N/A" or one or more non-whitespace characters (ESync fail).

        3. EEC DPLL and PPS DPLL:
            r"Current reference:\\s*(.*)"
                - Current reference:\\s*: Matches the literal string.
                - (.*): Captures any characters (reference name).
            r"Status:\\s*(.*)"
                - Status:\\s*: Matches the literal string.
                - (.*): Captures any characters (status).
            r"Phase offset \\[ps]:\\s*(.*)"
                - Phase offset \\[ps]:\\s*: Matches the literal string (escapes the brackets).
                - (.*): Captures any characters (phase offset).

        Returns:
            PtpCguComponentObject - the PtpCguComponentObject.
        Raise:
            KeywordException - if output is unable to be parsed.

        """
        cgu: PtpCguComponentObject = None

        match = re.match(r"(Found (\S+) CGU|Password: Found (\S+) CGU)", self.cat_ptp_cgu_output[0]) # Ask about this
        if match:
            chip_model = match.group(1)
            config_version_match = re.search(
                r"DPLL Config ver: (.*)", self.cat_ptp_cgu_output[1]
            )
            fw_version_match = re.search(
                r"DPLL FW ver: (.*)", self.cat_ptp_cgu_output[2]
            )
            if config_version_match and fw_version_match:
                config_version = config_version_match.group(1)
                fw_version = fw_version_match.group(1)
                cgu = PtpCguComponentObject(config_version, fw_version, chip_model)
            else:
                raise KeywordException(
                    f"Unable to parse output. Got : {self.cat_ptp_cgu_output}"
                )
        else:
            raise KeywordException(
                f"Unexpected format: could not parse. Got: {self.cat_ptp_cgu_output}"
            )

        for i, line in enumerate(self.cat_ptp_cgu_output):
            # CGU Input Status
            match = re.match(
                r"\s*(\S+)\s*\((\d+)\)\s*\|\s*(\S+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(N/A|\S+)\s*\|",
                line,
            )
            if match and cgu:
                input_name, idx, state, eec, pps, esync_fail = match.groups()
                cgu.append_cgu_input(
                    PtpCguInputObject(
                        input_name, int(idx), state, int(eec), int(pps), esync_fail
                    )
                )

            # EEC DPLL
            match = re.match(r"EEC DPLL:", line)
            if match and cgu:
                current_ref_match = re.search(
                    r"Current reference:\s*(.*)", self.cat_ptp_cgu_output[i + 1]
                )
                status_match = re.search(
                    r"Status:\s*(.*)", self.cat_ptp_cgu_output[i + 2]
                )
                if current_ref_match and status_match:
                    cgu.set_eec_dpll(
                        PtpCguEecDpllObject(
                            current_ref_match.group(1), status_match.group(1)
                        )
                    )

            # PPS DPLL
            match = re.match(r"PPS DPLL:", line)
            if match and cgu:
                current_ref_match = re.search(
                    r"Current reference:\s*(.*)", self.cat_ptp_cgu_output[i + 1]
                )
                status_match = re.search(
                    r"Status:\s*(.*)", self.cat_ptp_cgu_output[i + 2]
                )
                phase_offset_match = re.search(
                    r"Phase offset \[ps]:\s*(.*)", self.cat_ptp_cgu_output[i + 3]
                )

                if current_ref_match and status_match and phase_offset_match:
                    cgu.set_pps_dpll(
                        PtpCguPpsDpllObject(
                            current_ref_match.group(1),
                            status_match.group(1),
                            int(phase_offset_match.group(1).replace(" ", "")),
                        )
                    )

        return cgu
