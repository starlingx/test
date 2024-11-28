from keywords.k8s.node.object.kubectl_node_description_output import KubectlNodeDescriptionOutput


def test_node_description_output_parser():
    """
    Tests the node_description_output_parser
    Returns:

    """

    describe_node_output = (
        'Name:               controller-0\n',
        'Roles:              control-plane\n',
        'Labels:             beta.kubernetes.io/arch=amd64\n',
        '                    beta.kubernetes.io/os=linux\n',
        '                    kubernetes.io/arch=amd64\n',
        '                    kubernetes.io/hostname=controller-0\n',
        '                    kubernetes.io/os=linux\n',
        '                    node-role.kubernetes.io/control-plane=\n',
        '                    node.kubernetes.io/exclude-from-external-load-balancers=\n',
        'Annotations:        csi.volume.kubernetes.io/nodeid: {"cephfs.csi.ceph.com":"controller-0","rbd.csi.ceph.com":"controller-0"}\n',
        '                    kubeadm.alpha.kubernetes.io/cri-socket: unix:///var/run/containerd/containerd.sock\n',
        '                    node.alpha.kubernetes.io/ttl: 0\n',
        '                    projectcalico.org/IPv6Address: abcd::2/64\n',
        '                    volumes.kubernetes.io/controller-managed-attach-detach: true\n',
        'CreationTimestamp:  Mon, 03 Jun 2024 18:14:59 +0000\n',
        'Taints:             <none>\n',
        'Unschedulable:      false\n',
        'Lease:\n',
        '    HolderIdentity:  controller-0\n',
        '    AcquireTime:     <unset>\n',
        '    RenewTime:       Thu, 25 Jul 2024 14:00:50 +0000\n',
        'Conditions:\n',
        '    Type                 Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message\n',
        '    ----                 ------  -----------------                 ------------------                ------                       -------\n',
        '    NetworkUnavailable   False   Tue, 23 Jul 2024 20:39:45 +0000   Tue, 23 Jul 2024 20:39:45 +0000   CalicoIsUp                   Calico is running on this node\n',
        '    MemoryPressure       False   Thu, 25 Jul 2024 14:00:49 +0000   Mon, 03 Jun 2024 18:14:57 +0000   KubeletHasSufficientMemory   kubelet has sufficient memory available\n',
        '    DiskPressure         False   Thu, 25 Jul 2024 14:00:49 +0000   Mon, 03 Jun 2024 18:14:57 +0000   KubeletHasNoDiskPressure     kubelet has no disk pressure\n',
        '    PIDPressure          False   Thu, 25 Jul 2024 14:00:49 +0000   Mon, 03 Jun 2024 18:14:57 +0000   KubeletHasSufficientPID      kubelet has sufficient PID available\n',
        '    Ready                True    Thu, 25 Jul 2024 14:00:49 +0000   Tue, 23 Jul 2024 20:39:28 +0000   KubeletReady                 kubelet is posting ready status\n',
        'Addresses:\n',
        '    InternalIP:  abcd::2\n',
        '    Hostname:    controller-0\n',
        'Capacity:\n',
        '  cpu:                24\n',
        '  ephemeral-storage:  10218772Ki\n',
        '  hugepages-1Gi:      0\n',
        '  hugepages-2Mi:      0\n',
        '  memory:             129003248Ki\n',
        '  pods:               110\n',
        'Allocatable:\n',
        '  cpu:                22\n',
        '  ephemeral-storage:  9417620260\n',
        '  hugepages-1Gi:      0\n',
        '  hugepages-2Mi:      0\n',
        '  memory:             118660848Ki\n',
        '  pods:               110\n',
        ' System Info:\n',
        '  Machine ID:                  aaa9999a76584037a9a7fd11d22284ba\n',
        '  System UUID:                 4c4c4544-0057-4b10-8351-a1a04f505233\n',
        '  Boot ID:                     03d4d256-b334-408f-8c25-95d888df57dd\n',
        '  Kernel Version:              5.10.0-6-amd64\n',
        '  OS Image:                    Debian GNU/Linux 11 (bullseye)\n',
        '  Operating System:            linux\n',
        '  Architecture:                amd64\n',
        '  Container Runtime Version:   containerd://1.6.21\n',
        '  Kubelet Version:             v1.28.4\n',
        '  Kube-Proxy Version:          v1.28.4\n',
        'Non-terminated Pods:           (22 in total)\n',
        '  Namespace                    Name                                               CPU Requests  CPU Limits  Memory Requests  Memory Limits  Age\n',
        '  ---------                    ----                                               ------------  ----------  ---------------  -------------  ---\n',
        '  cert-manager                 cm-cert-manager-588d948bcd-gpxd6                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  cert-manager                 cm-cert-manager-cainjector-5df9bd5969-rztg6        0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  cert-manager                 cm-cert-manager-webhook-5cbd9c8648-2kkmb           0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  flux-helm                    helm-controller-797b654649-mzgjg                   0 (0%)        1 (4%)      64Mi (0%)        1Gi (0%)       51d\n',
        '  flux-helm                    source-controller-7d48c57c48-vkt9d                 0 (0%)        1 (4%)      64Mi (0%)        1Gi (0%)       51d\n',
        '  kube-system                  calico-kube-controllers-7958849499-vbvmt           0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  calico-node-xv5zp                                  0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  cephfs-nodeplugin-f4bkv                            0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  cephfs-provisioner-7dd49b59c5-xq6dw                0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  coredns-559fbd6c7b-gcfhs                           0 (0%)        0 (0%)      70Mi (0%)        170Mi (0%)     51d\n',
        '  kube-system                  ic-nginx-ingress-ingress-nginx-controller-b4d6x    0 (0%)        0 (0%)      90Mi (0%)        0 (0%)         51d\n',
        '  kube-system                  kube-apiserver-controller-0                        0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  kube-controller-manager-controller-0               0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  kube-multus-ds-amd64-bzr9x                         0 (0%)        0 (0%)      50Mi (0%)        50Mi (0%)      51d\n',
        '  kube-system                  kube-proxy-fg9b6                                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  kube-scheduler-controller-0                        0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  kube-sriov-cni-ds-amd64-47h7c                      0 (0%)        0 (0%)      50Mi (0%)        50Mi (0%)      51d\n',
        '  kube-system                  rbd-nodeplugin-kq7mh                               0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  rbd-provisioner-7f6c9b6467-cqbl4                   0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  kube-system                  volume-snapshot-controller-0                       0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  platform-deployment-manager  dm-monitor-565c4b7977-cz289                        0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        '  platform-deployment-manager  platform-deployment-manager-5c66f84595-4wml6       0 (0%)        0 (0%)      0 (0%)           0 (0%)         51d\n',
        'Allocated resources:\n',
        '  (Total limits may be over 100 percent, i.e., overcommitted.)\n',
        '  Resource           Requests    Limits\n',
        '  --------           --------    ------\n',
        '  cpu                0 (0%)      2 (9%)\n',
        '  memory             388Mi (0%)  2318Mi (2%)\n',
        '  ephemeral-storage  0 (0%)      0 (0%)\n',
        '  hugepages-1Gi      0 (0%)      0 (0%)\n',
        '  hugepages-2Mi      0 (0%)      0 (0%)\n',
        'Events:              <none>\n',
    )

    node_description_object = KubectlNodeDescriptionOutput(describe_node_output).get_node_description()

    assert node_description_object.get_name() == "controller-0"
    assert node_description_object.get_roles() == "control-plane"

    labels = node_description_object.get_labels()
    assert len(labels) == 7
    assert labels[0] == "beta.kubernetes.io/arch=amd64"
    assert labels[6] == "node.kubernetes.io/exclude-from-external-load-balancers="

    annotations = node_description_object.get_annotations()
    assert len(annotations) == 5
    assert annotations[0] == 'csi.volume.kubernetes.io/nodeid: {"cephfs.csi.ceph.com":"controller-0","rbd.csi.ceph.com":"controller-0"}'
    assert annotations[4] == 'volumes.kubernetes.io/controller-managed-attach-detach: true'

    assert node_description_object.get_creation_timestamp() == "Mon, 03 Jun 2024 18:14:59 +0000"

    kubernetes_node_capacity = node_description_object.get_capacity()
    assert kubernetes_node_capacity.get_cpu() == 24
    assert kubernetes_node_capacity.get_ephemeral_storage() == "10218772Ki"
    assert kubernetes_node_capacity.get_hugepages_1gi() == "0"
    assert kubernetes_node_capacity.get_hugepages_2mi() == "0"
    assert kubernetes_node_capacity.get_memory() == "129003248Ki"
    assert kubernetes_node_capacity.get_pods() == 110

    kubernetes_node_allocatable = node_description_object.get_allocatable()
    assert kubernetes_node_allocatable.get_cpu() == 22
    assert kubernetes_node_allocatable.get_ephemeral_storage() == "9417620260"
    assert kubernetes_node_allocatable.get_hugepages_1gi() == "0"
    assert kubernetes_node_allocatable.get_hugepages_2mi() == "0"
    assert kubernetes_node_allocatable.get_memory() == "118660848Ki"
    assert kubernetes_node_allocatable.get_pods() == 110

    allocated_resources = node_description_object.get_allocated_resources()
    assert allocated_resources.get_cpu().get_limits() == "2 (9%)"
    assert allocated_resources.get_cpu().get_requests() == "0 (0%)"
    assert allocated_resources.get_cpu().get_resource() == "cpu"
    assert allocated_resources.get_memory().get_limits() == "2318Mi (2%)"
