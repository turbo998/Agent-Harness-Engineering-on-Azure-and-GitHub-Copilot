#!/usr/bin/env python3
"""Original stdlib-only lab. Import the COMPLETE pinned eval_manifest module.
Not a notebook runner, package smoke test, or production transaction layer.
Run only after separate execution admission; preparation status is NOT_RUN.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile

SOURCE_SHA256 = "8788999297e5048e197cefa939248683e5beb7b57dcbe3b9f28329dd430acfa3"
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source/src/usersim/reporting/eval_manifest.py"
CASE_IDS = (
    "append_sequence", "cross_run_rejection", "fresh_cross_run", "schema_edges",
    "mixed_consensus", "prewrite_eval_failure", "prewrite_commit_failure",
    "fresh_history_loss", "missing_prediction_denominator", "successful_receipt",
)


class BusinessOracleFailure(AssertionError):
    """A meaningful state/contract assertion, never a syntax/import failure."""


class InjectedEvaluationFailure(RuntimeError):
    pass


class InjectedCommitFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise BusinessOracleFailure(message)


def read(m, path):
    result = m.read_eval_sample_manifest(path)
    require(result is not None, "manifest missing")
    return result


def record(m, path, *, ids=("t1", "t2"), run="r1", mode="full",
           locales=None, fresh=False, epoch=100):
    return m.record_eval_sample_pass(
        path, run_id=run, mode=mode, n=None, random_seed=42,
        eval_locales=locales, n_selected=len(ids), n_total=3,
        trajectory_ids=ids, fresh=fresh, wrote_at_epoch=epoch,
    )


def expect_error(kind, action):
    caught = False
    try:
        action()
    except kind:
        caught = True
    require(caught, "required exception absent: " + kind.__name__)


def reconciled_commit(manifest, receipts):
    # ORIGINAL LAB policy, not an upstream field or API. Receipts are synthetic.
    return bool(receipts)


def planned_denominator(planned, predictions):
    # ORIGINAL LAB policy: missing outputs remain in the declared denominator.
    return len(set(planned))


def intent_as_commit(manifest, receipts):
    # Single-point mutant: incorrectly promote any intent to committed.
    return bool(manifest.passes)


def observed_denominator(planned, predictions):
    # Single-point mutant: silently exclude absent predictions.
    return len(set(predictions) & set(planned))


class SyntheticStore:
    """In-memory stand-in only. Does NOT implement UserSim parquet storage."""
    def __init__(self, rows=None):
        self.rows = dict(rows or {})
        self.receipts = []
        self.eval_calls = 0
        self.commit_calls = 0
        self.events = []

    def evaluate(self, ids, fail=False):
        self.eval_calls += 1
        self.events.append("evaluate")
        if fail:
            raise InjectedEvaluationFailure("synthetic evaluation fault")
        return {x: "prediction" for x in ids}

    def commit(self, predictions, fail=False):
        self.commit_calls += 1
        self.events.append("commit_attempt")
        if fail:
            raise InjectedCommitFailure("synthetic pre-commit fault")
        self.rows = dict(predictions)
        self.receipts.append("synthetic-receipt")
        self.events.append("receipt")


def synthetic_flow(m, path, store, *, fresh=False, fault=None):
    record(m, path, ids=("new",), fresh=fresh, epoch=200)
    store.events.append("intent_written")
    predictions = store.evaluate(("new",), fail=fault == "evaluate")
    store.commit(predictions, fail=fault == "commit")


def case_append_sequence(m, path, commit_policy, denominator):
    record(m, path, ids=("t1", "t2"), locales=["en_US"])
    record(m, path, ids=("t2", "t3"), locales=["fr_FR"], epoch=101)
    state = read(m, path)
    require(len(state.passes) == 2, "append must retain both passes")
    require([p.wrote_at_epoch for p in state.passes] == [100, 101], "pass order changed")
    require([p.trajectory_ids for p in state.passes] == [["t1", "t2"], ["t2", "t3"]], "IDs changed")
    require(state.latest_pass is state.passes[-1], "latest pass mismatch")
    require(state.has_locale_targeted_pass, "locale targeting lost")
    require(sum(p.n_selected for p in state.passes) == 4, "selected counts changed")
    require(len({x for p in state.passes for x in p.trajectory_ids}) == 3, "unique planned IDs mismatch")
    require(state.consensus_mode == "full", "same modes lack consensus")


def case_cross_run_rejection(m, path, commit_policy, denominator):
    record(m, path)
    before = path.read_bytes()
    rejected = False
    try:
        record(m, path, run="r2")
    except ValueError:
        rejected = True
    unchanged = path.read_bytes() == before
    require(rejected and unchanged, "cross-run must reject AND leave bytes unchanged")


def case_fresh_cross_run(m, path, commit_policy, denominator):
    record(m, path)
    try:
        record(m, path, run="r2", ids=("new",), fresh=True)
    except ValueError as exc:
        raise BusinessOracleFailure("fresh must bypass old-run rejection") from exc
    state = read(m, path)
    require(state.run_id == "r2" and len(state.passes) == 1, "fresh intentionally bypasses old run check")
    require(state.passes[0].trajectory_ids == ["new"], "fresh retained old IDs")


def case_schema_edges(m, path, commit_policy, denominator):
    require(m.read_eval_sample_manifest(path) is None, "missing file should return None")
    for text in ("{", "[]", "null", "42"):
        path.write_text(text, encoding="utf-8")
        expect_error(ValueError, lambda: m.read_eval_sample_manifest(path))
    path.write_text(json.dumps({"schema_version": 999, "run_id": "r1", "passes": []}), encoding="utf-8")
    state = read(m, path)
    require(state.passes == [] and state.latest_pass is None, "passes list is discriminator, not version")
    require(state.consensus_mode == "unknown", "empty consensus should be unknown")
    path.write_text(json.dumps({"run_id": "r1", "mode": "legacy", "trajectory_ids": ["old"]}), encoding="utf-8")
    state = read(m, path)
    require(len(state.passes) == 1 and state.passes[0].wrote_at_epoch == 0, "v1 promotion failed")
    require(state.consensus_mode == "legacy", "mode is not enum-validated")
    path.write_text(json.dumps({"passes": []}), encoding="utf-8")
    record(m, path, run="r1")
    require(read(m, path).run_id == "", "missing run ID is not repaired by append")
    path.write_text(json.dumps({"run_id": "r1", "passes": [None]}), encoding="utf-8")
    expect_error(AttributeError, lambda: m.read_eval_sample_manifest(path))
    path.write_text(json.dumps({"run_id": "r1", "passes": "bad"}), encoding="utf-8")
    state = read(m, path)
    require(len(state.passes) == 1 and state.consensus_mode == "unknown", "non-list passes falls back to v1")


def case_mixed_consensus(m, path, commit_policy, denominator):
    record(m, path, mode="full")
    record(m, path, mode="per_locale", ids=("t1",), locales=["en_US"], epoch=101)
    state = read(m, path)
    require(len(state.passes) == 2, "mixed test needs both passes")
    require(state.consensus_mode == "mixed", "mixed history mislabeled as latest mode")


def fault_case(m, path, commit_policy, fault, fresh=False):
    store = SyntheticStore({"old": "old-result"})
    if fresh:
        record(m, path, ids=("old",))
    before = dict(store.rows)
    error = InjectedEvaluationFailure if fault == "evaluate" else InjectedCommitFailure
    expect_error(error, lambda: synthetic_flow(m, path, store, fresh=fresh, fault=fault))
    state = read(m, path)
    require(len(state.passes) == 1 and state.passes[0].trajectory_ids == ["new"], "intent must survive downstream fault; fresh drops history")
    require(store.rows == before and store.receipts == [], "failed attempt must not fabricate commit receipt")
    require(not commit_policy(state, store.receipts), "intent incorrectly counted as committed")
    require(store.eval_calls == 1 and store.commit_calls == (1 if fault == "commit" else 0), "unexpected synthetic call counts")
    expected = ["intent_written", "evaluate"] + (["commit_attempt"] if fault == "commit" else [])
    require(store.events == expected, "synthetic notebook ordering changed")


def case_prewrite_eval_failure(m, path, commit_policy, denominator):
    fault_case(m, path, commit_policy, "evaluate")


def case_prewrite_commit_failure(m, path, commit_policy, denominator):
    fault_case(m, path, commit_policy, "commit")


def case_fresh_history_loss(m, path, commit_policy, denominator):
    fault_case(m, path, commit_policy, "evaluate", fresh=True)


def case_missing_prediction_denominator(m, path, commit_policy, denominator):
    record(m, path, ids=("t1", "t2", "t3"))
    planned = read(m, path).passes[0].trajectory_ids
    predictions = {"t1": "yes", "t2": "no"}
    require(set(planned) - set(predictions) == {"t3"}, "missing prediction lost")
    require(denominator(planned, predictions) == 3, "observed-only denominator hides missing prediction")
    require(len(predictions) == 2, "observed count mismatch")
    # Counts are distinct: planned=3, observed=2, missing=1; no score claimed.


def case_successful_receipt(m, path, commit_policy, denominator):
    store = SyntheticStore()
    synthetic_flow(m, path, store)
    state = read(m, path)
    require(commit_policy(state, store.receipts), "successful synthetic receipt not recognized")
    require(store.rows == {"new": "prediction"}, "successful synthetic data not committed")
    require(store.events == ["intent_written", "evaluate", "commit_attempt", "receipt"], "success ordering")


# Exact single-replacement mutations, applied ONLY to disposable copies.
SOURCE_MUTATIONS = {
    "append_to_replace": ("manifest.passes.append(pass_record)", "manifest.passes[:] = [pass_record]", "append_sequence"),
    "remove_cross_run_guard": ("if existing is not None and existing.run_id and existing.run_id != run_id:", "if False:", "cross_run_rejection"),
    "ignore_fresh": ("existing = None if fresh else read_eval_sample_manifest(p)", "existing = read_eval_sample_manifest(p)", "fresh_history_loss"),
    "latest_not_consensus": ('return "mixed"', 'return self.passes[-1].mode', "mixed_consensus"),
    "version_gate": ('if isinstance(raw.get("passes"), list):', 'if raw.get("schema_version") == 2 and isinstance(raw.get("passes"), list):', "schema_edges"),
}


def import_complete_module(directory):
    # Normal import machinery, complete file, including dataclasses; no extraction,
    # exec/eval, package import, monkeypatched upstream dependencies, or notebook.
    sys.modules.pop("eval_manifest", None)
    sys.path.insert(0, str(directory))
    importlib.invalidate_caches()
    try:
        module = importlib.import_module("eval_manifest")
        require(Path(module.__file__).resolve() == (directory / "eval_manifest.py").resolve(), "wrong module origin")
        return module
    finally:
        sys.path.pop(0)


def run_suite(module, base, commit_policy, denominator, effects):
    results = []
    for name in CASE_IDS:
        case_dir = base / name
        case_dir.mkdir(parents=True)
        outcome = {"case": name, "status": "PASS"}
        try:
            globals()["case_" + name](module, case_dir / "manifest.json", commit_policy, denominator)
        except BusinessOracleFailure as exc:
            outcome.update(status="BUSINESS_ORACLE_FAILURE", detail=str(exc))
        except Exception as exc:
            # Import/syntax/KeyError/etc. can NEVER count as a mutation kill.
            outcome.update(status="ERROR", detail=type(exc).__name__ + ": " + str(exc))
        finally:
            outcome["blocked_effect_attempts"] = dict(effects)
        if any(effects.values()):
            outcome.update(status="SAFETY_FAILURE")
        results.append(outcome)
    return results


def main():
    sys.dont_write_bytecode = True
    require(hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256, "source hash mismatch")
    effects = {"network": 0, "process": 0}

    def audit(event, args):
        category = None
        if event.startswith("socket."):
            category = "network"
        elif event in ("subprocess.Popen", "os.system", "os.fork", "os.posix_spawn", "os.exec"):
            category = "process"
        if category:
            effects[category] += 1
            raise RuntimeError("prohibited effect: " + event)

    sys.addaudithook(audit)
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    results = {"source_sha256": SOURCE_SHA256, "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "case_ids": list(CASE_IDS), "variants": {}}
    source_text = SOURCE.read_text(encoding="utf-8")
    variants = [("baseline", None, reconciled_commit, planned_denominator, None)]
    for name, (old, new, target) in SOURCE_MUTATIONS.items():
        require(source_text.count(old) == 1, "mutation anchor not unique: " + name)
        variants.append((name, source_text.replace(old, new, 1), reconciled_commit, planned_denominator, target))
    variants.extend([
        ("intent_as_commit", None, intent_as_commit, planned_denominator, "prewrite_eval_failure"),
        ("observed_denominator", None, reconciled_commit, observed_denominator, "missing_prediction_denominator"),
    ])
    with tempfile.TemporaryDirectory(prefix="suite-", dir=runtime) as work:
        work = Path(work)
        for name, changed, commit_policy, denominator, target in variants:
            module_dir = SOURCE.parent
            if changed is not None:
                module_dir = work / name / "module"
                module_dir.mkdir(parents=True)
                (module_dir / "eval_manifest.py").write_text(changed, encoding="utf-8")
            try:
                module = import_complete_module(module_dir)
                rows = run_suite(module, work / name / "cases", commit_policy, denominator, effects)
                complete = [r["case"] for r in rows] == list(CASE_IDS)
                only_business = all(r["status"] in ("PASS", "BUSINESS_ORACLE_FAILURE") for r in rows)
                killed = target is not None and any(r["case"] == target and r["status"] == "BUSINESS_ORACLE_FAILURE" for r in rows)
                accepted = complete and (all(r["status"] == "PASS" for r in rows) if target is None else only_business and killed)
                results["variants"][name] = {"accepted": accepted, "target": target, "mutation_killed": killed, "cases": rows}
            except Exception as exc:
                results["variants"][name] = {"accepted": False, "status": "ERROR", "detail": type(exc).__name__ + ": " + str(exc)}
    results["blocked_effect_attempts"] = effects
    results["status"] = "PASS" if all(v["accepted"] for v in results["variants"].values()) and not any(effects.values()) else "FAIL"
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
