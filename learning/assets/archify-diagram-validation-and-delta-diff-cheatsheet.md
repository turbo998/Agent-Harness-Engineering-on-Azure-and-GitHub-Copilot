<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 架构图工作流增强参考 — 借鉴 Archify 的 Schema 校验 + Delta Diff 机制

> 来源：tt-a1i/archify（⭐7,214 已 API 核实，MIT，2026-07-25 调研）。本文件只提炼"可移植的设计思路"，不建议整体引入该工具本身（详见末尾理由）。

## 一、诊断信息自愈格式（可移植）

Archify 的 schema 校验失败时不是抛一句 "invalid JSON"，而是结构化输出：

```json
{
  "code": "NODE_OVERLAP",
  "subject": "node:api-gateway",
  "evidence": "bbox overlaps node:auth-service by 12px",
  "supportedFixes": ["shift_node", "resize_canvas"]
}
```

**落地建议**：现有 architecture-diagram / drawio-architecture 工作流生成 mermaid/drawio XML 时，若校验失败（节点重叠、连线穿越、标签碰撞），改用同样的四字段格式（code/subject/evidence/supportedFixes）反馈给 LLM，而不是纯文本报错。这样 LLM 自我修复时有明确的候选动作集，减少"瞎猜"轮次。

## 二、Architecture Delta（改造前后对比）设计模式

核心思路（非文本diff，是语义diff）：
1. **canonical化**：排序节点/连线、剥离 meta/output 字段、归一化 URL 与版本号，消除"无意义差异"噪音。
2. **强制唯一 id**：每条 connection 必须有 authored id，禁止靠 label/endpoint 猜测"这是不是同一条线改名了"。
3. **三态输出**：Before / Delta（增/删/改） / After，配 HTML 可视化 + 结构化 sidecar 回执。

**落地建议**：给 SA 的 POC 评审 / PR 前架构对比场景写一个轻量 diff 脚本：
- 输入两版 mermaid/drawio 源文件（需先约定节点/连线 id 规范，如 `id: svc-{name}`）。
- canonical化后按 id 做集合运算（新增/删除/属性变更）。
- 输出结构化 diff 报告，可直接贴进变更说明或 PR description。

**边界**：Archify README 自己明确写"never claim...verified PR impact"——这只是"设计评审辅助"，不是真正的风险分析工具，避免过度包装成"自动化架构合规检查"。

## 三、Repo-Evidence（代码溯源标注）——谨慎评估中

机制：`sources:[{path,line,end_line,label}]`，本地校验 git origin + commit SHA + 行号真实存在，仅支持公开 GitHub repo + architecture 模式。

**潜在SA用途**：技术问答中如果要回答"这个组件对应哪段代码"，理论上可以用类似机制核实引用的代码位置真实存在，避免向客户展示凭空编造的代码引用。

**未核实**：该功能在真实场景下的准确率、是否有误报（比如行号因后续commit漂移）。**建议**：先做一次小范围试验（3-5次真实引用），再决定是否固化为 SA 自己的习惯做法。

## 四、为什么不整体采用 Archify 作为日常出图工具

| 维度 | Archify | SA 现有 draw.io/mermaid 流程 |
|---|---|---|
| 产出格式 | 自包含交互 HTML（含内嵌JS/SVG） | SVG/PNG/drawio XML |
| 企业协作 | 需单独打开HTML | 可直接嵌 Confluence/邮件/PPT |
| 生态成熟度 | 7214★但**未核实**生产稳定性 | SA 已熟练、客户熟悉 |
| 集成方式 | Node CLI + SKILL.md（偏Claude Code/Cursor原生） | 通用，需由所用运行环境控制执行权限 |

**结论**：只借鉴"校验诊断格式"与"Delta diff"两个子能力，不整体替换现有出图工作流。

## 五、编码 Agent Hooks 三态能力核实速查（本晚新增，另详见 coding-agent-hooks-tristack-comparison-cheatsheet.md）

| 能力 | Codex | Claude Code | grok-build (xAI) | Mistral Vibe |
|---|---|---|---|---|
| 可读工具入参 | 已核实 | 已核实 | 已核实 | 已核实 |
| 可拒绝(deny) | 已核实 | 已核实 | 已核实 | 已核实 |
| **可重写参数(rewrite)** | **支持**（`updatedInput`字段） | 不支持（仅allow/deny/ask） | 不支持（仅allow/deny二态） | 支持 |

来源：developers.openai.com/codex/hooks（308→200）、code.claude.com/docs/en/hooks（200）、xai-org/grok-build docs/user-guide/10-hooks.md（200）。均已 curl 核实可达并逐字读取原文。

**SA落点**：客户问"哪个编码Agent CLI的hook治理能力最强"时，"能否重写工具入参而非只能放行/拒绝"是一个具体、可演示的差异化指标，目前已知只有 Codex 和 Mistral Vibe 支持。
