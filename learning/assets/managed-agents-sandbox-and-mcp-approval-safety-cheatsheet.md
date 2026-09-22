<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Managed Agents 容器沙箱 + MCP 工具审批/安全护栏 速查表
> 生成日期：2026-08-02（研究快照）｜状态：核实来源见文末，未核实项已标注

## 一、为什么关注这个（SA 落点）
本周三条独立信号指向同一个主题——"给 Agent 更多自主权时，如何设计好隔离与审批边界"：
1. **Anthropic `anthropics/skills` 仓库新增 `managed-agents-environments.md`**（官方仓库，165,624★/19,691★，健康比率≈8.4，2026-07-31前后更新）——讲 Claude 托管 Agent 的容器隔离与代码 clone-to-session 最佳实践。
2. **microsoft/semantic-kernel Python 端新增 MCP 工具审批(approval)回调**（PR#14210，breaking change，2026-07-28）——给高风险 MCP 工具调用加人工审批点。
3. **microsoft-foundry/foundry-samples 发现并修正 content-safety 样例文档错误**（PR#824，2026-07-30）：文档声称无效/占位符 RAI policy ID 会阻断请求，但**实测行为是 fail-open（放行而非拦截）**。

三者共同指向 SA 在客户 POC 里最容易被问到、也最容易踩坑的一类问题：**"Agent 拿到工具执行权限后，出了问题谁能挡住？"**

## 二、三件事分别是什么

### 1. Anthropic Managed Agents 容器隔离模式（官方，未核实版本号具体diff，仅核实仓库与文档存在）
- 来源：https://github.com/anthropics/skills （curl 200 核实可达；具体 managed-agents-environments.md 内容未逐字抓取，**标注：原研究快照中仅确认文档存在与主题，未逐字核实实现细节**）
- 核心思路（据搜索摘要，未逐字核实，需下次深挖坐实）：Agent 运行时代码不直接跑在宿主环境，而是 clone 到隔离 session 容器里执行；容器生命周期与会话绑定，会话结束容器销毁。
- SA 落点：这是"POC 部署"环节被问到"你们的 Agent 会不会跑坏我的服务器"时的标准话术素材——可以类比 Azure Container Apps / ACA 的每-session 容器模式，或 Azure Functions 的沙箱隔离，讲清楚"Claude 官方也是这么做的"。

### 2. Semantic Kernel MCP 工具审批回调（breaking change，2026-07-28，PR#14210）
- 来源：https://github.com/microsoft/semantic-kernel/commit/e78a8f503b387acfe0d25cbcabae59e317c13b5b （curl 核实存在）
- 核心：Python 侧为 Azure AI Agent 新增 MCP 工具调用前的审批(approval)回调 hook，允许在工具真正执行前插入人工确认/自动策略判断。
- ⚠️ 标记为 breaking change，意味着存量代码升级 SK 版本后需要显式适配该回调点（**具体 API 签名原研究快照中未逐字读取代码，需使用前补做**）。
- SA 落点：技术问答高频题"SK Agent 怎么做 HITL（human-in-the-loop）审批高风险工具调用"——现在有了官方一手实现可以引用，而不是只能建议"自己包一层"。

### 3. Foundry content-safety 样例 fail-open 文档错误（安全警示，2026-07-30，PR#824）
- 来源：https://github.com/microsoft-foundry/foundry-samples/commit/f92ce9b68db68b89d943eeae14dfbab7cc2fabab （curl 核实存在）
- 核心：README 此前声称"引用不存在的 RAI（Responsible AI）policy ID 会导致请求失败被阻断"，但实测行为是 **fail-open**——即配置错误时内容审核护栏会被静默跳过，有害内容可能被放行。
- **⚠️ Fail loud 提醒**：如果 SA 手上任何 POC / 客户环境引用了 Foundry content-safety guardrail 样例模式，必须人工核实实际使用的 RAI policy ID 真实有效——**不要假设"配置错了它至少会报错拦下来"**，实际证据是它不会。
- SA 落点：这是一条**可以立刻用在下一个客户 POC 安全评审清单**里的具体检查项，而不是泛泛的"建议做安全测试"。

## 三、组合起来给客户的一句话话术
> "无论是 Anthropic、微软还是你们自己搭的 Agent，'工具调用护栏'从来不是配置完就一劳永逸——容器隔离防的是执行环境跑飞，审批回调防的是恶意/误操作的工具调用，而 content-safety 这类内容护栏本身也可能因为配置错误而悄悄失效（fail-open）。POC 验收清单里这三层必须分别验证，不能只测其中一层就当作全测过了。"

- [ ] Anthropic managed-agents-environments.md 原文逐字核实容器实现细节（原研究快照中仅确认主题存在）
- [ ] SK PR#14210 审批回调 API 签名代码级核实
- [ ] 亲自用一个占位符 RAI policy ID 复现 foundry-samples fail-open 现象，形成可复现验证步骤

## 来源核实记录
| URL | 核实方式 | 结果 |
|---|---|---|
| github.com/anthropics/skills | curl | 200，仓库存在，star/fork 经 API 核实 |
| github.com/microsoft/semantic-kernel/commit/e78a8f5... | curl (GitHub API) | 200，commit 存在 |
| github.com/microsoft-foundry/foundry-samples/commit/f92ce9b... | curl (GitHub API) | 200，commit 存在 |
