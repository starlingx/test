import re


class SystemHealthQueryParser:
    """
    Class for System health-query parsing.

    In health-query output, health checks and their corresponding status are arranged in
    structured text, with each check listed alongside its status.

    As an example of a typical argument for the constructor of this class,
    consider the output of the command 'system health-query-kube-upgrade':

    ```
    System Health:
    All hosts are provisioned: [OK]
    All hosts are unlocked/enabled: [OK]
    All hosts have current configurations: [OK]
    All hosts are patch current: [OK]
    Ceph Storage Healthy: [OK]
    No alarms: [OK]
    All kubernetes nodes are ready: [OK]
    All kubernetes control plane pods are ready: [OK]
    All kubernetes applications are in a valid state: [OK]
    ```
    """

    def __init__(self, health_query_output: list[str]) -> None:
        """
        Constructor

        Args:
            health_query_output (list[str]): A list of strings representing the output of a 'system health-query*' command.
        """
        self.health_query_output = health_query_output

    def get_output_values_dict(self) -> dict:
        """Retrieves the output values from health query output as a dictionary.

        This method parses the health check content and returns it as a dictionary.
        Each key-value pair corresponds to a health check name and its status.

        Returns:
            dict: A dictionary representation of the parsed health check content.
        """
        output_values_dict = {}

        # Iterate through each line of the health query output
        for i, line in enumerate(self.health_query_output):
            line = line.strip()

            # Look for lines matching the pattern "Check name: [Status]"
            if ": [" in line and line.endswith("]"):
                # Use regex to extract check name and status
                match = re.match(r"^(.+): \[(.+)\]$", line)
                if match:
                    check_name = match.group(1).strip()
                    status = match.group(2).strip()

                    # Store the check name and status in the dictionary
                    output_values_dict[check_name] = {"status": status}

                    # If status is Fail and there's a next line, include it as reason
                    if status == "Fail" and i + 1 < len(self.health_query_output):
                        next_line = self.health_query_output[i + 1].strip()
                        if next_line and not (": [" in next_line and next_line.endswith("]")):
                            output_values_dict[check_name]["reason"] = next_line

        return output_values_dict
