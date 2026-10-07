class SystemHostKernelShowObject:
    """
    This class represents a Host Kernel as an object.

    """

    def __init__(self):
        self.hostname = None
        self.kernel_provisioned = None
        self.kernel_running = None

    def set_hostname(self, hostname: str):
        """Setter for hostname"""
        self.hostname = hostname

    def get_hostname(self) -> str:
        """Getter for hostname"""
        return self.hostname

    def set_kernel_provisioned(self, kernel_provisioned: str):
        """Setter for kernel_provisioned"""
        self.kernel_provisioned = kernel_provisioned

    def get_kernel_provisioned(self) -> str:
        """Getter for kernel_provisioned"""
        return self.kernel_provisioned

    def set_kernel_running(self, kernel_running: str):
        """Setter for kernel_running"""
        self.kernel_running = kernel_running

    def get_kernel_running(self) -> str:
        """Getter for kernel_running"""
        return self.kernel_running

    def is_lowlatency(self) -> bool:
        """Return True if the running kernel is the lowlatency/real-time kernel.

        host-kernel-show reports the kernel TYPE ('standard' | 'lowlatency')
        Returns:
            bool: True if the running kernel type is 'lowlatency'.
        """
        return self.kernel_running is not None and self.kernel_running.lower() == "lowlatency"
