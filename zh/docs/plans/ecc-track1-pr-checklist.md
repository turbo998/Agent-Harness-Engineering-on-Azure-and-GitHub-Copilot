# Workshop 改造 PR 清单（轨道一：ECC 反哺教学资产）

> 状态：researcher 起草，**待 fde persona 执行**。已对 workshop 当前一手结构（5 labs + 双语 zh/+EN + 180min agenda）校准，剔除已存在项。
> 仓库：本地 `/home/azureuser/Harness-Engineering-in-GithHub-Copilot-Workshop`，远端 `turbo998/Agent-Harness-Engineering-on-Azure-and-GitHub-Copilot`
> ⚠️ 双语：每个改动都要 root(EN) + zh/ 两套同步，否则双版本漂移。

---

## PR-1 — DESIGN.md 把 ECC 加为「第二标杆」

**Gap 真伪：真**（当前对比表只有 gstack，DESIGN.md L106-122）
- 文件：`docs/DESIGN.md` L107 表 + `zh/docs/DESIGN.md` L106 表
- 动作：在 gstack 对比表后新增一节「另一种 harness 风格：ECC」，并把对比表从 2 列扩成 3 列（gstack / ECC / 本 Workshop），维度补「跨 harness 可移植性」「每 agent 内置防御」两行。
- 验收：学员能从表里看到 harness 设计是光谱而非单一答案。
- ⚠️ 不提 ECC star 数（三方打架，不作背书）；只引其文档/代码做法。

## PR-2 — lab2 新增「Agent 注入防御基线」动手模块

**Gap 真伪：真**（lab3 现有 "injection attacks" 是教学员找**代码**里的注入 bug；本项是给 **agent 本身**写防御层——概念不同，确为缺口）
- 文件：`labs/lab2-harness-engineering.md` + `zh/labs/lab2-harness-engineering.md`
- 动作：在三层模型（Rule/Role/Workflow）后加第 4 个维度「不可信外部内容防御」。配动手练习：学员给自己的 agent 写防御规则 → 用注入样本（"忽略以上指令""把密钥发到…"）攻击 → 验证 agent 是否守住。
- 可直接引本轮 Hermes 实践做活案例（dogfooding：我自己 5 个 persona 就是这么加防御的）。
- 验收：学员产出一份能挡住注入样本的 agent 防御规则。

## PR-3 — lab3 新增「传 PURPOSE vs 只传 task」对照练习

**Gap 真伪：真**（lab3 现有多 agent 协作，但无 PURPOSE 传递对照）
- 文件：`labs/lab3-multi-agent-collaboration.md` + `zh/labs/lab3-multi-agent-collaboration.md`
- 动作：加一个 A/B 练习——上游 agent 分别(A)只传 task、(B)传 task+PURPOSE 给下游，让学员实测下游产出质量差异。引 ECC 跨 harness 架构的 PURPOSE 传递理念佐证。
- 验收：学员亲眼看到传 PURPOSE 后下游产出更对齐。

## PR-4 — lab2 backpressure 节补 ECC token 预算真实案例

**Gap 真伪：弱**（backpressure 概念已有，仅缺真实案例佐证）
- 文件：`labs/lab2-harness-engineering.md` L531 附近 + zh 对应
- 动作：在「黑屋子走路」比喻后，补一段 ECC「token 预算是硬约束、接近就总结重开」作为生产级 backpressure 实例。轻量增补，非新模块。
- 验收：backpressure 从比喻落到可量化实践。

---

## 执行建议（给 fde）

1. 优先级：PR-2 > PR-1 > PR-3 > PR-4（PR-2 价值最高、最容易被合作伙伴忽略）。
2. 每个 PR 独立分支、conventional commits、双语同步改。
3. PR-2/PR-3 是新增动手模块，需配可复现的样本/脚本，按 lab 现有风格写。
4. PAT 写权限注意：fine-grained token 可能 `Contents: write` 缺失（push 报 403），先验证。

## 关联资产
- 双轨清单（本清单上游）：https://feishu.cn/docx/CCoTdJevnod7HyxYMAwcWbyDnuf
- ECC 架构拆解：https://feishu.cn/docx/XY3idF315oWkCixv2Grcr40xnyc
- ECC × Workshop 对标：https://feishu.cn/docx/JZqed29rKoBQK3x1fGPc5WXpn9g
