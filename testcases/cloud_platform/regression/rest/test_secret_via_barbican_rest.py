"""REST API CRUD operations on Barbican secrets."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.barbican.get_barbican_secrets_keywords import GetBarbicanSecretsKeywords


@mark.p1
def test_secret_operations(request) -> None:
    """Test Barbican secret CRUD operations via REST API.

    Test Steps:
        1. List existing secrets
        2. Create a new secret
        3. List secrets again and verify new secret is in the list
        4. Get the created secret and verify
        5. Update the secret payload
        6. Get the secret again and verify
        7. Delete the secret
    """
    barbican = GetBarbicanSecretsKeywords()
    state = {"secret_id": None}

    def _cleanup_secret() -> None:
        """Delete the test secret if it was created."""
        if state["secret_id"]:
            get_logger().log_teardown_step(f"Deleting secret {state['secret_id']}")
            barbican.delete_secret(state["secret_id"])

    request.addfinalizer(_cleanup_secret)

    get_logger().log_test_case_step("List existing secrets")
    list_output = barbican.list_secrets()
    validate_equals(list_output is not None, True, "List secrets returns valid output")

    get_logger().log_test_case_step("Create a new secret")
    create_output = barbican.create_secret(secret_name="test_secret")
    secret_object = create_output.get_secret_object()
    validate_equals(secret_object is not None, True, "Create secret returns valid object")
    validate_equals(secret_object.get_secret_ref() is not None, True, "Created secret has a valid secret_ref")
    state["secret_id"] = secret_object.get_secret_id()
    validate_equals(state["secret_id"] is not None, True, "Created secret has a valid ID")
    get_logger().log_info(f"Secret created: {state['secret_id']}")

    get_logger().log_test_case_step("List secrets and verify new secret is present")
    list_output = barbican.list_secrets()
    secret_refs = [s.get_secret_ref() for s in list_output.get_secret_objects()]
    validate_equals(secret_object.get_secret_ref() in secret_refs, True, "Newly created secret is in the secrets list")

    get_logger().log_test_case_step("Get the created secret and verify")
    get_output = barbican.get_secret(state["secret_id"])
    validate_equals(get_output.get_secret_object().get_secret_id() == state["secret_id"], True, "Get secret returns correct ID")

    get_logger().log_test_case_step("Update the secret payload")
    barbican.update_secret(state["secret_id"], "test_payload")

    get_logger().log_test_case_step("Get secret after update and verify")
    get_output = barbican.get_secret(state["secret_id"])
    validate_equals(get_output.get_secret_object().get_secret_id() == state["secret_id"], True, "Secret ID still valid after update")

    get_logger().log_test_case_step("Delete the secret")
    barbican.delete_secret(state["secret_id"])
    state["secret_id"] = None
