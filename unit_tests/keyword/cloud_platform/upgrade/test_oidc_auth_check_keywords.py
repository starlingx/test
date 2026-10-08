"""Unit tests for the oidc-auth-apps authentication check.

These run against a stateful in-memory stand-in for the system rather than a sequence of canned
return values. That matters here because the check's correctness is mostly about **what it refuses
to accept**: a login that exits zero without succeeding, a token that authenticates but authorizes
nothing, a username that changed underneath the ClusterRoleBinding, a deployment that is absent and
reads back as a blank image. A scripted list of return values would pass even if the keyword never
looked at any of it.

The model's login outcome is a consequence of its own state - dex up or down, the claim mapping,
whether the check user is bound - rather than something each test dictates, so the assertions are
exercised the way the real system would exercise them.

No validate_* function is patched. Failures surface as the exceptions the production code would
really raise.
"""

import unittest
from typing import Callable
from unittest.mock import patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.oidc_auth_check_keywords import OidcAuthCheckKeywords

OAM_IP = "192.0.2.10"
ISSUER = f"https://{OAM_IP}:30556/dex"
OIDC_USER = "oidcuser"
OIDC_PASSWORD = "unit-test-only"
DEX_IMAGE = "registry.local:9001/ghcr.io/dexidp/dex:v2.44.0"
CLIENT_IMAGE = "registry.local:9001/docker.io/starlingx/stx-oidc-client:stx.12.0-v1.0.3"


class FakeSession:
    """A stand-in for the SSH session opened as the check user."""

    def __init__(self, system: "FakeOidcSystem"):
        """Build a session bound to a system model.

        Args:
            system (FakeOidcSystem): the system this session talks to.

        """
        self.system = system
        self.closed = False
        self._last_rc = 0

    def send(self, command: str) -> list[str]:
        """Run a command, returning what the real system would print.

        Args:
            command (str): the command to run.

        Returns:
            list[str]: output lines.

        """
        if "auth can-i" in command:
            return ["yes" if self.system.cluster_admin else "no"]
        if "get secrets" in command:
            return self.system.secrets_read_output()
        if "auth whoami" in command:
            out = self.system.whoami_output()
            # Non-empty output with a non-zero status is the case that matters: kubectl prints its
            # error to stdout, so text alone cannot distinguish success from failure.
            self._last_rc = 1 if (self.system.kubeconfig_missing or not (out and out[0])) else 0
            return out
        if command.startswith("oidc-auth"):
            return self.system.oidc_auth_output()
        return [""]

    def get_return_code(self) -> int:
        """Return the exit status of the last command.

        Models the real connection, where a kubectl that cannot reach a server exits non-zero while
        still printing text to stdout.

        Returns:
            int: 0 when the last command succeeded, 1 otherwise.

        """
        return self._last_rc

    def close(self) -> None:
        """Close the session and record that it happened."""
        self.closed = True
        self.system.closed_sessions += 1


class FakePodsOutput:
    """A stand-in for KubectlGetPodsOutput holding only what the check reads."""

    def __init__(self, pods: list):
        """Hold a list of pods.

        Args:
            pods (list): the pods this output reports.

        """
        self._pods = pods

    def get_pods(self) -> list:
        """Return the pods.

        Returns:
            list: the pods this output reports.

        """
        return self._pods


class FakeOidcSystem:
    """A small stateful stand-in for the OIDC-enabled system the keyword talks to.

    Holds whether dex is serving, which claim the apiserver is configured to read and what that
    claim resolves to, whether the resolved user is authorized, the two deployment images, and the
    secret-observer cron job's state. Authentication and authorization are derived from that state.
    """

    def __init__(
        self,
        dex_up: bool = True,
        resolved_username: str = OIDC_USER,
        echo_username: bool = True,
        login_marker: bool = True,
        authorized: bool = True,
        dex_image: str = DEX_IMAGE,
        client_image: str = CLIENT_IMAGE,
        cronjob_schedule: str = "*/15 * * * *",
        cronjob_suspended: str = "false",
        whoami_identity: str = None,
        cluster_admin: bool = False,
        login_fails: bool = False,
        kubeconfig_missing: bool = False,
        denial_shape: str = "forbidden",
    ):
        """Build a system model.

        Args:
            dex_up (bool): whether the issuer is serving. When False, oidc-auth fails the way it
                does with the deployment scaled to zero.
            resolved_username (str): the value the configured claim resolves to. Not necessarily
                the login name: on the lab this was developed against, 'oidc-username-claim=name'
                with dex 'nameAttr: gecos' resolves to the GECOS field.
            echo_username (bool): whether oidc-auth prints the 'Using "..." as username.' line the
                check reads the username from.
            login_marker (bool): whether oidc-auth prints "Login succeeded". Set False to model a
                script that exits zero without actually logging in.
            whoami_identity (str): the identity 'kubectl auth whoami' reports. Defaults to the
                resolved username. Set to "kubernetes-admin" to model the defect where the read
                falls back to /etc/kubernetes/admin.conf and authenticates over X.509 instead of
                with the OIDC token.
            cluster_admin (bool): whether a broad binding is still in effect, which would make a
                denial vacuous.
            kubeconfig_missing (bool): whether the user's kubeconfig is absent. kubectl then talks
                to the default localhost endpoint, prints an error to stdout and exits non-zero -
                non-empty text that is not the administrator identity, which is why the return code
                has to be checked and not just the text.
            login_fails (bool): whether the session opens but the login itself fails, reported the
                way the framework reports it. Distinct from dex_up, which fails earlier at session
                setup and so never reaches the login.
            denial_shape (str): how the ungranted read is refused. "forbidden" is the healthy
                shape. "unauthorized" models authentication being dead and "server_error" models
                the read failing for an unrelated reason while still naming the resource - neither
                is a success, and neither may satisfy the denial assertion.
            authorized (bool): whether the resolved user may list pods. False models a missing or
                wrongly-subjected ClusterRoleBinding.
            dex_image (str): the oidc-dex container image, or "" for an absent deployment.
            client_image (str): the stx-oidc-client container image, or "" for an absent deployment.
            cronjob_schedule (str): the secret-observer cron schedule, or "" when absent.
            cronjob_suspended (str): the cron job's 'suspend' field as kubectl renders it.

        """
        self.dex_up = dex_up
        self.resolved_username = resolved_username
        self.whoami_identity = resolved_username if whoami_identity is None else whoami_identity
        self.echo_username = echo_username
        self.login_marker = login_marker
        self.authorized = authorized
        self.dex_image = dex_image
        self.client_image = client_image
        self.cronjob_schedule = cronjob_schedule
        self.cronjob_suspended = cronjob_suspended
        self.authentications = 0
        self.closed_sessions = 0
        self.kubeconfig_used = None
        self.cluster_admin = cluster_admin
        self.login_fails = login_fails
        self.kubeconfig_missing = kubeconfig_missing
        self.bindings_created = []
        self.bindings_deleted = []
        self.denial_shape = denial_shape
        self.sessions = []

    def secrets_read_output(self) -> list[str]:
        """Return what reading the ungranted resource prints.

        Returns:
            list[str]: the refusal, in the shape this model is configured for.

        """
        if self.denial_shape == "unauthorized":
            return ["error: You must be logged in to the server (Unauthorized)"]
        if self.denial_shape == "server_error":
            # Names the resource but is not a refusal, so only the Forbidden assertion can reject
            # it. A read that fails for any reason other than authorization says nothing about
            # whether authorization is being evaluated.
            return ["Error from server (InternalError): an error on the server prevented the request from succeeding (get secrets)"]
        return ['Error from server (Forbidden): secrets is forbidden: User "x" cannot list resource "secrets" in API group "" in the namespace "kube-system"']

    def whoami_output(self) -> list[str]:
        """Return what 'kubectl auth whoami' prints for the authenticated session.

        Returns:
            list[str]: the resolved identity, or nothing when the issuer is down so no token
                exists to resolve.

        """
        if self.kubeconfig_missing:
            return ["error: connection to the server localhost:8080 was refused - did you specify the right host or port?"]
        if not self.dex_up:
            return [""]
        return [self.whoami_identity]

    def oidc_auth_output(self) -> list[str]:
        """Return what oidc-auth would print in the current state.

        Returns:
            list[str]: output lines.

        """
        if not self.dex_up:
            return ["Error: could not reach the issuer", "Login failed."]
        lines = []
        if self.echo_username:
            lines.append(f'Using "{self.resolved_username}" as username.')
        if self.login_marker:
            lines.append("Login succeeded.")
        lines.append("Updating kubectl config ...")
        return lines

    def open_session(self, oam_ip: str, username: str, password: str) -> FakeSession:
        """Open a session as the check user, as _open_user_session would.

        Args:
            oam_ip (str): the address being connected to.
            username (str): the login name.
            password (str): that user's password.

        Returns:
            FakeSession: the opened session.

        Raises:
            KeywordException: when the issuer is down, which is how the real helper fails.

        """
        self.authentications += 1
        if not self.dex_up:
            raise KeywordException("oidc-auth failed")
        session = FakeSession(self)
        self.sessions.append(session)
        return session

    def resource_field(self, resource: str, name: str, jsonpath: str, namespace: str = None) -> str:
        """Return a resource field the way kubectl would, including empty for absent paths.

        Args:
            resource (str): resource kind.
            name (str): resource name.
            jsonpath (str): the jsonpath being read.
            namespace (str): the namespace.

        Returns:
            str: the field value, or "" when it does not resolve.

        """
        if resource == "deployment":
            if name == OidcAuthCheckKeywords.DEX_DEPLOYMENT:
                return self.dex_image
            if name == OidcAuthCheckKeywords.CLIENT_DEPLOYMENT:
                return self.client_image
            return ""
        if resource == "cronjob":
            if "schedule" in jsonpath:
                return self.cronjob_schedule
            if "suspend" in jsonpath:
                return self.cronjob_suspended
        return ""

    def oidc_auth_keywords(self, session: FakeSession):
        """Return a stand-in for OidcAuthKeywords bound to this model.

        Authentication fails when the issuer is not serving, which is how a dex deployment scaled
        to zero presents on a live system: oidc-auth cannot reach the issuer and exits non-zero.

        Args:
            session (FakeSession): the session to authenticate on.

        Returns:
            object: an object exposing the two methods the check calls.

        Raises:
            KeywordException: when the issuer is not serving.

        """
        dex_up = self.dex_up
        login_fails = self.login_fails

        class _Auth:
            """Stand-in for the two OidcAuthKeywords methods the check calls."""

            def setup_kubeconfig(self) -> None:
                """Run kubeconfig-setup, which succeeds regardless of the issuer's state."""
                return None

            def authenticate_ldap_user(self, password: str) -> None:
                """Authenticate, failing when the issuer is not serving.

                Fails with AssertionError because that is how the real helper reports it - a bare
                `assert 0 == rc` on the oidc-auth return code - and a model that raised something
                tidier would hide whether the retry loop actually catches it.

                Args:
                    password (str): the user's password, unused by the model.

                Raises:
                    AssertionError: when the issuer is not serving.

                """
                if not dex_up or login_fails:
                    raise AssertionError("Return code was 1")

        return _Auth()

    def pods_for(self, session: FakeSession, kubeconfig_path: str = None) -> FakePodsOutput:
        """Return the pods the authenticated user may see.

        Args:
            session (FakeSession): the authenticated session.
            kubeconfig_path (str): the kubeconfig the read names. Recorded so a test can assert the
                check does not fall back to the framework default, which is the administrator
                kubeconfig and would make the read bypass the OIDC token entirely.

        Returns:
            FakePodsOutput: the pods, empty when the user is not authorized.

        """
        self.kubeconfig_used = kubeconfig_path
        if not self.authorized:
            return FakePodsOutput([])
        return FakePodsOutput(["oidc-dex-xxxx", "stx-oidc-client-yyyy", "secret-observer-zzzz"])


class FakeRequest:
    """A stand-in for pytest's FixtureRequest that records finalizers."""

    def __init__(self):
        """Start with no finalizers."""
        self.finalizers = []

    def addfinalizer(self, func: Callable) -> None:
        """Record a finalizer.

        Args:
            func (Callable): the finalizer.

        """
        self.finalizers.append(func)

    def run_finalizers(self) -> None:
        """Run the recorded finalizers, most recently registered first."""
        for func in reversed(self.finalizers):
            func()


class OidcAuthCheckKeywordsTest(unittest.TestCase):
    """Exercise the OIDC authentication check against a stateful system model."""

    def setUp(self):
        """Silence the loggers so the suite runs outside a configured framework session.

        Only loggers are patched. No validate_* function is, so every assertion below is the real
        one and failures surface as the exceptions production code would raise.
        """
        self._patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.get_logger"),
            patch("keywords.k8s.auth.kubectl_auth_keywords.get_logger"),
            patch("framework.validation.validation.get_logger"),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        """Stop the logger patchers."""
        for patcher in self._patchers:
            patcher.stop()

    def _build(self, system: FakeOidcSystem) -> OidcAuthCheckKeywords:
        """Build a keyword wired to a system model.

        Args:
            system (FakeOidcSystem): the model to wire in.

        Returns:
            OidcAuthCheckKeywords: the keyword wired to the model.

        """
        keyword = OidcAuthCheckKeywords.__new__(OidcAuthCheckKeywords)
        keyword.ssh_connection = None
        keyword._sessions = {}

        class _Resources:
            """Stand-in for KubectlGetResourceKeywords, answering from the system model."""

            def get_resource_field(self, resource, name, jsonpath, namespace=None):
                """Answer a resource field read from the system model.

                Args:
                    resource (str): resource type.
                    name (str): resource name.
                    jsonpath (str): the field to read.
                    namespace (str): the namespace, unused by the model.

                Returns:
                    str: what the model reports for that field.

                """
                return system.resource_field(resource, name, jsonpath, namespace)

        class _Bindings:
            """Stand-in for the cluster-role-binding keywords, recording what was asked for."""

            def create_clusterrolebinding_for_user(self, binding_name, clusterrole, user):
                """Record a binding creation.

                Args:
                    binding_name (str): the binding name.
                    clusterrole (str): the role it grants.
                    user (str): the subject.

                """
                system.bindings_created.append((binding_name, clusterrole, user))

            def delete_clusterrolebinding(self, binding_name):
                """Record a binding deletion.

                Args:
                    binding_name (str): the binding name.

                """
                system.bindings_deleted.append(binding_name)

        keyword.bindings = _Bindings()
        keyword.resources = _Resources()
        return keyword

    def _run_phase(self, system: FakeOidcSystem, phase: str = "pre") -> tuple:
        """Run one phase of the check against the model.

        Args:
            system (FakeOidcSystem): the model.
            phase (str): the phase name.

        Returns:
            tuple: the observations dict and the request stand-in.

        """
        keyword = self._build(system)
        request = FakeRequest()
        with (
            patch.object(OidcAuthCheckKeywords, "_open_user_session", side_effect=system.open_session),
            patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.OidcAuthKeywords", side_effect=system.oidc_auth_keywords),
            patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlGetPodsKeywords") as pods_class,
            patch(
                "keywords.cloud_platform.upgrade.oidc_auth_check_keywords.OidcAuthCheckKeywords.AUTH_TIMEOUT",
                1,
            ),
            patch(
                "keywords.cloud_platform.upgrade.oidc_auth_check_keywords.OidcAuthCheckKeywords.AUTH_POLL_INTERVAL",
                0,
            ),
        ):
            pods_class.side_effect = lambda session, kubeconfig_path=None: type("P", (), {"get_pods": lambda _s, ns: system.pods_for(session, kubeconfig_path)})()
            observations = keyword.validate_oidc_access(request, phase, OIDC_USER, OIDC_PASSWORD, OAM_IP)
        return observations, request, keyword

    def test_healthy_system_authenticates_and_reports_observations(self):
        """A healthy system authenticates, authorizes, and reports both image tags."""
        system = FakeOidcSystem()
        observations, _request, _kw = self._run_phase(system)
        self.assertEqual(observations["username"], OIDC_USER)
        self.assertEqual(observations["dex_image"], DEX_IMAGE)
        self.assertEqual(observations["client_image"], CLIENT_IMAGE)

    def test_session_is_closed_on_the_happy_path(self):
        """The session is closed by the check itself, not left for teardown.

        A session left open holds an SSH connection across the host reboot the upgrade performs
        next.
        """
        system = FakeOidcSystem()
        self._run_phase(system)
        self.assertEqual(system.closed_sessions, 1)

    def test_each_phase_authenticates_again(self):
        """Every phase opens a new session, so no phase can pass on an earlier phase's token."""
        system = FakeOidcSystem()
        keyword = self._build(system)
        request = FakeRequest()
        with (
            patch.object(OidcAuthCheckKeywords, "_open_user_session", side_effect=system.open_session),
            patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.OidcAuthKeywords", side_effect=system.oidc_auth_keywords),
            patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlGetPodsKeywords") as pods_class,
        ):
            pods_class.side_effect = lambda session, kubeconfig_path=None: type("P", (), {"get_pods": lambda _s, ns: system.pods_for(session, kubeconfig_path)})()
            for phase in ("pre", "post-upgrade", "post-rollback"):
                keyword.validate_oidc_access(request, phase, OIDC_USER, OIDC_PASSWORD, OAM_IP)
        self.assertEqual(system.authentications, 3)
        self.assertEqual(system.closed_sessions, 3)

    def test_dex_down_fails_the_phase(self):
        """With the issuer unreachable the phase must fail.

        Commands already issued can still succeed from a cached key set, so it is re-login that has
        to break - which is exactly what authenticating from scratch in every phase buys.
        """
        system = FakeOidcSystem(dex_up=False)
        with self.assertRaises(KeywordException):
            self._run_phase(system)

    def test_a_login_failure_is_retried_rather_than_escaping(self):
        """A failed login must be retried, not propagated as the framework's bare assertion.

        The framework helper reports a failed login as `assert 0 == rc` on the oidc-auth return
        code, so a retry loop catching only KeywordException let the commonest real failure escape
        and fail the phase on its first attempt. Observed on a lab with the issuer deliberately
        broken: zero retries were logged.

        This models the session opening fine and the login itself failing, which is the only way to
        reach that branch - dex_up=False fails earlier, at session setup.
        """
        system = FakeOidcSystem(login_fails=True)
        with self.assertRaises(KeywordException) as caught:
            self._run_phase(system)
        # The retry loop's own message, which only appears if the assertion was caught and retried.
        self.assertIn("did not succeed within", str(caught.exception))

    def test_unreadable_identity_fails_with_an_explanation(self):
        """An identity that cannot be read must refuse rather than carry an empty username forward.

        An empty username would compare equal to another empty username in a later phase, so a
        claim mapping that broke across the upgrade would read as unchanged.
        """
        system = FakeOidcSystem(whoami_identity="")
        with self.assertRaises(KeywordException) as caught:
            self._run_phase(system)
        self.assertIn("could not read the authenticated username", str(caught.exception))

    def test_authenticated_but_unauthorized_fails(self):
        """A token that authenticates but lists nothing must fail.

        This is what a ClusterRoleBinding with the wrong subject produces, and a login-only check
        would pass it.
        """
        system = FakeOidcSystem(authorized=False)
        with self.assertRaises(Exception):
            self._run_phase(system)

    def test_a_changed_resolved_username_is_visible_to_the_caller(self):
        """The resolved username is reported, so the test can compare it across phases.

        If the claim mapping changed across the upgrade the binding would no longer match, and
        authorization would be silently lost on a system that still authenticates.
        """
        system = FakeOidcSystem(resolved_username="Check User")
        observations, _request, _kw = self._run_phase(system)
        self.assertEqual(observations["username"], "Check User")

    def test_absent_dex_deployment_fails_rather_than_reporting_a_blank(self):
        """kubectl returns empty with status 0 for an absent path, which must not read as equal."""
        system = FakeOidcSystem(dex_image="")
        with self.assertRaises(Exception):
            self._run_phase(system)

    def test_absent_client_deployment_fails_rather_than_reporting_a_blank(self):
        """The same guard applies to the second deployment."""
        system = FakeOidcSystem(client_image="")
        with self.assertRaises(Exception):
            self._run_phase(system)

    def test_secret_observer_absent_fails(self):
        """An absent cron job must fail: four prior OIDC cycles required this check."""
        system = FakeOidcSystem(cronjob_schedule="")
        keyword = self._build(system)
        with self.assertRaises(Exception):
            keyword.validate_secret_observer_is_scheduled("pre")

    def test_secret_observer_suspended_fails(self):
        """A suspended cron job will not restart the OIDC pods when certificates change."""
        system = FakeOidcSystem(cronjob_suspended="true")
        keyword = self._build(system)
        with self.assertRaises(Exception):
            keyword.validate_secret_observer_is_scheduled("pre")

    def test_secret_observer_healthy_passes(self):
        """A scheduled, unsuspended cron job passes, including when 'suspend' renders empty."""
        keyword = self._build(FakeOidcSystem(cronjob_suspended=""))
        keyword.validate_secret_observer_is_scheduled("pre")

    def test_finalizer_is_safe_to_run_after_the_phase_closed_its_own_session(self):
        """The finalizer must be a no-op once the phase cleaned up, not a second close."""
        system = FakeOidcSystem()
        _observations, request, _kw = self._run_phase(system)
        request.run_finalizers()
        self.assertEqual(system.closed_sessions, 1)

    def test_falling_back_to_the_administrator_kubeconfig_fails(self):
        """Reading the API as the administrator certificate must fail instead of passing.

        This is the defect this check was rewritten to make impossible. The framework's default
        kubeconfig is /etc/kubernetes/admin.conf; it is group-readable by sys_protected and the
        test user is in that group, so a read that does not name the user's own kubeconfig
        authenticates over X.509 as kubernetes-admin. The earlier revision of this check did
        exactly that and passed every phase without the OIDC token being involved - it would have
        passed with dex deleted. Asserting the identity before reading anything is what turns that
        silent pass into a failure.
        """
        system = FakeOidcSystem(whoami_identity="kubernetes-admin")
        with self.assertRaises(Exception) as caught:
            self._run_phase(system)
        self.assertIn("Validation Failed", str(caught.exception))

    def test_a_dead_authentication_does_not_satisfy_the_denial(self):
        """An Unauthorized response must not count as a successful denial.

        This is the fail-open an earlier draft of this check contained. A denial assertion that
        only establishes "the operation did not succeed" is also satisfied by 401 Unauthorized,
        which is what a completely broken authentication returns - so the check would report a
        healthy denial on a cluster where nobody can log in at all. Only 403 Forbidden proves the
        apiserver authenticated the token and then refused the action.
        """
        system = FakeOidcSystem(denial_shape="unauthorized")
        with self.assertRaises(Exception) as caught:
            self._run_phase(system)
        self.assertIn("Validation Failed", str(caught.exception))

    def test_a_failure_that_is_not_a_refusal_does_not_satisfy_the_denial(self):
        """A read that fails for a reason other than authorization must not count as a denial.

        Separates the two halves of the denial assertion. This response names the resource, so the
        resource-name check passes and only the Forbidden check can reject it - which is what
        proves that check is load-bearing rather than redundant.
        """
        system = FakeOidcSystem(denial_shape="server_error")
        with self.assertRaises(Exception) as caught:
            self._run_phase(system)
        self.assertIn("Validation Failed", str(caught.exception))

    def test_a_vacuous_denial_is_refused(self):
        """A subject that can still read the ungranted resource must fail, not report a denial.

        If a broad binding survives, nothing can be refused and the denial below would prove
        nothing. Failing here names the cause instead of producing a confusing assertion failure
        further on.
        """
        system = FakeOidcSystem(cluster_admin=True)
        with self.assertRaises(Exception) as caught:
            self._run_phase(system)
        self.assertIn("Validation Failed", str(caught.exception))

    def test_the_narrow_binding_is_recreated_every_phase(self):
        """The grant is reapplied per phase rather than assumed to survive the deploy.

        A rollback can restore an earlier etcd state, so a binding created once at the start cannot
        be relied on later. The keyword is idempotent, so reapplying costs nothing.
        """
        system = FakeOidcSystem()
        for phase in ("pre", "post-upgrade", "post-rollback"):
            self._run_phase(system, phase=phase)
        created = [name for name, _role, _user in system.bindings_created]
        self.assertEqual(created.count(OidcAuthCheckKeywords.SCOPED_BINDING), 3)

    def test_an_unreachable_api_server_is_not_mistaken_for_an_identity(self):
        """kubectl failing must fail the phase, even though it prints non-empty text.

        With the user's kubeconfig absent, kubectl talks to the default localhost endpoint and
        prints "connection to the server localhost:8080 was refused" on stdout while exiting
        non-zero. That text is non-empty and is not the administrator identity, so a check that
        read only the text would accept it as a resolved username and carry it forward as the
        identity - making the identity assertion useless, which is the defect this whole check
        exists to prevent.
        """
        system = FakeOidcSystem(kubeconfig_missing=True)
        with self.assertRaises(KeywordException) as caught:
            self._run_phase(system)
        self.assertIn("could not read the authenticated username", str(caught.exception))


class FakeAdminSession:
    """A stand-in for the administrator session the RBAC reads and writes run on."""

    def __init__(self, listing: str = "", fail_on: str = None):
        """Build a session that answers the cluster-role-binding listing.

        Args:
            listing (str): what 'kubectl get clusterrolebinding' prints, in the jsonpath shape the
                keyword asks for.
            fail_on (str): a substring; any command containing it raises, to model a kubectl that
                fails partway through housekeeping.

        """
        self.listing = listing
        self.fail_on = fail_on
        self.commands = []

    def send(self, command: str) -> list:
        """Run a command and return its output.

        Args:
            command (str): the command to run.

        Returns:
            list: output lines.

        Raises:
            KeywordException: when the command matches fail_on.

        """
        self.commands.append(command)
        if self.fail_on and self.fail_on in command:
            raise KeywordException(f"kubectl failed: {command[:40]}")
        if "get clusterrolebinding" in command:
            return self.listing.splitlines()
        return [""]


class OidcAuthCheckRbacTest(unittest.TestCase):
    """Cover the role-binding snapshot, suspend and restore.

    This is the only code in the check that changes state on a shared lab, so the cases that matter
    are the ones where it could leave a subject's access removed: a listing it parses wrongly, and a
    restore that gives up partway through.
    """

    # The real listing shape, taken from a lab. The prefixed form is the one worth keeping: the
    # apiserver prefixes the username with the issuer URL unless the claim is email, so the subject
    # itself contains colons and slashes and must survive parsing.
    PREFIXED_USER = "https://192.0.2.10:30556/dex#oidcuser"
    LISTING = (
        f"dex-attr-test-crb|cluster-admin|User:{PREFIXED_USER},\n"
        "dex-attr-test-crb-plain|cluster-admin|User:someone-else,\n"
        # Named for THIS user but a different kind. Restoring it as --user= would convert a group
        # grant into a user grant, so it must be left alone. A fixture naming someone else here
        # would never exercise kind-sensitivity at all.
        f"a-group-binding|cluster-admin|Group:{PREFIXED_USER},\n"
        f"a-serviceaccount-binding|cluster-admin|ServiceAccount:{PREFIXED_USER},\n"
        # A username this one is a strict prefix of, so a substring match would wrongly claim it.
        f"a-superstring-binding|cluster-admin|User:{PREFIXED_USER}-admin,\n"
        f"a-shared-binding|cluster-admin|User:{PREFIXED_USER},User:another-user,\n"
        # More fields than expected, which must be skipped rather than mis-parsed.
        f"a-malformed-binding|cluster-admin|User:{PREFIXED_USER},|extra\n"
    )

    def setUp(self):
        """Silence the loggers the keyword writes to."""
        for target in ("keywords.base_keyword.get_logger", "keywords.cloud_platform.upgrade.oidc_auth_check_keywords.get_logger", "keywords.k8s.auth.kubectl_auth_keywords.get_logger"):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _build(self, listing: str = None, fail_on: str = None):
        """Build a keyword wired to a fake administrator session.

        Args:
            listing (str): the cluster-role-binding listing to answer with.
            fail_on (str): substring of a binding command that should fail.

        Returns:
            tuple: the keyword, the admin session, and a record of binding calls.

        """
        keyword = OidcAuthCheckKeywords.__new__(OidcAuthCheckKeywords)
        session = FakeAdminSession(self.LISTING if listing is None else listing)
        keyword.ssh_connection = session
        keyword._sessions = {}
        record = {"created": [], "deleted": []}

        class _Bindings:
            """Records binding calls, and fails the one the test names."""

            def create_clusterrolebinding_for_user(self, binding_name, clusterrole, user):
                """Record or fail a binding creation.

                Args:
                    binding_name (str): the binding name.
                    clusterrole (str): the role granted.
                    user (str): the subject.

                Raises:
                    KeywordException: when this binding is the one named to fail.

                """
                if fail_on and fail_on == binding_name:
                    raise KeywordException(f"cannot create {binding_name}")
                record["created"].append((binding_name, clusterrole, user))

            def delete_clusterrolebinding(self, binding_name):
                """Record a binding deletion.

                Args:
                    binding_name (str): the binding name.

                """
                record["deleted"].append(binding_name)

        class _Resources:
            """Answers the cluster-role-binding listing the keyword now reads through."""

            def get_resource_field(self, resource_type, resource_name, jsonpath, namespace=None):
                """Return the canned listing.

                Args:
                    resource_type (str): resource type.
                    resource_name (str): empty, meaning list them all.
                    jsonpath (str): the projection asked for; recorded so a test can assert on it.
                    namespace (str): unused.

                Returns:
                    str: the listing.

                """
                session.commands.append(f"get {resource_type} -o jsonpath={jsonpath}")
                return session.listing

        keyword.resources = _Resources()
        keyword.bindings = _Bindings()
        return keyword, session, record

    def test_only_a_lone_user_subject_binding_is_suspended(self):
        """Only a binding whose single subject is this user may be touched.

        A Group or ServiceAccount binding would be recreated as --user= and so silently changed
        into something else, and a binding shared with other subjects cannot be reproduced from
        this listing at all. Both are left alone, which is safer than approximating them.
        """
        keyword, session, record = self._build()
        suspended = []
        with patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlCreateClusterRoleKeywords"):
            keyword.suspend_broad_access(self.PREFIXED_USER, suspended)

        self.assertEqual(suspended, [("dex-attr-test-crb", "cluster-admin")])
        self.assertEqual(record["deleted"], ["dex-attr-test-crb"])
        # GAP: the fake answers a canned listing regardless of the query, so without this the
        # jsonpath could stop emitting the subject kind and every assertion above would still pass.
        self.assertTrue(
            any("{.kind}:{.name}" in command for command in session.commands),
            f"the listing must ask for the subject kind; commands were {session.commands}",
        )

    def test_suspending_grants_only_pod_reads(self):
        """The replacement grant must be narrow, or the denial it enables is not observable."""
        keyword, _session, _record = self._build()
        with patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlCreateClusterRoleKeywords") as role_class:
            keyword.suspend_broad_access(self.PREFIXED_USER, [])

        role_class.return_value.create_clusterrole.assert_called_once_with(OidcAuthCheckKeywords.SCOPED_CLUSTERROLE, ["get", "list"], ["pods"])

    def test_a_binding_that_cannot_be_restored_does_not_abandon_the_others(self):
        """One failure must not strand the remaining bindings.

        A single try around the whole loop meant the first failure abandoned every binding after
        it, leaving a shared lab with a subject's access removed and no record of what was lost.
        """
        keyword, _session, record = self._build(fail_on="second")
        suspended = [("first", "cluster-admin"), ("second", "cluster-admin"), ("third", "cluster-admin")]

        keyword.restore_access(suspended, self.PREFIXED_USER)

        self.assertEqual(
            record["created"],
            [("first", "cluster-admin", self.PREFIXED_USER), ("third", "cluster-admin", self.PREFIXED_USER)],
        )

    def test_a_failure_creating_the_grant_removes_nothing(self):
        """If the replacement grant cannot be created, no binding may have been removed yet.

        The original order deleted the bindings first and created the grant afterwards, so a
        failure here left the subject with its access removed and the record of what to restore
        discarded. On a shared lab that is unrecoverable without someone reading the logs.
        """
        keyword, _session, record = self._build()
        suspended = []
        with patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlCreateClusterRoleKeywords") as role_class:
            role_class.return_value.create_clusterrole.side_effect = KeywordException("cannot create the role")
            with self.assertRaises(KeywordException):
                keyword.suspend_broad_access(self.PREFIXED_USER, suspended)

        self.assertEqual(record["deleted"], [], "nothing may be removed before the grant exists")
        self.assertEqual(suspended, [])

    def test_restore_removes_what_this_test_created(self):
        """The narrow binding and its ClusterRole must not be left behind on the lab."""
        keyword, _session, record = self._build()

        with patch("keywords.cloud_platform.upgrade.oidc_auth_check_keywords.KubectlCreateClusterRoleKeywords") as role_class:
            keyword.restore_access([], self.PREFIXED_USER)

        self.assertIn(OidcAuthCheckKeywords.SCOPED_BINDING, record["deleted"])
        role_class.return_value.delete_clusterrole.assert_called_once_with(OidcAuthCheckKeywords.SCOPED_CLUSTERROLE)


if __name__ == "__main__":
    unittest.main()
