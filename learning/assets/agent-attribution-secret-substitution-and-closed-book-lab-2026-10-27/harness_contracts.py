"""Offline Python 3.11+ standard-library reference contracts for the 2026-10-27 SA lab.

Scope & Provenance:
- This module models deterministic control-plane and data-plane contracts distilled from fixed
  upstream commits inspected on 2026-10-27 (see fixtures/provenance.json).
- Zero Python `assert` statements are used in this module so that behavior is identical under
  normal (`python3 -B`) and optimized (`python3 -B -O`) execution.
- Upstream product runtimes/CLIs/SDKs (MAF Python/.NET, Azure AI AgentServer, GitHub Copilot SDK
  AHP Host, Google ADK /run_live, MCP Go SDK, NVIDIA NeMo Helix, OpenAI Codex MITM Proxy & CLI,
  Anthropic Claude Code CLI) are NOT_RUN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Callable, Iterable, Mapping, Sequence


class ContractError(ValueError):
    """Deterministic contract violation raised by reference gates."""


# ============================================================================
# 1. Microsoft Agent Framework (MAF) Contracts
#    - S01: agent-hooks-declaration/1.0 (`18adf808a57eb6668fc773162037b311d36c5678`)
#    - S02: FIDES Quarantine Client Scope (`7db56c05f949b39535fef6d5a9bfdf645e3beffc`)
#    - S03: FoundryToolboxService require_approval (`264439f7f5c71713051b8db4e51fd04f33fcb422`)
# ============================================================================

DECLARATION_VERSION = "agent-hooks-declaration/1.0"
DECLARATION_KIND = "agent_framework.interceptor"
DECLARATION_CAPABILITIES = frozenset(
    {"model_calls", "tool_calls", "int64_json", "bigint_json", "host_declaration"}
)
DECLARATION_POSTURE = "terminate"


@dataclass(frozen=True)
class ResolvedHookBinding:
    binding_id: str
    interceptor_name: str
    handler: Callable[[str], str]


@dataclass(frozen=True)
class SealedHooksDeclarationSession:
    session_id: str
    declaration_version: str
    posture: str
    bindings: tuple[ResolvedHookBinding, ...]


def validate_and_bind_agent_hooks_declaration(
    document: Mapping[str, Any],
    interceptors: Mapping[str, Callable[[str], str]],
    *,
    session_id: str = "run-session-01",
) -> SealedHooksDeclarationSession:
    """Validate an `agent-hooks-declaration/1.0` document against MAF host surface.

    Enforces:
    - Exact declaration version `agent-hooks-declaration/1.0`
    - Tool-seam host error posture must be `terminate` (rejects `continue` or missing)
    - Requested capabilities must be a subset of `DECLARATION_CAPABILITIES`
    - Non-empty bindings of kind `agent_framework.interceptor` resolved strictly via
      dictionary lookup (`config.name` or `binding.id`) with zero dynamic imports and
      without echoing sensitive `config` payloads on failure.
    """
    if not isinstance(document, Mapping):
        raise ContractError("declaration document must be a mapping")
    version = document.get("declaration")
    if version != DECLARATION_VERSION:
        raise ContractError(f"unsupported declaration version: {version!r}")

    configuration = document.get("configuration")
    if not isinstance(configuration, Mapping):
        raise ContractError("declaration configuration must be a mapping")

    posture = configuration.get("posture")
    if not isinstance(posture, Mapping) or posture.get("tool_seam_host_error") != DECLARATION_POSTURE:
        raise ContractError("declaration posture.tool_seam_host_error must equal 'terminate'")

    requested_caps = configuration.get("capabilities", ())
    if not isinstance(requested_caps, (list, tuple, set, frozenset)):
        raise ContractError("declaration configuration.capabilities must be a sequence")
    unknown_caps = set(requested_caps) - DECLARATION_CAPABILITIES
    if unknown_caps:
        raise ContractError(f"unsupported host surface capabilities: {sorted(unknown_caps)}")

    raw_bindings = document.get("bindings")
    if not isinstance(raw_bindings, Sequence) or isinstance(raw_bindings, (str, bytes)) or len(raw_bindings) == 0:
        raise ContractError("declaration bindings must be a non-empty sequence")

    resolved: list[ResolvedHookBinding] = []
    seen_ids: set[str] = set()
    for item in raw_bindings:
        if not isinstance(item, Mapping):
            raise ContractError("binding entry must be a mapping")
        binding_id = item.get("id")
        kind = item.get("kind")
        if not isinstance(binding_id, str) or not binding_id.strip():
            raise ContractError("binding id must be a non-empty string")
        if binding_id in seen_ids:
            raise ContractError(f"duplicate binding id: {binding_id}")
        seen_ids.add(binding_id)
        if kind != DECLARATION_KIND:
            raise ContractError(f"unsupported binding kind for '{binding_id}': {kind!r}")

        cfg = item.get("config")
        lookup_name = binding_id
        if cfg is not None:
            if not isinstance(cfg, Mapping):
                raise ContractError(f"binding '{binding_id}' config must be a mapping")
            if "module" in cfg or "import_path" in cfg:
                raise ContractError(f"binding '{binding_id}' prohibits dynamic import keys")
            cfg_name = cfg.get("name")
            if cfg_name is not None:
                if not isinstance(cfg_name, str) or not cfg_name.strip():
                    raise ContractError(f"binding '{binding_id}' config.name must be a non-empty string")
                lookup_name = cfg_name

        if lookup_name not in interceptors:
            # Never echo raw `cfg` dictionary values (which may hold sensitive policy thresholds/tokens)
            raise ContractError(
                f"unregistered interceptor '{lookup_name}' for binding '{binding_id}'"
            )
        resolved.append(
            ResolvedHookBinding(
                binding_id=binding_id,
                interceptor_name=lookup_name,
                handler=interceptors[lookup_name],
            )
        )

    return SealedHooksDeclarationSession(
        session_id=session_id,
        declaration_version=DECLARATION_VERSION,
        posture=DECLARATION_POSTURE,
        bindings=tuple(resolved),
    )


@dataclass
class ScopedQuarantineMiddleware:
    """Models `LabelTrackingFunctionMiddleware` quarantine binding (`7db56c05`)."""

    quarantine_client_bound: bool = False
    quarantine_client_override: str | None = None


def bind_quarantine_client_to_middleware(
    middleware: ScopedQuarantineMiddleware,
    config_quarantine_client: str | None,
) -> ScopedQuarantineMiddleware:
    """Bind a `SecureAgentConfig`'s client (including explicit `None`) to its middleware."""
    middleware.quarantine_client_bound = True
    middleware.quarantine_client_override = config_quarantine_client
    return middleware


def resolve_fides_quarantine_client(
    middleware: ScopedQuarantineMiddleware | None,
    process_global_client: str | None,
) -> str | None:
    """Resolve the quarantine LLM client for `quarantined_llm` tool execution.

    Scoped middleware always wins, including when `quarantine_client_override` is explicitly `None`
    (preventing cross-agent inheritance from the process-global slot). Standalone calls (`middleware=None`
    or unbound) fall back to `process_global_client`.
    """
    if middleware is not None and middleware.quarantine_client_bound:
        return middleware.quarantine_client_override
    return process_global_client


def requires_foundry_toolbox_approval(
    meta: Mapping[str, Any] | None,
    *,
    service_already_requires_approval: bool = False,
) -> tuple[bool, bool]:
    """Model `FoundryToolboxService.RequiresToolApproval` (`264439f7`).

    Returns `(requires_approval, logged_warning)`.
    - Service-level `ApprovalRequiredAIFunction` takes precedence -> `(True, False)`.
    - Missing `_meta` or missing `tool_configuration` -> `(False, False)`.
    - `tool_configuration` is a JSON object without `require_approval` -> `(False, False)`.
    - `require_approval == "always"` -> `(True, False)`.
    - `require_approval == "never"` -> `(False, False)`.
    - Any other explicit `tool_configuration` or unsupported/malformed `require_approval` value
      fails closed -> `(True, True)`.
    """
    if service_already_requires_approval:
        return (True, False)
    if meta is None or not isinstance(meta, Mapping):
        return (False, False)
    if "tool_configuration" not in meta:
        return (False, False)

    tool_cfg = meta["tool_configuration"]
    if isinstance(tool_cfg, Mapping):
        if "require_approval" not in tool_cfg:
            return (False, False)
        policy = tool_cfg["require_approval"]
        if isinstance(policy, str):
            if policy == "always":
                return (True, False)
            if policy == "never":
                return (False, False)

    return (True, True)


# ============================================================================
# 2. Azure AI AgentServer & GitHub Copilot SDK AHP Host Contracts
#    - S05: `FoundryOriginalSubject` & `FoundryAgentRequestContext` (`a7dd9f37`)
#    - S04: `AhpHostAuthentication` & `setAllowCreatingNewSessions` (`f2b720c8`)
# ============================================================================

ORIGINAL_SUBJECT_HEADER = "x-ms-original-subject"
FOUNDRY_CALL_ID_HEADER = "x-agent-foundry-call-id"
AGENT_USER_ID_HEADER = "x-agent-user-id"

_ORIGINAL_SUBJECT_MEMBER_RE = re.compile(
    r'(oid|tid|idtype)="((?:[\x20-\x21\x23-\x5b\x5d-\x7e]|\\["\\])*)"'
)


@dataclass(frozen=True, repr=False)
class FoundryOriginalSubject:
    """Invocation-local original-subject assertions (`a7dd9f37`)."""

    oid: str | None = None
    tid: str | None = None
    idtype: str | None = None

    @classmethod
    def from_headers(cls, headers: Mapping[str, str] | Sequence[tuple[str, str]]) -> FoundryOriginalSubject | None:
        items: Sequence[tuple[str, str]]
        if isinstance(headers, Mapping):
            items = list(headers.items())
        else:
            items = list(headers)

        fields = [value for name, value in items if name.lower() == ORIGINAL_SUBJECT_HEADER]
        if not fields:
            return None
        if len(fields) != 1:
            raise ContractError("Original-subject attribution requires a single header field.")

        remaining = fields[0].strip(" \t")
        values: dict[str, str] = {}
        while remaining:
            member = _ORIGINAL_SUBJECT_MEMBER_RE.match(remaining)
            if member is None or member.group(1) in values:
                raise ContractError(
                    "Original-subject attribution requires unique oid/tid/idtype string members."
                )
            values[member.group(1)] = re.sub(r'\\(["\\])', r"\1", member.group(2))
            remaining = remaining[member.end() :].lstrip(" \t")
            if not remaining:
                break
            if not remaining.startswith(",") or not remaining[1:].strip(" \t"):
                raise ContractError(
                    "Original-subject attribution requires comma-separated dictionary members."
                )
            remaining = remaining[1:].lstrip(" \t")
        if not values:
            raise ContractError("Original-subject attribution requires a nonempty dictionary.")
        return cls(oid=values.get("oid"), tid=values.get("tid"), idtype=values.get("idtype"))


@dataclass(frozen=True)
class FoundryAgentRequestContextContract:
    call_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    original_subject: FoundryOriginalSubject | None = None

    def platform_headers(self) -> dict[str, str]:
        """Headers sent to platform tools (Foundry Toolbox, etc.): never includes original_subject."""
        if self.call_id:
            return {FOUNDRY_CALL_ID_HEADER: self.call_id}
        return {}

    def model_attribution_headers(self) -> dict[str, str]:
        """Build per-call attribution headers for supported model endpoints (`a7dd9f37`)."""
        subject = self.original_subject
        if subject is None:
            return {}
        members: list[str] = []
        for name, value in (("oid", subject.oid), ("tid", subject.tid), ("idtype", subject.idtype)):
            if not value or any(ch < "!" or ch > "~" for ch in value):
                raise ContractError("Original-subject attribution requires a complete, HTTP-safe tuple.")
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            members.append(f'{name}="{escaped}"')
        result = {ORIGINAL_SUBJECT_HEADER: ", ".join(members)}
        if self.call_id:
            result[FOUNDRY_CALL_ID_HEADER] = self.call_id
        return result


@dataclass(frozen=True)
class AhpAdmissionDecision:
    admitted: bool
    reason: str
    owner_identity: str | None = None
    used_as_inference_credential: bool = False


def evaluate_ahp_host_admission(
    *,
    auth_mode: str | None,
    require_identity: str | None = None,
    github_environment_enabled: bool = False,
    allow_creating_new_sessions: bool = False,
    is_new_session_request: bool = False,
    admission_token: str | None = None,
    callback_result: Mapping[str, Any] | None = None,
    cancelled: bool = False,
    now_epoch_seconds: int = 1_793_000_000,
) -> AhpAdmissionDecision:
    """Model GitHub Copilot SDK `AhpHostAuthentication` & session creation gate (`f2b720c8`)."""
    if auth_mode not in {"github", "none", "custom"}:
        return AhpAdmissionDecision(False, "missing_or_invalid_auth_mode")

    if github_environment_enabled and auth_mode != "github":
        return AhpAdmissionDecision(False, "github_environment_requires_github_auth_mode")

    if is_new_session_request and not allow_creating_new_sessions:
        return AhpAdmissionDecision(False, "new_session_creation_disabled")

    if cancelled:
        return AhpAdmissionDecision(False, "authentication_cancelled")

    if auth_mode == "none":
        return AhpAdmissionDecision(True, "anonymous_admitted", owner_identity=None)

    if auth_mode == "github":
        if not admission_token:
            return AhpAdmissionDecision(False, "missing_github_admission_token")
        return AhpAdmissionDecision(True, "github_admitted", owner_identity="github-owner")

    # auth_mode == "custom"
    if not isinstance(require_identity, str) or not require_identity.strip():
        return AhpAdmissionDecision(False, "custom_auth_requires_non_empty_identity")
    if not admission_token:
        return AhpAdmissionDecision(False, "missing_custom_admission_token")
    if not isinstance(callback_result, Mapping):
        return AhpAdmissionDecision(False, "custom_auth_callback_rejected")

    returned_identity = callback_result.get("identity")
    expires_at_raw = callback_result.get("expires_at")
    if returned_identity != require_identity:
        return AhpAdmissionDecision(False, "custom_auth_identity_mismatch")
    if not isinstance(expires_at_raw, str) or not expires_at_raw.strip():
        return AhpAdmissionDecision(False, "custom_auth_missing_expires_at")

    try:
        normalized = expires_at_raw[:-1] + "+00:00" if expires_at_raw.endswith("Z") else expires_at_raw
        parsed_dt = datetime.fromisoformat(normalized)
        if parsed_dt.tzinfo is None:
            return AhpAdmissionDecision(False, "custom_auth_expires_at_missing_tz")
        exp_epoch = parsed_dt.astimezone(timezone.utc).timestamp()
    except ValueError:
        return AhpAdmissionDecision(False, "custom_auth_invalid_rfc3339_expires_at")

    if exp_epoch <= float(now_epoch_seconds):
        return AhpAdmissionDecision(False, "custom_auth_token_expired")

    return AhpAdmissionDecision(
        admitted=True,
        reason="custom_admitted",
        owner_identity=returned_identity,
        used_as_inference_credential=False,
    )


# ============================================================================
# 3. Google ADK `/run_live` & MCP Go SDK Enterprise Auth Contracts
#    - S06: Google ADK `/run_live` malformed frame & teardown (`3b227d6e`)
#    - S07/S08: MCP Go SDK RFC 9207 `iss` (`fa799c5f`) & ID-JAG (`6f47cb79`)
# ============================================================================

@dataclass(frozen=True)
class AdkLiveSessionOutcome:
    wait_policy: str
    close_code: int | None
    close_reason: str
    redacted_warning_log: str | None
    queue_closed: bool
    sibling_tasks_cancelled_and_awaited: bool


def simulate_adk_run_live_session(
    *,
    inbound_frame: Mapping[str, Any] | None = None,
    validation_error_types: Sequence[str] = (),
    runner_exception: str | None = None,
    client_disconnected: bool = False,
) -> AdkLiveSessionOutcome:
    """Model Google ADK `/run_live` lifecycle (`3b227d6ec82490dae6473f681dcc825b1ac31679`).

    - Uses `FIRST_COMPLETED` (not `FIRST_EXCEPTION`) so a normal `return` from `process_messages()`
      after a malformed client frame cannot wedge `forward_events()`.
    - Logs only sorted unique Pydantic `error["type"]` identifiers, never raw payload or invented field names.
    - Always closes `live_request_queue`, cancels tasks, and awaits them in `finally`.
    """
    if client_disconnected:
        return AdkLiveSessionOutcome(
            wait_policy="FIRST_COMPLETED",
            close_code=None,
            close_reason="",
            redacted_warning_log=None,
            queue_closed=True,
            sibling_tasks_cancelled_and_awaited=True,
        )

    if validation_error_types:
        unique_sorted_types = ", ".join(sorted(set(validation_error_types)))
        return AdkLiveSessionOutcome(
            wait_policy="FIRST_COMPLETED",
            close_code=1007,
            close_reason="Invalid live request",
            redacted_warning_log=f"Invalid live request: {unique_sorted_types}",
            queue_closed=True,
            sibling_tasks_cancelled_and_awaited=True,
        )

    if runner_exception == "SessionNotFoundError":
        return AdkLiveSessionOutcome(
            wait_policy="FIRST_COMPLETED",
            close_code=1002,
            close_reason="Session not found",
            redacted_warning_log=None,
            queue_closed=True,
            sibling_tasks_cancelled_and_awaited=True,
        )

    if runner_exception is not None:
        return AdkLiveSessionOutcome(
            wait_policy="FIRST_COMPLETED",
            close_code=1011,
            close_reason=runner_exception[:123],
            redacted_warning_log=None,
            queue_closed=True,
            sibling_tasks_cancelled_and_awaited=True,
        )

    return AdkLiveSessionOutcome(
        wait_policy="FIRST_COMPLETED",
        close_code=1000,
        close_reason="",
        redacted_warning_log=None,
        queue_closed=True,
        sibling_tasks_cancelled_and_awaited=True,
    )


TOKEN_TYPE_ID_JAG = "urn:ietf:params:oauth:token-type:id-jag"


def verify_mcp_oidc_and_id_jag_exchange(
    *,
    expected_state: str,
    received_state: str,
    expected_issuer: str,
    received_iss: str,
    iss_parameter_supported: bool,
    exchanged_issued_token_type: str,
) -> str:
    """Model MCP Go SDK `checkAuthorizationResponseIssuer` (`fa799c5f`) + `EnterpriseHandler.Authorize` (`6f47cb79`)."""
    if received_state != expected_state:
        raise ContractError(f"state mismatch: expected {expected_state!r}, got {received_state!r}")

    if received_iss == "":
        if iss_parameter_supported:
            raise ContractError(
                "IdP advertises RFC 9207 iss parameter support but none was received in the authorization response"
            )
    elif received_iss != expected_issuer:
        raise ContractError(
            f"authorization response issuer {received_iss!r} does not match expected issuer {expected_issuer!r}"
        )

    if exchanged_issued_token_type != TOKEN_TYPE_ID_JAG:
        raise ContractError(
            f"token exchange issued a token of type {exchanged_issued_token_type!r}, want {TOKEN_TYPE_ID_JAG!r}"
        )

    return "MCP_ENTERPRISE_TOKEN_EXCHANGE_VERIFIED"


# ============================================================================
# 4. NVIDIA NeMo Helix Closed-Book Route Gate
#    - S09: `require_closed_book_route` (`8c3ef7f50c88ba6ff1775350dd4cdfa5473c7b9a`)
# ============================================================================

CLOSED_BOOK_MIDDLEWARE = "nemo-evals-closed-book"
MODEL_FREE_HARBOR_AGENTS = frozenset({"oracle", "nop"})


def _task_runs_without_network(task_cfg: Mapping[str, Any]) -> bool:
    env = task_cfg.get("environment")
    if isinstance(env, Mapping):
        if env.get("network_mode") == "no-network" or env.get("allow_internet") is False:
            return True
    agent = task_cfg.get("agent")
    if isinstance(agent, Mapping) and agent.get("network_mode") == "no-network":
        return True
    steps = task_cfg.get("steps")
    if isinstance(steps, Sequence) and not isinstance(steps, (str, bytes)):
        for step in steps:
            if isinstance(step, Mapping):
                step_agent = step.get("agent")
                if isinstance(step_agent, Mapping) and step_agent.get("network_mode") == "no-network":
                    return True
                step_env = step.get("environment")
                if isinstance(step_env, Mapping) and step_env.get("network_mode") == "no-network":
                    return True
    return False


def require_closed_book_virtual_model_route(
    *,
    agent_name: str,
    gateway_model_ref: str | None,
    tasks: Iterable[tuple[str, Mapping[str, Any]]],
    caller_authorized_to_read_virtual_model: bool = True,
    virtual_model_exists: bool = True,
    request_middleware: Sequence[str] = (),
    response_middleware: Sequence[str] = (),
) -> str:
    """Model `require_closed_book_route` (`8c3ef7f50c88ba6ff1775350dd4cdfa5473c7b9a`)."""
    no_network_ids = [tid for tid, cfg in tasks if _task_runs_without_network(cfg)]
    if not no_network_ids or agent_name in MODEL_FREE_HARBOR_AGENTS:
        return "ALLOWED_NO_CLOSED_BOOK_CHECK_REQUIRED"

    if not gateway_model_ref:
        raise ContractError(
            f"closed_book_required: no-network tasks {no_network_ids} need the agent's model calls "
            "to go through a closed-book VirtualModel"
        )

    if not caller_authorized_to_read_virtual_model:
        raise PermissionError(f"caller is not authorized to read virtual_model {gateway_model_ref!r}")

    _ = response_middleware  # Response middleware cannot prevent hosted tools from running on the model
    if (
        not virtual_model_exists
        or not request_middleware
        or request_middleware[-1] != CLOSED_BOOK_MIDDLEWARE
    ):
        raise ContractError(
            f"closed_book_required: no-network tasks {no_network_ids} need a closed-book model route, "
            f"and {gateway_model_ref} isn't one: make `{CLOSED_BOOK_MIDDLEWARE}` the last entry "
            "of its VirtualModel's request_middleware"
        )

    return "ALLOWED_CLOSED_BOOK_VIRTUAL_MODEL_VERIFIED"


# ============================================================================
# 5. OpenAI Codex MITM v2 Body Secret Substitution & Advisory Rollout Budget
#    - S10: `secret_substitution.rs` & `mitm.rs` (`619531225b29dcf6437ec6571537f9da9da002bc`)
#    - S11: `rollout_budget.rs` (`77eb019ad039d21e5a346e77568739993a7f94cd`)
#    - S12: Cookbook Databricks `codex exec-server` scope (`8495326b6f1b7cec94e7f5e393a4045e328a268e`)
# ============================================================================

MAX_SUBSTITUTION_SEARCH_BYTES = 256 * 1024 * 1024
MAX_SUBSTITUTION_MATCHES = 65_536
FORBIDDEN_INTEGRITY_HEADERS = frozenset(
    {
        "trailer",
        "x-amz-trailer",
        "x-amz-decoded-content-length",
        "content-md5",
        "digest",
        "content-digest",
        "repr-digest",
        "x-amz-content-sha256",
    }
)


@dataclass(frozen=True)
class BodySecretReplacementBinding:
    placeholder: str
    secret_bytes: bytes


@dataclass(frozen=True)
class MitmSubstitutedRequest:
    body: bytes
    headers: dict[str, str]
    pipeline_trace: tuple[str, ...]


def apply_codex_mitm_v2_body_secret_substitution(
    *,
    scheme: str,
    port: int,
    configured_port: int = 443,
    max_body_bytes: int = 8 * 1024 * 1024,
    headers: Mapping[str, str],
    body: bytes,
    has_trailers: bool = False,
    replacements: Sequence[BodySecretReplacementBinding],
    sign_after_substitution: bool = False,
) -> MitmSubstitutedRequest:
    """Model Codex `BodySecretSubstitution::apply` & `mitm.rs` ordering (`61953122`)."""
    if configured_port <= 0 or max_body_bytes > 16 * 1024 * 1024:
        raise ContractError("invalid body substitution port, bindings, or limit (maximum 16 MiB)")
    if not replacements or len(replacements) > 32:
        raise ContractError("invalid body substitution port, bindings, or limit (maximum 16 MiB)")

    for idx, item in enumerate(replacements):
        if not (16 <= len(item.placeholder) <= 256) or not item.placeholder.isascii():
            raise ContractError("body placeholders must be opaque ASCII markers of 16 to 256 bytes")
        for prev in replacements[:idx]:
            if prev.placeholder in item.placeholder or item.placeholder in prev.placeholder:
                raise ContractError("body substitution bindings overlap")

    for item in replacements:
        if len(item.secret_bytes) > max_body_bytes:
            raise ContractError("body substitution secret exceeds limit or contains a placeholder")
        for binding in replacements:
            if binding.placeholder.encode("ascii") in item.secret_bytes:
                raise ContractError("body substitution secret exceeds limit or contains a placeholder")

    if scheme != "https" or port != configured_port:
        raise ContractError("body substitution requires its configured HTTPS port")

    lower_headers = {k.lower(): v for k, v in headers.items()}
    content_encoding = lower_headers.get("content-encoding", "identity")
    if any(part.strip().lower() != "identity" for part in content_encoding.split(",")):
        raise ContractError(
            "body substitution does not support encoded, streaming-signed, or integrity-protected payloads"
        )

    for hname in lower_headers:
        if hname in FORBIDDEN_INTEGRITY_HEADERS or hname.startswith("x-amz-checksum-"):
            raise ContractError(
                "body substitution does not support encoded, streaming-signed, or integrity-protected payloads"
            )

    if has_trailers:
        raise ContractError("body substitution does not support request trailers")

    if len(body) > max_body_bytes:
        raise ContractError("body substitution exceeds limit or cannot read payload")

    if "content-length" in lower_headers:
        try:
            declared_len = int(lower_headers["content-length"])
        except ValueError as exc:
            raise ContractError("body substitution content length does not match the request body") from exc
        if declared_len != len(body):
            raise ContractError("body substitution content length does not match the request body")

    total_search_work = 0
    for item in replacements:
        plen = len(item.placeholder)
        windows = max(0, len(body) - (plen - 1))
        total_search_work += windows * plen
        if total_search_work > MAX_SUBSTITUTION_SEARCH_BYTES:
            raise ContractError("body substitution search exceeds work limit")

    matches: list[tuple[int, int, int]] = []
    for idx, item in enumerate(replacements):
        needle = item.placeholder.encode("ascii")
        plen = len(needle)
        for offset in range(0, max(0, len(body) - plen + 1)):
            if body[offset : offset + plen] == needle:
                if len(matches) >= MAX_SUBSTITUTION_MATCHES:
                    raise ContractError("too many body substitution occurrences")
                matches.append((offset, offset + plen, idx))

    matches.sort()
    cursor = 0
    expanded_size = len(body)
    for start, end, idx in matches:
        if start < cursor:
            raise ContractError("body substitution matches overlap")
        expanded_size = expanded_size - (end - start) + len(replacements[idx].secret_bytes)
        cursor = end

    if expanded_size > max_body_bytes:
        raise ContractError("expanded body substitution exceeds limit")

    out_chunks: list[bytes] = []
    cursor = 0
    for start, end, idx in matches:
        out_chunks.append(body[cursor:start])
        out_chunks.append(replacements[idx].secret_bytes)
        cursor = end
    out_chunks.append(body[cursor:])
    new_body = b"".join(out_chunks)

    out_headers = dict(lower_headers)
    out_headers.pop("transfer-encoding", None)
    out_headers.pop("trailer", None)
    out_headers["content-length"] = str(len(new_body))

    trace = ["destination_authorized", "body_secret_substituted"]
    if sign_after_substitution:
        import hashlib

        out_headers["x-amz-content-sha256"] = hashlib.sha256(new_body).hexdigest()
        trace.append("aws_sigv4_signed_over_expanded_body")

    return MitmSubstitutedRequest(
        body=new_body,
        headers=out_headers,
        pipeline_trace=tuple(trace),
    )


@dataclass
class CodexRolloutBudgetTracker:
    """Model `RolloutBudget` (`77eb019ad039d21e5a346e77568739993a7f94cd`)."""

    limit_tokens: int
    enforce_limit: bool = True
    reminder_at_remaining_tokens: tuple[int, ...] = (50, 20, 0)
    sampling_token_weight: float = 1.0
    prefill_token_weight: float = 1.0
    weighted_tokens_used: float = 0.0
    emitted_reminders: set[int] = field(default_factory=set)

    def record_usage(
        self,
        *,
        output_tokens: int,
        non_cached_input_tokens: int = 0,
    ) -> tuple[bool, int | None]:
        """Record token usage across root/subagents and return `(is_enforced_exhausted, reminder_remaining)`."""
        units = (
            float(output_tokens) * self.sampling_token_weight
            + float(non_cached_input_tokens) * self.prefill_token_weight
        )
        self.weighted_tokens_used += units
        remaining = max(0, int(round(float(self.limit_tokens) - self.weighted_tokens_used)))

        triggered_reminder: int | None = None
        for threshold in sorted(self.reminder_at_remaining_tokens, reverse=True):
            if remaining <= threshold and threshold not in self.emitted_reminders:
                self.emitted_reminders.add(threshold)
                triggered_reminder = remaining if threshold == 0 else threshold

        if remaining == 0 and 0 not in self.emitted_reminders:
            self.emitted_reminders.add(0)
            triggered_reminder = 0

        exhausted = self.enforce_limit and (self.weighted_tokens_used >= float(self.limit_tokens))
        return (exhausted, triggered_reminder)


# ============================================================================
# 6. Anthropic Claude Code `v2.1.307`–`v2.1.310` & `mods/sec-default` Reopen
#    - S13: `v2.1.307`–`v2.1.310` (`b70dc4113ad72e0ee44f7b1b95afaf510b53ee98`)
#    - S14: `mods/sec-default` reopen gate (`318b7e6ac4e726e88a4ad326214866a93c373b1b`)
#    - Community reference: `yonatangross/orchestkit` (`b850f51af1a66623b8a5c7c34ef7cdf7ee325a9d`)
# ============================================================================

MAX_SEC_DEFAULT_REOPEN_REGEX_CHARS = 65_536


@dataclass(frozen=True)
class ClaudeSecDefaultReopenOutcome:
    user_tier_reopened: bool
    reason: str
    safety_event_emitted: bool


def evaluate_claude_sec_default_reopen_and_safety(
    *,
    opener_tier: str,
    spells_next_to_user: bool,
    matcher_regex_pattern: str,
    event_matches_opener_matcher: bool,
    tool_verdict: str = "allow",
) -> ClaudeSecDefaultReopenOutcome:
    """Model `mods/sec-default` reopen boundary (`318b7e6a`) and `claude_code.safety_event` (`v2.1.307`).

    - Only an organization plugin seated above `sec-default` in `prepend` can reopen an event
      to the `user` tier via `next.to(e, "user")`.
    - Plugins seated below `sec-default` (`user` or `append`) reopen nothing (`append` floor wins).
    - RegExp patterns exceeding 65,536 characters are not read and the reopen is refused.
    - Whenever a tool call is `stopped`, `prompted`, or `sent_back` by a permission rule, auto mode,
      safety check, hook, or sandbox, `claude_code.safety_event` is emitted.
    """
    safety_event = tool_verdict in {"stopped", "prompted", "sent_back"}

    if not spells_next_to_user:
        return ClaudeSecDefaultReopenOutcome(False, "no_reopen_requested", safety_event)

    if opener_tier != "prepend":
        return ClaudeSecDefaultReopenOutcome(False, "floor_at_append_wins_for_non_prepend_tier", safety_event)

    if len(matcher_regex_pattern) > MAX_SEC_DEFAULT_REOPEN_REGEX_CHARS:
        return ClaudeSecDefaultReopenOutcome(False, "regexp_exceeds_65536_char_limit_reopen_refused", safety_event)

    if not event_matches_opener_matcher:
        return ClaudeSecDefaultReopenOutcome(False, "event_outside_opener_matcher_width", safety_event)

    return ClaudeSecDefaultReopenOutcome(True, "reopened_to_user_tier_by_prepend_org_plugin", safety_event)


def verify_nested_claude_headless_spawn_argv(
    argv: Sequence[str],
    *,
    cwd: str,
) -> bool:
    """Validate nested `claude -p` spawn arguments against privilege escalation & `/tmp` settings poisoning.

    Enforces that any nested `claude -p` helper spawned in an untrusted or shared working directory
    (such as `/tmp`) includes both `--restricted` (ignoring `<cwd>/.claude/settings.json` `apiKeyHelper`)
    and `--tools ""` (disabling built-in `Bash`/`WebFetch` tools).
    """
    if "-p" not in argv and "--print" not in argv:
        raise ContractError("nested helper must run in non-interactive print mode (-p)")

    if "--restricted" not in argv:
        raise ContractError(
            f"nested claude spawn in {cwd!r} missing '--restricted': vulnerable to cwd settings/apiKeyHelper poisoning"
        )

    has_empty_tools = False
    for idx, token in enumerate(argv[:-1]):
        if token == "--tools" and argv[idx + 1] == "":
            has_empty_tools = True
            break
    if not has_empty_tools:
        raise ContractError("nested claude spawn missing '--tools \"\"': built-in Bash/WebFetch remain enabled")

    return True
