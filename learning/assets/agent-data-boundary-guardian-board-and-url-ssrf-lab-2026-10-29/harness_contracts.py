"""Offline Python 3.11+ stdlib reference specification for six cross-pillar agent harness contracts (2026-10-29).

Scope boundary:
- Original stdlib-only reference contract model for offline unit testing and mutation calibration.
- Zero `assert` statements (`ast.Assert` count == 0) so all gates remain active under `python3 -B -O`.
- Upstream product runtimes/CLIs/SDKs (Azure MCP Server 4.0.0-beta.3, Microsoft Agent Framework Python,
  Google ADK Python, NVIDIA NeMo Guardrails Rust Relay Plugin, OpenAI Agents Python SDK, OpenAI Codex CLI,
  Anthropic Claude Code CLI, and Planning with Files hooks) are NOT_RUN.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Final, Sequence


class ContractViolationError(ValueError):
    """Raised when a harness security, routing, scope, or protocol invariant is violated."""


# ============================================================================
# 1. Azure MCP Server 4.0.0-beta.3 — ResiliencyAgent A2A DataBoundaryResolver,
#    AttachmentPolicy (1434 KiB), & ArtifactWriter (microsoft/mcp@b3f862be67cfd39ff43a9de038bc747e378f4571)
# ============================================================================

RESILIENCY_PUBLIC_CLOUD: Final[str] = "AzurePublicCloud"
RESILIENCY_TRANSIENT_HTTP_CODES: Final[frozenset[int]] = frozenset({408, 429, 500, 502, 503, 504})
ATTACHMENT_MAX_FILES_PER_REQUEST: Final[int] = 10
ATTACHMENT_MAX_RAW_BYTES_PER_FILE: Final[int] = 1434 * 1024  # 1,468,416 bytes
ATTACHMENT_ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".zip",
        ".csv",
        ".json",
        ".yaml",
        ".tf",
        ".tfvars",
        ".bicep",
        ".bicepparam",
        ".md",
        ".docx",
        ".pdf",
        ".vsdx",
        ".jpeg",
        ".png",
        ".svg",
    }
)
WINDOWS_RESERVED_DEVICE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CLOCK$",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)
_URI_SCHEME_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
_ENV_VAR_RE: Final[re.Pattern[str]] = re.compile(r"(^|[\\/])(%[^%]+%|\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*)")
_INVALID_FILENAME_CHARS: Final[frozenset[str]] = frozenset('<>:"/\\|?*\x00')


@dataclass
class DataBoundaryResolverContract:
    """Models Azure MCP ResiliencyAgent DataBoundaryResolver (DataBoundaryResolver.cs)."""

    cloud_type: str = RESILIENCY_PUBLIC_CLOUD
    _cached_boundary: str | None = None
    arm_calls: int = 0

    def resolve(self, responses: Sequence[tuple[int, str]]) -> str:
        if self.cloud_type != RESILIENCY_PUBLIC_CLOUD:
            raise ContractViolationError(
                f"The Azure Resiliency Agent is currently supported only in Azure public cloud. "
                f"The configured cloud '{self.cloud_type}' is not supported."
            )
        if self._cached_boundary is not None:
            return self._cached_boundary

        max_attempts = min(3, len(responses))
        for attempt in range(1, max_attempts + 1):
            self.arm_calls += 1
            status_code, body = responses[attempt - 1]
            if 200 <= status_code <= 299:
                try:
                    doc = json.loads(body)
                    props = doc["properties"]
                    boundary = props["dataBoundary"]
                    if not isinstance(boundary, str):
                        boundary = None
                except (ValueError, KeyError, TypeError):
                    break

                upper = boundary.upper() if boundary is not None else ""
                if upper == "EU":
                    self._cached_boundary = "eu"
                    return self._cached_boundary
                if upper == "GLOBAL":
                    self._cached_boundary = "row"
                    return self._cached_boundary
                # Unsupported value fails closed immediately without retry
                break

            if status_code not in RESILIENCY_TRANSIENT_HTTP_CODES or attempt == 3:
                break

        raise ContractViolationError("The Azure Resiliency Agent could not prepare this request. Try again.")


@dataclass(frozen=True)
class LocalAttachmentSnapshot:
    canonical_path: str
    file_name: str
    size_bytes: int
    sha256: str


def validate_and_snapshot_local_attachment(
    untrusted_path: str,
    *,
    is_directory: bool = False,
    is_reparse_point: bool = False,
    initial_size: int,
    read_bytes: bytes,
    post_read_size: int | None = None,
    mtime_changed_during_read: bool = False,
) -> LocalAttachmentSnapshot:
    """Models LocalFileSnapshotter.Validate + SnapshotAsync (LocalFileSnapshotter.cs)."""
    if not untrusted_path or not untrusted_path.strip() or any(c in untrusted_path for c in ("\x00", "\r", "\n")):
        raise ContractViolationError("A valid file path is required.")
    if any(c in untrusted_path for c in ("*", "?")) or untrusted_path.startswith("~") or _ENV_VAR_RE.search(untrusted_path):
        raise ContractViolationError("Wildcards and environment-variable expansion are not supported.")
    if _URI_SCHEME_RE.match(untrusted_path):
        raise ContractViolationError("URLs cannot be attached.")
    if untrusted_path.startswith("\\\\") or untrusted_path.startswith("//"):
        raise ContractViolationError("Network or UNC paths cannot be attached.")
    if not untrusted_path.startswith("/") and not (
        len(untrusted_path) >= 3 and untrusted_path[0].isalpha() and untrusted_path[1] == ":" and untrusted_path[2] in ("/", "\\")
    ):
        raise ContractViolationError("Provide a fully-qualified local file path.")

    normalized_sep = untrusted_path.replace("\\", "/")
    components = [c for c in normalized_sep.split("/") if c]
    if any(c in (".", "..") for c in components):
        raise ContractViolationError("Dot path components are not supported.")
    for comp in components[1:] if len(untrusted_path) >= 2 and untrusted_path[1] == ":" else components:
        stem = comp.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED_DEVICE_NAMES:
            raise ContractViolationError("The path contains a reserved Windows device name.")

    if is_directory:
        raise ContractViolationError("Directories cannot be attached.")
    if is_reparse_point:
        raise ContractViolationError("Symbolic links, junctions, and other reparse points cannot be attached.")

    file_name = components[-1]
    dot_idx = file_name.rfind(".")
    extension = file_name[dot_idx:].lower() if dot_idx >= 0 else ""
    if extension not in ATTACHMENT_ALLOWED_EXTENSIONS:
        raise ContractViolationError(f"Files with extension '{extension}' are not supported.")
    if initial_size <= 0:
        raise ContractViolationError("Empty files cannot be attached.")
    if initial_size > ATTACHMENT_MAX_RAW_BYTES_PER_FILE:
        raise ContractViolationError(
            f"The selected file is {initial_size} bytes; the maximum is {ATTACHMENT_MAX_RAW_BYTES_PER_FILE} bytes."
        )

    effective_post_size = len(read_bytes) if post_read_size is None else post_read_size
    if (
        len(read_bytes) != initial_size
        or effective_post_size != initial_size
        or mtime_changed_during_read
    ):
        raise ContractViolationError("The selected file changed while it was being read. Try again.")

    return LocalAttachmentSnapshot(
        canonical_path=normalized_sep,
        file_name=file_name,
        size_bytes=len(read_bytes),
        sha256=hashlib.sha256(read_bytes).hexdigest(),
    )


def sanitize_resiliency_artifact_filename(
    untrusted_name: str | None,
    *,
    artifact_format: str | None = None,
    mime_type: str | None = None,
    existing_names: set[str] | None = None,
) -> str | None:
    """Models ArtifactWriter.SafeFileName + EnsureUsefulExtension + WriteUniqueFile (ArtifactWriter.cs)."""
    if untrusted_name is None or not untrusted_name.strip():
        return None
    trimmed = untrusted_name.strip()
    last_sep = max(trimmed.rfind("/"), trimmed.rfind("\\"))
    candidate = trimmed[last_sep + 1 :] if last_sep >= 0 else trimmed
    if not candidate or not candidate.strip() or candidate in (".", ".."):
        return None

    # NormalizeWhitespace: collapse whitespace runs to '-' and trim '-', '.', ' '
    ws_parts: list[str] = []
    ws_run = False
    for ch in candidate:
        if ch.isspace():
            if not ws_run and ws_parts:
                ws_parts.append("-")
            ws_run = True
        else:
            ws_parts.append(ch)
            ws_run = False
    candidate = "".join(ws_parts).strip("-. ")

    cleaned_chars = ["_" if (ch in _INVALID_FILENAME_CHARS or ord(ch) < 32) else ch for ch in candidate]
    cleaned = "".join(cleaned_chars).strip("-. ")
    if not cleaned:
        return None

    dot_idx = cleaned.rfind(".")
    ext = cleaned[dot_idx:] if dot_idx > 0 else ""
    stem = cleaned[:dot_idx] if dot_idx > 0 else cleaned

    target_ext: str | None = None
    fmt = (artifact_format or "").lower()
    mime = (mime_type or "").lower()
    if fmt == "bicep":
        target_ext = ".bicep"
    elif fmt == "arm":
        target_ext = ".json"
    elif fmt == "terraform":
        target_ext = ".tf"
    elif mime == "text/markdown":
        target_ext = ".md"

    if target_ext is not None and ext.lower() != target_ext:
        if ext == "" or ext.lower() in (".txt", ".json", ".md"):
            cleaned = f"{stem}{target_ext}"
            ext = target_ext

    if existing_names is None:
        return cleaned

    used_lower = {n.lower() for n in existing_names}
    dot_idx2 = cleaned.rfind(".")
    final_stem = cleaned[:dot_idx2] if dot_idx2 > 0 else cleaned
    final_ext = cleaned[dot_idx2:] if dot_idx2 > 0 else ""
    suffix = 1
    while True:
        unique_candidate = cleaned if suffix == 1 else f"{final_stem}-{suffix}{final_ext}"
        if unique_candidate.lower() not in used_lower:
            existing_names.add(unique_candidate)
            return unique_candidate
        suffix += 1


# ============================================================================
# 2. Microsoft Agent Framework (Python) — Redis Scope Token NUL Framing
#    (9b72ed4f96bca2be463468fadeeed28de07514c9) & Agent-Triggered Compaction
#    (c2a8f91b3070596c30723f74f303a124332bbb77)
# ============================================================================

MAF_REDIS_SCOPE_VERSION: Final[int] = 1
MAF_REDIS_SCOPE_NUL_SEPARATOR: Final[str] = "\x00"
MAF_REDIS_SCOPE_FIELDS: Final[tuple[str, ...]] = (
    "application_id",
    "agent_id",
    "user_id",
    "thread_id",
    "conversation_id",
)
MAF_COMPACTION_TRIGGER_CONSUMED_KEY: Final[str] = "_agent_compaction_trigger_consumed"


def compute_maf_redis_scope_token(name: str, value: str) -> str:
    """Models _scope_token(name, value) in agent_framework_redis/_context_provider.py."""
    if name not in MAF_REDIS_SCOPE_FIELDS:
        raise ContractViolationError(f"Unsupported Redis context scope field: {name}")
    payload = (
        f"agent-framework:redis-context:v{MAF_REDIS_SCOPE_VERSION}:{name}"
        f"{MAF_REDIS_SCOPE_NUL_SEPARATOR}{value}"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_maf_redis_scope_filter(
    *,
    application_id: str | None = None,
    agent_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, str]:
    """Models RedisContextProvider._validate_filters + _build_filter_from_dict."""
    if not (application_id or agent_id or user_id):
        raise ContractViolationError(
            "At least one of the filters: agent_id, user_id, or application_id is required."
        )
    raw = {
        "application_id": application_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "thread_id": session_id,
        "conversation_id": session_id,
    }
    out: dict[str, str] = {}
    for field_name, val in raw.items():
        if val:
            tag_field = f"af_scope_v{MAF_REDIS_SCOPE_VERSION}_{field_name}"
            out[tag_field] = compute_maf_redis_scope_token(field_name, val)
    return out


@dataclass
class CompactionMessageGroup:
    group_id: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    excluded: bool = False


def evaluate_maf_agent_triggered_compaction(
    groups: Sequence[CompactionMessageGroup],
    *,
    trigger_tool_name: str = "compact_context",
    stores_by_default: bool = False,
    store_option: bool | None = None,
    service_conversation_id: str | None = None,
    is_local_conversation_id: bool = False,
    exclude_trigger: bool = False,
    wrapped_strategy: Callable[[list[CompactionMessageGroup]], bool],
) -> bool:
    """Models _prepare_messages_for_model_call & AgentTriggeredCompactionStrategy.__call__."""
    service_stores_history = stores_by_default if store_option is None else (store_option is not False)
    has_service_conversation = bool(
        service_conversation_id and not is_local_conversation_id
    )
    if service_stores_history or has_service_conversation:
        raise ContractViolationError(
            "Agent-triggered compaction requires client-managed history. "
            "Set store=False and do not use a service-managed continuation option."
        )

    included = [g for g in groups if not g.excluded]
    if not included:
        return False
    latest_group = included[-1]
    unconsumed_triggers = [
        call
        for call in latest_group.tool_calls
        if call.get("name") == trigger_tool_name
        and call.get("completed", True) is True
        and call.get(MAF_COMPACTION_TRIGGER_CONSUMED_KEY) is not True
    ]
    if not unconsumed_triggers:
        return False

    snapshot_excluded = [(g, g.excluded) for g in groups]
    latest_group.excluded = True
    working_list = list(groups)
    try:
        changed = wrapped_strategy(working_list)
    except BaseException:
        for grp, orig_excl in snapshot_excluded:
            grp.excluded = orig_excl
        raise

    for call in unconsumed_triggers:
        call[MAF_COMPACTION_TRIGGER_CONSUMED_KEY] = True

    has_unrelated_calls = any(call.get("name") != trigger_tool_name for call in latest_group.tool_calls)
    has_other_included = any((g is not latest_group) and (not g.excluded) for g in groups)
    trigger_changed = bool(exclude_trigger and (not has_unrelated_calls) and has_other_included)
    if not trigger_changed:
        latest_group.excluded = False
    return bool(changed or trigger_changed)


# ============================================================================
# 3. Google ADK Python — URL Authority Backslash & NAT64/Embedded IPv4 SSRF Guard
#    (4d0cd985faedb3c0d9e3579077de327a6ef86a52) + \Z Name Regex (e2e9336a7fde1ea6450a56629090be7bc06cae52)
# ============================================================================

ADK_ALLOWED_URL_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
ADK_BLOCKED_HOSTNAMES: Final[frozenset[str]] = frozenset({"localhost", "metadata", "metadata.goog"})
ADK_BLOCKED_SUFFIXES: Final[tuple[str, ...]] = (".localhost", ".local", ".internal", ".metadata.goog")
ADK_NAT64_WELL_KNOWN_PREFIX: Final[ipaddress.IPv6Network] = ipaddress.ip_network("64:ff9b::/96")
ADK_SKILL_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\Z")


def extract_embedded_ipv4(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """Models _embedded_ipv4 in google/adk/tools/_url_validator.py."""
    if isinstance(addr, ipaddress.IPv4Address):
        return None
    if addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    if addr.sixtofour is not None:
        return addr.sixtofour
    if addr in ADK_NAT64_WELL_KNOWN_PREFIX:
        return ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)
    packed = int(addr)
    if (packed >> 32) == 0 and (packed & 0xFFFFFFFF) not in (0, 1):
        return ipaddress.IPv4Address(packed & 0xFFFFFFFF)
    return None


def is_blocked_ip_address(addr_str: str) -> bool:
    """Models _is_blocked_address in google/adk/tools/_url_validator.py."""
    addr = ipaddress.ip_address(addr_str)
    if not addr.is_global:
        return True
    embedded = extract_embedded_ipv4(addr)
    if embedded is not None and not embedded.is_global:
        return True
    return False


def validate_adk_model_supplied_url(
    url: str,
    *,
    resolved_ips: Sequence[str] = (),
) -> str:
    """Models validate_url / _parse_request_target in google/adk/tools/_url_validator.py."""
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ADK_ALLOWED_URL_SCHEMES:
        raise ContractViolationError(f"Unsupported url scheme: {scheme}")
    if "\\" in parsed.netloc:
        raise ContractViolationError(f"Backslash in url authority: {url}")
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not hostname:
        raise ContractViolationError(f"Missing hostname in url: {url}")
    if hostname in ADK_BLOCKED_HOSTNAMES or hostname.endswith(ADK_BLOCKED_SUFFIXES):
        raise ContractViolationError(f"Blocked hostname: {hostname}")

    try:
        literal_ip = ipaddress.ip_address(hostname)
        if is_blocked_ip_address(str(literal_ip)):
            raise ContractViolationError(f"Blocked IP literal: {hostname}")
    except ValueError:
        pass

    for ip_str in resolved_ips:
        if is_blocked_ip_address(ip_str):
            raise ContractViolationError(f"Blocked resolved IP {ip_str} for host {hostname}")
    return hostname


def validate_adk_skill_kebab_name(name: str) -> str:
    """Models Frontmatter skill name validation using \\Z instead of $ (models.py)."""
    if not isinstance(name, str) or ADK_SKILL_NAME_RE.match(name) is None:
        raise ContractViolationError(f"Invalid skill name (trailing newline or non-kebab rejected): {name!r}")
    return name


# ============================================================================
# 4. NVIDIA NeMo Guardrails PreToolUse Rust Client (7d2ef097f11b98aedaab6261060d007c59b53329) &
#    OpenAI Agents Python SDK Native Queue Cancel (cd26bbbc52847845fde73b9952b51e62e2bcbdc0)
# ============================================================================

NEMO_CLIENT_OWNED_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "connection",
        "content-length",
        "content-type",
        "host",
        "keep-alive",
        "proxy-connection",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
NEMO_MAX_SERVER_MESSAGE_CHARS: Final[int] = 512


def validate_nemo_relay_hook_config(endpoint: str, headers: dict[str, str]) -> tuple[str, list[str]]:
    """Models parse_endpoint and header_map in crates/nemo-guardrails-relay-plugin/src/config.rs."""
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ContractViolationError("Endpoint must be a valid http or https URL.")
    if parsed.username or parsed.password:
        raise ContractViolationError("Endpoint URL must not embed username or password; use headers instead.")

    seen_lower: set[str] = set()
    accepted_keys: list[str] = []
    for k, v in headers.items():
        lower_k = k.strip().lower()
        if not lower_k:
            raise ContractViolationError("Header name must not be empty.")
        if lower_k in NEMO_CLIENT_OWNED_HEADERS:
            raise ContractViolationError(f"Header '{lower_k}' is client-owned and cannot be overridden.")
        if lower_k in seen_lower:
            raise ContractViolationError(f"Duplicate header '{lower_k}' is not allowed.")
        if not isinstance(v, str) or "\r" in v or "\n" in v:
            # Never echo secret header value `v` in the error message
            raise ContractViolationError(f"Invalid header value for '{lower_k}' (value redacted).")
        seen_lower.add(lower_k)
        accepted_keys.append(lower_k)

    normalized_url = endpoint if endpoint.endswith("/") else f"{endpoint}/"
    return f"{normalized_url}v1/hooks/nemo-relay", accepted_keys


def evaluate_parallel_tool_cancellation(
    *,
    function_outcomes: Sequence[str],
    queued_native_tools: Sequence[str],
    cleanup_raises_secondary_error: bool = False,
    post_invoke_wait_seconds: float = 0.1,
) -> dict[str, Any]:
    """Models OpenAI Agents Python SDK _execute_tool_plan & gather_with_cancel (#5446)."""
    executed_native: list[str] = []
    primary_error: str | None = None
    sibling_category_failure = False

    for outcome in function_outcomes:
        if outcome.startswith("ERROR:"):
            primary_error = outcome
            sibling_category_failure = True
            break

    for idx, native_call in enumerate(queued_native_tools):
        if sibling_category_failure:
            break
        executed_native.append(native_call)
        # If function fails right after first native tool started
        if idx == 0 and primary_error is not None:
            break

    # Even if a cancelled native task raises a secondary error during cleanup,
    # primary_error is preserved and secondary cleanup error is logged/suppressed.
    propagated_error = primary_error
    if propagated_error is None and cleanup_raises_secondary_error:
        propagated_error = "ERROR:secondary_cleanup"

    return {
        "sibling_category_failure": sibling_category_failure,
        "executed_native_tools": executed_native,
        "propagated_error": propagated_error,
        "cancelled_children_timeout_seconds": round(2.0 * post_invoke_wait_seconds, 4),
    }


# ============================================================================
# 5. OpenAI Codex — Guardian V3 Local SQLite Board (bca6cff1e140c1791975f0f6c47cb3add4f31710),
#    Deferred Transcript Truncation (83a9600acbc902ab8b212ab2e5166d7d55a2519d), &
#    Config-Server Auth Decoupling (ec513795a6a727b32f906a2aa27f7fc92a996b6f)
# ============================================================================

GUARDIAN_NAMESPACE_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_-]{1,64}\Z")
GUARDIAN_MIN_RECENT_TOOL_ENTRIES: Final[int] = 5


@dataclass
class GuardianLocalBoardContract:
    """Models Codex Guardian V3 LocalBoard + LocalBoardConnection (bca6cff1e140c1791975f0f6c47cb3add4f31710)."""

    root_session_id: str
    canonical_db_path: str
    namespace: str = "guardian"
    deleted: bool = False
    channels: set[str] = field(default_factory=set)
    posts: list[tuple[str, str]] = field(default_factory=list)
    subscriptions: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if GUARDIAN_NAMESPACE_RE.match(self.namespace) is None:
            raise ContractViolationError(f"Invalid storage namespace: {self.namespace!r}")

    @property
    def database_filename(self) -> str:
        if self.namespace == "default":
            return "agent_message_board_1.sqlite"
        return f"message_board_{self.namespace}_1.sqlite"

    def verify_canonical_path(self, observed_canonical_path: str) -> None:
        if observed_canonical_path != self.canonical_db_path:
            raise ContractViolationError("board database changed; create a new board connection")

    def _ensure_not_deleted(self) -> None:
        if self.deleted:
            raise ContractViolationError("the message board's root has been permanently deleted")

    def execute_action(
        self,
        *,
        access_mode: str,
        caller_agent: str,
        action: str,
        channel: str = "general",
        content: str = "",
        target_agent: str | None = None,
    ) -> str:
        self._ensure_not_deleted()
        is_read_only = access_mode == "ReadOnly"

        if action == "create_channel":
            if is_read_only:
                raise ContractViolationError("PermissionDenied: This board connection is read-only (board.create_channel)")
            self.channels.add(channel)
            return f"channel:{channel}"

        if action == "post":
            if is_read_only:
                raise ContractViolationError("PermissionDenied: This board connection is read-only (channel.post)")
            if len(content.encode("utf-8")) > 64 * 1024:
                raise ContractViolationError("Post exceeds MAX_POST_BYTES (65536)")
            self.posts.append((channel, content))
            return f"post:{len(self.posts)}"

        if action == "set_subscription":
            effective_target = caller_agent if target_agent is None else target_agent
            if effective_target != caller_agent and is_read_only:
                raise ContractViolationError(
                    "PermissionDenied: This board connection is read-only (board.manage_subscriptions)"
                )
            self.subscriptions.setdefault(effective_target, set()).add(channel)
            return f"subscribed:{effective_target}->{channel}"

        if action == "delete_board":
            if is_read_only:
                raise ContractViolationError("PermissionDenied: This board connection is read-only (board.delete)")
            self.deleted = True
            self.channels.clear()
            self.posts.clear()
            self.subscriptions.clear()
            return "deleted_tombstone_recorded"

        raise ContractViolationError(f"Unsupported board action: {action}")


@dataclass(frozen=True)
class GuardianTranscriptEntry:
    kind: str  # "User", "Assistant", "ToolCall", "ToolOutput", "NodeReplToolOutput"
    text: str
    original_bytes: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "original_bytes", len(self.text.encode("utf-8")))


@dataclass(frozen=True)
class PreparedGuardianEntry:
    kind: str
    retained_text: str
    original_bytes: int
    retained_bytes: int
    truncated: bool
    retention: str  # "Required" or "Optional"


def prepare_guardian_sync_transcript(
    entries: Sequence[GuardianTranscriptEntry],
    *,
    entry_number_offset: int = 0,
    tool_byte_limit: int = 1000,
    node_repl_byte_limit: int = 400,
    message_byte_limit: int = 2000,
) -> list[PreparedGuardianEntry]:
    """Models Codex Guardian deferred truncation (83a9600acbc902ab8b212ab2e5166d7d55a2519d)."""
    if entry_number_offset < 0 or entry_number_offset > len(entries):
        raise ContractViolationError("Invalid entry_number_offset cursor")
    sliced = list(entries[entry_number_offset:])

    tool_indices = [
        idx
        for idx, e in enumerate(sliced)
        if e.kind in ("ToolCall", "ToolOutput", "NodeReplToolOutput")
    ]
    required_tool_indices = set(tool_indices[-GUARDIAN_MIN_RECENT_TOOL_ENTRIES:])

    prepared: list[PreparedGuardianEntry] = []
    for idx, entry in enumerate(sliced):
        raw_bytes = entry.text.encode("utf-8")
        if entry.kind == "User":
            limit = len(raw_bytes)
        elif entry.kind == "NodeReplToolOutput":
            limit = node_repl_byte_limit
        elif entry.kind in ("ToolCall", "ToolOutput"):
            limit = tool_byte_limit
        else:
            limit = message_byte_limit

        retained_raw = raw_bytes[:limit]
        retained_text = retained_raw.decode("utf-8", errors="ignore")
        retained_len = len(retained_text.encode("utf-8"))
        is_req = (
            entry.kind == "User"
            or idx in required_tool_indices
        )
        prepared.append(
            PreparedGuardianEntry(
                kind=entry.kind,
                retained_text=retained_text,
                original_bytes=entry.original_bytes,
                retained_bytes=retained_len,
                truncated=entry.original_bytes > retained_len,
                retention="Required" if is_req else "Optional",
            )
        )
    return prepared


@dataclass
class CodexConfigServerLifecycleContract:
    """Models Codex Config-Server OAuth vs Model Auth decoupling (ec513795) + Code-Mode Host (5fdb50af)."""

    config_server_enabled: bool
    enterprise_bundle_active: bool = True
    refresh_worker_alive: bool = True
    mcp_ema_token_cached: bool = True
    code_mode_host_alive: bool = True

    def on_model_credential_switch_or_logout(self) -> dict[str, bool]:
        if self.config_server_enabled:
            # Only revoke MCP EMA token; keep enterprise config bundle & refresh worker alive
            self.mcp_ema_token_cached = False
        else:
            self.mcp_ema_token_cached = False
            self.enterprise_bundle_active = False
            self.refresh_worker_alive = False
        return {
            "enterprise_bundle_active": self.enterprise_bundle_active,
            "refresh_worker_alive": self.refresh_worker_alive,
            "mcp_ema_token_cached": self.mcp_ema_token_cached,
        }

    def dispatch_code_mode_rpc(self, *, phase: str) -> str:
        """Models Restrict code-mode host replacement to session admission (5fdb50af)."""
        if self.code_mode_host_alive:
            return "rpc_ok"
        if phase == "OpenSession":
            self.code_mode_host_alive = True
            return "host_replaced_at_session_admission"
        raise ContractViolationError(
            "Unavailable: code-mode host process exited mid-session; replacement forbidden outside OpenSession"
        )


# ============================================================================
# 6. Anthropic Claude Code — mods/sec-default Two-Pass Verdict & 19 Pinned Env Vars
#    (a5b0f2e03aba37ea34e527fe30b2f6aaa4895b9f) + Planning-with-Files Subagent Isolation
#    (5d29800bf8b919ca9a88ee7885b90050b5cb64ed)
# ============================================================================

CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS: Final[frozenset[str]] = frozenset(
    {
        # 9 Policy & auth source variables
        "CLAUDE_CODE_MANAGED_SETTINGS_PATH",
        "CLAUDE_CODE_REMOTE_SETTINGS_PATH",
        "CLAUDE_CODE_DISABLE_ADMIN_ENV_UNION",
        "CLAUDE_CODE_MOCK_REMOTE_SETTINGS",
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_SECURESTORAGE_CONFIG_DIR",
        "USE_LOCAL_OAUTH",
        "USE_STAGING_OAUTH",
        "CLAUDE_LOCAL_OAUTH_API_BASE",
        # 10 Code-loading & shell startup variables
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
_VERDICT_STRICTNESS: Final[dict[str, int]] = {"allow": 0, "ask": 1, "deny": 2}
_PROTECTED_VERDICT_SOURCES: Final[frozenset[str]] = frozenset({"rule", "hook", "setting", "plugin", "ceiling"})
_PWF_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


@dataclass(frozen=True)
class SecDefaultVerdict:
    decision: str  # "allow", "ask", "deny"
    source_kind: str | None = None
    approver: str | None = None
    reason: str = ""


def evaluate_claude_sec_default_two_pass(
    *,
    full_chain_verdict: SecDefaultVerdict,
    user_layer_rewrote: bool,
    append_only_verdict: SecDefaultVerdict,
    allow_mods_to_override_deny_rules: bool = False,
) -> tuple[SecDefaultVerdict, bool]:
    """Models mods/sec-default register.ts & holds-over.ts two-pass execution."""
    if not user_layer_rewrote or allow_mods_to_override_deny_rules:
        return full_chain_verdict, False

    held = append_only_verdict
    protected_hold = (
        held.decision == "deny"
        or (held.source_kind in _PROTECTED_VERDICT_SOURCES)
        or (held.decision == "ask" and held.approver == "host")
    )
    if not protected_hold:
        return full_chain_verdict, True

    held_rank = _VERDICT_STRICTNESS.get(held.decision, 2)
    ans_rank = _VERDICT_STRICTNESS.get(full_chain_verdict.decision, 0)
    loosened_or_reworded = (ans_rank < held_rank) or (
        ans_rank == held_rank and full_chain_verdict.reason != held.reason
    )
    if loosened_or_reworded:
        return held, True
    return full_chain_verdict, True


def check_claude_sec_default_env_set(
    var_name: str,
    *,
    managed_env_keys: Sequence[str] = (),
    has_process_wrapper: bool = False,
    policy_read_failed: bool = False,
) -> None:
    """Models mods/sec-default/hooks/policy/pinned-names.ts."""
    if policy_read_failed:
        raise ContractViolationError("Refused env.set: managed policy read failed (fail-closed).")
    upper = var_name.strip().upper()
    managed_upper = {k.upper() for k in managed_env_keys}
    if (
        upper in CLAUDE_SEC_DEFAULT_PINNED_ENV_VARS
        or upper in managed_upper
        or (has_process_wrapper and upper == "CLAUDE_CODE_PROCESS_WRAPPER")
    ):
        raise ContractViolationError(f"Refused env.set on pinned security variable: {upper}")


def evaluate_pwf_subagent_hook_gate(
    raw_stdin_json: str,
    *,
    skip_subagents: bool = True,
) -> tuple[str, str]:
    """Models OthmanAdi/planning-with-files v3.26.0 hook_is_main & hook_identity (inject-plan.py)."""
    try:
        payload = json.loads(raw_stdin_json)
    except ValueError:
        return ("skip", "!invalid")
    if not isinstance(payload, dict):
        return ("skip", "!invalid")

    agent_id = payload.get("agent_id")
    prompt_id = payload.get("prompt_id")

    if agent_id is not None:
        if not isinstance(agent_id, str) or _PWF_ID_RE.match(agent_id) is None:
            return ("skip", "!invalid")
        if prompt_id is not None and (not isinstance(prompt_id, str) or _PWF_ID_RE.match(prompt_id) is None):
            return ("skip", "!invalid")
        if skip_subagents:
            return ("skip", agent_id)
        return ("run_subagent", agent_id)

    return ("run_main", "main")
