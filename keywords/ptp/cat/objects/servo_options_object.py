class ServoOptionsObject:
    """Object to hold the values of Servo Options Options"""

    def __init__(self):
        self.pi_proportional_const: float = None
        self.pi_integral_const: float = None
        self.pi_proportional_scale: float = None
        self.pi_proportional_exponent: float = None
        self.pi_proportional_norm_max: float = None
        self.pi_integral_scale: float = None
        self.pi_integral_exponent: float = None
        self.pi_integral_norm_max: float = None
        self.step_threshold: float = None
        self.first_step_threshold: float = None
        self.max_frequency: int = None
        self.clock_servo: str = ""
        self.sanity_freq_limit: int = -1
        self.ntpshm_segment: int = -1
        self.msg_interval_request: int = -1
        self.servo_num_offset_values: int = -1
        self.servo_offset_threshold: int = -1
        self.write_phase_mode: int = -1

    def get_pi_proportional_const(self) -> float:
        """
        Getter for pi_proportional

        Returns:
            float: the pi_proportional_const value
        """
        return self.pi_proportional_const

    def set_pi_proportional_const(self, pi_proportional_const: float) -> None:
        """
        Setter for pi_proportional_const

        Args:
            pi_proportional_const (float): the pi_proportional_const value
        """
        self.pi_proportional_const = pi_proportional_const

    def get_pi_integral_const(self) -> float:
        """
        Getter for pi_integral_const

        Returns:
            float: the pi_integral_const value
        """
        return self.pi_integral_const

    def set_pi_integral_const(self, pi_integral_const: float) -> None:
        """
        Setter for pi_integral_const

        Args:
            pi_integral_const (float): pi_integral_const value
        """
        self.pi_integral_const = pi_integral_const

    def get_pi_proportional_scale(self) -> float:
        """
        Getter for pi_proportional_scale

        Returns:
            float: the pi_proportional_scale value
        """
        return self.pi_proportional_scale

    def set_pi_proportional_scale(self, pi_proportional_scale: float) -> None:
        """
        Setter for pi_proportional_scale

        Args:
            pi_proportional_scale (float): pi_proportional_scale value
        """
        self.pi_proportional_scale = pi_proportional_scale

    def get_pi_proportional_exponent(self) -> float:
        """
        Getter for pi_proportional_exponent

        Returns:
            float: the pi_proportional_exponent value
        """
        return self.pi_proportional_exponent

    def set_pi_proportional_exponent(self, pi_proportional_exponent: float) -> None:
        """
        Setter for pi_proportional_exponent

        Args:
            pi_proportional_exponent (float): the pi_proportional_exponent value
        """
        self.pi_proportional_exponent = pi_proportional_exponent

    def get_pi_proportional_norm_max(self) -> float:
        """
        Getter for pi_proportional_norm_max

        Returns:
            float: the pi_proportional_norm_max value
        """
        return self.pi_proportional_norm_max

    def set_pi_proportional_norm_max(self, pi_proportional_norm_max: float) -> None:
        """
        Setter for pi_proportional_norm_max

        Args:
            pi_proportional_norm_max (float): the pi_proportional_norm_max value
        """
        self.pi_proportional_norm_max = pi_proportional_norm_max

    def get_pi_integral_scale(self) -> float:
        """
        Getter for pi_integral_scale

        Returns:
            float: the pi_integral_scale value
        """
        return self.pi_integral_scale

    def set_pi_integral_scale(self, pi_integral_scale: float) -> None:
        """
        Setter for pi_integral_scale

        Args:
            pi_integral_scale (float): the pi_integral_scale value
        """
        self.pi_integral_scale = pi_integral_scale

    def get_pi_integral_exponent(self) -> float:
        """
        Getter for pi_integral_exponent

        Returns:
            float: pi_integral_exponent value
        """
        return self.pi_integral_exponent

    def set_pi_integral_exponent(self, pi_integral_exponent: float) -> None:
        """
        Setter for pi_integral_exponent

        Args:
            pi_integral_exponent (float): the pi_integral_exponent value
        """
        self.pi_integral_exponent = pi_integral_exponent

    def get_pi_integral_norm_max(self) -> float:
        """
        Getter for pi_integral_norm_max

        Returns:
            float: the pi_integral_norm_max value
        """
        return self.pi_integral_norm_max

    def set_pi_integral_norm_max(self, pi_integral_norm_max: float) -> None:
        """
        Setter for pi_integral_norm_max

        Args:
            pi_integral_norm_max (float): the pi_integral_norm_max value
        """
        self.pi_integral_norm_max = pi_integral_norm_max

    def get_step_threshold(self) -> float:
        """
        Getter for step_threshold

        Returns:
            float: the step_threshold value
        """
        return self.step_threshold

    def set_step_threshold(self, step_threshold: float) -> None:
        """
        Setter for step_threshold

        Args:
            step_threshold (float): the step_threshold value
        """
        self.step_threshold = step_threshold

    def get_first_step_threshold(self) -> float:
        """
        Getter for first_step_threshold

        Returns:
            float: the first_step_threshold value
        """
        return self.first_step_threshold

    def set_first_step_threshold(self, first_step_threshold: float) -> None:
        """
        Setter for first_step_threshold

        Args:
            first_step_threshold (float): the first_step_threshold value
        """
        self.first_step_threshold = first_step_threshold

    def get_max_frequency(self) -> int:
        """
        Getter for max_frequency

        Returns:
            int: the max_frequency value
        """
        return self.max_frequency

    def set_max_frequency(self, max_frequency: int) -> None:
        """
        Setter for max_frequency

        Args:
            max_frequency (int): the max_frequency value
        """
        self.max_frequency = max_frequency

    def get_clock_servo(self) -> str:
        """
        Getter for clock_servo

        Returns:
            str: the clock_servo value
        """
        return self.clock_servo

    def set_clock_servo(self, clock_servo: str) -> None:
        """
        Setter for clock_servo

        Args:
            clock_servo (str): the clock_servo value
        """
        self.clock_servo = clock_servo

    def get_sanity_freq_limit(self) -> int:
        """
        Getter for sanity_freq_limit

        Returns:
            int: the sanity_freq_limit value
        """
        return self.sanity_freq_limit

    def set_sanity_freq_limit(self, sanity_freq_limit: int) -> None:
        """
        Setter for sanity_freq_limit

        Args:
            sanity_freq_limit (int): the sanity_freq_limit value
        """
        self.sanity_freq_limit = sanity_freq_limit

    def get_ntpshm_segment(self) -> int:
        """
        Getter for ntpshm_segment

        Returns:
            int: the ntpshm_segment value
        """
        return self.ntpshm_segment

    def set_ntpshm_segment(self, ntpshm_segment: int) -> None:
        """
        Setter for ntpshm_segment

        Args:
            ntpshm_segment (int): the ntpshm_segment value
        """
        self.ntpshm_segment = ntpshm_segment

    def get_msg_interval_request(self) -> int:
        """
        Getter for msg_interval_request

        Returns:
            int: the msg_interval_request value
        """
        return self.msg_interval_request

    def set_msg_interval_request(self, msg_interval_request: int) -> None:
        """
        Setter for msg_interval_request

        Args:
            msg_interval_request (int): the msg_interval_request value
        """
        self.msg_interval_request = msg_interval_request

    def get_servo_num_offset_values(self) -> int:
        """
        Getter for servo_num_offset_values

        Returns:
            int: the servo_num_offset_values value
        """
        return self.servo_num_offset_values

    def set_servo_num_offset_values(self, servo_num_offset_values: int) -> None:
        """
        Setter for servo_num_offset_values

        Args:
            servo_num_offset_values (int): the servo_num_offset_values value
        """
        self.servo_num_offset_values = servo_num_offset_values

    def get_servo_offset_threshold(self) -> int:
        """
        Getter for servo_offset_threshold

        Returns:
            int: the servo_offset_threshold value
        """
        return self.servo_offset_threshold

    def set_servo_offset_threshold(self, servo_offset_threshold: int) -> None:
        """
        Setter for servo_offset_threshold

        Args:
            servo_offset_threshold (int): the servo_offset_threshold value
        """
        self.servo_offset_threshold = servo_offset_threshold

    def get_write_phase_mode(self) -> int:
        """
        Getter for write_phase_mode

        Returns:
            int: the write_phase_mode value
        """
        return self.write_phase_mode

    def set_write_phase_mode(self, write_phase_mode: int) -> None:
        """
        Setter for write_phase_mode

        Args:
            write_phase_mode (int): the write_phase_mode value
        """
        self.write_phase_mode = write_phase_mode
