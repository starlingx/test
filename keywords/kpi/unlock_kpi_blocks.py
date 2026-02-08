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
        1. Lock Host: Lock action -> mtcAgent.log Disable complete (excluded from KPI)
        2. Shutdown: mtcAgent.log Unlock action -> daemon.log Service stopped
        3. Blackout: daemon.log Service stopped -> kern.log Kernel boot (excluded from KPI)
        4. OS Startup: kern.log Kernel boot -> daemon.log Multi-user system
        5. Platform Startup: daemon.log Multi-user system -> Host available
        6. K8s Startup: daemon.log CPU plugin started -> Pod recovery done
        
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
                "label": "SHUTDOWN PHASE",
                "file": ["mtcAgent.log*", "daemon.log*"],
                "start": "Info : {hostname} Unlock Action",
                "stop": "info Stopped Service Management API Unit.",
                "exclude_from_kpi": False
            },
            {
                "label": "BLACKOUT PHASE",
                "file": ["daemon.log*", "kern.log*"],
                "start": "info Stopped Service Management API Unit.",
                "stop": "Kernel command line:",
                "exclude_from_kpi": True
            },
            {
                "label": "OS STARTUP PHASE",
                "file": ["kern.log*", "daemon.log*"],
                "start": "Kernel command line:",
                "stop": "Reached target Multi-User System",
                "max_time_delta": 300
            },
            {
                "label": "PLATFORM STARTUP PHASE",
                "file": ["daemon.log*", "nfv-vim.log*"],
                "start": "Reached target Multi-User System",
                "stop": [
                    "nfvi_host_admin_state=unlocked, nfvi_host_oper_state=enabled, nfvi_host_avail_status=available",
                    "nfvi_host_admin_state=unlocked, nfvi_host_oper_state=enabled, nfvi_host_avail_status=degraded"
                ]
            },
            {
                "label": "K8s STARTUP PHASE",
                "file": "daemon.log*",
                "start": "info Started Kubernetes Isolated CPU Plugin Daemon.",
                "stop": "info k8s-pod-recovery.service: Succeeded.",
                "max_time_delta": 1200
            }
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
