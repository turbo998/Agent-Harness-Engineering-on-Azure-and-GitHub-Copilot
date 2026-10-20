"""Offline unit tests and 7-mutation calibration suite (2026-10-21).

Runs with zero `assert` statements so behavior is identical under:
  python3 -B test_harness_contracts.py
  python3 -B -O test_harness_contracts.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import harness_contracts as hc
from harness_contracts import BusinessOracleFailure

BASE_DIR = Path(__file__).resolve().parent
TRACES_PATH = BASE_DIR / "fixtures" / "cookbook_recorded_traces.json"
PROVENANCE_PATH = BASE_DIR / "fixtures" / "provenance.json"


def _expect_true(cond: bool, msg: str) -> None:
    if not cond:
        raise BusinessOracleFailure(msg)


def _expect_equal(actual: Any, expected: Any, msg: str) -> None:
    if actual != expected:
        raise BusinessOracleFailure(f"{msg}: expected {expected!r}, got {actual!r}")


def _expect_raises(exc_type: Any, fn: Callable[[], Any], msg: str) -> Exception:
    try:
        fn()
    except exc_type as exc:
        return exc
    except Exception as exc:
        raise BusinessOracleFailure(f"{msg}: expected {exc_type}, got {type(exc).__name__}: {exc}") from exc
    raise BusinessOracleFailure(f"{msg}: expected {exc_type}, but no exception was raised")


# ============================================================================
# 24 Baseline Contract & Replay Tests
# ============================================================================

def test_01_copilot_limit_to_rejects_scheme_port_path_and_query(mutation: Optional[str] = None) -> None:
    bad_rules = [
        "Domain(https://api.github.com)",
        "Domain(api.github.com:443)",
        "Domain(api.github.com/v1)",
        "Domain(api.github.com?foo=1)",
        "Domain(*.com)",
        "Domain(*)",
        "https://api.github.com",
    ]
    for rule in bad_rules:
        _expect_raises(
            ValueError,
            lambda r=rule: hc.evaluate_copilot_limit_to([[r]], "api.github.com", _mutation=mutation),
            f"rule {rule!r} must be rejected",
        )


def test_02_copilot_limit_to_intersection_and_empty_vs_null(mutation: Optional[str] = None) -> None:
    # None means unrestricted
    _expect_true(
        hc.evaluate_copilot_limit_to([None, None], "127.0.0.2", _mutation=mutation),
        "all-None layers should allow host",
    )
    # Explicit empty list [] denies all hosts
    _expect_equal(
        hc.evaluate_copilot_limit_to([["Domain(*.corp.internal)"], []], "api.corp.internal", _mutation=mutation),
        False,
        "explicit empty limitTo array must deny all hosts",
    )
    # Multi-layer intersection
    layer_a = ["Domain(*.corp.internal)", "Domain(127.0.0.1)"]
    layer_b = ["Domain(api.corp.internal)", "Domain(10.0.0.1)"]
    _expect_true(
        hc.evaluate_copilot_limit_to([layer_a, layer_b], "api.corp.internal", _mutation=mutation),
        "host in intersection of wildcard and exact rule must be allowed",
    )
    _expect_equal(
        hc.evaluate_copilot_limit_to([layer_a, layer_b], "127.0.0.1", _mutation=mutation),
        False,
        "host only in layer_a must be denied by layer_b intersection",
    )


def test_03_copilot_pre_mcp_sandbox_create_and_managed_conflict(mutation: Optional[str] = None) -> None:
    cfg = {"enabled": True, "sandboxMcpServers": True, "userPolicy": {"network": {"allowOutbound": False}}}
    out = hc.evaluate_copilot_session_sandbox(mode="create", requested_sandbox=cfg, managed_conflict=False)
    _expect_true(out.mcp_started_under_sandbox, "createSession must confine MCP before startup")
    _expect_equal(out.mcp_restarted, False, "initial create should not restart MCP")

    err = _expect_raises(
        RuntimeError,
        lambda: hc.evaluate_copilot_session_sandbox(mode="create", requested_sandbox=cfg, managed_conflict=True),
        "managed sandbox conflict must fail session creation",
    )
    _expect_true("managed_sandbox_policy_conflict" in str(err), "error code must name managed_sandbox_policy_conflict")


def test_04_copilot_cold_vs_resident_resume_and_idempotent_update(mutation: Optional[str] = None) -> None:
    cfg = {"enabled": True, "sandboxMcpServers": True}
    cold = hc.evaluate_copilot_session_sandbox(mode="cold_resume", requested_sandbox=None, resident_sandbox=cfg)
    _expect_equal(cold.mcp_started_under_sandbox, False, "cold resume omitting sandboxConfig loses confinement")

    resident = hc.evaluate_copilot_session_sandbox(mode="resident_resume", requested_sandbox=None, resident_sandbox=cfg)
    _expect_true(resident.mcp_started_under_sandbox, "resident resume omitting sandboxConfig keeps resident policy")

    same_upd = hc.evaluate_copilot_session_sandbox(mode="update", requested_sandbox=cfg, resident_sandbox=cfg)
    _expect_equal(same_upd.mcp_restarted, False, "identical options.update must not restart MCP servers")

    diff_upd = hc.evaluate_copilot_session_sandbox(
        mode="update",
        requested_sandbox={"enabled": True, "sandboxMcpServers": True, "extra": 1},
        resident_sandbox=cfg,
    )
    _expect_true(diff_upd.mcp_restarted, "changed sandbox policy on update must restart MCP servers")


def test_05_maf_dotnet_scoped_vs_singleton_agent_lifetime(mutation: Optional[str] = None) -> None:
    scoped_ep = hc.HostedAgentEndpointSimulator("Scoped", "triage-agent")
    _expect_equal(scoped_ep._counter, 0, "Scoped agent must not be instantiated at route mapping time")
    code1, res1 = scoped_ep.handle_request({})
    code2, res2 = scoped_ep.handle_request({})
    _expect_equal((code1, code2), (200, 200), "Scoped requests should succeed")
    if res1 is None or res2 is None:
        raise BusinessOracleFailure("Scoped response payload missing")
    _expect_true(res1["agent_instance_id"] != res2["agent_instance_id"], "Scoped agent must resolve per request")
    _expect_equal(res1["session_storage_identity"], "triage-agent", "session partition must stay stable")

    single_ep = hc.HostedAgentEndpointSimulator("Singleton", "singleton-agent")
    _expect_equal(single_ep._counter, 1, "Singleton agent resolved once at mapping time")
    _, s1 = single_ep.handle_request({})
    _, s2 = single_ep.handle_request({})
    if s1 is None or s2 is None:
        raise BusinessOracleFailure("Singleton response payload missing")
    _expect_equal(s1["agent_instance_id"], s2["agent_instance_id"], "Singleton instance reused across requests")


def test_06_maf_dotnet_request_selector_404_skips_store_and_blank_name_rejected(
    mutation: Optional[str] = None,
) -> None:
    ep = hc.HostedAgentEndpointSimulator(
        "Selector",
        None,
        factory=lambda ctx: None if ctx.get("unknown") else hc.AgentInstance(name=ctx.get("name", "dyn"), instance_id=9),
    )
    code, payload = ep.handle_request({"unknown": True})
    _expect_equal(code, 404, "null selector result must return HTTP 404")
    _expect_equal(payload, None, "404 response has no session payload")
    _expect_equal(ep.store_load_calls, 0, "404 selector must not touch AgentSessionStore")

    _expect_raises(
        ValueError,
        lambda: ep.handle_request({"name": "   "}),
        "whitespace-only selected agent Name must raise InvalidOperationException",
    )
    _expect_equal(ep.store_load_calls, 0, "invalid selected agent Name must fail before loading session store")


def test_07_maf_dotnet_duplicate_approval_id_purges_state_and_saves(mutation: Optional[str] = None) -> None:
    state = hc.ToolApprovalState(
        surfaced_approval_requests={"call-dup": "read_file", "call-ok": "list_dir"},
        queued_approval_requests=[("call-dup", "read_file"), ("call-ok", "list_dir")],
        collected_approval_responses=[("call-dup", True), ("call-ok", True)],
    )
    _expect_raises(
        ValueError,
        lambda: hc.ensure_approval_request_ids_unique(
            [("call-dup", "delete_production_db")],
            state,
            include_surfaced_requests=True,
            _mutation=mutation,
        ),
        "duplicate request ID across surfaced state must raise",
    )
    _expect_true("call-dup" not in state.surfaced_approval_requests, "colliding ID must be purged from surfaced")
    _expect_true(
        all(req_id != "call-dup" for req_id, _ in state.queued_approval_requests),
        "colliding ID must be purged from queued requests",
    )
    _expect_true(
        all(req_id != "call-dup" for req_id, _ in state.collected_approval_responses),
        "colliding ID must be purged from collected responses",
    )
    _expect_true("call-ok" in state.surfaced_approval_requests, "non-colliding ID must remain intact")
    _expect_equal(state.saved_snapshots, 1, "purged state must be persisted to session store")


def test_08_maf_dotnet_unique_approval_ids_recorded_cleanly(mutation: Optional[str] = None) -> None:
    state = hc.ToolApprovalState()
    hc.ensure_approval_request_ids_unique(
        [("call-1", "tool_a"), ("call-2", "tool_b")],
        state,
        include_surfaced_requests=False,
        _mutation=mutation,
    )
    _expect_equal(len(state.surfaced_approval_requests), 2, "two unique approval IDs recorded")
    _expect_equal(state.saved_snapshots, 1, "state saved once")


def test_09_adk_vmaas_deadline_exceeded_in_message_returns_timed_out_once(
    mutation: Optional[str] = None,
) -> None:
    steps = [
        (
            "STATE_RUNNING",
            hc.SandboxAPIError(400, "FAILED_PRECONDITION", "Command killed: DEADLINE_EXCEEDED after 30s"),
        ),
        ("STATE_RUNNING", "should-never-run-second-time"),
    ]
    res = hc.execute_vmaas_sandbox_command(steps, _mutation=mutation)
    _expect_true(res.timed_out, "DEADLINE_EXCEEDED in message must be classified as timeout")
    _expect_equal(res.exit_code, -1, "timeout exit_code must be -1")
    _expect_equal(res.attempts, 1, "timed out command must never be executed a second time")


def test_10_adk_vmaas_running_failed_precondition_raises_without_retry(
    mutation: Optional[str] = None,
) -> None:
    steps = [
        ("STATE_RUNNING", hc.SandboxAPIError(400, "FAILED_PRECONDITION", "non-timeout precondition failure")),
        ("STATE_RUNNING", "unsafe-second-execution"),
    ]
    _expect_raises(
        hc.SandboxAPIError,
        lambda: hc.execute_vmaas_sandbox_command(steps, _mutation=mutation),
        "FAILED_PRECONDITION on STATE_RUNNING sandbox must re-raise without retry",
    )


def test_11_adk_vmaas_paused_resumes_once_and_unreachable_retries_safely(
    mutation: Optional[str] = None,
) -> None:
    steps = [
        ("STATE_PAUSED", hc.SandboxAPIError(400, "FAILED_PRECONDITION", "Sandbox is paused")),
        ("STATE_STARTING", hc.SandboxAPIError(503, "UNAVAILABLE", "Unable to reach the sandbox environment")),
        ("STATE_RUNNING", "ok-after-resume"),
    ]
    res = hc.execute_vmaas_sandbox_command(steps, _mutation=mutation)
    _expect_equal(res.exit_code, 0, "paused then unreachable sandbox should succeed once running")
    _expect_equal(res.stdout, "ok-after-resume", "expected stdout from third attempt")
    _expect_equal(res.resume_calls, 1, "wait_until_running called exactly once")
    _expect_equal(res.attempts, 3, "three delivery attempts total (only last reached shell)")


def test_12_mcp_sep2640_uri_containment_and_linear_slash_trim(mutation: Optional[str] = None) -> None:
    long_slashes = "skill://acme/billing" + ("/" * 5000)
    _expect_equal(
        hc.trim_trailing_slashes_linear(long_slashes),
        "skill://acme/billing",
        "linear trailing-slash trimmer must strip 5000 slashes",
    )
    _expect_true(
        hc.is_within_skill_root("skill://acme/billing", "skill://acme/billing/references/GUIDE.md"),
        "valid child URI must be within root",
    )
    for bad in [
        "skill://acme/billing/../secret.md",
        "skill://acme/billing/%2e%2e/secret.md",
        "skill://acme/billing/sub/%2fetc/passwd",
        "skill://acme/billing/sub/file%00.md",
        "skill://other/billing/SKILL.md",
    ]:
        _expect_equal(
            hc.is_within_skill_root("skill://acme/billing", bad),
            False,
            f"escaped URI {bad!r} must be rejected by is_within_skill_root",
        )


def test_13_mcp_sep2640_rejects_unlisted_size_digest_and_frontmatter_mismatch(
    mutation: Optional[str] = None,
) -> None:
    body = b"---\nname: refunds\n---\n# Refunds\n"
    digest = hashlib.sha256(body).hexdigest()
    entry = {
        "uri": "skill://acme/refunds/SKILL.md",
        "frontmatter": {"name": "refunds", "tier": "gold"},
        "resources": [
            {"uri": "skill://acme/refunds/SKILL.md", "size": len(body), "digest": digest},
        ],
    }
    # 1. Unlisted reference rejected before fetch
    _expect_raises(
        hc.SkillVerificationError,
        lambda: hc.verify_and_read_sep2640_skill_file(
            entry,
            "references/UNLISTED.md",
            lambda _u, _m: (b"x", None, False),
            _mutation=mutation,
        ),
        "unlisted file must raise SkillVerificationError('unlisted')",
    )
    # 2. Frontmatter mismatch rejected even when size and SHA-256 match
    err = _expect_raises(
        hc.SkillVerificationError,
        lambda: hc.verify_and_read_sep2640_skill_file(
            entry,
            "SKILL.md",
            lambda _u, _m: (body, {"name": "refunds", "tier": "tampered"}, False),
            _mutation=mutation,
        ),
        "frontmatter spoofing must raise SkillVerificationError('frontmatter')",
    )
    if isinstance(err, hc.SkillVerificationError):
        _expect_equal(err.check, "frontmatter", "error check must be 'frontmatter'")


def test_14_mcp_sep2640_stale_cache_refreshes_once_and_verifies(mutation: Optional[str] = None) -> None:
    good_bytes = b"---\nname: refunds\n---\n# Clean\n"
    good_digest = hashlib.sha256(good_bytes).hexdigest()
    entry = {
        "uri": "skill://acme/refunds/SKILL.md",
        "frontmatter": {"name": "refunds"},
        "resources": [
            {"uri": "skill://acme/refunds/SKILL.md", "size": len(good_bytes), "digest": good_digest},
        ],
    }
    modes_seen: List[str] = []

    def fake_fetch(_uri: str, mode: str) -> Tuple[bytes, Optional[Dict[str, Any]], bool]:
        modes_seen.append(mode)
        if mode == "default":
            return (b"corrupted-cached-bytes", {"name": "refunds"}, True)
        return (good_bytes, {"name": "refunds"}, False)

    out = hc.verify_and_read_sep2640_skill_file(entry, "SKILL.md", fake_fetch, _mutation=mutation)
    _expect_equal(modes_seen, ["default", "refresh"], "corrupted cached entry must trigger one cacheMode=refresh")
    _expect_true(out["verified"], "refreshed entry must be marked verified=True")


def test_15_codex_frozen_cloud_skill_snapshot_validation_and_authority_isolation(
    mutation: Optional[str] = None,
) -> None:
    valid_payload = json.dumps(
        {
            "skills": [
                {
                    "package": "skill://demo/work",
                    "name": "demo:work",
                    "description": "Do work.",
                    "alias_root": "skill://demo",
                    "main_resource": "skill://demo/work/SKILL.md",
                    "prompt_visible": False,
                    "resources": {
                        "skill://demo/work/SKILL.md": "# Work\n",
                    },
                }
            ]
        }
    ).encode("utf-8")
    snap = hc.FrozenCloudSkillSnapshot(valid_payload, _mutation=mutation)
    _expect_equal(snap.list_skills(include_cloud_skills=False), [], "include_cloud_skills=False returns empty")
    entries = snap.list_skills(include_cloud_skills=True)
    _expect_equal(len(entries), 1, "one frozen cloud skill listed")
    _expect_equal(entries[0]["prompt_visible"], False, "prompt_visible=False preserved")
    _expect_equal(
        snap.read_resource(("Cloud", "codex_apps"), "skill://demo/work", "skill://demo/work/SKILL.md"),
        "# Work\n",
        "hidden skill remains readable under Cloud/codex_apps authority",
    )
    # Wrong authority must be rejected
    _expect_raises(
        PermissionError,
        lambda: snap.read_resource(("executor", "demo"), "skill://demo/work", "skill://demo/work/SKILL.md"),
        "non-cloud authority must be rejected",
    )
    # Cross-package resource injection in snapshot must be rejected at startup
    escaped_payload = json.dumps(
        {
            "skills": [
                {
                    "package": "skill://demo/work",
                    "name": "demo:work",
                    "description": "Do work.",
                    "alias_root": "skill://demo",
                    "main_resource": "skill://demo/work/SKILL.md",
                    "resources": {
                        "skill://demo/work/SKILL.md": "# Work\n",
                        "skill://other/secret.md": "stolen",
                    },
                }
            ]
        }
    ).encode("utf-8")
    _expect_raises(
        ValueError,
        lambda: hc.FrozenCloudSkillSnapshot(escaped_payload, _mutation=mutation),
        "cross-package resource in frozen snapshot must fail startup validation",
    )


def test_16_codex_auth_generation_fences_stale_reload_and_cross_login_refresh(
    mutation: Optional[str] = None,
) -> None:
    mgr = hc.CodexAuthManagerModel()
    # Empty cache logout still advances generation and blocks in-flight reload captured before logout
    gen_before = mgr.generation
    mgr.logout()
    _expect_equal(
        mgr.publish_reloaded_auth(gen_before, "user-a", "rt-a", "at-a"),
        False,
        "stale reload across logout on empty cache must be rejected",
    )
    # Valid reload at current generation succeeds
    _expect_true(
        mgr.publish_reloaded_auth(mgr.generation, "user-a", "rt-a", "at-a"),
        "reload matching current generation must succeed",
    )
    # In-flight refresh for user-a must fail if user-b logged in meanwhile
    mgr.publish_reloaded_auth(mgr.generation, "user-b", "rt-b", "at-b")
    _expect_equal(
        mgr.persist_refreshed_tokens(
            expected_login_owner_id="user-a",
            expected_refresh_token="rt-a",
            new_access_token="at-a-new",
            new_refresh_token="rt-a-new",
        ),
        False,
        "in-flight refresh from previous login must not overwrite new login",
    )
    _expect_equal(mgr.cached_login_owner_id, "user-b", "stored login must remain user-b")

    # Legacy client dropped login_owner_id (None), but refresh_token still matches -> allowed
    mgr.cached_login_owner_id = None
    _expect_true(
        mgr.persist_refreshed_tokens(
            expected_login_owner_id="user-b",
            expected_refresh_token="rt-b",
            new_access_token="at-b-2",
            new_refresh_token="rt-b-2",
        ),
        "legacy metadata drop with matching refresh_token must be allowed",
    )


def test_17_claude_2_1_304_person_decider_blocks_headless_and_auto_classifier(
    mutation: Optional[str] = None,
) -> None:
    # Headless / scheduled session where nobody can be asked -> refused with mod's reason even if auto mode approves
    headless = hc.evaluate_claude_2_1_304_person_decider_and_env(
        mod_decision="ask",
        mod_decider="person",
        mod_reason="requires human security sign-off",
        interactive_dialog_available=False,
        host_callback_available=False,
        auto_mode_classifier_approves=True,
        candidate_env_var="CLAUDE_CODE_DISABLE_CLAUDE_MDS",
        _mutation=mutation,
    )
    _expect_equal(
        headless["final_decision"],
        "deny",
        "decider='person' must refuse when neither dialog nor host callback is available, ignoring auto classifier",
    )
    _expect_equal(headless["reason"], "requires human security sign-off", "refusal must preserve mod reason")
    _expect_true(headless["env_blocked"], "CLAUDE_CODE_DISABLE_CLAUDE_MDS must be flagged as blocked env var")

    # Host callback available -> routed to human/host callback
    with_cb = hc.evaluate_claude_2_1_304_person_decider_and_env(
        mod_decision="ask",
        mod_decider="person",
        mod_reason="requires human security sign-off",
        interactive_dialog_available=False,
        host_callback_available=True,
        auto_mode_classifier_approves=False,
        _mutation=mutation,
    )
    _expect_equal(with_cb["final_decision"], "ask_human_or_host_callback", "host callback satisfies person decider")


def test_18_cookbook_l2_standalone_recorded_traces_5_of_5(mutation: Optional[str] = None) -> None:
    data = json.loads(TRACES_PATH.read_text(encoding="utf-8"))
    cases = data["traces"]["l2_standalone"]
    _expect_equal(len(cases), 5, "l2_standalone must have 5 cases")
    for c in cases:
        res = hc.grade_recorded_trace_case(c, _mutation=mutation)
        _expect_equal(res["pass"], True, f"L2 {c['case_id']} must pass")
        _expect_equal(res["score"], 1.0, f"L2 {c['case_id']} score must be 1.0")
        _expect_equal(res["pass"], c["recorded_pass"], f"L2 {c['case_id']} must match recorded pass")


def test_19_cookbook_l3_codex_before_instructions_cases_1_to_3_pass(mutation: Optional[str] = None) -> None:
    data = json.loads(TRACES_PATH.read_text(encoding="utf-8"))
    cases = data["traces"]["l3_codex_before_instructions"][:3]
    for c in cases:
        res = hc.grade_recorded_trace_case(c, _mutation=mutation)
        _expect_equal(res["pass"], True, f"L3-before {c['case_id']} must pass")
        _expect_equal(res["score"], 1.0, f"L3-before {c['case_id']} score must be 1.0")


def test_20_cookbook_l3_codex_before_case_4_cpi_fails_on_unexpected_series(
    mutation: Optional[str] = None,
) -> None:
    data = json.loads(TRACES_PATH.read_text(encoding="utf-8"))
    case4 = data["traces"]["l3_codex_before_instructions"][3]
    res = hc.grade_recorded_trace_case(case4, _mutation=mutation)
    _expect_equal(res["pass"], False, "L3-before case_4 (CPI) must fail due to unexpected series CUUR0000SA0")
    _expect_equal(res["score"], 0.0, "L3-before case_4 score must be 0.0")
    _expect_true(
        "fetched series outside the expectation: ['CUUR0000SA0']" in res["reason"],
        "L3-before case_4 reason must report unexpected series CUUR0000SA0",
    )


def test_21_cookbook_l3_codex_before_case_5_employment_fails_on_unexpected_series(
    mutation: Optional[str] = None,
) -> None:
    data = json.loads(TRACES_PATH.read_text(encoding="utf-8"))
    case5 = data["traces"]["l3_codex_before_instructions"][4]
    res = hc.grade_recorded_trace_case(case5, _mutation=mutation)
    _expect_equal(
        res["pass"],
        False,
        "L3-before case_5 (employment) must fail when model fetches top candidates without clarification",
    )
    _expect_true(
        "fetched series outside the expectation: ['CES0000000001', 'LNS12000000']" in res["reason"],
        "L3-before case_5 reason must report unexpected series ['CES0000000001', 'LNS12000000']",
    )


def test_22_cookbook_l3_codex_after_mcp_instructions_5_of_5_pass(mutation: Optional[str] = None) -> None:
    data = json.loads(TRACES_PATH.read_text(encoding="utf-8"))
    cases = data["traces"]["l3_codex_after_instructions"]
    _expect_equal(len(cases), 5, "l3_codex_after_instructions must have 5 cases")
    for c in cases:
        res = hc.grade_recorded_trace_case(c, _mutation=mutation)
        _expect_equal(res["pass"], True, f"L3-after {c['case_id']} must pass after MCP instructions")
        _expect_equal(res["score"], 1.0, f"L3-after {c['case_id']} score must be 1.0")
        _expect_equal(res["pass"], c["recorded_pass"], f"L3-after {c['case_id']} must match recorded pass")


def test_23_cookbook_codex_grader_fails_closed_on_mcp_error_or_corrupt_raw(
    mutation: Optional[str] = None,
) -> None:
    corrupt_case = {
        "mode": "codex",
        "vars": {"expected_tools": "resolve", "expected_series_ids": ""},
        "output": "some answer",
        "providerResponse": {"raw": "{not-valid-json"},
    }
    res1 = hc.grade_recorded_trace_case(corrupt_case, _mutation=mutation)
    _expect_equal(res1["pass"], False, "corrupt raw trace must fail closed")
    _expect_equal(res1["reason"], "could not read the Codex item trace", "corrupt raw reason mismatch")

    failed_mcp_case = {
        "mode": "codex",
        "vars": {"expected_tools": "resolve", "expected_series_ids": ""},
        "output": "some answer",
        "providerResponse": {
            "raw": {
                "items": [{"type": "mcp_tool_call", "tool": "resolve", "status": "failed", "error": "timeout"}],
                "finalResponse": "some answer",
            }
        },
    }
    res2 = hc.grade_recorded_trace_case(failed_mcp_case, _mutation=mutation)
    _expect_equal(res2["pass"], False, "failed MCP tool call must fail closed")
    _expect_equal(res2["reason"], "MCP tool call failed: resolve", "failed MCP reason mismatch")


def test_24_provenance_and_recorded_trace_fixtures_integrity(mutation: Optional[str] = None) -> None:
    prov = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    _expect_equal(prov.get("schema_version"), 1, "provenance schema_version must be 1")
    sources = prov.get("sources", [])
    _expect_equal(len(sources), 9, "provenance must bind 9 primary sources")
    for s in sources:
        _expect_equal(s.get("http_status"), 200, f"source {s.get('source_id')} must have HTTP 200")
        _expect_equal(len(str(s.get("revision", ""))), 40, f"source {s.get('source_id')} must have 40-char SHA")
        _expect_equal(len(str(s.get("captured_sha256", ""))), 64, f"source {s.get('source_id')} must have SHA-256")


ALL_TESTS: List[Tuple[str, Callable[[Optional[str]], None]]] = [
    ("test_01_copilot_limit_to_rejects_scheme_port_path_and_query", test_01_copilot_limit_to_rejects_scheme_port_path_and_query),
    ("test_02_copilot_limit_to_intersection_and_empty_vs_null", test_02_copilot_limit_to_intersection_and_empty_vs_null),
    ("test_03_copilot_pre_mcp_sandbox_create_and_managed_conflict", test_03_copilot_pre_mcp_sandbox_create_and_managed_conflict),
    ("test_04_copilot_cold_vs_resident_resume_and_idempotent_update", test_04_copilot_cold_vs_resident_resume_and_idempotent_update),
    ("test_05_maf_dotnet_scoped_vs_singleton_agent_lifetime", test_05_maf_dotnet_scoped_vs_singleton_agent_lifetime),
    ("test_06_maf_dotnet_request_selector_404_skips_store_and_blank_name_rejected", test_06_maf_dotnet_request_selector_404_skips_store_and_blank_name_rejected),
    ("test_07_maf_dotnet_duplicate_approval_id_purges_state_and_saves", test_07_maf_dotnet_duplicate_approval_id_purges_state_and_saves),
    ("test_08_maf_dotnet_unique_approval_ids_recorded_cleanly", test_08_maf_dotnet_unique_approval_ids_recorded_cleanly),
    ("test_09_adk_vmaas_deadline_exceeded_in_message_returns_timed_out_once", test_09_adk_vmaas_deadline_exceeded_in_message_returns_timed_out_once),
    ("test_10_adk_vmaas_running_failed_precondition_raises_without_retry", test_10_adk_vmaas_running_failed_precondition_raises_without_retry),
    ("test_11_adk_vmaas_paused_resumes_once_and_unreachable_retries_safely", test_11_adk_vmaas_paused_resumes_once_and_unreachable_retries_safely),
    ("test_12_mcp_sep2640_uri_containment_and_linear_slash_trim", test_12_mcp_sep2640_uri_containment_and_linear_slash_trim),
    ("test_13_mcp_sep2640_rejects_unlisted_size_digest_and_frontmatter_mismatch", test_13_mcp_sep2640_rejects_unlisted_size_digest_and_frontmatter_mismatch),
    ("test_14_mcp_sep2640_stale_cache_refreshes_once_and_verifies", test_14_mcp_sep2640_stale_cache_refreshes_once_and_verifies),
    ("test_15_codex_frozen_cloud_skill_snapshot_validation_and_authority_isolation", test_15_codex_frozen_cloud_skill_snapshot_validation_and_authority_isolation),
    ("test_16_codex_auth_generation_fences_stale_reload_and_cross_login_refresh", test_16_codex_auth_generation_fences_stale_reload_and_cross_login_refresh),
    ("test_17_claude_2_1_304_person_decider_blocks_headless_and_auto_classifier", test_17_claude_2_1_304_person_decider_blocks_headless_and_auto_classifier),
    ("test_18_cookbook_l2_standalone_recorded_traces_5_of_5", test_18_cookbook_l2_standalone_recorded_traces_5_of_5),
    ("test_19_cookbook_l3_codex_before_instructions_cases_1_to_3_pass", test_19_cookbook_l3_codex_before_instructions_cases_1_to_3_pass),
    ("test_20_cookbook_l3_codex_before_case_4_cpi_fails_on_unexpected_series", test_20_cookbook_l3_codex_before_case_4_cpi_fails_on_unexpected_series),
    ("test_21_cookbook_l3_codex_before_case_5_employment_fails_on_unexpected_series", test_21_cookbook_l3_codex_before_case_5_employment_fails_on_unexpected_series),
    ("test_22_cookbook_l3_codex_after_mcp_instructions_5_of_5_pass", test_22_cookbook_l3_codex_after_mcp_instructions_5_of_5_pass),
    ("test_23_cookbook_codex_grader_fails_closed_on_mcp_error_or_corrupt_raw", test_23_cookbook_codex_grader_fails_closed_on_mcp_error_or_corrupt_raw),
    ("test_24_provenance_and_recorded_trace_fixtures_integrity", test_24_provenance_and_recorded_trace_fixtures_integrity),
]

MUTATIONS: List[Tuple[str, str]] = [
    ("M1_copilot_empty_limit_to_allows_all", "evaluate_copilot_limit_to"),
    ("M2_maf_duplicate_approval_skips_state_purge", "ensure_approval_request_ids_unique"),
    ("M3_adk_vmaas_retries_running_failed_precondition", "execute_vmaas_sandbox_command"),
    ("M4_mcp_skills_skip_frontmatter_diff", "verify_and_read_sep2640_skill_file"),
    ("M5_codex_frozen_skill_allows_cross_package_resource", "FrozenCloudSkillSnapshot"),
    ("M6_cookbook_grader_ignores_unexpected_series", "grade_cookbook_normalized_calls"),
    ("M7_claude_person_decider_allows_auto_classifier", "evaluate_claude_2_1_304_person_decider_and_env"),
]


def run_suite() -> Dict[str, Any]:
    passed = 0
    for name, fn in ALL_TESTS:
        fn(None)
        passed += 1

    mutation_records: List[Dict[str, Any]] = []
    killed = 0
    for mut_id, target in MUTATIONS:
        failed_tests: List[str] = []
        for t_name, fn in ALL_TESTS:
            try:
                fn(mut_id)
            except BusinessOracleFailure:
                failed_tests.append(t_name)
        status = "KILLED" if failed_tests else "SURVIVED"
        if status != "KILLED":
            raise BusinessOracleFailure(f"Mutation {mut_id} SURVIVED!")
        killed += 1
        mutation_records.append(
            {
                "mutation_id": mut_id,
                "target": target,
                "status": status,
                "failed_test_count": len(failed_tests),
                "failed_tests": failed_tests,
            }
        )

    return {
        "tests_run": len(ALL_TESTS),
        "tests_passed": passed,
        "mutations_total": len(MUTATIONS),
        "mutations_killed": killed,
        "mutations": mutation_records,
    }


if __name__ == "__main__":
    summary = run_suite()
    print(json.dumps(summary, indent=2))
    sys.exit(0)
