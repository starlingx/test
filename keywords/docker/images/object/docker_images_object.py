class DockerImagesObject:
    """
    Class to hold attributes of a 'docker images' namespace entry.
    """

    def __init__(self, repository: str):
        """
        Constructor
        Args:
            repository: repository of the image.
        """

        self.repository = repository
        self.tag = None
        self.image_id = None
        self.created = None
        self.size = None

    def get_repository(self) -> str:
        """
        Getter for repository entry
        Returns: The repository

        """
        return self.repository

    def set_tag(self, tag: str) -> None:
        """
        Setter for tag
        Args:
            tag: str

        Returns: None

        """
        self.tag = tag

    def get_tag(self) -> str:
        """
        Getter for tag entry
        """

        return self.tag

    def set_image_id(self, image_id: str) -> None:
        """
        Setter for image_id
        Args:
            image_id: str

        Returns: None

        """
        self.image_id = image_id

    def get_image_id(self) -> str:
        """
        Getter for image_id entry
        """

        return self.image_id

    def set_created(self, created: str) -> None:
        """
        Setter for created
        Args:
            created: str

        Returns: None

        """
        self.created = created

    def get_created(self) -> str:
        """
        Getter for created entry
        """

        return self.created

    def set_size(self, size: str) -> None:
        """
        Setter for size
        Args:
            size: str

        Returns: None

        """
        self.size = size

    def get_size(self) -> str:
        """
        Getter for size entry
        """

        return self.size
