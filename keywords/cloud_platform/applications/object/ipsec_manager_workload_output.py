"""Manager rollout, pod ownership and immutable image interpretation."""

import json
import re

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.applications.object.ipsec_policy_images_output import IPsecPolicyImagesOutput
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput


class IPsecManagerWorkloadOutput:
    """Interpret independently refreshed Deployment/ReplicaSet/pod snapshots."""

    def __init__(self, deployment_content: str, replicaset_content: str, pod_content: str):
        """Check current rollout coverage and every owned container.

        Args:
            deployment_content (str): Deployment JSON.
            replicaset_content (str): ReplicaSet list JSON.
            pod_content (str): Pod list JSON.

        """
        self.deployment = json.loads(deployment_content)
        self.replicasets = json.loads(replicaset_content)["items"]
        self.manager_pods = json.loads(pod_content)["items"]

    def get_ready_images(self) -> IPsecPolicyImagesOutput | None:
        """Check current rollout coverage and every owned container.

        Returns:
            IPsecPolicyImagesOutput | None: Images or pending terminating pods.
        """
        images = {}
        deployment = self.deployment
        desired = deployment["spec"].get("replicas", 1)
        status = deployment.get("status", {})
        if desired < 1 or status.get("observedGeneration") != deployment["metadata"].get("generation") or any(status.get(field) != desired for field in ("updatedReplicas", "readyReplicas", "availableReplicas", "replicas")):
            raise KeywordException("Policy manager rollout is not current and ready")
        replicasets = self.replicasets
        owner_uids = {item["metadata"]["uid"] for item in replicasets if any(owner.get("uid") == deployment["metadata"]["uid"] and owner.get("controller") is True for owner in item["metadata"].get("ownerReferences", []))}
        manager_pods = self.manager_pods
        count = 0
        for pod in manager_pods:
            if not any(owner.get("uid") in owner_uids and owner.get("controller") is True for owner in pod["metadata"].get("ownerReferences", [])):
                continue
            if pod["metadata"].get("deletionTimestamp"):
                return None
            statuses = pod.get("status", {}).get("containerStatuses", [])
            if not statuses or not all(item.get("ready") and "running" in item.get("state", {}) for item in statuses) or {item["name"] for item in statuses} != {item["name"] for item in pod["spec"]["containers"]}:
                raise KeywordException("Policy manager has stale or unready pods")
            count += 1
            images[f"manager/{pod['metadata']['name']}"] = PodJsonOutput(pod).get_container_digests()
        if count != desired or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for containers in images.values() for digest in containers.values()):
            raise KeywordException("Missing manager coverage or immutable image identity")
        return IPsecPolicyImagesOutput(images)
