# Harness Engineering on GitHub Copilot: Design Principles

## What Is Harness Engineering (Definition)

Harness Engineering is a systematic methodology for AI collaboration. Unlike simple prompt engineering, it uses **structured rules, roles, and workflows** to constrain and guide AI agent behavior, enabling stable, predictable, and safe operation within team engineering practices.

Core idea: It's not about writing a good prompt — it's about building a **harness system** that lets AI deliver maximum value within well-defined boundaries.

## Why Harness > Prompt Engineering (Comparison)

| Dimension | Prompt Engineering | Harness Engineering |
|-----------|-------------------|-------------------|
| Scope | Single conversation | Entire project lifecycle |
| Reusability | Low, depends on individual experience | High, team-shared config files |
| Consistency | May vary each conversation | Rule layer ensures consistent behavior |
| Safety | Relies on human memory | System-level guardrails enforced |
| Collaboration | Single user | Multi-agent collaboration with clear roles |
| Auditability | None | Rules and processes reviewable & version-controlled |

**Conclusion**: Prompt Engineering is a skill; Harness Engineering is an engineering discipline.

## 3-Layer Harness Model

```
┌─────────────────────────────────────────┐
│  Workflow Layer                          │
│  .github/prompts/*.prompt.md            │
│  Define task flows: Think→Plan→Build→Test│
├─────────────────────────────────────────┤
│  Role Layer                             │
│  .github/agents/*.agent.md              │
│  Define expert roles: architect, etc.   │
├─────────────────────────────────────────┤
│  Rule Layer                             │
│  .github/copilot-instructions.md        │
│  Global rules: code style, security,    │
│  quality standards                      │
└─────────────────────────────────────────┘
```

**Bottom-up enforcement**: The Rule Layer is the foundation — all agents and workflows must comply. The Role Layer defines expert perspectives. The Workflow Layer orchestrates specific tasks.

### Rule Layer — `copilot-instructions.md`
- Project-level global rules, effective across all Copilot interactions
- Includes: language standards, security constraints, code quality standards, collaboration protocols

### Role Layer — Custom Agents (`.agent.md`)
- Each agent file defines an expert role
- Clearly defines role boundaries, domain expertise, and available tools
- Examples: `architect.agent.md`, `security-reviewer.agent.md`

### Workflow Layer — Prompt Files (`.prompt.md`)
- Define reusable task templates
- Orchestrate multi-step processes
- Can reference specific agents to execute subtasks

## Multi-Role Agent Philosophy

Following the gstack design philosophy: **each role = one expert perspective**.

| Role | Responsibility | Analogy |
|------|---------------|---------|
| Architect | System design, tech selection, architecture decisions | CTO / Tech Director |
| Developer | Feature implementation, code writing | Senior Engineer |
| Reviewer | Code review, quality gate | Tech Lead |
| Security Reviewer | Security audit, vulnerability detection | Security Engineer |
| Tester | Test strategy, test case authoring | QA Engineer |

**Key Principles**:
- Clear boundaries between roles — no overstepping
- Tasks passed between roles via `@mention` mechanism
- Each role carries its own system prompt and tool permissions

## Sprint Process: Think → Plan → Build → Review → Test → Ship

Adapted from gstack's development process, tailored for the GitHub Copilot environment:

1. **Think** — Understand requirements, analyze constraints, identify risks
2. **Plan** — Design solutions, break down tasks, determine implementation path
3. **Build** — Write code, following all Rule Layer standards
4. **Review** — Invoke the reviewer agent for code review
5. **Test** — Run tests, ensure coverage, verify edge cases
6. **Ship** — Submit PR with full description, await human confirmation

Each step has a corresponding prompt file that can drive automated execution.

## Safety & Guardrails Philosophy

Safety is not an add-on feature — it's **part of the system architecture**.

### Hard Guardrails (Never Violate)
- ❌ Never delete files (unless user explicitly confirms)
- ❌ Never force-push to main/master
- ❌ Never modify `.env` or credential files
- ❌ Never expose stack traces in API responses

### Mandatory Actions
- ✅ Run tests before committing
- ✅ Sanitize all user inputs
- ✅ Error messages must be actionable (describe the problem + suggest a fix)

### Design Principles
- **Fail-safe by default**: When uncertain, choose the safer behavior
- **Explicit > Implicit**: Ask one more question rather than silently executing dangerous operations
- **Audit trail**: All important decisions are traceable

## Comparison: gstack (Claude Code) vs This Workshop (GitHub Copilot)

| Dimension | gstack (Claude Code) | This Workshop (GitHub Copilot) |
|-----------|---------------------|-------------------------------|
| AI Engine | Claude (Anthropic) | GPT-4o / Claude (via Copilot) |
| Config Files | `CLAUDE.md` + `ETHOS.md` | `copilot-instructions.md` |
| Role Definitions | SubAgents in CLAUDE.md | `.agent.md` files |
| Workflows | Bash scripts + prompts | `.prompt.md` files |
| Core Principles | Boil the Lake, Search Before Building, User Sovereignty | Completeness First, Search Before Building, User Sovereignty |
| IDE Integration | Terminal-based (CLI) | VS Code native integration |
| Multi-Agent | Via SubAgent directives | Via `@agent` mentions |
| Best For | Full-stack dev, complex refactoring | Daily development, team collaboration, code review |
| Learning Curve | Steeper (requires CLI workflow knowledge) | Gentler (in-IDE operations) |
| Enterprise Fit | Small teams / individuals | Enterprise-grade (GitHub ecosystem integration) |

**Core consensus**: Both agree — AI agents need structured constraints to operate reliably in engineering practice.

## Enterprise Team Best Practices

### 1. Version Control Your Harness
- Put `copilot-instructions.md`, `.agent.md`, `.prompt.md` all under Git
- Modify rules via PR review, not ad-hoc edits

### 2. Progressive Adoption
- Week 1: Configure only `copilot-instructions.md` (Rule Layer)
- Week 2: Add 2–3 core agents (Role Layer)
- Week 3: Author common workflow prompts (Workflow Layer)

### 3. Team Alignment
- Regularly review and update harness configuration
- Include harness training in new member onboarding
- Build a harness template library for team reuse

### 4. Measure & Improve
- Track bug rates for AI-assisted code
- Collect team feedback on agent behavior
- Iterate on guardrails and quality standards regularly

### 5. Security & Compliance
- Use stricter guardrails for sensitive projects
- Periodically audit agent behavior logs
- Ensure AI-generated code passes security scans

---

> *"Good tools need good harnesses. Harness Engineering is the methodology that turns AI into a reliable teammate."*
