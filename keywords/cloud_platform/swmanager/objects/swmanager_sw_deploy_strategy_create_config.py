class SwManagerSwDeployStrategyCreateConfig:
    """Configuration class for sw-deploy-strategy create command parameters.
    
    This class encapsulates all the parameters needed to create a software deployment
    strategy using the 'sw-manager sw-deploy-strategy create' command. It provides
    a clean interface for building command arguments and follows the framework's
    Rule 29 (No Variadic Parameters) by using explicit parameter objects.
    
    Example:
        config = SwManagerSwDeployStrategyCreateConfig(
            release="starlingx-26.03.1",
            delete=True,
            controller_apply_type="serial"
        )
        keywords.get_sw_deploy_strategy_create(config)
    """

    def __init__(self, release: str, delete: bool = False, snapshot: bool = False,
                 rollback: bool = False, controller_apply_type: str = None,
                 storage_apply_type: str = None, worker_apply_type: str = None,
                 instance_action: str = None, alarm_restrictions: str = None,
                 max_parallel_worker_hosts: int = None) -> None:
        """Initializes SwManagerSwDeployStrategyCreateConfig.

        Args:
            release (str): The release to be deployed (e.g., 'starlingx-26.03.1').
            delete (bool): If True, delete existing strategy before creating new one.
            snapshot (bool): If True, create snapshot before deployment.
            rollback (bool): If True, create rollback strategy instead of deployment.
            controller_apply_type (str): How to apply to controllers ('serial', 'ignore').
            storage_apply_type (str): How to apply to storage nodes ('serial', 'parallel', 'ignore').
            worker_apply_type (str): How to apply to worker nodes ('serial', 'parallel', 'ignore').
            instance_action (str): Action for instances ('stop-start', 'migrate').
            alarm_restrictions (str): Alarm handling ('strict', 'relaxed', 'permissive').
            max_parallel_worker_hosts (int): Max workers to update simultaneously (2-10).
        """
        # Core deployment parameters
        self.release = release  # Target release for deployment
        self.delete = delete    # Delete existing strategy flag
        self.snapshot = snapshot  # Create snapshot flag
        self.rollback = rollback  # Rollback strategy flag
        
        # Node-specific apply strategies
        self.controller_apply_type = controller_apply_type  # Controller update strategy
        self.storage_apply_type = storage_apply_type        # Storage node update strategy
        self.worker_apply_type = worker_apply_type          # Worker node update strategy
        
        # Deployment behavior settings
        self.instance_action = instance_action              # VM/container handling
        self.alarm_restrictions = alarm_restrictions        # Alarm tolerance level
        self.max_parallel_worker_hosts = max_parallel_worker_hosts  # Parallelism limit

    def build_command_args(self) -> str:
        """Builds command arguments string from configuration.
        
        Converts the configuration object into a space-separated string of
        command-line arguments suitable for the sw-manager command.
        
        Returns:
            str: Command arguments string (e.g., '--delete --controller-apply-type serial').
        """
        args = []
        
        # Boolean flags - add if True
        if self.delete:
            args.append("--delete")
        if self.snapshot:
            args.append("--snapshot")
        if self.rollback:
            args.append("--rollback")
        
        # Node apply type parameters - add if specified
        if self.controller_apply_type:
            args.append(f"--controller-apply-type {self.controller_apply_type}")
        if self.storage_apply_type:
            args.append(f"--storage-apply-type {self.storage_apply_type}")
        if self.worker_apply_type:
            args.append(f"--worker-apply-type {self.worker_apply_type}")
        
        # Deployment behavior parameters - add if specified
        if self.instance_action:
            args.append(f"--instance-action {self.instance_action}")
        if self.alarm_restrictions:
            args.append(f"--alarm-restrictions {self.alarm_restrictions}")
        if self.max_parallel_worker_hosts:
            args.append(f"--max-parallel-worker-hosts {self.max_parallel_worker_hosts}")
        
        return " ".join(args)