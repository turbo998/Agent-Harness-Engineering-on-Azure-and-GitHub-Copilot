# GitHub Copilot Workshop 180-Minute Enhanced Agenda

> **Version**: v2.0 | **Duration**: 180 minutes (with 10-minute flex buffer) | **Labs**: 5

---

## Agenda Overview

| # | Session | Duration | Cumulative |
|------|------|------|----------|
| 0 | Opening | 10min | 0:10 |
| 1 | Part 1: AI-DLC Concepts | 15min | 0:25 |
| L1 | Lab 1: AI-DLC Full Lifecycle | 20min | 0:45 |
| 2 | Part 2: Harness Engineering Deep Dive | 20min | 1:05 |
| L2 | Lab 2: Harness Engineering Practice | 25min | 1:30 |
| ☕ | Break | 10min | 1:40 |
| 3 | Part 3: Multi-Agent Collaboration & Role Division | 15min | 1:55 |
| L3 | Lab 3: Multi-Agent Sequential Collaboration | 20min | 2:15 |
| L4 | Lab 4: Multi-Role Joint Code Review | 20min | 2:35 |
| 4 | Part 4: End-to-End Release Process | 10min | 2:45 |
| L5 | Lab 5: End-to-End Release Process | 25min | 3:10 |
| 5 | Summary & Q&A | 10min | 3:20 |

> 💡 200 minutes of total content; the 10-minute flex buffer can be used to adjust Lab durations based on participant pace.

---

## Detailed Agenda

### 0. Opening (10min) ⏱ 0:00-0:10

**Goal**: Icebreaker, understand participant backgrounds, set expectations

- Instructor self-introduction
- Icebreaker: "How often do you currently use Copilot?" (show of hands/poll)
- Quick survey of participant backgrounds: programming languages, team size, AI tool experience
- Workshop objectives and agenda preview
- Environment check: confirm VS Code + Copilot Chat are ready

### 1. Part 1: AI-DLC Concepts (15min) ⏱ 0:10-0:25

**Goal**: Understand the Copilot evolution path and the AI-DLC full lifecycle

- **Three Stages of Copilot Evolution**
  - Completions → Chat → Agent
  - Capability leaps and use cases at each stage
- **AI-DLC Full Lifecycle Concept**
  - AI-Development Life Cycle (AI-DLC)
  - End-to-end AI empowerment from requirements analysis to deployment and operations
  - Comparison with traditional SDLC

### Lab 1: AI-DLC Full Lifecycle (20min) ⏱ 0:25-0:45

**Goal**: Experience the Ask → Plan → Agent three modes

- Task: Based on ticket-service requirements, use all three modes
  - Ask mode: Inquire about technical solutions
  - Plan mode: Generate an implementation plan
  - Agent mode: Automatically generate code
- Compare the output differences across the three modes

### 2. Part 2: Harness Engineering Deep Dive (20min) ⏱ 0:45-1:05

**Goal**: Master the Harness Engineering three-layer model and multi-role system

- **Three-Layer Model**
  - 🔧 **Rules Layer**: `.github/copilot-instructions.md` — Global behavior constraints
  - 🎭 **Roles Layer (Agents)**: `.github/agents/*.md` — Expert role definitions
  - 🔄 **Workflow Layer (Prompts)**: `.github/prompts/*.prompt.md` — Reusable process templates
- **Multi-Role Agent System** (inspired by the gstack methodology)
  - 10 specialized Agent roles
  - Inter-Agent collaboration and chaining
- **Safety Guardrails**
  - Input filtering, output constraints, behavior boundaries
  - Preventing prompt injection and unauthorized operations
- **Completeness Principles**
  - Ensuring testability and reviewability of AI-generated code
  - Human-AI collaboration checkpoint design

### Lab 2: Harness Engineering Practice (25min) ⏱ 1:05-1:30

**Goal**: Configure the three-layer model files

- Task 1: Write `copilot-instructions.md` global rules
- Task 2: Create a custom Agent (e.g., `@api-designer`)
- Task 3: Write a `.prompt.md` workflow template
- Verification: Invoke the custom Agent and observe behavior changes

### ☕ Break (10min) ⏱ 1:30-1:40

### 3. Part 3: Multi-Agent Collaboration & Role Division (15min) ⏱ 1:40-1:55

**Goal**: Understand multi-Agent collaboration patterns

- **10 Agent Roles Overview**
  - `@code-reviewer` — Code Review Expert
  - `@red-team` — Security Red Team
  - `@api-designer` — API Designer
  - `@test-strategist` — Test Strategist
  - `@perf-analyst` — Performance Analyst
  - `@doc-writer` — Documentation Engineer
  - `@devops-pilot` — DevOps Pilot
  - `@arch-advisor` — Architecture Advisor
  - `@accessibility-checker` — Accessibility Checker
  - `@tech-debt-tracker` — Tech Debt Tracker
- **Collaboration Patterns**
  - Sequential: Agent A output → Agent B input
  - Parallel: Multiple Agents review the same code simultaneously
- **Code Review Legion Concept**
  - Multi-perspective review: functionality + security + performance + accessibility
  - Analogy to a real team's code review process

### Lab 3: Multi-Agent Sequential Collaboration (20min) ⏱ 1:55-2:15

**Goal**: Practice Agent sequential collaboration chains

- Task: `@api-designer` designs the interface → `@code-reviewer` reviews → `@test-strategist` generates tests
- Observe how each Agent builds on the previous one's output
- Document the strengths and limitations of the collaboration chain

### Lab 4: Multi-Role Joint Code Review (20min) ⏱ 2:15-2:35

**Goal**: Experience multi-role parallel review

- Task: Review the same code with different roles:
  - `@code-reviewer` — Find code quality issues
  - `@red-team` — Find security vulnerabilities
  - `@perf-analyst` — Find performance bottlenecks
  - `@accessibility-checker` — Find accessibility issues
- Consolidate review reports and appreciate the value of multi-role review

### 4. Part 4: End-to-End Release Process (10min) ⏱ 2:35-2:45

**Goal**: Understand the Think→Plan→Build→Review→Test→Ship full process

- **gstack Six-Phase Model**
  - Think: Requirements clarification and technical research
  - Plan: Task breakdown and solution design
  - Build: Code generation and implementation
  - Review: Multi-role review
  - Test: Automated test generation
  - Ship: Release and deployment
- **Prompt Template-Driven Workflows**
  - Each phase maps to a `.prompt.md`
  - Template chaining enables end-to-end automation
  - `ship-release.prompt` example

### Lab 5: End-to-End Release Process (25min) ⏱ 2:45-3:10

**Goal**: Complete the full Think→Ship process

- Task: Use prompt templates to drive the complete release process
  - Use `think-clarify.prompt` to clarify requirements
  - Use `plan-tasks.prompt` to break down tasks
  - Use Agent mode to Build code
  - Use `review-multi.prompt` for multi-role review
  - Use `test-generate.prompt` to generate tests
  - Use `ship-release.prompt` to generate a release checklist
- Review the full process and discuss enterprise adoption feasibility

### 5. Summary & Q&A (10min) ⏱ 3:10-3:20

**Goal**: Summarize key takeaways, look ahead to adoption

- **Key Takeaways Review**
  - AI-DLC full lifecycle philosophy
  - Harness Engineering three-layer model
  - Practical value of multi-Agent collaboration
- **Enterprise Adoption Recommendations**
  - Gradual introduction: Rules → Roles → Workflows
  - Team-standardized Prompt template library
  - Security and compliance considerations
- **gstack Comparison**
  - Mapping workshop content to the gstack methodology
  - Further learning paths
- **Resource Links**
  - GitHub Copilot official documentation
  - gstack project repository
  - awesome-copilot resource collection
- **Q&A**
