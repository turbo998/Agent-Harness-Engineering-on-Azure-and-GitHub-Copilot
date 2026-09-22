<!-- learning-asset-sanitized: v1 -->
> **发布界定 / Publication boundary**
>
> 本文是由历史研究快照整理出的补充学习材料。原始资料中的 HTTP 200、抓取时间或“已核实”表述只代表当时的来源可达性/文本核对，不代表本次发布时已经重新核验；本文也不是正式实验报告、生产部署建议或合规结论。
>
> 未对其中的命令、代码块、外部仓库、云资源、生产环境或合规控制做本次实机验证。请在独立测试环境中重新验证后再用于客户/生产场景。

# Agent 自主安全扫描 Harness 速查（源自 anthropics/defending-code-reference-harness 深挖，2026-07-16）

> 来源：github.com/anthropics/defending-code-reference-harness（⭐6482/🍴526，2026-07-16 API 核实；README 明确"not maintained, not accepting contributions"——**参考实现非生产产品**，license=`other`/NOASSERTION 非标准OSS，商业二次分发需法务复核）。
> 官方托管商用替代：claude.com/product/claude-security（配套博客 claude.com/blog/using-llms-to-secure-source-code）。
> 主+子agent双重curl核实，未执行仓库内任何脚本（vp-sandboxed/setup_sandbox.sh 等均未运行）。

## 一句话定位
业界参考架构证明："Agent 自动安全扫描"可拆成 **威胁建模→扫描→分诊→修补** 四段能力，核心工程原则是**安全约束写死在代码层（沙箱隔离/write-scope白名单），不能只靠 prompt 要求模型"不要做什么"**。

## 四段能力拆解（可直接讲给客户）

| 阶段 | 输入 | 核心机制 | 关键安全设计 |
|---|---|---|---|
| **威胁建模**(`/threat-model`) | 代码目录+可选CVE历史/design doc | 三模式：interview(四问框架访谈)/bootstrap(5阶段并行研究群自动推导)/两者链式；区分"威胁"(不因单点修复消失)与"漏洞"(证据) | Step 0 强制声明**只做静态分析**，不build/execute/fuzz/联网 |
| **扫描**(`/vuln-scan`) | 威胁模型的入口点/信任边界表 | **非regex/AST，是多个Task子代理并行做LLM代码阅读式审查**(每focus area一个子代理，上限10并发)；可选第二轮独立confidence打分子代理 | 绝不执行目标代码/虚构行号；findings 永不在此阶段丢弃(丢弃是triage职责) |
| **分诊**(`/triage`) | VULN-FINDINGS.json等 | 六阶段：归一化→去重(确定性+语义)→**对抗式验证**(每候选派生N=3个独立无共享上下文子代理投票+16条FP排除规则)→按前置条件数重新分级→路由owner(CODEOWNERS→git history→路径) | 断点续跑(`.triage-state/`)；分级逻辑=前置条件数+所需权限(0前置+未认证远程=HIGH) |
| **修补**(`/patch`) | TRIAGE.json | 执行验证模式(pipeline crash走build→PoC不再崩→测试通过→新一轮find agent绕不过的验证ladder) 或 静态模式(生成diff子代理+**完全独立看不到finding描述的reviewer子代理**四项审查) | **核心亮点：无`--apply`/`--approve`标志，能力缺失即安全**——不是靠prompt约束"不要自动应用"，而是代码里根本没这个能力，无法被prompt注入利用 |

## Harness 本身架构（7阶段：Build→Recon→Find→Verify/Grade→Dedupe/Judge→Report→Patch）
- 强制 **gVisor**容器隔离（非普通Docker/runc），出网仅限Claude API allowlist proxy
- `bin/vp-sandboxed`唯一入口，脱离沙箱需显式`--dangerously-no-sandbox`覆盖
- Setup阶段(可联网装依赖)与Attack阶段(严格出网限制)分离，构建产出frozen镜像快照

## 可定制性（`/customize`访谈式重写指南）
明确自述"reference不是product，不会在任意代码库开箱即用"。架构地图：
- **必须重写**：find/grade/report/judge/patch的prompt模板 + asan.py解析器 + targets模板
- **完全不变**：cli.py(编排核心)/agent.py(agent runner)/docker_ops.py(容器管理)

## SA 落地方式

### 技术问答话术（"Agent怎么做自动安全扫描"）
"业界参考架构（如Anthropic开源的defending-code-reference-harness）把AI自动安全扫描拆成四段：威胁建模区分威胁与漏洞；扫描是多子代理并行LLM审查而非传统规则引擎；分诊靠对抗式多票验证降噪（默认让validator假设scanner是错的去反驳）；修补只生成diff供人审核、**故意不给自动apply能力**防prompt注入被利用改代码。核心原则：安全约束写在代码层不是prompt层。"

### POC 演示（5分钟内可跑通，不需要沙箱基础设施）
```
/threat-model bootstrap <客户代码目录>
/vuln-scan <客户代码目录>
/triage <目录>/VULN-FINDINGS.json --repo <目录>
/patch ./TRIAGE.json --repo <目录>
```
产出 THREAT_MODEL.md + VULN-FINDINGS.md + TRIAGE.md + 候选diff，视觉冲击力强。
⚠️**不要**用其C/C++ ASAN harness/pipeline做POC——对客户代码库大概率跑不通，且需要完整gVisor+Docker+egress proxy基础设施，落地成本高，仓库不维护不适合生产依赖。

### 架构图素材（三张图）
1. 四阶段流水线图（威胁建模→扫描N并行子agent→分诊去重+对抗验证N票+重排级→修补生成diff+独立reviewer）
2. 安全隔离分层图（Setup可联网→Freeze镜像快照→Attack gVisor+仅API出网→Patch只写PATCHES/无自动apply）
3. 能力矩阵图（只读写文件skill vs 需强隔离的代码执行组件）——讲"权限最小化"的直观素材

## Fail-loud：未核实项
- harness/*.py（cli.py/agent.py/find.py/grade.py等）具体实现代码逻辑未逐字审阅，仅读取SKILL.md转述描述
- targets/(alsa/htslib/drlibs)各Dockerfile/entry.c内容未逐字核实
- LICENSE具体条款文本未读，仅知API标记为`other`/NOASSERTION

[→harness]
