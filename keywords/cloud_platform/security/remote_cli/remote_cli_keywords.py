import os
import shutil
import subprocess
import threading
import time

import paramiko

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_none
from framework.web.webdriver_core import WebDriverCore
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.keycloak_kubectl_result_object import KubectlResultObject
from keywords.cloud_platform.security.remote_cli.object.remote_cli_tarball_info_output import RemoteCliTarballInfoOutput
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.serviceaccount.kubectl_delete_serviceaccount_keywords import KubectlDeleteServiceAccountKeywords
from keywords.k8s.token.kubectl_create_token_keywords import KubectlCreateTokenKeywords
from web_pages.keycloak.login.keycloak_login_page import KeycloakLoginPage


class RemoteCliKeywords(BaseKeyword):
    """Keywords for setting up, using, and tearing down the remote CLI container environment.

    The remote CLI runs kubectl commands inside a Docker container on the test
    machine. Setup mirrors the CGCS __install_remote_cli flow:
      1. Download the wrs-remote-clients tarball from the build server to the test machine.
      2. Extract the tarball locally.
      3. On the controller: create a ServiceAccount + ClusterRoleBinding and
         generate a temp-kubeconfig with a short-lived token.
      4. Download temp-kubeconfig from the controller to the test machine via SFTP.
      5. Run configure_client.sh to pull the container image and configure the working directory.
    Teardown deletes the ServiceAccount and ClusterRoleBinding from the cluster.
    """

    SERVICE_ACCOUNT_NAME = "admin-user"
    SERVICE_ACCOUNT_NAMESPACE = "kube-system"
    TEMP_KUBECONFIG_NAME = "temp-kubeconfig"
    ADMIN_LOGIN_YAML = "admin-login.yaml"

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): Active controller SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)
        self.yaml_keywords = YamlKeywords(ssh_connection)
        self.kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
        self.kubectl_token = KubectlCreateTokenKeywords(ssh_connection)
        self.kubectl_crb = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
        self.kubectl_delete_sa = KubectlDeleteServiceAccountKeywords(ssh_connection)

    def setup(self, oam_ip: str, build_server_user: str, build_server_password: str, install_dir: str, working_dir: str, docker_image: str, tarball_remote_path: str = "", build_server_ip: str = "") -> None:
        """Set up the remote CLI container on the test machine.

        If tarball_remote_path or build_server_ip are not provided, they are
        auto-discovered by reading /etc/build.info from the controller.
        Downloads the wrs-remote-clients tarball from the build server using rsync,
        extracts it locally, creates a ServiceAccount and ClusterRoleBinding on the
        controller, generates a temp-kubeconfig with a token, downloads it to the
        test machine via SFTP, then runs configure_client.sh to pull the container
        image and configure the working directory.

        Args:
            oam_ip (str): OAM floating IP of the controller (bracket-wrapped for IPv6).
            build_server_user (str): Username for the build server.
            build_server_password (str): Password for the build server.
            install_dir (str): Local directory to extract the tarball into.
            working_dir (str): Local working directory path for the remote CLI container.
            docker_image (str): Docker image reference for the remote CLI container.
            tarball_remote_path (str): Path to the tarball on the build server. Auto-discovered if empty.
            build_server_ip (str): IP or hostname of the build server. Auto-discovered if empty.
        """
        validate_not_none(working_dir, "remote_cli working_dir must be configured in security config")

        if not tarball_remote_path or not build_server_ip:
            get_logger().log_info("Auto-discovering build server and tarball path from controller /etc/build.info")
            tarball_info = self.resolve_tarball_path().get_remote_cli_tarball_info_object()
            build_server_ip = build_server_ip or tarball_info.get_build_host()
            tarball_remote_path = tarball_remote_path or tarball_info.get_tarball_path()

        validate_equals(bool(build_server_ip), True, "build_server_ip could not be resolved from /etc/build.info")
        validate_equals(bool(tarball_remote_path), True, "tarball_remote_path could not be resolved from /etc/build.info")

        configure_client_script = os.path.join(install_dir, "configure_client.sh")
        if os.path.isfile(configure_client_script):
            get_logger().log_info("Step 1: Tarball already extracted, skipping download")
        else:
            get_logger().log_info("Step 1: Download wrs-remote-clients tarball from build server")
            subprocess.run(["mkdir", "-p", install_dir], capture_output=True, text=True)
            local_tarball = self.download_file_from_build_server(
                host=build_server_ip,
                username=build_server_user,
                password=build_server_password,
                remote_glob_path=tarball_remote_path,
                local_dir=install_dir,
            )
            validate_equals(os.path.isfile(local_tarball), True, f"Tarball should be downloaded to '{local_tarball}'")

            get_logger().log_info("Step 2: Extract wrs-remote-clients tarball")
            result = subprocess.run(
                ["tar", "-xzf", local_tarball, "-C", install_dir, "--strip-components", "1"],
                capture_output=True,
                text=True,
            )
            validate_equals(result.returncode, 0, f"Tarball extraction should succeed: {result.stderr}")
            os.remove(local_tarball)

        validate_equals(os.path.isfile(configure_client_script), True, f"configure_client.sh should exist at '{configure_client_script}'")

        get_logger().log_info("Step 3: Resolve docker image from docker_image_version.sh")
        if not docker_image:
            docker_image = self.resolve_docker_image(install_dir)

        get_logger().log_info("Step 4: Create ServiceAccount and ClusterRoleBinding on controller")
        template = get_stx_resource_path("resources/cloud_platform/security/remote_cli/admin-login.yaml")
        replacement_dict = {
            "service_account_name": self.SERVICE_ACCOUNT_NAME,
            "service_account_namespace": self.SERVICE_ACCOUNT_NAMESPACE,
        }
        self.yaml_keywords.generate_yaml_file_from_template(template, replacement_dict, self.ADMIN_LOGIN_YAML, "", copy_to_remote=True)
        self.kubectl_file_apply.apply_resource_from_yaml(self.ADMIN_LOGIN_YAML)

        get_logger().log_info("Step 5: Generate temp-kubeconfig with token")
        token = self.kubectl_token.create_token(self.SERVICE_ACCOUNT_NAMESPACE, self.SERVICE_ACCOUNT_NAME)
        self.ssh_connection.send(f"kubectl config --kubeconfig {self.TEMP_KUBECONFIG_NAME} set-cluster wrcp-cluster --server=https://{oam_ip}:6443 --insecure-skip-tls-verify")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send(f"kubectl config --kubeconfig {self.TEMP_KUBECONFIG_NAME} set-credentials {self.SERVICE_ACCOUNT_NAME} --token={token}")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send(f"kubectl config --kubeconfig {self.TEMP_KUBECONFIG_NAME} set-context {self.SERVICE_ACCOUNT_NAME}@wrcp-cluster --cluster=wrcp-cluster --user={self.SERVICE_ACCOUNT_NAME} --namespace=default")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send(f"kubectl config --kubeconfig {self.TEMP_KUBECONFIG_NAME} use-context {self.SERVICE_ACCOUNT_NAME}@wrcp-cluster")
        self.validate_success_return_code(self.ssh_connection)
        self.ssh_connection.send(f"chmod a+rw {self.TEMP_KUBECONFIG_NAME}")
        self.validate_success_return_code(self.ssh_connection)

        get_logger().log_info("Step 6: Download temp-kubeconfig from controller to test machine via SFTP")
        if os.path.isfile(working_dir):
            os.remove(working_dir)
        result = subprocess.run(["mkdir", "-p", working_dir], capture_output=True, text=True)
        validate_equals(result.returncode, 0, f"Working directory '{working_dir}' should be created successfully: {result.stderr}")
        local_kubeconfig = os.path.join(working_dir, self.TEMP_KUBECONFIG_NAME)
        self.file_keywords.download_file(self.TEMP_KUBECONFIG_NAME, local_kubeconfig)
        validate_equals(os.path.isfile(local_kubeconfig), True, f"temp-kubeconfig should be downloaded to '{local_kubeconfig}'")

        get_logger().log_info("Step 7: Extract system-local-ca certificate from controller")
        self.ssh_connection.send(export_k8s_config("kubectl get secret system-local-ca -n cert-manager -o jsonpath='{.data.ca\\.crt}' | base64 -d > root-ca-secret.crt"))
        self.validate_success_return_code(self.ssh_connection)

        get_logger().log_info("Step 8: Run configure_client.sh on test machine")
        openrc_file = os.path.join(install_dir, "admin-openrc.sh")
        if not os.path.isfile(openrc_file):
            floating_ip = oam_ip.strip("[]")
            openrc_content = f"export OS_AUTH_URL=http://{floating_ip}:5000/v3\n" "export OS_PROJECT_NAME=admin\n" "export OS_USER_DOMAIN_NAME=Default\n" "export OS_PROJECT_DOMAIN_NAME=Default\n" "export OS_USERNAME=admin\n" f"export OS_PASSWORD={self.ssh_connection.password}\n" "export OS_INTERFACE=internalURL\n" "export OS_IDENTITY_API_VERSION=3\n"
            with open(openrc_file, "w") as f:
                f.write(openrc_content)
        os.chmod(configure_client_script, 0o755)
        cfg_result = subprocess.run(
            [configure_client_script, "-k", local_kubeconfig, "-w", working_dir, "-p", docker_image],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=install_dir,
        )
        validate_equals(cfg_result.returncode, 0, f"configure_client.sh should succeed: {cfg_result.stdout} {cfg_result.stderr}")

        get_logger().log_info("Step 9: Copy CA cert to working_dir and append OS_CACERT to admin-openrc.sh")
        ca_cert_dest = os.path.join(working_dir, "root-ca-secret.crt")
        self.file_keywords.download_file("root-ca-secret.crt", ca_cert_dest)
        validate_equals(os.path.isfile(ca_cert_dest), True, f"CA cert should be downloaded to '{ca_cert_dest}'")
        with open(openrc_file) as f:
            existing = f.read()
        if "OS_CACERT" not in existing:
            with open(openrc_file, "a") as f:
                f.write("\nexport OS_CACERT=root-ca-secret.crt\n")

        get_logger().log_info("Step 10: Create .helm and .cache directories in working_dir")
        subprocess.run(["mkdir", "-p", os.path.join(working_dir, ".helm"), os.path.join(working_dir, ".cache")], capture_output=True, text=True)

        get_logger().log_info("Step 11: Pre-pull docker image to avoid timeout during kubectl execution")
        pull_result = subprocess.run(["docker", "pull", docker_image], capture_output=True, text=True, timeout=300)
        validate_equals(pull_result.returncode, 0, f"Docker image pull should succeed: {pull_result.stderr}")
        get_logger().log_info("Remote CLI setup complete")

    def run_kubectl_in_container_with_browser_login(self, install_dir: str, working_dir: str, kubectl_cmd: str, container_kubeconfig_path: str, username: str, password: str, totp_secret: str = None, url_timeout: int = 60, completion_timeout: int = 60) -> KubectlResultObject:
        """Run kubectl inside the remote CLI container and authenticate via Keycloak browser login.

        Sources remote_client_platform.sh from install_dir to activate the container
        environment, sets KUBECONFIG to the container-internal kubeconfig path, then
        runs the kubectl command. kubelogin prints the browser URL to stdout because
        --skip-open-browser is set in the kubeconfig. Selenium navigates to the URL
        and completes the Keycloak MFA flow.

        Args:
            install_dir (str): Local directory where remote_client_platform.sh was generated by configure_client.sh.
            working_dir (str): Local working directory mounted as /wd in the remote CLI container.
            kubectl_cmd (str): kubectl command to run inside the container (without --kubeconfig).
            container_kubeconfig_path (str): Container-internal path to the OIDC kubeconfig (e.g. /wd/...).
            username (str): Keycloak username.
            password (str): Keycloak password.
            totp_secret (str): Base32 TOTP secret. Pass None for CONFIGURE_TOTP flow.
            url_timeout (int): Maximum seconds to wait for kubelogin to print the browser URL.
            completion_timeout (int): Maximum seconds to wait for kubectl to complete after login.

        Returns:
            KubectlResultObject: Result containing kubectl output.
        """
        output_lines = []
        login_url_found = [None]
        deadline = time.time() + url_timeout

        env = os.environ.copy()
        env["OSC_WORKDIR"] = working_dir
        env["CONFIG_TYPE"] = "platform"
        env["K8S_CONFIG_FILE"] = os.path.join(working_dir, self.TEMP_KUBECONFIG_NAME)
        env["FORCE_NO_SHELL"] = "true"
        platform_image_result = subprocess.run(
            ["bash", "-c", f"source {install_dir}/docker_image_version.sh && echo $PLATFORM_DOCKER_IMAGE"],
            capture_output=True,
            text=True,
        )
        env["PLATFORM_DOCKER_IMAGE"] = platform_image_result.stdout.strip()

        proc = subprocess.Popen(
            ["bash", install_dir + "/client_wrapper.sh"] + kubectl_cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=install_dir,
        )

        def drain_stdout() -> None:
            for line in proc.stdout:
                output_lines.append(line)
                if login_url_found[0] is None and "visit the following URL in your browser" in line:
                    parts = line.split("http", 1)
                    if len(parts) > 1:
                        login_url_found[0] = "http" + parts[1].strip()

        drain_thread = threading.Thread(target=drain_stdout, daemon=True)
        drain_thread.start()

        while login_url_found[0] is None and time.time() < deadline:
            time.sleep(0.5)

        if login_url_found[0] is None:
            get_logger().log_error("kubelogin browser URL not found in container output within deadline; aborting login")
            proc.kill()
            drain_thread.join(timeout=10)
            result = KubectlResultObject()
            result.set_output("".join(output_lines))
            return result

        get_logger().log_info(f"kubelogin browser URL from container: {login_url_found[0]}")
        driver = WebDriverCore()
        keycloak_login_page = KeycloakLoginPage(driver)
        keycloak_login_page.navigate_to_login_url(login_url_found[0])
        keycloak_login_page.login(username=username, password=password, totp_secret=totp_secret)
        driver.quit()

        drain_thread.join(timeout=completion_timeout)
        proc.wait()

        result = KubectlResultObject()
        result.set_output("".join(output_lines))
        return result

    def prepare_oidc_kubeconfig_for_container(self, local_kubeconfig_path: str, working_dir: str, install_dir: str = "") -> str:
        """Copy the OIDC kubeconfig into working_dir for container use.

        The remote CLI container mounts working_dir as /wd. The kubeconfig already
        uses bare filenames (e.g. system-local-ca.crt) which resolve correctly
        inside the container since kubectl runs with /wd as the working directory.
        The CA cert must already be present in working_dir (copied there by setup).

        Args:
            local_kubeconfig_path (str): Local path to the OIDC kubeconfig on the test machine.
            working_dir (str): Local working directory mounted as /wd inside the container.
            install_dir (str): Unused, kept for API compatibility.

        Returns:
            str: Container-internal path to the kubeconfig (/wd/<filename>).
        """
        kubeconfig_filename = os.path.basename(local_kubeconfig_path)
        shutil.copy2(local_kubeconfig_path, os.path.join(working_dir, kubeconfig_filename))
        container_kubeconfig_path = f"/wd/{kubeconfig_filename}"
        get_logger().log_info(f"OIDC kubeconfig prepared for container at {container_kubeconfig_path}")
        return container_kubeconfig_path

    def resolve_docker_image(self, install_dir: str) -> str:
        """Read docker_image_version.sh from the extracted tarball to get the platform docker image.

        Sources docker_image_version.sh and reads the PLATFORM_DOCKER_IMAGE variable,
        then constructs the full image reference using the registry from config.

        Args:
            install_dir (str): Local directory where the tarball was extracted.

        Returns:
            str: Full docker image reference.
        """
        docker_version_script = os.path.join(install_dir, "docker_image_version.sh")
        validate_equals(os.path.isfile(docker_version_script), True, f"docker_image_version.sh should exist at '{docker_version_script}'")
        result = subprocess.run(
            ["bash", "-c", f"source {docker_version_script} && echo $PLATFORM_DOCKER_IMAGE"],
            capture_output=True,
            text=True,
        )
        validate_equals(result.returncode, 0, "docker_image_version.sh should source successfully")
        platform_image = result.stdout.strip()
        validate_equals(bool(platform_image), True, "PLATFORM_DOCKER_IMAGE should be set in docker_image_version.sh")
        get_logger().log_info(f"Resolved docker image: {platform_image}")
        return platform_image

    def download_file_from_build_server(self, host: str, username: str, password: str, remote_glob_path: str, local_dir: str) -> str:
        """Download a file from the build server using paramiko SFTP.

        Connects directly to the build server from the test machine using
        paramiko, resolves the glob pattern to find the tarball, and downloads
        it to the local directory.

        Args:
            host (str): Build server hostname or IP.
            username (str): Build server username.
            password (str): Build server password.
            remote_glob_path (str): Full remote path, may include glob wildcard.
            local_dir (str): Local directory to download the file into.

        Returns:
            str: Local path to the downloaded file.
        """
        get_logger().log_info(f"Connecting to build server {host} via paramiko")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(host, username=username, password=password, timeout=30)

        remote_dir = os.path.dirname(remote_glob_path)
        pattern = os.path.basename(remote_glob_path)
        _, stdout, stderr = ssh_client.exec_command(f"ls {remote_dir}/{pattern} 2>/dev/null || find {remote_dir} -name '{pattern}' 2>/dev/null")
        matches = [line.strip() for line in stdout.readlines() if line.strip()]
        get_logger().log_info(f"ls output: {matches}, stderr: {''.join(stderr.readlines())}")
        validate_equals(len(matches) > 0, True, f"Tarball matching '{remote_glob_path}' should exist on build server {host}")
        remote_file = matches[0]

        local_file = os.path.join(local_dir, os.path.basename(remote_file))
        get_logger().log_info(f"Downloading {remote_file} to {local_file}")
        sftp = ssh_client.open_sftp()
        sftp.get(remote_file, local_file)
        sftp.close()
        ssh_client.close()
        get_logger().log_info(f"Tarball downloaded to {local_file}")
        return local_file

    def resolve_tarball_path(self) -> RemoteCliTarballInfoOutput:
        """Read /etc/build.info from the controller and construct the tarball path on the build server.

        Returns:
            RemoteCliTarballInfoOutput: Output object containing the resolved build server and tarball path.
        """
        build_info_lines = self.file_keywords.read_file("/etc/build.info")
        build_info = {}
        for line in build_info_lines:
            line = line.strip().strip('"')
            if "=" in line:
                key, _, value = line.partition("=")
                build_info[key.strip()] = value.strip().strip('"')
        build_number = build_info.get("BUILD_NUMBER", "")
        tarball_info_output = RemoteCliTarballInfoOutput(build_info)
        tarball_info_object = tarball_info_output.get_remote_cli_tarball_info_object()
        get_logger().log_info(f"Resolved build server: {tarball_info_object.get_build_host()}, tarball path: {tarball_info_object.get_tarball_path()} (fallback BUILD_NUMBER: {build_number})")
        return tarball_info_output

    def clear_container_token_cache(self, working_dir: str, docker_image: str) -> None:
        """Remove the OIDC token cache directory created inside the remote CLI container.

        The container runs as root so the cache/ directory in working_dir is
        root-owned and cannot be removed by the test machine user directly.
        This method runs a docker container to remove it with the correct permissions.

        Args:
            working_dir (str): Local working directory mounted as /wd in the container.
            docker_image (str): Docker image to use for the removal command.
        """
        get_logger().log_info(f"Clearing container OIDC token cache at {working_dir}/cache")
        subprocess.run(
            ["docker", "run", "--rm", "--volume", f"{working_dir}:/wd", "--entrypoint", "/bin/bash", docker_image, "-c", "rm -rf /wd/cache"],
            capture_output=True,
            text=True,
        )
