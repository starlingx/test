class PromptResponse:
    """
    This class is a holder for a Prompt's text content and the associated
    response that we want to send.
    """

    def __init__(self, prompt_substring, prompt_response=None):
        """
        Constructor
        Args:
            prompt_substring: Substring indicating that we have the right prompt.
            prompt_response: Answer that we send when we encounter this prompt.
                             If set to None, that means that we don't want to respond to the prompt.
        """

        self.prompt_substring = prompt_substring
        self.prompt_response = prompt_response

        # Store the full ssh output up to this prompt. [Since the last prompt]
        self.complete_output = ""

    def get_prompt_substring(self) -> str:
        """
        Getter for prompt substring
        Returns (str): prompt substring

        """
        return self.prompt_substring

    def get_prompt_response(self) -> str:
        """
        Getter for the prompt response
        Returns (str): prompt response

        """
        return self.prompt_response

    def set_complete_output(self, complete_output: str):
        """
        Setter for the complete output.
        Args:
            complete_output: The full ssh output up to this prompt. [Since the last prompt]

        Returns:c None

        """
        self.complete_output = complete_output

    def get_complete_output(self) -> str:
        """
        Getter for the complete ssh output that led to this prompt.
        Returns (str): The complete ssh output that led to this prompt. [Since the last prompt]

        """
        return self.complete_output
