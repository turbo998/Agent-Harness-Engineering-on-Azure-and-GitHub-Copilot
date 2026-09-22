<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 双 Harness Skill 编写规范 —— mattpocock/skills 拆解速查（2026-08-04 新增）

> 来源：https://github.com/mattpocock/skills （201,232★ / 17,344 fork，GitHub API 核实，08-03 仍在推送）
> 与已吸收案例对照：obra/superpowers（内容质量纪律为主）、google-deepmind/science-skills（科研方法论为主）。
> mattpocock/skills 的独特价值：**唯一同时覆盖 Claude Code + Codex 双 harness 同步规范**的高星仓库。

> ⚠️ 订正说明（08-04）：本页只把 `mattpocock/skills` 当作公开样本，观察 `SKILL.md` 与 Codex 可选扩展文件的共存形态；不再引用内部 skill 研究记录，也不比较不同 host 的配置“简单性”。

## 一、核心发现：双 harness 同步规范（`.agents/invocation.md`）

原文（https://raw.githubusercontent.com/mattpocock/skills/main/.agents/invocation.md ，已curl核实）明确规定：
每个技能必须**同时**维护两套 frontmatter 保持"user-invoked / model-invoked"状态一致：
- **Claude Code 侧**：`SKILL.md` frontmatter 里 `disable-model-invocation: true`
- **Codex 侧**：`agents/openai.yaml` 里 `policy.allow_implicit_invocation: false`

是目前调研到的**调研范围内暂未发现同类的双harness技能同步纪律仓库**；obra/superpowers、google-deepmind/science-skills 都只针对单一harness（Claude Code）（⚠️样本量小，非全网穷举结论）。

**→ 反哺 harness workshop**：以 `SKILL.md` 为技能主体；`agents/openai.yaml` 仅作为 Codex 场景的可选扩展元数据，不应把扩展文件误解为跨 host 必需项。

## 二、Model-invoked vs User-invoked 二分法 + Router Skill 模式

来源：`skills/productivity/writing-great-skills/SKILL.md`

- **核心美德："predictability"（可预测性）是技能设计的根本原则**
- **Model-invoked**：技能带描述，靠模型自主判断触发，消耗context load
- **User-invoked**：`disable-model-invocation: true`，零context load但需人记忆命令
- **Router skill 模式**：技能过多导致认知负担时，用一个"路由技能"做统一入口分流，而非让模型同时权衡N个技能描述

**→ SA 落点**：这是比 obra/superpowers 更精细化的"调用机制设计"层规范（obra偏内容质量，mattpocock偏调用机制）。可直接吸收"model-invoked vs user-invoked"二分法与"router skill"概念，充实 SA 自己 SKILL.md 编写规范。

## 三、技能生命周期分级管理

顶层目录结构：`.agents/`（跨harness共享规范）+ `.claude-plugin/`（Claude Code插件清单）+ `skills/`（6大分类：`deprecated/engineering/in-progress/misc/personal/productivity`）+ `AGENTS.md`/`CLAUDE.md`/`CONTEXT.md` 并存。

`.claude-plugin/plugin.json` 核实：仅约22个"engineering/productivity"分类技能**对外发布进插件包**，`deprecated/in-progress/misc/personal` **不进入插件包**——即"草稿区/生产区分离"的明确分级，避免技能库杂乱。

**→ SA 落点**：反哺 harness workshop repo 的技能生命周期管理模式（草稿→生产两级目录），避免自建技能库变成大杂烩。

## 四、双轴并行子代理审查范式（Code Review 技能）

`skills/engineering/code-review/SKILL.md`：采用"Standards轴 + Spec轴"双维度并行子代理审查，两个子agent互不污染上下文，最后由主技能聚合结果。

**→ SA 落点**：回答客户"多子代理如何协作而不互相干扰"架构问题的优秀范式案例，可直接搬进 harness workshop 的 subagent 编排示范。

## 五、Codex 端配置极简验证

`skills/engineering/tdd/SKILL.md` 是主体说明；旁边的 `agents/openai.yaml` 可作为 Codex 的 UI/调用策略扩展。该样本只能说明文件职责分层，不能推出某一 host 的配置普遍更简单。

## 六、横向对比表

| 维度 | obra/superpowers | google-deepmind/science-skills | mattpocock/skills |
|---|---|---|---|
| Harness覆盖 | 仅Claude Code | 仅Claude Code | **Claude Code + Codex双支持**（独有） |
| 编写规范深度 | 内容/流程质量为主 | 科研方法论为主 | **调用机制(model/user-invoked)+context load理论**最系统 |
| 生命周期管理 | 无明显分级 | 无明显分级 | **deprecated/in-progress/misc分级+仅部分发布**（独有） |
| 子代理编排 | 有涉及 | 较少 | **双轴并行子代理审查**范式清晰 |

## 七、待办 / 未核实
- 尚未在 workshop repo 实际试点 `.agents/` 目录约定，属于"设计参考"而非"已验证落地"
- Star数为08-04采集时刻值，会自然漂移

## 客户话术
"如果同时面向多个编码 Agent host，建议先把技能主体写成清晰、短小、可审计的 SKILL.md；再按目标 host/version 增加可选扩展配置（例如 Codex 的 agents/openai.yaml），并分别做路由与行为验证。"
