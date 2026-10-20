"""Offline stdlib reference contracts and recorded-trace replay grader (2026-10-21).

Scope boundary:
- Original Python 3.11+ standard-library reference specification across 6 mechanism groups
  plus a deterministic replay grader for OpenAI Cookbook `harness_aware_plugin_evals`
  (`5bd6cb40b6b84b69b2032d810610aa85064102df`).
- Contains zero `assert` statements so behavior is identical under `python3 -B` and `python3 -B -O`.
- Upstream product runtimes (GitHub Copilot CLI/SDK, MAF ASP.NET Core, Google ADK VMaaS,
  MCP TypeScript SDK, OpenAI Codex CLI/App Server, Anthropic Claude Code CLI) are NOT_RUN.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple


class BusinessOracleFailure(AssertionError):
    """Explicit business-oracle failure used by baseline tests and mutation calibration."""


# ============================================================================
# 1. GitHub Copilot SDK: permissions.limitTo & pre-MCP sandboxConfig
#    Sources: 20d75a718bf40d856525b0c33713c553371af1ab, 51e9556d2607f00f9f72038fa16accfe2f5d150d
# ============================================================================

_DOMAIN_RULE_RE = re.compile(r"^Domain\(([^()]+)\)$")
_HOSTNAME_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


def parse_domain_rule(rule: str) -> Tuple[str, str]:
    """Parse a Copilot SDK `Domain(...)` rule into (`kind`, `normalized_value`).

    Rejects schemes, ports, paths, queries, fragments, whitespace, or bare `*`.
    Returns kind in {"ip", "wildcard", "exact"}.
    """
    if not isinstance(rule, str):
        raise ValueError("limitTo rule must be a string")
    match = _DOMAIN_RULE_RE.match(rule)
    if match is None:
        raise ValueError(f"invalid limitTo rule syntax: {rule!r}")
    inner = match.group(1)
    if not inner or any(ch.isspace() for ch in inner):
        raise ValueError(f"empty or whitespace domain rule: {rule!r}")
    if any(sep in inner for sep in ("/", ":", "?", "#", "@", "\\")):
        raise ValueError(f"scheme, port, path, query, or userinfo forbidden in limitTo: {rule!r}")

    if inner.startswith("*."):
        suffix = inner[2:].lower()
        labels = suffix.split(".")
        if len(labels) < 2 or any(not _HOSTNAME_LABEL_RE.match(lbl) for lbl in labels):
            raise ValueError(f"invalid wildcard domain rule: {rule!r}")
        return ("wildcard", suffix)

    if "*" in inner:
        raise ValueError(f"wildcard only allowed as leading '*.': {rule!r}")

    try:
        ip_obj = ipaddress.ip_address(inner)
        return ("ip", str(ip_obj))
    except ValueError:
        pass

    lowered = inner.lower()
    labels = lowered.split(".")
    if any(not _HOSTNAME_LABEL_RE.match(lbl) for lbl in labels):
        raise ValueError(f"invalid hostname in limitTo rule: {rule!r}")
    return ("exact", lowered)


def _host_matches_single_layer(host: str, layer_rules: Sequence[str]) -> bool:
    if not isinstance(host, str) or not host.strip():
        return False
    normalized_host = host.strip().lower()
    parsed_rules = [parse_domain_rule(r) for r in layer_rules]
    for kind, target in parsed_rules:
        if kind in ("ip", "exact") and normalized_host == target:
            return True
        if kind == "wildcard":
            if normalized_host.endswith("." + target) and normalized_host != target:
                return True
    return False


def evaluate_copilot_limit_to(
    layers: Sequence[Optional[Sequence[str]]],
    candidate_host: str,
    *,
    _mutation: Optional[str] = None,
) -> bool:
    """Evaluate multi-layer `managedSettings.permissions.limitTo` intersection semantics.

    - `None` layer means that layer does not restrict outbound hosts.
    - Explicit empty sequence `[]` means that layer denies ALL outbound hosts.
    - When multiple non-None layers exist, candidate_host must satisfy EVERY active layer (intersection).
    """
    for layer in layers:
        if layer is not None:
            for r in layer:
                parse_domain_rule(r)

    active_layers = [list(layer) for layer in layers if layer is not None]
    if not active_layers:
        return True

    for layer in active_layers:
        if len(layer) == 0:
            if _mutation == "M1_copilot_empty_limit_to_allows_all":
                continue
            return False
        if not _host_matches_single_layer(candidate_host, layer):
            return False
    return True


@dataclass(frozen=True)
class CopilotSessionSandboxOutcome:
    effective_sandbox: Optional[Dict[str, Any]]
    mcp_started_under_sandbox: bool
    mcp_restarted: bool


def evaluate_copilot_session_sandbox(
    *,
    mode: str,
    requested_sandbox: Optional[Dict[str, Any]],
    managed_conflict: bool = False,
    resident_sandbox: Optional[Dict[str, Any]] = None,
) -> CopilotSessionSandboxOutcome:
    """Model pre-MCP `sandboxConfig` injection on `create`, `cold_resume`, `resident_resume`, and `update`."""
    if managed_conflict and requested_sandbox is not None:
        raise RuntimeError("JSON-RPC error data.code=managed_sandbox_policy_conflict")

    if mode == "create" or mode == "cold_resume":
        effective = copy.deepcopy(requested_sandbox)
        confined = bool(effective and effective.get("enabled") and effective.get("sandboxMcpServers"))
        return CopilotSessionSandboxOutcome(
            effective_sandbox=effective,
            mcp_started_under_sandbox=confined,
            mcp_restarted=False,
        )

    if mode == "resident_resume":
        effective = copy.deepcopy(resident_sandbox if requested_sandbox is None else requested_sandbox)
        confined = bool(effective and effective.get("enabled") and effective.get("sandboxMcpServers"))
        return CopilotSessionSandboxOutcome(
            effective_sandbox=effective,
            mcp_started_under_sandbox=confined,
            mcp_restarted=False,
        )

    if mode == "update":
        if requested_sandbox is None or requested_sandbox == resident_sandbox:
            effective = copy.deepcopy(resident_sandbox)
            confined = bool(effective and effective.get("enabled") and effective.get("sandboxMcpServers"))
            return CopilotSessionSandboxOutcome(
                effective_sandbox=effective,
                mcp_started_under_sandbox=confined,
                mcp_restarted=False,
            )
        effective = copy.deepcopy(requested_sandbox)
        confined = bool(effective and effective.get("enabled") and effective.get("sandboxMcpServers"))
        return CopilotSessionSandboxOutcome(
            effective_sandbox=effective,
            mcp_started_under_sandbox=confined,
            mcp_restarted=True,
        )

    raise ValueError(f"unsupported session mode: {mode!r}")


# ============================================================================
# 2. Microsoft Agent Framework (.NET): HostedAgentResolution & Duplicate Approval IDs
#    Sources: 30bc5c1bd0159f3a96353c9b98a118dc53cc9f6d, 8ab068b8b360369d6425cc50603eeba07207a9d1
# ============================================================================

@dataclass
class AgentInstance:
    name: str
    instance_id: int


class HostedAgentEndpointSimulator:
    """Models MAF .NET `MapAGUIServer` lifetime resolution and selector 404 before session store load."""

    def __init__(
        self,
        lifetime: str,
        registered_name: Optional[str],
        factory: Optional[Callable[[Dict[str, Any]], Optional[AgentInstance]]] = None,
    ) -> None:
        if lifetime not in ("Singleton", "Scoped", "Transient", "Selector"):
            raise ValueError(f"invalid lifetime: {lifetime!r}")
        self.lifetime = lifetime
        self.registered_name = registered_name
        self._counter = 0
        self.store_load_calls = 0
        self._singleton_instance: Optional[AgentInstance] = None
        self._selector = factory

        if lifetime in ("Singleton", "Scoped", "Transient"):
            if not registered_name or not registered_name.strip():
                raise KeyError("Keyed AIAgent registration missing at endpoint mapping time")
            if lifetime == "Singleton":
                self._counter += 1
                self._singleton_instance = AgentInstance(name=registered_name, instance_id=self._counter)

    def handle_request(self, request_context: Dict[str, Any]) -> Tuple[int, Optional[Dict[str, Any]]]:
        if self.lifetime == "Selector":
            if self._selector is None:
                raise RuntimeError("selector not configured")
            selected = self._selector(request_context)
            if selected is None:
                return (404, None)
            if not isinstance(selected.name, str) or not selected.name.strip():
                raise ValueError("InvalidOperationException: Selected AIAgent.Name must not be null or whitespace.")
            agent = selected
            storage_identity = selected.name
        elif self.lifetime == "Singleton":
            if self._singleton_instance is None:
                raise RuntimeError("singleton not initialized")
            agent = self._singleton_instance
            storage_identity = self.registered_name or agent.name
        else:
            self._counter += 1
            reg_name = self.registered_name or ""
            agent = AgentInstance(name=reg_name, instance_id=self._counter)
            storage_identity = reg_name

        self.store_load_calls += 1
        return (
            200,
            {
                "agent_instance_id": agent.instance_id,
                "session_storage_identity": storage_identity,
                "store_load_calls": self.store_load_calls,
            },
        )


@dataclass
class ToolApprovalState:
    surfaced_approval_requests: Dict[str, str] = field(default_factory=dict)
    queued_approval_requests: List[Tuple[str, str]] = field(default_factory=list)
    collected_approval_responses: List[Tuple[str, bool]] = field(default_factory=list)
    saved_snapshots: int = 0


def ensure_approval_request_ids_unique(
    requests: Sequence[Tuple[str, str]],
    state: ToolApprovalState,
    *,
    include_surfaced_requests: bool,
    _mutation: Optional[str] = None,
) -> None:
    """Model `ToolApprovalAgent.EnsureRequestIdsUnique` (`8ab068b8`).

    - Checks duplicates within `requests` and optionally against `state.surfaced_approval_requests`.
    - When any duplicate ID is found, purges all colliding IDs from `surfaced_approval_requests`,
      `queued_approval_requests`, and `collected_approval_responses`, increments `saved_snapshots`,
      and raises `ValueError` ("InvalidOperationException: Tool approval request IDs ... were used more than once.").
    """
    if not requests:
        return

    known_ids: Set[str] = set()
    if include_surfaced_requests:
        known_ids.update(state.surfaced_approval_requests.keys())

    duplicate_ids: Set[str] = set()
    for req_id, _tool_name in requests:
        if req_id in known_ids:
            duplicate_ids.add(req_id)
        else:
            known_ids.add(req_id)

    if not duplicate_ids:
        for req_id, tool_name in requests:
            state.surfaced_approval_requests[req_id] = tool_name
            state.queued_approval_requests.append((req_id, tool_name))
        state.saved_snapshots += 1
        return

    if _mutation != "M2_maf_duplicate_approval_skips_state_purge":
        for dup_id in duplicate_ids:
            state.surfaced_approval_requests.pop(dup_id, None)
            state.queued_approval_requests = [
                item for item in state.queued_approval_requests if item[0] != dup_id
            ]
            state.collected_approval_responses = [
                item for item in state.collected_approval_responses if item[0] != dup_id
            ]
        state.saved_snapshots += 1

    sorted_dups = "', '".join(sorted(duplicate_ids))
    raise ValueError(
        f"InvalidOperationException: Tool approval request IDs '{sorted_dups}' were used more than once."
    )


# ============================================================================
# 3. Google ADK Python: VMaaS Sandbox At-Most-Once Execution Guard
#    Source: 019b2b21f9b68a344efd6b92f4f7a40a7c6e273b
# ============================================================================

@dataclass
class SandboxAPIError(Exception):
    code: int
    status: str
    message: str


@dataclass(frozen=True)
class SandboxExecutionResult:
    exit_code: int
    timed_out: bool
    stdout: str = ""
    attempts: int = 0
    resume_calls: int = 0


def is_vmaas_timeout(err: SandboxAPIError) -> bool:
    return (
        err.code == 504
        or err.status == "DEADLINE_EXCEEDED"
        or "DEADLINE_EXCEEDED" in (err.message or "")
    )


def is_vmaas_unreachable(err: SandboxAPIError) -> bool:
    return "Unable to reach the sandbox environment" in (err.message or "")


def execute_vmaas_sandbox_command(
    scripted_steps: Sequence[Tuple[str, Any]],
    *,
    max_unreachable_retries: int = 3,
    _mutation: Optional[str] = None,
) -> SandboxExecutionResult:
    """Model `AgentEngineEnvironment.execute` and `_execute_bash` (`019b2b21`).

    `scripted_steps` is a sequence of `(sandbox_state, outcome)` where `outcome` is either
    a stdout string or a `SandboxAPIError`.
    """
    attempts = 0
    resume_calls = 0
    resumed = False
    unreachable_retries = 0
    idx = 0

    while True:
        if idx >= len(scripted_steps):
            raise RuntimeError("scripted_steps exhausted without terminal outcome")
        sandbox_state, outcome = scripted_steps[idx]
        idx += 1
        attempts += 1

        if not isinstance(outcome, SandboxAPIError):
            return SandboxExecutionResult(
                exit_code=0,
                timed_out=False,
                stdout=str(outcome),
                attempts=attempts,
                resume_calls=resume_calls,
            )

        err = outcome
        if is_vmaas_timeout(err) and _mutation != "M3_adk_vmaas_retries_running_failed_precondition":
            return SandboxExecutionResult(
                exit_code=-1,
                timed_out=True,
                stdout="",
                attempts=attempts,
                resume_calls=resume_calls,
            )

        if is_vmaas_unreachable(err):
            if unreachable_retries < max_unreachable_retries:
                unreachable_retries += 1
                continue
            raise err

        if resumed or (err.code != 503 and err.status != "FAILED_PRECONDITION"):
            raise err

        if sandbox_state == "STATE_RUNNING" and _mutation != "M3_adk_vmaas_retries_running_failed_precondition":
            raise err

        resume_calls += 1
        resumed = True
        unreachable_retries = 0


# ============================================================================
# 4. MCP TypeScript SDK SEP-2640 (`SkillsClient`) & Codex Frozen Cloud Skill Snapshots
#    Sources: 46d9c9921b6542e813c1ecc5f9fc964085e8e3bb, e776b27eb0422c3d10fba676c632ff08ffb4469b
# ============================================================================

class SkillVerificationError(ValueError):
    def __init__(self, check: str, uri: str, message: str, differences: Optional[List[str]] = None) -> None:
        super().__init__(message)
        self.check = check
        self.uri = uri
        self.differences = differences or []


def trim_trailing_slashes_linear(text: str) -> str:
    end = len(text)
    while end > 0 and text[end - 1] == "/":
        end -= 1
    return text[:end]


def is_within_skill_root(root_uri: str, candidate_uri: str) -> bool:
    """Model SEP-2640 `isWithin(rootUri, uri)` without regex backtracking."""
    root_clean = trim_trailing_slashes_linear(root_uri)
    if not candidate_uri.startswith(root_clean + "/"):
        return False
    rel = candidate_uri[len(root_clean) + 1 :]
    if not rel:
        return False
    for segment in rel.split("/"):
        decoded = urllib.parse.unquote(segment)
        if decoded in ("", ".", "..") or "/" in decoded or "\x00" in decoded or "\\" in decoded:
            return False
    return True


def frontmatter_differences(entry_fm: Any, parsed_fm: Any, path: str = "") -> List[str]:
    label = "(frontmatter)" if path == "" else path
    if isinstance(entry_fm, list) and isinstance(parsed_fm, list):
        if len(entry_fm) != len(parsed_fm):
            return [f"{label}: the entry has {len(entry_fm)} items, SKILL.md has {len(parsed_fm)}"]
        diffs: List[str] = []
        for idx, (a, b) in enumerate(zip(entry_fm, parsed_fm)):
            diffs.extend(frontmatter_differences(a, b, f"{path}[{idx}]"))
        return diffs
    if isinstance(entry_fm, dict) and isinstance(parsed_fm, dict):
        keys = sorted(set(entry_fm.keys()) | set(parsed_fm.keys()))
        diffs = []
        for k in keys:
            sub = k if path == "" else f"{path}.{k}"
            if k not in entry_fm:
                diffs.append(f"{sub}: the entry has nothing, SKILL.md has {json.dumps(parsed_fm[k])}")
            elif k not in parsed_fm:
                diffs.append(f"{sub}: the entry has {json.dumps(entry_fm[k])}, SKILL.md has nothing")
            else:
                diffs.extend(frontmatter_differences(entry_fm[k], parsed_fm[k], sub))
        return diffs
    if type(entry_fm) is not type(parsed_fm) or entry_fm != parsed_fm:
        return [f"{label}: the entry has {json.dumps(entry_fm)}, SKILL.md has {json.dumps(parsed_fm)}"]
    return []


def verify_and_read_sep2640_skill_file(
    skill_entry: Dict[str, Any],
    requested_ref: str,
    fetch_fn: Callable[[str, str], Tuple[bytes, Optional[Dict[str, Any]], bool]],
    *,
    _mutation: Optional[str] = None,
) -> Dict[str, Any]:
    """Model SEP-2640 `SkillsClient.read` with unlisted check, size, SHA-256, frontmatter diff, and cache refresh."""
    skill_uri = str(skill_entry["uri"])
    if not skill_uri.endswith("/SKILL.md"):
        raise TypeError(f"{skill_uri} is not a SKILL.md URI")
    root_uri = skill_uri[: -len("/SKILL.md")]
    if not root_uri or root_uri.endswith("/"):
        raise TypeError(f"invalid skill root in {skill_uri}")

    if requested_ref == "SKILL.md" or requested_ref == "":
        target_uri = skill_uri
        is_manifest = True
    elif "://" in requested_ref:
        target_uri = requested_ref.split("#", 1)[0]
        is_manifest = target_uri == skill_uri
    else:
        clean_ref = requested_ref.split("#", 1)[0].lstrip("/")
        target_uri = f"{root_uri}/{clean_ref}"
        is_manifest = target_uri == skill_uri

    if not is_manifest and not is_within_skill_root(root_uri, target_uri):
        raise SkillVerificationError("unlisted", target_uri, f"{target_uri} escapes skill root {root_uri}")

    resources = skill_entry.get("resources", [])
    listed_entry: Optional[Dict[str, Any]] = None
    if resources != "dynamic":
        for item in resources:
            if item.get("uri") == target_uri:
                listed_entry = item
                break
        if listed_entry is None:
            raise SkillVerificationError("unlisted", target_uri, f"{target_uri} is not listed in skill resources")

    def _check_payload(raw_bytes: bytes, parsed_fm: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if listed_entry is not None:
            expected_size = int(listed_entry["size"])
            if len(raw_bytes) != expected_size:
                raise SkillVerificationError(
                    "size", target_uri, f"expected {expected_size} bytes, got {len(raw_bytes)}"
                )
            digest = hashlib.sha256(raw_bytes).hexdigest()
            if digest != listed_entry["digest"]:
                raise SkillVerificationError(
                    "digest", target_uri, f"expected digest {listed_entry['digest']}, got {digest}"
                )
        if is_manifest and _mutation != "M4_mcp_skills_skip_frontmatter_diff":
            if parsed_fm is None:
                raise SkillVerificationError("frontmatter", target_uri, "missing parsed frontmatter")
            diffs = frontmatter_differences(skill_entry.get("frontmatter", {}), parsed_fm)
            if diffs:
                raise SkillVerificationError(
                    "frontmatter", target_uri, f"frontmatter mismatch: {'; '.join(diffs)}", diffs
                )
        return {
            "uri": target_uri,
            "bytes": raw_bytes,
            "verified": listed_entry is not None,
            "frontmatter": parsed_fm if is_manifest else None,
        }

    raw_bytes, parsed_fm, was_cached = fetch_fn(target_uri, "default")
    try:
        return _check_payload(raw_bytes, parsed_fm)
    except SkillVerificationError:
        if not was_cached:
            raise
        raw_bytes_2, parsed_fm_2, _ = fetch_fn(target_uri, "refresh")
        return _check_payload(raw_bytes_2, parsed_fm_2)


class FrozenCloudSkillSnapshot:
    """Model OpenAI Codex `FrozenCloudSkillProvider` (`e776b27eb0422c3d10fba676c632ff08ffb4469b`)."""

    MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
    MAX_RESOURCE_BYTES = 1024 * 1024
    REQUIRED_AUTHORITY = ("Cloud", "codex_apps")

    def __init__(
        self,
        payload_bytes: bytes,
        *,
        max_resource_bytes: int = MAX_RESOURCE_BYTES,
        _mutation: Optional[str] = None,
    ) -> None:
        if len(payload_bytes) > self.MAX_SNAPSHOT_BYTES:
            raise ValueError("skill snapshot exceeds 64 MiB")
        data = json.loads(payload_bytes.decode("utf-8"))
        if not isinstance(data, dict) or set(data.keys()) != {"skills"}:
            raise ValueError("invalid skill snapshot schema")
        self._catalog: List[Dict[str, Any]] = []
        self._resources: Dict[str, Dict[str, str]] = {}
        self._mutation = _mutation

        allowed_keys = {
            "package",
            "name",
            "description",
            "alias_root",
            "main_resource",
            "prompt_visible",
            "resources",
        }
        for skill in data["skills"]:
            if not isinstance(skill, dict) or not set(skill.keys()).issubset(allowed_keys):
                raise ValueError("unknown or invalid fields in snapshot skill")
            pkg = str(skill.get("package", ""))
            alias_root = str(skill.get("alias_root", ""))
            name = str(skill.get("name", ""))
            main_res = str(skill.get("main_resource", ""))
            res_map = skill.get("resources", {})
            prompt_visible = bool(skill.get("prompt_visible", True))

            if (
                not alias_root.startswith("skill://")
                or not is_within_skill_root(alias_root, pkg)
                or not name.strip()
                or not isinstance(res_map, dict)
                or main_res not in res_map
            ):
                raise ValueError("invalid skill package or missing main_resource")

            for r_uri, r_content in res_map.items():
                if not isinstance(r_content, str) or len(r_content.encode("utf-8")) > max_resource_bytes:
                    raise ValueError("resource exceeds size limit")
                if _mutation != "M5_codex_frozen_skill_allows_cross_package_resource":
                    if not is_within_skill_root(pkg, r_uri):
                        raise ValueError(f"resource {r_uri!r} escapes package {pkg!r}")

            if pkg in self._resources:
                raise ValueError(f"duplicate skill package: {pkg}")

            self._resources[pkg] = dict(res_map)
            self._catalog.append(
                {
                    "package": pkg,
                    "name": name,
                    "alias_root": alias_root,
                    "main_resource": main_res,
                    "prompt_visible": prompt_visible,
                    "authority": self.REQUIRED_AUTHORITY,
                }
            )

    def list_skills(self, *, include_cloud_skills: bool) -> List[Dict[str, Any]]:
        if not include_cloud_skills:
            return []
        return copy.deepcopy(self._catalog)

    def read_resource(self, authority: Tuple[str, str], package: str, resource_uri: str) -> str:
        if self._mutation != "M5_codex_frozen_skill_allows_cross_package_resource":
            if authority != self.REQUIRED_AUTHORITY:
                raise PermissionError("invalid frozen skill authority")
        pkg_map = self._resources.get(package)
        if pkg_map is None or resource_uri not in pkg_map:
            raise KeyError("unknown frozen skill resource")
        return pkg_map[resource_uri]


# ============================================================================
# 5. OpenAI Codex Auth Generation / Owner Fencing (`c6e4438a`) &
#    Anthropic Claude Code v2.1.304 `decider: "person"` + CLAUDE.md Disable Guard
#    Sources: c6e4438a5d5befe6c8e59b01b6534eb8f0792230, 772c6bee5c36f58be43bbb2b182862aeb22aceff,
#             a6e289a2e772a17b3614a9ef43303003de5cd887
# ============================================================================

@dataclass
class CodexAuthManagerModel:
    generation: int = 0
    owner_generation: int = 0
    cached_login_owner_id: Optional[str] = None
    cached_refresh_token: Optional[str] = None
    cached_access_token: Optional[str] = None

    def logout(self) -> int:
        """Invalidate cached auth and advance generation even when cache was already empty."""
        self.cached_login_owner_id = None
        self.cached_refresh_token = None
        self.cached_access_token = None
        self.generation += 1
        self.owner_generation += 1
        return self.generation

    def publish_reloaded_auth(
        self,
        read_generation: int,
        login_owner_id: str,
        refresh_token: str,
        access_token: str,
    ) -> bool:
        if read_generation != self.generation:
            return False
        self.cached_login_owner_id = login_owner_id
        self.cached_refresh_token = refresh_token
        self.cached_access_token = access_token
        self.generation += 1
        return True

    def persist_refreshed_tokens(
        self,
        *,
        expected_login_owner_id: str,
        expected_refresh_token: str,
        new_access_token: str,
        new_refresh_token: Optional[str],
    ) -> bool:
        """Persist refresh only if stored login matches, or legacy writer dropped login metadata but refresh token matches."""
        if self.cached_refresh_token is None:
            return False
        if self.cached_login_owner_id is not None:
            if self.cached_login_owner_id != expected_login_owner_id:
                return False
        else:
            if self.cached_refresh_token != expected_refresh_token:
                return False
        self.cached_access_token = new_access_token
        if new_refresh_token is not None:
            self.cached_refresh_token = new_refresh_token
        self.generation += 1
        return True


CLAUDE_MD_DISABLE_VARS: FrozenSet[str] = frozenset(
    {
        "CLAUDE_CODE_DISABLE_CLAUDE_MDS",
        "CLAUDE_CODE_SIMPLE",
        "CLAUDE_CODE_SAFE_MODE",
    }
)


def evaluate_claude_2_1_304_person_decider_and_env(
    *,
    mod_decision: str,
    mod_decider: Optional[str],
    mod_reason: str,
    interactive_dialog_available: bool,
    host_callback_available: bool,
    auto_mode_classifier_approves: bool,
    candidate_env_var: Optional[str] = None,
    _mutation: Optional[str] = None,
) -> Dict[str, Any]:
    """Model Claude Code v2.1.304 `decider: "person"` on `tool.check` and `a6e289a2` CLAUDE.md disable env boundary."""
    env_blocked = False
    if candidate_env_var is not None and candidate_env_var in CLAUDE_MD_DISABLE_VARS:
        env_blocked = True

    if mod_decision == "deny":
        return {"final_decision": "deny", "reason": mod_reason, "env_blocked": env_blocked}

    if mod_decision == "ask" and mod_decider == "person":
        if _mutation == "M7_claude_person_decider_allows_auto_classifier" and auto_mode_classifier_approves:
            return {"final_decision": "allow", "reason": "auto_mode_classifier", "env_blocked": env_blocked}
        if interactive_dialog_available or host_callback_available:
            return {"final_decision": "ask_human_or_host_callback", "reason": mod_reason, "env_blocked": env_blocked}
        return {"final_decision": "deny", "reason": mod_reason, "env_blocked": env_blocked}

    if mod_decision == "ask":
        if auto_mode_classifier_approves:
            return {"final_decision": "allow", "reason": "auto_mode_classifier", "env_blocked": env_blocked}
        if interactive_dialog_available or host_callback_available:
            return {"final_decision": "ask_human_or_host_callback", "reason": mod_reason, "env_blocked": env_blocked}
        return {"final_decision": "deny", "reason": mod_reason, "env_blocked": env_blocked}

    return {"final_decision": "allow", "reason": mod_reason, "env_blocked": env_blocked}


# ============================================================================
# 6. OpenAI Cookbook `harness_aware_plugin_evals` Recorded Trace Replay Grader
#    Source: 5bd6cb40b6b84b69b2032d810610aa85064102df
# ============================================================================

def _csv_values(value: Any) -> Set[str]:
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    return {str(item) for item in (value or [])}


def grade_cookbook_normalized_calls(
    calls: Sequence[Dict[str, Any]],
    variables: Dict[str, Any],
    answer: str,
    completed: bool,
    *,
    _mutation: Optional[str] = None,
) -> Dict[str, Any]:
    """Exact stdlib port of `eval_grading.py:grade` (`5bd6cb40`)."""
    used_tools = {str(call.get("name")) for call in calls if call.get("name")}
    expected_tools = _csv_values(variables.get("expected_tools"))
    missing_tools = sorted(expected_tools - used_tools)

    fetched_series = {
        str(series_id)
        for call in calls
        if call.get("name") == "fetch_bls_data"
        for series_id in (call.get("arguments") or {}).get("series_ids", [])
    }
    returned_series = {
        str(record.get("series_id"))
        for call in calls
        if call.get("name") == "fetch_bls_data"
        for record in (((call.get("result") or {}).get("data")) or [])
        if not record.get("error") and record.get("series_id")
    }
    expected_series = _csv_values(variables.get("expected_series_ids"))
    missing_series = sorted(expected_series - returned_series)
    if _mutation == "M6_cookbook_grader_ignores_unexpected_series":
        unexpected_series: List[str] = []
    else:
        unexpected_series = sorted(fetched_series - expected_series)

    reasons: List[str] = []
    if not completed:
        reasons.append("run did not finish before the step limit")
    if missing_tools:
        reasons.append(f"missing tools: {missing_tools}")
    if missing_series:
        reasons.append(f"no observations for: {missing_series}")
    if unexpected_series:
        reasons.append(f"fetched series outside the expectation: {unexpected_series}")
    if not (answer or "").strip():
        reasons.append("empty final answer")

    return {
        "pass": not reasons,
        "score": 0.0 if reasons else 1.0,
        "reason": "; ".join(reasons) or "expected tools called and BLS series fetched",
    }


def grade_recorded_trace_case(
    case: Dict[str, Any],
    *,
    _mutation: Optional[str] = None,
) -> Dict[str, Any]:
    """Grade one recorded case from `cookbook_recorded_traces.json` (`standalone` or `codex` mode)."""
    mode = case.get("mode")
    variables = case.get("vars") or {}
    output = str(case.get("output") or "")

    if mode == "standalone":
        parsed = json.loads(output)
        return grade_cookbook_normalized_calls(
            parsed.get("tool_calls", []),
            variables,
            str(parsed.get("answer") or ""),
            bool(parsed.get("completed", False)),
            _mutation=_mutation,
        )

    if mode == "codex":
        prov = case.get("providerResponse") or {}
        raw = prov.get("raw")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = None
        if not isinstance(raw, dict):
            return {"pass": False, "score": 0.0, "reason": "could not read the Codex item trace"}

        mcp_items = [item for item in raw.get("items", []) if item.get("type") == "mcp_tool_call"]
        for item in mcp_items:
            if item.get("error") or item.get("status") == "failed":
                return {
                    "pass": False,
                    "score": 0.0,
                    "reason": f"MCP tool call failed: {item.get('tool')}",
                }

        calls = [
            {
                "name": item.get("tool"),
                "arguments": item.get("arguments") if isinstance(item.get("arguments"), dict) else {},
                "result": (item.get("result") or {}).get("structured_content"),
            }
            for item in mcp_items
        ]
        errored = prov.get("error")
        completed = (not errored) and bool(str(raw.get("finalResponse") or "").strip())
        return grade_cookbook_normalized_calls(
            calls,
            variables,
            output,
            completed,
            _mutation=_mutation,
        )

    raise ValueError(f"unknown trace mode: {mode!r}")
