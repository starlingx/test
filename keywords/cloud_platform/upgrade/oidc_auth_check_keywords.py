"""Keywords for the oidc-auth-apps authentication check.

Used by the platform-upgrade compatibility test.

The functional truth for oidc-auth-apps is that a user can authenticate **from scratch** and then
act on the Kubernetes API **with the resulting token**. Checking that the pods are running proves
considerably less: in several reported upgrade defects the pods were up and the application
reported ``applied`` while authentication was broken.

The emphasis on *with the resulting token* is not rhetorical. An earlier revision of this check
read the pod list through the framework's default kubeconfig, which is
``/etc/kubernetes/admin.conf``. That file is group-readable by ``sys_protected``, and the test
user is in that group, so ``kubectl`` authenticated as ``kubernetes-admin`` over X.509 and the
assertion passed without the OIDC token being involved at all - it would have passed with dex
deleted. Two things now make that impossible to reintroduce silently:

* every Kubernetes read on the authenticated session passes ``USER_KUBECONFIG`` explicitly, and
* the identity is asserted with ``kubectl auth whoami`` before anything else is read, so a
  fallback to the administrator certificate fails the check instead of satisfying it.

``kubectl auth whoami`` is also the correct reader for the Kubernetes username, which cannot be
derived from the login name. The apiserver prefixes the username with the issuer URL unless
``oidc-username-claim`` is ``email``, so the same user is ``<issuer>#<name>`` on one lab and a bare
name on another. Measured on two labs that differ in exactly that way.

Established by measurement rather than assumed: a login does survive the deploy, but not instantly in
both directions. It returned on the first attempt after an upgrade and after activate, and took
around 90 seconds after a rollback, which is what sizes the retry window below.
"""

import time
from typing import Callable

from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals, validate_greater_than, validate_not_equals, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.security.keycloak.objects.keycloak_kubectl_result_object import KubectlResultObject
from keywords.cloud_platform.security.oidc.oidc_auth_keywords import OidcAuthKeywords
from keywords.k8s.auth.kubectl_auth_keywords import KubectlAuthKeywords
from keywords.k8s.clusterrole.kubectl_create_clusterrole_keywords import KubectlCreateClusterRoleKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class OidcAuthCheckKeywords(BaseKeyword):
    """Authenticate as an OIDC user from scratch and act on the Kubernetes API as that user."""

    NAMESPACE = "kube-system"
    DEX_DEPLOYMENT = "oidc-dex"
    CLIENT_DEPLOYMENT = "stx-oidc-client"
    # Written by kubeconfig-setup for the authenticated user. Passed explicitly to every read made
    # on that user's session: the framework default is the administrator kubeconfig, which this
    # user can read, and relying on the default is what made an earlier revision of this check
    # pass without using the token.
    USER_KUBECONFIG = "$HOME/.kube/config"
    # The identity the administrator certificate in /etc/kubernetes/admin.conf presents. If the
    # authenticated session ever reports this, the token is not being used and the check must fail.
    ADMIN_IDENTITY = "kubernetes-admin"
    # The application ships three charts and the platform requires all three. secret-observer is
    # the cron job that restarts the other two when the certificate secret changes, so an upgrade
    # that replaces certificates is exactly what breaks it. Four prior upgrade cycles of this
    # application called for this check explicitly.
    SECRET_OBSERVER_CRONJOB = "secret-observer-cron-job"
    # The four flags the apiserver must actually be running with. Read from the static pod
    # manifest rather than from the service-parameter list: the parameter can be set while the
    # apiserver has not been restarted to pick it up, which is the state one lab was found in.
    APISERVER_OIDC_FLAGS = ("oidc-issuer-url", "oidc-client-id", "oidc-username-claim", "oidc-groups-claim")
    APISERVER_MANIFEST = "/etc/kubernetes/manifests/kube-apiserver.yaml"
    # This test's own RBAC objects. Named for this test so no other suite's resources are touched
    # or depended on: three merged suites share a cluster-admin binding for the same subject, and
    # two of them delete it in their finalizers.
    SCOPED_CLUSTERROLE = "oidc-upgrade-compat-pod-reader"
    SCOPED_BINDING = "oidc-upgrade-compat-pod-reader-binding"
    # The operation that must be refused. Read-only, namespaced, and not granted by the narrow
    # ClusterRole above, so a refusal is unambiguous and nothing is mutated to find out.
    DENIED_RESOURCE = "secrets"
    # Measured on a live system, and the two directions are not alike. The upgrade half recovered on the
    # first attempt - 1.08 s after the reboot into the new release and 9 s after activate - but the
    # rollback half took 94 s and four attempts. An earlier revision set 120 s from the upgrade
    # numbers alone, which left 26 s of margin against one observation.
    AUTH_TIMEOUT = 300
    AUTH_POLL_INTERVAL = 15

    def __init__(self, ssh_connection: SSHConnection):
        """Instance of the class.

        Args:
            ssh_connection (SSHConnection): connection to the active controller, used for the
                cluster-side reads made as the administrator. The authentication itself runs over
                its own session opened as the OIDC user.

        """
        self.ssh_connection = ssh_connection
        self.resources = KubectlGetResourceKeywords(ssh_connection)
        self.bindings = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
        # One instance serves every phase of a test, so the session is tracked per phase and closed
        # by that phase's finalizer. A shared attribute would let a later phase's cleanup close a
        # session an earlier phase still believed it owned.
        self._sessions = {}

    def validate_preconditions(self) -> None:
        """Assert the lab is configured for OIDC, naming whatever is missing.

        This check does not configure OIDC. Setting the apiserver's OIDC service parameters
        restarts the apiserver, and issuing the application's certificate is a cert-manager
        operation, so both belong to lab preparation rather than to a test that is measuring an
        upgrade. Failing with a sentence that names the missing piece beats a mid-phase
        authentication timeout that reads like a product defect.

        Raises:
            KeywordException: when the apiserver is not running with the OIDC flags.

        """
        manifest = self.ssh_connection.send_as_sudo_non_interactive(f"cat {self.APISERVER_MANIFEST}")
        manifest_text = "\n".join(manifest) if isinstance(manifest, list) else str(manifest)
        missing = [flag for flag in self.APISERVER_OIDC_FLAGS if f"--{flag}=" not in manifest_text]
        if missing:
            raise KeywordException(f"this lab is not configured for OIDC: the apiserver is not running with " f"{', '.join(missing)}. Configure the kube_apiserver OIDC service parameters and " f"run 'system service-parameter-apply kubernetes', which restarts the apiserver.")

        secret_type = self.resources.get_resource_field("secret", "oidc-auth-apps-certificate", "{.type}", namespace=self.NAMESPACE)
        validate_greater_than(
            len(secret_type.strip()),
            0,
            f"the oidc-auth-apps-certificate secret must exist in {self.NAMESPACE}; it is issued by cert-manager and the application mounts it",
        )

    def validate_oidc_access(self, request: FixtureRequest, phase: str, username: str, password: str, oam_ip: str) -> dict:
        """Authenticate from scratch as the OIDC user and act on the API as that user.

        The session is opened fresh, used, and closed as the last act of the check rather than
        being left for test teardown: a session left open holds an SSH connection to the lab across
        a host reboot, and the reboot is the next thing the upgrade does. A finalizer is registered
        as well, so the session is still closed if an assertion fails part-way through.

        Args:
            request (FixtureRequest): used to register cleanup for the failure path.
            phase (str): where in the upgrade this is running, for assertion messages and so one
                phase's cleanup cannot close another's session. For example "pre".
            username (str): the LDAP login name of the OIDC user.
            password (str): that user's password.
            oam_ip (str): lab OAM floating address to SSH to.

        Returns:
            dict: observations from this phase, with keys ``username`` (the Kubernetes username the
                apiserver resolved), ``dex_image`` and ``client_image``. Observations, not
                expectations; the test compares them across phases.

        """
        request.addfinalizer(self._close_finalizer(phase))
        self._authenticate_with_retry(phase, username, password, oam_ip)
        session = self._sessions[phase]

        # Identity first. If this reports the administrator certificate, the token is not in play
        # and nothing read afterwards would mean anything.
        resolved_username = self._resolved_username(session, phase)
        validate_not_equals(
            resolved_username,
            self.ADMIN_IDENTITY,
            f"[{phase}] the authenticated session must act as the OIDC user, not the administrator certificate identity '{self.ADMIN_IDENTITY}'",
        )

        # Acting on the API with that token is the assertion. A token that authenticates but
        # authorizes nothing would pass a login-only check, and that is what a missing or
        # wrongly-subjected role binding produces. Both an allowed and a refused operation are
        # asserted: an allowed-only check passes on a cluster whose authorization has failed open.
        self.validate_denial_is_not_vacuous(phase, session)
        self.validate_scoped_authorization(phase, session, resolved_username)

        observations = {
            "username": resolved_username,
            "dex_image": self._deployment_image(self.DEX_DEPLOYMENT, phase),
            "client_image": self._deployment_image(self.CLIENT_DEPLOYMENT, phase),
        }
        self._close_session(phase)
        return observations

    def validate_apiserver_oidc_flags_in_effect(self, phase: str) -> None:
        """Assert the apiserver is running with all four OIDC flags.

        Guards the defect class where the service parameters are present in configuration but the
        apiserver has not been restarted to enforce them, so authentication silently stops working
        while the configuration still looks correct. Read from the static pod manifest, which is
        what the apiserver actually started from.

        Args:
            phase (str): where in the upgrade this is running, for the assertion message.

        """
        # Read the running process, not the manifest. The manifest is what the apiserver was
        # started from; the defect being guarded against is precisely that the two have diverged
        # because a parameter was changed without the apiserver being restarted.
        argv = self.ssh_connection.send_as_sudo_non_interactive("ps -C kube-apiserver -o args= | head -1")
        argv_text = "\n".join(argv) if isinstance(argv, list) else str(argv)
        validate_str_contains(argv_text, "kube-apiserver", f"[{phase}] the kube-apiserver process must be running to inspect its arguments")
        for flag in self.APISERVER_OIDC_FLAGS:
            validate_equals(
                f"--{flag}=" in argv_text,
                True,
                f"[{phase}] the running apiserver process must have --{flag} in its arguments",
            )

    def validate_secret_observer_is_scheduled(self, phase: str) -> None:
        """Assert the secret-observer cron job is present and not suspended.

        secret-observer restarts stx-oidc-client and oidc-dex when the certificate secret changes.
        An upgrade replaces certificates, so this is the component most likely to be broken by one,
        and four previous upgrade cycles of this application called for it explicitly.

        Args:
            phase (str): where in the upgrade this is running, for the assertion message.

        """
        schedule = self.resources.get_resource_field("cronjob", self.SECRET_OBSERVER_CRONJOB, "{.spec.schedule}", namespace=self.NAMESPACE)
        validate_greater_than(
            len(schedule.strip()),
            0,
            f"[{phase}] the {self.SECRET_OBSERVER_CRONJOB} cron job must exist with a schedule",
        )
        suspended = self.resources.get_resource_field("cronjob", self.SECRET_OBSERVER_CRONJOB, "{.spec.suspend}", namespace=self.NAMESPACE)
        # kubectl renders an unset boolean as an empty string, so absence and false look alike. The
        # schedule read above is what distinguishes an absent cron job from a healthy one.
        validate_equals(
            suspended.strip().lower() in ("", "false"),
            True,
            f"[{phase}] the {self.SECRET_OBSERVER_CRONJOB} cron job must not be suspended",
        )

    def suspend_broad_access(self, username: str, suspended_out: list) -> None:
        """Narrow the subject's authorization so that a denial is observable, and restore it after.

        A denied operation is what proves authorization is actually being evaluated. An
        allowed-only check passes just as happily on a cluster whose authorization has failed open.
        The labs bind this subject to ``cluster-admin``, so nothing can be refused and the denial
        would be vacuous.

        Broad bindings are therefore suspended for the duration and recreated afterwards, and the
        subject is granted a narrow ClusterRole instead. Only bindings whose sole subject is this
        user are touched: a binding shared with other subjects cannot be recreated faithfully from
        what kubectl reports here, so it is left alone, and the precondition below then fails with a
        message naming it rather than silently reporting a vacuous denial.

        The finalizer is registered before anything is changed, so a failure part-way through still
        restores what was there.

        The caller owns the list and registers the restore before calling this, rather than
        receiving a return value afterwards. Two reasons, both about not stranding a real lab:
        pytest runs finalizers last-in-first-out so the restore has to be registered before the
        release restore, and a list handed in can be acted on even if this method raises partway
        through. Returning the snapshot at the end meant a failure mid-way lost the record of what
        had already been removed.

        For the same reason the replacement grant is created before anything is deleted, and each
        binding is recorded before it is removed rather than after.

        Args:
            username (str): the Kubernetes username, as resolved by the apiserver.
            suspended_out (list): appended to with each ``(binding_name, clusterrole_name)`` pair
                as it is suspended. Owned by the caller so the restore can always see it.

        """
        # Before any deletion: if creating the replacement grant fails, nothing has been removed.
        KubectlCreateClusterRoleKeywords(self.ssh_connection).create_clusterrole(self.SCOPED_CLUSTERROLE, ["get", "list"], ["pods"])
        for binding_name, role in self._sole_subject_bindings(username):
            # Recorded before the delete, so a failure in the delete still leaves the caller able
            # to restore it.
            suspended_out.append((binding_name, role))
            get_logger().log_info(f"suspending the broad binding '{binding_name}' so a denial is observable; it is restored on teardown")
            self.bindings.delete_clusterrolebinding(binding_name)

    def restore_access(self, suspended: list, username: str) -> None:
        """Remove this test's grant and recreate the bindings it suspended.

        Best effort and never raises: this is housekeeping, and reporting a cleanup problem as the
        test result would hide the real outcome.

        Args:
            suspended (list): the pairs returned by ``suspend_broad_access``.
            username (str): the subject to recreate them for.

        """
        # Each item is restored independently. Sharing one try meant the first failure abandoned
        # every remaining binding, which on a shared lab leaves a subject with its access stripped
        # and no record of what was removed.
        for binding_name, role in suspended:
            try:
                self.bindings.create_clusterrolebinding_for_user(binding_name, role, username)
                get_logger().log_info(f"restored the broad binding '{binding_name}' -> {role}")
            except Exception as restore_error:  # noqa: BLE001 - keep restoring the rest
                get_logger().log_info(f"FAILED to restore the broad binding '{binding_name}' -> {role} for '{username}': {restore_error}. Restore it by hand.")
        for name, deleter in ((self.SCOPED_BINDING, self.bindings.delete_clusterrolebinding),):
            try:
                deleter(name)
            except Exception as cleanup_error:  # noqa: BLE001 - housekeeping must not mask a failure
                get_logger().log_info(f"could not remove this test's '{name}': {cleanup_error}")
        try:
            KubectlCreateClusterRoleKeywords(self.ssh_connection).delete_clusterrole(self.SCOPED_CLUSTERROLE)
        except Exception as role_error:  # noqa: BLE001 - housekeeping must not mask a failure
            get_logger().log_info(f"could not remove this test's ClusterRole: {role_error}")

    def read_resolved_username(self, username: str, password: str, oam_ip: str) -> str:
        """Authenticate once, read the Kubernetes username, and close the session again.

        Needed before the phases begin: the username is what the RBAC snapshot and grant are keyed
        on, and the snapshot has to happen before the first phase asserts a denial. It cannot be
        derived from the login name, since the apiserver prefixes it with the issuer URL unless the
        configured claim is ``email``.

        Args:
            username (str): LDAP login name.
            password (str): that user's password.
            oam_ip (str): lab OAM floating address.

        Returns:
            str: the Kubernetes username the apiserver resolved.

        """
        phase = "resolve"
        self._authenticate_with_retry(phase, username, password, oam_ip)
        try:
            return self._resolved_username(self._sessions[phase], phase)
        finally:
            self._close_session(phase)

    def validate_scoped_authorization(self, phase: str, session: SSHConnection, username: str) -> None:
        """Assert one allowed and one denied operation, using the user's own token for both.

        The binding is recreated here rather than once for the whole test. The keyword is
        idempotent, so this costs nothing and removes any assumption that RBAC objects survive a
        deploy and its rollback - a rollback can restore an earlier etcd state.

        Args:
            phase (str): where in the upgrade this is running, for the assertion messages.
            session (SSHConnection): the authenticated session belonging to this phase.
            username (str): the Kubernetes username, as resolved by the apiserver.

        """
        self.bindings.create_clusterrolebinding_for_user(self.SCOPED_BINDING, self.SCOPED_CLUSTERROLE, username)

        pods = KubectlGetPodsKeywords(session, kubeconfig_path=self.USER_KUBECONFIG).get_pods(self.NAMESPACE)
        validate_greater_than(
            len(pods.get_pods()),
            0,
            f"[{phase}] the granted operation must succeed: '{username}' may list pods in {self.NAMESPACE} using its own token",
        )

        denied_output = session.send(f"export KUBECONFIG={self.USER_KUBECONFIG};kubectl get {self.DENIED_RESOURCE} -n {self.NAMESPACE} 2>&1; true")
        denied_result = KubectlResultObject()
        denied_result.set_output("\n".join(denied_output) if isinstance(denied_output, list) else str(denied_output))
        # Specifically Forbidden, and not merely unsuccessful. A failed authentication answers 401
        # Unauthorized, which is also not a success, so a check for "did not succeed" would pass
        # with authentication completely dead - the same fail-open shape this check exists to
        # avoid. Forbidden means the apiserver authenticated the token and then refused the action,
        # which is the only outcome that proves authorization is being evaluated.
        # Specifically Forbidden, judged by the result object rather than by matching text here. A
        # failed authentication answers 401 Unauthorized, which is also not a success, so a check
        # for "did not succeed" would report a healthy denial on a cluster where nobody can log in.
        validate_equals(
            denied_result.is_kubectl_forbidden(),
            True,
            f"[{phase}] the ungranted operation must be refused as Forbidden, not merely fail: '{username}' must not read {self.DENIED_RESOURCE} in {self.NAMESPACE}",
        )
        validate_str_contains(
            denied_result.get_output(),
            self.DENIED_RESOURCE,
            f"[{phase}] the refusal must name the resource that was refused, confirming it is this operation being denied",
        )

    def validate_denial_is_not_vacuous(self, phase: str, session: SSHConnection) -> None:
        """Assert the subject cannot already perform the operation that must be refused.

        Without this a leftover broad binding would make the denial below prove nothing. The
        keyword raises rather than answering when the question cannot be evaluated, so an
        unreachable apiserver fails here instead of being mistaken for a denial.

        Args:
            phase (str): where in the upgrade this is running, for the assertion message.
            session (SSHConnection): the authenticated session belonging to this phase.

        """
        answer = KubectlAuthKeywords(session, kubeconfig_path=self.USER_KUBECONFIG).can_i("list", self.DENIED_RESOURCE, namespace=self.NAMESPACE)
        validate_equals(
            answer.is_denied(),
            True,
            f"[{phase}] the subject must not already be able to read {self.DENIED_RESOURCE}, or the denial below proves nothing. A broad binding is still in effect",
        )

    def _sole_subject_bindings(self, username: str) -> list:
        """Find the cluster role bindings whose only subject is this user.

        Args:
            username (str): the Kubernetes username to match.

        Returns:
            list: ``(binding_name, clusterrole_name)`` pairs, which is everything needed to
                recreate them.

        """
        # Through the existing escape hatch rather than a hand-built command, which also
        # removes the inlined administrator kubeconfig path. An empty resource name lists them
        # all. get_resource_field documents itself as the escape hatch for resource types with
        # no dedicated Output object, which clusterrolebinding is.
        text = self.resources.get_resource_field(
            "clusterrolebinding",
            "",
            '{range .items[*]}{.metadata.name}|{.roleRef.name}|{range .subjects[*]}{.kind}:{.name},{end}{"\\n"}{end}',
        )
        matches = []
        for line in text.splitlines():
            parts = line.strip().split("|")
            if len(parts) != 3:
                continue
            subjects = [subject for subject in parts[2].split(",") if subject]
            # Only a lone User subject is touched. A Group or ServiceAccount binding would be
            # recreated as --user= and so silently changed into something else, and a binding with
            # several subjects cannot be reproduced from this listing at all.
            if subjects == [f"User:{username}"]:
                matches.append((parts[0], parts[1]))
        return matches

    def _resolved_username(self, session: SSHConnection, phase: str) -> str:
        """Read the Kubernetes username the apiserver resolved for the authenticated session.

        Delegated to KubectlAuthKeywords, which refuses an answer that is not a username rather
        than returning one. The user's own kubeconfig is named explicitly: the framework default is
        the administrator kubeconfig, which this user can read, so a read that did not name it
        would authenticate over X.509 and report an identity unrelated to the token.

        Args:
            session (SSHConnection): the authenticated session.
            phase (str): the phase, for the failure message.

        Returns:
            str: the resolved Kubernetes username.

        Raises:
            KeywordException: when the username cannot be read.

        """
        try:
            return KubectlAuthKeywords(session, kubeconfig_path=self.USER_KUBECONFIG).whoami().get_username()
        except KeywordException as read_error:
            raise KeywordException(f"[{phase}] {read_error}") from read_error

    def _authenticate_with_retry(self, phase: str, username: str, password: str, oam_ip: str) -> None:
        """Open a session as the OIDC user and authenticate, retrying for a bounded window.

        Only the authentication is retried, and only for the window above. The rollback direction
        was measured taking 94 s and four attempts, so a short window would make the post-rollback
        phase flaky; a much longer one would only delay a real failure.

        Args:
            phase (str): the phase this belongs to.
            username (str): LDAP login name.
            password (str): that user's password.
            oam_ip (str): lab OAM floating address.

        Raises:
            KeywordException: when authentication does not succeed within the window.

        """
        deadline = time.time() + self.AUTH_TIMEOUT
        attempt = 0
        last_error = ""
        while time.time() < deadline:
            attempt += 1
            try:
                session = self._open_user_session(oam_ip, username, password)
                self._sessions[phase] = session
                # authenticate_ldap_user runs kubeconfig-setup as its first step, so calling it
                # here as well would run it twice per attempt.
                OidcAuthKeywords(session).authenticate_ldap_user(password)
                if attempt > 1:
                    get_logger().log_info(f"[{phase}] OIDC authentication succeeded on attempt {attempt}")
                return
            except (KeywordException, AssertionError) as auth_error:
                # AssertionError is not defensive breadth: the framework's authenticate_ldap_user
                # reports a failed login as a bare `assert 0 == rc`, so catching only
                # KeywordException let the most common real failure escape the retry entirely and
                # made this window dead code. Found when a deliberately broken issuer failed the
                # post-upgrade phase on the first attempt instead of retrying for 300 s.
                last_error = str(auth_error)
            # A session that did not authenticate must not be left open for the next attempt to
            # inherit, and must not leak if the window expires.
            self._close_session(phase)
            get_logger().log_info(f"[{phase}] OIDC authentication not available yet; retrying in {self.AUTH_POLL_INTERVAL}s")
            time.sleep(self.AUTH_POLL_INTERVAL)

        raise KeywordException(f"[{phase}] OIDC authentication did not succeed within {self.AUTH_TIMEOUT}s. Last output: {last_error[:300]}")

    def _open_user_session(self, oam_ip: str, username: str, password: str) -> SSHConnection:
        """Open an SSH session as the OIDC user, honouring the lab's port and jump host.

        ``OidcAuthKeywords.create_ldap_user_ssh`` cannot be reused here. It calls
        ``SSHConnectionManager.create_ssh_connection(oam_ip, username, password)`` and so takes the
        defaults ``ssh_port=22`` and ``jump_host=None``. On a lab reached through a jump box on a
        non-default port that connection can never be established, and the symptom is a long run of
        transport errors rather than a clear failure.

        Args:
            oam_ip (str): lab OAM floating address.
            username (str): LDAP login name of the OIDC user.
            password (str): that user's password.

        Returns:
            SSHConnection: a connected session as the OIDC user.

        """
        lab_config = ConfigurationManager.get_lab_config()
        jump_host = lab_config.get_jump_host_configuration() if lab_config.is_use_jump_server() else None
        session = SSHConnectionManager.create_ssh_connection(
            oam_ip,
            username,
            password,
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host,
        )
        session.connect()
        return session

    def _deployment_image(self, deployment: str, phase: str) -> str:
        """Read a deployment's first container image.

        Args:
            deployment (str): deployment name.
            phase (str): the phase, for the assertion message.

        Returns:
            str: the image reference, including its tag.

        """
        image = self.resources.get_resource_field("deployment", deployment, "{.spec.template.spec.containers[0].image}", namespace=self.NAMESPACE)
        # kubectl returns an empty string with status 0 for a path that does not resolve, so an
        # absent deployment would otherwise be recorded as a blank image and compared equal to
        # another blank image in a later phase.
        validate_greater_than(len(image.strip()), 0, f"[{phase}] {deployment} must report a container image")
        return image.strip()

    def _close_finalizer(self, phase: str) -> Callable:
        """Return a finalizer that closes this phase's session unless the phase already did.

        Args:
            phase (str): the phase the finalizer belongs to.

        Returns:
            Callable: the finalizer to register.

        """

        def _finalizer() -> None:
            """Close this phase's session if the phase did not already close it."""
            self._close_session(phase)

        return _finalizer

    def _close_session(self, phase: str) -> None:
        """Close and forget this phase's session, if it is still open.

        Best effort: a session that cannot be closed is untidy but is not a test result, and
        reporting it would replace a real failure with a housekeeping error.

        Args:
            phase (str): the phase whose session should be closed.

        """
        session = self._sessions.pop(phase, None)
        if session is None:
            return
        try:
            session.close()
        except Exception as close_error:  # noqa: BLE001 - housekeeping must not fail the test
            get_logger().log_info(f"[{phase}] could not close the OIDC session: {close_error}")
