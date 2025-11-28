import json
import os
import time
from datetime import datetime

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


METRIC_REPORTER_CONFIG_TEMPLATE = {
    "cluster": {
        "host": "{host_url}",
        "distributedcloud": "no",
        "metric_url": "/mon-elasticsearch-client/metricbeat-*/_search?scroll=",
        "scroll_url": "/mon-elasticsearch-client/_search/scroll",
        "username": "{target_system_user}",
        "password": "{target_system_password}"
    },
    "dc": {
        "ip_addr": "not a dc system",
        "ssh_port": "",
        "ssh_pass": "not a dc system"
    },
    "filters": {
        "__SYSNAME__": "{lab_name}",
        "__START_TS__": "{start_time}",
        "__END_TS__": "{end_time}",
        "__TIMEZONE__": "UTC",
        "__QSIZE__": "4096",
        "__SCROLL__": "15m"
    },
    "datasets": [
        {"name": "system.core", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "system.cpu", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "linux.iostat", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "system.diskio", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "system.filesystem", "query": "queries/scrolling_dataset.json", "csv": "true", "exclude": ["^/var/lib/kubelet/plugins/kubernetes.io/rbd/mounts"]},
        {"name": "system.load", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "system.memory", "query": "queries/scrolling_dataset.json", "csv": "true"},
        {"name": "system.network", "query": "queries/scrolling_dataset.json", "csv": "true", "exclude": ["^cali"]},
        {"name": "system.process", "query": "queries/scrolling_dataset.json", "csv": "true", "period": "10"},
        {"name": "system.top_n", "query": "queries/scrolling_dataset.json", "csv": "true", "top_n": "", "hosts": ""},
        {"name": "kubernetes.container", "query": "queries/scrolling_dataset.json", "csv": "true", "period": "10"},
        {"name": "kubernetes.pod", "query": "queries/scrolling_dataset.json", "csv": "true", "period": "10"},
        {"name": "kubernetes.node", "query": "queries/scrolling_dataset.json", "csv": "true", "period": "10"}
    ],
    "reporting": {
        "output_dir": "{result_output_dir}",
        "json": "true",
        "tabular": "true"
    }
}


class MetricReporterKeywords(BaseKeyword):
    """
    Keywords for running metric reporter to collect system metrics during tests.
    """

    def __init__(self, ssh_connection):
        """
        Constructor

        Args:
            ssh_connection: SSH connection to the target system
        """
        self.ssh_connection = ssh_connection

    def run_metric_reporter(self, start_time: datetime, end_time: datetime) -> str:
        """
        Run metric reporter to collect system metrics for the specified time period.

        Args:
            start_time (datetime): Start time for metric collection
            end_time (datetime): End time for metric collection

        Returns:
            str: Local directory path where metrics were downloaded
        """

        get_logger().log_info(f"Loading metric server configuration...")
        server_config_path = get_stx_resource_path("config/system_test/metric_report_server.json5")
        with open(server_config_path, 'r') as f:
            server_config = json.load(f)

        # Extract values from server config
        result_output_dir = f"{server_config['home']}/metric_reports_{int(time.time())}"
        metric_server = server_config["server"]
        metric_user = server_config["user"]
        metric_password = server_config["password"]
        metric_reporter_location = server_config["metric_reporter_location"]
        pythonpath = server_config["pythonpath"]

        # Create SSH connection to metric server
        metric_ssh = SSHConnectionManager.create_ssh_connection(
            metric_server,
            metric_user,
            metric_password,
        )

        get_logger().log_debug(f"Creating remote directory: {result_output_dir} and content config file")
        metric_ssh.send(f"mkdir -p {result_output_dir}")
        self.validate_success_return_code(metric_ssh)
        config_content = self._create_config_content(start_time, end_time, result_output_dir, server_config)
        config_file_name = f"report_config_{datetime.utcnow().strftime('%y%m%d%H%M')}.json"
        remote_config_path = f"{result_output_dir}/{config_file_name}"
        create_config_cmd = f'cat > {remote_config_path} << "EOF"\n{config_content}\nEOF'
        metric_ssh.send(create_config_cmd)
        self.validate_success_return_code(metric_ssh)
        get_logger().log_debug(f"Created config file on remote server: {remote_config_path}")

        #set PYTHONPATH and run metric reporter
        setup_cmd = f"export PYTHONPATH={pythonpath}"
        metric_ssh.send(setup_cmd)
        self.validate_success_return_code(metric_ssh)
        run_cmd = f"python3 {metric_reporter_location}/main.py -c {remote_config_path}"
        get_logger().log_info(f"Running metric reporter: {run_cmd}")
        output = metric_ssh.send_as_sudo(run_cmd)
        self.validate_success_return_code(metric_ssh)
        get_logger().log_info(f"Metric reporter output: {''.join(output)}")

        local_dest = os.path.join(get_logger().get_test_case_log_dir(), os.path.basename(result_output_dir))
        get_logger().log_info(f"Downloading metric results from {result_output_dir} to {local_dest}")

        os.makedirs(local_dest, exist_ok=True)
        file_keywords = FileKeywords(metric_ssh)
        for filename in file_keywords.get_files_in_dir(result_output_dir):
            remote_file = f"{result_output_dir}/{filename}"
            local_file = os.path.join(local_dest, filename)
            file_keywords.download_file(remote_file, local_file)
        get_logger().log_info(f"Metric results downloaded to: {local_dest}")

        return local_dest


    def _create_config_content(self, start_time: datetime, end_time: datetime, 
                              result_output_dir: str, server_config: dict) -> str:
        """
        Create metric reporter configuration content in JSON format using template.

        Args:
            start_time (datetime): Start time for metric collection
            end_time (datetime): End time for metric collection
            result_output_dir (str): Output directory for results
            lab_name (str): Lab name
            lab_ip (str): Lab IP address

        Returns:
            str: JSON configuration content
        """
        # Get lab configuration
        lab_config = ConfigurationManager.get_lab_config()
        lab_name = lab_config.get_lab_name()
        lab_ip = lab_config.get_floating_ip()

        # Create config from template
        config_str = json.dumps(METRIC_REPORTER_CONFIG_TEMPLATE)
        host_url = f"https://[{lab_ip}]:31001" if ":" in lab_ip else f"https://{lab_ip}:31001"
        config_str = config_str.replace("{host_url}", host_url)
        config_str = config_str.replace("{lab_name}", lab_name)
        config_str = config_str.replace("{start_time}", start_time.strftime('%Y-%m-%dT%H:%M:%S.%f'))
        config_str = config_str.replace("{end_time}", end_time.strftime('%Y-%m-%dT%H:%M:%S.%f'))
        config_str = config_str.replace("{result_output_dir}", result_output_dir)
        config_str = config_str.replace("{target_system_user}", server_config.get("target_system_user", ""))
        config_str = config_str.replace("{target_system_password}", server_config.get("target_system_password", ""))      
        config = json.loads(config_str)

        return json.dumps(config, indent=2)