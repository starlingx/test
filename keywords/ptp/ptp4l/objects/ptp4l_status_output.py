from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.ptp4l.objects.ptp4l_status_object import PTP4LStatusObject
from keywords.ptp.ptp4l.ptp4l_status_parser import PTP4LStatusParser


class PTP4LStatusOutput:
    """
    This class parses the output of Run time Options

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
        Constructor.

        Create an internal RunTimeOptionsObject from the passed parameter.

        Args:
            ptp4l_status_output (list[str]): a list of strings representing the ptp4l_status_output
        """
        ptp4l_status_parser = PTP4LStatusParser(ptp4l_status_output)
        output_values = ptp4l_status_parser.get_output_values_dict()

        self.ptp4l_status_object_list: list[PTP4LStatusObject()] = []

        for value in output_values:
            ptp4l_status_object = PTP4LStatusObject(value)
            if "Loaded" in output_values[value]:
                ptp4l_status_object.set_loaded(output_values[value]["Loaded"])
            if "Active" in output_values[value]:
                ptp4l_status_object.set_active(output_values[value]["Active"])
            if "Process" in output_values[value]:
                ptp4l_status_object.set_process(output_values[value]["Process"])
            if "Main PID" in output_values[value]:
                ptp4l_status_object.set_main_pid(output_values[value]["Main PID"])
            if "Tasks" in output_values[value]:
                ptp4l_status_object.set_tasks(output_values[value]["Tasks"])
            if "Memory" in output_values[value]:
                ptp4l_status_object.set_memory(output_values[value]["Memory"])
            if "CPU" in output_values[value]:
                ptp4l_status_object.set_cpu(output_values[value]["CPU"])
            if "CGroup" in output_values[value]:
                ptp4l_status_object.set_c_group(output_values[value]["CGroup"])
            if "command" in output_values[value]:
                ptp4l_status_object.set_command(output_values[value]["command"])
            self.ptp4l_status_object_list.append(ptp4l_status_object)

    def get_ptp4l_objects(self) -> list[PTP4LStatusObject]:
        """
        Getter for ptp4l status object.

        Returns:
            list[PTP4LStatusObject]: A PTP4LStatusObject list
        """
        return self.ptp4l_status_object_list

    def get_ptp4l_object(self, service_name: str) -> PTP4LStatusObject:
        """
        Getter for ptp4l object with the given service name

        Args:
            service_name (str): the name of the service (e.g., "phc1")

        Returns:
            PTP4LStatusObject: the PTP4LStatusObject with the given service name

        Raises:
            KeywordException: if no service with the given name is found or if more than one service with the given name is found.
        """
        service_list = list(filter(lambda service: service.get_service_name() == service_name, self.ptp4l_status_object_list))
        if len(service_list) == 1:
            return service_list[0]
        else:  # should never be more than one but this will check anyway
            raise KeywordException(f"Found {len(service_list)} service(s) with the service name: {service_name}.")
