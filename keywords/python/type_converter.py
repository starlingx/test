class TypeConverter:
    """
    This class contains static utility methods for converting between types.
    """

    @staticmethod
    def parse_string_to_dict(string: str, separator_char: str = "=") -> dict[str, str]:
        """
        Converts a string representation of key-value pairs into a dictionary.

        This function converts a string in the format "key_1<separator_char>value_1, key_2<separator_char>value_2,...
        key_n<separator_char>value_n" in a dictionary in the following format:
        {"key_1": value_1, "key_2": value_2 ... "key_n": value_n}.

        Note: this function will try to convert numeric and boolean values to its correct type.

        Args:
            string (str): a string in the following format: "key_1 <separator_char> value_1,
                key_2 <separator_char> value_2, ... key_n <separator_char> value_n"
            separator_char (str): the character used to separate key from value in the <string>.
                If not provided, the default value is '='.

        Returns:
            dict[str, str]: a dictionary in the following format: {"key_1": value_1, "key_2": value_2 ... "key_n": value_n}
        """
        result = {}

        clean_string = string.replace("{", "").replace("}", "").replace("'", "")
        pairs = clean_string.split(",")

        for pair in pairs:
            key, value = pair.split(separator_char)
            key = key.strip()
            value = value.strip()

            if TypeConverter.is_number(value):
                result[key] = int(value) if value.isdigit() else float(value)
            elif TypeConverter.is_boolean(value):
                result[key] = bool(value)
            else:
                result[key] = value

        return result

    @staticmethod
    def parse_string_to_list(string: str) -> list[str]:
        """
        Converts a string representation of a list into an actual list.

        This function converts a string in the format "['value_1, value_2 ... value_n']" in a list of string in
        the following format: ["value_1", "value_2" ... "value_n"].

        Args:
            string (str): a string in the following format: "['value_1, value_2 ... value_n']"

        Returns:
            list[str]: a list of string in the following format: ["value_1", "value_2" ... "value_n"]
        """
        if string is None or string == "[]":
            return []

        cleaned_str = string.strip("[]").strip()

        if not cleaned_str:
            return []

        items = [item.strip().strip("'\"") for item in cleaned_str.split(",")]

        return items

    @staticmethod
    def is_int(string: str) -> bool:
        """
        This function verifies if <string> represents an integer number.

        Args:
            string (str): a string that one wants to verify to see if it represents an integer number.

        Returns:
            bool: True if <string> represents an integer number, and False otherwise.

        Raises:
            TypeError: If the input is not a string.
        """
        if not isinstance(string, str):
            raise TypeError(f"The argument passed <{string}> is not of type str.")

        return string.isdigit()

    @staticmethod
    def is_float(string: str) -> bool:
        """
        This function verifies if <string> represents a float point number.

        Args:
            string (str): a string that one wants to verify to see if it represents a floating-point number.

        Returns:
            bool: True if <string> represents a float point number, and False otherwise.

        Raises:
            TypeError: If the input is not a string.
        """
        if not isinstance(string, str):
            raise TypeError(f"The argument passed <{string}> is not of type str.")

        return string.replace(".", "", 1).isdigit() and string.count(".") < 2

    @staticmethod
    def is_number(string: str) -> bool:
        """
        This function verifies if <string> represents an integer or float point number.

        Args:
            string (str) : a string that one wants to verify to see if it represents an integer or a floating-point number.

        Returns:
            bool: True if <string> represents an integer or float point number, and False otherwise.
        """
        return TypeConverter.is_int(string) or TypeConverter.is_float(string)

    @staticmethod
    def is_boolean(string: str) -> bool:
        """
        This function verifies if <string> represents a boolean value.

        Args:
            string (str) : a string that one wants to verify to see if it represents a boolean value.

        Returns:
            bool: True if <string> represents a boolean value, and False otherwise.

        Raises:
            TypeError: If the input is not a string.
        """
        if not isinstance(string, str):
            raise TypeError(f"The argument passed <{string}> is not of type str.")

        string_upper = string.upper()
        return string_upper == "TRUE" or string_upper == "FALSE"

    @staticmethod
    def str_to_bool(string: str) -> bool:
        """
        This function converts a string passed as an argument to its corresponding boolean value.

        Args:
            string (str): A string that one wants to convert to its corresponding boolean value.

        Returns:
            bool: True if <string> represents a True boolean value or False if <string> represents
            a False boolean value.

        Raises:
            TypeError: If the input is not a string.
            ValueError: If the string does not represent a valid boolean case-insensitive value ('true' or 'false').
        """
        if not isinstance(string, str):
            raise TypeError(f"The argument passed <{string}> is not of type str.")

        if not TypeConverter.is_boolean(string):
            raise (ValueError(f"The value {string} cannot be converted to bool because it does not represent a boolean value."))

        return string.upper() == "TRUE"
