class OpenstackSecretOutput:
    """Class to parse and handle the output of 'openstack secret store' command."""

    def __init__(self, output: str):
        """
        Constructor.

        Args:
            output (str): Raw output from 'openstack secret store' command.
        """
        raw_lines = output.split("\n") if isinstance(output, str) else output
        # Strip \r and filter empty lines (from readlines() \r\n + join \n + split \n)
        self.output = [line.strip() for line in raw_lines if line.strip()]
        self._secret_href = self._parse_secret_href()

    def _parse_secret_href(self) -> str:
        """
        Parse the secret href from the command output.

        Handles multi-line values where the UUID wraps to a continuation line:
            | Secret href   | http://controller.internal:9311/v1/secrets/f105abce-69b4-    |
            |               | 4005-8c12-fa3cc9bf7af3                                       |

        Returns:
            str: The secret href URL.
        """
        href = ""
        found = False
        for line in self.output:
            if "Secret href" in line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    href = parts[2].strip()
                    found = True
            elif found and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    field_name = parts[1].strip() if len(parts) > 1 else ""
                    value = parts[2].strip()
                    # Continuation line: field name is empty, value is non-empty
                    if not field_name and value:
                        href += value
                    else:
                        break
                else:
                    break
            elif found:
                break
        return href

    def get_secret_href(self) -> str:
        """
        Get the secret href URL.

        Returns:
            str: The secret href URL.
        """
        return self._secret_href

    def get_raw_output(self) -> str:
        """
        Get the raw output from the command.

        Returns:
            str: Raw command output as string.
        """
        return "\n".join(self.output) if isinstance(self.output, list) else self.output
