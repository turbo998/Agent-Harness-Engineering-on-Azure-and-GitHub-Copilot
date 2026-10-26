"""Unit and mutation-calibration suite for the 2026-10-27 SA harness lab.

Rules:
- Uses `unittest.TestCase` methods (`assertEqual`, `assertTrue`, `assertRaises`, etc.) exclusively.
- Contains zero bare `assert` statements so behavior is identical under `python3 -B` and `python3 -B -O`.
- Includes 24 baseline tests and a programmatic 6-mutant calibration helper.
"""

from __future__ import annotations

from pathlib import Path
import json
import unittest

import harness_contracts as hc


class TestHarnessContracts20261027(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Microsoft Agent Framework (MAF): Hooks Declaration, FIDES, Toolbox
    # ------------------------------------------------------------------
    def test_01_maf_agent_hooks_declaration_valid_session_and_config_name_lookup(self) -> None:
        doc = {
            "declaration": "agent-hooks-declaration/1.0",
            "configuration": {
                "posture": {"tool_seam_host_error": "terminate"},
                "capabilities": ["model_calls", "tool_calls", "host_declaration"],
            },
            "bindings": [
                {"id": "egress-guard", "kind": "agent_framework.interceptor", "config": {"name": "egress"}},
                {"id": "audit", "kind": "agent_framework.interceptor"},
            ],
        }
        interceptors = {
            "egress": lambda x: f"egress:{x}",
            "audit": lambda x: f"audit:{x}",
        }
        session = hc.validate_and_bind_agent_hooks_declaration(doc, interceptors, session_id="s-101")
        self.assertEqual(session.session_id, "s-101")
        self.assertEqual(session.declaration_version, "agent-hooks-declaration/1.0")
        self.assertEqual(session.posture, "terminate")
        self.assertEqual(len(session.bindings), 2)
        self.assertEqual(session.bindings[0].interceptor_name, "egress")
        self.assertEqual(session.bindings[1].interceptor_name, "audit")

    def test_02_maf_agent_hooks_declaration_rejects_continue_posture_and_dynamic_imports(self) -> None:
        bad_posture_doc = {
            "declaration": "agent-hooks-declaration/1.0",
            "configuration": {"posture": {"tool_seam_host_error": "continue"}},
            "bindings": [{"id": "g1", "kind": "agent_framework.interceptor"}],
        }
        with self.assertRaisesRegex(hc.ContractError, "terminate"):
            hc.validate_and_bind_agent_hooks_declaration(bad_posture_doc, {"g1": lambda x: x})

        dynamic_import_doc = {
            "declaration": "agent-hooks-declaration/1.0",
            "configuration": {"posture": {"tool_seam_host_error": "terminate"}},
            "bindings": [
                {
                    "id": "g1",
                    "kind": "agent_framework.interceptor",
                    "config": {"module": "os.system", "secret": "CANARY_DO_NOT_ECHO"},
                }
            ],
        }
        with self.assertRaisesRegex(hc.ContractError, "prohibits dynamic import keys"):
            hc.validate_and_bind_agent_hooks_declaration(dynamic_import_doc, {"g1": lambda x: x})

    def test_03_maf_agent_hooks_declaration_missing_interceptor_never_echoes_secret_config(self) -> None:
        doc = {
            "declaration": "agent-hooks-declaration/1.0",
            "configuration": {"posture": {"tool_seam_host_error": "terminate"}},
            "bindings": [
                {
                    "id": "guard-1",
                    "kind": "agent_framework.interceptor",
                    "config": {"name": "missing_guard", "api_token": "SUPER_SECRET_POLICY_TOKEN_99"},
                }
            ],
        }
        with self.assertRaises(hc.ContractError) as ctx:
            hc.validate_and_bind_agent_hooks_declaration(doc, {})
        self.assertNotIn("SUPER_SECRET_POLICY_TOKEN_99", str(ctx.exception))
        self.assertIn("missing_guard", str(ctx.exception))

    def test_04_maf_fides_quarantine_client_scoped_isolation_and_explicit_none(self) -> None:
        mw_a = hc.bind_quarantine_client_to_middleware(hc.ScopedQuarantineMiddleware(), "client-A")
        mw_b = hc.bind_quarantine_client_to_middleware(hc.ScopedQuarantineMiddleware(), "client-B")
        mw_empty = hc.bind_quarantine_client_to_middleware(hc.ScopedQuarantineMiddleware(), None)
        mw_unbound = hc.ScopedQuarantineMiddleware()

        self.assertEqual(hc.resolve_fides_quarantine_client(mw_a, "global-B"), "client-A")
        self.assertEqual(hc.resolve_fides_quarantine_client(mw_b, "global-A"), "client-B")
        # Explicit None in a scoped SecureAgentConfig must NOT inherit the global slot
        self.assertIsNone(hc.resolve_fides_quarantine_client(mw_empty, "global-B"))
        # Standalone / unbound calls retain legacy process-global fallback
        self.assertEqual(hc.resolve_fides_quarantine_client(mw_unbound, "global-B"), "global-B")
        self.assertEqual(hc.resolve_fides_quarantine_client(None, "global-B"), "global-B")

    def test_05_maf_foundry_toolbox_require_approval_fail_closed_matrix(self) -> None:
        self.assertEqual(hc.requires_foundry_toolbox_approval(None), (False, False))
        self.assertEqual(hc.requires_foundry_toolbox_approval({}), (False, False))
        self.assertEqual(hc.requires_foundry_toolbox_approval({"tool_configuration": {}}), (False, False))
        self.assertEqual(
            hc.requires_foundry_toolbox_approval({"tool_configuration": {"require_approval": "never"}}),
            (False, False),
        )
        self.assertEqual(
            hc.requires_foundry_toolbox_approval({"tool_configuration": {"require_approval": "always"}}),
            (True, False),
        )
        # Service-level approval wins over metadata "never"
        self.assertEqual(
            hc.requires_foundry_toolbox_approval(
                {"tool_configuration": {"require_approval": "never"}},
                service_already_requires_approval=True,
            ),
            (True, False),
        )
        # Unsupported or malformed explicit configurations fail closed with warning
        self.assertEqual(
            hc.requires_foundry_toolbox_approval({"tool_configuration": {"require_approval": "sometimes"}}),
            (True, True),
        )
        self.assertEqual(
            hc.requires_foundry_toolbox_approval({"tool_configuration": "malformed-string"}),
            (True, True),
        )

    # ------------------------------------------------------------------
    # 2. Azure AI AgentServer Original-Subject & Copilot SDK AHP Host Auth
    # ------------------------------------------------------------------
    def test_06_azure_agentserver_original_subject_parsing_and_channel_separation(self) -> None:
        headers = {
            "X-MS-Original-Subject": ' \tidtype="user" , tid="tenant-01", oid="obj-01"\t ',
            "x-ms-original-subject-oid": "retired-oid-ignored",
        }
        subj = hc.FoundryOriginalSubject.from_headers(headers)
        self.assertIsNotNone(subj)
        if subj is None:
            self.fail("Expected FoundryOriginalSubject instance")
        self.assertEqual((subj.oid, subj.tid, subj.idtype), ("obj-01", "tenant-01", "user"))

        ctx = hc.FoundryAgentRequestContextContract(
            call_id="call-77",
            user_id="state-partition-user",
            session_id="sess-01",
            original_subject=subj,
        )
        self.assertEqual(
            ctx.model_attribution_headers(),
            {
                "x-ms-original-subject": 'oid="obj-01", tid="tenant-01", idtype="user"',
                "x-agent-foundry-call-id": "call-77",
            },
        )
        # Platform tool callbacks never receive x-ms-original-subject
        self.assertEqual(ctx.platform_headers(), {"x-agent-foundry-call-id": "call-77"})

    def test_07_azure_agentserver_original_subject_absent_does_not_infer_from_user_id(self) -> None:
        ctx = hc.FoundryAgentRequestContextContract(call_id="call-88", user_id="state-only-user")
        self.assertIsNone(ctx.original_subject)
        self.assertEqual(ctx.model_attribution_headers(), {})
        self.assertIsNone(
            hc.FoundryOriginalSubject.from_headers({"x-agent-user-id": "state-only-user"})
        )

    def test_08_azure_agentserver_original_subject_rejects_malformed_duplicate_and_partial_forward(self) -> None:
        # Duplicate headers rejected
        with self.assertRaisesRegex(hc.ContractError, "single header field"):
            hc.FoundryOriginalSubject.from_headers(
                [
                    ("x-ms-original-subject", 'oid="o1"'),
                    ("x-ms-original-subject", 'tid="t1", idtype="user"'),
                ]
            )

        for bad in [
            "",
            'oid="o1", oid="o2"',
            'oid="o1", unknown="v"',
            'oid="o1";param="v"',
            'OID="o1"',
            'oid="bad\r\ninjected"',
        ]:
            with self.assertRaises(hc.ContractError):
                hc.FoundryOriginalSubject.from_headers({"x-ms-original-subject": bad})

        # Partial tuple parses into snapshot but raises on model_attribution_headers()
        partial = hc.FoundryOriginalSubject.from_headers(
            {"x-ms-original-subject": 'oid="obj-01", tid="tenant-01"'}
        )
        self.assertIsNotNone(partial)
        with self.assertRaisesRegex(hc.ContractError, "complete, HTTP-safe tuple"):
            hc.FoundryAgentRequestContextContract(original_subject=partial).model_attribution_headers()

    def test_09_copilot_sdk_ahp_host_custom_auth_and_session_creation_policy(self) -> None:
        # Valid custom admission with future RFC3339 expiry
        ok = hc.evaluate_ahp_host_admission(
            auth_mode="custom",
            require_identity="org-owner-42",
            allow_creating_new_sessions=True,
            is_new_session_request=True,
            admission_token="adm-tok-1",
            callback_result={"identity": "org-owner-42", "expires_at": "2026-10-27T12:00:00Z"},
            now_epoch_seconds=1_793_000_000,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.used_as_inference_credential)

        # Identity mismatch rejected
        mismatch = hc.evaluate_ahp_host_admission(
            auth_mode="custom",
            require_identity="org-owner-42",
            admission_token="adm-tok-1",
            callback_result={"identity": "other-user", "expires_at": "2026-10-27T12:00:00Z"},
            now_epoch_seconds=1_793_000_000,
        )
        self.assertFalse(mismatch.admitted)
        self.assertEqual(mismatch.reason, "custom_auth_identity_mismatch")

        # Expired timestamp rejected
        expired = hc.evaluate_ahp_host_admission(
            auth_mode="custom",
            require_identity="org-owner-42",
            admission_token="adm-tok-1",
            callback_result={"identity": "org-owner-42", "expires_at": "2020-01-01T00:00:00Z"},
            now_epoch_seconds=1_793_000_000,
        )
        self.assertFalse(expired.admitted)
        self.assertEqual(expired.reason, "custom_auth_token_expired")

        # New session blocked when allow_creating_new_sessions is False
        no_new = hc.evaluate_ahp_host_admission(
            auth_mode="none",
            allow_creating_new_sessions=False,
            is_new_session_request=True,
        )
        self.assertFalse(no_new.admitted)
        self.assertEqual(no_new.reason, "new_session_creation_disabled")

    # ------------------------------------------------------------------
    # 3. Google ADK `/run_live` & MCP Go SDK Enterprise Auth
    # ------------------------------------------------------------------
    def test_10_google_adk_run_live_malformed_frame_closes_1007_and_redacts_payload(self) -> None:
        outcome = hc.simulate_adk_run_live_session(
            inbound_frame={"secret_user_prompt": "SSN-999-00-1234", "invented_field": 1},
            validation_error_types=["json_invalid", "extra_forbidden", "json_invalid"],
        )
        self.assertEqual(outcome.wait_policy, "FIRST_COMPLETED")
        self.assertEqual(outcome.close_code, 1007)
        self.assertEqual(outcome.close_reason, "Invalid live request")
        self.assertEqual(outcome.redacted_warning_log, "Invalid live request: extra_forbidden, json_invalid")
        self.assertNotIn("SSN-999-00-1234", outcome.redacted_warning_log or "")
        self.assertTrue(outcome.queue_closed)
        self.assertTrue(outcome.sibling_tasks_cancelled_and_awaited)

    def test_11_google_adk_run_live_normal_and_error_close_codes(self) -> None:
        normal = hc.simulate_adk_run_live_session()
        self.assertEqual(normal.close_code, 1000)
        self.assertTrue(normal.sibling_tasks_cancelled_and_awaited)

        not_found = hc.simulate_adk_run_live_session(runner_exception="SessionNotFoundError")
        self.assertEqual(not_found.close_code, 1002)

        internal = hc.simulate_adk_run_live_session(runner_exception="X" * 200)
        self.assertEqual(internal.close_code, 1011)
        self.assertEqual(len(internal.close_reason), 123)

    def test_12_mcp_go_sdk_rfc9207_iss_and_id_jag_token_type_verification(self) -> None:
        res = hc.verify_mcp_oidc_and_id_jag_exchange(
            expected_state="st-1",
            received_state="st-1",
            expected_issuer="https://idp.example.com",
            received_iss="https://idp.example.com",
            iss_parameter_supported=True,
            exchanged_issued_token_type="urn:ietf:params:oauth:token-type:id-jag",
        )
        self.assertEqual(res, "MCP_ENTERPRISE_TOKEN_EXCHANGE_VERIFIED")

        # Missing iss when IdP advertises RFC 9207 support -> rejected
        with self.assertRaisesRegex(hc.ContractError, "RFC 9207 iss parameter support"):
            hc.verify_mcp_oidc_and_id_jag_exchange(
                expected_state="st-1",
                received_state="st-1",
                expected_issuer="https://idp.example.com",
                received_iss="",
                iss_parameter_supported=True,
                exchanged_issued_token_type="urn:ietf:params:oauth:token-type:id-jag",
            )

        # Wrong iss even when IdP did not advertise support -> rejected
        with self.assertRaisesRegex(hc.ContractError, "does not match expected issuer"):
            hc.verify_mcp_oidc_and_id_jag_exchange(
                expected_state="st-1",
                received_state="st-1",
                expected_issuer="https://idp.example.com",
                received_iss="https://attacker-idp.example.com",
                iss_parameter_supported=False,
                exchanged_issued_token_type="urn:ietf:params:oauth:token-type:id-jag",
            )

    def test_13_mcp_go_sdk_rejects_non_id_jag_access_token_leakage(self) -> None:
        with self.assertRaisesRegex(hc.ContractError, "want 'urn:ietf:params:oauth:token-type:id-jag'"):
            hc.verify_mcp_oidc_and_id_jag_exchange(
                expected_state="st-1",
                received_state="st-1",
                expected_issuer="https://idp.example.com",
                received_iss="https://idp.example.com",
                iss_parameter_supported=True,
                exchanged_issued_token_type="urn:ietf:params:oauth:token-type:access_token",
            )

    # ------------------------------------------------------------------
    # 4. NVIDIA NeMo Helix Closed-Book VirtualModel Route Gate
    # ------------------------------------------------------------------
    def test_14_nemo_helix_closed_book_accepts_last_request_middleware_and_model_free_agents(self) -> None:
        tasks = [("t1", {"environment": {"network_mode": "no-network"}})]
        status = hc.require_closed_book_virtual_model_route(
            agent_name="codex",
            gateway_model_ref="ws/cb-gpt",
            tasks=tasks,
            request_middleware=("nemo-switchyard", "nemo-evals-closed-book"),
        )
        self.assertEqual(status, "ALLOWED_CLOSED_BOOK_VIRTUAL_MODEL_VERIFIED")

        # oracle and nop call no model
        for free_agent in ("oracle", "nop"):
            free_status = hc.require_closed_book_virtual_model_route(
                agent_name=free_agent,
                gateway_model_ref=None,
                tasks=tasks,
            )
            self.assertEqual(free_status, "ALLOWED_NO_CLOSED_BOOK_CHECK_REQUIRED")

    def test_15_nemo_helix_closed_book_rejects_router_after_closed_book_or_response_only(self) -> None:
        tasks = [("offline", {"steps": [{"name": "solve", "agent": {"network_mode": "no-network"}}]})]
        # Router placed AFTER closed-book middleware could re-route to a web-search-enabled model
        with self.assertRaisesRegex(hc.ContractError, "last entry of its VirtualModel's request_middleware"):
            hc.require_closed_book_virtual_model_route(
                agent_name="codex",
                gateway_model_ref="ws/cb-gpt",
                tasks=tasks,
                request_middleware=("nemo-evals-closed-book", "nemo-switchyard"),
            )

        # Response middleware alone is rejected
        with self.assertRaisesRegex(hc.ContractError, "closed_book_required"):
            hc.require_closed_book_virtual_model_route(
                agent_name="codex",
                gateway_model_ref="ws/cb-gpt",
                tasks=tasks,
                request_middleware=(),
                response_middleware=("nemo-evals-closed-book",),
            )

    def test_16_nemo_helix_closed_book_checks_caller_read_permission_before_disclosing_middleware(self) -> None:
        tasks = [("offline", {"environment": {"allow_internet": False}})]
        with self.assertRaises(PermissionError):
            hc.require_closed_book_virtual_model_route(
                agent_name="codex",
                gateway_model_ref="ws/secret-vm",
                tasks=tasks,
                caller_authorized_to_read_virtual_model=False,
                request_middleware=("nemo-evals-closed-book",),
            )

    # ------------------------------------------------------------------
    # 5. OpenAI Codex MITM v2 Body Secret Substitution & Rollout Budget
    # ------------------------------------------------------------------
    def test_17_codex_mitm_v2_body_secret_substitution_and_post_substitution_sigv4(self) -> None:
        placeholder = "codex-secret-0123456789abcdef"
        secret = b"REAL_PRODUCTION_CREDENTIAL_VALUE_9876543210"
        raw_body = f'{{"auth":"{placeholder}"}}'.encode("utf-8")

        res = hc.apply_codex_mitm_v2_body_secret_substitution(
            scheme="https",
            port=443,
            headers={"Content-Length": str(len(raw_body)), "Content-Type": "application/json"},
            body=raw_body,
            replacements=[hc.BodySecretReplacementBinding(placeholder=placeholder, secret_bytes=secret)],
            sign_after_substitution=True,
        )
        expected_body = b'{"auth":"REAL_PRODUCTION_CREDENTIAL_VALUE_9876543210"}'
        self.assertEqual(res.body, expected_body)
        self.assertEqual(res.headers["content-length"], str(len(expected_body)))
        self.assertEqual(
            res.pipeline_trace,
            ("destination_authorized", "body_secret_substituted", "aws_sigv4_signed_over_expanded_body"),
        )

    def test_18_codex_mitm_v2_prevents_recursive_expansion_and_overlapping_bindings(self) -> None:
        p1 = "codex-secret-aaaa1111bbbb2222"
        p2 = "codex-secret-aaaa1111bbbb2222-extended"
        with self.assertRaisesRegex(hc.ContractError, "bindings overlap"):
            hc.apply_codex_mitm_v2_body_secret_substitution(
                scheme="https",
                port=443,
                headers={},
                body=b"{}",
                replacements=[
                    hc.BodySecretReplacementBinding(p1, b"s1"),
                    hc.BodySecretReplacementBinding(p2, b"s2"),
                ],
            )

        # Secret containing another placeholder is rejected at compile/validation time
        p3 = "codex-secret-cccc3333dddd4444"
        with self.assertRaisesRegex(hc.ContractError, "contains a placeholder"):
            hc.apply_codex_mitm_v2_body_secret_substitution(
                scheme="https",
                port=443,
                headers={},
                body=b"{}",
                replacements=[
                    hc.BodySecretReplacementBinding(p1, p3.encode("ascii")),
                    hc.BodySecretReplacementBinding(p3, b"real"),
                ],
            )

    def test_19_codex_mitm_v2_rejects_gzip_trailers_and_client_digest_headers(self) -> None:
        placeholder = "codex-secret-0123456789abcdef"
        binding = [hc.BodySecretReplacementBinding(placeholder, b"secret")]

        for bad_headers in [
            {"Content-Encoding": "gzip"},
            {"Digest": "sha-256=xyz"},
            {"X-Amz-Content-Sha256": "precomputed"},
            {"X-Amz-Checksum-CRC32": "1234"},
        ]:
            with self.assertRaisesRegex(hc.ContractError, "does not support encoded"):
                hc.apply_codex_mitm_v2_body_secret_substitution(
                    scheme="https",
                    port=443,
                    headers=bad_headers,
                    body=b"{}",
                    replacements=binding,
                )

        with self.assertRaisesRegex(hc.ContractError, "request trailers"):
            hc.apply_codex_mitm_v2_body_secret_substitution(
                scheme="https",
                port=443,
                headers={},
                body=b"{}",
                has_trailers=True,
                replacements=binding,
            )

    def test_20_codex_rollout_budget_enforced_vs_advisory_zero_remaining_reminder(self) -> None:
        enforced = hc.CodexRolloutBudgetTracker(
            limit_tokens=30,
            enforce_limit=True,
            reminder_at_remaining_tokens=(20, 10),
        )
        ex1, rem1 = enforced.record_usage(output_tokens=15)
        self.assertFalse(ex1)
        self.assertEqual(rem1, 20)
        ex2, _ = enforced.record_usage(output_tokens=20)
        self.assertTrue(ex2)

        advisory = hc.CodexRolloutBudgetTracker(
            limit_tokens=30,
            enforce_limit=False,
            reminder_at_remaining_tokens=(20, 10),
        )
        adv_ex1, adv_rem1 = advisory.record_usage(output_tokens=35)
        # Advisory mode never raises SessionBudgetExceeded (exhausted=False), but emits 0-remaining reminder
        self.assertFalse(adv_ex1)
        self.assertEqual(adv_rem1, 0)

    # ------------------------------------------------------------------
    # 6. Anthropic Claude Code `mods/sec-default` Reopen & Nested Spawn
    # ------------------------------------------------------------------
    def test_21_claude_sec_default_reopen_allows_only_prepend_and_enforces_65536_regex_cap(self) -> None:
        ok = hc.evaluate_claude_sec_default_reopen_and_safety(
            opener_tier="prepend",
            spells_next_to_user=True,
            matcher_regex_pattern="^Bash\\(git status\\)$",
            event_matches_opener_matcher=True,
            tool_verdict="allow",
        )
        self.assertTrue(ok.user_tier_reopened)
        self.assertFalse(ok.safety_event_emitted)

        # Seated below sec-default -> append floor wins
        below = hc.evaluate_claude_sec_default_reopen_and_safety(
            opener_tier="append",
            spells_next_to_user=True,
            matcher_regex_pattern=".*",
            event_matches_opener_matcher=True,
            tool_verdict="stopped",
        )
        self.assertFalse(below.user_tier_reopened)
        self.assertTrue(below.safety_event_emitted)

        # RegExp > 65,536 chars refused
        over_regex = hc.evaluate_claude_sec_default_reopen_and_safety(
            opener_tier="prepend",
            spells_next_to_user=True,
            matcher_regex_pattern="a" * 65_537,
            event_matches_opener_matcher=True,
            tool_verdict="prompted",
        )
        self.assertFalse(over_regex.user_tier_reopened)
        self.assertEqual(over_regex.reason, "regexp_exceeds_65536_char_limit_reopen_refused")
        self.assertTrue(over_regex.safety_event_emitted)

    def test_22_nested_claude_headless_spawn_requires_restricted_and_empty_tools(self) -> None:
        safe_argv = [
            "claude",
            "-p",
            "--model",
            "haiku",
            "--tools",
            "",
            "--restricted",
            "--no-session-persistence",
        ]
        self.assertTrue(hc.verify_nested_claude_headless_spawn_argv(safe_argv, cwd="/tmp"))

        with self.assertRaisesRegex(hc.ContractError, "missing '--restricted'"):
            hc.verify_nested_claude_headless_spawn_argv(
                ["claude", "-p", "--tools", ""],
                cwd="/tmp",
            )

        with self.assertRaisesRegex(hc.ContractError, 'missing \'--tools ""\''):
            hc.verify_nested_claude_headless_spawn_argv(
                ["claude", "-p", "--restricted"],
                cwd="/tmp",
            )

    # ------------------------------------------------------------------
    # 7. Provenance Manifest & Mutation Calibration Self-Verification
    # ------------------------------------------------------------------
    def test_23_provenance_manifest_integrity_and_14_sources(self) -> None:
        prov_path = Path(__file__).resolve().parent / "fixtures" / "provenance.json"
        data = json.loads(prov_path.read_text(encoding="utf-8"))
        self.assertEqual(data["date"], "2026-10-27")
        self.assertEqual(len(data["sources"]), 14)
        for src in data["sources"]:
            self.assertEqual(src["http_status"], 200)
            self.assertEqual(len(src["revision"]), 40)
            self.assertEqual(len(src["captured_sha256"]), 64)

    def test_24_mutation_calibration_kills_all_6_single_point_mutants(self) -> None:
        summary = run_mutation_calibration()
        self.assertEqual(summary["mutations_total"], 6)
        self.assertEqual(summary["mutations_killed"], 6)


def _run_suite_and_collect_failures() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHarnessContracts20261027)
    # Exclude test_24 itself to avoid recursion during mutation runs
    filtered = unittest.TestSuite(
        [t for t in suite if getattr(t, "_testMethodName", "") != "test_24_mutation_calibration_kills_all_6_single_point_mutants"]
    )
    result = unittest.TestResult()
    filtered.run(result)
    failed = [test.id().split(".")[-1] for test, _ in (result.failures + result.errors)]
    return sorted(failed)


def run_mutation_calibration() -> dict[str, object]:
    """Run 6 targeted single-point mutations and verify each is killed by the test suite."""
    mutations: list[tuple[str, str, object]] = [
        (
            "M1_maf_fides_empty_config_falls_back_to_global",
            "resolve_fides_quarantine_client",
            lambda mw, glob: (mw.quarantine_client_override or glob) if (mw and mw.quarantine_client_bound) else glob,
        ),
        (
            "M2_azure_subject_infers_from_user_id",
            "FoundryAgentRequestContextContract",
            None,  # Handled via method patch below
        ),
        (
            "M3_mcp_enterprise_ignores_issued_token_type",
            "TOKEN_TYPE_ID_JAG",
            "urn:ietf:params:oauth:token-type:access_token",
        ),
        (
            "M4_nemo_closed_book_accepts_any_middleware_position",
            "require_closed_book_virtual_model_route",
            lambda *, agent_name, gateway_model_ref, tasks, caller_authorized_to_read_virtual_model=True, virtual_model_exists=True, request_middleware=(), response_middleware=(): (
                "ALLOWED_CLOSED_BOOK_VIRTUAL_MODEL_VERIFIED"
                if hc.CLOSED_BOOK_MIDDLEWARE in request_middleware
                else "REJECTED"
            ),
        ),
        (
            "M5_codex_mitm_allows_digest_header",
            "FORBIDDEN_INTEGRITY_HEADERS",
            frozenset({"trailer"}),
        ),
        (
            "M6_claude_sec_default_ignores_regex_length_cap",
            "MAX_SEC_DEFAULT_REOPEN_REGEX_CHARS",
            10_000_000,
        ),
    ]

    records: list[dict[str, object]] = []
    killed = 0
    for mid, attr, replacement in mutations:
        if mid == "M2_azure_subject_infers_from_user_id":
            orig_method = hc.FoundryAgentRequestContextContract.model_attribution_headers

            def _mutant_headers(self: hc.FoundryAgentRequestContextContract) -> dict[str, str]:
                if self.original_subject is None and self.user_id:
                    return {"x-ms-original-subject": f'oid="{self.user_id}", tid="t", idtype="user"'}
                return orig_method(self)

            setattr(hc.FoundryAgentRequestContextContract, "model_attribution_headers", _mutant_headers)
            try:
                failed = _run_suite_and_collect_failures()
            finally:
                setattr(hc.FoundryAgentRequestContextContract, "model_attribution_headers", orig_method)
        else:
            orig_val = getattr(hc, attr)
            setattr(hc, attr, replacement)
            try:
                failed = _run_suite_and_collect_failures()
            finally:
                setattr(hc, attr, orig_val)

        status = "KILLED" if failed else "SURVIVED"
        if status == "KILLED":
            killed += 1
        records.append(
            {
                "mutation_id": mid,
                "target": attr,
                "status": status,
                "failed_test_count": len(failed),
                "failed_tests": failed,
            }
        )

    return {
        "mutations_total": len(mutations),
        "mutations_killed": killed,
        "mutations": records,
    }


if __name__ == "__main__":
    unittest.main()
