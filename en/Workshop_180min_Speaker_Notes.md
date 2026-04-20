# GitHub Copilot Harness Engineering Workshop — Speaker Notes (180 Minutes)

## Slide 1: Welcome
**Key Points:**
- Welcome to the 180-minute GitHub Copilot deep-dive workshop
- Theme: Harness Engineering — Engineering methods for mastering AI-powered programming
- Hands-on focused, with 5 Labs throughout

**Script:** Welcome everyone! Today we'll spend 3 hours exploring the engineering approach to GitHub Copilot. It's not just about code completions — you'll learn how to systematically harness AI Agents and turn them into a true productivity multiplier for your team.

---

## Slide 2: Participant Background Survey (Copilot Usage)
**Key Points:**
- Show of hands: Who uses Copilot daily?
- Have you used Chat mode? Agent mode?
- Gauge participant levels to adjust pacing

**Script:** Before we start, I'd like to quickly understand your backgrounds. Please raise your hand: Who uses Copilot completions daily? Who has used Copilot Chat? Who has tried Agent mode? This helps me calibrate today's pace.

---

## Slide 3: Workshop Objectives & Agenda Overview
**Key Points:**
- Objective: Master the Harness Engineering three-layer model, independently configure 10 Agent roles
- Agenda: Theory → Lab exercises → Multi-Agent collaboration → End-to-end release
- Deliverables: Configuration files and Prompt templates ready to use with your team

**Script:** Today's goal is clear — you'll walk away with a complete AI engineering configuration, including 10 Agent role definitions and 6 Prompt templates, ready to deploy in your team immediately.

---

## Slide 4: Three Stages of AI-Assisted Development (Completions→Chat→Agent)
**Key Points:**
- Completions: Passive completion, accept with Tab
- Chat: Active conversation, contextual Q&A
- Agent: Autonomous execution, multi-step task orchestration

**Script:** AI-assisted development has gone through three stages. From basic code completions, to interactive Chat, to today's Agent mode — where AI can autonomously read files, run terminal commands, and create PRs. Today's focus is how to harness the Agent.

---

## Slide 5: AI-DLC Full Lifecycle Concept
**Key Points:**
- AI-DLC = AI-Development Life Cycle
- Covers: Requirements analysis → Design → Coding → Review → Testing → Deployment
- Each phase can be handled by a dedicated Agent

**Script:** AI-DLC is the concept of embedding AI throughout the entire software development lifecycle. It's not just about the coding step — from requirements breakdown to final release, every phase has a corresponding Agent role to boost efficiency.

---

## Slide 6: Lab 1 Introduction (AI-DLC Full Lifecycle Hands-On)
**Key Points:**
- Use Copilot Agent to complete a full requirements-to-code workflow
- Experience the Agent autonomously reading context, generating code, and running tests
- Duration: 15 minutes

**Script:** Now let's jump into Lab 1. Please open the lab guide and use Copilot Agent mode to complete a small feature's full lifecycle. Focus on how the Agent autonomously handles multi-step tasks.

---

## Slide 7: Harness Engineering Three-Layer Model (Rules/Roles/Workflows)
**Key Points:**
- Rules: Global rules, safety guardrails
- Roles: 10 Agent role definitions
- Workflows: 6 Prompt template-driven standard processes

**Script:** The core of Harness Engineering is the three-layer model. The Rules layer sets boundaries, the Roles layer defines responsibilities, and the Workflow layer drives standardized execution. Together, they make AI output controllable, predictable, and reusable.

---

## Slide 8: Rules Layer — copilot-instructions.md (Safety Guardrails, Code Standards)
**Key Points:**
- `.github/copilot-instructions.md` is the global instruction file
- Defines code style, security constraints, and prohibited patterns
- All Agents automatically inherit these rules

**Script:** The Rules layer is implemented via copilot-instructions.md. Write your team's coding standards and security red lines into it, and all Agent interactions will automatically comply. This is the first step toward enterprise-grade usage.

---

## Slide 9: Roles Layer — 10 Agent Roles Overview
**Key Points:**
- 10 roles: Architect, Planner, Coder, Reviewer, Tester, Debugger, DocWriter, SecurityAuditor, Refactorer, Deployer
- Each role has a dedicated system prompt and responsibility boundaries
- Stored in the `.github/agents/` directory

**Script:** We've predefined 10 Agent roles, each with distinct responsibilities. From Architect to Deployer, every role has clear duties and constraints. Think of it as a virtual team, each member focused on what they do best.

---

## Slide 10: Workflow Layer — Prompt Template-Driven (6 Templates)
**Key Points:**
- 6 templates: Requirements Analysis, Technical Design, Code Generation, Code Review, Test Generation, Release Checklist
- Templates standardize input/output formats
- Stored in the `.github/prompts/` directory

**Script:** The Workflow layer uses 6 Prompt templates to drive standardized processes. Templates define what goes in, what comes out, and the format — ensuring consistent, high-quality results regardless of who invokes the Agent.

---

## Slide 11: Lab 2 Introduction (Harness Engineering Practice)
**Key Points:**
- Configure copilot-instructions.md and Agent role files
- Use different roles to complete corresponding tasks
- Duration: 20 minutes

**Script:** In Lab 2, get hands-on with the three-layer model. Start by writing the rules file, then create at least 3 Agent roles, and finally execute a standard workflow using a Prompt template.

---

## Slide 12: Break
**Key Points:**
- 10-minute break
- Check Lab progress during the break
- TAs are available for questions

**Script:** Take a 10-minute break! Grab some coffee and digest the first half. Feel free to ask questions anytime.

---

## Slide 13: Multi-Agent Collaboration Patterns (Sequential vs Parallel, gstack Reference)
**Key Points:**
- Sequential: Agent A output → Agent B input, pipeline mode
- Parallel: Multiple Agents work simultaneously, results merged
- gstack reference architecture: layered multi-Agent orchestration

**Script:** A single Agent is powerful, but multi-Agent collaboration is where the real productivity leap happens. Sequential mode works like a pipeline; parallel mode works like team collaboration. gstack provides a reference architecture for layered orchestration.

---

## Slide 14: Code Review Legion Concept (4 Reviewer Roles)
**Key Points:**
- Logic Reviewer: Business logic correctness
- Security Reviewer: Security vulnerability scanning
- Performance Reviewer: Performance bottleneck identification
- Style Reviewer: Code style and standards

**Script:** The Code Review Legion is a classic multi-Agent parallel scenario. Four Reviewers each examine a different dimension, then consolidate findings — more comprehensive and faster than a single-person review.

---

## Slide 15: Lab 3 Introduction (Multi-Agent Sequential Collaboration)
**Key Points:**
- Architect → Planner → Coder sequential pipeline
- Each step's output becomes the next step's input
- Duration: 15 minutes

**Script:** Lab 3 is about sequential collaboration. Let the Architect propose a solution, the Planner break it into tasks, and the Coder implement it. Experience how context flows between Agents.

---

## Slide 16: Lab 4 Introduction (Multi-Role Joint Code Review)
**Key Points:**
- Give the same code to 4 Reviewers for parallel review
- Compare the different issues found by different roles
- Duration: 15 minutes

**Script:** In Lab 4, have 4 Reviewers examine the same piece of code simultaneously. You'll see that the Security Reviewer and Performance Reviewer focus on entirely different aspects — multi-dimensional review dramatically improves code quality.

---

## Slide 17: End-to-End Release Process Think→Plan→Build→Review→Test→Ship
**Key Points:**
- 6-phase closed loop: Think→Plan→Build→Review→Test→Ship
- Each phase maps to specific Agents and Prompt templates
- The entire process is traceable and reproducible

**Script:** The end-to-end release process ties everything together. From product thinking to final release, 6 phases form a closed loop, each supported by corresponding Agents and templates, achieving engineering-grade AI-assisted development.

---

## Slide 18: Lab 5 Introduction (End-to-End Release Process Hands-On)
**Key Points:**
- Complete a feature's full Think-to-Ship process
- Combine multiple Agents and Prompt templates
- Duration: 25 minutes

**Script:** The final comprehensive Lab! Complete a small feature's end-to-end release, walking through the entire Think-to-Ship process. This is the culmination of everything we've covered today.

---

## Slide 19: Enterprise Adoption Recommendations (Gradual Adoption Roadmap)
**Key Points:**
- Month 1: Deploy the Rules layer, org-wide copilot-instructions.md
- Month 2: Introduce 3-5 core Agent roles
- Month 3: Roll out Prompt templates and multi-Agent collaboration workflows

**Script:** For enterprise adoption, take a gradual approach. Start with the Rules layer to unify coding standards; then progressively introduce Agent roles and workflow templates. Don't try to do everything at once — let the team adapt step by step.

---

## Slide 20: Summary, Resources & Q&A
**Key Points:**
- Recap: Three-layer model + 5 Labs + 10 Agents + 6 templates
- Resources: GitHub docs, sample repositories, community forums
- Open Q&A

**Script:** Today we went from the evolution of AI-assisted development to hands-on Harness Engineering practice. Take your configuration files and templates with you — they're ready to use. Now let's open the floor for questions — anything goes!
