<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Claude Code / Agent Harness 驾驭机制速查（2026-07-20）

> 来源：Anthropic 官方博客 https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more （原快照记录响应103→200，发布日期2026-06-18；本次未重新核验）。

## 一、七种"驾驭 Claude Code 行为"机制对照表

| 机制 | 加载时机 | Context成本 | Compaction行为（整理转述，非逐字引用博客原文，机制细节以官方文档为准） | 典型适用场景 | 反模式警示 |
|---|---|---|---|---|---|
| CLAUDE.md | 会话启动即常驻加载 | 每轮都占用token（常驻） | 通常保留在压缩摘要前部（整理转述） | 项目级稳定约定、代码规范、目录结构说明 | ❌不要把"过程性/条件触发"指令塞进CLAUDE.md——会长期占用context |
| Rules(嵌套) | 按目录就近加载 | 仅在相关目录下生效时占用 | 随目录上下文一起管理（整理转述） | 子目录特定约定（如某模块专属规范） | 层级过深/重复率高会增加维护成本 |
| Skills(SKILL.md) | 按需/描述路由触发，可`context:fork`独立运行 ⚠️此细节来自另一来源code.claude.com/docs/en/skills(07-18已核实)，非本次Steering Claude Code博客内容 | 未触发时几乎零成本 | 触发一次性执行，不常驻 | 过程性/多步骤/工具性任务（如"帮我生成PPT"） | ❌不要把"每次都用得到的稳定约定"做成skill——会增加路由不确定性 |
| Subagents | 显式`/subtask`或委派触发 | 独立context，不污染主会话 | 结果摘要回传主会话 | 需要隔离探索/并行任务 | 嵌套上限5层 ⚠️未核实/经验值，未在本次核实来源中找到明确出处，使用前建议官方文档二次确认 |
| Hooks | 特定事件触发（PreToolUse/PostToolUse等）| 极低，事件驱动 | 不受影响 | **硬约束/强制校验**（如禁止某些命令执行） | ❌不要用prompt去实现"必须拦截"的硬约束——用hook |
| Output Styles | 会话级/命令级切换 | 低 | 不受影响 | 统一输出格式（如markdown规范、语言风格） | 不适合放实质性指令，仅管格式 |
| append-system-prompt (CLI flag) | 启动时一次性注入 | 常驻但可控 | 保留在最前 | CI/无人值守场景注入固定角色设定 | 不适合频繁变化的指令 |

**核心判断口诀**：
- 稳定 + 常驻 + 项目级 → CLAUDE.md
- 稳定 + 目录局部 → Rules
- 按需 + 多步骤 + 过程性 → Skill
- 需要隔离/并行 → Subagent
- 硬约束/必须拦截 → Hook（不是prompt！）
- 只管格式不管内容 → Output Style
- CI/无人值守角色注入 → append-system-prompt

## 二、v2.1.215 新信号：Skill自动触发权限收紧
- `/verify` 和 `/code-review` 两个内置skill不再自主触发，必须显式slash command调用
- **SA设计原则**：自研skill默认"显式调用"（`user-invocable`），除非有充分理由才开`disable-model-invocation:false`自动触发，降低误触发/滥用风险

## 三、三厂商编码Agent CLI 横向对比（雏形，待补全）

| 维度 | Claude Code | Codex CLI | Grok Build (xAI) |
|---|---|---|---|
| 最新稳定版(07-20) | v2.1.215 | rust-v0.144.6 | 首个大版本(07-14创建) |
| Skills/委派机制 | SKILL.md + subagent(`/subtask`)+ `/fork`(整会话复制) | AGENTS.md + skill delegation(PR#30274扩大授权范围) | 支持MCP/Skills/插件/Hooks/ACP协议(细节待深挖) |
| 硬约束机制 | Hooks | dangerous-command detection | 未核实 |
| 生态热度(★) | N/A(闭源客户端) | N/A | 19,913★/6天(★/🍴≈5.5:1健康) |
| 官方一手文档 | code.claude.com/docs/en/skills | AGENTS.md规范(agents.md) | 待补 |

## 四、SA 客户话术模板
- "选CLAUDE.md还是Skill" 场景：*"如果这条指令每次对话都用得上、且比较稳定，放CLAUDE.md；如果是按需触发的多步骤流程，做成Skill更省token、路由也更精准。"*
- "硬约束怎么保证一定生效" 场景：*"prompt层面的约束Claude可能在极端情况下绕过，真正要保证'一定拦截'的规则应该用Hook机制，在工具调用前后做硬校验，这是Anthropic官方推荐的模式。"*

## 五、POC 检查清单新增项
- [ ] 检查客户CLAUDE.md/AGENTS.md是否混入了应该做成skill的过程性指令（context常驻浪费）
- [ ] 检查安全硬约束是否只靠prompt表达而未用hook/dangerous-command机制兜底
- [ ] 若客户已用Claude Code，按官方发行说明确认所用版本包含适用的权限逃逸修复，并在隔离环境回归测试。

## 未核实/待补全
- Grok Build的Hooks/ACP协议实现细节未深挖（仅README级别confirm支持）
- 三厂商对比表"硬约束机制"一栏Grok Build待核实
