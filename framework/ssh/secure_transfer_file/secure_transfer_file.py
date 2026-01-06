import os
import stat

from framework.logging.automation_logger import get_logger
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
from framework.validation.validation import validate_equals_with_retry
from keywords.python.string import String


class SecureTransferFile:
    """
    Class that provides an easier way to transfer a file over SFTP.
    """

    def __init__(self, secure_transfer_file_input_object: SecureTransferFileInputObject):
        """Constructor.

        Args:
            secure_transfer_file_input_object (SecureTransferFileInputObject): An instance of SecureTransferFileInputObject
                with the setup to transfer a single file via SFTP.
        """
        # Check the required fields.
        if secure_transfer_file_input_object.get_sftp_client() is None:
            raise ValueError("The field 'sftp_client' in the 'SecureTransferFileInputObject' instance must be defined.")

        if String.is_empty(secure_transfer_file_input_object.get_origin_path()):
            raise ValueError("The field 'origin_path' in the 'SecureTransferFileInputObject' instance cannot be empty.")

        if String.is_empty(secure_transfer_file_input_object.get_destination_path()):
            raise ValueError("The field 'destination_path' in the 'SecureTransferFileInputObject' instance cannot be empty.")

        if secure_transfer_file_input_object.get_transfer_direction() not in TransferDirection:
            raise ValueError("The field 'transfer_direction' in the 'SecureTransferFileInputObject' must be specified as one of the values in 'TransferDirection'.")

        self.secure_transfer_file_input_object = secure_transfer_file_input_object

    def transfer_file(self) -> bool:
        """Transfer the file specified in the constructor via SFTP.

        Returns:
            bool: True, if the file specified in the constructor of this class was successfully transferred; False
                otherwise.
        """
        # Origin path.
        origin_path = self.secure_transfer_file_input_object.get_origin_path()

        # Destination path.
        destination_path = self.secure_transfer_file_input_object.get_destination_path()
        destination_file_name = os.path.basename(destination_path)
        destination_folder_name = os.path.dirname(destination_path)

        # Gets the SFTP client
        sftp_client = self.secure_transfer_file_input_object.get_sftp_client()

        # Determines the transfer direction to perform either a 'get' or 'put' operation.
        transfer_direction = self.secure_transfer_file_input_object.transfer_direction

        # Transfers the file from remote to local destination.
        if transfer_direction == TransferDirection.FROM_REMOTE_TO_LOCAL:

            def is_file_at_destination():
                return os.path.isfile(destination_path)

            # Manages forced file transfer.
            force_transfer = self.secure_transfer_file_input_object.get_force()
            if is_file_at_destination():
                if not force_transfer:
                    get_logger().log_info(f"The file {destination_path} already exists. Try setting the 'force' property of the SecureTransferFileInputObject instance to 'True' if you want to overwrite it.")
                    return False

            # Transfers the file from remote to local destination.
            try:
                sftp_client.get(origin_path, destination_path)
            except Exception as ex:
                get_logger().log_exception(f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Exception: {ex}")
                raise ex

            # Validate that the file was transferred successfully
            validate_equals_with_retry(is_file_at_destination, True, f"File {origin_path} is transferred to {destination_path}.", timeout=self.secure_transfer_file_input_object.get_timeout_in_seconds())

        # Transfers to remote destination.
        elif transfer_direction == TransferDirection.FROM_LOCAL_TO_REMOTE:

            def is_file_at_destination():
                file_list = sftp_client.listdir(destination_folder_name)
                return any(destination_file_name == file for file in file_list)

            # Manages forced file transfer.
            force_transfer = self.secure_transfer_file_input_object.get_force()
            if is_file_at_destination():
                if not force_transfer:
                    get_logger().log_info(f"The file {destination_path} already exists. Try setting the 'force' property of the SecureTransferFileInputObject instance to 'True' if you want to overwrite it.")
                    return False

            # Transfers the file to remote destination.
            try:
                sftp_client.put(origin_path, destination_path)
            except Exception as ex:
                get_logger().log_exception(f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Exception: {ex}")
                raise ex

            # Validate that the file was transferred successfully
            validate_equals_with_retry(is_file_at_destination, True, f"File {origin_path} is transferred to {destination_path}.", timeout=self.secure_transfer_file_input_object.get_timeout_in_seconds())

        # The property 'transfer_direction' was not properly specified.
        else:
            message = f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Property 'transfer_direction' must be specified as either TransferDirection.FROM_LOCAL_TO_REMOTE or TransferDirection.FROM_REMOTE_TO_LOCAL"
            get_logger().log_exception(message)
            raise ValueError(message)

    def transfer_directory_recursive(self) -> bool:
        """Transfer directory recursively via SFTP.

        Returns:
            bool: True if directory was successfully transferred, False otherwise.
        """
        origin_path = self.secure_transfer_file_input_object.get_origin_path()
        destination_path = self.secure_transfer_file_input_object.get_destination_path()
        sftp_client = self.secure_transfer_file_input_object.get_sftp_client()
        transfer_direction = self.secure_transfer_file_input_object.transfer_direction

        if transfer_direction == TransferDirection.FROM_REMOTE_TO_LOCAL:
            return self._transfer_from_remote_recursive(origin_path, destination_path, sftp_client)
        elif transfer_direction == TransferDirection.FROM_LOCAL_TO_REMOTE:
            return self._transfer_to_remote_recursive(origin_path, destination_path, sftp_client)
        else:
            message = f"Invalid transfer direction for recursive transfer: {transfer_direction}"
            get_logger().log_exception(message)
            raise ValueError(message)

    def _transfer_from_remote_recursive(self, remote_path: str, local_path: str, sftp_client) -> bool:
        """
        Recursively transfer from remote to local.
        """
        try:
            file_attr = sftp_client.stat(remote_path)
            if stat.S_ISDIR(file_attr.st_mode):
                os.makedirs(local_path, exist_ok=True)
                for item in sftp_client.listdir(remote_path):
                    self._transfer_from_remote_recursive(f"{remote_path}/{item}", os.path.join(local_path, item), sftp_client)
            else:
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                transfer_obj = SecureTransferFileInputObject()
                transfer_obj.set_sftp_client(sftp_client)
                transfer_obj.set_origin_path(remote_path)
                transfer_obj.set_destination_path(local_path)
                transfer_obj.set_transfer_direction(TransferDirection.FROM_REMOTE_TO_LOCAL)
                transfer_obj.set_force(self.secure_transfer_file_input_object.get_force())
                SecureTransferFile(transfer_obj).transfer_file()
            return True
        except Exception as ex:
            get_logger().log_exception(f"Error transferring {remote_path} to {local_path}: {ex}")
            return False

    def _transfer_to_remote_recursive(self, local_path: str, remote_path: str, sftp_client) -> bool:
        """
        Recursively transfer from local to remote.
        """
        try:
            if os.path.isdir(local_path):
                try:
                    sftp_client.mkdir(remote_path)
                except IOError:
                    pass  # Directory might already exist
                for item in os.listdir(local_path):
                    self._transfer_to_remote_recursive(os.path.join(local_path, item), f"{remote_path}/{item}", sftp_client)
            else:
                transfer_obj = SecureTransferFileInputObject()
                transfer_obj.set_sftp_client(sftp_client)
                transfer_obj.set_origin_path(local_path)
                transfer_obj.set_destination_path(remote_path)
                transfer_obj.set_transfer_direction(TransferDirection.FROM_LOCAL_TO_REMOTE)
                transfer_obj.set_force(self.secure_transfer_file_input_object.get_force())
                SecureTransferFile(transfer_obj).transfer_file()
            return True
        except Exception as ex:
            get_logger().log_exception(f"Error transferring {local_path} to {remote_path}: {ex}")
            return False
