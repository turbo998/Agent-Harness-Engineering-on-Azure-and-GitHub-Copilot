#!/usr/bin/env python3
"""Unit and mutation-calibration tests for harness_contracts.py (2026-10-19).

Runs in both normal (`python3 -B`) and optimized (`python3 -B -O`) modes without
relying on bare `assert` statements for integrity checks.
"""
from __future__ import annotations

import copy
import unittest
from typing import Any

import harness_contracts as hc


class BusinessOracleError(AssertionError):
    """Explicit business-oracle failure used for mutation calibration."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BusinessOracleError(message)


class TestMAFAGUIScopeAndApprovalShape(unittest.TestCase):
    def test_01_scope_config_rejects_zero_modes(self) -> None:
        with self.assertRaises(ValueError):
            hc.validate_agui_scope_config()

    def test_02_scope_config_rejects_multiple_modes(self) -> None:
        with self.assertRaises(ValueError):
            hc.validate_agui_scope_config(
                authorization_scope_resolver=lambda: "tenant-a",
                single_user=True,
            )

    def test_03_scope_config_rejects_non_bool_single_user(self) -> None:
        with self.assertRaises(TypeError):
            hc.validate_agui_scope_config(single_user="true")

    def test_04_scope_resolver_failure_raises_without_fallback(self) -> None:
        for bad_value in ("", None, 123):
            with self.subTest(bad_value=bad_value):
                with self.assertRaises(RuntimeError) as ctx:
                    hc.resolve_agui_request_scope(
                        authorization_scope_resolver=lambda v=bad_value: v
                    )
                _require("HTTP_500" in str(ctx.exception), "Expected HTTP_500 on invalid scope")

    def test_05_valid_authorization_and_single_user_scopes(self) -> None:
        self.assertEqual(
            hc.resolve_agui_request_scope(authorization_scope_resolver=lambda: "tenant:42"),
            "tenant:42",
        )
        self.assertEqual(
            hc.resolve_agui_request_scope(
                single_user=True, registration_scope_id="ag-ui:single-user:demo1"
            ),
            "ag-ui:single-user:demo1",
        )

    def test_06_client_shared_state_blocks_approval_authority_by_shape(self) -> None:
        server_state: dict[str, Any] = {"existing": {"count": 1}}
        client_state: dict[str, Any] = {
            "benign_note": {"text": "hello"},
            "hidden_rules": {"rules": [{"tool_name": "gated_tool"}]},
            "hidden_queue": {"queued_approval_requests": [["id", "req1"]]},
            "hidden_resp": {"collected_approval_responses": [{"approved": True}]},
            "empty_rules_allowed": {"rules": []},
        }
        merged, ignored = hc.merge_agui_shared_state(
            server_session_state=server_state,
            client_shared_state=client_state,
            named_protected_keys=(),
        )
        self.assertEqual(ignored, {"hidden_rules", "hidden_queue", "hidden_resp"})
        self.assertNotIn("hidden_rules", merged)
        self.assertNotIn("hidden_queue", merged)
        self.assertNotIn("hidden_resp", merged)
        self.assertIn("benign_note", merged)
        self.assertIn("empty_rules_allowed", merged)

    def test_07_server_existing_approval_state_cannot_be_overwritten_by_empty_client_list(self) -> None:
        server_state: dict[str, Any] = {
            "custom_approvals": hc.ToolApprovalStateMarker(rules=("gated_tool",)),
            "mapping_approvals": {"rules": ["admin_tool"]},
        }
        client_state: dict[str, Any] = {
            "custom_approvals": {"rules": []},
            "mapping_approvals": {"other": "wipe"},
        }
        merged, _ = hc.merge_agui_shared_state(
            server_session_state=server_state,
            client_shared_state=client_state,
        )
        self.assertIsInstance(merged["custom_approvals"], hc.ToolApprovalStateMarker)
        self.assertEqual(merged["mapping_approvals"], {"rules": ["admin_tool"]})


class TestAzureMCPCommandContextAndSSRFPolicy(unittest.TestCase):
    def test_08_missing_or_blank_context_keeps_ssrf_enabled_even_under_all(self) -> None:
        policy = hc.SsrfProtectionPolicy(["ALL"])
        accessor = hc.CommandContextAccessor()
        self.assertTrue(policy.are_ssrf_protections_enabled(accessor))
        for blank in ("", "   ", None):
            dispose = accessor.begin_scope(hc.CommandContext(tool_namespace_name=blank))
            try:
                self.assertTrue(policy.are_ssrf_protections_enabled(accessor))
            finally:
                dispose()

    def test_09_untrimmed_all_marker_does_not_disable_all_namespaces(self) -> None:
        policy = hc.SsrfProtectionPolicy([" ALL ", "compute"])
        accessor = hc.CommandContextAccessor()
        dispose_storage = accessor.begin_scope(hc.CommandContext(tool_namespace_name="storage"))
        try:
            self.assertTrue(policy.are_ssrf_protections_enabled(accessor))
        finally:
            dispose_storage()
        dispose_compute = accessor.begin_scope(hc.CommandContext(tool_namespace_name="COMPUTE"))
        try:
            self.assertFalse(policy.are_ssrf_protections_enabled(accessor))
        finally:
            dispose_compute()

    def test_10_scope_dispose_clears_captured_holder_and_blocks_nesting(self) -> None:
        accessor = hc.CommandContextAccessor()
        dispose = accessor.begin_scope(hc.CommandContext(tool_namespace_name="compute"))
        floating_reader = accessor.capture_floating_reader()
        self.assertEqual(floating_reader(), hc.CommandContext(tool_namespace_name="compute"))
        with self.assertRaises(RuntimeError):
            accessor.begin_scope(hc.CommandContext(tool_namespace_name="nested"))
        dispose()
        self.assertIsNone(accessor.current_context)
        self.assertIsNone(floating_reader())

    def test_11_proxy_and_direct_transport_selection_requires_valid_endpoint(self) -> None:
        policy = hc.SsrfProtectionPolicy(["compute"])
        accessor = hc.CommandContextAccessor()
        with self.assertRaises(PermissionError):
            hc.select_mcp_http_transport(
                request_uri="https://169.254.169.254/metadata",
                proxy_uri="http://proxy.corp:8080",
                policy=policy,
                accessor=accessor,
                endpoint_valid=False,
            )
        self.assertEqual(
            hc.select_mcp_http_transport(
                request_uri="https://management.azure.com/subscriptions",
                proxy_uri="http://proxy.corp:8080",
                policy=policy,
                accessor=accessor,
                endpoint_valid=True,
            ),
            "proxied_transport",
        )
        # PAC DIRECT or NO_PROXY returning same URI uses direct protected transport when no scope
        self.assertEqual(
            hc.select_mcp_http_transport(
                request_uri="https://management.azure.com/subscriptions",
                proxy_uri="https://management.azure.com/subscriptions",
                policy=policy,
                accessor=accessor,
                endpoint_valid=True,
            ),
            "protected_anti_ssrf_transport",
        )


class TestMAFDotNetAutoRejectAndWorkflowHoldback(unittest.TestCase):
    def test_12_unanswered_approvals_auto_rejected_and_cloned_without_mutating_saved(self) -> None:
        saved = {
            "call-1": hc.FunctionCallObj("call-1", "delete_vm"),
            "call-2": hc.FunctionCallObj("call-2", "list_vms"),
            "call-settled": hc.FunctionCallObj("call-settled", "read_tag"),
        }
        outcome = hc.bind_or_auto_reject_approvals(
            saved_pending_requests=saved,
            supplied_decisions={"call-2": True},
            settled_call_ids=("call-settled",),
            inner_call_succeeds=True,
        )
        self.assertEqual(outcome["generated_rejections"], [("call-1", False, False)])
        self.assertEqual(
            outcome["ficc_decisions"],
            [("call-1", False, True), ("call-2", True, True)],
        )
        self.assertFalse(outcome["original_mutated"])
        self.assertEqual(outcome["remaining_pending"], {})

    def test_13_failed_inner_call_retains_unmutated_pending_requests_for_retry(self) -> None:
        saved = {"call-1": hc.FunctionCallObj("call-1", "delete_vm")}
        outcome = hc.bind_or_auto_reject_approvals(
            saved_pending_requests=saved,
            supplied_decisions={},
            inner_call_succeeds=False,
        )
        self.assertIn("call-1", outcome["remaining_pending"])
        self.assertFalse(outcome["remaining_pending"]["call-1"].informational_only)

    def test_14_workflow_forwarding_requires_both_completed_call_and_result(self) -> None:
        with self.assertRaises(RuntimeError):
            hc.build_workflow_forwarded_approval(
                call_id="call-1",
                completed_calls={"call-1": "deploy"},
                completed_results={},
                approved=True,
            )
        forwarded = hc.build_workflow_forwarded_approval(
            call_id="call-1",
            completed_calls={"call-1": "deploy"},
            completed_results={"call-1": "ok"},
            approved=True,
        )
        self.assertTrue(forwarded["has_result"])


class TestGoogleADKRetryRewindAndLoopJoinBarrier(unittest.TestCase):
    def test_15_dynamic_child_retry_rewinds_to_attempt_snapshot_not_zero(self) -> None:
        sched = hc.DynamicCounterScheduler()
        # Attempt 1: parent runs fetch -> fetch_1, then parent rejects fetch_1 (no child retry)
        first_id = sched.next_run_id("fetch", "root/parent")
        self.assertEqual(first_id, "fetch_1")

        # Attempt 2 starts: snapshot taken at attempt start ({'root/parent': {'fetch': 1}})
        snap_attempt_2 = sched.snapshot_counters("root/parent")
        second_id = sched.next_run_id("fetch", "root/parent")
        self.assertEqual(second_id, "fetch_2")
        # Child fails inside Attempt 2 -> rewind to snap_attempt_2
        sched.reset_for_retry("root/parent", snap_attempt_2)

        # Attempt 3 must produce fetch_2 (fresh run after rejected fetch_1), NOT replay fetch_1
        third_id = sched.next_run_id("fetch", "root/parent")
        self.assertEqual(third_id, "fetch_2")

    def test_16_loop_join_barrier_waits_for_each_iteration_and_clears_none_output(self) -> None:
        barrier = hc.LoopJoinBarrier(predecessors=frozenset({"node_a", "node_b"}))
        self.assertIsNone(barrier.record_completion("node_a", "A1"))
        first_join = barrier.record_completion("node_b", "B1")
        self.assertEqual(first_join, {"node_a": "A1", "node_b": "B1"})

        # Iteration 2: node_a finishes with None; join must NOT fire with stale B1
        self.assertIsNone(barrier.record_completion("node_a", None))
        second_join = barrier.record_completion("node_b", "B2")
        self.assertEqual(second_join, {"node_a": None, "node_b": "B2"})


class TestCodexWakeGateAndCookbookMCPGrader(unittest.TestCase):
    def test_17_codex_wake_on_agent_messages_respects_three_boundaries(self) -> None:
        # Positive case: enabled, root, not interrupted, pending mail, default mode
        self.assertTrue(
            hc.should_wake_on_agent_messages(
                feature_enabled=True,
                is_interrupted=False,
                has_pending_mailbox_items=True,
                is_non_root_agent=False,
                collaboration_mode="default",
            )
        )
        # Negative 1: interrupted root
        self.assertFalse(
            hc.should_wake_on_agent_messages(
                feature_enabled=True,
                is_interrupted=True,
                has_pending_mailbox_items=True,
                is_non_root_agent=False,
                collaboration_mode="default",
            )
        )
        # Negative 2: Plan mode root
        self.assertFalse(
            hc.should_wake_on_agent_messages(
                feature_enabled=True,
                is_interrupted=False,
                has_pending_mailbox_items=True,
                is_non_root_agent=False,
                collaboration_mode="plan",
            )
        )
        # Negative 3: inherited child subagent
        self.assertFalse(
            hc.should_wake_on_agent_messages(
                feature_enabled=True,
                is_interrupted=False,
                has_pending_mailbox_items=True,
                is_non_root_agent=True,
                collaboration_mode="default",
            )
        )

    def test_18_queue_only_wake_retains_previous_turn_options(self) -> None:
        self.assertEqual(
            hc.select_woken_turn_options(
                has_trigger_turn_mail=False,
                previous_options="effort=high",
            ),
            "effort=high",
        )
        self.assertEqual(
            hc.select_woken_turn_options(
                has_trigger_turn_mail=True,
                previous_options="effort=high",
            ),
            "default_options",
        )

    def test_19_cookbook_grader_catches_skipped_resolve_and_unexpected_series(self) -> None:
        # Without MCP instructions: Codex skips resolve and fetches memorized series
        before_items = [
            {
                "type": "mcp_tool_call",
                "tool": "fetch_bls_data",
                "arguments": {"series_ids": ["CUUR0000SA0", "WRONG_MEMORIZED"]},
                "result": {
                    "structured_content": {
                        "data": [{"series_id": "CUUR0000SA0"}, {"series_id": "WRONG_MEMORIZED"}]
                    }
                },
            }
        ]
        verdict_before = hc.grade_codex_mcp_trace(
            raw_items=before_items,
            expected_tools=["resolve", "fetch_bls_data"],
            expected_series_ids=["CUUR0000SA0"],
            final_answer="CPI rose.",
        )
        self.assertFalse(verdict_before["pass"])
        self.assertIn("missing tools: ['resolve']", verdict_before["reason"])
        self.assertIn("fetched series outside the expectation: ['WRONG_MEMORIZED']", verdict_before["reason"])

        # With MCP instructions: Codex resolves first and fetches exact series
        after_items = [
            {
                "type": "mcp_tool_call",
                "tool": "resolve",
                "arguments": {"indicator": "consumer price index"},
                "result": {"structured_content": {"candidates": ["CUUR0000SA0"]}},
            },
            {
                "type": "mcp_tool_call",
                "tool": "fetch_bls_data",
                "arguments": {"series_ids": ["CUUR0000SA0"]},
                "result": {"structured_content": {"data": [{"series_id": "CUUR0000SA0"}]}},
            },
        ]
        verdict_after = hc.grade_codex_mcp_trace(
            raw_items=after_items,
            expected_tools=["resolve", "fetch_bls_data"],
            expected_series_ids=["CUUR0000SA0"],
            final_answer="CPI is 314.5.",
        )
        self.assertTrue(verdict_after["pass"])
        self.assertEqual(verdict_after["score"], 1.0)


class TestClaudeSecDefaultTwoPassAndEnvPinning(unittest.TestCase):
    def test_20_sec_default_restores_held_deny_or_ask_when_user_mod_loosens(self) -> None:
        held_deny = hc.Verdict(decision="deny", source="rule", rule="Bash(rm -rf *)")
        user_allow = hc.Verdict(decision="allow", source="user_mod", rule=None)
        final_verdict, action = hc.evaluate_sec_default_tool_check(
            full_chain_answer=user_allow,
            append_only_answer=held_deny,
            user_tier_rewrote=True,
        )
        self.assertEqual(final_verdict, held_deny)
        self.assertEqual(action, "lift")

        # User tightening (ask -> deny) is preserved
        held_ask = hc.Verdict(decision="ask", source="rule", rule="Bash(git push *)")
        user_deny = hc.Verdict(decision="deny", source="user_mod", rule="strict_local")
        tight_verdict, tight_action = hc.evaluate_sec_default_tool_check(
            full_chain_answer=user_deny,
            append_only_answer=held_ask,
            user_tier_rewrote=True,
        )
        self.assertEqual(tight_verdict, user_deny)
        self.assertIsNone(tight_action)

    def test_21_sec_default_detects_reworded_ask_and_fails_closed_on_policy_error(self) -> None:
        held_ask = hc.Verdict(decision="ask", source="host", rule="host_callback")
        reworded_ask = hc.Verdict(decision="ask", source="user_mod", rule="spoofed_reason")
        final_verdict, action = hc.evaluate_sec_default_tool_check(
            full_chain_answer=reworded_ask,
            append_only_answer=held_ask,
            user_tier_rewrote=True,
            deny_rules_hold_policy=False,
            policy_read_failed=True,
        )
        self.assertEqual(final_verdict, held_ask)
        self.assertEqual(action, "reword")

    def test_22_sec_default_env_set_pins_19_vars_managed_keys_and_fails_closed(self) -> None:
        for var in ("LD_PRELOAD", "NODE_OPTIONS", "CLAUDE_CODE_MANAGED_SETTINGS_PATH", "corp_proxy"):
            res = hc.evaluate_sec_default_env_set(
                caller_tier="user",
                var_name=var,
                managed_env_keys=("CORP_PROXY",),
            )
            self.assertEqual(res, "deny_pinned")

        self.assertEqual(
            hc.evaluate_sec_default_env_set(
                caller_tier="user",
                var_name="CUSTOM_UNPINNED_VAR",
                managed_env_keys=(),
                policy_read_failed=False,
            ),
            "pass_chain",
        )
        # Fail-closed when policy cannot be read: every variable counts as pinned
        self.assertEqual(
            hc.evaluate_sec_default_env_set(
                caller_tier="user",
                var_name="CUSTOM_UNPINNED_VAR",
                managed_env_keys=(),
                policy_read_failed=True,
            ),
            "deny_pinned",
        )


def run_mutation_calibration() -> dict[str, Any]:
    """Run 6 single-point negative-control mutations and verify each is killed."""
    loader = unittest.TestLoader()
    suite_classes = (
        TestMAFAGUIScopeAndApprovalShape,
        TestAzureMCPCommandContextAndSSRFPolicy,
        TestMAFDotNetAutoRejectAndWorkflowHoldback,
        TestGoogleADKRetryRewindAndLoopJoinBarrier,
        TestCodexWakeGateAndCookbookMCPGrader,
        TestClaudeSecDefaultTwoPassAndEnvPinning,
    )

    def _run_all() -> tuple[int, int, list[str]]:
        suite = unittest.TestSuite()
        for cls in suite_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))
        result = unittest.TestResult()
        suite.run(result)
        failed_ids = [t.id().split(".")[-1] for t, _ in result.failures + result.errors]
        return result.testsRun, len(failed_ids), failed_ids

    base_total, base_fail, base_failed_ids = _run_all()
    _require(base_total == 22 and base_fail == 0, f"Baseline failed: {base_failed_ids}")

    mutations: list[tuple[str, str, Any]] = [
        (
            "M1_agui_skip_shape_guard",
            "carries_tool_approval_authority",
            lambda value: False,
        ),
        (
            "M2_mcp_blank_context_allows_all_override",
            "SsrfProtectionPolicy",
            type(
                "MutatedSsrfPolicy",
                (),
                {
                    "__init__": hc.SsrfProtectionPolicy.__init__,
                    "are_ssrf_protections_enabled": lambda self, accessor: (
                        "all" not in self._disabled_lower
                    ),
                },
            ),
        ),
        (
            "M3_maf_dotnet_mutate_saved_request_in_place",
            "bind_or_auto_reject_approvals",
            lambda *, saved_pending_requests, supplied_decisions, settled_call_ids=(), inner_call_succeeds=True: (
                [setattr(c, "informational_only", True) for c in saved_pending_requests.values()]
                and {}
            )
            or {
                "generated_rejections": [("call-1", False, True)],
                "ficc_decisions": [],
                "remaining_pending": saved_pending_requests,
                "original_mutated": True,
            },
        ),
        (
            "M4_adk_rewind_counter_to_zero",
            "DynamicCounterScheduler",
            type(
                "MutatedScheduler",
                (hc.DynamicCounterScheduler,),
                {
                    "reset_for_retry": lambda self, parent_path, snapshot: self.run_counters.clear()
                },
            ),
        ),
        (
            "M5_codex_wake_ignores_plan_and_subagent_guards",
            "should_wake_on_agent_messages",
            lambda *, feature_enabled, is_interrupted, has_pending_mailbox_items, is_non_root_agent, collaboration_mode: (
                feature_enabled and not is_interrupted and has_pending_mailbox_items
            ),
        ),
        (
            "M6_claude_sec_default_fail_open_on_user_lift",
            "evaluate_sec_default_tool_check",
            lambda *, full_chain_answer, append_only_answer, user_tier_rewrote, deny_rules_hold_policy=True, policy_read_failed=False: (
                full_chain_answer,
                None,
            ),
        ),
    ]

    mutation_records: list[dict[str, Any]] = []
    for mut_id, attr_name, replacement in mutations:
        original = getattr(hc, attr_name)
        setattr(hc, attr_name, replacement)
        try:
            _, fail_count, failed_ids = _run_all()
            killed = fail_count > 0
            _require(killed, f"Mutation {mut_id} survived!")
            mutation_records.append(
                {
                    "mutation_id": mut_id,
                    "target": attr_name,
                    "status": "KILLED",
                    "failed_test_count": fail_count,
                    "failed_tests": failed_ids,
                }
            )
        finally:
            setattr(hc, attr_name, original)

    post_total, post_fail, _ = _run_all()
    _require(post_total == 22 and post_fail == 0, "Post-mutation baseline restoration failed")
    return {
        "baseline_tests": base_total,
        "baseline_passed": base_total - base_fail,
        "mutations_total": len(mutation_records),
        "mutations_killed": len(mutation_records),
        "mutations": mutation_records,
    }


if __name__ == "__main__":
    summary = run_mutation_calibration()
    unittest.main(verbosity=2)
