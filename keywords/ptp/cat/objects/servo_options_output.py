from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.servo_options_object import ServoOptionsObject


class ServoOptionsOutput:
    """
    This class parses the output of Servo Options

    Example:
        pi_proportional_const   0.0
        pi_integral_const       0.0
        pi_proportional_scale   0.0
        pi_proportional_exponent        -0.3
        pi_proportional_norm_max        0.7
        pi_integral_scale       0.0
        pi_integral_exponent    0.4
        pi_integral_norm_max    0.3
        step_threshold          0.0
        first_step_threshold    0.00002
        max_frequency           900000000
        clock_servo             pi
        sanity_freq_limit       200000000
        ntpshm_segment          0
        msg_interval_request    0
        servo_num_offset_values 10
        servo_offset_threshold  0
        write_phase_mode        0

    """

    def __init__(self, servo_options_output: list[str]):
        """
        Create an internal ServoOptionsObject from the passed parameter.

        Args:
            servo_options_output (list[str]): a list of strings representing the servo options output
        """
        cat_ptp_table_parser = CatPtpTableParser(servo_options_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.servo_options_object = ServoOptionsObject()

        if "pi_proportional_const" in output_values:
            self.servo_options_object.set_pi_proportional_const(float(output_values["pi_proportional_const"]))

        if "pi_integral_const" in output_values:
            self.servo_options_object.set_pi_integral_const(float(output_values["pi_integral_const"]))

        if "pi_proportional_scale" in output_values:
            self.servo_options_object.set_pi_proportional_scale(float(output_values["pi_proportional_scale"]))

        if "pi_proportional_exponent" in output_values:
            self.servo_options_object.set_pi_proportional_exponent(float(output_values["pi_proportional_exponent"]))

        if "pi_proportional_norm_max" in output_values:
            self.servo_options_object.set_pi_proportional_norm_max(float(output_values["pi_proportional_norm_max"]))

        if "pi_integral_scale" in output_values:
            self.servo_options_object.set_pi_integral_scale(float(output_values["pi_integral_scale"]))

        if "pi_integral_exponent" in output_values:
            self.servo_options_object.set_pi_integral_exponent(float(output_values["pi_integral_exponent"]))

        if "pi_integral_norm_max" in output_values:
            self.servo_options_object.set_pi_integral_norm_max(float(output_values["pi_integral_norm_max"]))

        if "step_threshold" in output_values:
            self.servo_options_object.set_step_threshold(float(output_values["step_threshold"]))

        if "first_step_threshold" in output_values:
            self.servo_options_object.set_first_step_threshold(float(output_values["first_step_threshold"]))

        if "max_frequency" in output_values:
            self.servo_options_object.set_max_frequency(int(output_values["max_frequency"]))

        if "clock_servo" in output_values:
            self.servo_options_object.set_clock_servo(output_values["clock_servo"])

        if "sanity_freq_limit" in output_values:
            self.servo_options_object.set_sanity_freq_limit(int(output_values["sanity_freq_limit"]))

        if "ntpshm_segment" in output_values:
            self.servo_options_object.set_ntpshm_segment(int(output_values["ntpshm_segment"]))

        if "msg_interval_request" in output_values:
            self.servo_options_object.set_msg_interval_request(int(output_values["msg_interval_request"]))

        if "servo_num_offset_values" in output_values:
            self.servo_options_object.set_servo_num_offset_values(int(output_values["servo_num_offset_values"]))

        if "servo_offset_threshold" in output_values:
            self.servo_options_object.set_servo_offset_threshold(int(output_values["servo_offset_threshold"]))

        if "write_phase_mode" in output_values:
            self.servo_options_object.set_write_phase_mode(int(output_values["write_phase_mode"]))

    def get_servo_options_object(self) -> ServoOptionsObject:
        """
        Getter for servo_options_object object.

        Returns:
            ServoOptionsObject: The servo options object containing parsed values.
        """
        return self.servo_options_object
