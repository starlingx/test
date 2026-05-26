from typing import Dict, List, Any


class UnlockKpiBlocks:
    """
    Unlock KPI block definitions for log pattern matching.

    Contains block configurations for both pair mode (start/stop timing)
    and sequential mode (pattern matching).
    """

    @staticmethod
    def active_controller_unlock_kpi_blocks() -> List[Dict[str, Any]]:
        """
        Get unlock KPI blocks for active controller - measures phase durations.

        Returns:
            List[Dict[str, Any]]: Block definitions for pair mode timing
        """
        return [
            {
                "label": "LOCK HOST PATTERN",
                "file": ["mtcAgent.log*"],
                "patterns": ["Info : {hostname} Lock Action"],
                "max_time_delta": 2000
            },
            {
                "label": "LOCK HOST",
                "file": ["mtcAgent.log*"],
                "start": "Info : {hostname} Lock Action",
                "stop": "Info : {hostname} Disable Complete",
                "exclude_from_kpi": True
            },
            {
                "label": "SHUTDOWN PHASE",
                "file": ["mtcAgent.log*", "auth.log*"],
                "start": "Info : {hostname} Unlock Action",
                "stop": "notice System is rebooting",
                "max_time_delta": 600
            },
            {
                "label": "POD DRAIN",
                "file": ["mtcAgent.log*"],
                "start": "{hostname} force pod drain script launched",
                "stop": "pods drained",
                "max_time_delta": 600
            },
            {
                "label": "test-service-no-pvc outage",
                "file": ["mtcAgent.log*", "availability-test-service.log*"],
                "start": "{hostname} force pod drain script launched",
                "stop": "availability-test-service: Starting periodic write task",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "test-service-with-pvc outage",
                "file": ["mtcAgent.log*", "availability-test-service-with-pvc.log*"],
                "start": "{hostname} force pod drain script launched",
                "stop": "availability-test-service-with-pvc: Starting periodic write task",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "LAZY REBOOT",
                "file": ["mtcClient.log*"],
                "start": "lazy reboot command received",
                "stop": "failsafe reboot script launched",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "BLACKOUT PHASE",
                "file": ["auth.log*", "kern.log*"],
                "start": "notice System is rebooting",
                "stop": "Kernel command line:",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "OS: NETWORK CONFIG PHASE",
                "file": ["kern.log*", "daemon.log*"],
                "start": "Kernel command line:",
                "stop": "Reached target Network is Online",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "OS: PLATFORM SVC CONFIG PHASE",
                "file": ["kern.log*", "daemon.log*"],
                "start": "Kernel command line:",
                "stop": "Reached target Multi-User System",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "Kubelet startup",
                "file": ["daemon.log*"],
                "patterns": ["info Starting Kubernetes Kubelet Server"],
                "max_time_delta": 600
            },
            {
                "label": "PLATFORM READY PHASE",
                "file": ["daemon.log*", "mtcAgent.log*"],
                "start": "Reached target Multi-User System",
                "stop": "Info : controller-0 unlocked-enabled-available",
                "max_time_delta": 600
            },
            {
                "label": "CSI Ready",
                "file": ["daemon.log*"],
                "start": "info Starting Kubernetes Kubelet Server",
                "stop": "kubernetes.io/csi: Register new plugin with name",
                "max_time_delta": 600
            },
            {
                "label": "test-service-no-pvc ready",
                "file": ["daemon.log*", "availability-test-service.log*"],
                "start": "info Starting Kubernetes Kubelet Server",
                "stop": "availability-test-service: Starting periodic write task",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "test-service-with-pvc ready",
                "file": ["daemon.log*", "availability-test-service-with-pvc.log*"],
                "start": "info Starting Kubernetes Kubelet Server",
                "stop": "availability-test-service-with-pvc: Starting periodic write task",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "K8s STARTUP PHASE",
                "file": ["daemon.log*"],
                "start": "info Starting Kubernetes Kubelet Server",
                "stop": "info k8s-pod-recovery.service: Succeeded.",
                "max_time_delta": 600,
                "optional": True
            },
            {
                "label": "Platform Ready",
                "file": ["mtcAgent.log*", "daemon.log*"],
                "start": "Info : controller-0 unlocked-enabled-available",
                "stop": "info k8s-pod-recovery.service: Succeeded.",
                "max_time_delta": 600
            }
        ]

    @staticmethod
    def node_unlock_kpi_blocks() -> List[Dict[str, Any]]:
        """
        Get unlock KPI blocks for non-active controllers (standby/compute).

        Returns:
            List[Dict[str, Any]]: Block definitions for pair mode timing
        """
        return [
            {
                "label": "LOCK HOST",
                "file": ["mtcAgent.log*"],
                "start": "Info : {hostname} Lock Action",
                "stop": "Info : {hostname} Disable Complete",
                "exclude_from_kpi": True
            },
            {
                "label": "UNLOCK HOST",
                "file": ["mtcAgent.log*"],
                "start": "Info : {hostname} Unlock Action",
                "stop": "Info : {hostname} unlocked-enabled-available",
                "exclude_from_kpi": False
            }
        ]
