from keywords.k8s.secret.object.kubectl_get_secret_table_parser import KubectlGetSecretsTableParser
from keywords.k8s.secret.object.kubectl_secret_object import KubectlSecretObject


class KubectlGetSecretOutput:
    """Parses and stores the output of `kubectl get secret` commands."""

    def __init__(self, kubectl_get_secrets_output: str):
        """Represents parsed output from `kubectl get secret` command

        Args:
            kubectl_get_secrets_output (str): Raw string output from running "kubectl get secrets" command
        """
        self.kubectl_secret: [KubectlSecretObject] = []
        kubectl_get_secrets_table_parser = KubectlGetSecretsTableParser(kubectl_get_secrets_output)
        output_values_list = kubectl_get_secrets_table_parser.get_output_values_list()

        for secret_dict in output_values_list:
            if "NAME" not in secret_dict:
                raise ValueError(f"There is no NAME associated with the secret: {secret_dict}")

            secret = KubectlSecretObject(secret_dict["NAME"])

            if "TYPE" in secret_dict:
                secret.set_type(secret_dict["TYPE"])

            if "DATA" in secret_dict:
                secret.set_data(secret_dict["DATA"])

            if "AGE" in secret_dict:
                secret.set_age(secret_dict["AGE"])

            self.kubectl_secret.append(secret)

    def get_secrets(self) -> list[KubectlSecretObject]:
        """Return parsed secret objects.

        Returns:
            list[KubectlSecretObject]: List of parsed secret objects.
        """
        return self.kubectl_secret
