from keywords.cloud_platform.system.application.object.system_application_show_object import SystemApplicationShowObject


class SystemApplicationShowOutput:
    """
    Parses the output from the 'system application-show <app_name>' command

    Methods:
        get_system_application_object(): Returns the parsed system application object
    """

    def __init__(self, raw_output: str | list):
        """
        Initialize with raw output and parse it.

        Args:
            raw_output (str | list): The raw command output from the system
        """
        if isinstance(raw_output, list):
            raw_output = "".join(raw_output)
        self.raw_output = raw_output
        self.application_object = self._parse_output(self.raw_output)

    def _parse_output(self, output: str) -> SystemApplicationShowObject:
        """
        Parses the CLI output into a SystemApplicationShowObject

        Args:
            output (str): Raw command output

        Returns:
            SystemApplicationShowObject: Parsed application data
        """
        app_obj = SystemApplicationShowObject()
        for line in output.strip().splitlines():
            if "|" not in line or "Property" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) == 2:
                key = parts[0].lower().replace(" ", "_")
                value = parts[1]
                app_obj.set_property(key, value)
        return app_obj

    def get_system_application_object(self) -> SystemApplicationShowObject:
        """
        Returns the parsed system application object

        Returns:
            SystemApplicationShowObject: The application object containing parsed data
        """
        return self.application_object
