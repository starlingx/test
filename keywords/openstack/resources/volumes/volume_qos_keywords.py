"""Cinder QoS spec and volume type keywords.

Volume type operations use the OpenStack SDK block storage proxy directly.
QoS spec operations go through the Cinder REST API because openstacksdk 4.12.0
has no QoS support in its block storage v3 proxy - the qos_spec resource and
the create_qos_spec/delete_qos_spec/associate_qos_spec proxy methods were added
to the SDK after that release. The REST calls are issued through the same
ServiceProxy, so they are still logged like any other SDK call.
"""

from typing import Dict

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from framework.exceptions.keyword_exception import KeywordException
from requests import Response

QOS_SPECS_PATH = "/qos-specs"


class VolumeQosKeywords(BaseKeyword):
    """CRUD operations for Cinder QoS specs and volume types."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize VolumeQosKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def create_qos_spec(self, name: str, consumer: str, specs: Dict[str, int]) -> str:
        """Create a Cinder QoS spec.

        The Cinder API expects QoS properties as flat top-level keys in the
        request body alongside 'name' and 'consumer', not nested under 'specs'.

        Args:
            name (str): QoS spec name.
            consumer (str): Consumer type ('front-end', 'back-end', or 'both').
            specs (Dict[str, int]): QoS spec key-value pairs (e.g. {'read_bytes_sec': 10485769}).

        Returns:
            str: The created QoS spec ID.

        Raises:
            KeywordException: If the Cinder API rejects the request or returns
                no QoS spec ID.
        """
        get_logger().log_info(f"Creating QoS spec '{name}' (consumer={consumer}, specs={specs})")
        qos_body = {"name": name, "consumer": consumer}
        for spec_key, spec_value in specs.items():
            qos_body[spec_key] = str(spec_value)

        storage = self.openstack_connection.get_block_storage()
        response = storage.post(QOS_SPECS_PATH, json={"qos_specs": qos_body})
        self._validate_response(response, f"create QoS spec '{name}'")

        qos_id = response.json().get("qos_specs", {}).get("id", "")
        if not qos_id:
            get_logger().log_error(
                f"Cinder returned no QoS spec ID when creating '{name}'"
            )
            raise KeywordException(
                f"Cinder returned no QoS spec ID when creating '{name}'"
            )

        get_logger().log_info(f"Created QoS spec: id={qos_id}")
        return qos_id

    def delete_qos_spec(self, qos_id: str) -> None:
        """Delete a Cinder QoS spec.

        Args:
            qos_id (str): QoS spec ID to delete.

        Raises:
            KeywordException: If the Cinder API rejects the request.
        """
        get_logger().log_info(f"Deleting QoS spec '{qos_id}'")
        storage = self.openstack_connection.get_block_storage()
        response = storage.delete(f"{QOS_SPECS_PATH}/{qos_id}", params={"force": "False"})
        self._validate_response(response, f"delete QoS spec '{qos_id}'")

    def create_volume_type(self, name: str) -> str:
        """Create a Cinder volume type.

        Args:
            name (str): Volume type name.

        Returns:
            str: The created volume type ID.
        """
        get_logger().log_info(f"Creating volume type '{name}'")
        storage = self.openstack_connection.get_block_storage()
        vtype = storage.create_type(name=name)
        get_logger().log_info(f"Created volume type: id={vtype.id}")
        return vtype.id

    def delete_volume_type(self, volume_type_id: str) -> None:
        """Delete a Cinder volume type.

        Args:
            volume_type_id (str): Volume type ID to delete.
        """
        get_logger().log_info(f"Deleting volume type '{volume_type_id}'")
        storage = self.openstack_connection.get_block_storage()
        storage.delete_type(volume_type_id)

    def associate_qos_to_volume_type(self, qos_id: str, volume_type_id: str) -> None:
        """Associate a QoS spec with a volume type.

        The Cinder associate endpoint is a GET with the volume type passed as a
        query parameter, not a POST.

        Args:
            qos_id (str): QoS spec ID.
            volume_type_id (str): Volume type ID.

        Raises:
            KeywordException: If the Cinder API rejects the request.
        """
        get_logger().log_info(f"Associating QoS '{qos_id}' with volume type '{volume_type_id}'")
        storage = self.openstack_connection.get_block_storage()
        response = storage.get(f"{QOS_SPECS_PATH}/{qos_id}/associate", params={"vol_type_id": volume_type_id})
        self._validate_response(response, f"associate QoS spec '{qos_id}' with volume type '{volume_type_id}'")

    def is_qos_spec_present(self, qos_id: str) -> bool:
        """Check whether a QoS spec exists.

        Args:
            qos_id (str): QoS spec ID.

        Returns:
            bool: True if the QoS spec exists.
        """
        storage = self.openstack_connection.get_block_storage()
        response = storage.get(f"{QOS_SPECS_PATH}/{qos_id}", raise_exc=False)
        return response.status_code == 200

    def cleanup_qos_spec(self, qos_id: str) -> None:
        """Safely delete a QoS spec if it exists.

        Args:
            qos_id (str): QoS spec ID.
        """
        if self.is_qos_spec_present(qos_id):
            self.delete_qos_spec(qos_id)
            get_logger().log_info(f"Cleaned up QoS spec: {qos_id}")
        else:
            get_logger().log_info(f"QoS spec '{qos_id}' already gone, skipping cleanup")

    def cleanup_volume_type(self, volume_type_id: str) -> None:
        """Safely delete a volume type if it exists.

        Args:
            volume_type_id (str): Volume type ID.
        """
        storage = self.openstack_connection.get_block_storage()
        vtype = storage.find_type(volume_type_id, ignore_missing=True)
        if vtype:
            storage.delete_type(vtype.id)
            get_logger().log_info(f"Cleaned up volume type: {volume_type_id}")


    def _validate_response(self, response: Response, action: str,) -> None:
        """Validate that a Cinder REST response indicates success.

        Args:
            response (object): Response returned by the block storage proxy.
            action (str): Human-readable description of the attempted action.

        Raises:
            KeywordException: If the response status code is not in the 2xx range.
        """
        status_code = response.status_code
        if status_code < 200 or status_code >= 300:
            get_logger().log_error(
                f"Failed to {action}: HTTP {status_code} - {response.text}"
            )
            raise KeywordException(
                f"Failed to {action}: HTTP {status_code} - {response.text}"
            )
