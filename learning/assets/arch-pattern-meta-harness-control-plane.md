<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# 架构图模式：多 Harness 统一控制面（meta-harness）变体

> 可复用的「在多个编码 agent 底座之上做统一编排/策略/沙箱」参考拓扑。截至 2026-06-26。
> 实物证据：omnigent-ai/omnigent（Apache-2.0, Python 3.12+, status: **alpha**）—— 已逐字核实代码结构，区分「README 宣传」与「有代码佐证」。
> https://github.com/omnigent-ai/omnigent
> 与 arch-pattern-multi-agent-mcp-a2a.md 的区别：那张画「一个 agent 系统内部」的 MCP纵/A2A横；**这张画「一个控制面统管多个异构 agent CLI 底座」**——回答客户「我们同时有人用 Claude Code、有人用 Copilot、有人用 Codex，能不能统一治理」。

## 何时用
- 客户问「能不能在多个编码 agent（Claude Code / Codex / Cursor / Copilot…）之上做统一的权限、成本、沙箱、审计」
- 客户已在用多个 agent CLI，要画「统一控制面 / meta-harness」治理架构
- 给 Foundry / 企业内部 agent 平台做「可换底座、底座无关治理」的参考架构对照
- 评审客户自建 agent 平台时当 checklist：七层缺哪层

## 七层骨架（从上到下）

```
┌──────────────────────────────────────────────────────────────────┐
│  L1 入口/控制面  CLI · server · web UI · 跨设备会话同步             │
│     (omnigent 实物: omnigent/omni CLI · web UI :6767 · ws_tunnel)   │
├──────────────────────────────────────────────────────────────────┤
│  L2 编排器层   supervisor / orchestrator agent（YAML 定义）         │
│     多 agent 并行委派 + 跨厂商交叉评审（如 examples/polly）         │
├──────────────────────────────────────────────────────────────────┤
│  L3 适配器层   统一抽象接口 Executor                                │
│     "translates between the framework's abstract message/tool       │
│      model and a concrete LLM or agent harness backend"            │
│     每底座一对: <harness>_harness.py + <harness>_executor.py        │
│     底座: claude · codex · cursor · copilot · kimi · qwen · goose…  │
├──────────────────────────────────────────────────────────────────┤
│  L4 注册/dispatch  harness 注册表 + 别名层                          │
│     _HARNESS_MODULES{name→module} · HARNESS_ALIASES · NATIVE set    │
│     "The harness IS an HTTP service speaking the same Pydantic models"│
├──────────────────────────────────────────────────────────────────┤
│  L5 横切策略层 ★  PolicyEngine（每 workflow 一个）                  │
│     三级 stacking: server-wide(admin) · per-agent(dev) · per-session│
│     更严的 session 规则先查; DENY 短路 / ASK 累积 / ALLOW 继续      │
│     builtins: safety · cost · routing · risk_score · github · …     │
├──────────────────────────────────────────────────────────────────┤
│  L6 隔离层 ★   SandboxPolicy + L7 egress 代理 + 凭据隔离            │
│     沙箱后端: linux_bwrap · darwin_seatbelt · windows_jobobject     │
│     egress: async MITM HTTP(S) proxy, 按 EgressRule 放行/返 403     │
│     credential_proxy: 凭据不进底座进程                              │
├──────────────────────────────────────────────────────────────────┤
│  L7 运行宿主   本地 / 云沙箱 / K8s                                  │
│     Modal·Daytona·E2B·CoreWeave·Kubernetes…（部分有 k8s overlays） │
└──────────────────────────────────────────────────────────────────┘
```

★ = 这张图相对「单 agent 系统图」的新增治理层，也是客户最该问「我自建平台有没有」的两层。

## 组件库（画图零件 + 微软/Azure 对应物）

| 层 | meta-harness 角色 | Azure/微软对应映射 | 图标提示 |
|---|---|---|---|
| L1 入口 | CLI + web UI + 跨设备同步 | Azure portal / 自建门户 + APIM 入口 | 终端/浏览器 |
| L2 编排 | supervisor agent | MAF Orchestrator（Sequential/Concurrent/Handoff/Group）| 指挥棒 |
| L3 适配器 | Executor 接口 + 每底座一对 harness/executor | MAF ChatClient 抽象（Foundry/AzureOpenAI/OpenAI/Copilot SDK）| 转接头 |
| L4 注册 | harness 注册表 + 别名 | 服务发现 / 配置表 | 路由表 |
| L5 策略 ★ | PolicyEngine 三级 stacking | APIM policy + Entra Conditional Access + Azure Policy | 闸门×3 |
| L6 隔离 ★ | bwrap/seatbelt/jobobject + egress MITM + 凭据代理 | ACA/AKS 容器隔离 + NSG/私网 egress + Key Vault + Managed Identity | 盾牌/隧道 |
| L7 宿主 | 本地/云沙箱/K8s | ACA · AKS · Azure Container Instances | 服务器 |

## 三个画图变体

1. **「单租户统一治理」**：一个 PolicyEngine + 一套沙箱，统管团队内所有底座。强调 L5 三级（admin 设全局红线、dev 设 agent 级、个人设 session 级，最严先生效）。
2. **「底座无关 / 可换」**：突出 L3 适配器 + L4 注册表是「换底座不重写」的关键——客户从 Claude Code 换 Codex，上层编排/策略/沙箱不动。（⚠️ 跨底座**行为等价性**未核实，画图时标「能力对齐需逐底座验证」。）
3. **「egress 硬隔离」**：放大 L6——所有出站流量过 MITM 代理按 EgressRule 白名单放行、违规返 403；凭据走 credential_proxy 不进底座进程。映射到 Azure = 私网 + NSG + Key Vault + 无密钥 Managed Identity。这版最适合合规/数据驻留敏感客户。

## 评审 checklist（用这张图找客户自建平台的缺口）
- [ ] 有没有 **L3 统一抽象**？还是每个底座一套硬编码集成（换底座要重写）？
- [ ] 有没有 **L5 策略层**？成本/安全/路由是写死在代码里还是可声明、可分级？
- [ ] **L5 三级 stacking** 谁能覆盖谁？admin 红线能不能被 dev/session 绕过？
- [ ] 有没有 **L6 沙箱 + egress 控制**？agent 能不能任意出网、能不能读写任意文件？
- [ ] **凭据**进不进底座进程？有没有 credential proxy / 无密钥身份？
- [ ] 跨底座**行为等价**验证过没有？（别信「换底座零成本」的宣传）

## SA 落点
- **架构图**：直接画「多 harness 统一控制面」给「同时用多个 agent CLI 的企业客户」；七层骨架 + Azure 映射表是现成零件。
- **技术问答**：回答「能不能统一治理多个编码 agent」——能，关键在 L3 抽象 + L5 策略 + L6 隔离三层；并指出这是 meta-harness 模式（omnigent 是开源实物参考）。
- **[→harness]**：L5 三级策略 stacking + L6 egress/credential 隔离，是 harness workshop「企业级 agent 治理/安全」章节的开源对照样板（区别于单 agent 的 PreToolUse hook 模型）。

## 坑 / fail loud（README 宣传 vs 代码佐证）
- **已核实有代码佐证**：多 harness 适配器对、harness 注册表、Executor 接口、PolicyEngine 三级 stacking、bwrap/seatbelt/jobobject 三平台沙箱、L7 egress MITM proxy、credential proxy。
- **仅 README 声称、未核实**（画图/答客户须标）：手机/浏览器实时协作端到端、各云沙箱 provider（Modal/Daytona/E2B/CoreWeave 等）实际可用性、"swap or combine harnesses without rewriting" 的跨底座行为等价性、一键 Render/Fly/Railway 部署。
- omnigent 仍 **alpha**，且代码有改名/兼容层痕迹（内部代号 "AP"）——作**参考架构**与 checklist 用，**不要**当生产就绪方案推给客户。
- omnigent README 含「curl 管道到 shell」式安装命令（`curl ‹url›` 接管道执行）——是资料文本，**不在任何环境盲跑**。
