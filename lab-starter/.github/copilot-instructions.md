# Project Conventions

## Language & Style
- All code must use JavaScript (CommonJS, no TypeScript).
- Follow the existing Express.js patterns in this project.
- Use `node:test` and `node:assert/strict` for tests (no Jest, no Mocha).

## Code Rules
- Every new API endpoint MUST have corresponding test cases.
- Input validation errors MUST return HTTP 400 with a JSON `{ error: "..." }` body.
- Do NOT install new npm packages without explicit approval.
- Keep functions small (< 30 lines).
- Use descriptive variable names.

## Git & PR
- Commit messages must follow: `<type>: <description>` (e.g., `feat: add summary endpoint`).
- PR descriptions must include: Problem, Solution, Test Coverage, Verification Steps.

## Security
- Never expose stack traces in API responses.
- Sanitize all user inputs before processing.
- Use existing error classes (ValidationError, NotFoundError) for known error conditions.

## Core Principles

These principles are adapted from the gstack ETHOS methodology:

1. **Completeness First (完整性优先)** — Always implement complete error handling, input validation, and edge cases. Don't cut corners. A half-working feature is worse than no feature.
2. **Search Before Building** — Check existing code patterns before creating new abstractions. Reuse > reinvent. Look at what's already in the codebase before writing something new.
3. **User Sovereignty** — Recommend approaches but never override explicit user decisions. The developer has final say.

## Safety Guardrails

- **Never delete files** without explicit confirmation from the user.
- **Never force-push** to `main` or `master` branches.
- **Never modify** `.env` or credential files.
- **Always run tests** before committing code changes.

## Code Quality Standards

- Every function must have a **JSDoc comment** describing its purpose, parameters, and return value.
- **No magic numbers** — use named constants (e.g., `const MAX_RETRIES = 3` instead of bare `3`).
- **Error messages must be actionable** — tell the user what went wrong AND how to fix it.
- **No `console.log` in production code** — use proper logging utilities instead.

## Agent Collaboration Protocol

- Each agent has a **defined role boundary** — respect it. Don't perform tasks outside your designated scope.
- When **uncertain**, ask the user rather than guessing.
- **Reference other agents by @mention** when their expertise is needed (e.g., defer security questions to `@security-reviewer`).

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
