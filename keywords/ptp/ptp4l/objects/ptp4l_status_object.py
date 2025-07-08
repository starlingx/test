class PTP4LStatusObject:
    """
    Represents system resource information for a PTP4L service.
    """

    def __init__(self, service_name: str):
        """
        Initializes a new PTP4LStatusObject instance with default values.

        Args:
            service_name (str): The name of the PTP4L service (e.g., "phc1").

        Attributes:
            service_name (str): the name of the service
            loaded (str): The loading status of the resource.
            active (str): The active status of the resource.
            process (str): The process associated with the resource.
            main_pid (str): The main process ID associated with the resource.
            tasks (str): Information about the tasks related to the resource.
            memory (str): Memory usage information.
            cpu (str): CPU usage information.
            c_group (str): The C group the resource belongs to.
            command (str): The command used to start the resource.
        """
        self.service_name = service_name
        self.loaded: str = ""
        self.active: str = ""
        self.process: str = ""
        self.main_pid: str = ""
        self.tasks: str = ""
        self.memory: str = ""
        self.cpu: str = ""
        self.c_group: str = ""
        self.command: str = ""

    def get_service_name(self) -> str:
        """Gets the service_name.

        Returns:
            str: The service_name.
        """
        return self.service_name

    def set_service_name(self, service_name: str) -> None:
        """Sets service_name.

        Args:
            service_name (str): The new loading status.

        Returns:
            None: This method does not return anything.
        """
        self.service_name = service_name

    def get_loaded(self) -> str:
        """Gets the loading status.

        Returns:
            str: The loading status.
        """
        return self.loaded

    def set_loaded(self, loaded: str) -> None:
        """Sets the loading status.

        Args:
            loaded (str): The new loading status.

        Returns:
            None: This method does not return anything.
        """
        self.loaded = loaded

    def get_active(self) -> str:
        """Gets the active status.

        Returns:
            str: The active status.
        """
        return self.active

    def set_active(self, active: str) -> None:
        """Sets the active status.

        Args:
            active (str): The new active status.

        Returns:
            None: This method does not return anything.
        """
        self.active = active

    def get_main_pid(self) -> str:
        """Gets the main process ID.

        Returns:
            str: The main process ID.
        """
        return self.main_pid

    def set_main_pid(self, main_pid: str) -> None:
        """Sets the main process ID.

        Args:
            main_pid (str): The new main process ID.

        Returns:
            None: This method does not return anything.
        """
        self.main_pid = main_pid

    def get_tasks(self) -> str:
        """Gets the tasks information.

        Returns:
            str: The tasks information.
        """
        return self.tasks

    def set_tasks(self, tasks: str) -> None:
        """Sets the tasks information.

        Args:
            tasks (str): The new tasks information.

        Returns:
            None: This method does not return anything.
        """
        self.tasks = tasks

    def get_memory(self) -> str:
        """Gets the memory information.

        Returns:
            str: The memory information.
        """
        return self.memory

    def set_memory(self, memory: str) -> None:
        """Sets the memory information.

        Args:
            memory (str): The new memory information.

        Returns:
            None: This method does not return anything.
        """
        self.memory = memory

    def get_cpu(self) -> str:
        """Gets the CPU information.

        Returns:
            str: The CPU information.
        """
        return self.cpu

    def set_cpu(self, cpu: str) -> None:
        """Sets the CPU information.

        Args:
            cpu (str): The new CPU information.

        Returns:
            None: This method does not return anything.
        """
        self.cpu = cpu

    def get_c_group(self) -> str:
        """Gets the C group.

        Returns:
            str: The C group.
        """
        return self.c_group

    def set_c_group(self, c_group: str) -> None:
        """Sets the C group.

        Args:
            c_group (str): The new C group.

        Returns:
            None: This method does not return anything.
        """
        self.c_group = c_group

    def get_command(self) -> str:
        """Gets the command.

        Returns:
            str: The command.
        """
        return self.command

    def set_command(self, command: str) -> None:
        """Sets the command.

        Args:
            command (str): The new command.

        Returns:
            None: This method does not return anything.
        """
        self.command = command

    def get_process(self) -> str:
        """Gets the process.

        Returns:
            str: The process.
        """
        return self.process

    def set_process(self, process: str) -> None:
        """Sets the process.

        Args:
            process (str): The new process.

        Returns:
            None: This method does not return anything.
        """
        self.process = process
