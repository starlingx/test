class TiSError(Exception):
    """
    Base class for TiS test automation exceptions.

    Notes:
        Each module (or package depends on which makes more sense) should
        have its own sub-base-class that
    inherits this class.Then the specific exception for that module/package
    should inherit the sub-base-class.

    Examples:
        sub-base-class for ssh.py: SSHException(TiSError); ssh retry timeout
        exception: SSHRetryTimeout(SSHException)
    """
    message = "An unknown exception occurred"

    def __init__(self, detailed_message="No details provided"):
        super(TiSError, self).__init__()
        self._error_string = self.message + "\nDetails: " + detailed_message

    def __str__(self):
        return self._error_string


class NoMatchFoundError(TiSError):
    message = "No match found."


class InvalidStructure(TiSError):
    message = "Invalid cli output table structure."


class SSHException(TiSError):
    """
    Base class for SSH Exceptions. All SSH exceptions thrown from utils >
    ssh.py module should inherit this class.
    Examples: SSHRetryTimeout(SSHException)
    """
    message = "SSH error."


class TelnetError(TiSError):
    message = "Telnet Error"


class TelnetTimeout(TelnetError):
    message = 'Telnet timeout'


class TelnetEOF(TelnetError):
    message = 'Telnet EOF.'


class LocalHostError(TiSError):
    message = 'Localhost error.'


class SSHRetryTimeout(SSHException):
    message = "Timed out to connect to host."


class IncorrectCredential(SSHException):
    message = "Login credential rejected by host."


class SSHExecCommandFailed(SSHException):
    """Raised when remotely executed command returns nonzero status."""
    message = "Failed to execute command via SSH."


class TimeoutException(SSHException):
    message = "Request(s) timed out"


class ImproperUsage(SSHException):
    message = "Improper use of test framework"


class ActiveControllerUnsetException(SSHException):
    message = ("Active controller ssh client is not set! "
               "Please use ControllerClient.set_active_controller(ssh_client) "
               "to set an active controller client.")


class NatBoxClientUnsetException(SSHException):
    message = "NatBox ssh client it not set! Please use " \
              "NATBoxClient.set_natbox_client(ip) to set an natbox client"


class CLIRejected(TiSError):
    """Throw when cli command is rejected due to unexpected reasons, such as
    missing arguments"""
    message = "CLI command is rejected."


class HostError(TiSError):
    """Generic Host error"""
    message = "Host error."


class HostPostCheckFailed(HostError):
    """Throws when expected host status is not reached after running certain
    host action cli command."""
    message = "Check failed post host operation."


class HostPreCheckFailed(HostError):
    message = "Check failed pre host operation."


class HostTimeout(HostError):
    message = "Host operation timed out."


class VMError(TiSError):
    message = "VM error."


class VMPostCheckFailed(VMError):
    message = "Check failed post VM operation."


class VMNetworkError(VMError):
    message = "VM network error."


class VMTimeout(VMError):
    message = "VM operation timed out."


class VMOperationFailed(VMError):
    """Failure indicated by CLI output"""
    message = "VM operation failed."


class VolumeError(TiSError):
    message = "Volume error."


class ImageError(TiSError):
    message = "Image error."


class FlavorError(TiSError):
    message = "Flavor error."


class CommonError(TiSError):
    message = "Setup/Teardown error."


class NovaError(TiSError):
    message = "Nova error."


class NeutronError(TiSError):
    message = "Neutron error."


class HeatError(TiSError):
    message = "Heat error."


class CeilometerError(TiSError):
    message = "Ceilometer error."


class SysinvError(TiSError):
    message = 'Sysinv error.'


class ContainerError(SysinvError):
    message = 'Container error.'


class CinderError(TiSError):
    message = 'Cinder error.'


class KeystoneError(TiSError):
    message = 'Keystone error.'


class BuildServerError(TiSError):
    message = "Build Server error."


class ThreadingError(TiSError):
    message = "Multi threading error."


class VLMError(TiSError):
    message = "VLM Operation Error."


class SwiftError(TiSError):
    message = "Swift error."


class OrchestrationError(TiSError):
    message = 'Orchestration error.'


class UpgradeError(TiSError):
    message = 'Upgrade error.'


class BackupSystem(TiSError):
    message = 'System Backup error.'


class RestoreSystem(TiSError):
    message = 'System Restore error.'


class StorageError(TiSError):
    message = 'Storage error.'


class HorizonError(TiSError):
    message = 'Horizon error.'


class IxiaError(TiSError):
    message = 'Ixia error.'


class RefStackError(TiSError):
    message = 'RefStack test(s) failed.'


class DovetailError(TiSError):
    message = 'Dovetail test(s) failed.'


class MuranoError(TiSError):
    message = 'Murano error.'


class DCError(TiSError):
    message = 'DC error.'


class PatchError(TiSError):
    message = 'Patch error.'


class KubeError(TiSError):
    message = 'Kubernetes error.'


class KubeCmdError(KubeError):
    message = 'Kubernetes cmd failed.'


class InstallError(TiSError):
    message = 'Install error'


class K8sError(TiSError):
    message = 'K8s error'
