#!/usr/bin/env python3
"""Offline structural classifier v2; caller assertions are NOT authentication.
No network, subprocess, dynamic imports or vendor execution. Author: NOT_RUN.
Only classify_document is the public classification API; CLI exits 2 on bad input.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime

SCHEMA_VERSION = "release-evidence-contract-2026-10-06-v2"
TOP_KEYS = {"schema_version", "records"}
RECORD_KEYS = {"repo", "component", "fact_id", "source_path", "commit", "tag",
               "channel", "time", "evidencekind", "http_status",
               "content_verified", "incorporation", "runtime"}
RUNTIME_KEYS = {"observed", "scope", "environment", "build_id", "test_run_id",
                "component", "synthetic"}
CHANNELS = {"main", "stable", "latest", "alpha", "next", "registry", "release", "docs"}
KINDS = {"registry", "release_metadata", "release_body", "main_source", "tag_source", "runtime"}
COMPONENTS = {
    "openai/codex": {"codex-rs", "code-mode-runtime", "npm-package"},
    "anthropics/claude-code": {"cli", "npm-package", "changelog"},
    "microsoft/agent-framework": {"python", "dotnet", "repo"},
    "local/release-sentinel": {"fixture-runtime"},
}
SHA = re.compile(r"[0-9a-f]{40}", re.ASCII)
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", re.ASCII)
TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", re.ASCII)


def _is_plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_time(value):
    # Narrow RFC3339 profile: uppercase T/Z, microseconds at most, no leap seconds
    # or -00:00 (unknown offset). Validate offset BEFORE Python normalization.
    if not isinstance(value, str) or TIME.fullmatch(value) is None or value.endswith("-00:00"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def _path(value):
    return (bool(value) and not value.startswith("/") and
            all(part not in {"", ".", ".."} for part in value.split("/")) and
            re.fullmatch(r"[A-Za-z0-9_./-]+", value, re.ASCII) is not None)


def _issue(index, code, message):
    out = {"code": code, "message": message}
    if index is not None:
        out["index"] = index
    return out


def validate_document(doc):
    errors = []
    if not isinstance(doc, dict):
        return [_issue(None, "document_type", "expected object")], []
    if set(doc) != TOP_KEYS:
        errors.append(_issue(None, "top_keys", "top keys must be exactly schema_version, records"))
    if doc.get("schema_version") != SCHEMA_VERSION:
        errors.append(_issue(None, "schema_version", "v2 schema required"))
    records = doc.get("records")
    if not isinstance(records, list):
        return errors + [_issue(None, "records_type", "expected array")], []
    if not records:
        errors.append(_issue(None, "records_empty", "empty batch rejected to avoid false green"))
    seen_tags, seen_facts, seen_runtime = {}, {}, {}
    for index, rec in enumerate(records):
        start = len(errors)
        def error(code, message):
            errors.append(_issue(index, code, message))
        if not isinstance(rec, dict):
            error("record_type", "expected object")
            continue
        if set(rec) - RECORD_KEYS:
            error("unknown_record_keys", "unknown record fields")
        if RECORD_KEYS - set(rec):
            error("missing_record_keys", "all v2 fields required")
            continue
        strings = RECORD_KEYS - {"http_status", "content_verified", "runtime"}
        bad_strings = False
        for key in sorted(strings):
            if not isinstance(rec[key], str):
                error(key + "_type", "expected string; booleans are not strings")
                bad_strings = True
        if not _is_plain_int(rec["http_status"]):
            error("http_status_type", "expected integer, explicitly excluding bool")
        elif not 100 <= rec["http_status"] <= 599:
            error("http_status_range", "expected 100..599")
        if type(rec["content_verified"]) is not bool:
            error("content_verified_type", "expected boolean, not integer")
        if bad_strings:
            continue
        repo, component = rec["repo"], rec["component"]
        kind, channel = rec["evidencekind"], rec["channel"]
        commit, tag = rec["commit"], rec["tag"]
        fact, path = rec["fact_id"], rec["source_path"]
        if component not in COMPONENTS.get(repo, set()):
            error("component_mismatch", "repo/component not allowlisted")
        if kind not in KINDS:
            error("evidencekind_value", "unknown evidence kind")
        if channel not in CHANNELS:
            error("channel_value", "unknown channel")
        if rec["incorporation"] not in {"TRUE", "FALSE", "UNKNOWN"}:
            error("incorporation_value", "expected TRUE/FALSE/UNKNOWN string")
        if not _parse_time(rec["time"]):
            error("date_invalid", "expected strict timezone-aware RFC3339 profile")
        if commit and SHA.fullmatch(commit) is None:
            error("commit_invalid", "commit must be empty or exact lowercase 40 hex SHA")
        for key in ("tag", "fact_id"):
            if rec[key] and TOKEN.fullmatch(rec[key]) is None:
                error(key + "_invalid", "expected nonblank canonical token")
        if path and not _path(path):
            error("source_path_invalid", "expected canonical repo-relative ASCII path")
        if kind in {"main_source", "tag_source", "runtime"} and not (commit and fact and path):
            error("source_identity", "source/runtime needs SHA, fact_id and source_path")
        if kind == "main_source" and (channel != "main" or tag):
            error("main_identity", "main_source requires main channel and empty tag")
        if kind == "tag_source" and (not tag or channel == "main"):
            error("tag_identity", "tag_source requires nonblank tag and non-main channel")
        rt = rec["runtime"]
        if kind != "runtime":
            if rt is not None:
                error("runtime_for_nonruntime", "runtime must be null for source/metadata records")
        elif not isinstance(rt, dict):
            error("runtime_type", "runtime evidence requires runtime object")
        else:
            if set(rt) != RUNTIME_KEYS:
                error("runtime_keys", "runtime fields must match v2 exactly")
            for key in ("observed", "synthetic"):
                if type(rt.get(key)) is not bool:
                    error("runtime_" + key + "_type", "expected boolean, not integer")
            # Scope is a closed enum, not free prose that can smuggle global claims.
            if rt.get("scope") not in ("local", "build"):
                error("runtime_scope", "scope must be exactly local or build; never global")
            for key in ("environment", "build_id", "test_run_id"):
                value = rt.get(key)
                if not isinstance(value, str) or TOKEN.fullmatch(value) is None:
                    error("runtime_" + key, "expected nonblank bounded identifier")
            if rt.get("component") != component:
                error("component_mismatch", "runtime.component must equal record component")
            if rt.get("synthetic") is True and repo != "local/release-sentinel":
                error("synthetic_identity", "synthetic runtime must use local fixture identity, not vendor repo")
            if repo == "local/release-sentinel" and rt.get("synthetic") is not True:
                error("synthetic_identity", "local fixture runtime must be explicitly synthetic")
        if len(errors) != start:
            continue
        # commit is a source snapshot / tag target, NEVER the feature's origin SHA.
        # Tag mapping remains consistent even across different facts/components.
        if tag and commit:
            key = (repo, tag)
            prior = seen_tags.get(key)
            if prior is not None and prior != commit:
                error("conflicting_source", "same repo/tag has conflicting snapshot SHAs across channels")
            else:
                seen_tags[key] = commit
        if fact:
            # Untagged main/runtime snapshots are separate identities by SHA.
            key = (repo, component, fact, tag, "" if tag else commit)
            state = seen_facts.setdefault(key, {"commit": set(), "path": set(), "truth": set()})
            if commit:
                state["commit"].add(commit)
            if path:
                state["path"].add(path)
            if rec["incorporation"] != "UNKNOWN":
                state["truth"].add(rec["incorporation"])
            if any(len(values) > 1 for values in state.values()):
                error("conflicting_fact", "same repo/component/fact/tag disagrees on snapshot, path or TRUE/FALSE")
        if kind == "runtime":
            key = (repo, component, fact, commit, tag, rt["scope"], rt["environment"],
                   rt["build_id"], rt["test_run_id"])
            prior = seen_runtime.get(key)
            if prior is not None and prior != rt["observed"]:
                error("conflicting_runtime", "same runtime test identity has contradictory observation")
            seen_runtime[key] = rt["observed"]
    return errors, records


def _classify_record(rec):
    kind = rec["evidencekind"]
    asserted = rec["http_status"] == 200 and rec["content_verified"] and rec["incorporation"] == "TRUE"
    pinned = bool(rec["commit"] and rec["source_path"] and rec["fact_id"])
    eligible = False
    label = "release metadata"
    if kind == "registry":
        label = "registry signal"  # M1 anchor
    elif kind == "release_body":
        label = "release-body-declaration"
        if asserted and pinned and rec["tag"] and rec["channel"] != "main":
            label, eligible = "release-body-assertion", True
    elif kind == "main_source":
        if rec["http_status"] == 200 and rec["content_verified"]:
            label = "main-only"
    elif kind == "tag_source":
        if asserted:
            label, eligible = "tag-source-assertion", True
        elif rec["incorporation"] == "FALSE":
            label = "tag-source-absent-assertion"
        else:
            label = "tag-source-unconfirmed"
    elif kind == "runtime":
        label = "runtime-unconfirmed"
        if asserted and rec["runtime"]["observed"]:
            label, eligible = "runtime-scoped", True  # M4 anchor
    return {
        **{key: rec[key] for key in ("repo", "component", "fact_id", "source_path", "commit", "tag", "channel", "time", "incorporation")},
        "classification": label,
        "evidence_eligible": eligible,
        "eligibility_basis": "syntactic-only; asserted-by-caller; not authentication or feature authorization",
        "source_ref": f"{rec['repo']}@{rec['commit']}:{rec['source_path']}" if pinned else None,
        "runtime_scope": rec["runtime"]["scope"] if kind == "runtime" else None,
        "runtime": dict(rec["runtime"]) if kind == "runtime" else None,
    }


def classify_document(doc):
    errors, records = validate_document(doc)
    return {"ok": not errors, "schema_version": SCHEMA_VERSION,
            "assurance": "syntactic-only; no source content fetched or authenticated",
            "validation_errors": errors,
            "records": [] if errors else [dict(index=i, **_classify_record(r)) for i, r in enumerate(records)]}


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: " + key)
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("non-JSON numeric constant: " + value)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    try:
        if len(argv) not in (1, 2):
            raise ValueError("usage: classifier.py [evidence.json]")
        options = {"object_pairs_hook": _unique_object, "parse_constant": _reject_constant}
        if len(argv) == 2:
            with open(argv[1], encoding="utf-8") as stream:
                doc = json.load(stream, **options)
        else:
            doc = json.load(sys.stdin, **options)
        out = classify_document(doc)
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        out = {"ok": False, "schema_version": SCHEMA_VERSION, "records": [],
               "validation_errors": [_issue(None, "input_error", str(exc))]}
    json.dump(out, sys.stdout, ensure_ascii=True, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
