"""Pure-stdlib reference contracts for the 2026-10-31 Agent Harness Lab.

Covers 6 mechanism groups across Microsoft Agent Framework (.NET 1.27.0 & Python 1.24.0),
GitHub Copilot SDK & Azure MCP Server 4.0.0-beta.4, Google ADK Python/Go,
MCP Go SDK & OpenAI Agents JS, OpenAI Codex rust-v0.166.0 & Cookbook Decisions API,
and Anthropic Claude Code v2.1.312-v2.1.314 + mods/sec-default + infragate/capa.

All runtime checks use explicit conditional raises (`BusinessOracleFailure`,
`ValueError`, `PermissionError`) with zero `assert` statements so behavior is
identical under `python3 -B` and `python3 -B -O`.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class BusinessOracleFailure(RuntimeError):
    """Raised when a contract invariant or test oracle fails."""


# --- Mutation-calibratable module constants ---
MAGENTIC_HEURISTIC_RESTORE_ENABLED: bool = True
COPILOT_AUTOPILOT_REQUIRE_STOP_EVENT: bool = True
ADK_TEMP_STATE_PREFIX: str = "temp:"
OPENAI_SANDBOX_AUTHORITY_FIELDS: frozenset[str] = frozenset({
    "environment",
    "extra_path_grants",
    "remote_mount_command_allowlist",
    "mount_credential_exposure_policy",
})
CODEX_EXCLUDE_ORIGINAL_COMMAND_FROM_STDIN_LIMIT: bool = True
CODEX_MAX_STDIN_APPROVAL_BYTES: int = 8000
CLAUDE_MAX_ACTIVE_HOOKS_PER_SESSION: int = 24
CLAUDE_MAX_TIMEOUT_WAITING_HOOKS: int = 12
CLAUDE_PRECOMPACT_HOOK_OUTPUT_CAP: int = 10000


# ============================================================================
# 1. Microsoft Agent Framework: .NET Magentic Plan Review & Python MCP/Pickle
# ============================================================================

class MagenticPlanReviewStateMachine:
    """Reference contract for `MagenticOrchestrator` plan review state (`5f469d26`)."""

    AWAITING_STATE_KEY = "AwaitingPlanReviewStateKey"

    def __init__(
        self,
        *,
        require_plan_signoff: bool = True,
        has_task_ledger: bool = True,
        is_terminated: bool = False,
        current_speaker_executor_id: str | None = None,
    ) -> None:
        self.require_plan_signoff = require_plan_signoff
        self.has_task_ledger = has_task_ledger
        self.is_terminated = is_terminated
        self.current_speaker_executor_id = current_speaker_executor_id
        self.is_awaiting_plan_review: bool = False
        self.warnings: list[str] = []

    def submit_plan_review_request(self, plan_text: str) -> dict[str, Any]:
        if not plan_text.strip():
            raise ValueError("Plan text must be non-empty")
        self.is_awaiting_plan_review = True
        return {
            "status": "plan_review_requested",
            "awaiting_plan_review": self.is_awaiting_plan_review,
            "plan": plan_text,
        }

    def take_turn(self, message: str) -> dict[str, Any]:
        if self.is_awaiting_plan_review:
            warning = (
                "Magentic Orchestrator is waiting for a plan review response; "
                "this turn was ignored."
            )
            self.warnings.append(warning)
            return {
                "status": "ignored_awaiting_plan_review",
                "warning": warning,
                "message": message,
            }
        return {
            "status": "turn_executed",
            "message": message,
        }

    def handle_plan_review_response(
        self,
        *,
        is_approved: bool,
        revised_plan: str | None = None,
        buffered_ordinary_messages: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.is_awaiting_plan_review:
            raise ValueError(
                "This Magentic orchestration is not waiting for a plan review response."
            )
        drained = list(buffered_ordinary_messages or [])
        if drained:
            self.warnings.append(
                f"{len(drained)} buffered ordinary messages were ignored."
            )
        if is_approved:
            self.is_awaiting_plan_review = False
            return {
                "status": "delegated_to_team",
                "awaiting_plan_review": self.is_awaiting_plan_review,
                "drained_count": len(drained),
            }
        self.is_awaiting_plan_review = True
        return {
            "status": "re_requested_after_revision",
            "awaiting_plan_review": self.is_awaiting_plan_review,
            "revised_plan": revised_plan or "",
            "drained_count": len(drained),
        }

    def checkpoint_state(self) -> dict[str, Any]:
        return {self.AWAITING_STATE_KEY: self.is_awaiting_plan_review}

    @classmethod
    def restore_from_checkpoint(
        cls,
        state: dict[str, Any],
        *,
        require_plan_signoff: bool,
        has_task_ledger: bool,
        is_terminated: bool,
        current_speaker_executor_id: str | None,
    ) -> "MagenticPlanReviewStateMachine":
        instance = cls(
            require_plan_signoff=require_plan_signoff,
            has_task_ledger=has_task_ledger,
            is_terminated=is_terminated,
            current_speaker_executor_id=current_speaker_executor_id,
        )
        saved = state.get(cls.AWAITING_STATE_KEY)
        if isinstance(saved, bool):
            instance.is_awaiting_plan_review = saved
        elif MAGENTIC_HEURISTIC_RESTORE_ENABLED:
            instance.is_awaiting_plan_review = bool(
                require_plan_signoff
                and has_task_ledger
                and not is_terminated
                and current_speaker_executor_id is None
            )
        else:
            instance.is_awaiting_plan_review = False
        return instance


def _normalize_approval_names(names: Any) -> tuple[str, ...]:
    if names is None:
        return ()
    if isinstance(names, str):
        return (names,)
    return tuple(str(n) for n in names)


def evaluate_maf_mcp_approval_and_checkpoint_guard(
    *,
    approval_mode: str | dict[str, Any] | None,
    tool_name: str,
    unpickle_target: str,
    unpickle_args: tuple[Any, ...] = (),
    unpickle_kwargs: dict[str, Any] | None = None,
    is_metaclass_alias: bool = False,
    is_unpopulated_enum: bool = False,
) -> dict[str, Any]:
    """Reference contract for MAF MCP dual approval merge (`2e931679`, `5de71b8a`)
    and checkpoint metaclass/enum guard (`34452c8a`).
    """
    kw = unpickle_kwargs or {}
    if unpickle_target == "builtins:type":
        if len(unpickle_args) != 1 or kw:
            raise PermissionError(
                "3-arg dynamic type() construction is blocked in checkpoint unpickler"
            )
        if isinstance(unpickle_args[0], type):
            raise PermissionError(
                "type(cls) returning raw type metaclass is blocked in checkpoint unpickler"
            )
    if is_metaclass_alias:
        raise PermissionError(
            f"Metaclass target '{unpickle_target}' is blocked in checkpoint unpickler"
        )
    if is_unpopulated_enum:
        raise PermissionError(
            f"Unpopulated Enum constructor '{unpickle_target}' is blocked in checkpoint unpickler"
        )

    foundry_require_approval: str | dict[str, list[str]] | None = None
    local_decision: str | None = None
    emitted_future_warning: bool = False

    if approval_mode in ("always_require", "never_require"):
        foundry_require_approval = (
            "always" if approval_mode == "always_require" else "never"
        )
        local_decision = str(approval_mode)
    elif isinstance(approval_mode, dict):
        always_names = _normalize_approval_names(
            approval_mode.get("always_require_approval")
        )
        never_names = _normalize_approval_names(
            approval_mode.get("never_require_approval")
        )
        default_policy = approval_mode.get("default")
        if default_policy not in (None, "always_require", "never_require"):
            raise ValueError(f"Invalid MCP approval default: {default_policy!r}")

        merged: dict[str, list[str]] = {}
        if always_names:
            merged["always"] = list(always_names)
        if never_names:
            merged["never"] = list(never_names)
        if merged:
            foundry_require_approval = merged

        if never_names and default_policy is None:
            emitted_future_warning = True

        if tool_name in always_names:
            local_decision = "always_require"
        elif tool_name in never_names:
            local_decision = "never_require"
        else:
            local_decision = default_policy

    return {
        "foundry_require_approval": foundry_require_approval,
        "local_decision": local_decision,
        "emitted_future_warning": emitted_future_warning,
        "unpickle_allowed": True,
    }


# ============================================================================
# 2. GitHub Copilot SDK (`15fe4675`, `9bc718cb`) & Azure MCP (`2caca623`, `286a2b8b`)
# ============================================================================

class CopilotStructuredOutputWaiter:
    """Reference contract for Copilot SDK `StructuredOutputState` & Autopilot waiter (`15fe4675`)."""

    def __init__(self, *, mode: str = "interactive") -> None:
        if mode not in ("interactive", "autopilot"):
            raise ValueError(f"Unsupported session mode: {mode}")
        self.mode = mode
        self.admitted: bool = False
        self.message_id: str | None = None
        self.pending_events: list[dict[str, Any]] = []
        self.final_message: str | None = None
        self.pending_tool_requests: list[str] = []
        self.status: str = "pending"
        self.result: str | None = None
        self.error: str | None = None

    def push_event(self, event: dict[str, Any]) -> None:
        if not self.admitted:
            self.pending_events.append(dict(event))
            return
        self._process_event(event)

    def admit_request(self, message_id: str) -> None:
        if not message_id:
            raise ValueError("message_id must be non-empty")
        self.message_id = message_id
        self.admitted = True
        queued = list(self.pending_events)
        self.pending_events.clear()
        for ev in queued:
            if self.status != "pending":
                break
            self._process_event(ev)

    def _complete_structured_output(self) -> None:
        if self.pending_tool_requests:
            self.status = "failed"
            self.error = "run completed with pending tool_requests"
            return
        if self.final_message is None or not self.final_message.strip():
            self.status = "failed"
            self.error = "run completed without a structured assistant response"
            return
        self.status = "completed"
        self.result = self.final_message

    def _process_event(self, event: dict[str, Any]) -> None:
        ev_type = event.get("type")
        if ev_type == "assistant.message":
            self.final_message = str(event.get("content", ""))
            self.pending_tool_requests = list(event.get("tool_requests") or [])
        elif ev_type == "session.error":
            origin = event.get("originating_message_id")
            if origin is None or origin == self.message_id:
                self.status = "failed"
                self.error = str(event.get("message", "Session error"))
        elif ev_type == "session.idle":
            ev_mode = event.get("mode", self.mode)
            if COPILOT_AUTOPILOT_REQUIRE_STOP_EVENT and ev_mode == "autopilot":
                return
            if event.get("aborted") is True:
                self.status = "failed"
                self.error = "Session aborted before structured output completed"
                return
            self._complete_structured_output()
        elif ev_type == "session.autopilot_stopped":
            if event.get("request_id") != self.message_id:
                return
            reason = event.get("reason", "completed")
            if reason == "error":
                self.status = "failed"
                self.error = "Autopilot request failed"
            elif reason == "aborted":
                self.status = "failed"
                self.error = "Session aborted before structured output completed"
            else:
                self._complete_structured_output()


def evaluate_copilot_trusted_display_identity(
    *,
    server_name: str,
    claimed_display_name: str | None,
    trusted_catalog: dict[str, str],
    policy_rule_target: str,
    allow_all_mcp_server_instructions: bool,
    incoming_mcp_instructions: str | None,
) -> dict[str, Any]:
    """Reference contract for Copilot SDK `serverDisplayName` / `elicitationSourceDisplayName` (`9bc718cb`)
    and `allowAllMcpServerInstructions` (`15fe4675`).
    """
    if not server_name.strip():
        raise ValueError("server_name must be non-empty")
    effective_display_name = trusted_catalog.get(server_name)
    policy_matched = (policy_rule_target == server_name)
    injected_instructions = (
        incoming_mcp_instructions
        if (allow_all_mcp_server_instructions and incoming_mcp_instructions)
        else None
    )
    return {
        "identity_key": server_name,
        "claimed_display_name_ignored": claimed_display_name,
        "effective_display_name": effective_display_name,
        "policy_matched": policy_matched,
        "injected_mcp_instructions": injected_instructions,
    }


def validate_azure_mcp_cache_and_kusto_token(
    *,
    pages: list[dict[str, Any]],
    child_loader_ttls_seconds: list[int | None],
    elapsed_seconds: int,
    transport_mode: str,
    token_expires_in_seconds: int,
    request_tenant_id: str,
    cached_tenant_id: str,
) -> dict[str, Any]:
    """Reference contract for Azure MCP `ToolListCache` (`2caca623`) & `KustoClient` (`286a2b8b`)."""
    default_ttl = 3600
    Refresh_buffer = 300

    tools: list[str] = []
    candidate_ttls: list[int] = []
    seen_cursors: set[str] = set()

    for page in pages:
        for tool in page.get("tools", []):
            if tool not in tools:
                tools.append(tool)
        page_ttl = page.get("ttl_seconds")
        if isinstance(page_ttl, int) and page_ttl > 0:
            candidate_ttls.append(page_ttl)
        cursor = page.get("next_cursor")
        if cursor:
            if cursor in seen_cursors:
                raise ValueError(f"Duplicate pagination cursor detected: {cursor}")
            seen_cursors.add(cursor)
        else:
            break

    for loader_ttl in child_loader_ttls_seconds:
        if isinstance(loader_ttl, int) and loader_ttl > 0:
            candidate_ttls.append(loader_ttl)

    effective_ttl = min(candidate_ttls) if candidate_ttls else default_ttl
    cache_valid = elapsed_seconds < effective_ttl

    if transport_mode not in ("stdio", "http"):
        raise ValueError(f"Unsupported transport_mode: {transport_mode}")

    # HTTP mode must never retain/reuse client or token across requests
    kusto_can_reuse_cached_token = bool(
        transport_mode == "stdio"
        and request_tenant_id.lower() == cached_tenant_id.lower()
        and token_expires_in_seconds > Refresh_buffer
    )

    return {
        "aggregated_tools": tools,
        "effective_ttl_seconds": effective_ttl,
        "cache_valid": cache_valid,
        "kusto_can_reuse_cached_token": kusto_can_reuse_cached_token,
    }


# ============================================================================
# 3. Google ADK Python (`968cd869`, `87d9dcdf`, `2cabbddf`) & Go (`beea418c`)
# ============================================================================

ADK_ALLOWED_CREATE_SESSION_KEYS: frozenset[str] = frozenset({
    "display_name",
    "displayName",
    "ttl",
    "expire_time",
    "expireTime",
    "labels",
})


def evaluate_google_adk_session_and_toolauth(
    *,
    create_session_kwargs: dict[str, Any],
    session_state: dict[str, Any],
    compaction_aborted: bool,
    artifact_dir_versions: dict[str, list[str]],
    auth_config: dict[str, Any],
) -> dict[str, Any]:
    """Reference contract for Google ADK Python session allowlist, compaction abort,
    artifact version check, and ADK Go `toolauth` redaction.
    """
    unexpected = sorted(set(create_session_kwargs) - ADK_ALLOWED_CREATE_SESSION_KEYS)
    if unexpected:
        raise ValueError(f"Unexpected create_session config keys: {unexpected}")

    has_ttl = "ttl" in create_session_kwargs and create_session_kwargs["ttl"] is not None
    has_expire = (
        create_session_kwargs.get("expire_time") is not None
        or create_session_kwargs.get("expireTime") is not None
    )
    if has_ttl and has_expire:
        raise ValueError("Cannot specify both ttl and expire_time/expireTime")

    persisted_state = {
        k: v
        for k, v in session_state.items()
        if not k.startswith(ADK_TEMP_STATE_PREFIX)
    }

    compaction_status = (
        "aborted_cancelled_no_write" if compaction_aborted else "committed_summary"
    )

    visible_artifacts = sorted(
        key for key, versions in artifact_dir_versions.items() if len(versions) > 0
    )

    # ADK Go toolauth stable cache key (excluding dynamic tokens/state/codes)
    static_identity = {
        "auth_scheme": auth_config.get("auth_scheme", ""),
        "auth_type": auth_config.get("auth_type", ""),
        "client_id": auth_config.get("client_id", ""),
        "scopes": sorted(auth_config.get("scopes", [])),
    }
    digest = hashlib.sha256(
        json.dumps(static_identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    credential_cache_key = f"adk_{static_identity['auth_scheme']}_{digest}_{static_identity['auth_type']}"

    # ADK Go toolauth redact.go contract
    redacted_log: dict[str, Any] = {}
    sensitive_fields = {
        "password",
        "token",
        "client_secret",
        "auth_code",
        "access_token",
        "refresh_token",
        "additional_headers",
    }
    for k, v in auth_config.items():
        if k == "extra" and isinstance(v, dict):
            redacted_log["extra"] = {ek: "<redacted>" for ek in v}
        elif k in sensitive_fields and v is not None:
            redacted_log[k] = "<redacted>"
        else:
            redacted_log[k] = v

    return {
        "persisted_state": persisted_state,
        "compaction_status": compaction_status,
        "visible_artifact_keys": visible_artifacts,
        "credential_cache_key": credential_cache_key,
        "redacted_log": redacted_log,
    }


# ============================================================================
# 4. MCP Go SDK MRTR (`eafb671c`) & OpenAI Agents JS Manifest Authority (`52fcb576`)
# ============================================================================

def evaluate_mcp_mrtr_and_sandbox_manifest_authority(
    *,
    mrtr_method: str,
    middleware_chain: list[str],
    middleware_reject_at: str | None,
    envelope_version: int,
    environment_preparation: str,
    provider_manifest: dict[str, Any],
    trusted_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Reference contract for MCP Go SDK MRTR receiving middleware routing (`eafb671c`)
    and OpenAI Agents JS `mergeClientPreparedManifestAuthority` (`52fcb576`).
    """
    allowed_mrtr_methods = {
        "elicitation/create",
        "sampling/createMessage",
        "roots/list",
    }
    if mrtr_method not in allowed_mrtr_methods:
        raise ValueError(f"Unsupported MRTR method: {mrtr_method}")

    executed_trace: list[str] = []
    for mw in middleware_chain:
        executed_trace.append(f"mw:enter:{mw}")
        if middleware_reject_at == mw:
            raise PermissionError(f"MRTR request blocked by receiving middleware '{mw}'")
    executed_trace.append(f"handler:{mrtr_method}")

    if envelope_version < 6 or environment_preparation != "client":
        raise PermissionError(
            "Sandbox session state requires envelope v6+ with client environmentPreparation"
        )

    # Structural fields come from provider_manifest; security authority fields strictly from trusted_manifest
    merged_manifest: dict[str, Any] = {
        "entries": list(provider_manifest.get("entries", [])),
        "users": list(provider_manifest.get("users", [])),
        "groups": list(provider_manifest.get("groups", [])),
        "environment": dict(provider_manifest.get("environment", {})),
        "extra_path_grants": list(provider_manifest.get("extra_path_grants", [])),
        "remote_mount_command_allowlist": list(
            provider_manifest.get("remote_mount_command_allowlist", [])
        ),
        "mount_credential_exposure_policy": provider_manifest.get(
            "mount_credential_exposure_policy", "default"
        ),
    }
    for auth_field in OPENAI_SANDBOX_AUTHORITY_FIELDS:
        if auth_field in trusted_manifest:
            val = trusted_manifest[auth_field]
            if isinstance(val, dict):
                merged_manifest[auth_field] = dict(val)
            elif isinstance(val, list):
                merged_manifest[auth_field] = list(val)
            else:
                merged_manifest[auth_field] = val

    return {
        "mrtr_trace": executed_trace,
        "merged_manifest": merged_manifest,
    }


# ============================================================================
# 5. OpenAI Codex (`fc916a22`, `7c11b807`, `154e8736`) & Cookbook Decisions (`f5819076`)
# ============================================================================

def parse_codex_guardian_assessment(
    *,
    event_kind: str,
    response_id: str | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Reference contract for `codex_api::guardian_assessment::parse_guardian_assessment` (`fc916a22`)."""
    if event_kind != "response.metadata":
        return None
    if not isinstance(response_id, str) or not response_id:
        return None
    if not isinstance(metadata, dict):
        return None
    guardian = metadata.get("guardian")
    if not isinstance(guardian, dict):
        return None
    item_id = guardian.get("item_id")
    requires_review = guardian.get("requires_review")
    if not isinstance(item_id, str) or not item_id:
        return None
    if not isinstance(requires_review, bool):
        return None
    return {
        "response_id": response_id,
        "item_id": item_id,
        "requires_review": requires_review,
        "grants_execution_permission": False,
        "enters_conversation_history": False,
    }


def validate_codex_write_stdin_approval_size(
    *,
    process_id: int,
    original_command: str,
    stdin_input: str,
    cwd: str,
    sandbox_permissions: str,
    approval_reason: str,
) -> dict[str, Any]:
    """Reference contract for `UnifiedExecProcessManager` `write_stdin` size check (`7c11b807`)."""
    full_action_payload: dict[str, Any] = {
        "tool": "write_stdin",
        "session_id": process_id,
        "original_command": original_command,
        "chars": stdin_input,
        "cwd": cwd,
        "sandbox_permissions": sandbox_permissions,
    }
    size_check_payload = dict(full_action_payload)
    if CODEX_EXCLUDE_ORIGINAL_COMMAND_FROM_STDIN_LIMIT:
        size_check_payload.pop("original_command", None)

    serialized = json.dumps(size_check_payload, indent=2)
    total_bytes = len(serialized.encode("utf-8")) + len(approval_reason.encode("utf-8"))
    oversized = total_bytes > CODEX_MAX_STDIN_APPROVAL_BYTES
    return {
        "guardian_action_json": full_action_payload,
        "measured_stdin_approval_bytes": total_bytes,
        "oversized": oversized,
        "decision": "reject_unreviewable_tail" if oversized else "submit_to_guardian",
    }


def _config_paths_overlap(segments: list[str], managed_path: list[str]) -> bool:
    return all(a == b for a, b in zip(segments, managed_path))


def merge_and_protect_codex_otel_metadata(
    *,
    user_span_attributes: dict[str, str],
    user_tracestate: dict[str, dict[str, str]],
    managed_span_attributes: dict[str, str],
    managed_tracestate: dict[str, dict[str, str]],
    write_path_segments: list[str],
    mtls_client_cert: str | None = None,
    mtls_client_key: str | None = None,
) -> dict[str, Any]:
    """Reference contract for Codex managed OpenTelemetry metadata & mTLS (`154e8736`)."""
    if (mtls_client_cert is None) != (mtls_client_key is None):
        raise ValueError("mTLS requires both client_certificate and client_private_key")
    tls_backend = "rustls" if (mtls_client_cert and mtls_client_key) else "default"

    effective_span = dict(user_span_attributes)
    conflict = False
    if managed_span_attributes:
        for k, v in managed_span_attributes.items():
            if not k:
                raise ValueError("Empty span attribute key is invalid")
            if k in effective_span and effective_span[k] != v:
                conflict = True
            effective_span[k] = v

    effective_tracestate: dict[str, dict[str, str]] = {
        m: dict(fields) for m, fields in user_tracestate.items() if fields
    }
    for member, fields in managed_tracestate.items():
        if not fields:
            continue
        target_member = effective_tracestate.setdefault(member, {})
        for fk, fv in fields.items():
            if "\n" in fv or "\r" in fv:
                raise ValueError("Header-unsafe newline in tracestate value")
            if fk in target_member and target_member[fk] != fv:
                conflict = True
            target_member[fk] = fv

    blocked_by: str | None = None
    if managed_span_attributes:
        for key in managed_span_attributes:
            if _config_paths_overlap(
                write_path_segments, ["otel", "span_attributes", key]
            ):
                blocked_by = "otel.span_attributes"
                break
    if blocked_by is None and managed_tracestate:
        for member, fields in managed_tracestate.items():
            if not fields:
                continue
            for field in fields:
                if _config_paths_overlap(
                    write_path_segments, ["otel", "tracestate", member, field]
                ):
                    blocked_by = "otel.tracestate"
                    break
            if blocked_by is not None:
                break

    return {
        "effective_span_attributes": effective_span,
        "effective_tracestate": effective_tracestate,
        "conflict": conflict,
        "write_blocked_by": blocked_by,
        "tls_backend": tls_backend,
    }


def evaluate_openai_decisions_and_capa_path_guard(
    *,
    decision_response: dict[str, Any],
    allowed_routes: tuple[str, ...],
    project_root: str,
    candidate_target_path: str,
    tool_exposure_mode: str = "mcp",
) -> dict[str, Any]:
    """Reference contract for OpenAI Cookbook `examples/decisions/routing.py` (`f5819076`)
    and `infragate/capa` `install-path-guard.ts` + `register-mcp-server.ts` (`d7af1197`).
    """
    route: str | None = None
    confidence: float | None = None
    answers = decision_response.get("answers")
    if isinstance(answers, list) and len(answers) == 1 and isinstance(answers[0], dict):
        ans = answers[0]
        raw_conf = ans.get("confidence")
        if (
            ans.get("type") == "choice"
            and ans.get("name") == "route"
            and ans.get("choice") in allowed_routes
            and not isinstance(raw_conf, bool)
            and isinstance(raw_conf, (int, float))
            and 0.0 <= float(raw_conf) <= 1.0
        ):
            route = str(ans["choice"])
            confidence = float(raw_conf)

    # capa install-path-guard: lexical relative check + per-segment symlink check
    root_path = Path(project_root).resolve()
    cand_path = Path(candidate_target_path)
    if not cand_path.is_absolute():
        cand_path = root_path / cand_path

    # Check lexical containment before resolving symlinks
    norm_root = os.path.normpath(str(root_path))
    norm_cand = os.path.normpath(str(cand_path))
    rel = os.path.relpath(norm_cand, norm_root)
    if rel == ".." or rel.startswith(".." + os.sep) or os.path.isabs(rel):
        raise PermissionError(f"Target path escapes projectRoot lexically: {candidate_target_path}")

    # Walk existing path chain and reject symlinks or realpath escape
    cur = root_path
    for part in Path(rel).parts:
        if part in ("", "."):
            continue
        cur = cur / part
        if cur.is_symlink():
            raise PermissionError(f"Symlink detected in provider install path: {cur}")
        if cur.exists():
            real_cur = cur.resolve()
            real_rel = os.path.relpath(str(real_cur), str(root_path))
            if real_rel == ".." or real_rel.startswith(".." + os.sep):
                raise PermissionError(f"Resolved realpath escapes projectRoot: {real_cur}")

    unregister_stale_mcp = (tool_exposure_mode == "none")

    return {
        "selected_route": route or "human_review",
        "confidence": confidence,
        "path_inside_project": True,
        "unregister_stale_mcp_servers": unregister_stale_mcp,
    }


# ============================================================================
# 6. Anthropic Claude Code (`v2.1.312`–`v2.1.314` & `mods/sec-default`)
# ============================================================================

SEC_DEFAULT_NO_CHAIN_SKIP_EVENTS: frozenset[str] = frozenset({
    "env.get",
    "command.describe",
    "tool.describe",
    "agent.offer",
    "attribution.text",
    "prompt.section",
})


def evaluate_claude_hook_concurrency_and_write_guard(
    *,
    active_hooks: int,
    timeout_waiting_hooks: int,
    requested_timeout_seconds: float,
    raw_hook_output: str,
    target_file_path: str,
    working_directories: list[str],
    block_writes_outside_working_dirs: bool,
    is_rule_or_claude_md_file: bool,
    file_total_lines: int,
    lines_read_by_model: int,
    sec_default_event: str,
    only_builtin_sec_default_hooks_event: bool,
) -> dict[str, Any]:
    """Reference contract for Claude Code v2.1.312-v2.1.314 hook concurrency cap (24+12),
    <1s timeout floor, PreCompact 10,000-char cap, `permissions.blockWritesOutsideWorkingDirectories`,
    unread large `CLAUDE.md` overwrite guard, and `mods/sec-default` 6-event skip optimization.
    """
    effective_timeout = max(1.0, float(requested_timeout_seconds))
    hook_admitted = (
        active_hooks < CLAUDE_MAX_ACTIVE_HOOKS_PER_SESSION
        and timeout_waiting_hooks < CLAUDE_MAX_TIMEOUT_WAITING_HOOKS
    )
    truncated_hook_output = raw_hook_output[:CLAUDE_PRECOMPACT_HOOK_OUTPUT_CAP]

    norm_target = os.path.normpath(target_file_path)
    inside_workdir = False
    for wd in working_directories:
        norm_wd = os.path.normpath(wd)
        rel = os.path.relpath(norm_target, norm_wd)
        if rel == "." or (rel != ".." and not rel.startswith(".." + os.sep)):
            inside_workdir = True
            break

    write_decision = "allow"
    if block_writes_outside_working_dirs and not inside_workdir:
        write_decision = "deny_outside_working_directories"
    elif is_rule_or_claude_md_file and file_total_lines > 0 and lines_read_by_model < file_total_lines:
        write_decision = "deny_unread_large_rule_file_read_all_or_edit_in_place"

    chain_skipped = bool(
        only_builtin_sec_default_hooks_event
        and sec_default_event in SEC_DEFAULT_NO_CHAIN_SKIP_EVENTS
    )

    return {
        "hook_admitted": hook_admitted,
        "effective_timeout_seconds": effective_timeout,
        "truncated_hook_output": truncated_hook_output,
        "write_decision": write_decision,
        "sec_default_chain_skipped": chain_skipped,
    }
