"""Prepared, NOT_RUN: original 14 intents plus reviewer regressions.
Default unittest discovery MUST run the full fixtures through API AND real CLI.
All records, SHAs and runtime assertions are synthetic. No upstream execution.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from classifier import SCHEMA_VERSION, classify_document

ROOT = Path(__file__).resolve().parent
A, B = "a" * 40, "b" * 40


def record(**overrides):
    value = dict(repo="openai/codex", component="codex-rs", fact_id="synthetic.fact",
                 source_path="codex-rs/example.rs", commit=A, tag="", channel="main",
                 time="2026-10-05T00:00:00Z", evidencekind="main_source", http_status=200,
                 content_verified=True, incorporation="UNKNOWN", runtime=None)
    value.update(overrides)
    return value


def tagged(**overrides):
    value = record(tag="v1", channel="stable", evidencekind="tag_source", incorporation="TRUE")
    value.update(overrides)
    return value


def runtime_record(**overrides):
    value = record(repo="local/release-sentinel", component="fixture-runtime",
                   fact_id="synthetic.runtime-fact", source_path="tests/fixture.py",
                   evidencekind="runtime", incorporation="TRUE",
                   runtime=dict(observed=True, scope="local", environment="test-host",
                                build_id="fixture-build", test_run_id="fixture-run",
                                component="fixture-runtime", synthetic=True))
    value.update(overrides)
    return value


def doc(records):
    return dict(schema_version=SCHEMA_VERSION, records=records)


class ReleaseEvidenceClassifierExamples(unittest.TestCase):
    def result(self, rec, label, eligible=False):
        out = classify_document(doc([rec]))
        self.assertTrue(out["ok"], out)
        row = out["records"][0]
        self.assertEqual(row["classification"], label)
        self.assertIs(row["evidence_eligible"], eligible)
        self.assertNotIn("feature_claim_allowed", row)
        self.assertIn("syntactic-only", row["eligibility_basis"])
        return row

    def rejects(self, records, code):
        out = classify_document(doc(records))
        self.assertFalse(out["ok"], out)
        self.assertEqual(out["records"], [])
        self.assertIn(code, {item["code"] for item in out["validation_errors"]})

    # Original fourteen business/type intents, migrated to explicit v2 semantics.
    def test_codex_new_main_not_stable(self):
        self.result(record(), "main-only")

    def test_codex_stable_tag_absent(self):
        self.result(tagged(incorporation="FALSE"), "tag-source-absent-assertion")

    def test_registry_signal_only(self):
        self.result(tagged(evidencekind="registry"), "registry signal")

    def test_claude_next_no_changelog(self):
        self.result(record(repo="anthropics/claude-code", component="npm-package",
                           channel="next", tag="v-next", commit="", source_path="",
                           evidencekind="registry"), "registry signal")

    def test_claude_pinned_changelog_body_fact(self):
        self.result(tagged(repo="anthropics/claude-code", component="changelog",
                           source_path="CHANGELOG.md", evidencekind="release_body"),
                    "release-body-assertion", True)

    def test_empty_body_not_feature(self):
        self.result(tagged(evidencekind="release_body", content_verified=False),
                    "release-body-declaration")

    def test_maf_newer_sha_main_only(self):
        self.result(record(repo="microsoft/agent-framework", component="python",
                           source_path="python/example.py"), "main-only")

    def test_runtime_scoped(self):
        rec = runtime_record()
        row = self.result(rec, "runtime-scoped", True)
        self.assertEqual(row["runtime_scope"], "local")
        self.assertEqual(row["runtime"], rec["runtime"])
        self.assertTrue(row["runtime"]["synthetic"])

    def test_same_day_release_metadata_not_feature(self):
        self.result(tagged(evidencekind="release_metadata"), "release metadata")

    def test_head_200_not_feature(self):
        self.result(tagged(evidencekind="release_body", content_verified=False,
                           source_path="", commit=""), "release-body-declaration")

    def test_reject_bool_as_int_http_status(self):
        for value in (True, False, 200.0, "200"):
            with self.subTest(value=value):
                self.rejects([record(http_status=value)], "http_status_type")

    def test_reject_invalid_date(self):
        self.rejects([record(time="2026-02-30T00:00:00Z")], "date_invalid")

    def test_reject_conflicting_source(self):
        self.rejects([tagged(), tagged(commit=B)], "conflicting_source")

    def test_reject_component_mismatch_and_unknown_keys(self):
        bad = record(component="invented", extra=True)
        self.rejects([bad], "component_mismatch")
        self.rejects([bad], "unknown_record_keys")

    # Reviewer-derived independent regressions, not copies just to grow the count.
    def test_tag_source_requires_fixed_identity(self):
        for patch, code in (({"commit":""}, "source_identity"),
                            ({"commit":"abc123"}, "commit_invalid"),
                            ({"commit":" "}, "commit_invalid"),
                            ({"tag":""}, "tag_identity"),
                            ({"tag":" "}, "tag_invalid"),
                            ({"channel":"main"}, "tag_identity"),
                            ({"fact_id":""}, "source_identity"),
                            ({"source_path":""}, "source_identity")):
            with self.subTest(patch=patch):
                self.rejects([tagged(**patch)], code)

    def test_tag_source_positive_retains_reference(self):
        row = self.result(tagged(), "tag-source-assertion", True)
        self.assertEqual(row["source_ref"], f"openai/codex@{A}:codex-rs/example.rs")
        self.assertEqual(row["fact_id"], "synthetic.fact")

    def test_release_body_missing_identity_is_only_declaration(self):
        for key in ("commit", "fact_id", "source_path", "tag"):
            with self.subTest(key=key):
                self.result(tagged(evidencekind="release_body", **{key:""}),
                            "release-body-declaration")
        self.result(tagged(evidencekind="release_body", channel="main"),
                    "release-body-declaration")

    def test_date_requires_full_time_and_timezone(self):
        for value in ("2026-10-05", "2026-10-05T00:00:00", "2026-10-05 00:00:00Z",
                      True, 1791158400):
            with self.subTest(value=value):
                self.rejects([record(time=value)], "time_type" if not isinstance(value,str) else "date_invalid")

    def test_date_offset_not_normalized(self):
        for suffix in ("+00:99", "+24:00", "+99:99", "-01:60", "-00:00"):
            with self.subTest(suffix=suffix):
                self.rejects([record(time="2026-10-05T00:00:00" + suffix)], "date_invalid")

    def test_date_profile_calendar_and_clock_bounds(self):
        for value in ("2025-02-29T00:00:00Z", "2026-10-05T24:00:00Z", "2026-10-05T00:00:60Z",
                      "2026-10-05T00:00:00.1234567Z", "2026-10-05t00:00:00z"):
            with self.subTest(value=value):
                self.rejects([record(time=value)], "date_invalid")

    def test_date_accepts_valid_signed_offsets(self):
        for value in ("2024-02-29T23:59:59.123456Z", "2026-10-05T00:00:00+05:30",
                      "2026-10-05T00:00:00-07:00", "2026-10-05T00:00:00+00:00"):
            with self.subTest(value=value):
                self.result(record(time=value), "main-only")

    def test_boolean_fields_reject_integers(self):
        self.rejects([record(content_verified=1)], "content_verified_type")
        for field in ("observed", "synthetic"):
            rec = runtime_record()
            rec["runtime"][field] = 1
            self.rejects([rec], "runtime_" + field + "_type")
        self.rejects([tagged(incorporation=True)], "incorporation_type")

    def test_runtime_scope_cannot_be_empty_or_global(self):
        for scope in ("", " ", "globally available", "local: globally available", "LOCAL", [], True):
            rec = runtime_record()
            rec["runtime"]["scope"] = scope
            self.rejects([rec], "runtime_scope")

    def test_runtime_build_and_environment_are_explicit(self):
        rec = runtime_record()
        rec["runtime"]["scope"] = "build"
        row = self.result(rec, "runtime-scoped", True)
        self.assertEqual(row["runtime_scope"], "build")
        for field in ("environment", "build_id", "test_run_id"):
            bad = copy.deepcopy(rec)
            bad["runtime"][field] = " "
            self.rejects([bad], "runtime_" + field)

    def test_runtime_component_mismatch(self):
        rec = runtime_record()
        rec["runtime"]["component"] = "all-components"
        self.rejects([rec], "component_mismatch")

    def test_runtime_unobserved_not_eligible(self):
        rec = runtime_record()
        rec["runtime"]["observed"] = False
        self.result(rec, "runtime-unconfirmed")

    def test_synthetic_runtime_never_uses_vendor_identity(self):
        rec = runtime_record(repo="microsoft/agent-framework", component="python")
        rec["runtime"]["component"] = "python"
        self.rejects([rec], "synthetic_identity")

    def test_cross_channel_tag_target_conflict_across_facts(self):
        # Different facts must still share one tag target; specifically kills M3.
        self.rejects([tagged(), tagged(channel="latest", fact_id="other.fact", commit=B)],
                     "conflicting_source")

    def test_cross_channel_same_fact_truth_conflict(self):
        self.rejects([tagged(), tagged(channel="latest", incorporation="FALSE")], "conflicting_fact")

    def test_same_fact_path_cannot_change_across_channels(self):
        self.rejects([tagged(), tagged(channel="next", source_path="other/file.rs")], "conflicting_fact")

    def test_different_facts_can_disagree_on_incorporation(self):
        out = classify_document(doc([tagged(), tagged(fact_id="other.fact", incorporation="FALSE")]))
        self.assertTrue(out["ok"], out)
        self.assertEqual([r["evidence_eligible"] for r in out["records"]], [True, False])

    def test_unknown_is_not_upgraded_by_other_records(self):
        out = classify_document(doc([tagged(), tagged(channel="latest", incorporation="UNKNOWN")]))
        self.assertTrue(out["ok"], out)
        self.assertEqual([r["evidence_eligible"] for r in out["records"]], [True, False])

    def test_guards_for_all_three_eligible_kinds(self):
        for base in (tagged(), tagged(evidencekind="release_body"), runtime_record()):
            for patch in ({"content_verified":False}, {"http_status":404}, {"incorporation":"UNKNOWN"}):
                rec = copy.deepcopy(base)
                rec.update(patch)
                out = classify_document(doc([rec]))
                self.assertTrue(out["ok"], out)
                self.assertIs(out["records"][0]["evidence_eligible"], False)

    def test_unknown_fields_at_each_level_are_rejected(self):
        value = doc([record()]); value["extra"] = True
        out = classify_document(value)
        self.assertFalse(out["ok"])
        self.assertIn("top_keys", {e["code"] for e in out["validation_errors"]})
        self.rejects([record(path="not-source_path")], "unknown_record_keys")
        rec = runtime_record(); rec["runtime"]["extra"] = True
        self.rejects([rec], "runtime_keys")

    def test_source_path_is_canonical_relative(self):
        for path in ("../x", "/tmp/x", "x//y", "x/./y", "x\\y", "https://example.com/x", " "):
            self.rejects([tagged(source_path=path)], "source_path_invalid")

    def test_runtime_payload_cannot_hide_on_source(self):
        self.rejects([record(runtime=runtime_record()["runtime"])], "runtime_for_nonruntime")

    def test_runtime_same_test_observation_conflict(self):
        r1, r2 = runtime_record(), runtime_record()
        r2["runtime"]["observed"] = False
        self.rejects([r1, r2], "conflicting_runtime")

    def test_empty_or_malformed_document(self):
        for value in (None, [], {}, doc([]), doc([None]), doc([{}])):
            out = classify_document(value)
            self.assertFalse(out["ok"], out)
            self.assertEqual(out["records"], [])

    def test_whole_fixtures_api_required(self):
        fixture = json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))
        out = classify_document(fixture)
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(out["records"]), 12)
        self.assertEqual([r["classification"] for r in out["records"]], [
            "main-only", "tag-source-absent-assertion", "main-only", "registry signal",
            "registry signal", "release-body-assertion", "release-body-declaration", "main-only",
            "release metadata", "runtime-scoped", "release metadata", "release-body-assertion"])
        self.assertEqual([r["evidence_eligible"] for r in out["records"]],
                         [False,False,False,False,False,True,False,False,False,True,False,True])
        self.assertEqual(out["records"][9]["repo"], "local/release-sentinel")
        self.assertTrue(out["records"][9]["runtime"]["synthetic"])

    def cli(self, *args, data=None):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "classifier.py"), *args],
                                input=data, capture_output=True, text=True, timeout=15, cwd=ROOT)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_whole_fixtures_cli_required(self):
        code, out = self.cli(str(ROOT / "fixtures.json"))
        self.assertEqual(code, 0)
        expected = classify_document(json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8")))
        self.assertEqual(out, expected)
        self.assertTrue(out["ok"])

    def test_cli_schema_error_exit2(self):
        code, out = self.cli(data=json.dumps(doc([tagged(commit="")])) )
        self.assertEqual(code, 2)
        self.assertFalse(out["ok"])
        self.assertEqual(out["records"], [])

    def test_cli_json_and_duplicate_key_errors_exit2(self):
        for raw in ("{", '{"schema_version":"x","schema_version":"y","records":[]}',
                    '{"records":NaN}', '{"records":Infinity}'):
            code, out = self.cli(data=raw)
            self.assertEqual(code, 2)
            self.assertFalse(out["ok"])
            self.assertEqual(out["validation_errors"][0]["code"], "input_error")

    def test_cli_unicode_error_protocol_and_schema_controls(self):
        import os

        # Force strict UTF-8 output: never depend on surrogateescape or locale.
        environment = dict(os.environ, PYTHONIOENCODING="utf-8:strict")
        duplicate_cases = []
        for key in ("\ud800", "\udfff", "é", "中文", "😀"):
            escaped = json.dumps(key, ensure_ascii=True)
            pair = escaped + ':1,' + escaped + ':2'
            duplicate_cases.extend([
                ("top", key, '{' + pair + '}'),
                ("nested", key, '{"records":[{' + pair + '}]}'),
                ("runtime", key, '{"records":[{"runtime":{' + pair + '}}]}'),
            ])

        # Both literal UTF-8 and escaped Unicode stay subject to the same schema.
        # There are no free-form Unicode string fields in this closed schema.
        accepted = doc([tagged()])
        controls = [("accepted", accepted, True)]
        controls.append(("nonascii-fact", doc([tagged(fact_id="事实")]), False))
        controls.append(("nonascii-path", doc([tagged(source_path="源码.py")]), False))
        unknown = doc([tagged()]); unknown["说明"] = "正常 Unicode"
        controls.append(("nonascii-key", unknown, False))
        rt = runtime_record(); rt["runtime"]["environment"] = "测试环境"
        controls.append(("nonascii-runtime", doc([rt]), False))

        with tempfile.TemporaryDirectory() as directory:
            input_file = Path(directory) / "unicode-input.json"

            def invoke(raw, mode):
                args = [sys.executable, "-B", str(ROOT / "classifier.py")]
                if mode == "file":
                    input_file.write_text(raw, encoding="utf-8")
                    args.append(str(input_file))
                result = subprocess.run(
                    args, input=raw if mode == "stdin" else None,
                    capture_output=True, text=True, encoding="utf-8", errors="strict",
                    timeout=15, cwd=ROOT, env=environment)
                self.assertEqual(result.stderr, "")
                self.assertTrue(result.stdout.endswith("\n"))
                self.assertTrue(result.stdout.isascii())
                # loads consumes the complete JSON document, not a truncated prefix.
                return result.returncode, json.loads(result.stdout)

            for mode in ("stdin", "file"):
                for location, key, raw in duplicate_cases:
                    with self.subTest(mode=mode, location=location, key=repr(key)):
                        code, out = invoke(raw, mode)
                        self.assertEqual(code, 2)
                        self.assertEqual(out, {
                            "ok": False, "schema_version": SCHEMA_VERSION, "records": [],
                            "validation_errors": [{"code": "input_error",
                                "message": "duplicate JSON key: " + key}]})
                for name, value, expected_ok in controls:
                    for ascii_only in (False, True):
                        with self.subTest(mode=mode, control=name, escaped=ascii_only):
                            expected = classify_document(value)
                            self.assertIs(expected["ok"], expected_ok)
                            code, out = invoke(json.dumps(value, ensure_ascii=ascii_only), mode)
                            self.assertEqual(code, 0 if expected_ok else 2)
                            self.assertEqual(out, expected)
                # Valid JSON Unicode escapes can represent allowed ASCII identifiers.
                with self.subTest(mode=mode, control="escaped-schema-key"):
                    raw = json.dumps(accepted).replace('"schema_version"', r'"\u0073chema_version"')
                    code, out = invoke(raw, mode)
                    self.assertEqual(code, 0)
                    self.assertEqual(out, classify_document(accepted))

    def test_cli_io_and_usage_errors_exit2(self):
        with tempfile.TemporaryDirectory() as directory:
            for args in ((str(Path(directory) / "missing.json"),), ("one", "two")):
                code, out = self.cli(*args)
                self.assertEqual(code, 2)
                self.assertFalse(out["ok"])

    def test_cli_stdin_valid_exit0(self):
        code, out = self.cli(data=json.dumps(doc([tagged()])))
        self.assertEqual(code, 0)
        self.assertEqual(out, classify_document(doc([tagged()])))


# Single exact source replacement per mutant; no mutants are applied/run by this file.
# Reviewer must copy all four files, assert old text occurs exactly once, run full suite.
# Kill = named assertion FAILURE; syntax/import/timeout/unrelated errors are NOT kills.
MUTATION_DESIGNS_NOT_RUN = [
    dict(id="M1", old='label = "registry signal"  # M1 anchor',
         new='label, eligible = "release-body-assertion", True  # M1 anchor',
         target="test_registry_signal_only", meaning="registry promotion only; no metadata mutation"),
    dict(id="M2", old='return isinstance(value, int) and not isinstance(value, bool)',
         new='return isinstance(value, int)', target="test_reject_bool_as_int_http_status",
         meaning="type-error-code kill only; range rejection still prevents bool acceptance"),
    dict(id="M3", old='key = (repo, tag)', new='key = (repo, tag, channel)',
         target="test_cross_channel_tag_target_conflict_across_facts",
         meaning="channel-inclusive tag map permits conflicting commits across different facts; fact guard unchanged"),
    dict(id="M4", old='label, eligible = "runtime-scoped", True  # M4 anchor',
         new='label, eligible = "release-body-assertion", True  # M4 anchor',
         target="test_runtime_scoped", meaning="runtime label promotion only; scope/component validation unchanged"),
]

if __name__ == "__main__":
    unittest.main()
