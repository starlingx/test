from typing import List

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.registry.objects.system_registry_image_tags_object import SystemRegistryImageTagsObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemRegistryImageTagsOutput:
    """Parses the output of the command 'system registry-image-tags <image>'.

    Holds a list of SystemRegistryImageTagsObject instances, one per row.
    """

    def __init__(self, system_registry_image_tags_output: List[str]) -> None:
        """Constructor.

        Args:
            system_registry_image_tags_output (List[str]): Raw stdout lines from
                the 'system registry-image-tags <image>' command.

        Raises:
            KeywordException: If a row in the output does not contain the expected
                'Image Tag' column.
        """
        self.tags: List[SystemRegistryImageTagsObject] = []
        parser = SystemTableParser(system_registry_image_tags_output)
        rows = parser.get_output_values_list()

        for row in rows:
            if "Image Tag" not in row:
                raise KeywordException(f"The output row {row} did not contain an 'Image Tag' column.")
            image_tag = row["Image Tag"]
            if image_tag:
                self.tags.append(SystemRegistryImageTagsObject(image_tag))

    def get_tags(self) -> List[SystemRegistryImageTagsObject]:
        """Get the list of tag objects.

        Returns:
            List[SystemRegistryImageTagsObject]: List of tag objects.
        """
        return self.tags

    def get_tag_names(self) -> List[str]:
        """Get the list of tag strings (convenience helper).

        Returns:
            List[str]: List of tag strings.
        """
        return [tag.get_image_tag() for tag in self.tags]
