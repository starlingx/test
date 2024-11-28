import os
import time

from framework.logging.automation_logger import get_logger
from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from framework.ssh.secure_transfer_file.secure_transfer_file_input_object import SecureTransferFileInputObject
from keywords.python.string import String


class SecureTransferFile:
    """
    Class that provides an easier way to transfer a file over SFTP.
    """

    def __init__(self, secure_transfer_file_input_object: SecureTransferFileInputObject):
        """
        Constructor
        Args:
            secure_transfer_file_input_object (SecureTransferFileInputObject): an instance of SecureTransferFileInputObject
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
        """
        Transfer the file specified in the constructor via SFTP.
        Returns:
            bool: True, if the file specified in the constructor of this class was successfully transferred; False
            otherwise.

        """
        file_was_transferred = False

        # Origin path.
        origin_path = self.secure_transfer_file_input_object.get_origin_path()

        # Destination path.
        destination_path = self.secure_transfer_file_input_object.get_destination_path()

        # Try to extract the destination file name from destination_path. If that is not possible, attempt to extract it
        # from origin_path. If this also fails, terminate the process.
        destination_file_name = os.path.basename(destination_path)
        if String.is_empty(destination_file_name):
            destination_file_name = os.path.basename(origin_path)
            if String.is_empty(destination_file_name):
                get_logger().log_error("The file name must be specified in the property 'origin_path'.")
                return False

        # Gets the SFTP client
        sftp_client = self.secure_transfer_file_input_object.get_sftp_client()

        # Determines the transfer direction to perform either a 'get' or 'put' operation.
        transfer_direction = self.secure_transfer_file_input_object.transfer_direction

        # Transfers the file from remote to local destination.
        if transfer_direction == TransferDirection.FROM_REMOTE_TO_LOCAL:
            # Verifies is the file already exists at the destination path.
            file_already_exists = os.path.isfile(destination_path)

            # Manages forced file transfer.
            force_transfer = self.secure_transfer_file_input_object.get_force()
            if file_already_exists:
                if not force_transfer:
                    get_logger().log_info(
                        f"The file {destination_path} already exists. Try setting the 'force' property of the SecureTransferFileInputObject instance to 'True' if you want to overwrite it."
                    )
                    return False

            # Transfers the file from remote to local destination.
            try:
                sftp_client.get(origin_path, destination_path)
            except Exception as ex:
                get_logger().log_exception(f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Exception: {ex}")
                raise ex

            # Monitors the file transfer from remote to the local destination.
            check_interval = 3
            timeout_seconds = self.secure_transfer_file_input_object.get_timeout_in_seconds()
            end_time = time.time() + timeout_seconds
            while time.time() < end_time:
                try:
                    file_was_transferred = os.path.isfile(destination_path)
                except Exception as ex:
                    get_logger().log_exception(f"Error while trying to transfer the file {destination_path}. Exception: {ex}")
                    raise ex
                if file_was_transferred:
                    break
                time.sleep(check_interval)
                get_logger().log_exception(
                    f"Waiting for {check_interval} more seconds to the file {origin_path} be transferred to {destination_path}. Maximum total time to wait: {timeout_seconds} s. Remaining time: {end_time - time.time():.3f} s."
                )

        # Transfers to remote destination.
        elif transfer_direction == TransferDirection.FROM_LOCAL_TO_REMOTE:
            # Verifies is the file already exists at the destination path.
            file_list = sftp_client.listdir()
            file_already_exists = any(destination_file_name == file for file in file_list)

            # Manages forced file transfer.
            force_transfer = self.secure_transfer_file_input_object.get_force()
            if file_already_exists:
                if not force_transfer:
                    get_logger().log_info(
                        f"The file {destination_path} already exists. Try setting the 'force' property of the SecureTransferFileInputObject instance to 'True' if you want to overwrite it."
                    )
                    return False

            # Transfers the file to remote destination.
            try:
                sftp_client.put(origin_path, destination_path)
            except Exception as ex:
                get_logger().log_exception(f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Exception: {ex}")
                raise ex

            # Monitors the file transfer to the remote destination.
            file_was_transferred = False
            check_interval = 3
            timeout_seconds = self.secure_transfer_file_input_object.get_timeout_in_seconds()
            end_time = time.time() + timeout_seconds
            while time.time() < end_time:
                try:
                    file_list = sftp_client.listdir()
                except Exception as ex:
                    get_logger().log_exception(f"Error while trying to transfer the file {destination_path}. Exception: {ex}")
                    raise ex
                file_was_transferred = any(destination_file_name == file for file in file_list)
                if file_was_transferred:
                    break
                time.sleep(check_interval)
                get_logger().log_exception(
                    f"Waiting for {check_interval} more seconds to the file {origin_path} be transferred to {destination_path}. Maximum total time to wait: {timeout_seconds} s. Remaining time: {end_time - time.time()} s."
                )

        # The property 'transfer_direction' was not properly specified.
        else:
            message = f"Error when trying to transfer the file {origin_path} to destination {destination_path}. Property 'transfer_direction' must be specified as either TransferDirection.FROM_LOCAL_TO_REMOTE or TransferDirection.FROM_REMOTE_TO_LOCAL"
            get_logger().log_exception(message)
            raise ValueError(message)

        # If we've reached this point, the file was either transferred successfully or the transfer failed due to a timeout.
        if file_was_transferred:
            message = f"File {origin_path} successfully transferred to {destination_path}."
            get_logger().log_info(message)
            return True
        else:
            message = f"Error while trying to transfer the file {destination_path}. Time to transfer ({self.secure_transfer_file_input_object.get_timeout_in_seconds()} s) exceeded."
            get_logger().log_error(message)
            return False
