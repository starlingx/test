class ValidationResponse:
    """
    Class that models the response from a ValidationWithRetry.

    The purpose of this object is to store a return value as well as a value to validate.
    """

    def __init__(self, value_to_validate: object, value_to_return: object):
        """
        Constructor for ValidationResponse

        Args:
            value_to_validate (object): What we want to validate.
            value_to_return (object): The object that we want to return if the validation is successful.
        """
        self.value_to_validate: object = value_to_validate
        self.value_to_return: object = value_to_return

    def get_value_to_validate(self) -> object:
        """
        Getter for the value to validate
        """
        return self.value_to_validate

    def get_value_to_return(self) -> object:
        """
        Getter for the value to return
        """
        return self.value_to_return
