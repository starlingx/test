from framework.validation.validation import validate_equals_with_retry
from keywords.ptp.pmc.pmc_keywords import PMCKeywords


class PTPReadinessKeywords:
    """
    PMC (PTP Management Client) operations to check various PTP parameters with retry logic.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the PTPReadinessKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def wait_for_port_state_appear_in_port_data_set(self, name: str, hostname: str, expected_port_states: list[str]) -> None:
        """
        Waits until the port states observed in the port data set match the expected states, or times out.

        Args:
            name (str): Name of the PTP instance.
            hostname (str): Hostname of the target system.
            expected_port_states (list[str]): List of expected port states to wait for.

        Raises:
            Exception: If expected port states do not appear within the timeout.
        """

        def check_port_state_in_port_data_set(name: str) -> list[str]:
            """
            Checks whether the observed port states from the port data set match the expected port states.

            Args:
                name (str): Name of the PTP instance.

            Returns:
                list[str]: List of expected port states.
            """
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"

            pmc_keywords = PMCKeywords(self.ssh_connection)

            observed_states = [obj.get_port_state() for obj in pmc_keywords.pmc_get_port_data_set(config_file, socket_file).get_pmc_get_port_data_set_objects()]

            return observed_states

        validate_equals_with_retry(lambda: check_port_state_in_port_data_set(name, hostname), expected_port_states, "port state in port data set", 120, 30)

    def wait_for_clock_class_appear_in_grandmaster_settings_np(self, name: str, hostname: str, expected_clock_class: int) -> None:
        """
        Waits until the clock class observed in the grandmaster settings np match the expected clock class, or times out.

        Args:
            name (str): Name of the PTP instance.
            hostname (str): Hostname of the target system.
            expected_clock_class (int): expected clock class to wait for.

        Raises:
            Exception: If expected clock class do not appear within the timeout.
        """

        def get_clock_class_in_grandmaster_settings_np(name: str) -> int:
            """
            Get the observed clock class from the grandmaster settings np.

            Args:
                name (str): Name of the PTP instance.

            Returns:
                int: observed clock class.
            """
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"

            pmc_keywords = PMCKeywords(self.ssh_connection)

            get_grandmaster_settings_np_object = pmc_keywords.pmc_get_grandmaster_settings_np(config_file, socket_file).get_pmc_get_grandmaster_settings_np_object()
            observed_clock_class = get_grandmaster_settings_np_object.get_clock_class()

            return observed_clock_class

        validate_equals_with_retry(lambda: get_clock_class_in_grandmaster_settings_np(name, hostname), expected_clock_class, "clock class in grandmaster settings np", 120, 30)

    def wait_for_gm_clock_class_appear_in_parent_data_set(self, name: str, hostname: str, expected_gm_clock_class: int) -> None:
        """
        Waits until the gm clock class observed in the parent data set match the expected clock class, or times out.

        Args:
            name (str): Name of the PTP instance.
            hostname (str): Hostname of the target system.
            expected_gm_clock_class (int): expected gm clock class to wait for.

        Raises:
            Exception: If expected gm clock class do not appear within the timeout.
        """

        def get_gm_clock_class_in_parent_data_set(name: str) -> int:
            """
            Get the observed gm clock class from the parent data set.

            Args:
                name (str): Name of the PTP instance.

            Returns:
                int: observed gm clock class.
            """
            config_file = f"/etc/linuxptp/ptpinstance/ptp4l-{name}.conf"
            socket_file = f"/var/run/ptp4l-{name}"

            pmc_keywords = PMCKeywords(self.ssh_connection)

            parent_data_set_obj = pmc_keywords.pmc_get_parent_data_set(config_file, socket_file).get_pmc_get_parent_data_set_object()
            observed_gm_clock_class = parent_data_set_obj.get_gm_clock_class()

            return observed_gm_clock_class

        validate_equals_with_retry(lambda: get_gm_clock_class_in_parent_data_set(name, hostname), expected_gm_clock_class, "gm clock class in parent data set", 120, 30)
