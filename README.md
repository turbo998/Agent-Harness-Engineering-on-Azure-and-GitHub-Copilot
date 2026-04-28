🌐 English | [中文](zh/README.md)

# Agent Harness Engineering on Azure

> 🚀 180-minute enterprise workshop on Agent Harness Engineering — from basic completions to multi-agent collaboration, master Copilot engineering practices end to end.

## 🆕 What's New in v2

| Dimension | v1 | v2 |
|-----------|----|----|
| Duration | 120 min | **180 min** |
| Labs | 3 Labs | **5 Labs** |
| Agents | 3 Agents | **10 Agents** |
| Prompt Templates | 1 Prompt | **6 Prompts** |

## 📁 File Listing

| File | Description |
|------|-------------|
| `README.md` | Project README (English) |
| `zh/README.md` | Project README (Chinese) |
| `docs/DESIGN.md` | Design Principles (English) |
| `docs/enterprise-deployment-guide.md` | Enterprise Deployment Guide (Azure + VM) |
| `docs/agent-security-sandbox.md` | Agent Security & Sandbox Isolation |
| `zh/docs/` | Chinese versions of all docs |
| `.github/copilot-instructions.md` | Copilot global instructions |
| `.github/agents/*.md` | 10 custom agent definitions |
| `.github/prompts/*.prompt.md` | 6 reusable prompt templates |
| `.github/workflows/ci.yml` | CI/CD pipeline (Azure Container Apps + VM) |
| `SOUL.md` | Agent Soul — identity & personality definition |
| `labs/lab1` … `labs/lab5` | Lab materials |
| `src/` | Sample application source code (Ticket Service) |
| `package.json` | Node.js project configuration |

## 🤖 Agent Table (10 Agents)

| Agent | Role | Responsibility |
|-------|------|----------------|
| `code-reviewer` | Code Reviewer | Review code quality, style, and best practices |
| `architect` | Architect | System design, tech selection, architecture decisions |
| `investigator` | Investigator | Deep-dive root cause analysis and context gathering |
| `release-engineer` | Release Engineer | Manage release process, versioning, and changelogs |
| `product-reviewer` | Product Reviewer | Evaluate feature completeness and UX from a product perspective |
| `performance-engineer` | Performance Engineer | Identify performance bottlenecks and provide optimizations |
| `red-team` | Red Team | Adversarial testing to uncover attack surfaces |
| `security-reviewer` | Security Reviewer | Check for security vulnerabilities and compliance |
| `test-engineer` | Test Engineer | Write and optimize test cases, improve coverage |
| `doc-writer` | Doc Writer | Generate and maintain technical and API documentation |

## 📝 Prompt Template Table (6 Prompts)

| Template | Purpose | Typical Scenario |
|----------|---------|-----------------|
| `add-endpoint` | Add API Endpoint | Quickly generate RESTful routes, controllers, and tests |
| `fix-bug` | Fix Bug | Locate and fix bugs based on issue descriptions |
| `code-review` | Code Review | Structured review and feedback on PRs |
| `design-feature` | Feature Design | Output feature plan, data models, and API definitions |
| `investigate-issue` | Issue Investigation | Analyze logs and stack traces to identify root cause |
| `ship-release` | Ship Release | Generate changelog, tags, and release checklist |

## 🧪 Lab Overview (5 Labs)

| Lab | Topic | Duration | Focus |
|-----|-------|----------|-------|
| Lab 1 | Copilot Basics & Code Completion | 30 min | Inline completion, Chat panel, context awareness |
| Lab 2 | Custom Instructions & Prompt Engineering | 30 min | `copilot-instructions.md`, prompt templates |
| Lab 3 | Agent Collaboration (Agent Mode) | 40 min | Multi-agent invocation, role division |
| Lab 4 | End-to-End Feature Development | 40 min | Full workflow from design to release |
| Lab 5 | Security Review & Red Team | 40 min | Security scanning, adversarial prompts, defense strategies |

## ✅ Prerequisites

- **VS Code** latest version (1.90+ recommended)
- **GitHub Copilot** active license (Individual / Business / Enterprise)
- **Node.js 18+** (for running the sample project)
- Basic Git proficiency

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/<org>/copilot-workshop.git
cd copilot-workshop

# 2. Install dependencies
npm install

# 3. Open in VS Code
code .

# 4. Ensure the Copilot extension is enabled, then navigate to labs/lab-1/ to begin
```

## 📚 References

- [garrytan/gstack](https://github.com/garrytan/gstack) — GStack reference architecture
- [GitHub Copilot Docs](https://docs.github.com/en/copilot)
- [Copilot Extensions & Agents](https://docs.github.com/en/copilot/customizing-copilot)

## 📄 License

[MIT](LICENSE)
