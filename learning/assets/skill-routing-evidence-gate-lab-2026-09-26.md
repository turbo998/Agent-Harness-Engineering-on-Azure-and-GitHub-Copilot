# Workshop Lab：Skill Routing Evidence Gate（2026-09-26）

## 0. 目的与边界

本文件只描述一个离线、零依赖、合成数据的 routing fixture gate。它不是 host/live 执行证明，也不是工具授权或业务完成证明。输入前提是调用方已经用 `json.loads` 解码为 JSON primitives；不得传入任意 Python 对象，也不得在校验/评估期间并发修改输入。

### 来源与设计动机

以下为 Google GitHub 组织下的 `google/skill-reach`（项目并非官方支持的 Google 产品） 的固定源码快照 `33e0461c081bfbaf7024fd1aa8d339ca7b104c36`，2026-09-26 核实可达、只读未运行；本文代码是原创教学模型，不是上游实现或测试的副本。

- [README](https://raw.githubusercontent.com/google/skill-reach/33e0461c081bfbaf7024fd1aa8d339ca7b104c36/README.md)：skill 路由评测的范围及宿主权限边界。
- [check.py](https://raw.githubusercontent.com/google/skill-reach/33e0461c081bfbaf7024fd1aa8d339ca7b104c36/src/reach/check.py)：无查询可能 exit 0；目标查询先于邻居排入预算，预算截断不等于全覆盖；results 数不等于本次 live 调用数。
- [metrics.py](https://raw.githubusercontent.com/google/skill-reach/33e0461c081bfbaf7024fd1aa8d339ca7b104c36/src/reach/metrics.py)：错误样本排除后 scored 分母可能仍获得高分；完整性必须独立判断。
- [Claude Code runtime adapter](https://raw.githubusercontent.com/google/skill-reach/33e0461c081bfbaf7024fd1aa8d339ca7b104c36/src/reach/runtime/claude_code.py)：Skill 调用轨迹是路由证据，不是业务完成证明。
- [Apache-2.0 LICENSE](https://raw.githubusercontent.com/google/skill-reach/33e0461c081bfbaf7024fd1aa8d339ca7b104c36/LICENSE)：引用归属；不代替依赖、供应链或运行隔离审查。

**SA 用法：**技术问答区分“得分高”和“证据齐”；POC 用受信查询清单做完成门槛；架构图把 `原始观测 → 完整性门 → 路由质量门 → 独立业务验收` 分开画。本例只实现前两道判断，不创建模型/CLI适配器。

### 明确契约

受信 manifest/policy 应由验收方预先固定，不能让受测 Agent 随结果重写。run/revision 关联只是相等性检查，不验证来源真实性或签名；生产需要独立受信加载、制品来源和防篡改机制。


- manifest 与 policy 是受信结构，observations 只提供观测值；query `group/target/required_status` 来自 manifest，不从 observation 继承。
- `run_id/revision/id/query_id/status/mode` 等必须是 exact、非空 `str`，不做 `str(...)` coercion。
- `dict/list` 必须是 exact 类型；所有记录字段集合 exact match，unknown/missing fields 统一拒绝。
- policy bool 必须是 exact `bool`；阈值拒绝 `NaN/Inf/bool/out-of-range`。
- 所有 required query 必须 `PASS`；`FAIL/ERROR/SKIP/NOT_RUN` 均使报告 `REJECT`，且 `ERROR` 只计数、不再有 `allow_errors` 逃逸口。
- schema malformed 统一 `ValueError`；schema 合法但语义错误返回 `REJECT`。
- good baseline 全是合成 routing observation fixture；不把动态 host 的 `NOT_RUN` 塞进 good 基线。
- scope 固定为 `routing-fixture-only`，报告正文也明确与实际 host 无关。
- 保留 survivor：extra trailing skill 属于质量策略范围，当前 top1/reach 未授权业务副作用。

## 1. Host 边界矩阵（独立于 good fixture）

| host 类别 | 状态 | 说明 |
|---|---|---|
| 文件系统/进程/端口 | `NOT_RUN` | 本 lab 不读取本机状态作为 routing 通过证据。 |
| 网络/外部 CLI | `NOT_RUN` | 不联网、不执行真实工具，不把动态 host 结果混入基线。 |
| 业务副作用 | `NOT_RUN` | `decision=ACCEPT` 仅表示报告结构与 routing fixture 质量可接受。 |

## 2. 完整代码

保存为 `skill_gate_lab.py` 后运行：

```bash
python skill_gate_lab.py
```

```python
"""Routing-fixture-only gate; JSON-decoded inputs, no concurrent modification."""
import math
import unittest

STATUSES = {"PASS", "FAIL", "ERROR", "SKIP", "NOT_RUN"}
SCOPE = "routing-fixture-only"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def record(x, keys):
    require(type(x) is dict, "expected exact dict")
    require(set(x) == set(keys.split()), "missing/unknown fields")


def text(x):
    require(type(x) is str and bool(x.strip()), "expected nonblank exact str")


def strings(x, nonempty=False):
    require(type(x) is list, "expected exact list")
    require(not nonempty or bool(x), "empty list")
    for item in x:
        text(item)


def validate(m, obs, p):
    record(m, "scope run_id revision required_groups budget_truncated expected_queries")
    require(m["scope"] == SCOPE and type(m["scope"]) is str, "unsupported scope")
    for key in ("run_id", "revision"):
        text(m[key])
    require(type(m["budget_truncated"]) is bool, "budget must be bool")
    strings(m["required_groups"], True)
    groups = m["required_groups"]
    require(len(groups) == len(set(groups)), "duplicate group")
    require(set(groups) <= {"target", "neighbor"}, "invalid group")
    queries = m["expected_queries"]
    require(type(queries) is list and bool(queries), "empty/invalid manifest queries")
    for q in queries:
        record(q, "id group target required_status")
        for value in q.values():
            text(value)
        require(q["group"] in groups, "query group outside manifest")
        require(q["required_status"] == "PASS", "required status must be PASS")
    require(len({q["id"] for q in queries}) == len(queries), "duplicate manifest id")
    require({q["group"] for q in queries} == set(groups), "unrepresented required group")
    record(p, "allow_live allow_cache min_top1 min_reach")
    for key in ("allow_live", "allow_cache"):
        require(type(p[key]) is bool, "policy must be strict bool")
    for key in ("min_top1", "min_reach"):
        value = p[key]
        require(type(value) in (int, float), "threshold must be numeric, not bool")
        require(0 <= value <= 1 and (type(value) is int or math.isfinite(value)), "invalid threshold")
    require(type(obs) is list, "observations must be exact list")
    for o in obs:
        record(o, "id query_id run_id revision status mode plan selected")
        for key in ("id", "query_id", "run_id", "revision", "status", "mode"):
            text(o[key])
        require(o["status"] in STATUSES, "invalid status")
        require(o["mode"] in {"live", "cache"}, "invalid mode")
        strings(o["plan"])
        strings(o["selected"])


def evaluate(manifest, observations, policy):
    validate(manifest, observations, policy)
    m, obs, p = manifest, observations, policy
    expected = {q["id"]: q for q in m["expected_queries"]}
    issues, seen_groups, not_scored = [], set(), []
    ids = [o["id"] for o in obs]
    qids = [o["query_id"] for o in obs]
    if len(ids) != len(set(ids)):
        issues.append("duplicate_observation_id")
    if len(qids) != len(set(qids)):
        issues.append("duplicate_observed_query")
    if set(qids) != set(expected):
        issues.append("query_coverage_mismatch")
    if m["budget_truncated"]:
        issues.append("budget_truncated")
    counts = {status.lower(): sum(o["status"] == status for o in obs) for status in STATUSES}
    scored = top1 = reach = 0
    for o in obs:
        qid, status = o["query_id"], o["status"]
        q = expected.get(qid)
        if o["run_id"] != m["run_id"] or o["revision"] != m["revision"]:
            issues.append("stale_record:" + qid)
        if not p["allow_" + o["mode"]]:
            issues.append("mode_forbidden:" + qid)
        if status != "PASS":
            issues.append("required_query_not_pass:" + qid)
        if status != "PASS" or q is None:
            not_scored.append(qid + ":" + status)
            continue
        if not o["plan"]:
            issues.append("empty_plan:" + qid)
        seen_groups.add(q["group"])
        scored += 1
        top1 += bool(o["selected"]) and o["selected"][0] == q["target"]
        reach += q["target"] in o["selected"]
    if seen_groups != set(m["required_groups"]):
        issues.append("group_coverage_mismatch")
    quality = {"top1_accuracy": top1 / scored if scored else 0.0,
               "trajectory_reachability": reach / scored if scored else 0.0}
    quality_ok = scored > 0 and quality["top1_accuracy"] >= p["min_top1"] and quality["trajectory_reachability"] >= p["min_reach"]
    counts.update(expected=len(expected), observed=len(obs), scored=scored, not_scored=len(not_scored))
    return {"decision": "ACCEPT" if not issues and quality_ok else "REJECT", "scope": SCOPE,
            "completeness_ok": not issues, "quality_ok": quality_ok, "issues": issues,
            "quality": quality, "counts": counts, "not_scored": not_scored,
            "note": "synthetic routing report only; not tool authorization or business completion; no host evidence"}


def good():
    queries = [{"id": "q1", "group": "target", "target": "calendar", "required_status": "PASS"},
               {"id": "q2", "group": "target", "target": "calendar", "required_status": "PASS"},
               {"id": "q3", "group": "neighbor", "target": "mail", "required_status": "PASS"}]
    m = {"scope": SCOPE, "run_id": "run-001", "revision": "rev-a", "required_groups": ["target", "neighbor"],
         "budget_truncated": False, "expected_queries": queries}
    obs = [{"id": "o-" + q["id"], "query_id": q["id"], "run_id": m["run_id"], "revision": m["revision"],
            "status": "PASS", "mode": "live", "plan": ["synthetic routing fixture; no execution"],
            "selected": [q["target"]]} for q in queries]
    return m, obs, {"allow_live": True, "allow_cache": False, "min_top1": 1.0, "min_reach": 1.0}


class GateTests(unittest.TestCase):
    def changed(self, path, value):
        args = list(good())
        parent = args
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = value
        return args

    def test_good_multi_query_same_group(self):
        r = evaluate(*good())
        self.assertEqual((r["decision"], r["counts"]["scored"], r["scope"]), ("ACCEPT", 3, SCOPE))
        self.assertIn("not tool authorization", r["note"])

    def test_review_1_3_5_all_nonpass_reject_even_group_covered(self):
        for status in ("FAIL", "ERROR", "SKIP", "NOT_RUN"):
            with self.subTest(status=status):
                r = evaluate(*self.changed((1, 0, "status"), status))
                self.assertEqual(r["decision"], "REJECT")
                self.assertIn("required_query_not_pass:q1", r["issues"])
                self.assertEqual((r["counts"]["scored"], r["counts"]["not_scored"]), (2, 1))
                self.assertEqual(r["counts"][status.lower()], 1)
                self.assertEqual(r["counts"]["error"], int(status == "ERROR"))
                self.assertEqual(r["quality"]["top1_accuracy"], 1.0)

    def test_review_2_no_global_host_boolean_escape(self):
        for key in ("legacy_host_flag", "legacy_host_not_run"):
            for value in (True, False):
                with self.subTest(key=key, value=value):
                    self.assertRaises(ValueError, evaluate, *self.changed((0, key), value))
        self.assertRaises(ValueError, evaluate, *self.changed((0, "scope"), "host-live"))
        self.assertRaises(ValueError, evaluate, *self.changed((0, "expected_queries", 0, "group"), "host"))

    def test_review_3_no_allow_errors_escape(self):
        for value in (True, False, "false"):
            self.assertRaises(ValueError, evaluate, *self.changed((2, "allow_errors"), value))

    def test_review_4_strict_policy_bools(self):
        for key in ("allow_live", "allow_cache"):
            for value in ("false", "true", 0, 1, None, [], {}):
                with self.subTest(key=key, value=value):
                    self.assertRaises(ValueError, evaluate, *self.changed((2, key), value))

    def test_review_6_7_exact_container_schema(self):
        paths = [(0,), (1,), (2,), (0, "expected_queries"), (0, "required_groups"),
                 (0, "expected_queries", 0), (1, 0), (1, 0, "plan"), (1, 0, "selected")]
        for path in paths:
            for value in (None, 1, True, "target", {}, []):
                if path in [(1,), (1, 0, "plan"), (1, 0, "selected")] and value == []:
                    continue
                with self.subTest(path=path, value=value):
                    self.assertRaises(ValueError, evaluate, *self.changed(path, value))

    def test_exact_nonblank_strings_no_coercion(self):
        paths = [(0, k) for k in ("run_id", "revision")]
        paths += [(0, "expected_queries", 0, k) for k in ("id", "group", "target", "required_status")]
        paths += [(1, 0, k) for k in ("id", "query_id", "run_id", "revision", "status", "mode")]
        paths += [(0, "required_groups", 0), (1, 0, "plan", 0), (1, 0, "selected", 0)]
        for path in paths:
            for value in ("", " \t", None, 1, True, [], {}):
                with self.subTest(path=path, value=value):
                    self.assertRaises(ValueError, evaluate, *self.changed(path, value))

    def test_thresholds_nan_inf_bool_out_of_range(self):
        for key in ("min_top1", "min_reach"):
            for value in (float("nan"), float("inf"), -float("inf"), True, False, "1", None, -0.1, 1.1, 10**400):
                with self.subTest(key=key, value=value):
                    self.assertRaises(ValueError, evaluate, *self.changed((2, key), value))
            for value in (0, 1, 0.0, 0.5, 1.0):
                self.assertEqual(evaluate(*self.changed((2, key), value))["decision"], "ACCEPT")

    def test_missing_unknown_fields_all_records(self):
        for path in ((0,), (2,), (0, "expected_queries", 0), (1, 0)):
            args = list(good()); obj = args
            for key in path:
                obj = obj[key]
            for key in list(obj):
                bad = dict(obj); del bad[key]
                self.assertRaises(ValueError, evaluate, *self.changed(path, bad))
            self.assertRaises(ValueError, evaluate, *self.changed(path, dict(obj, unexpected=True)))

    def test_invalid_groups_status_mode_budget(self):
        changes = [((0, "required_groups"), x) for x in (["host"], ["target", "target"], ["target"], ["neighbor"])]
        changes += [((0, "expected_queries", 2, "group"), "target"), ((0, "expected_queries", 0, "required_status"), "SKIP"),
                    ((1, 0, "status"), "OK"), ((1, 0, "mode"), "cached"), ((0, "budget_truncated"), "false")]
        m, o, p = good(); m["expected_queries"].append(dict(m["expected_queries"][0]))
        self.assertRaises(ValueError, evaluate, m, o, p)
        for path, value in changes:
            self.assertRaises(ValueError, evaluate, *self.changed(path, value))

    def test_coverage_duplicates_stale_budget_plan(self):
        m, o, p = good()
        changes = [((1,), []), ((1,), o[:-1]), ((1,), o + [dict(o[0], id="extra", query_id="extra")]),
                   ((1, 1, "id"), o[0]["id"]), ((1, 1, "query_id"), "q1"), ((1, 0, "query_id"), " q1"),
                   ((1, 0, "run_id"), "old"), ((1, 0, "revision"), "old"), ((0, "budget_truncated"), True), ((1, 0, "plan"), [])]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                self.assertEqual(evaluate(*self.changed(path, value))["decision"], "REJECT")

    def test_explicit_live_cache_policies(self):
        self.assertEqual(evaluate(*self.changed((2, "allow_live"), False))["decision"], "REJECT")
        m, o, p = self.changed((1, 0, "mode"), "cache")
        self.assertEqual(evaluate(m, o, p)["decision"], "REJECT")
        p["allow_cache"] = True
        self.assertEqual(evaluate(m, o, p)["decision"], "ACCEPT")

    def test_quality_and_threshold_boundaries(self):
        m, o, p = self.changed((1, 0, "selected"), ["mail", "calendar"])
        r = evaluate(m, o, p)
        self.assertEqual((r["decision"], r["quality"]["trajectory_reachability"]), ("REJECT", 1.0))
        p["min_top1"] = 2 / 3
        self.assertEqual(evaluate(m, o, p)["decision"], "ACCEPT")
        p["min_top1"] += 0.001
        self.assertEqual(evaluate(m, o, p)["decision"], "REJECT")
        m, o, p = self.changed((1, 0, "selected"), [])
        p["min_top1"] = 0
        self.assertEqual(evaluate(m, o, p)["decision"], "REJECT")
        p["min_reach"] = 2 / 3
        self.assertEqual(evaluate(m, o, p)["decision"], "ACCEPT")
        p["min_reach"] += 0.001
        self.assertEqual(evaluate(m, o, p)["decision"], "REJECT")
        for row in o:
            row["status"] = "ERROR"
        p.update(min_top1=0, min_reach=0)
        r = evaluate(m, o, p)
        self.assertEqual((r["decision"], r["counts"]["scored"], r["counts"]["error"]), ("REJECT", 0, 3))
        self.assertFalse(r["quality_ok"])

    def test_survivor_extra_trailing_skill_is_not_authorization(self):
        r = evaluate(*self.changed((1, 0, "selected"), ["calendar", "mail"]))
        self.assertEqual(r["decision"], "ACCEPT")
        self.assertEqual(r["quality"], {"top1_accuracy": 1.0, "trajectory_reachability": 1.0})
        self.assertIn("not tool authorization", r["note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

```

## 3. 离线复现与故障注入

前置：一次性空白目录、CPython 3.11+、仅保存本文两个原创代码块；必须使用默认优化级别0，不使用 `-O`、`-OO` 或非空 `PYTHONOPTIMIZE`，否则runner的assert门会被移除；不安装依赖、不接客户数据。把上一块保存为 `skill_gate_lab.py`，先执行 `python skill_gate_lab.py`，预期 14 tests / OK / exit 0。测试方法内还有多个 subTest，方法数不是覆盖率指标。

把以下代码保存为 `mutation_lab.py`，在同一目录执行 `python mutation_lab.py`。它只在临时目录生成本文代码的变体，完成即清理；失败、超时、导入/语法错误都不能当作测试杀死变体。

```python
"""Run only the reviewed synthetic lab, never downloaded or customer code."""
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

source = Path("skill_gate_lab.py").read_text(encoding="utf-8").rstrip() + "\n"
mutations = {
    "nonpass": ('if status != "PASS":\n            issues.append("required_query_not_pass:" + qid)', 'if False:\n            issues.append("required_query_not_pass:" + qid)'),
    "strict_bool": ('require(type(p[key]) is bool, "policy must be strict bool")', 'require(True, "policy must be strict bool")'),
    "finite_threshold": ('require(0 <= value <= 1 and (type(value) is int or math.isfinite(value)), "invalid threshold")', 'require(True, "invalid threshold")'),
    "query_coverage": ('if set(qids) != set(expected):\n        issues.append("query_coverage_mismatch")', 'if False:\n        issues.append("query_coverage_mismatch")'),
    "quality_threshold": ('quality_ok = scored > 0 and quality["top1_accuracy"] >= p["min_top1"] and quality["trajectory_reachability"] >= p["min_reach"]', 'quality_ok = scored > 0'),
    "stale_binding": ('if o["run_id"] != m["run_id"] or o["revision"] != m["revision"]:', 'if False:'),
    "group_diagnostic_survivor": ('if seen_groups != set(m["required_groups"]):\n        issues.append("group_coverage_mismatch")', 'if False:\n        issues.append("group_coverage_mismatch")'),
}

def run(path):
    return subprocess.run([sys.executable, str(path)], capture_output=True,
                          text=True, timeout=20)

with tempfile.TemporaryDirectory(prefix="routing-fixture-") as directory:
    baseline = Path(directory) / "baseline.py"
    ast.parse(source)
    baseline.write_text(source, encoding="utf-8")
    result = run(baseline)
    assert result.returncode == 0 and "Ran 14 tests" in result.stderr, result.stderr
    for name, (old, new) in mutations.items():
        assert source.count(old) == 1, (name, "ambiguous mutation")
        mutant = source.replace(old, new, 1)
        ast.parse(mutant)  # A syntax/import failure is not a meaningful kill.
        target = Path(directory) / (name + ".py")
        target.write_text(mutant, encoding="utf-8")
        result = run(target)
        text = result.stdout + result.stderr
        killed = (result.returncode != 0 and "Ran 14 tests" in text
                  and re.search(r"FAILED \(failures=[1-9][0-9]*\)\s*$", text) is not None)
        survivor = result.returncode == 0 and "Ran 14 tests" in text
        if name == "group_diagnostic_survivor":
            assert survivor, (name, text)
            print(name, "SURVIVED: final rejection retained, diagnostic coverage gap")
        else:
            assert killed, (name, "not assertion-killed", text)
            print(name, "ASSERTION_KILLED")
```

预期前六个 mutation 输出 `ASSERTION_KILLED`；第七个 `group_diagnostic_survivor` 输出 `SURVIVED`：移除组覆盖诊断不会改变被其他完整性规则拒绝的结果，但当前测试没有要求该诊断必须保留。此 survivor 是已知覆盖缺口，不是安全保证；如扩展诊断契约，应补定向断言再改变预期。

**已执行的验证范围（2026-09-26）：**独立复评从正文提取主代码运行14 tests，通过3,730项独立输入/语义探针；另构造11个真实源码变体，10个 assertion-killed、1个诊断survivor。这里的数量只是该快照的测试结果，不证明穷尽安全性或任何上游产品行为。本文附带runner是一组更小、可独立复现的6+1练习，不把探针脚本未公开的完整扫描宣称为本文即拿即跑功能。

## 4. 练习卡与局限

- **完整性卡：**删除一条query；再保留该条但改SKIP，同组其他query照常PASS。两者都必须REJECT。
- **类型卡：**把 `allow_cache` 改为字符串 `false`、阈值改为NaN：必须ValueError，不能利用Python truthiness。
- **分母卡：**一条ERROR、其余routing满分：报告仍REJECT，errors与scored分开展示。
- **来源卡：**改旧run/revision：REJECT。相等并不证明来源真实，受信manifest/policy的加载与不可篡改仍是外部前提。
- **模式卡：**cache命中不等live调用；本例二者只是合成标签，不启动任何CLI。
- **边界卡：**额外trailing skill不降低top1/reach，当前可ACCEPT；任意非空plan只是形状约束，不证明计划被执行。较低阈值允许较差甚至空selected，仍不得推导工具授权。
- 本例不复刻上游runtime，不替代许可证、供应链、沙箱与敏感信息审查；无输入体积/CPU预算或防并发修改机制，不作为公网生产解析器。
- 若组织需要exact trajectory、冗余skill惩罚、密码学来源验证或host/live执行证明，应另建policy与独立证据链。
