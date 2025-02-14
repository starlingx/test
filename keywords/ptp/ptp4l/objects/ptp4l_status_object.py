class PTP4LStatusObject:
    """Represents system resource information.

    Attributes:
        service_name (str): the name of the service
        loaded (str): The loading status of the resource.
        active (str): The active status of the resource.
        main_pid (str): The main process ID associated with the resource.
        tasks (str): Information about the tasks related to the resource.
        memory (str): Memory usage information.
        cpu (str): CPU usage information.
        c_group (str): The C group the resource belongs to.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.loaded: str = ''
        self.active: str = ''
        self.process: str = ''
        self.main_pid: str = ''
        self.tasks: str = ''
        self.memory: str = ''
        self.cpu: str = ''
        self.c_group: str = ''
        self.command: str = ''

    def get_service_name(self) -> str:
        """Gets the service_name.

        Returns:
            The service_name.
        """
        return self.service_name

    def set_service_name(self, service_name: str) -> None:
        """Sets service_name.

        Args:
            service_name: The new loading status.
        """
        self.service_name = service_name

    def get_loaded(self) -> str:
        """Gets the loading status.

        Returns:
            The loading status.
        """
        return self.loaded

    def set_loaded(self, loaded: str) -> None:
        """Sets the loading status.

        Args:
            loaded: The new loading status.
        """
        self.loaded = loaded

    def get_active(self) -> str:
        """Gets the active status.

        Returns:
            The active status.
        """
        return self.active

    def set_active(self, active: str) -> None:
        """Sets the active status.

        Args:
            active: The new active status.
        """
        self.active = active

    def get_main_pid(self) -> str:
        """Gets the main process ID.

        Returns:
            The main process ID.
        """
        return self.main_pid

    def set_main_pid(self, main_pid: str) -> None:
        """Sets the main process ID.

        Args:
            main_pid: The new main process ID.
        """
        self.main_pid = main_pid

    def get_tasks(self) -> str:
        """Gets the tasks information.

        Returns:
            The tasks information.
        """
        return self.tasks

    def set_tasks(self, tasks: str) -> None:
        """Sets the tasks information.

        Args:
            tasks: The new tasks information.
        """
        self.tasks = tasks

    def get_memory(self) -> str:
        """Gets the memory information.

        Returns:
            The memory information.
        """
        return self.memory

    def set_memory(self, memory: str) -> None:
        """Sets the memory information.

        Args:
            memory: The new memory information.
        """
        self.memory = memory

    def get_cpu(self) -> str:
        """Gets the CPU information.

        Returns:
            The CPU information.
        """
        return self.cpu

    def set_cpu(self, cpu: str) -> None:
        """Sets the CPU information.

        Args:
            cpu: The new CPU information.
        """
        self.cpu = cpu

    def get_c_group(self) -> str:
        """Gets the C group.

        Returns:
            The C group.
        """
        return self.c_group

    def set_c_group(self, c_group: str) -> None:
        """Sets the C group.

        Args:
            c_group: The new C group.
        """
        self.c_group = c_group

    def get_command(self) -> str:
        """Gets the command.

        Returns:
            The command.
        """
        return self.command

    def set_command(self, command: str) -> None:
        """Sets the command.

        Args:
            command: The new command.
        """
        self.command = command

    def get_process(self) -> str:
        """Gets the process.

        Returns:
            The process.
        """
        return self.process

    def set_process(self, process: str) -> None:
        """Sets the process.

        Args:
            process: The new process.
        """
        self.process = process


