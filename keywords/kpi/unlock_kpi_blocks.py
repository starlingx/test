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
        Get unlock KPI blocks for pair mode - measures phase durations.
        
        Phases:
        1. Lock Host Pattern: Initial lock action marker
        2. Lock Host: Lock action -> Disable complete
        3. Shutdown: Unlock action -> System rebooting
        4. Pod Drain: Force pod drain -> Pods drained
        5. Lazy Reboot: Lazy reboot command -> Failsafe reboot (optional)
        6. Blackout: System rebooting -> Kernel boot
        7. OS Network Config: Kernel boot -> Network online
        8. OS Platform Service Config: Kernel boot -> Multi-user system
        9. Platform Ready: Multi-user system -> Host available
        10. K8s Startup: Kubelet starting -> Pod recovery done
        
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
                "stop": "Info : {hostname} Disable Complete"
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
                "max_time_delta": 600
            },
            {
                "label": "OS: NETWORK CONFIG PHASE",
                "file": ["kern.log*", "daemon.log*"],
                "start": "Kernel command line:",
                "stop": "Reached target Network is Online",
                "max_time_delta": 600
            },
            {
                "label": "OS: PLATFORM SVC CONFIG PHASE",
                "file": ["kern.log*", "daemon.log*"],
                "start": "Kernel command line:",
                "stop": "Reached target Multi-User System",
                "max_time_delta": 600
            },
            {
                "label": "K8s STARTUP PHASE",
                "file": ["daemon.log*"],
                "start": "info Starting Kubernetes Kubelet Server",
                "stop": "info k8s-pod-recovery.service: Succeeded.",
                "max_time_delta": 600
            },
            {
                "label": "PLATFORM READY PHASE",
                "file": ["daemon.log*", "mtcAgent.log*"],
                "start": "Reached target Multi-User System",
                "stop": "Info : controller-0 unlocked-enabled-available",
                "max_time_delta": 600
            }
            # {
            #     "label": "K8s STARTUP PHASE",
            #     "file": ["daemon.log*"],
            #     "start": "info Starting Kubernetes Kubelet Server",
            #     "stop": "info k8s-pod-recovery.service: Succeeded.",
            #     "max_time_delta": 600
            # }
        ]

    @staticmethod
    def node_unlock_kpi_blocks() -> List[Dict[str, Any]]:
        """
        Get unlock KPI blocks for pair mode - measures phase durations.
        
        Phases:
        1. Lock Host: Lock action -> mtcAgent.log Disable complete (excluded from KPI)
        2. Unlock Phase: mtcAgent.log Unlock action -> unlocked-enabled-available
        
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
    
    @staticmethod
    def get_sequential_mode_blocks() -> List[Dict[str, Any]]:
        """
        Get unlock KPI blocks for sequential mode - pattern matching in order.
        
        Returns:
            List[Dict[str, Any]]: Block definitions for sequential mode
        """
        return [
            {
                "label": "Unlock Action Staged",
                "file": "sysinv.log*",
                "patterns": ["{hostname} Action staged: unlock"]
            },
            {
                "label": "SHUTDOWN PHASE",
                "file": "daemon.log*",
                "optional": True,
                "patterns": ["Stopped target Graphical Interface"]
            },
            {
                "label": "BLACKOUT PHASE",
                "file": "kern.log*",
                "patterns": ["Kernel command line:"],
                "exclude_from_kpi": True
            },
            {
                "label": "OS STARTUP PHASE",
                "file": "daemon.log*",
                "patterns": ["Reached target Network is Online"]
            },
            {
                "label": "PLATFORM STARTUP PHASE",
                "file": "nfv-vim.log*",
                "optional": False,
                "patterns": [[
                    "nfvi_host_name={hostname}, nfvi_host_admin_state=unlocked, nfvi_host_oper_state=enabled, nfvi_host_avail_status=available",
                    "nfvi_host_name={hostname}, nfvi_host_admin_state=unlocked, nfvi_host_oper_state=enabled, nfvi_host_avail_status=degraded"
                ]]
            },
            {
                "label": "KUBERNETES STARTUP PHASE",
                "file": "daemon.log*",
                "optional": False,
                "patterns": ["k8s-pod-recovery.service: Succeeded."]
            }
        ]
