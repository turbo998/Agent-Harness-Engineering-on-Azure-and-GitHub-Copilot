#!/usr/bin/env python3
"""Offline reference contracts for 2026-10-19 agent harness acceptance gates.

Pure Python 3.11+ standard-library reference models derived from static source
reading of six upstream mechanisms:
  1. MAF Python AG-UI explicit authorization scope & approval-state shape guard
     (microsoft/agent-framework@9a1d66b3e973bdbfdcd4359d72c5f6fd4ff4d931 &
      abeed6c62a8cc70e796334a5b490c8e94621f89d)
  2. Azure MCP Server 3.0.0 GA ambient command-context SSRF policy & proxy split
     (microsoft/mcp@da75e4d390cd8be7e77119dfd4d6c0e47188eeb9)
  3. MAF .NET unanswered tool-approval next-run auto-reject & workflow holdback
     (microsoft/agent-framework@95feea605dbbe879f678602585c76fdb5a963b63)
  4. Google ADK workflow dynamic-child retry counter rewind & loop JoinNode barrier
     (google/adk-python@e2dbc0f55027372f3a701d41004ee006ee8f9f14 &
      a6ed85905d4c1d1f285ba9d4f76a9d801b66d17f)
  5. OpenAI Codex idle root wakeup gate & Cookbook harness-aware MCP trace grader
     (openai/codex@8c076942cb70fba8e5c4732c23f1faabc4aed484 &
      openai/openai-cookbook@5bd6cb40b6b84b69b2032d810610aa85064102df)
  6. Anthropic Claude Code sec-default two-pass verdict hold & pinned env guard
     (anthropics/claude-code@dd6bee38458cc3e6dc5f2b16eca1f0f364619ad8)

Boundary note: This module is an original stdlib specification and mutation-test
target. Executing it exercises the reference model only and does NOT execute
upstream MAF, Azure MCP, Google ADK, OpenAI Codex, or Claude Code packages/hosts.
"""
from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

TOOL_APPROVAL_STATE_FIELDS: tuple[str, ...] = (
    "rules",
    "queued_approval_requests",
    "collected_approval_responses",
)

PINNED_POLICY_AND_CODE_VARS: frozenset[str] = frozenset(
    {
        "CLAUDE_CODE_MANAGED_SETTINGS_PATH",
        "CLAUDE_CODE_REMOTE_SETTINGS_PATH",
        "CLAUDE_CODE_MOCK_REMOTE_SETTINGS",
        "CLAUDE_CODE_DISABLE_ADMIN_ENV_UNION",
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_SECURESTORAGE_CONFIG_DIR",
        "USE_LOCAL_OAUTH",
        "USE_STAGING_OAUTH",
        "CLAUDE_LOCAL_OAUTH_API_BASE",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "LD_AUDIT",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "DYLD_FRAMEWORK_PATH",
        "BASH_ENV",
        "ENV",
        "ZDOTDIR",
        "NODE_OPTIONS",
    }
)


# ---------------------------------------------------------------------------
# 1. MAF Python AG-UI authorization scope & client Shared State shape guard
# ---------------------------------------------------------------------------

def validate_agui_scope_config(
    *,
    authorization_scope_resolver: Callable[[], Any] | None = None,
    snapshot_scope_resolver: Callable[[], Any] | None = None,
    single_user: Any = False,
) -> str:
    """Validate mutually exclusive AG-UI endpoint authorization configuration."""
    if not isinstance(single_user, bool):
        raise TypeError("single_user must be a bool.")
    configured_modes = sum(
        (
            authorization_scope_resolver is not None,
            snapshot_scope_resolver is not None,
            single_user,
        )
    )
    if configured_modes == 0:
        raise ValueError("AG-UI endpoint authorization must be explicit.")
    if configured_modes > 1:
        raise ValueError("Configure exactly one AG-UI authorization mode.")
    if authorization_scope_resolver is not None:
        return "authorization_scope_resolver"
    if snapshot_scope_resolver is not None:
        return "snapshot_scope_resolver"
    return "single_user"


def resolve_agui_request_scope(
    *,
    authorization_scope_resolver: Callable[[], Any] | None = None,
    snapshot_scope_resolver: Callable[[], Any] | None = None,
    single_user: bool = False,
    registration_scope_id: str = "ag-ui:single-user:fixed",
) -> str:
    """Resolve per-request AG-UI scope without falling back on resolver failure."""
    mode = validate_agui_scope_config(
        authorization_scope_resolver=authorization_scope_resolver,
        snapshot_scope_resolver=snapshot_scope_resolver,
        single_user=single_user,
    )
    if mode == "authorization_scope_resolver":
        if authorization_scope_resolver is None:
            raise RuntimeError("authorization_scope_resolver missing after validation.")
        resolved = authorization_scope_resolver()
        if not isinstance(resolved, str) or not resolved:
            raise RuntimeError("HTTP_500: authorization_scope_resolver must return a non-empty string.")
        return resolved
    if mode == "snapshot_scope_resolver":
        if snapshot_scope_resolver is None:
            raise RuntimeError("snapshot_scope_resolver missing after validation.")
        resolved = snapshot_scope_resolver()
        if not isinstance(resolved, str) or not resolved:
            raise ValueError("snapshot_scope_resolver must return a non-empty string.")
        return resolved
    return registration_scope_id


@dataclass(frozen=True)
class ToolApprovalStateMarker:
    rules: tuple[str, ...] = ()


def carries_tool_approval_authority(value: Any) -> bool:
    """Detect client Shared State values carrying non-empty approval lists by shape."""
    if not isinstance(value, Mapping):
        return False
    return any(
        isinstance(value.get(field_name), list) and bool(value[field_name])
        for field_name in TOOL_APPROVAL_STATE_FIELDS
    )


def server_tool_approval_state_keys(session_state: Mapping[str, Any]) -> set[str]:
    """Identify server session keys already holding tool-approval state."""
    protected: set[str] = set()
    for key, value in session_state.items():
        if isinstance(value, ToolApprovalStateMarker):
            protected.add(key)
        elif isinstance(value, Mapping) and any(
            field_name in value for field_name in TOOL_APPROVAL_STATE_FIELDS
        ):
            protected.add(key)
    return protected


def merge_agui_shared_state(
    *,
    server_session_state: Mapping[str, Any],
    client_shared_state: Mapping[str, Any],
    named_protected_keys: Iterable[str] = (),
) -> tuple[dict[str, Any], set[str]]:
    """Merge client Shared State into server session state while blocking approval authority."""
    named_set = set(named_protected_keys)
    server_keys = server_tool_approval_state_keys(server_session_state)
    authority_keys = {
        key
        for key, value in client_shared_state.items()
        if carries_tool_approval_authority(value)
    }
    protected_keys = named_set | server_keys | authority_keys
    merged = copy.deepcopy(dict(server_session_state))
    for key, value in client_shared_state.items():
        if key not in protected_keys:
            merged[key] = copy.deepcopy(value)
    ignored_authority_keys = authority_keys - named_set
    return merged, ignored_authority_keys


# ---------------------------------------------------------------------------
# 2. Azure MCP Server ambient CommandContextAccessor & SSRF policy/transport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandContext:
    tool_namespace_name: str | None


class _CommandContextHolder:
    def __init__(self, context: CommandContext) -> None:
        self._context: CommandContext | None = context

    @property
    def context(self) -> CommandContext | None:
        return self._context

    def clear(self) -> None:
        self._context = None


class CommandContextAccessor:
    """Ambient command context accessor that clears holder on scope exit."""

    def __init__(self) -> None:
        self._holder: _CommandContextHolder | None = None

    @property
    def current_context(self) -> CommandContext | None:
        return None if self._holder is None else self._holder.context

    def capture_floating_reader(self) -> Callable[[], CommandContext | None]:
        """Simulate a background task that captured the holder reference during scope."""
        captured_holder = self._holder
        return lambda: None if captured_holder is None else captured_holder.context

    def begin_scope(self, context: CommandContext) -> Callable[[], None]:
        if context is None:
            raise ValueError("context must not be None")
        if self.current_context is not None:
            raise RuntimeError("InvalidOperationException: CommandContext scope cannot be nested.")
        holder = _CommandContextHolder(context)
        self._holder = holder
        disposed = False

        def dispose() -> None:
            nonlocal disposed
            if disposed:
                return
            disposed = True
            holder.clear()
            if self._holder is holder:
                self._holder = None

        return dispose


class SsrfProtectionPolicy:
    """Host-owned immutable emergency namespace override policy."""

    ALL_NAMESPACES = "ALL"

    def __init__(self, dangerously_disabled_namespaces: Iterable[str] | None = None) -> None:
        raw = dangerously_disabled_namespaces or ()
        # Values are matched case-insensitively without trimming (" ALL " != "ALL").
        self._disabled_lower: frozenset[str] = frozenset(
            item.lower()
            for item in raw
            if isinstance(item, str) and not item.isspace() and item != ""
        )

    def are_ssrf_protections_enabled(self, accessor: CommandContextAccessor) -> bool:
        if accessor is None:
            raise ValueError("accessor is required")
        ctx = accessor.current_context
        namespace = None if ctx is None else ctx.tool_namespace_name
        if namespace is None or not isinstance(namespace, str) or namespace.strip() == "":
            return True
        ns_lower = namespace.lower()
        return (
            self.ALL_NAMESPACES.lower() not in self._disabled_lower
            and ns_lower not in self._disabled_lower
        )


def select_mcp_http_transport(
    *,
    request_uri: str,
    proxy_uri: str | None,
    policy: SsrfProtectionPolicy,
    accessor: CommandContextAccessor,
    endpoint_valid: bool,
) -> str:
    """Select HTTP transport pool after mandatory endpoint validation."""
    if not endpoint_valid:
        raise PermissionError("SecurityException: Endpoint rejected by allowlist before transport.")
    if proxy_uri is not None and proxy_uri != "" and proxy_uri != request_uri:
        return "proxied_transport"
    if policy.are_ssrf_protections_enabled(accessor):
        return "protected_anti_ssrf_transport"
    return "unprotected_override_transport"


# ---------------------------------------------------------------------------
# 3. MAF .NET unanswered tool approvals next-run auto-reject & workflow hold
# ---------------------------------------------------------------------------

@dataclass
class FunctionCallObj:
    call_id: str
    name: str
    informational_only: bool = False


def bind_or_auto_reject_approvals(
    *,
    saved_pending_requests: Mapping[str, FunctionCallObj],
    supplied_decisions: Mapping[str, bool],
    settled_call_ids: Iterable[str] = (),
    inner_call_succeeds: bool = True,
) -> dict[str, Any]:
    """Bind supplied approval answers, auto-reject remaining unanswered, and preserve retry on failure."""
    settled = set(settled_call_ids)
    generated_rejections: list[tuple[str, bool, bool]] = []
    ficc_decisions: list[tuple[str, bool, bool]] = []

    for call_id, req_call in saved_pending_requests.items():
        if call_id in settled:
            continue
        if call_id in supplied_decisions:
            approved = bool(supplied_decisions[call_id])
            ficc_copy = FunctionCallObj(req_call.call_id, req_call.name, informational_only=False)
            # FICC mutates its processed copy to InformationalOnly=True
            ficc_copy.informational_only = True
            ficc_decisions.append((call_id, approved, ficc_copy.informational_only))
        else:
            # Snapshot request for caller-visible generated rejection AND separate copy for FICC
            caller_copy = FunctionCallObj(req_call.call_id, req_call.name, informational_only=False)
            ficc_copy = FunctionCallObj(req_call.call_id, req_call.name, informational_only=False)
            ficc_copy.informational_only = True
            generated_rejections.append((call_id, False, caller_copy.informational_only))
            ficc_decisions.append((call_id, False, ficc_copy.informational_only))

    if inner_call_succeeds:
        remaining_pending = {}
    else:
        remaining_pending = {
            cid: FunctionCallObj(call.call_id, call.name, call.informational_only)
            for cid, call in saved_pending_requests.items()
        }

    return {
        "generated_rejections": generated_rejections,
        "ficc_decisions": ficc_decisions,
        "remaining_pending": remaining_pending,
        "original_mutated": any(c.informational_only for c in saved_pending_requests.values()),
    }


def build_workflow_forwarded_approval(
    *,
    call_id: str,
    completed_calls: Mapping[str, str],
    completed_results: Mapping[str, str],
    approved: bool,
) -> dict[str, Any]:
    """Require both completed call and matching result before forwarding approval in a workflow."""
    if call_id not in completed_calls or call_id not in completed_results:
        raise RuntimeError(
            "InvalidOperationException: Completed function call and result are both required."
        )
    return {
        "call_id": call_id,
        "tool_name": completed_calls[call_id],
        "approved": approved,
        "has_result": True,
    }


# ---------------------------------------------------------------------------
# 4. Google ADK dynamic child retry counter rewind & loop JoinNode barrier
# ---------------------------------------------------------------------------

class DynamicCounterScheduler:
    """Track sequential dynamic child run counters with attempt-start snapshot rewind."""

    def __init__(self) -> None:
        self.run_counters: dict[str, dict[str, int]] = {}

    def _counter_paths_under(self, parent_path: str) -> list[str]:
        prefix = f"{parent_path}/" if parent_path else ""
        return [
            key
            for key in self.run_counters
            if key == parent_path or (prefix and key.startswith(prefix))
        ]

    def next_run_id(self, node_name: str, parent_path: str) -> str:
        counters = self.run_counters.setdefault(parent_path, {})
        counters[node_name] = counters.get(node_name, 0) + 1
        return f"{node_name}_{counters[node_name]}"

    def snapshot_counters(self, parent_path: str) -> dict[str, dict[str, int]]:
        return {
            path: dict(self.run_counters[path])
            for path in self._counter_paths_under(parent_path)
        }

    def reset_for_retry(
        self,
        parent_path: str,
        snapshot: Mapping[str, Mapping[str, int]],
    ) -> None:
        for path in self._counter_paths_under(parent_path):
            del self.run_counters[path]
        for path, counters in snapshot.items():
            self.run_counters[path] = dict(counters)


@dataclass
class LoopJoinBarrier:
    """Wait-for-all JoinNode barrier in a loop that consumes arrivals on each fire."""

    predecessors: frozenset[str]
    completed_status: dict[str, bool] = field(default_factory=dict)
    node_outputs: dict[str, Any] = field(default_factory=dict)
    arrivals: set[str] = field(default_factory=set)

    def record_completion(self, node_name: str, output: Any) -> dict[str, Any] | None:
        if node_name not in self.predecessors:
            return None
        self.completed_status[node_name] = True
        if output is not None:
            self.node_outputs[node_name] = output
        else:
            self.node_outputs.pop(node_name, None)
        self.arrivals.add(node_name)
        if not all(
            pred in self.arrivals and self.completed_status.get(pred, False)
            for pred in self.predecessors
        ):
            return None
        self.arrivals.clear()
        return {pred: self.node_outputs.get(pred) for pred in sorted(self.predecessors)}


# ---------------------------------------------------------------------------
# 5. OpenAI Codex idle root wakeup gate & Cookbook MCP trace grader
# ---------------------------------------------------------------------------

def should_wake_on_agent_messages(
    *,
    feature_enabled: bool,
    is_interrupted: bool,
    has_pending_mailbox_items: bool,
    is_non_root_agent: bool,
    collaboration_mode: str,
) -> bool:
    """Evaluate whether queue-only agent mail can wake an idle Codex session."""
    if not feature_enabled or is_interrupted or not has_pending_mailbox_items:
        return False
    permits_automatic = collaboration_mode == "default"
    return (not is_non_root_agent) and permits_automatic


def select_woken_turn_options(
    *,
    has_trigger_turn_mail: bool,
    previous_options: str,
    default_options: str = "default_options",
) -> str:
    """Retain previous turn options on queue-only wakes; reset when trigger_turn is set."""
    return default_options if has_trigger_turn_mail else previous_options


def grade_codex_mcp_trace(
    *,
    raw_items: Iterable[Mapping[str, Any]],
    expected_tools: Iterable[str],
    expected_series_ids: Iterable[str],
    final_answer: str,
    provider_error: str | None = None,
) -> dict[str, Any]:
    """Grade normalized MCP tool trace for missing/hallucinated series and failed calls."""
    mcp_items = [item for item in raw_items if item.get("type") == "mcp_tool_call"]
    for item in mcp_items:
        if item.get("error") or item.get("status") == "failed":
            return {
                "pass": False,
                "score": 0.0,
                "reason": f"MCP tool call failed: {item.get('tool')}",
            }

    used_tools = {str(item.get("tool")) for item in mcp_items if item.get("tool")}
    exp_tools = {str(t).strip() for t in expected_tools if str(t).strip()}
    missing_tools = sorted(exp_tools - used_tools)

    fetched_series = {
        str(series_id)
        for item in mcp_items
        if item.get("tool") == "fetch_bls_data"
        for series_id in (item.get("arguments") or {}).get("series_ids", [])
    }
    returned_series = {
        str(record.get("series_id"))
        for item in mcp_items
        if item.get("tool") == "fetch_bls_data"
        for record in (((item.get("result") or {}).get("structured_content") or {}).get("data") or [])
        if isinstance(record, Mapping) and not record.get("error") and record.get("series_id")
    }
    exp_series = {str(s).strip() for s in expected_series_ids if str(s).strip()}
    missing_series = sorted(exp_series - returned_series)
    unexpected_series = sorted(fetched_series - exp_series)

    completed = (not provider_error) and bool(final_answer.strip())
    reasons: list[str] = []
    if not completed:
        reasons.append("run did not finish before the step limit")
    if missing_tools:
        reasons.append(f"missing tools: {missing_tools}")
    if missing_series:
        reasons.append(f"no observations for: {missing_series}")
    if unexpected_series:
        reasons.append(f"fetched series outside the expectation: {unexpected_series}")
    if not final_answer.strip():
        reasons.append("empty final answer")

    return {
        "pass": not reasons,
        "score": 0.0 if reasons else 1.0,
        "reason": "; ".join(reasons) or "expected tools called and BLS series fetched",
    }


# ---------------------------------------------------------------------------
# 6. Anthropic Claude Code sec-default two-pass verdict hold & env pinning
# ---------------------------------------------------------------------------

_DECISION_STRICTNESS: dict[str, int] = {"allow": 0, "ask": 1, "deny": 2}
_HELD_ASK_SOURCES: frozenset[str] = frozenset({"rule", "hook", "setting", "ceiling", "host", "person"})


@dataclass(frozen=True)
class Verdict:
    decision: str
    source: str | None = None
    rule: str | None = None

    def is_held_target(self) -> bool:
        if self.decision == "deny":
            return True
        if self.decision == "ask" and self.source in _HELD_ASK_SOURCES:
            return True
        return False


def evaluate_sec_default_tool_check(
    *,
    full_chain_answer: Verdict,
    append_only_answer: Verdict,
    user_tier_rewrote: bool,
    deny_rules_hold_policy: bool = True,
    policy_read_failed: bool = False,
) -> tuple[Verdict, str | None]:
    """Run sec-default two-pass tool.check verification against user-tier loosening."""
    # Policy reads fail closed: if reading policy fails, denyRulesHold remains in force.
    effective_hold_policy = True if policy_read_failed else deny_rules_hold_policy
    if not user_tier_rewrote or not effective_hold_policy:
        return full_chain_answer, None

    if not append_only_answer.is_held_target():
        return full_chain_answer, None

    full_rank = _DECISION_STRICTNESS.get(full_chain_answer.decision, -1)
    held_rank = _DECISION_STRICTNESS.get(append_only_answer.decision, -1)

    # User tier may tighten (e.g. ask -> deny), which stands without being overridden.
    if full_rank > held_rank:
        return full_chain_answer, None

    if full_rank < held_rank:
        return append_only_answer, "lift"

    if (
        full_chain_answer.source != append_only_answer.source
        or full_chain_answer.rule != append_only_answer.rule
    ):
        return append_only_answer, "reword"

    return full_chain_answer, None


def evaluate_sec_default_env_set(
    *,
    caller_tier: str,
    var_name: str,
    managed_env_keys: Iterable[str] = (),
    has_process_wrapper: bool = False,
    policy_read_failed: bool = False,
) -> str:
    """Enforce sec-default env.set pinning for user-tier callers with fail-closed policy read."""
    if caller_tier in {"prepend", "append"}:
        return "continue_to_append"
    if policy_read_failed:
        return "deny_pinned" if caller_tier == "user" else "continue_to_append"

    upper_name = var_name.upper()
    managed_upper = {k.upper() for k in managed_env_keys}
    pinned_upper = {k.upper() for k in PINNED_POLICY_AND_CODE_VARS}
    is_pinned = (
        upper_name in managed_upper
        or upper_name in pinned_upper
        or (has_process_wrapper and upper_name == "CLAUDE_CODE_PROCESS_WRAPPER")
    )
    if not is_pinned:
        return "pass_chain"
    return "deny_pinned" if caller_tier == "user" else "continue_to_append"
