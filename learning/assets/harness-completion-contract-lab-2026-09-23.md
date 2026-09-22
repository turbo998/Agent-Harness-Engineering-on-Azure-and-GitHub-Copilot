# Completion Evidence Contract Lab（2026-09-23 离线练习卡）

目标：用一个完全离线、仅 Python 标准库的 toy contract，练习“完成证据”不能只看单个 `completed`/`exit 0`/`validator passed` 信号。所有字段均为 workshop 自定义字段，不是任何厂商 API。

安全边界：

- 代码不联网、不启动子进程、不执行外部/不可信代码；测试只使用内存中的合成低风险 POC 字符串。
- 代码不读写任意路径；从本 Markdown 复制为 `completion_lab.py` 后可直接运行。
- `evaluate` 是 pure function：输入 evidence、可信 `expected_revision`、可信 `now`、独立传入的可信审批 receipt（含 approval_code 与上下文绑定）、预期 task/check 集合、已见 nonce 快照，输出判定；不访问系统状态。
- `sha256` 在本练习中只表达完整性绑定，不表达真实性、签名、授权或来源身份。
- 真实授权、原子防重放、沙箱隔离、签名验证、内容安全审查不由此 toy 保证。生产者和评审者字符串不同只是必要条件；caller 必须从可信身份与审批服务取参数，不能从待审 evidence 自行生成审批。`trusted_approval()` 仅构造固定合成测试夹具，绝非授权实现。
- 同一 nonce 在纯函数外需要事务性占用/消费；本函数不更新 seen 集合，重复调用不保证 exactly-once。
- 最终 gate 名称是 `ready_for_demo`，故意不叫 `production_ready`。

```python
import hashlib, json, unittest

TOP = {"schema","task_id","producer_id","input_revision","artifact","coverage","producer","review","approval","collected_at","nonce"}
ART = {"kind","content","sha256"}; COV = {"required_total","covered","gaps"}
PROD = {"status","persisted","parent_consumed"}; REV = {"reviewer_id","artifact_sha256","decision"}
APP = {"status","approval_code"}


def canonical_hash(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def artifact_hash(rev, content, task_id="task-1", kind="markdown"):
    return canonical_hash({"task_id":task_id, "revision":rev, "kind":kind, "content":content})


def approval_binding(e):
    return canonical_hash({"task_id":e["task_id"], "revision":e["input_revision"],
                           "producer_id":e["producer_id"], "nonce":e["nonce"],
                           "artifact_sha256":e["artifact"]["sha256"], "review":e["review"]})


def trusted_approval():
    # Synthetic stand-in for an independently authenticated approval service.
    return {"approval_code":"DEMO_OK", "binding":approval_binding(base())}


def base():
    rev, content = "rev-2026-09-23", "synthetic poc: add two numbers"
    h = artifact_hash(rev, content)
    return {"schema":"completion-evidence-lab/v1","task_id":"task-1","producer_id":"worker-a",
            "input_revision":rev,"artifact":{"kind":"markdown","content":content,"sha256":h},
            "coverage":{"required_total":2,"covered":["contract","tests"],"gaps":[]},
            "producer":{"status":"completed","persisted":True,"parent_consumed":True},
            "review":{"reviewer_id":"reviewer-b","artifact_sha256":h,"decision":"approved"},
            "approval":{"status":"approved","approval_code":"DEMO_OK"},"collected_at":1_000,"nonce":"n-1"}


def ensure_fields(obj, allowed, required, name):
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be object")
    if not all(type(k) is str for k in obj):
        raise ValueError(f"{name} keys must be strings")
    extra = set(obj) - allowed
    if extra:
        raise ValueError(f"{name} unknown fields: {sorted(extra)}")
    missing = required - set(obj)
    if missing:
        raise ValueError(f"{name} missing fields: {sorted(missing)}")


def validate(e):
    ensure_fields(e, TOP, TOP, "evidence")
    if e["schema"] != "completion-evidence-lab/v1":
        raise ValueError("bad schema")
    for k in ["task_id","producer_id","input_revision","nonce"]:
        if not isinstance(e[k], str) or not e[k]:
            raise ValueError(f"{k} must be non-empty string")
    if type(e["collected_at"]) is not int:
        raise ValueError("collected_at must be int")
    ensure_fields(e["artifact"], ART, ART, "artifact")
    if type(e["artifact"]["kind"]) is not str or e["artifact"]["kind"] not in {"markdown","json"}:
        raise ValueError("artifact.kind invalid")
    for k in ["content","sha256"]:
        if not isinstance(e["artifact"][k], str) or not e["artifact"][k]:
            raise ValueError(f"artifact.{k} must be non-empty string")
    ensure_fields(e["coverage"], COV, COV, "coverage")
    if type(e["coverage"]["required_total"]) is not int or e["coverage"]["required_total"] < 1:
        raise ValueError("coverage.required_total must be positive int")
    for k in ["covered","gaps"]:
        if not isinstance(e["coverage"][k], list) or not all(isinstance(x, str) and x for x in e["coverage"][k]):
            raise ValueError(f"coverage.{k} must be list of non-empty strings")
    ensure_fields(e["producer"], PROD, PROD, "producer")
    if type(e["producer"]["status"]) is not str or e["producer"]["status"] not in {"completed","failed","unknown"}:
        raise ValueError("producer.status invalid")
    for k in ["persisted","parent_consumed"]:
        if type(e["producer"][k]) is not bool:
            raise ValueError(f"producer.{k} must be bool")
    ensure_fields(e["review"], REV, REV, "review")
    if not all(isinstance(e["review"][k], str) and e["review"][k] for k in REV):
        raise ValueError("review fields must be non-empty strings")
    if e["review"]["decision"] not in {"approved","changes_requested","unknown"}:
        raise ValueError("review.decision invalid")
    ensure_fields(e["approval"], APP, APP, "approval")
    if type(e["approval"]["status"]) is not str or e["approval"]["status"] not in {"approved","pending","denied"} or not isinstance(e["approval"]["approval_code"], str):
        raise ValueError("approval invalid")


def evaluate(e, expected_revision, now, approval_receipt, seen_nonces=(),
             expected_task_id="task-1", expected_checks=("contract", "tests")):
    validate(e)
    if type(now) is not int or not isinstance(expected_task_id, str) or not expected_task_id:
        raise ValueError("invalid trusted clock or task")
    if not isinstance(expected_revision, str) or not expected_revision:
        raise ValueError("invalid trusted revision")
    if (not isinstance(expected_checks, (tuple, list)) or not expected_checks
            or not all(type(x) is str and x for x in expected_checks)
            or len(expected_checks) != len(set(expected_checks))):
        raise ValueError("invalid trusted checks")
    ensure_fields(approval_receipt, {"approval_code", "binding"}, {"approval_code", "binding"}, "receipt")
    if not all(type(x) is str and x for x in approval_receipt.values()):
        raise ValueError("invalid trusted receipt")
    if not isinstance(seen_nonces, (tuple, list, set, frozenset)) or not all(type(x) is str for x in seen_nonces):
        raise ValueError("invalid replay snapshot")
    fail, unknown = [], []
    art = e["artifact"]; cov = e["coverage"]; prod = e["producer"]; rev = e["review"]; app = e["approval"]
    if e["task_id"] != expected_task_id:
        fail.append("task identity mismatch")
    if e["input_revision"] != expected_revision:
        fail.append("input revision mismatch")
    if art["sha256"] != artifact_hash(e["input_revision"], art["content"], e["task_id"], art["kind"]):
        fail.append("artifact hash not bound to input revision and content")
    if e["nonce"] in seen_nonces:
        fail.append("replay nonce")
    if now - e["collected_at"] > 3600 or e["collected_at"] > now + 60:
        fail.append("stale or future evidence")
    if prod["status"] == "failed":
        fail.append("producer failed")
    elif prod["status"] != "completed":
        unknown.append("producer not completed")
    if prod["status"] == "completed" and (not prod["persisted"] or not prod["parent_consumed"]):
        unknown.append("completed producer evidence not persisted and consumed")
    expected = set(expected_checks)
    covered = set(cov["covered"])
    if (cov["required_total"] != len(expected) or not covered <= expected
            or len(covered) != len(cov["covered"])):
        fail.append("coverage contract mismatch")
    if covered != expected or cov["gaps"]:
        unknown.append("coverage gap")
    if rev["reviewer_id"] == e["producer_id"]:
        fail.append("reviewer is not independent")
    if rev["artifact_sha256"] != art["sha256"]:
        fail.append("review not bound to current artifact")
    if rev["decision"] == "changes_requested":
        fail.append("review requested changes")
    elif rev["decision"] != "approved":
        unknown.append("review not approved")
    if approval_receipt["binding"] != approval_binding(e):
        fail.append("approval receipt context mismatch")
    if app["status"] == "denied":
        fail.append("human approval denied")
    elif app["status"] != "approved" or app["approval_code"] != approval_receipt["approval_code"]:
        unknown.append("human approval not approved")
    if fail:
        return {"ready_for_demo": False, "status": "fail", "reasons": fail}
    if unknown:
        return {"ready_for_demo": False, "status": "unknown", "reasons": unknown}
    return {"ready_for_demo": True, "status": "pass", "reasons": []}


class LabTests(unittest.TestCase):
    def ev(self, **changes):
        e = base()
        for path, value in changes.items():
            cur = e; parts = path.split("__")
            for p in parts[:-1]: cur = cur[p]
            cur[parts[-1]] = value
        return e
    def out(self, e, seen=()):
        return evaluate(e, "rev-2026-09-23", 1_100, trusted_approval(), seen)
    def assertStatus(self, e, s): self.assertEqual(self.out(e)["status"], s)
    def assertBad(self, e):
        with self.assertRaises(ValueError): self.out(e)

    def test_all_gates_pass_ready_for_demo(self): self.assertTrue(self.out(base())["ready_for_demo"])
    def test_result_key_not_production_ready(self): self.assertNotIn("production_ready", self.out(base()))
    def test_fail_beats_unknown(self): self.assertStatus(self.ev(producer__status="failed", review__decision="unknown"), "fail")
    def test_unknown_when_only_unknowns(self): self.assertStatus(self.ev(producer__status="unknown"), "unknown")
    def test_zero_required_rejected_not_empty_success(self): self.assertBad(self.ev(coverage__required_total=0, coverage__covered=[]))
    def test_coverage_gap_by_count(self): self.assertStatus(self.ev(coverage__covered=["contract"]), "unknown")
    def test_coverage_gap_by_declared_gap(self): self.assertStatus(self.ev(coverage__gaps=["review missing"]), "unknown")
    def test_hash_changes_with_content(self): self.assertStatus(self.ev(artifact__content="tamper"), "fail")
    def test_hash_bound_to_revision(self): self.assertStatus(self.ev(input_revision="rev-old"), "fail")
    def test_expected_revision_mismatch(self): self.assertEqual(evaluate(base(), "rev-other", 1_100, trusted_approval())["status"], "fail")
    def test_completed_not_persisted_unknown(self): self.assertStatus(self.ev(producer__persisted=False), "unknown")
    def test_completed_not_parent_consumed_unknown(self): self.assertStatus(self.ev(producer__parent_consumed=False), "unknown")
    def test_reviewer_must_differ(self): self.assertStatus(self.ev(review__reviewer_id="worker-a"), "fail")
    def test_review_bound_to_current_hash(self): self.assertStatus(self.ev(review__artifact_sha256="0"*64), "fail")
    def test_review_pending_unknown(self):
        e = self.ev(review__decision="unknown")
        receipt = {"approval_code":"DEMO_OK", "binding":approval_binding(e)}
        self.assertEqual(evaluate(e, "rev-2026-09-23", 1_100, receipt)["status"], "unknown")
    def test_review_changes_requested_fail(self): self.assertStatus(self.ev(review__decision="changes_requested"), "fail")
    def test_pending_human_approval_not_approved(self): self.assertStatus(self.ev(approval__status="pending"), "unknown")
    def test_bad_approval_code_unknown(self): self.assertStatus(self.ev(approval__approval_code="WRONG"), "unknown")
    def test_denied_approval_fail(self): self.assertStatus(self.ev(approval__status="denied"), "fail")
    def test_stale_evidence_fail(self): self.assertStatus(self.ev(collected_at=-3_000), "fail")
    def test_future_evidence_fail(self): self.assertStatus(self.ev(collected_at=9_999), "fail")
    def test_replay_nonce_fail(self): self.assertEqual(self.out(base(), seen=("n-1",))["status"], "fail")
    def test_unknown_top_field_rejected(self): e = base(); e["vendor_status"] = "completed"; self.assertBad(e)
    def test_unknown_nested_field_rejected(self): e = base(); e["artifact"]["path"] = "fixture/output.md"; self.assertBad(e)
    def test_bad_type_rejected(self): self.assertBad(self.ev(producer__persisted="true"))
    def test_missing_field_rejected(self): e = base(); del e["review"]["decision"]; self.assertBad(e)

    def test_bool_timestamp_rejected(self): self.assertBad(self.ev(collected_at=True))
    def test_bool_count_rejected(self): self.assertBad(self.ev(coverage__required_total=True))
    def test_forged_coverage_names_fail(self): self.assertStatus(self.ev(coverage__covered=["a", "b"]), "fail")
    def test_duplicate_coverage_names_fail(self): self.assertStatus(self.ev(coverage__covered=["contract", "contract"]), "fail")
    def test_self_reported_count_fail(self): self.assertStatus(self.ev(coverage__required_total=1), "fail")
    def test_cross_task_fail(self): self.assertStatus(self.ev(task_id="task-2"), "fail")
    def test_trusted_task_mismatch_fail(self):
        self.assertEqual(evaluate(base(), "rev-2026-09-23", 1_100, trusted_approval(), expected_task_id="task-2")["status"], "fail")
    def test_delimiter_ambiguity_removed(self): self.assertNotEqual(artifact_hash("a\nb", "c"), artifact_hash("a", "b\nc"))
    def test_kind_bound_to_hash(self): self.assertStatus(self.ev(artifact__kind="json"), "fail")
    def test_old_receipt_after_artifact_change_fail(self):
        e = self.ev(artifact__content="new artifact")
        h = artifact_hash(e["input_revision"], e["artifact"]["content"])
        e["artifact"]["sha256"] = e["review"]["artifact_sha256"] = h
        self.assertStatus(e, "fail")
    def test_old_receipt_new_nonce_fail(self): self.assertStatus(self.ev(nonce="n-2"), "fail")
    def test_old_receipt_new_reviewer_fail(self): self.assertStatus(self.ev(review__reviewer_id="reviewer-c"), "fail")
    def test_list_kind_valueerror(self): self.assertBad(self.ev(artifact__kind=[]))
    def test_list_producer_status_valueerror(self): self.assertBad(self.ev(producer__status=[]))
    def test_list_approval_status_valueerror(self): self.assertBad(self.ev(approval__status=[]))
    def test_unknown_receipt_field_rejected(self):
        receipt = trusted_approval(); receipt["extra"] = True
        with self.assertRaises(ValueError): evaluate(base(), "rev-2026-09-23", 1_100, receipt)
    def test_empty_trusted_checks_rejected(self):
        with self.assertRaises(ValueError): evaluate(base(), "rev-2026-09-23", 1_100, trusted_approval(), expected_checks=())
    def test_bool_clock_rejected(self):
        with self.assertRaises(ValueError): evaluate(base(), "rev-2026-09-23", True, trusted_approval())
    def test_wrong_schema_rejected(self): self.assertBad(self.ev(schema="other"))
    def test_mixed_unknown_key_types_rejected(self):
        e = base(); e[1] = "x"; self.assertBad(e)

if __name__ == "__main__":
    unittest.main(verbosity=2)
```

## 建议讨论题

1. 为什么 `producer.status == completed` 仍然不足以证明父流程已消费结果？
2. 为什么 coverage validator 通过不等于没有 coverage gap？
3. 为什么 artifact hash 必须与输入 revision 一起绑定？
4. 为什么 pending approval、stale evidence、replay nonce 都不能被折叠成“暂时成功”？
5. 这个 toy 明确没有解决哪些真实系统问题：身份真实性、签名、原子防重放、沙箱、真实审批授权、内容安全审查。

## 使用与验收边界

在批准的 Python 3 环境把唯一 Python 代码块保存为 `completion_lab.py` 后运行。2026-09-23 的本地合成测试执行了 **46 tests，全部通过**；未运行任何上游 CLI/SDK/云资源。测试失败时不得删除失败项以生成绿色结果。

可信输入是调用方控制的任务标识、revision、required-check 集合、时钟和独立审批 receipt；不要让 worker 同时生成 evidence 和这些可信参数。测试中的 `trusted_approval()` 只构造合成正例；不能把这种做法移植为真实授权服务。

`persisted` 与 `parent_consumed` 是待核验的证据声明；真实宿主需由持久存储与消费记录提供它们，本 toy 不证明文件已写、消息已读。`reviewer_id` 不同不证明不同真人/模型/权限域。示例只收字符串产物；不解析 JSON 文本、去重重复 JSON key、检验事实蕴含、签名或限制输入大小。

## 设计来源与原创范围

本代码与 schema 为独立改写的 workshop 教学模型，不复制上游实现、不声称厂商 API 兼容。来源用于解释为何需要门禁，不能用本 toy 通过替代产品实机验收。

- F1：[Checks.ps1：Get-Outcome、Finding/Coverage](https://raw.githubusercontent.com/microsoft-foundry/foundry-samples/c7226f4392c07326f03dcaae0ec1e7bb93118783/infrastructure/infrastructure-setup-bicep/15a-private-network-evaluation-only-setup/vnet-project-setup-diagnostic/scripts/Checks.ps1)（固定源码/发布声明静态核对，未运行上游）。

- C1：[Claude Code v2.1.280 changelog](https://raw.githubusercontent.com/anthropics/claude-code/v2.1.280/CHANGELOG.md)（固定源码/发布声明静态核对，未运行上游）。

- S2：Cloudflare security-audit-skill 的 coverage state validator 与 findings validator（固定源码静态核对，未运行上游；完整固定来源链接见主资产）。

- O3：[Cookbook workflow.py：顺序、引用与路由](https://raw.githubusercontent.com/openai/openai-cookbook/0493fe8ca45f5cc17b12c04a0e5220a373091582/examples/partners/AWS/prior_authorization_agentcore/runtime_source/workflow.py)（固定源码/发布声明静态核对，未运行上游）。

完整来源、方案取舍与各产品验收矩阵见 [Agent完成证据与POC门禁](agent-evidence-completion-and-poc-gates-2026-09-23.md)。
