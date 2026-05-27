#!/bin/bash
# Configures kubernetes auth, policy, role, and KV v2 secret engine for vault testing.
# Used by: testcases/cloud_platform/regression/security/test_vault.py

set -e

# Get root token from kubernetes secret
ROOT_TOKEN=$(kubectl get secret cluster-key-root -n vault -o jsonpath="{.data.strdata}" | base64 --decode)

# Get kubernetes API server address from vault pod
KUBERNETES_PORT_443_TCP_ADDR=$(kubectl exec -n vault sva-vault-0 -- sh -c 'echo $KUBERNETES_PORT_443_TCP_ADDR')

# Wrap IPv6 address in brackets
if [[ $KUBERNETES_PORT_443_TCP_ADDR =~ .*:.* ]]; then
    KUBERNETES_PORT_443_TCP_ADDR="[${KUBERNETES_PORT_443_TCP_ADDR}]"
fi

# Save the CA cert for REST API calls
echo $(kubectl get secrets -n vault vault-ca -o jsonpath='{.data.tls\.crt}') | base64 --decode > /home/sysadmin/vault_ca.pem

# Enable kubernetes auth
curl --cacert /home/sysadmin/vault_ca.pem \
    --header "X-Vault-Token:$ROOT_TOKEN" \
    --request POST \
    --data '{"type":"kubernetes","description":"kubernetes auth"}' \
    https://sva-vault.vault.svc.cluster.local:8200/v1/sys/auth/kubernetes 2>/dev/null || true

# Configure kubernetes auth (modern: vault reads cert and token from pod mounts)
curl --cacert /home/sysadmin/vault_ca.pem \
    --header "X-Vault-Token:$ROOT_TOKEN" \
    --request POST \
    --data '{"kubernetes_host": "'"https://$KUBERNETES_PORT_443_TCP_ADDR:443"'"}' \
    https://sva-vault.vault.svc.cluster.local:8200/v1/auth/kubernetes/config 2>/dev/null

# Create the policy for basic-secret path (KV v2 uses /data/ prefix)
curl --cacert /home/sysadmin/vault_ca.pem \
    --header "X-Vault-Token:$ROOT_TOKEN" \
    -H "Content-Type: application/json" \
    --request PUT \
    -d '{"policy":"path \"secret/data/basic-secret/*\" {capabilities = [\"read\"]}"}' \
    https://sva-vault.vault.svc.cluster.local:8200/v1/sys/policy/basic-secret-policy 2>/dev/null

# Create the role with policy and namespace
curl --cacert /home/sysadmin/vault_ca.pem \
    --header "X-Vault-Token:$ROOT_TOKEN" \
    --request POST \
    --data '{"bound_service_account_names": "basic-secret", "bound_service_account_namespaces": "pvtest", "policies": "basic-secret-policy", "max_ttl": "1800000"}' \
    https://sva-vault.vault.svc.cluster.local:8200/v1/auth/kubernetes/role/basic-secret-role 2>/dev/null

# Enable the KV v2 secret engine
curl --cacert /home/sysadmin/vault_ca.pem \
    --header "X-Vault-Token:$ROOT_TOKEN" \
    --request POST \
    --data '{"type": "kv","options":{"version":"2"}}' \
    https://sva-vault.vault.svc.cluster.local:8200/v1/sys/mounts/secret 2>/dev/null || true
