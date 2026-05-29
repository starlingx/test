from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.registry.objects.system_registry_image_list_object import SystemRegistryImageListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemRegistryImageListOutput:
    """Parses the output of the command 'system registry-image-list'.

    Holds a list of SystemRegistryImageListObject instances, one per row.
    """

    def __init__(self, system_registry_image_list_output: List[str]) -> None:
        """Constructor.

        Args:
            system_registry_image_list_output (List[str]): Raw stdout lines from
                the 'system registry-image-list' command.

        Raises:
            KeywordException: If a row in the output does not contain the expected
                'Image Name' column.
        """
        self.images: List[SystemRegistryImageListObject] = []
        parser = SystemTableParser(system_registry_image_list_output)
        rows = parser.get_output_values_list()

        for row in rows:
            if "Image Name" not in row:
                raise KeywordException(f"The output row {row} did not contain an 'Image Name' column.")
            image_name = row["Image Name"]
            if image_name:
                self.images.append(SystemRegistryImageListObject(image_name))

    def get_images(self) -> List[SystemRegistryImageListObject]:
        """Get the list of image objects.

        Returns:
            List[SystemRegistryImageListObject]: List of image objects in the registry.
        """
        return self.images

    def get_image_names(self) -> List[str]:
        """Get the list of image name strings (convenience helper).

        Returns:
            List[str]: List of image name strings.
        """
        return [image.get_image_name() for image in self.images]
