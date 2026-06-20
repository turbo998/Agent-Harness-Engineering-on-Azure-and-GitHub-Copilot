# Lab 2: Harness Engineering — From "Writing Prompts" to "Designing the Agent Runtime Environment"

## Lab Objective

This is not a simple `copilot-instructions.md` introductory lab — it is a **deep-dive Harness Engineering lab**.

After completing this lab, participants should be able to:
1. Understand that **prompt engineering ≠ harness engineering**
2. Identify the main harness components in GitHub Copilot: instructions / prompt files / custom agents / MCP / hooks / tests / lint / repo structure
3. Based on a real project, codify "experience" into a reusable, version-controlled, team-shareable Agent runtime environment
4. Understand why **environment design matters more than prompt tuning** when enterprises adopt Agents

---

## Duration
Recommended upgrade from the original 15 minutes to **20–25 minutes**

If the total workshop must stay within 120 minutes, options include:
- Do the **core version in 15 minutes** during the workshop
- Leave the advanced parts as a **post-workshop extension / additional 10-minute discussion**

---

## Why Go Deeper on This Topic?

Many teams' understanding of Harness Engineering is still stuck at:

> "Oh, it's just writing a few more instructions."

That's far too shallow.

More accurately:

> **Harness Engineering = Designing the Agent's working environment so it's easier to do the right thing, harder to do the wrong thing, and able to self-correct when it does make mistakes.**

This means shifting attention from "how to write a cleverer prompt" to:
- Is the repository structure clear?
- Can constraints be mechanically enforced by tools?
- Is there a fast feedback loop (test/lint/typecheck)?
- Is there role separation and handoff?
- Can high-frequency tasks be templatized?

---

## Industry & GitHub Reference Resources

For this lab, instructors should first give participants an "industry reference map" to show that this isn't something invented on the spot — it's the direction the entire Agent engineering practice is converging toward.

### Recommended Reference Sources

#### 1. `github/awesome-copilot`
GitHub official/community high-visibility resource collection covering:
- instructions
- custom agents
- skills
- hooks
- workflows
- plugins

**How to frame it in the workshop:**
> GitHub is evolving Copilot customization from "scattered tips and tricks" to "composable engineering assets."
> The instructions / agents / prompt files we're building in today's lab are essentially the smallest deployable units of this ecosystem.

#### 2. `walkinglabs/awesome-harness-engineering`
A great "harness engineering reference guide" that breaks the field into:
- context / memory
- constraints / guardrails
- specs / agent files
- evals / observability
- runtimes / harnesses

**How to frame it in the workshop:**
> A harness is not a single file — it's an entire layer of system design.
> What we're doing today in GitHub Copilot is the layer closest to enterprise dev teams within that larger framework: repo-local harness.

#### 3. GitHub Copilot Customization Handbook
This material clearly organizes GitHub Copilot's customization mechanisms:
- Instructions = always-on context
- Prompt Files = on-demand reusable workflows
- Custom Agents = named personas with scoped rules/tools
- MCP = external capability extension

**How to frame it in the workshop:**
> Not all rules should go into a single instructions file.
> You should split them by: always-on rules / on-demand templates / role boundaries / external capabilities.

#### 4. AgentPatterns / HumanLayer / OpenAI articles on Harness Engineering
These materials share a core consensus:

> **Poor results are usually not because the model isn't good enough — it's because the harness isn't good enough.**

In other words, if the repository lacks:
- Type constraints
- Test feedback
- Structured rules
- Task templates
- Role boundaries

Then switching to a more powerful model just means it will "make mistakes more confidently."

---

## Core Concept: From Prompt Engineering to Harness Engineering

### The Prompt Engineering Approach
```text
Please help me elegantly, safely, and following standards to add an API, and supplement tests.
```

Problems:
- One-shot
- Unstable
- Not reusable across people
- May not work in the next conversation
- Agent drifts in long sessions

### The Harness Engineering Approach
Break the above requirements into different layers:

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| Always-on rules | `copilot-instructions.md` | Project-level standards |
| Role boundaries | `custom agents` | Who can modify code, who only reviews |
| Standard task templates | `prompt files` | Standardize high-frequency tasks |
| External capabilities | `MCP` | Access additional tools/APIs |
| Feedback loop | tests / lint / CI | Automatic back-pressure constraints for the agent |
| Architecture constraints | repo structure / naming | Limit the error search space |

**In one sentence:**
> Prompts are one-shot conversation techniques; harnesses are long-term reusable production environment designs.

---

## Instructor: Start with a Counter-Example

Let participants see first: **why prompts alone aren't enough.**

### Counter-Example Prompt
```text
Implement a new endpoint cleanly and safely.
```

This prompt looks fine, but too many things are left undefined:
- What does "cleanly" mean?
- What's the standard for "safely"?
- Which test framework to use?
- Can new packages be installed?
- What's the boundary between modifying production code and test code?
- What format for the PR description?

So the Agent can only "guess."

**The goal of Harness Engineering is: turn what used to be guessing into structured constraints.**

---

## The Most Important Harness Components in GitHub Copilot

### 1. Custom Instructions
File: `.github/copilot-instructions.md`

Purpose: Project-level always-on rules, automatically injected into all Ask / Plan / Agent conversations.

Good for:
- Tech stack constraints
- Architecture principles
- Testing/error handling standards
- PR/commit conventions

Not good for:
- Minor syntax preferences that can be mechanically enforced by lint
- Task requirements that differ every time
- Overly long, fragmented checklists

---

### 2. Prompt Files
File: `.github/prompts/*.prompt.md`

Purpose: Templatize high-frequency tasks, triggered on demand.

Good for:
- "Add an API"
- "Generate PR description"
- "Do a security review"
- "Do a migration"
- "Generate release notes"

---

### 3. Custom Agents
File: `.github/agents/*.md` or `.agent.md`

Purpose: Define specialized roles, tool boundaries, and behavior boundaries.

Good for:
- test engineer
- security reviewer
- docs writer
- planner
- refactoring specialist

---

### 4. MCP / External Tools
File: `.vscode/mcp.json` (or user-level config)

Purpose: Extend the Agent's available capabilities.

Good for:
- Querying internal documentation
- Calling APIs
- Accessing issue trackers
- Calling test environments / databases / design system docs

---

### 5. Backpressure (Feedback Pressure)
This isn't a file — it's a feedback system:
- `npm test`
- lint
- typecheck
- CI
- pre-commit hook

A critical principle in Harness Engineering:

> **Let the Agent hit clear errors on its own, then self-correct.**

Without these mechanisms, all errors must be caught by human review, which is far less efficient.

---

## Lab Design: Three-Layer Progressive Harness Building

This lab has three layers:

1. **Rule Layer**: First define always-on engineering constraints
2. **Role Layer**: Then define different Agents' responsibility boundaries
3. **Workflow Layer**: Finally define high-frequency task templates

That is:

```text
Rule Layer → Role Layer → Workflow Layer
```

---

# Part A: Rule Layer

## Step 1: Create a "Project Constitution" Style copilot-instructions.md

In the `lab-starter` directory, create or update:

```text
lab-starter/.github/copilot-instructions.md
```

Recommended upgraded content:

```markdown
# Ticket Service Engineering Rules

## Architecture
- This project is a small Node.js Express service.
- Keep business logic in `src/ticketStore.js`.
- Keep HTTP routing logic in `src/app.js`.
- Reuse existing error classes (`ValidationError`, `NotFoundError`) for expected failures.

## Language & Framework
- Use JavaScript (CommonJS) only.
- Follow the existing Express.js patterns in this repository.
- Use `node:test` and `node:assert/strict` for tests.
- Do not introduce Jest, Mocha, TypeScript, or new frameworks.

## Implementation Constraints
- Every new endpoint MUST include corresponding tests.
- Input validation failures MUST return HTTP 400 with JSON `{ "error": "..." }`.
- Not found cases MUST return HTTP 404 with JSON `{ "error": "..." }` when appropriate.
- Do NOT install new npm packages unless the user explicitly asks.
- Prefer small focused functions and reuse existing code paths where possible.

## Review Expectations
Before declaring a task complete:
1. Run tests
2. Check whether edge cases were covered
3. Summarize changed files
4. Explain any trade-offs or limitations

## Security
- Never expose stack traces in API responses.
- Validate all externally provided inputs.
- Prefer explicit validation over implicit assumptions.

## PR Output Format
When asked for a PR description, always include:
- Problem
- Solution
- Test Coverage
- Verification Steps
```

### Instructor Teaching Points

Don't present it as a "prompt file" — present it as:

> This is a project-level Agent operating constraint.
> It's not telling the Agent "help me do one thing" — it's defining **how the Agent works long-term**.

### Insights from Popular GitHub Repos

Referencing `github/awesome-copilot` and the Copilot Customization Handbook, guide participants to understand:
- Instructions are **always-on context**
- They're best suited for **project-level consensus**, not one-off task details

---

## Step 2: Run a "Weak Harness vs Strong Harness" Comparison

### Prompt A (prompt only, no harness)
```text
Add a PUT /tickets/:id endpoint.
```

### Prompt B (with harness)
Same input:
```text
Add a PUT /tickets/:id endpoint.
```

### What to Observe
Have participants compare:
- Did it automatically think to add tests?
- Did it follow the existing error handling style?
- Did it try to install new packages?
- Did it provide a more structured delivery summary?

### Learning Point
**The best harness makes the same prompt more stable across different people.**

---

# Part A+: Soul Layer — Defining Agent Identity & Personality

## The Missing Layer: From Rules to Identity

The Rule Layer tells the Agent **what constraints to follow**. But there's a deeper question:

> **Who is the Agent? What does it value? How does it behave when rules don't cover a situation?**

This is the **Soul Layer** — inspired by production AI agent platforms (like Hermes Agent's `SOUL.md`) that mount a personality/identity file into every agent instance.

### Why It Matters

| Without Soul | With Soul |
|-------------|-----------|
| Agent follows rules mechanically | Agent has judgment aligned with team values |
| Ambiguous situations → random behavior | Ambiguous situations → predictable defaults |
| Different agents feel disconnected | Unified team personality across all agents |
| Rules grow endlessly trying to cover every case | Values + principles handle the long tail |

### Step 2.5: Create a SOUL.md

Create `lab-starter/SOUL.md`:

```markdown
# Ticket Service — Agent Soul

## Identity
You are an engineering agent working on the Ticket Service project.

## Personality
- **Pragmatic**: Prefer simple, working solutions over clever abstractions
- **Safety-first**: Always validate inputs, never trust external data
- **Test-driven**: No feature is complete without tests
- **Transparent**: Explain trade-offs and limitations honestly

## Values
1. Working code over perfect code — ship incrementally
2. Existing patterns over new patterns — consistency matters
3. Explicit over implicit — clear errors, typed params, documented contracts
4. Team knowledge over individual cleverness

## Boundaries
- You do not make product decisions — escalate to @product-reviewer
- You do not bypass security constraints — escalate to @security-reviewer
```

### How It Connects to the Harness Model

The updated model is now **4 layers**:

```text
┌─────────────────────────────────────────────┐
│  Soul Layer    │ SOUL.md — identity, values, personality   │
├─────────────────────────────────────────────┤
│  Rule Layer    │ copilot-instructions.md — constraints     │
├─────────────────────────────────────────────┤
│  Role Layer    │ agents/*.md — specialized personas        │
├─────────────────────────────────────────────┤
│  Workflow Layer│ prompts/*.prompt.md — task templates       │
└─────────────────────────────────────────────┘
```

> [!TIP]
> **Instructor tip**: The Soul Layer is what differentiates "configuring an AI tool" from "onboarding a team member." When you onboard a new hire, you don't just hand them rules — you communicate team values, personality, and judgment. SOUL.md does the same for Agents.

### Test It: Soul-Guided Behavior

Ask the Agent a deliberately ambiguous question:

```text
Should I add a caching layer to the ticket service for better performance?
```

**Without SOUL.md**: Agent might enthusiastically add Redis, npm packages, etc.
**With SOUL.md**: Agent should apply "pragmatic" + "existing patterns over new patterns" values and push back — "The current in-memory store is sufficient for this service's scale. Adding caching introduces complexity without clear benefit."

### Enterprise Application: Soul at Different Levels

| Level | Soul Scope | Example |
|-------|-----------|---------|
| Organization | Company engineering culture | "We ship daily. We prefer boring technology." |
| Team | Team-specific conventions | "This team owns payments — never auto-approve money-related changes." |
| Project | Project personality | The SOUL.md you just created |
| Agent | Individual role identity | Defined in each agent's .md file |

In Azure-managed deployments (Container Apps), SOUL.md can be mounted as a ConfigMap equivalent; in VM deployments, it's simply a file in the repo root — both paths version-control the Agent's identity.

---

# Part B: Role Layer

## Step 3: Create a "Planner Agent" — Not Just a test-engineer

Many workshops only cover a test agent, which feels too lightweight.
A better approach is to show: **role separation itself is a harness.**

Create file:

```text
lab-starter/.github/agents/planner.agent.md
```

Content:

```markdown
---
name: planner
description: Planning-focused agent for implementation design and task breakdown
---

# Planner Agent

You are a planning specialist for this repository.

## Responsibilities
- Understand requirements
- Produce step-by-step implementation plans
- Identify impacted files
- Highlight risks, assumptions, and edge cases
- Recommend validation steps

## Rules
- Do NOT edit code directly
- Do NOT propose new frameworks or packages unless explicitly requested
- Prefer minimal changes aligned with the current repository structure
- Call out unclear requirements before implementation

## Output format
1. Goal
2. Files to modify
3. Implementation steps
4. Risks / edge cases
5. Verification steps
```

### Test Run Prompt
```text
@planner Plan how to add a PUT /tickets/:id endpoint with validation and tests.
```

### What You Want Participants to See
- It only plans — it doesn't directly modify code
- It proactively identifies affected files and edge cases
- It separates "design" from "implementation"

### Instructor Key Points
This step can be connected to the GitHub Copilot Customization Handbook's positioning of custom agents:

> An agent is not "a prompt with a different skin" — it defines a session-level role boundary.

You can also segue into the Multi-Agent chapter:
- Planner plans first
- Developer implements
- Reviewer reviews

---

## Step 4: Keep test-engineer, but Upgrade the Lab to a "Permission Boundary Demo"

Create or use:

```text
lab-starter/.github/agents/test-engineer.md
```

Then give the prompt:

```text
@test-engineer Review the ticketStore test coverage and add missing tests for update and delete operations.
```

### What to Observe
- Does it only modify test files?
- Does it proactively run tests?
- Does it output a coverage gap summary?

### Instructor Emphasis
Frame "role separation" as a harness, not a gimmick:

> A key principle of Harness Engineering is: **instead of having one omnipotent Agent do everything, have multiple constrained Agents each doing their own thing.**

This aligns with the large number of custom agents in `github/awesome-copilot`:
- Specialization
- Tool and boundary convergence
- Clear task responsibilities

---

# Part C: Workflow Layer

## Step 5: Create a More Complete Prompt File — Not Just a Simple add-endpoint Template

Create:

```text
lab-starter/.github/prompts/ship-api-change.prompt.md
```

Recommended content:

```markdown
---
name: ship-api-change
description: Plan, implement, test, and summarize an API change
mode: agent
---

Your job is to deliver an API change safely in this repository.

## Change Request
{{ change_request }}

## Workflow
1. Understand the requirement and summarize it in 2-3 bullets
2. Inspect the existing project patterns before coding
3. List files that need to change
4. Implement the change using existing conventions
5. Add or update tests
6. Run tests
7. Provide a final delivery summary

## Delivery Summary Format
- Requirement summary
- Files changed
- Tests added/updated
- Verification result
- Risks / follow-up suggestions
```

### Usage
```text
/ship-api-change change_request="Add a PUT /tickets/:id endpoint that updates title, priority, and status"
```

### Significance of This Step
It's not "just another prompt file" — it's:

> You've started templatizing your team's high-frequency workflows.

This aligns with the core philosophy of high-visibility customization repos on GitHub:
- Turn ad-hoc conversations into long-term assets
- Turn individual tricks into team-reusable capabilities

---

# Part D: Taking Harness Engineering from "Configuration" to "Engineering"

## Step 6: Add a Backpressure Discussion (This Is the Key to Deepening the Lab)

This section is the most important part of the entire lab upgrade.

### Start by Asking Participants a Question
> If the Agent writes incorrect code, how does it know it's wrong?

The answer is NOT:
- A smarter model
- A more elegant prompt

The answer is:
- Tests
- Lint
- Types
- CI
- Hooks

### Core Message for Participants
> **The essence of a harness is not "telling the Agent what to do" — it's "enabling the system to promptly tell the Agent what it did wrong."**

### Suggested Framing (Can Reference AgentPatterns / HumanLayer)

Explain it this way:

- Prompts provide the "initial direction"
- Harness provides "course correction along the way"
- Backpressure provides "self-correction"

Without backpressure, the Agent is walking in a dark room;
with backpressure, it can bump into walls and adjust its own direction.

### Hands-On Suggestion
Have participants make a small change, then ask the Agent:

```text
Implement the endpoint and do not stop until tests pass.
```

Then observe:
- Does the Agent proactively run tests?
- Does it iterate on fixes when tests fail?
- Does it reach a conclusion based on test results?

### Instructor Summary
Ground this step in enterprise value:

> What enterprises really need is not an Agent that's "occasionally brilliant,"
> but an Agent that is **predictable, regression-testable, and auditable** within an engineering system.

---

# Part E: Mapping Popular Repo Ideas to This Lab

## Reference Mapping Table

| Reference Source | Key Idea | Mapping in This Lab |
|------------------|----------|---------------------|
| `github/awesome-copilot` | Customizations should be modularly composable | Layered design of instructions / agents / prompt files |
| `walkinglabs/awesome-harness-engineering` | A harness is an entire system layer, not just prompts | This lab adds role / workflow / backpressure |
| Copilot Customization Handbook | instructions / prompts / agents / MCP each have their role | Three-layer structure separating rules, roles, tasks |
| AgentPatterns / HumanLayer | Environment design matters more than prompts | Emphasis on tests/lint/CI/boundaries over "magic prompts" |

---

## Completion Criteria (Upgraded)

Completing this lab is no longer just "created a few files" — you should reach the following understanding:

- [ ] Understood the difference between prompt engineering and harness engineering
- [ ] Created or understood the project-level role of `.github/copilot-instructions.md`
- [ ] Created or used at least 2 custom agents (e.g., planner / test-engineer)
- [ ] Created 1 reusable workflow prompt file
- [ ] Understood the role of tests / lint / CI in a harness
- [ ] Can articulate why Agent reliability is an "environment problem," not just a "model problem"

---

## Suggested Instructor Closing Remarks

> Many people think the key to AI programming is "how to write prompts that feel like magic spells."
> But truly mature teams don't pin their hopes on spells.
>
> They do three things:
> 1. Use instructions to codify project consensus
> 2. Use agents to establish clear role boundaries
> 3. Use tests / lint / CI to build automatic course-correction mechanisms
>
> That's Harness Engineering.
> It doesn't make the Agent more magical — it makes the Agent **more reliable**.

---

## Optional Bonus Exercises (For Advanced Participants)

### Bonus 1: Restrict test-engineer to Testing Tools Only
Discussion question:
- If GitHub Copilot gains finer-grained tool permission controls for custom agents in the future, which agents should have their write access restricted?

### Bonus 2: Design a security-review Prompt File
For example:
```text
/security-review target="new DELETE endpoint"
```
Requiring structured report output.

### Bonus 3: Design an Organization-Level Harness
Discussion questions:
- Which rules should be at the repo level?
- Which rules should be at the org level?
- Which rules should be at the user level?

---

## One-Sentence Summary

**Prompt engineering improves the quality of a single conversation; harness engineering improves the long-term success rate of an entire team using Agents.**

---

## Further Reading: who else is building the harness?

In 2026 the cloud vendors started shipping the harness *as a managed product* — AWS **Bedrock AgentCore Managed Harness** and Azure **AI Foundry Agent Service**. The static harness you just built (chatmodes, prompt files, MCP tools, `SKILL.md` packs) is the **same vocabulary** those platforms use, so your work here is portable to them.

→ See [`docs/managed-harness-platforms.md`](../docs/managed-harness-platforms.md) for a 10-capability AWS-vs-Azure map — **and the critical note that Azure Foundry Agent Service is not yet available on Azure China (21Vianet)**, which is exactly why the build-your-own-on-Copilot approach in this Lab is, today, the more deployable option inside that boundary.
