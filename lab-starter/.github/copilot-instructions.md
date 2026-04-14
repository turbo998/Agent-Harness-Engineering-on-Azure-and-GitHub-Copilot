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
