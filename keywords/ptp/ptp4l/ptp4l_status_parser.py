class PTP4LStatusParser:
    """
    Class for PTP4LStatusParser

    Example:
    ● ptp4l@ptp1.service - Precision Time Protocol (PTP) service
         Loaded: loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)
         Active: active (running) since Mon 2025-02-10 18:36:34 UTC; 3 days ago
         Main PID: 15221 (ptp4l)
         Tasks: 1 (limit: 150897)
         Memory: 336.0K
           CPU: 1min 33.917s
         CGroup: /system.slice/system-ptp4l.slice/ptp4l@ptp1.service
           └─15221 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp1.conf

    ● ptp4l@ptp3.service - Precision Time Protocol (PTP) service
         Loaded: loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)
         Active: active (running) since Wed 2025-02-12 16:22:23 UTC; 2 days ago
         Process: 3816049 ExecStartPost=/bin/bash -c echo $MAINPID > /var/run/ptp4l-ptp3.pid (code=exited, status=0/SUCCESS)
         Main PID: 3816048 (ptp4l)
         Tasks: 1 (limit: 150897)
         Memory: 328.0K
           CPU: 38.984s
         CGroup: /system.slice/system-ptp4l.slice/ptp4l@ptp3.service
           └─3816048 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp3.conf
    """

    def __init__(self, ptp4l_status_output: list[str]):
        """
        Constructor

        Args:
            ptp4l_status_output (list[str]): a list of strings representing the output of a systemctl status <>.
        """
        self.ptp4l_status_output = ptp4l_status_output

    def get_output_values_dict(self) -> dict[str, dict[str, str]]:
        """
        Getter for output values dict

        Returns:
            dict[str, dict[str, str]]: the output values dict
        """
        services = {}
        current_service = None
        for line in self.ptp4l_status_output:
            line = line.strip()
            if line.startswith("●"):  # we have a new service to get values for
                service_name = line.split("@")[1].split(" ")[0].replace(".service", "")  # format ptp4l@ptp1.service - Precision Time Protocol (PTP) service
                services[service_name] = {}
                current_service = services[service_name]
            elif line.startswith("└─") and current_service is not None:
                current_service["command"] = line[2:].strip()  # we have a special case with the └─  which maps to the command to start the service
            elif current_service is not None:
                parts = line.split(":", 1)  # parse the rest using the first : to make key value pairs
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                current_service[key] = value

        return services
