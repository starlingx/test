from framework.logging.automation_logger import get_logger


class AnsiblePlaybookBackUpRestoreOutput:
    """
    This class parses the output of 'Ansible-playbook backup and Restore' command to verify the output.
    """

    def __init__(self, cmd_output: str):
        """
        Constructor

        Args:
            cmd_output (str): Output of the 'ansible-playbook backup <cmd>' command.
        """
        self.cmd_output = cmd_output

    def validate_ansible_playbook_backup_restore_result(self) -> bool:
        """
        Checks if the output contains all the expected values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.

        sample output format:
        PLAY RECAP ******************************************************************************************************************************************
        localhost                  : ok=274  changed=151  unreachable=0    failed=0    skipped=270  rescued=0    ignored=0

        Thursday 10 April 2025  18:08:50 +0000 (0:00:00.020)       0:25:50.203 ********
        ===============================================================================
        common/push-docker-images : Download images and push to local registry --------------------------------------------------------------------- 450.63s
        optimized-restore/apply-manifest : Applying puppet restore manifest ------------------------------------------------------------------------ 136.43s
        optimized-restore/apply-manifest : Create puppet hieradata runtime configuration ------------------------------------------------------------ 80.92s

        """
        successful_backup = False
        output = "".join(self.cmd_output)

        if output and len(output) > 0:
            lastlines = output[output.rfind("PLAY RECAP") :].splitlines()
            result_line = [line for line in lastlines if "PLAY RECAP" not in line]
            result_line = result_line[0] if len(result_line) > 0 else None
            get_logger().log_info(f"Ansible result line = {result_line}")
            if result_line and ":" in result_line:
                result = result_line.split(":")[1].split()
                failed = [i for i in result if "failed" in i]
                if failed:
                    if int(failed[0].split("=")[1]) == 0:
                        successful_backup_restore = True
        get_logger().log_info(f"successful ansible : {successful_backup_restore}")
        return successful_backup_restore
