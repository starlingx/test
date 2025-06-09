class SoftwareUploadObject:
    """Class to hold attributes of a software upload as returned by software upload command"""

    def __init__(self, uploaded_file: str, release: str) -> None:
        """Initializes a SoftwareUploadObject with the uploaded file and release."""
        self.uploaded_file = uploaded_file
        self.release = release

    def get_uploaded_file(self) -> str:
        """Getter for uploaded_file.

        Returns:
            str: the uploaded file name
        """
        return self.uploaded_file

    def get_release(self) -> str:
        """Getter for release.

        Returns:
            str: the release name
        """
        return self.release
