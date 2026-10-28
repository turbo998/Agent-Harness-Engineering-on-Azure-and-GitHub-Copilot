"""Unit and single-point mutation calibration suite for harness_contracts.py (2026-10-29).

- Zero `assert` statements (`ast.Assert` count == 0) across both implementation and test files.
- Verified under both normal (`python3 -B`) and optimized (`python3 -B -O`) modes.
"""

from __future__ import annotations

import ast
import pathlib
import unittest
from unittest.mock import patch

import harness_contracts as hc
from harness_contracts import (
    ATTACHMENT_MAX_RAW_BYTES_PER_FILE,
    CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS,
    CompactionMessageGroup,
    ContractViolationError,
    CodexConfigServerLifecycleContract,
    DataBoundaryResolverContract,
    GuardianLocalBoardContract,
    GuardianTranscriptEntry,
    SecDefaultVerdict,
    build_maf_redis_scope_filter,
    check_claude_sec_default_env_set,
    compute_maf_redis_scope_token,
    evaluate_claude_sec_default_two_pass,
    evaluate_maf_agent_triggered_compaction,
    evaluate_parallel_tool_cancellation,
    evaluate_pwf_subagent_hook_gate,
    prepare_guardian_sync_transcript,
    sanitize_resiliency_artifact_filename,
    validate_adk_model_supplied_url,
    validate_adk_skill_kebab_name,
    validate_and_snapshot_local_attachment,
    validate_nemo_relay_hook_config,
)


class HarnessContractsTest(unittest.TestCase):
    # --- Group 1: Azure MCP ResiliencyAgent A2A DataBoundary, Attachment Snapshot & ArtifactWriter ---

    def test_01_azure_mcp_data_boundary_maps_eu_and_global_and_caches(self) -> None:
        resolver = DataBoundaryResolverContract()
        routed = resolver.resolve([(503, "busy"), (200, '{"properties":{"dataBoundary":"EU"}}')])
        self.assertEqual(routed, "eu")
        self.assertEqual(resolver.arm_calls, 2)
        cached = resolver.resolve([(200, '{"properties":{"dataBoundary":"Global"}}')])
        self.assertEqual(cached, "eu")
        self.assertEqual(resolver.arm_calls, 2)

        resolver_global = DataBoundaryResolverContract()
        self.assertEqual(resolver_global.resolve([(200, '{"properties":{"dataBoundary":"Global"}}')]), "row")

    def test_02_azure_mcp_data_boundary_fails_closed_on_unknown_malformed_or_sovereign(self) -> None:
        sovereign = DataBoundaryResolverContract(cloud_type="AzureChinaCloud")
        with self.assertRaisesRegex(ContractViolationError, "supported only in Azure public cloud"):
            sovereign.resolve([(200, '{"properties":{"dataBoundary":"Global"}}')])

        unknown_boundary = DataBoundaryResolverContract()
        with self.assertRaisesRegex(ContractViolationError, "could not prepare this request"):
            unknown_boundary.resolve([(200, '{"properties":{"dataBoundary":"USGov"}}'), (200, '{"properties":{"dataBoundary":"EU"}}')])
        self.assertEqual(unknown_boundary.arm_calls, 1)

        non_transient = DataBoundaryResolverContract()
        with self.assertRaisesRegex(ContractViolationError, "could not prepare this request"):
            non_transient.resolve([(403, "forbidden"), (200, '{"properties":{"dataBoundary":"EU"}}')])
        self.assertEqual(non_transient.arm_calls, 1)

    def test_03_azure_mcp_attachment_snapshot_enforces_syntax_1434kib_and_toctou(self) -> None:
        payload = b"resource stg 'Microsoft.Storage/storageAccounts@2023-01-01' = {}"
        snap = validate_and_snapshot_local_attachment(
            "/workspace/infra/main.bicep",
            initial_size=len(payload),
            read_bytes=payload,
        )
        self.assertEqual(snap.file_name, "main.bicep")
        self.assertEqual(snap.size_bytes, len(payload))

        for bad_path in (
            "https://example.com/main.bicep",
            "../secret.bicep",
            "/workspace/$HOME/main.bicep",
            "\\\\server\\share\\main.bicep",
            "C:\\workspace\\CON.bicep",
        ):
            with self.assertRaises(ContractViolationError):
                validate_and_snapshot_local_attachment(bad_path, initial_size=10, read_bytes=b"0123456789")

        with self.assertRaisesRegex(ContractViolationError, "reparse points"):
            validate_and_snapshot_local_attachment(
                "/workspace/link.bicep", is_reparse_point=True, initial_size=4, read_bytes=b"1234"
            )
        with self.assertRaisesRegex(ContractViolationError, "maximum is 1468416"):
            validate_and_snapshot_local_attachment(
                "/workspace/huge.bicep",
                initial_size=ATTACHMENT_MAX_RAW_BYTES_PER_FILE + 1,
                read_bytes=b"x",
            )
        with self.assertRaisesRegex(ContractViolationError, "changed while it was being read"):
            validate_and_snapshot_local_attachment(
                "/workspace/race.bicep",
                initial_size=len(payload),
                read_bytes=payload,
                mtime_changed_during_read=True,
            )

    def test_04_azure_mcp_artifact_writer_strips_traversal_normalizes_and_deduplicates(self) -> None:
        used: set[str] = set()
        first = sanitize_resiliency_artifact_filename(
            "../../.ssh/my  resiliency\tplan.txt",
            artifact_format="bicep",
            existing_names=used,
        )
        self.assertEqual(first, "my-resiliency-plan.bicep")
        second = sanitize_resiliency_artifact_filename(
            "my-resiliency-plan.json",
            artifact_format="bicep",
            existing_names=used,
        )
        self.assertEqual(second, "my-resiliency-plan-2.bicep")
        self.assertIsNone(sanitize_resiliency_artifact_filename("../../.."))
        self.assertIsNone(sanitize_resiliency_artifact_filename("   ---...   "))

    # --- Group 2: Microsoft Agent Framework Python Redis Scope Token & Agent-Triggered Compaction ---

    def test_05_maf_redis_scope_token_prevents_delimiter_collision(self) -> None:
        # Exact NUL-framed vector check: sha256(b"agent-framework:redis-context:v1:user_id\x00alice,admin")
        expected_nul_framed = hc.hashlib.sha256(
            b"agent-framework:redis-context:v1:user_id\x00alice,admin"
        ).hexdigest()
        tok_a = compute_maf_redis_scope_token("user_id", "alice,admin")
        tok_b = compute_maf_redis_scope_token("user_id", "alice")
        tok_agent = compute_maf_redis_scope_token("agent_id", "alice,admin")
        self.assertEqual(tok_a, expected_nul_framed)
        self.assertNotEqual(tok_a, tok_b)
        self.assertNotEqual(tok_a, tok_agent)
        self.assertEqual(len(tok_a), 64)

    def test_06_maf_redis_scope_filter_requires_at_least_one_principal_scope(self) -> None:
        with self.assertRaisesRegex(ContractViolationError, "At least one of the filters"):
            build_maf_redis_scope_filter(session_id="sess-only")
        flt = build_maf_redis_scope_filter(user_id="u-1", session_id="s-1")
        self.assertIn("af_scope_v1_user_id", flt)
        self.assertIn("af_scope_v1_thread_id", flt)
        self.assertIn("af_scope_v1_conversation_id", flt)
        self.assertNotIn("af_scope_v1_agent_id", flt)

    def test_07_maf_agent_triggered_compaction_rejects_server_stored_history(self) -> None:
        g1 = CompactionMessageGroup("g1", [{"name": "compact_context", "completed": True}])
        with self.assertRaisesRegex(ContractViolationError, "requires client-managed history"):
            evaluate_maf_agent_triggered_compaction(
                [g1],
                stores_by_default=True,
                store_option=None,
                wrapped_strategy=lambda _: True,
            )
        with self.assertRaisesRegex(ContractViolationError, "requires client-managed history"):
            evaluate_maf_agent_triggered_compaction(
                [g1],
                stores_by_default=False,
                store_option=False,
                service_conversation_id="conv_remote_123",
                is_local_conversation_id=False,
                wrapped_strategy=lambda _: True,
            )

    def test_08_maf_agent_triggered_compaction_consumes_once_and_restores_on_exception(self) -> None:
        g_old = CompactionMessageGroup("g_old", [{"name": "search", "completed": True}])
        g_trig = CompactionMessageGroup("g_trig", [{"name": "compact_context", "completed": True}])

        def failing_strategy(_: list[CompactionMessageGroup]) -> bool:
            raise RuntimeError("compaction failed")

        with self.assertRaisesRegex(RuntimeError, "compaction failed"):
            evaluate_maf_agent_triggered_compaction(
                [g_old, g_trig],
                store_option=False,
                wrapped_strategy=failing_strategy,
            )
        self.assertFalse(g_trig.excluded)
        self.assertNotIn("_agent_compaction_trigger_consumed", g_trig.tool_calls[0])

        changed = evaluate_maf_agent_triggered_compaction(
            [g_old, g_trig],
            store_option=False,
            exclude_trigger=True,
            wrapped_strategy=lambda groups: False,
        )
        self.assertTrue(changed)
        self.assertTrue(g_trig.excluded)
        self.assertIs(g_trig.tool_calls[0].get("_agent_compaction_trigger_consumed"), True)

        # Second invocation with no new trigger call must be a no-op
        g_trig.excluded = False
        second = evaluate_maf_agent_triggered_compaction(
            [g_old, g_trig],
            store_option=False,
            wrapped_strategy=lambda _: True,
        )
        self.assertFalse(second)

    # --- Group 3: Google ADK Python URL Backslash/NAT64 SSRF & \Z Regex Anchor ---

    def test_09_google_adk_url_validator_rejects_backslash_authority_confusion(self) -> None:
        self.assertEqual(
            validate_adk_model_supplied_url("https://api.example.com/v1/items", resolved_ips=("93.184.216.34",)),
            "api.example.com",
        )
        with self.assertRaisesRegex(ContractViolationError, "Backslash in url authority"):
            validate_adk_model_supplied_url("http://169.254.169.254\\@example.com/latest/meta-data/")

    def test_10_google_adk_url_validator_rejects_nat64_sixtofour_and_mapped_ipv6(self) -> None:
        for ssrf_ip in (
            "64:ff9b::a9fe:a9fe",        # NAT64 169.254.169.254 (is_global is True in Python ipaddress!)
            "64:ff9b::ac10:0101",        # NAT64 172.16.1.1
            "::ffff:127.0.0.1",          # IPv4-mapped loopback
            "2002:0a00:0001::1",         # 6to4 10.0.0.1
            "::10.0.0.1",                # IPv4-compatible private
        ):
            with self.assertRaisesRegex(ContractViolationError, "Blocked"):
                validate_adk_model_supplied_url("https://public.example.com/ hook", resolved_ips=(ssrf_ip,))

    def test_11_google_adk_skill_name_regex_rejects_trailing_newline(self) -> None:
        self.assertEqual(validate_adk_skill_kebab_name("azure-architecture-review"), "azure-architecture-review")
        with self.assertRaisesRegex(ContractViolationError, "Invalid skill name"):
            validate_adk_skill_kebab_name("azure-architecture-review\n")

    # --- Group 4: NVIDIA NeMo Guardrails PreToolUse Client & OpenAI Agents Py Native Queue Cancel ---

    def test_12_nemo_guardrails_relay_rejects_url_credentials_and_client_owned_headers(self) -> None:
        url, keys = validate_nemo_relay_hook_config(
            "https://guardrails.internal.example/prefix",
            {"Authorization": "Bearer tok-123", "X-Tenant-Id": "t-1"},
        )
        self.assertEqual(url, "https://guardrails.internal.example/prefix/v1/hooks/nemo-relay")
        self.assertEqual(keys, ["authorization", "x-tenant-id"])

        with self.assertRaisesRegex(ContractViolationError, "must not embed username or password"):
            validate_nemo_relay_hook_config("https://user:secret@guardrails.internal.example", {})
        with self.assertRaisesRegex(ContractViolationError, "client-owned"):
            validate_nemo_relay_hook_config("https://guardrails.internal.example", {"Transfer-Encoding": "chunked"})
        with self.assertRaisesRegex(ContractViolationError, "value redacted"):
            validate_nemo_relay_hook_config("https://guardrails.internal.example", {"Authorization": "Bearer bad\nval"})

    def test_13_openai_agents_py_stops_native_tool_queue_and_preserves_root_cause(self) -> None:
        res = evaluate_parallel_tool_cancellation(
            function_outcomes=["OK:read", "ERROR:policy_violation"],
            queued_native_tools=["shell:rm -rf /tmp/a", "apply_patch:file.py"],
            cleanup_raises_secondary_error=True,
            post_invoke_wait_seconds=0.1,
        )
        self.assertTrue(res["sibling_category_failure"])
        self.assertEqual(res["executed_native_tools"], [])
        self.assertEqual(res["propagated_error"], "ERROR:policy_violation")
        self.assertEqual(res["cancelled_children_timeout_seconds"], 0.2)

    # --- Group 5: OpenAI Codex Guardian V3 Board, Deferred Truncation & Config-Server Decoupling ---

    def test_14_codex_guardian_v3_board_enforces_readonly_except_self_subscription(self) -> None:
        board = GuardianLocalBoardContract(
            root_session_id="root-sess-1",
            canonical_db_path="/var/codex/message_board_guardian_1.sqlite",
        )
        self.assertEqual(board.database_filename, "message_board_guardian_1.sqlite")
        board.execute_action(access_mode="ReadWrite", caller_agent="main", action="create_channel", channel="alerts")
        board.execute_action(access_mode="ReadWrite", caller_agent="main", action="post", channel="alerts", content="ev1")

        # ReadOnly reviewer can subscribe itself, but cannot subscribe other agents or post/create channels
        sub_self = board.execute_action(
            access_mode="ReadOnly", caller_agent="guardian-reviewer", action="set_subscription", channel="alerts"
        )
        self.assertEqual(sub_self, "subscribed:guardian-reviewer->alerts")
        with self.assertRaisesRegex(ContractViolationError, "read-only"):
            board.execute_action(
                access_mode="ReadOnly",
                caller_agent="guardian-reviewer",
                action="set_subscription",
                channel="alerts",
                target_agent="main",
            )
        with self.assertRaisesRegex(ContractViolationError, "read-only"):
            board.execute_action(
                access_mode="ReadOnly", caller_agent="guardian-reviewer", action="post", channel="alerts", content="spoof"
            )

    def test_15_codex_guardian_v3_board_detects_canonical_path_drift_and_tombstone(self) -> None:
        board = GuardianLocalBoardContract(
            root_session_id="root-sess-2",
            canonical_db_path="/var/codex/message_board_guardian_1.sqlite",
        )
        with self.assertRaisesRegex(ContractViolationError, "board database changed"):
            board.verify_canonical_path("/tmp/symlinked/message_board_guardian_1.sqlite")

        board.execute_action(access_mode="ReadWrite", caller_agent="main", action="delete_board")
        with self.assertRaisesRegex(ContractViolationError, "permanently deleted"):
            board.execute_action(access_mode="ReadWrite", caller_agent="main", action="post", content="late write")

    def test_16_codex_guardian_deferred_truncation_preserves_original_bytes_and_promotes_recent_tools(self) -> None:
        entries = [
            GuardianTranscriptEntry("User", "check deployment logs"),
            GuardianTranscriptEntry("ToolOutput", "A" * 500),
            GuardianTranscriptEntry("ToolOutput", "B" * 500),
            GuardianTranscriptEntry("ToolOutput", "C" * 500),
            GuardianTranscriptEntry("ToolOutput", "D" * 500),
            GuardianTranscriptEntry("ToolOutput", "E" * 500),
            GuardianTranscriptEntry("NodeReplToolOutput", "R" * 600),
        ]
        # Before preparation, NodeReplToolOutput retains all 600 original bytes
        self.assertEqual(entries[-1].original_bytes, 600)

        prepared = prepare_guardian_sync_transcript(
            entries,
            entry_number_offset=0,
            tool_byte_limit=200,
            node_repl_byte_limit=150,
        )
        # 6 tool entries total: oldest tool entry (index 1) is Optional, latest 5 (indices 2..6) are Required
        self.assertEqual(prepared[1].retention, "Optional")
        for idx in range(2, 7):
            self.assertEqual(prepared[idx].retention, "Required")
        self.assertEqual(prepared[6].original_bytes, 600)
        self.assertEqual(prepared[6].retained_bytes, 150)
        self.assertTrue(prepared[6].truncated)

    def test_17_codex_config_server_decouples_enterprise_policy_and_restricts_host_replacement(self) -> None:
        lifecycle = CodexConfigServerLifecycleContract(config_server_enabled=True)
        state = lifecycle.on_model_credential_switch_or_logout()
        self.assertTrue(state["enterprise_bundle_active"])
        self.assertTrue(state["refresh_worker_alive"])
        self.assertFalse(state["mcp_ema_token_cached"])

        lifecycle.code_mode_host_alive = False
        with self.assertRaisesRegex(ContractViolationError, "replacement forbidden outside OpenSession"):
            lifecycle.dispatch_code_mode_rpc(phase="ExecuteTurn")
        self.assertEqual(lifecycle.dispatch_code_mode_rpc(phase="OpenSession"), "host_replaced_at_session_admission")

    # --- Group 6: Claude Code mods/sec-default Two-Pass Verdict & Planning-with-Files Subagent Gate ---

    def test_18_claude_sec_default_two_pass_restores_held_deny_or_host_ask(self) -> None:
        # User mod attempts to loosen an enterprise append-layer deny to allow
        verdict, ran_second_pass = evaluate_claude_sec_default_two_pass(
            full_chain_verdict=SecDefaultVerdict("allow", source_kind="user_mod", reason="lifted by user mod"),
            user_layer_rewrote=True,
            append_only_verdict=SecDefaultVerdict("deny", source_kind="rule", reason="enterprise block"),
        )
        self.assertTrue(ran_second_pass)
        self.assertEqual(verdict.decision, "deny")
        self.assertEqual(verdict.reason, "enterprise block")

        # User mod attempts to reword reason on same-level deny
        verdict2, _ = evaluate_claude_sec_default_two_pass(
            full_chain_verdict=SecDefaultVerdict("deny", source_kind="rule", reason="spoofed reason"),
            user_layer_rewrote=True,
            append_only_verdict=SecDefaultVerdict("deny", source_kind="rule", reason="canonical reason"),
        )
        self.assertEqual(verdict2.reason, "canonical reason")

        # Tightening from ask -> deny by user mod is preserved
        verdict3, _ = evaluate_claude_sec_default_two_pass(
            full_chain_verdict=SecDefaultVerdict("deny", source_kind="user_mod", reason="stricter user block"),
            user_layer_rewrote=True,
            append_only_verdict=SecDefaultVerdict("ask", source_kind="setting", approver="host", reason="host ask"),
        )
        self.assertEqual(verdict3.decision, "deny")
        self.assertEqual(verdict3.reason, "stricter user block")

    def test_19_claude_sec_default_pins_19_security_env_vars_and_fails_closed(self) -> None:
        self.assertEqual(len(CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS), 19)
        for pinned in ("LD_PRELOAD", "node_options", "BASH_ENV", "CLAUDE_CODE_MANAGED_SETTINGS_PATH"):
            with self.assertRaisesRegex(ContractViolationError, "Refused env.set"):
                check_claude_sec_default_env_set(pinned)
        with self.assertRaisesRegex(ContractViolationError, "fail-closed"):
            check_claude_sec_default_env_set("SAFE_USER_VAR", policy_read_failed=True)
        check_claude_sec_default_env_set("SAFE_USER_VAR", managed_env_keys=("CORP_PROXY",))

    def test_20_pwf_subagent_hook_gate_skips_subagents_and_fails_closed_on_malformed_json(self) -> None:
        self.assertEqual(evaluate_pwf_subagent_hook_gate('{"tool_name":"Bash"}'), ("run_main", "main"))
        self.assertEqual(
            evaluate_pwf_subagent_hook_gate('{"tool_name":"Bash","agent_id":"subagent-01"}', skip_subagents=True),
            ("skip", "subagent-01"),
        )
        self.assertEqual(
            evaluate_pwf_subagent_hook_gate('{"tool_name":"Bash","agent_id":"../bad\n"}', skip_subagents=False),
            ("skip", "!invalid"),
        )
        self.assertEqual(evaluate_pwf_subagent_hook_gate("{not-valid-json"), ("skip", "!invalid"))

    # --- Group 7: AST Zero-Assert Gate & Single-Point Mutation Calibration ---

    def test_21_ast_zero_assert_statements_in_contracts_and_tests(self) -> None:
        here = pathlib.Path(__file__).resolve().parent
        for fname in ("harness_contracts.py", "test_harness_contracts.py"):
            tree = ast.parse((here / fname).read_text(encoding="utf-8"), filename=fname)
            assert_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
            self.assertEqual(len(assert_nodes), 0, f"Found forbidden ast.Assert in {fname}")

    def test_22_mutation_calibration_all_six_single_point_mutants_killed(self) -> None:
        mutants = [
            (
                "M1_azure_mcp_allows_non_transient_retry",
                patch.object(hc, "RESILIENCY_TRANSIENT_HTTP_CODES", frozenset({403, 408, 429, 500, 502, 503, 504})),
                "test_02_azure_mcp_data_boundary_fails_closed_on_unknown_malformed_or_sovereign",
            ),
            (
                "M2_maf_redis_omits_nul_separator",
                patch.object(hc, "MAF_REDIS_SCOPE_NUL_SEPARATOR", ":"),
                "test_05_maf_redis_scope_token_prevents_delimiter_collision",
            ),
            (
                "M3_adk_nat64_prefix_disabled",
                patch.object(hc, "ADK_NAT64_WELL_KNOWN_PREFIX", hc.ipaddress.ip_network("2001:db8::/96")),
                "test_10_google_adk_url_validator_rejects_nat64_sixtofour_and_mapped_ipv6",
            ),
            (
                "M4_nemo_allows_transfer_encoding_override",
                patch.object(hc, "NEMO_CLIENT_OWNED_HEADERS", frozenset({"host"})),
                "test_12_nemo_guardrails_relay_rejects_url_credentials_and_client_owned_headers",
            ),
            (
                "M5_codex_guardian_zero_required_recent_tools",
                patch.object(hc, "GUARDIAN_MIN_RECENT_TOOL_ENTRIES", 1),
                "test_16_codex_guardian_deferred_truncation_preserves_original_bytes_and_promotes_recent_tools",
            ),
            (
                "M6_claude_sec_default_drops_bash_env_pin",
                patch.object(
                    hc,
                    "CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS",
                    hc.CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS - {"BASH_ENV"},
                ),
                "test_19_claude_sec_default_pins_19_security_env_vars_and_fails_closed",
            ),
        ]

        for mutant_id, ctx_mgr, target_test_name in mutants:
            with ctx_mgr:
                suite = unittest.TestSuite([HarnessContractsTest(target_test_name)])
                result = unittest.TestResult()
                suite.run(result)
                total_failures = len(result.failures) + len(result.errors)
                self.assertGreaterEqual(
                    total_failures,
                    1,
                    f"Mutant {mutant_id} survived against {target_test_name}",
                )

    def test_23_monitor_ingestion_and_provenance_fixture_integrity(self) -> None:
        here = pathlib.Path(__file__).resolve().parent
        prov_path = here / "fixtures" / "provenance.json"
        data = hc.json.loads(prov_path.read_text(encoding="utf-8"))
        self.assertEqual(data["date"], "2026-10-29")
        self.assertEqual(len(data["sources"]), 15)
        for src in data["sources"]:
            self.assertEqual(src["http_status"], 200)
            self.assertEqual(len(src["revision"]), 40)
            self.assertEqual(len(src["captured_sha256"]), 64)

    def test_24_codex_guardian_board_rejects_oversized_post_and_invalid_namespace(self) -> None:
        with self.assertRaisesRegex(ContractViolationError, "Invalid storage namespace"):
            GuardianLocalBoardContract(root_session_id="s1", canonical_db_path="/db", namespace="../bad")
        board = GuardianLocalBoardContract(root_session_id="s1", canonical_db_path="/db")
        with self.assertRaisesRegex(ContractViolationError, "MAX_POST_BYTES"):
            board.execute_action(
                access_mode="ReadWrite",
                caller_agent="main",
                action="post",
                content="x" * (64 * 1024 + 1),
            )


if __name__ == "__main__":
    unittest.main()
