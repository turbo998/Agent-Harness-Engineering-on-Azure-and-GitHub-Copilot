# retry is not exactly-once

**日期：2026-09-24｜性质：原创、可公开、离线教学模型｜证据级别：source commit-level｜验证：原创模型验证，未上游实机验证。**

## README：先分开三个问题

“允许失败后重试”不等于“业务副作用只发生一次”。本 lab 用三个相互独立的防线回答三个不同问题：

| 防线 | 要回答的问题 | 本模型里的键与动作 |
|---|---|---|
| Trusted request binding | 这条 response 真在回应服务器认可的 request 吗？ | `(tenant, session, request)` 绑定 call、operation、payload 快照；先验证再碰副作用 |
| 业务幂等 | 换了 call ID 的同一业务操作，是否已经完成？ | `(tenant, session, operation)` 查重；示例 operation 为 `purchase:order-001`；相同 payload 复用结果，不同 payload 拒绝 |
| Generation 条件提交 | 旧 consumer 能否删掉或改写新事件留下的工作？ | session 队列保存 generation；完成与失败更新均先比较 generation |

**POC 数据流：** 可信入口保存 request → response 按认证上下文匹配 → operation 查重 → 模拟 effect → 保存结果 → transport 回包；另一条路径是事件 → session 合并队列 → consumer 携带 generation → 条件完成/重试。两条路径分别验证，不把队列去重冒充业务幂等。

### 可核查来源与解释边界

1. **MAF 新证据**：[commit 30b9b8e06766b2038e366d32979357c2fc4b9def diff](https://github.com/microsoft/agent-framework/commit/30b9b8e06766b2038e366d32979357c2fc4b9def.diff)。测试 `RunAsync_WhenApprovalResumeFails_RestoredSessionCanSendApprovalResponseAgainAsync` 断言失败回合后 `toolInvocationsAfterFailedTurn = 1`，恢复并重试后 `toolInvocations = 2`。这是“该测试场景会再次调用工具”的源码证据；不是对所有运行方式的概括，也不是调用次数等于真实外部扣款次数的证据。上游注释同时提醒有不可重复副作用的工具需要幂等。
2. **较早的 binding 背景，非本次新增重试证据**：[MAF bf93c539 diff（短提交标识）](https://github.com/microsoft/agent-framework/commit/bf93c539.diff)。核心是信任服务端保存的 request/call，而非客户端回放的调用内容。本 lab 抽象这个边界，不宣称所有工具都需要人工审批，也不实现上游审批协议。
3. **Runloop 模式来源**：[OpenAI Cookbook commit 5986832a554169dc87285b1b0b396941f235a62e 的 handler.py](https://raw.githubusercontent.com/openai/openai-cookbook/5986832a554169dc87285b1b0b396941f235a62e/examples/agents_api/sandboxes/webhook_managed/runloop/handler.py)。源码按 session 合并队列，generation 变化后旧任务只能删除自己那代，失败路径的更新也带 generation 条件。本模型原创重写该思想，另加 tenant 维度与**同一 Lab 实例生命周期内**不复用 epoch；**这些扩展不是对上游实现的声称**。

以上引用 URL 在制作时通过实际 HTTP 获取核对；来源仅作为文本数据阅读、提取结构化事实，未执行下载的源码。未调用模型、Runloop 或 MAF 服务。

### 如何运行

实测环境为 **CPython 3.11.15**；代码语法面向 Python 3.9+，但锁探针调用 CPython `RLock._is_owned` 私有诊断接口，其他实现/版本未验证，缺该接口会失败而非证明业务锁失效。只用标准库，无安装、凭据或网络依赖。把下方**唯一的 Python 代码块完整复制**到 `harness_retry_generation_lab.py`，在终端运行 `python3 harness_retry_generation_lab.py`。不需要其他文件；`unittest` 默认将报告写到 stderr，可用 `python3 harness_retry_generation_lab.py > tests.log 2>&1` 保存。

本次实测：**30 个具名 unittest 全部通过；代码 209 行（含空行）**。每个测试重新建模，无 sleep；线程测试只检查共享同一 `Lab` 实例的同步行为。新增的锁探针用可审计 `append` 确认 effect 写入发生在该实例的 `RLock` 临界区内；它不是跨实例、多进程或崩溃保护。另用 `nullcontext` 替换 `RLock` 的 mutation 实测失败，说明该探针不会让无锁 mutation 走 happy path。故意验证“发生两次”的反例也应该显示 `ok`，不是测试失败。

### 状态与故障注入

- `bind` 是可信服务器入口；`ctx=(tenant, session)` 假定由认证中间件提供，不接受客户端自报身份。这是信任边界模拟，不是认证系统。`call` 标识协议调用，`operation` 标识业务意图；两者不能混用。新业务意图使用新 key，例如 `purchase:order-002`；同一业务意图的重试必须稳定复用同一 key，例如 `purchase:order-001`，不能靠每次生成新 operation 绕过去重。
- `run(..., mode=...)` 的 mode **仅由测试控制**，不是客户端可选的恢复权限。常规路径先匹配 request，再检查 operation 的 payload 与状态。
- `fail`：已知在 effect 前失败，状态记为 `failed`，下次可重试。`pending`：已知在 effect 前暂停；普通重放仍抛出 `Pending`。只有测试显式 `resume` 才继续。这**不意味着生产中的未知 pending 可以直接再次执行**。
- `transport`：effect 已发生且结果记录已写入，但回包丢失；重试返回原结果，effect 数仍为一。
- `gap`：effect 已发生而记录丢失，模拟“外部系统成功、本地事务未提交”的崩溃窗口；重试 effect 数变为二。另有重建进程内状态的反例，外部 effect 留存而幂等记录消失。
- 队列 `finish(..., 'fail'/'pending')` 保留当前 generation 并递增尝试次数；`ok` 才条件删除。新事件重新入队，产生新 generation 并重置尝试次数。重试由测试主动触发，不实现时间调度、退避或次数上限。

## 断言矩阵

以下名称均省略 `test_` 前缀；每行对应代码里的一个具名测试。

| 测试 | 关键断言 / 排除的错误 |
|---|---|
| trusted_binding_executes | 合法绑定产生一个 effect |
| unknown_request_rejected | 不存在的 request 拒绝且无 effect |
| call_substitution_rejected | call ID 被替换，拒绝 |
| operation_substitution_rejected | response 偷换业务操作，拒绝 |
| payload_substitution_rejected | response 偷换参数，拒绝 |
| tenant_replay_rejected | 不同 tenant 不可重放原 request |
| session_replay_rejected | 同 tenant 不同 session 不可重放 |
| request_cannot_be_rebound | 原 request 不得被重新绑定不同 call；原绑定仍可用 |
| payload_snapshot_not_mutable_alias | 修改原字典不篡改已保存的可信快照 |
| identical_replay_returns_original_result | 同请求重复返回同一结果，effect 仍为一 |
| new_call_id_same_business_operation | 新 request/call、相同稳定 operation key 仍去重 |
| business_payload_conflict_despite_valid_binding | 即使新 request 合法，相同 operation 换 payload 也拒绝 |
| json_key_order_does_not_change_identity | JSON 对象键顺序不导致误判冲突 |
| distinct_operations_not_collapsed | 不同业务 operation 不能误去重 |
| tenants_have_distinct_operation_namespaces | tenant 之间相同 operation 相互独立 |
| sessions_have_distinct_operation_namespaces | session 之间相同 operation 相互独立 |
| transport_failure_after_effect_retries_without_duplicate | effect+记录后回包失败，重试不重复 effect |
| effect_append_requires_instance_lock | effect 写入必须发生在同一 Lab 实例的 RLock 临界区内 |
| known_pre_effect_failure_is_retryable | effect 前失败无 effect，下次执行成功 |
| pending_blocks_replay_until_explicit_safe_resume | pending 不盲重试，显式已知安全恢复才执行 |
| pending_still_rejects_payload_conflict | pending 不能绕过 operation 参数一致性检查 |
| effect_record_gap_can_duplicate | 外部 effect 与记录间隙导致两次 effect，明确反例 |
| restart_loses_in_memory_deduplication | 重建内存状态后同一 operation 可再次产生 effect |
| threads_share_one_lock_and_result | 共享实例多线程重试返回一个结果、一个 effect |
| latest_generation_coalesces_session_work | 同 session 多事件合并成一项，generation 增加 |
| stale_success_cannot_delete_new_generation | 旧 consumer 成功不得删除新 generation |
| stale_failure_cannot_modify_new_generation | 旧 consumer 失败不得污染新 generation 的尝试计数 |
| failed_and_pending_jobs_remain_retryable | fail/pending 保留工作并计次，随后 ok 删除 |
| deleted_generation_never_reused_in_instance | 删除后重新入队不复用 epoch，旧完成回调无效 |
| queue_tenant_and_session_isolation | 一个 tenant/session 完成不影响另两个上下文 |

## 单文件代码

```python
"""Original, offline teaching model; NOT an SDK or an exactly-once system."""
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor


class Pending(RuntimeError):
    pass


class Lab:
    def __init__(self, effects=None):
        self.lock = threading.RLock()
        self.requests, self.ops, self.jobs, self.epochs = {}, {}, {}, {}
        self.effects = [] if effects is None else effects

    @staticmethod
    def canonical(payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def bind(self, ctx, request, call, operation, payload):
        # Trusted server entry point; ctx comes from authenticated middleware.
        bound = (call, operation, self.canonical(payload))
        with self.lock:
            key = (ctx, request)
            if key in self.requests and self.requests[key] != bound:
                raise ValueError("request rebind")
            self.requests[key] = bound

    def run(self, ctx, request, call, operation, payload, mode="ok"):
        # mode is a test-only fault/control knob, NEVER a client parameter.
        if mode not in {"ok", "fail", "pending", "resume", "transport", "gap"}:
            raise ValueError("mode")
        value = self.canonical(payload)
        with self.lock:
            if self.requests.get((ctx, request)) != (call, operation, value):
                raise PermissionError("unbound response")
            key = (ctx, operation)  # Deliberately independent of call/request IDs.
            old = self.ops.get(key)
            if old and old[0] != value:
                raise ValueError("operation payload conflict")
            if old and old[1] == "done":
                return old[2]
            if old and old[1] == "pending" and mode != "resume":
                raise Pending("not safe to infer completion")
            self.ops[key] = (value, "pending", None)
            if mode == "pending":
                raise Pending("paused BEFORE effect")
            if mode == "fail":
                self.ops[key] = (value, "failed", None)
                raise RuntimeError("failed BEFORE effect")
            self.effects.append((key, value))
            result = len(self.effects)
            if mode == "gap":
                del self.ops[key]  # Crash: external effect survives, record does not.
                raise RuntimeError("effect/record gap")
            self.ops[key] = (value, "done", result)
            if mode == "transport":
                raise ConnectionError("reply lost AFTER effect and record")
            return result

    def enqueue(self, ctx):
        with self.lock:
            generation = self.epochs.get(ctx, 0) + 1
            self.epochs[ctx] = generation  # Retain epoch after deletion: avoid ABA.
            self.jobs[ctx] = (generation, 0, "pending")
            return generation

    def finish(self, ctx, generation, outcome):
        if outcome not in {"ok", "fail", "pending"}:
            raise ValueError("outcome")
        with self.lock:
            current = self.jobs.get(ctx)
            if not current or current[0] != generation:
                return False
            if outcome == "ok":
                del self.jobs[ctx]
            else:
                self.jobs[ctx] = (generation, current[1] + 1, outcome)
            return True


class Tests(unittest.TestCase):
    def setUp(self):
        self.lab, self.ctx, self.p = Lab(), ("tenant-a", "session-1"), {"amount": 7}
        self.bind()

    def bind(self, ctx=None, request="r1", call="c1", op="purchase:order-001", p=None):
        self.lab.bind(ctx or self.ctx, request, call, op, self.p if p is None else p)

    def run_op(self, ctx=None, request="r1", call="c1", op="purchase:order-001", p=None, mode="ok"):
        return self.lab.run(ctx or self.ctx, request, call, op, self.p if p is None else p, mode)
    def test_trusted_binding_executes(self):
        self.assertEqual(self.run_op(), 1)
        self.assertEqual(len(self.lab.effects), 1)
    def test_unknown_request_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(request="forged")
        self.assertEqual(self.lab.effects, [])
    def test_call_substitution_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(call="forged")
    def test_operation_substitution_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(op="withdraw")
    def test_payload_substitution_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(p={"amount": 99})
    def test_tenant_replay_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(ctx=("tenant-b", "session-1"))
    def test_session_replay_rejected(self):
        with self.assertRaises(PermissionError): self.run_op(ctx=("tenant-a", "session-2"))
    def test_request_cannot_be_rebound(self):
        with self.assertRaises(ValueError): self.bind(call="replacement")
        self.assertEqual(self.run_op(), 1)
    def test_payload_snapshot_not_mutable_alias(self):
        self.p["amount"] = 99
        self.assertEqual(self.run_op(p={"amount": 7}), 1)
    def test_identical_replay_returns_original_result(self):
        self.assertEqual([self.run_op(), self.run_op()], [1, 1])
        self.assertEqual(len(self.lab.effects), 1)
    def test_new_call_id_same_business_operation(self):
        self.run_op(); self.bind(request="r2", call="c2")
        self.assertEqual(self.run_op(request="r2", call="c2"), 1)
        self.assertEqual(len(self.lab.effects), 1)
    def test_business_payload_conflict_despite_valid_binding(self):
        self.run_op(); self.bind(request="r2", call="c2", p={"amount": 99})
        with self.assertRaises(ValueError): self.run_op(request="r2", call="c2", p={"amount": 99})
        self.assertEqual(len(self.lab.effects), 1)
    def test_json_key_order_does_not_change_identity(self):
        self.bind(request="r2", p={"a": 1, "b": 2})
        self.assertEqual(self.run_op(request="r2", p={"b": 2, "a": 1}), 1)
    def test_distinct_operations_not_collapsed(self):
        self.run_op(); self.bind(request="r2", op="refund:order-001")
        self.assertEqual(self.run_op(request="r2", op="refund:order-001"), 2)
    def test_tenants_have_distinct_operation_namespaces(self):
        self.run_op(); other = ("tenant-b", "session-1"); self.bind(ctx=other)
        self.assertEqual(self.run_op(ctx=other), 2)
    def test_sessions_have_distinct_operation_namespaces(self):
        self.run_op(); other = ("tenant-a", "session-2"); self.bind(ctx=other)
        self.assertEqual(self.run_op(ctx=other), 2)
    def test_transport_failure_after_effect_retries_without_duplicate(self):
        with self.assertRaises(ConnectionError): self.run_op(mode="transport")
        self.assertEqual(len(self.lab.effects), 1)
        self.assertEqual(self.run_op(), 1)
        self.assertEqual(len(self.lab.effects), 1)
    def test_effect_append_requires_instance_lock(self):
        class GuardedEffects(list):
            def __init__(self, locked):
                super().__init__(); self.locked, self.observed = locked, []
            def append(self, item):
                held = self.locked(); self.observed.append(held)
                if not held: raise AssertionError("effect append outside Lab lock")
                super().append(item)
        guarded = GuardedEffects(lambda: getattr(self.lab.lock, "_is_owned", lambda: False)())
        self.lab.effects = guarded
        self.assertEqual(self.run_op(), 1)
        self.assertEqual(guarded.observed, [True])
    def test_known_pre_effect_failure_is_retryable(self):
        with self.assertRaises(RuntimeError): self.run_op(mode="fail")
        self.assertEqual(self.lab.effects, [])
        self.assertEqual(self.run_op(), 1)
    def test_pending_blocks_replay_until_explicit_safe_resume(self):
        with self.assertRaises(Pending): self.run_op(mode="pending")
        with self.assertRaises(Pending): self.run_op()
        self.assertEqual(self.lab.effects, [])
        self.assertEqual(self.run_op(mode="resume"), 1)
    def test_pending_still_rejects_payload_conflict(self):
        with self.assertRaises(Pending): self.run_op(mode="pending")
        self.bind(request="r2", p={"amount": 99})
        with self.assertRaises(ValueError): self.run_op(request="r2", p={"amount": 99})
    def test_effect_record_gap_can_duplicate(self):
        with self.assertRaises(RuntimeError): self.run_op(mode="gap")
        self.assertEqual(self.run_op(), 2)
        self.assertEqual(len(self.lab.effects), 2)
    def test_restart_loses_in_memory_deduplication(self):
        self.run_op(); self.lab = Lab(self.lab.effects); self.bind()
        self.assertEqual(self.run_op(), 2)
    def test_threads_share_one_lock_and_result(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.run_op(), range(16)))
        self.assertEqual(set(results), {1}); self.assertEqual(len(self.lab.effects), 1)
    def test_latest_generation_coalesces_session_work(self):
        first = self.lab.enqueue(self.ctx); latest = self.lab.enqueue(self.ctx)
        self.assertGreater(latest, first); self.assertEqual(len(self.lab.jobs), 1)
    def test_stale_success_cannot_delete_new_generation(self):
        old = self.lab.enqueue(self.ctx); new = self.lab.enqueue(self.ctx)
        self.assertFalse(self.lab.finish(self.ctx, old, "ok"))
        self.assertEqual(self.lab.jobs[self.ctx], (new, 0, "pending"))
    def test_stale_failure_cannot_modify_new_generation(self):
        old = self.lab.enqueue(self.ctx); new = self.lab.enqueue(self.ctx)
        self.assertFalse(self.lab.finish(self.ctx, old, "fail"))
        self.assertEqual(self.lab.jobs[self.ctx], (new, 0, "pending"))
    def test_failed_and_pending_jobs_remain_retryable(self):
        g = self.lab.enqueue(self.ctx)
        for count, outcome in enumerate(("fail", "pending"), 1):
            self.assertTrue(self.lab.finish(self.ctx, g, outcome))
            self.assertEqual(self.lab.jobs[self.ctx], (g, count, outcome))
        self.assertTrue(self.lab.finish(self.ctx, g, "ok")); self.assertNotIn(self.ctx, self.lab.jobs)
    def test_deleted_generation_never_reused_in_instance(self):
        old = self.lab.enqueue(self.ctx); self.lab.finish(self.ctx, old, "ok")
        new = self.lab.enqueue(self.ctx)
        self.assertGreater(new, old); self.assertFalse(self.lab.finish(self.ctx, old, "ok"))
    def test_queue_tenant_and_session_isolation(self):
        contexts = [self.ctx, ("tenant-b", "session-1"), ("tenant-a", "session-2")]
        generations = [self.lab.enqueue(ctx) for ctx in contexts]
        self.lab.finish(contexts[0], generations[0], "ok")
        self.assertEqual(set(self.lab.jobs), set(contexts[1:]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

## 常见问答与不能保证的事

**为什么 retry 不是 exactly-once？** retry 只表示允许再次尝试；丢失响应无法证明副作用未发生。这里 `transport` 展示记录仍在时的去重，`gap` 与重启测试则直接给出重复 effect 的反例。

**一个 RLock 能保证 exactly-once 吗？** 不能。它只串行化同一 Python 进程里共享同一 Lab 实例的访问，不覆盖不同实例、多进程、多机、崩溃、存储丢失。线程测试通过不等于跨进程 exactly-once。外部 side effect 与幂等记录不在同一事务时仍有 gap，不能靠这把锁消除。

**生产里怎么处理 gap 或未知 pending？** 需要按业务选择由目标系统原子执行的幂等键、可查询的操作状态、对账/补偿、适当的事务或 outbox 配合消费端去重。单独 outbox 也不自动让外部 effect 恰好一次。不能对未知 pending 直接使用本测试的 `resume`。这些机制均未在本 lab 实现。

**generation 是 exactly-once 或 worker lease 吗？** 都不是。它仅防止旧任务对新队列版本进行陈旧删除/更新，不互斥领取任务，也不阻止两个 consumer 都做外部 effect。这里保留的 epoch 只在同一 `Lab` 实例生命周期内有效，不是持久化 fencing token。队列表示“该 session 需要重新协调”，不是保存每个事件 payload 的无损消息日志。

**operation key 应该怎样定？** 本模型选 `(tenant, session, operation)` 来明确隔离，示例 `purchase:order-001` 表示“购买 order-001”这一稳定业务意图；同一意图重试要复用稳定 key，新订单或新业务意图才使用新 key（如 `purchase:order-002`）。跨 session 共享的订单幂等需求需要另行设计业务作用域，不能照搬。调用方不能为了绕过去重每次生成新 operation。payload 序列化仅处理教学用 JSON 值，拒绝 NaN；它不是完整的跨语言规范化、金额校验、权限验证或输入 schema。

**这证明了 MAF 或 Runloop 的真实行为吗？** 没有。上游部分只核对固定提交的源码证据；运行结果只验证这份原创模型的断言，不是框架兼容性测试或实机验收。模型没有实际审批 UI、网络 transport、持久化数据库、进程崩溃或真实业务 side effect；故障是确定性注入。
