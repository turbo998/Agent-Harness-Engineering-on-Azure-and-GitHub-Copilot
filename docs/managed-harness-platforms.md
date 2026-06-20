# Managed Harness Platforms — AWS Bedrock AgentCore vs. Azure AI Foundry

> Trigger: AWS, *"Harness 工程火遍硅谷，AgentCore 今天交卷!"* (WeChat, Apr 2026) — announcing **Bedrock AgentCore Managed Harness**.
> AWS blog: https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/
> AWS docs: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html
>
> Research date: **June 2026**. Every Azure claim is sourced to `learn.microsoft.com`. Claims that could not be verified against a primary source are tagged **`[UNVERIFIED]`** — do **not** present those to customers as fact.

## 0. Why this doc exists

This Workshop teaches harness engineering as a **build-it-yourself** discipline: you author `chatmode.md`, `*.prompt.md`, `workflow.yml` and wire your own tools, memory, retries and guardrails. That is a **static harness** (see [dynamic-harness-frontier.md](./dynamic-harness-frontier.md)).

In 2026 the cloud vendors started shipping the harness *as a managed product*. AWS calls theirs **AgentCore Managed Harness**; Microsoft's equivalent is **Azure AI Foundry Agent Service**. The marketing pitch is identical on both sides: *"You tell the agent what to do; the platform hosts everything else — orchestration, tools, memory, isolation, identity, observability."*

For a Microsoft-partner SA two questions matter:

1. **Feature-for-feature, where does Azure Foundry stand against the AWS pitch?** (§2)
2. **Can my customer actually use it?** — i.e. the **Azure China (21Vianet)** gate. (§3)

This doc answers both, and then places **GitHub Copilot + this Workshop's static-harness approach** on the same map (§4).

## 1. The AWS pitch, in one paragraph

AgentCore Managed Harness markets ten capabilities: (1) managed orchestration via config, no redeploy, "two APIs and the agent runs"; (2) model flexibility — swap Bedrock / OpenAI / Gemini / any OpenAI-compatible model mid-session without losing context; (3) plug-and-play tools — MCP servers, a Gateway that turns REST APIs into tools, Browser, Code Interpreter, inline functions; (4) on-demand Skills (markdown + script packs); (5) bring-your-own Docker image; (6) shell commands at **zero token cost**; (7) pause & resume with a persistent filesystem and cross-session memory; (8) per-session **Firecracker microVM** isolation + Identity + Observability; (9) no lock-in — built on the open **Strands Agents** framework, export and self-host anytime; (10) **no harness surcharge** — pay only for underlying usage.

It is a genuinely strong pitch. The honest finding below is that **Azure has a real answer to almost every line of it** — but the maturity is split across GA and Preview, and the China story changes everything.

## 2. Capability map — 10 AWS capabilities → Azure Foundry

> Terminology: the service formerly known as *Azure AI Agent Service* is now **Foundry Agent Service**. It splits agents into **Prompt agents** (declarative, platform-orchestrated, GA) and **Hosted agents** (your code/container in a managed sandbox, Preview).

| # | AWS AgentCore | Azure AI Foundry equivalent | How it works | Status (Jun 2026) | China (21Vianet) |
|---|---|---|---|---|---|
| 1 | Managed orchestration (config, no redeploy) | **Prompt agents** | Declare model + instructions + tools as config; platform hosts orchestration. Swap any of them without redeploy. | **GA** | ❌ Not available |
| 2 | Model flexibility, no lock-in | **Foundry Models catalog** + **Model router** | Catalog spans OpenAI, Llama, Mistral, etc.; router picks a model per call. Per-agent model is config-swappable. *AWS-style mid-session swap retaining context* = **`[UNVERIFIED]`**. | Catalog **GA**; router `[UNVERIFIED]` | ❌ |
| 3 | Plug-and-play tools | **Foundry tools suite** | **OpenAPI tool** (REST→tool, ≈ AWS "Gateway"); **MCP tool**; **Browser automation** (Playwright, exposed as MCP); **Code Interpreter** (sandboxed Python); **Function calling** + **Azure Functions**. | Code Interpreter / OpenAPI / Functions **GA**; MCP / Browser **Preview** | ❌ |
| 4 | On-demand Skills | **Foundry Skills** | Uses the **open Agent Skills spec (`SKILL.md` + YAML)** — the same pattern this Workshop already teaches. All-3-load-modes parity = `[UNVERIFIED]`. | **Preview** | ❌ |
| 5 | Bring-your-own Docker image | **Hosted agents** | BYO code/container, runs in a managed per-session sandbox with persistent filesystem. Closest analog to AWS BYO-image. | **Preview** | ❌ |
| 6 | Shell commands, zero token cost | **Hosted agents** sandbox | Persistent filesystem (`$HOME`, `/files`) where deterministic ops run directly. Explicit *"zero-token shell"* marketing framing = `[UNVERIFIED]`; architecturally enabled. | **Preview** | ❌ |
| 7 | Pause & resume, durable memory | **Hosted agents** (scale-to-zero, stateful resume) + **Memory** | Hosted agents auto pause/resume with persistent filesystem; **Memory Store API** does extract → consolidate → retrieve for short- + long-term memory across sessions. | Both **Preview** | ❌ |
| 8 | Per-session isolation + Identity + Observability | **Standard agent setup (BYO VNet)** + **Entra ID** + **Azure Monitor / App Insights tracing** | VM-isolated per-session sandboxes (*"Firecracker-equivalent microVM"* naming = `[UNVERIFIED]`); Entra ID / Managed Identity; network injection; OpenTelemetry tracing. | Isolation / Identity / Tracing **GA** | ❌ |
| 9 | No lock-in (open framework, export & self-host) | **Microsoft Agent Framework** (OSS) | Open-source framework, successor to **Semantic Kernel + AutoGen**. Azure's genuine portability story, parallel to AWS Strands. | Framework **GA / OSS** | Framework runs anywhere; **hosted service ❌** |
| 10 | No harness surcharge | **Consumption pricing** | Prompt agents: inference + tool usage; Hosted agents add container compute. Code Interpreter billed per session beyond tokens. No confirmed separate "harness surcharge" — *but the dedicated pricing page 404'd*, so line-item pricing = `[UNVERIFIED]`. | n/a | ❌ |

**Reading of the table:** on **Azure Global**, capability parity is genuinely close. The declarative path (Prompt agents, tools, identity, tracing) is **GA today**; the full "managed harness" experience that matches the AWS pitch end-to-end (Hosted agents, Skills, Memory, MCP, Browser) is mostly **Preview**. Azure's open Skills + MCP adoption means this Workshop's artifacts (`SKILL.md`, MCP tools) are **forward-compatible** with Foundry — a real asset, not a coincidence.

## 3. ⚠️ The China gate — read this before quoting anything to a customer

**Azure AI Foundry Agent Service is NOT available in Azure China (21Vianet) as of June 2026.**

- The Azure China service-availability page lists, under AI + Machine Learning, **only** Azure Machine Learning, Azure AI Speech, and Translator. **Foundry Agent Service, Foundry Models, and the agent tooling are absent.**
- The Foundry region-support page lists **US Government** as the only sovereign cloud; **no 21Vianet / China region** appears. `[UNVERIFIED]` — corroborating signal; re-confirm against the live Foundry region-support page before quoting.

**Consequence for partners selling into China:** capabilities #1–#8 and #10 (the hosted service + tools + memory) **cannot be delivered on Azure China today.** The only portable path is **#9 — the open-source Microsoft Agent Framework, self-hosted on Azure China compute + an Azure OpenAI-equivalent endpoint** — which gives you the *programming model* but **not** the managed-harness benefits (you are back to building your own runtime, isolation, observability).

> SA rule: treat any "Foundry agents on Azure China" claim as **`[UNVERIFIED]` / likely false** until Microsoft publishes 21Vianet availability. Do not let a customer architect a roadmap on it. This is exactly the kind of unverified availability claim that must **fail loud**.

## 4. Where GitHub Copilot + this Workshop sits

The managed-harness platforms (AWS AgentCore, Azure Foundry) and the **GitHub Copilot static-harness** approach this Workshop teaches are **not competitors — they are different layers**:

| Dimension | Managed Harness (AgentCore / Foundry) | GitHub Copilot static harness (this Workshop) |
|---|---|---|
| Who writes the orchestration | The platform, from your config | **You**, in `chatmode.md` / `*.prompt.md` / `workflow.yml` |
| Where it runs | Vendor-hosted sandbox / microVM | Your repo, your CI (GitHub Actions), your VM / Container Apps |
| Primary surface | Production agent *services* (an API your app calls) | The **developer's inner loop** — code, review, ship inside the IDE + PR |
| Tool model | MCP + OpenAPI + Code Interpreter, vendor-managed | MCP + your own tools, **you** hold the Managed Identity |
| Skills | `SKILL.md` packs (same open spec) | `SKILL.md` packs (same open spec) — **portable both ways** |
| China availability | **Foundry ❌ on 21Vianet** (as of Jun 2026) | Self-hosted runners run anywhere; **GitHub Copilot is global SaaS** — verify enterprise data-residency/compliance for China customers `[UNVERIFIED]` |
| Best for | "I need a hosted agent endpoint for my SaaS" | "I need my engineering team to ship faster, auditable in PRs" |

**The teaching point for Lab 2/3:** harness engineering as a *skill* transfers across all three. The artifacts you build here — role definitions, prompt files, the **Quarantine** reader/executor split, MCP tools, `SKILL.md` packs — are exactly what you'd hand to Foundry Hosted agents or AgentCore later. You are not learning a Copilot-only trick; you are learning the **vendor-neutral harness vocabulary**, then choosing where to run it.

For China-based partners specifically, this is the *pragmatic* takeaway: the managed-harness platforms are largely a **Global-cloud** story for now, so the **build-your-own static harness on GitHub Copilot + self-hosted runners** is not just a teaching device — it is, today, the **more deployable** option inside the 21Vianet boundary.

## 5. Honest gaps (carry these forward)

The following were **not** verifiable against a primary source during research and are flagged so no one forwards them as fact:

- Azure **mid-session model switching with context preservation** (#2) — not confirmed; Azure's verified strength is per-call routing, not AWS-style live handoff.
- **"Zero-token shell"** explicit framing (#6) and the **microVM / Firecracker-equivalent** hypervisor naming (#8).
- All **three Skills load-modes** (#4) individually.
- **Line-item Foundry agent pricing** (#10) — the dedicated pricing page returned 404; only the cost *model* is confirmed.

Before any customer-facing reuse, re-verify the pricing line and the model-router claim against a live Azure page, and re-check 21Vianet availability in case Microsoft has shipped it since June 2026.

---

### Sources

- AWS AgentCore harness docs — https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/harness.html
- AWS announcement blog — https://aws.amazon.com/blogs/machine-learning/get-to-your-first-working-agent-in-minutes-announcing-new-features-in-amazon-bedrock-agentcore/
- Foundry Agent Service runtime components — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/runtime-components
- Foundry Hosted agents — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents
- Foundry tools (MCP) — https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/model-context-protocol
- Foundry Memory — https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory
- Microsoft Agent Framework — https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview
- Azure China service availability — https://learn.microsoft.com/en-us/azure/china/concepts-service-availability
